"""Tests for playoff system (4.1) and Coppa Nazionale (2.2)."""
import pytest
import random
from src.models import Player, Team, Match, Position
from src.season import (
    Standings, generate_playoff_bracket, simulate_playoff,
    generate_cup_bracket, simulate_cup,
    PlayoffBracket, CupBracket,
)


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


def make_standings_with_4_teams(teams):
    """Helper: create standings with predetermined results."""
    standings = Standings()
    # Team 0 wins all, team 1 second, team 2 third, team 3 fourth
    results = [
        (0, 1, 3, 0),  # team 0 beats team 1
        (0, 2, 2, 1),  # team 0 beats team 2
        (0, 3, 4, 0),  # team 0 beats team 3
        (1, 2, 2, 0),  # team 1 beats team 2
        (1, 3, 1, 0),  # team 1 beats team 3
        (2, 3, 3, 1),  # team 2 beats team 3
    ]
    for home_idx, away_idx, hs, as_ in results:
        m = Match(
            home_team=teams[home_idx],
            away_team=teams[away_idx],
            home_score=hs,
            away_score=as_,
            played=True,
        )
        standings.update(m)
    return standings


class TestPlayoffBracket:
    def test_generate_playoff_bracket_4_teams(self):
        """generate_playoff_bracket should create a bracket with 4 teams."""
        teams = [make_team(f"Team {i}", 70 + i * 5) for i in range(4)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        assert isinstance(bracket, PlayoffBracket)
        assert bracket.semifinal1.home_team is not None
        assert bracket.semifinal1.away_team is not None
        assert bracket.semifinal2.home_team is not None
        assert bracket.semifinal2.away_team is not None

    def test_playoff_seeding_1v4_2v3(self):
        """Semifinals should be 1st vs 4th and 2nd vs 3rd."""
        teams = [make_team(f"Team {i}", 70 + i * 5) for i in range(4)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)

        ranking = standings.get_ranking()
        first = ranking[0]["team_name"]
        fourth = ranking[3]["team_name"]
        second = ranking[1]["team_name"]
        third = ranking[2]["team_name"]

        # SF1: 1st vs 4th
        assert bracket.semifinal1.home_team.name == first
        assert bracket.semifinal1.away_team.name == fourth
        # SF2: 2nd vs 3rd
        assert bracket.semifinal2.home_team.name == second
        assert bracket.semifinal2.away_team.name == third

    def test_playoff_bracket_not_enough_teams(self):
        """generate_playoff_bracket should raise with < 4 teams."""
        teams = [make_team("A"), make_team("B")]
        standings = Standings()
        m = Match(home_team=teams[0], away_team=teams[1], home_score=1, away_score=0, played=True)
        standings.update(m)
        with pytest.raises(ValueError):
            generate_playoff_bracket(teams, standings)

    def test_playoff_final_initially_none(self):
        """Final should be None before simulation."""
        teams = [make_team(f"Team {i}", 75) for i in range(4)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        assert bracket.final is None
        assert bracket.winner is None


class TestSimulatePlayoff:
    def test_simulate_playoff_returns_winner(self):
        """simulate_playoff should return a Team as winner."""
        teams = [make_team(f"Team {i}", 75) for i in range(4)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        winner = simulate_playoff(bracket, seed=42)
        assert isinstance(winner, Team)
        assert winner in teams

    def test_playoff_semifinals_played(self):
        """After simulation, both semifinals should be played."""
        teams = [make_team(f"Team {i}", 75) for i in range(4)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=42)
        assert bracket.semifinal1.played is True
        assert bracket.semifinal2.played is True

    def test_playoff_final_set_after_simulation(self):
        """Final should be set and played after simulation."""
        teams = [make_team(f"Team {i}", 75) for i in range(4)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=42)
        assert bracket.final is not None
        assert bracket.final.played is True

    def test_playoff_winner_is_final_winner(self):
        """The bracket winner should be the winner of the final."""
        teams = [make_team(f"Team {i}", 75) for i in range(4)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=42)
        if bracket.final.home_score >= bracket.final.away_score:
            assert bracket.winner == bracket.final.home_team
        else:
            assert bracket.winner == bracket.final.away_team

    def test_playoff_deterministic_with_seed(self):
        """Same seed should produce same winner."""
        teams1 = [make_team(f"Team {i}", 75) for i in range(4)]
        teams2 = [make_team(f"Team {i}", 75) for i in range(4)]
        standings1 = make_standings_with_4_teams(teams1)
        standings2 = make_standings_with_4_teams(teams2)
        bracket1 = generate_playoff_bracket(teams1, standings1, rng=random.Random(42))
        bracket2 = generate_playoff_bracket(teams2, standings2, rng=random.Random(42))
        w1 = simulate_playoff(bracket1, seed=42)
        w2 = simulate_playoff(bracket2, seed=42)
        assert w1.name == w2.name


class TestCupBracket:
    def test_generate_cup_bracket_6_teams(self):
        """generate_cup_bracket should create a bracket for 6 teams."""
        teams = [make_team(f"Team {i}", 70 + i) for i in range(6)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        assert isinstance(bracket, CupBracket)
        assert len(bracket.rounds) >= 2

    def test_generate_cup_bracket_2_teams(self):
        """generate_cup_bracket should work with minimum 2 teams."""
        teams = [make_team("A"), make_team("B")]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        assert isinstance(bracket, CupBracket)

    def test_generate_cup_bracket_too_few_teams(self):
        """generate_cup_bracket should raise with < 2 teams."""
        with pytest.raises(ValueError):
            generate_cup_bracket([make_team("Solo")])

    def test_simulate_cup_returns_winner(self):
        """simulate_cup should return a Team as winner."""
        teams = [make_team(f"Team {i}", 70 + i) for i in range(6)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        assert isinstance(winner, Team)
        assert winner in teams

    def test_cup_winner_gets_budget_bonus(self):
        """Cup winner should receive +200 budget."""
        teams = [make_team(f"Team {i}", 75) for i in range(6)]
        # Record initial budgets
        initial_budgets = {t.name: t.budget for t in teams}
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        assert winner.budget == initial_budgets[winner.name] + 200

    def test_cup_winner_gets_prestige_bonus(self):
        """Cup winner should receive +10 prestige."""
        teams = [make_team(f"Team {i}", 75) for i in range(6)]
        initial_prestige = {t.name: t.prestige for t in teams}
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        assert winner.prestige == initial_prestige[winner.name] + 10

    def test_cup_deterministic_with_seed(self):
        """Same seed should produce same winner."""
        teams1 = [make_team(f"Team {i}", 75) for i in range(6)]
        teams2 = [make_team(f"Team {i}", 75) for i in range(6)]
        bracket1 = generate_cup_bracket(teams1, rng=random.Random(42))
        bracket2 = generate_cup_bracket(teams2, rng=random.Random(42))
        w1 = simulate_cup(bracket1, seed=42)
        w2 = simulate_cup(bracket2, seed=42)
        assert w1.name == w2.name

    def test_cup_with_4_teams(self):
        """Cup should work with 4 teams (no byes needed)."""
        teams = [make_team(f"Team {i}", 75) for i in range(4)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        assert winner in teams

    def test_cup_with_2_teams(self):
        """Cup should work with 2 teams and return a winner."""
        teams = [make_team("A", 75), make_team("B", 70)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        assert winner is not None
        assert winner in teams

    def test_cup_with_3_teams(self):
        """Cup should work with 3 teams (1 bye in round 1)."""
        teams = [make_team(f"T{i}", 70 + i * 5) for i in range(3)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        assert winner is not None
        assert winner in teams

    def test_cup_with_5_teams(self):
        """Cup should work with 5 teams (3 byes in round 1)."""
        teams = [make_team(f"T{i}", 70 + i * 3) for i in range(5)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        assert winner is not None
        assert winner in teams

    def test_cup_with_7_teams(self):
        """Cup should work with 7 teams (1 bye in round 1)."""
        teams = [make_team(f"T{i}", 70 + i * 2) for i in range(7)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        assert winner is not None
        assert winner in teams

    def test_cup_no_double_award(self):
        """simulate_cup should not award budget/prestige twice."""
        teams = [make_team(f"T{i}", 75) for i in range(4)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        winner = simulate_cup(bracket, seed=42)
        budget_after_first = winner.budget
        prestige_after_first = winner.prestige
        # Call again
        winner2 = simulate_cup(bracket, seed=42)
        assert winner2 is winner
        assert winner.budget == budget_after_first
        assert winner.prestige == prestige_after_first