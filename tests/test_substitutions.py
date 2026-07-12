"""Tests for in-match substitutions and stamina decay (1.1)."""
import pytest
from src.models import Player, Team, Match, Position
from src.simulation import simulate_match, _stamina_decay, _make_substitution


def make_team(name, rating=75, stamina=75):
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
            stamina=stamina,
        )
        for i, pos in enumerate(positions)
    ]
    return Team(name=name, players=players)


class TestStaminaDecay:
    def test_no_decay_quarters_1_2(self):
        """Stamina decay should be 0 for quarters 1 and 2."""
        players = [Player(name="P1", position=Position.MIDFIELD, stamina=50)]
        assert _stamina_decay(players, 1) == 0.0
        assert _stamina_decay(players, 2) == 0.0

    def test_decay_quarters_3_4(self):
        """Stamina decay should be > 0 for quarters 3 and 4 with low stamina."""
        players = [Player(name="P1", position=Position.MIDFIELD, stamina=50)]
        decay = _stamina_decay(players, 3)
        assert decay > 0.0
        decay = _stamina_decay(players, 4)
        assert decay > 0.0

    def test_high_stamina_less_decay(self):
        """Players with high stamina should have less decay."""
        low_stamina = [Player(name="P1", position=Position.MIDFIELD, stamina=50)]
        high_stamina = [Player(name="P1", position=Position.MIDFIELD, stamina=90)]
        low_decay = _stamina_decay(low_stamina, 4)
        high_decay = _stamina_decay(high_stamina, 4)
        assert low_decay > high_decay

    def test_empty_players_no_decay(self):
        """Empty player list should return 0 decay."""
        assert _stamina_decay([], 3) == 0.0

    def test_decay_max_15_percent(self):
        """Decay should never exceed 0.15."""
        players = [Player(name="P1", position=Position.MIDFIELD, stamina=1)]
        decay = _stamina_decay(players, 4)
        assert decay <= 0.15


class TestSubstitutions:
    def test_make_substitution_success(self):
        """_make_substitution should replace a player in the active list."""
        team = make_team("Test", 75)
        starters = team.get_starters()
        bench_player = [p for p in team.players if p not in starters and p.can_play()][0]
        out_player = starters[0]

        sub = {"quarter": 3, "out": out_player.name, "in": bench_player.name}
        result = _make_substitution(team, sub, starters, "home")

        assert result is not None
        assert result["type"] == "substitution"
        assert result["out"] == out_player.name
        assert result["in"] == bench_player.name
        assert result["team"] == "home"
        assert bench_player in starters
        assert out_player not in starters

    def test_make_substitution_player_not_found(self):
        """_make_substitution should return None if out player not in active list."""
        team = make_team("Test", 75)
        starters = team.get_starters()
        bench_player = [p for p in team.players if p not in starters and p.can_play()][0]

        sub = {"quarter": 3, "out": "Nonexistent", "in": bench_player.name}
        result = _make_substitution(team, sub, starters, "home")
        assert result is None

    def test_make_substitution_replacement_not_found(self):
        """_make_substitution should return None if replacement not on team."""
        team = make_team("Test", 75)
        starters = team.get_starters()

        sub = {"quarter": 3, "out": starters[0].name, "in": "Nonexistent"}
        result = _make_substitution(team, sub, starters, "home")
        assert result is None

    def test_simulate_match_with_subs(self):
        """simulate_match should accept and process substitutions."""
        home = make_team("Home", 75)
        away = make_team("Away", 70)
        starters = home.get_starters()
        bench = [p for p in home.players if p not in starters and p.can_play()]

        if bench:
            home_subs = [{"quarter": 3, "out": starters[0].name, "in": bench[0].name}]
            m = simulate_match(home, away, seed=42, home_subs=home_subs)
            assert m.played is True
            sub_events = [e for e in m.events if e.get("type") == "substitution"]
            assert len(sub_events) >= 1

    def test_max_3_subs_per_team(self):
        """simulate_match should enforce max 3 substitutions per team."""
        home = make_team("Home", 75)
        away = make_team("Away", 70)
        starters = home.get_starters()
        bench = [p for p in home.players if p not in starters and p.can_play()]

        # Try to make 5 subs (should be capped at 3)
        home_subs = []
        for i in range(min(5, len(bench))):
            if i < len(starters):
                home_subs.append({"quarter": 2 + i % 2, "out": starters[i].name, "in": bench[i].name})

        m = simulate_match(home, away, seed=42, home_subs=home_subs)
        sub_events = [e for e in m.events if e.get("type") == "substitution" and e.get("team") == "home"]
        assert len(sub_events) <= 3

    def test_match_without_subs_still_works(self):
        """simulate_match should work fine without any substitutions (backward compat)."""
        home = make_team("Home", 75)
        away = make_team("Away", 70)
        m = simulate_match(home, away, seed=42)
        assert m.played is True
        assert m.home_score >= 0
        assert m.away_score >= 0

    def test_low_stamina_team_scores_less_late(self):
        """Teams with low stamina should score fewer late-quarter goals than high stamina."""
        low_stamina = make_team("Low", 75, stamina=40)
        high_stamina = make_team("High", 75, stamina=90)

        # Run many simulations: low_stamina vs high_stamina
        # Count goals scored by each team in Q3+Q4
        low_late_goals = 0
        high_late_goals = 0
        for seed in range(200):
            m = simulate_match(low_stamina, high_stamina, seed=seed)
            for e in m.events:
                if e.get("type") == "goal" and e.get("quarter", 0) >= 3:
                    if e.get("team") == "home":
                        low_late_goals += 1
                    elif e.get("team") == "away":
                        high_late_goals += 1
        # High stamina team should score more late goals than low stamina
        assert high_late_goals >= low_late_goals