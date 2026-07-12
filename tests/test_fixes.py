"""Tests for the fixes requested in the review: auto-subs, seed, CupBracket __str__, playoff edge cases."""
import random
import pytest
from src.models import Player, Team, Match, Position
from src.simulation import simulate_match, generate_auto_subs
from src.season import (
    Standings, generate_youth_prospects, generate_playoff_bracket,
    simulate_playoff, generate_cup_bracket, simulate_cup, CupBracket,
)


class TestAutoSubs:
    """m2 — Auto-subs when user doesn't choose substitutions."""

    def test_auto_subs_generates_up_to_3(self):
        """generate_auto_subs should return up to 3 substitution dicts."""
        players = []
        for i in range(14):
            players.append(Player(
                name=f"Player{i}", position=Position.ATTACK,
                passing=50 + i, shooting=50 + i, defense=50 + i,
                speed=50 + i, stamina=30 + i * 3,  # varied stamina
            ))
        team = Team(name="Test FC", players=players)
        subs = generate_auto_subs(team)
        assert len(subs) <= 3
        assert len(subs) > 0
        for sub in subs:
            assert "out" in sub
            assert "in" in sub
            assert sub["quarter"] == 3

    def test_auto_subs_picks_tired_starters(self):
        """Auto-subs should replace the players with lowest stamina."""
        players = [
            Player(name="Fresh1", position=Position.ATTACK, stamina=90, shooting=80),
            Player(name="Fresh2", position=Position.ATTACK, stamina=90, shooting=80),
            Player(name="Tired1", position=Position.ATTACK, stamina=30, shooting=80),
            Player(name="Tired2", position=Position.ATTACK, stamina=25, shooting=80),
            Player(name="Bench1", position=Position.ATTACK, stamina=85, shooting=75),
            Player(name="Bench2", position=Position.ATTACK, stamina=85, shooting=75),
            Player(name="Bench3", position=Position.ATTACK, stamina=85, shooting=75),
        ]
        team = Team(name="Test FC", players=players)
        subs = generate_auto_subs(team)
        out_names = [s["out"] for s in subs]
        # Tired players should be substituted out
        assert "Tired1" in out_names or "Tired2" in out_names

    def test_auto_subs_empty_team(self):
        """generate_auto_subs with no players returns empty list."""
        team = Team(name="Empty FC", players=[])
        subs = generate_auto_subs(team)
        assert subs == []

    def test_simulate_match_auto_subs_when_none_provided(self):
        """simulate_match should auto-sub when no manual subs are given."""
        players = []
        for i in range(14):
            players.append(Player(
                name=f"P{i}", position=Position.ATTACK,
                passing=50, shooting=50, defense=50,
                speed=50, stamina=20 + i * 5,
            ))
        home = Team(name="Home FC", players=players[:14])
        away = Team(name="Away FC", players=players[:14])
        match = simulate_match(home, away, seed=42)
        sub_events = [e for e in match.events if e.get("type") == "substitution"]
        # Auto-subs should produce at least some substitutions
        assert len(sub_events) > 0


class TestYouthProspectsSeed:
    """m3 — Youth prospects with optional seed."""

    def test_generate_youth_prospects_with_seed(self):
        """generate_youth_prospects should be deterministic with a seed."""
        team = Team(name="Test FC", players=[], prestige=20)
        prospects1 = generate_youth_prospects(team, seed=12345)
        prospects2 = generate_youth_prospects(team, seed=12345)
        assert len(prospects1) == len(prospects2)
        for p1, p2 in zip(prospects1, prospects2):
            assert p1.name == p2.name
            assert p1.potential == p2.potential
            assert p1.age == p2.age

    def test_different_seeds_different_results(self):
        """Different seeds should generally produce different prospects."""
        team = Team(name="Test FC", players=[], prestige=0)
        prospects1 = generate_youth_prospects(team, seed=1)
        prospects2 = generate_youth_prospects(team, seed=999)
        # Names or potential should differ (very high probability with different seeds)
        names1 = [p.name for p in prospects1]
        names2 = [p.name for p in prospects2]
        assert names1 != names2 or [p.potential for p in prospects1] != [p.potential for p in prospects2]


class TestCupBracketStr:
    """m4 — CupBracket __str__ method."""

    def test_cup_bracket_str_shows_rounds(self):
        """CupBracket.__str__ should show rounds and matches."""
        teams = [
            Team(name=f"Team{i}", players=[Player(name=f"P{i}", position=Position.ATTACK)])
            for i in range(4)
        ]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        s = str(bracket)
        assert "Round" in s
        assert "Team" in s

    def test_cup_bracket_str_shows_winner_after_simulation(self):
        """CupBracket.__str__ should show winner after simulate_cup."""
        teams = [
            Team(name=f"Team{i}", players=[
                Player(name=f"P{i}_{j}", position=Position.ATTACK, shooting=50 + i * 5)
                for j in range(11)
            ])
            for i in range(4)
        ]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        simulate_cup(bracket, seed=99)
        s = str(bracket)
        assert "Vincitore" in s

    def test_cup_bracket_empty_str(self):
        """Empty CupBracket should have a meaningful __str__."""
        bracket = CupBracket()
        s = str(bracket)
        assert "vuoto" in s.lower()


class TestPlayoffEdgeCases:
    """m6 — Playoff with fewer than 4 teams."""

    def test_playoff_with_3_teams(self):
        """Playoff should work with 3 teams (1st gets a bye)."""
        teams = [
            Team(name=f"Team{i}", players=[
                Player(name=f"P{i}_{j}", position=Position.ATTACK, shooting=50 + i * 5)
                for j in range(11)
            ])
            for i in range(3)
        ]
        standings = Standings()
        # Create some matches to generate standings
        m1 = Match(home_team=teams[0], away_team=teams[1], home_score=3, away_score=1, played=True)
        m2 = Match(home_team=teams[1], away_team=teams[2], home_score=2, away_score=2, played=True)
        m3 = Match(home_team=teams[0], away_team=teams[2], home_score=1, away_score=0, played=True)
        standings.update(m1)
        standings.update(m2)
        standings.update(m3)

        bracket = generate_playoff_bracket(teams, standings)
        winner = simulate_playoff(bracket, seed=42)
        assert winner is not None
        assert winner in teams

    def test_playoff_with_2_teams(self):
        """Playoff should work with just 2 teams (single final)."""
        teams = [
            Team(name=f"Team{i}", players=[
                Player(name=f"P{i}_{j}", position=Position.ATTACK, shooting=50 + i * 5)
                for j in range(11)
            ])
            for i in range(2)
        ]
        standings = Standings()
        m1 = Match(home_team=teams[0], away_team=teams[1], home_score=2, away_score=1, played=True)
        standings.update(m1)

        bracket = generate_playoff_bracket(teams, standings)
        winner = simulate_playoff(bracket, seed=42)
        assert winner is not None
        assert winner in teams

    def test_playoff_with_less_than_2_raises(self):
        """Playoff with fewer than 2 teams should raise ValueError."""
        teams = [Team(name="Only Team", players=[Player(name="P1", position=Position.ATTACK)])]
        standings = Standings()
        with pytest.raises(ValueError):
            generate_playoff_bracket(teams, standings)


class TestPlayoffStatsIsolation:
    """M2 — Playoff statistics should not contaminate regular season standings."""

    def test_playoff_does_not_update_standings(self):
        """simulate_playoff should not add points to regular season standings."""
        teams = [
            Team(name=f"Team{i}", players=[
                Player(name=f"P{i}_{j}", position=Position.ATTACK, shooting=50 + i * 5)
                for j in range(11)
            ])
            for i in range(4)
        ]
        standings = Standings()
        # Regular season
        m1 = Match(home_team=teams[0], away_team=teams[3], home_score=2, away_score=1, played=True)
        m2 = Match(home_team=teams[1], away_team=teams[2], home_score=3, away_score=0, played=True)
        standings.update(m1)
        standings.update(m2)

        points_before = {t.name: standings.get_points(t.name) for t in teams}

        # Run playoff
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=42)

        # Standings should be unchanged
        points_after = {t.name: standings.get_points(t.name) for t in teams}
        assert points_before == points_after

    def test_cup_does_not_update_standings(self):
        """simulate_cup should not add points to regular season standings."""
        teams = [
            Team(name=f"Team{i}", players=[
                Player(name=f"P{i}_{j}", position=Position.ATTACK, shooting=50 + i * 5)
                for j in range(11)
            ])
            for i in range(4)
        ]
        standings = Standings()
        m1 = Match(home_team=teams[0], away_team=teams[1], home_score=1, away_score=0, played=True)
        standings.update(m1)

        points_before = {t.name: standings.get_points(t.name) for t in teams}

        # Run cup
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        simulate_cup(bracket, seed=77)

        points_after = {t.name: standings.get_points(t.name) for t in teams}
        assert points_before == points_after