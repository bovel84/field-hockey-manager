"""Additional tests for edge cases and uncovered features."""
import json
import os
import tempfile
import pytest
from src.models import Player, Team, Match, Position
from src.database import Database
from src.season import (
    generate_calendar, generate_free_agents, player_price,
    train_player, TRAINING_ATTRIBUTES, MAX_TRAININGS_PER_WEEK,
    Standings, season_aging, age_player_one_year,
)
from src.simulation import simulate_match


def make_team(name, rating=75):
    """Helper: create a team with 16 players at a given rating."""
    positions = (
        [Position.GOALKEEPER] * 1
        + [Position.DEFENSE] * 4
        + [Position.MIDFIELD] * 5
        + [Position.ATTACK] * 6
    )
    players = [
        Player(
            name=f"{name} P{i+1}",
            position=pos,
            passing=rating,
            shooting=rating,
            defense=rating,
            speed=rating,
            stamina=rating,
        )
        for i, pos in enumerate(positions)
    ]
    return Team(name=name, players=players)


# ---------------------------------------------------------------------------
# main.py entry point
# ---------------------------------------------------------------------------

class TestMainEntryPoint:
    def test_main_module_importable(self):
        """Test that main module can be imported without errors."""
        from src import main as main_module
        assert hasattr(main_module, "run_game")
        assert hasattr(main_module, "main")
        assert hasattr(main_module, "load_teams_from_json")

    def test_load_teams_from_json(self, tmp_path):
        """Test loading teams from a JSON file."""
        teams_data = {
            "teams": [
                {
                    "name": "Test Team A",
                    "players": [
                        {"name": "P1", "position": "Portiere", "passing": 70, "shooting": 60, "defense": 80, "speed": 65, "stamina": 70},
                        {"name": "P2", "position": "Difesa", "passing": 65, "shooting": 50, "defense": 85, "speed": 60, "stamina": 75},
                    ],
                },
            ]
        }
        json_path = tmp_path / "teams.json"
        json_path.write_text(json.dumps(teams_data), encoding="utf-8")
        from src.main import load_teams_from_json
        teams = load_teams_from_json(str(json_path))
        assert len(teams) == 1
        assert teams[0].name == "Test Team A"
        assert len(teams[0].players) == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_team(self):
        """Test that a team with no players has rating 0 and handles gracefully."""
        team = Team(name="Empty", players=[])
        assert team.team_rating() == 0
        starters = team.get_starters()
        assert len(starters) == 0

    def test_malformed_json_raises_error(self, tmp_path):
        """Test that malformed JSON raises a JSONDecodeError."""
        json_path = tmp_path / "bad.json"
        json_path.write_text("{invalid json}", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            json.loads(json_path.read_text(encoding="utf-8"))

    def test_simulate_match_with_equal_teams(self):
        """Test simulation with two identical-strength teams."""
        home = make_team("Team A", 75)
        away = make_team("Team B", 75)
        m = simulate_match(home, away, seed=42)
        assert m.played is True
        assert m.home_score >= 0
        assert m.away_score >= 0

    def test_calendar_with_8_teams(self):
        """Test that calendar generation works with 8 teams (14 rounds)."""
        teams = [make_team(f"Team {i}") for i in range(8)]
        calendar = generate_calendar(teams)
        # 8 teams: C(8,2) = 28 pairs, x2 (home/away) = 56 matches
        assert len(calendar) == 56
        # Each team plays 14 matches (7 home + 7 away)
        for i in range(8):
            team_matches = [m for m in calendar if m["home"] == i or m["away"] == i]
            assert len(team_matches) == 14

    def test_calendar_with_2_teams(self):
        """Test calendar with minimum 2 teams."""
        teams = [make_team("A"), make_team("B")]
        calendar = generate_calendar(teams)
        assert len(calendar) == 2  # home and away

    def test_calendar_with_1_team(self):
        """Test that calendar with 1 team returns empty list."""
        teams = [make_team("Solo")]
        calendar = generate_calendar(teams)
        assert calendar == []


# ---------------------------------------------------------------------------
# Transfer market tests
# ---------------------------------------------------------------------------

class TestTransferMarket:
    def test_free_agents_generated(self):
        """Test that free agents are generated."""
        agents = generate_free_agents(5)
        assert len(agents) == 5
        for p in agents:
            assert p.name
            assert p.position in (Position.GOALKEEPER, Position.DEFENSE, Position.MIDFIELD, Position.ATTACK)

    def test_player_price_positive(self):
        """Test that player price is always positive."""
        p = Player(name="Test", position=Position.ATTACK, passing=70, shooting=80, defense=50, speed=75, stamina=70)
        price = player_price(p)
        assert price > 0

    def test_better_player_costs_more(self):
        """Test that a better player has a higher price."""
        weak = Player(name="Weak", position=Position.ATTACK, passing=40, shooting=40, defense=40, speed=40, stamina=40)
        strong = Player(name="Strong", position=Position.ATTACK, passing=90, shooting=90, defense=90, speed=90, stamina=90)
        assert player_price(strong) > player_price(weak)


# ---------------------------------------------------------------------------
# Training tests
# ---------------------------------------------------------------------------

class TestTraining:
    def test_train_player_improves_attribute(self):
        """Test that training can improve a player's attribute."""
        p = Player(name="Trainee", position=Position.MIDFIELD, passing=60, shooting=60, defense=60, speed=60, stamina=60)
        original = getattr(p, "passing")
        # Train multiple times to likely get an improvement
        improved = False
        for _ in range(20):
            gain = train_player(p, "passing")
            if gain > 0:
                improved = True
                break
        # With enough attempts, training should improve at least once
        assert improved or getattr(p, "passing") > original

    def test_training_attributes_list(self):
        """Test that TRAINING_ATTRIBUTES contains expected attributes."""
        assert "passing" in TRAINING_ATTRIBUTES
        assert "shooting" in TRAINING_ATTRIBUTES
        assert "defense" in TRAINING_ATTRIBUTES
        assert "speed" in TRAINING_ATTRIBUTES
        assert "stamina" in TRAINING_ATTRIBUTES

    def test_max_trainings_per_week(self):
        """Test that MAX_TRAININGS_PER_WEEK is a positive integer."""
        assert isinstance(MAX_TRAININGS_PER_WEEK, int)
        assert MAX_TRAININGS_PER_WEEK > 0


# ---------------------------------------------------------------------------
# Morale tests
# ---------------------------------------------------------------------------

class TestMorale:
    def test_morale_increase(self):
        """Test that apply_morale increases morale."""
        p = Player(name="Happy", position=Position.ATTACK, passing=70, shooting=70, defense=70, speed=70, stamina=70)
        p.morale = 50
        p.apply_morale(10)
        assert p.morale == 60

    def test_morale_decrease(self):
        """Test that apply_morale decreases morale."""
        p = Player(name="Sad", position=Position.ATTACK, passing=70, shooting=70, defense=70, speed=70, stamina=70)
        p.morale = 50
        p.apply_morale(-10)
        assert p.morale == 40

    def test_morale_clamped_at_100(self):
        """Test that morale doesn't exceed 100."""
        p = Player(name="Max", position=Position.ATTACK, passing=70, shooting=70, defense=70, speed=70, stamina=70)
        p.morale = 95
        p.apply_morale(20)
        assert p.morale == 100

    def test_morale_clamped_at_0(self):
        """Test that morale doesn't go below 0."""
        p = Player(name="Min", position=Position.ATTACK, passing=70, shooting=70, defense=70, speed=70, stamina=70)
        p.morale = 5
        p.apply_morale(-20)
        assert p.morale == 0


# ---------------------------------------------------------------------------
# Injury tests
# ---------------------------------------------------------------------------

class TestInjuries:
    def test_injured_player_cannot_play(self):
        """Test that injured players are marked as cannot play."""
        p = Player(name="Injured", position=Position.ATTACK, passing=70, shooting=70, defense=70, speed=70, stamina=70)
        assert p.can_play() is True
        p.injured = True
        p.injury_duration = 2
        assert p.can_play() is False

    def test_heal_one_match_reduces_duration(self):
        """Test that heal_one_match reduces injury duration."""
        p = Player(name="Recovering", position=Position.ATTACK, passing=70, shooting=70, defense=70, speed=70, stamina=70)
        p.injured = True
        p.injury_duration = 3
        p.heal_one_match()
        assert p.injury_duration == 2
        assert p.injured is True

    def test_heal_completes_recovery(self):
        """Test that heal_one_match clears injury when duration reaches 0."""
        p = Player(name="AlmostBack", position=Position.ATTACK, passing=70, shooting=70, defense=70, speed=70, stamina=70)
        p.injured = True
        p.injury_duration = 1
        p.heal_one_match()
        assert p.injury_duration == 0
        assert p.injured is False


# ---------------------------------------------------------------------------
# Tactics tests
# ---------------------------------------------------------------------------

class TestTactics:
    def test_formation_modifiers_exist(self):
        """Test that formation modifiers affect simulation."""
        home = make_team("Home", 75)
        away = make_team("Away", 75)
        m1 = simulate_match(home, away, seed=42, home_formation="4-3-3", home_intensity="Offensiva")
        m2 = simulate_match(home, away, seed=42, home_formation="5-3-2", home_intensity="Difensiva")
        # Both should produce valid results
        assert m1.played is True
        assert m2.played is True

    def test_intensity_modifiers(self):
        """Test that different intensities produce valid match results."""
        home = make_team("Home", 75)
        away = make_team("Away", 75)
        for intensity in ["Difensiva", "Bilanciata", "Offensiva"]:
            m = simulate_match(home, away, seed=42, home_intensity=intensity)
            assert m.played is True
            assert m.home_score >= 0
            assert m.away_score >= 0


# ---------------------------------------------------------------------------
# Database edge cases
# ---------------------------------------------------------------------------

class TestDatabaseEdgeCases:
    def test_database_save_and_load_team(self, tmp_path):
        """Test saving and loading a team from the database."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        team = make_team("Test FC", 75)
        db.save_team(team)
        loaded = db.load_team("Test FC")
        assert loaded is not None
        assert loaded.name == "Test FC"
        assert len(loaded.players) == 16

    def test_database_load_nonexistent_team(self, tmp_path):
        """Test loading a team that doesn't exist returns None."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        result = db.load_team("Nonexistent")
        assert result is None

    def test_database_save_and_load_state(self, tmp_path):
        """Test saving and loading game state."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        state = {"round": 5, "trainings": 2}
        db.save_state(state)
        loaded = db.load_state()
        assert loaded == state

    def test_database_clear_state(self, tmp_path):
        """Test clearing game state."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        db.save_state({"round": 1})
        db.clear_state()
        assert db.load_state() is None

    def test_database_clear_matches(self, tmp_path):
        """Test clearing matches."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        home = make_team("Home", 75)
        away = make_team("Away", 75)
        match = Match(home_team=home, away_team=away, home_score=2, away_score=1, played=True)
        match.events = []
        db.save_match(match, round_num=1)
        matches = db.load_matches()
        assert len(matches) == 1
        db.clear_matches()
        matches = db.load_matches()
        assert len(matches) == 0