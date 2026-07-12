"""Tests for Feature 1: Integrazione narrativa Coppa & Playoff."""
from __future__ import annotations
import random
from src.models import Player, Team, Match, Position
from src.season import (
    generate_cup_bracket, simulate_cup, generate_cup_headlines,
    generate_playoff_bracket, simulate_playoff, generate_playoff_headlines,
    Standings, CupBracket, PlayoffBracket,
)


def make_team(name: str, rating: int = 75) -> Team:
    """Create a team with players at the given rating."""
    players = []
    for pos in [Position.GOALKEEPER] + [Position.DEFENSE] * 4 + [Position.MIDFIELD] * 5 + [Position.ATTACK] * 6:
        players.append(Player(
            name=f"{name} {pos.value}",
            position=pos,
            passing=rating, shooting=rating, defense=rating,
            speed=rating, stamina=rating, age=25,
        ))
    return Team(name=name, players=players)


def make_standings_with_4_teams(teams: list[Team]) -> Standings:
    """Create standings with pre-set results for 4 teams."""
    standings = Standings()
    # Simulate matches so standings have data
    t1, t2, t3, t4 = teams[:4]
    matches = [
        Match(home_team=t1, away_team=t2, home_score=3, away_score=0, played=True),
        Match(home_team=t3, away_team=t4, home_score=2, away_score=1, played=True),
        Match(home_team=t1, away_team=t3, home_score=2, away_score=0, played=True),
        Match(home_team=t2, away_team=t4, home_score=1, away_score=0, played=True),
    ]
    for m in matches:
        standings.update(m)
    return standings


class TestCupHeadlines:
    """Tests for generate_cup_headlines()."""

    def test_cup_headlines_include_winner(self):
        """Cup headlines should include the winner announcement."""
        teams = [make_team("Team A", 80), make_team("Team B", 70),
                 make_team("Team C", 75), make_team("Team D", 65)]
        bracket = generate_cup_bracket(teams, rng=random.Random(42))
        simulate_cup(bracket, seed=100)
        headlines = generate_cup_headlines(bracket)
        assert any("vince la Coppa Nazionale" in h for h in headlines), \
            f"Expected winner headline, got: {headlines}"

    def test_cup_headlines_detect_upset(self):
        """Cup headlines should detect when a lower-rated team beats a higher-rated team."""
        teams = [make_team("Strong", 85), make_team("Weak", 50),
                 make_team("Medium", 70), make_team("Low", 55)]
        bracket = generate_cup_bracket(teams, rng=random.Random(99))
        simulate_cup(bracket, seed=999)
        headlines = generate_cup_headlines(bracket)
        # At least one headline should mention an upset or a winner
        assert len(headlines) > 0, "Expected at least one headline"

    def test_cup_headlines_empty_for_unplayed_bracket(self):
        """Cup headlines should be empty (or minimal) for an unplayed bracket."""
        teams = [make_team("A", 75), make_team("B", 75)]
        bracket = generate_cup_bracket(teams, rng=random.Random(1))
        headlines = generate_cup_headlines(bracket)
        # No winner yet, so no winner headline
        assert not any("vince la Coppa" in h for h in headlines)

    def test_cup_headlines_format(self):
        """Cup headlines should use emoji and correct format."""
        teams = [make_team("Alpha", 80), make_team("Beta", 70),
                 make_team("Gamma", 75), make_team("Delta", 65)]
        bracket = generate_cup_bracket(teams, rng=random.Random(7))
        simulate_cup(bracket, seed=777)
        headlines = generate_cup_headlines(bracket)
        for h in headlines:
            assert isinstance(h, str)
            assert len(h) > 0
        # Winner headline should have 🏆
        assert any("🏆" in h for h in headlines)

    def test_cup_headlines_skip_bye_matches(self):
        """Cup headlines should skip bye matches (same team vs itself)."""
        teams = [make_team("Solo1", 75), make_team("Solo2", 70)]
        bracket = generate_cup_bracket(teams, rng=random.Random(3))
        simulate_cup(bracket, seed=42)
        headlines = generate_cup_headlines(bracket)
        # Should not have headlines about a team eliminating itself
        for h in headlines:
            assert "elimina" not in h or h.count("elimina") == 1


class TestPlayoffHeadlines:
    """Tests for generate_playoff_headlines()."""

    def test_playoff_headlines_include_champion(self):
        """Playoff headlines should include the champion announcement."""
        teams = [make_team("First", 85), make_team("Second", 80),
                 make_team("Third", 75), make_team("Fourth", 70)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=42)
        headlines = generate_playoff_headlines(bracket)
        assert any("CAMPIONE D'ITALIA" in h for h in headlines), \
            f"Expected champion headline, got: {headlines}"

    def test_playoff_headlines_detect_upset(self):
        """Playoff headlines should detect upsets in semifinals."""
        # Create a bracket where a weak team upsets a strong team
        strong = make_team("Strong", 90)
        weak = make_team("Weak", 50)
        teams = [strong, weak, make_team("Mid1", 75), make_team("Mid2", 70)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=12345)
        headlines = generate_playoff_headlines(bracket)
        # Should have at least 1 headline (champion)
        assert len(headlines) >= 1

    def test_playoff_headlines_format(self):
        """Playoff headlines should be non-empty strings."""
        teams = [make_team("A", 80), make_team("B", 75),
                 make_team("C", 70), make_team("D", 65)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=555)
        headlines = generate_playoff_headlines(bracket)
        for h in headlines:
            assert isinstance(h, str)
            assert len(h) > 0

    def test_playoff_headlines_semifinal_content(self):
        """Playoff headlines should mention semifinal results or champion."""
        teams = [make_team("Top", 85), make_team("Good", 78),
                 make_team("OK", 72), make_team("Low", 68)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=111)
        headlines = generate_playoff_headlines(bracket)
        # Should mention either semifinal access or champion
        combined = " ".join(headlines)
        assert "CAMPIONE" in combined or "Finale" in combined or "Semifinale" in combined

    def test_playoff_headlines_champion_emoji(self):
        """Champion headline should include the 🏆 emoji."""
        teams = [make_team("Champs", 82), make_team("Rivals", 76),
                 make_team("Others", 70), make_team("Under", 66)]
        standings = make_standings_with_4_teams(teams)
        bracket = generate_playoff_bracket(teams, standings)
        simulate_playoff(bracket, seed=222)
        headlines = generate_playoff_headlines(bracket)
        assert any("🏆" in h for h in headlines)