"""Tests for season: calendar generation, standings, training, and transfers."""
import pytest
import random
from src.models import Team, Player, Position, Match
from src.season import (
    generate_calendar, Standings, train_player, TRAINING_ATTRIBUTES,
    MAX_TRAININGS_PER_WEEK, generate_free_agents, player_price,
    season_aging, age_player_one_year,
)


def make_team(name, rating=75):
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


class TestCalendar:
    def test_generate_calendar_6_teams(self):
        teams = [make_team(f"Team {i}") for i in range(6)]
        calendar = generate_calendar(teams)
        assert len(calendar) > 0
        for match in calendar:
            assert match["home"] is not None
            assert match["away"] is not None
            assert match["home"] != match["away"]

    def test_calendar_10_rounds_for_user_team(self):
        teams = [make_team(f"Team {i}") for i in range(6)]
        calendar = generate_calendar(teams, user_team_index=0)
        user_matches = [m for m in calendar if m["home"] == 0 or m["away"] == 0]
        assert len(user_matches) == 10

    def test_no_team_plays_itself(self):
        teams = [make_team(f"Team {i}") for i in range(6)]
        calendar = generate_calendar(teams)
        for m in calendar:
            assert m["home"] != m["away"]


class TestStandings:
    def test_update_standings_home_win(self):
        home = make_team("HC Cagliari")
        away = make_team("HC Roma")
        match = Match(home_team=home, away_team=away, home_score=3, away_score=1, played=True)
        standings = Standings()
        standings.update(match)
        assert standings.get_points("HC Cagliari") == 3
        assert standings.get_points("HC Roma") == 0
        assert standings.get_wins("HC Cagliari") == 1
        assert standings.get_losses("HC Roma") == 1

    def test_update_standings_away_win(self):
        home = make_team("HC Cagliari")
        away = make_team("HC Roma")
        match = Match(home_team=home, away_team=away, home_score=0, away_score=2, played=True)
        standings = Standings()
        standings.update(match)
        assert standings.get_points("HC Roma") == 3
        assert standings.get_points("HC Cagliari") == 0

    def test_update_standings_draw(self):
        home = make_team("HC Cagliari")
        away = make_team("HC Roma")
        match = Match(home_team=home, away_team=away, home_score=1, away_score=1, played=True)
        standings = Standings()
        standings.update(match)
        assert standings.get_points("HC Cagliari") == 1
        assert standings.get_points("HC Roma") == 1
        assert standings.get_draws("HC Cagliari") == 1
        assert standings.get_draws("HC Roma") == 1

    def test_goals_for_against(self):
        home = make_team("HC Cagliari")
        away = make_team("HC Roma")
        match = Match(home_team=home, away_team=away, home_score=3, away_score=1, played=True)
        standings = Standings()
        standings.update(match)
        assert standings.get_goals_for("HC Cagliari") == 3
        assert standings.get_goals_against("HC Cagliari") == 1
        assert standings.get_goals_for("HC Roma") == 1
        assert standings.get_goals_against("HC Roma") == 3

    def test_ranking_sorted(self):
        teams = {
            "A": make_team("A"),
            "B": make_team("B"),
            "C": make_team("C"),
        }
        standings = Standings()
        standings.update(Match(home_team=teams["A"], away_team=teams["B"], home_score=2, away_score=0, played=True))
        standings.update(Match(home_team=teams["C"], away_team=teams["A"], home_score=1, away_score=0, played=True))
        standings.update(Match(home_team=teams["B"], away_team=teams["C"], home_score=3, away_score=1, played=True))
        ranking = standings.get_ranking()
        assert len(ranking) == 3
        for entry in ranking:
            assert entry["points"] == 3

    def test_multiple_updates_accumulate(self):
        home = make_team("HC Cagliari")
        away = make_team("HC Roma")
        standings = Standings()
        m1 = Match(home_team=home, away_team=away, home_score=2, away_score=1, played=True)
        m2 = Match(home_team=away, away_team=home, home_score=1, away_score=0, played=True)
        standings.update(m1)
        standings.update(m2)
        assert standings.get_points("HC Cagliari") == 3
        assert standings.get_points("HC Roma") == 3
        assert standings.get_wins("HC Cagliari") == 1
        assert standings.get_wins("HC Roma") == 1


class TestTraining:
    def test_train_young_player(self):
        """Young players (<=22) should improve by +1 or +2."""
        p = Player(name="Young", position=Position.MIDFIELD, passing=50, age=20)
        rng = random.Random(42)
        total_gain = 0
        for _ in range(20):
            gain = train_player(p, "passing", rng)
            total_gain += gain
        assert total_gain > 0
        assert p.passing > 50

    def test_train_old_player(self):
        """Old players (>30) may not improve at all."""
        p = Player(name="Old", position=Position.MIDFIELD, passing=50, age=35)
        rng = random.Random(42)
        gains = []
        for _ in range(20):
            gain = train_player(p, "passing", rng)
            gains.append(gain)
        # At least some should be 0 (50% chance)
        assert 0 in gains

    def test_train_invalid_attribute(self):
        p = Player(name="Test", position=Position.MIDFIELD, passing=50)
        gain = train_player(p, "nonexistent", random.Random(42))
        assert gain == 0

    def test_train_caps_at_99(self):
        p = Player(name="Test", position=Position.MIDFIELD, passing=98, age=20)
        rng = random.Random(42)
        train_player(p, "passing", rng)
        assert p.passing <= 99

    def test_max_trainings_per_week(self):
        assert MAX_TRAININGS_PER_WEEK == 3

    def test_training_attributes_list(self):
        assert "passing" in TRAINING_ATTRIBUTES
        assert "shooting" in TRAINING_ATTRIBUTES
        assert "defense" in TRAINING_ATTRIBUTES
        assert "speed" in TRAINING_ATTRIBUTES
        assert "stamina" in TRAINING_ATTRIBUTES


class TestSeasonAging:
    def test_season_aging_old_player(self):
        """Players >30 should degrade by -1 in all attributes."""
        p = Player(name="Old", position=Position.MIDFIELD,
                   passing=70, shooting=70, defense=70, speed=70, stamina=70, age=32)
        season_aging(p)
        assert p.passing == 69
        assert p.shooting == 69
        assert p.defense == 69
        assert p.speed == 69
        assert p.stamina == 69

    def test_season_aging_young_player(self):
        """Players <=30 should not degrade."""
        p = Player(name="Young", position=Position.MIDFIELD,
                   passing=70, shooting=70, defense=70, speed=70, stamina=70, age=25)
        season_aging(p)
        assert p.passing == 70
        assert p.shooting == 70

    def test_season_aging_min_20(self):
        """Attributes should not go below 20."""
        p = Player(name="Old", position=Position.MIDFIELD,
                   passing=21, shooting=21, defense=21, speed=21, stamina=21, age=35)
        season_aging(p)
        assert p.passing == 20
        assert p.shooting == 20

    def test_age_player_one_year(self):
        p = Player(name="Test", position=Position.MIDFIELD, age=25)
        age_player_one_year(p)
        assert p.age == 26


class TestTransferMarket:
    def test_generate_free_agents(self):
        rng = random.Random(42)
        agents = generate_free_agents(5, rng)
        assert len(agents) == 5
        for a in agents:
            assert a.name  # has a name
            assert a.position in Position
            assert 16 <= a.age <= 35

    def test_generate_free_agents_count(self):
        rng = random.Random(42)
        agents = generate_free_agents(3, rng)
        assert len(agents) == 3

    def test_player_price(self):
        p = Player(name="Test", position=Position.MIDFIELD,
                   passing=80, shooting=80, defense=80, speed=80, stamina=80, age=25)
        price = player_price(p)
        assert price > 0

    def test_player_price_younger_costs_more(self):
        young = Player(name="Young", position=Position.ATTACK,
                       passing=80, shooting=80, defense=80, speed=80, stamina=80, age=20)
        old = Player(name="Old", position=Position.ATTACK,
                     passing=80, shooting=80, defense=80, speed=80, stamina=80, age=33)
        assert player_price(young) > player_price(old)

    def test_player_price_minimum(self):
        p = Player(name="Low", position=Position.GOALKEEPER,
                   passing=20, shooting=20, defense=20, speed=20, stamina=20, age=35)
        assert player_price(p) >= 10