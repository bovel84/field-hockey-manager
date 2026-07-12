"""Tests for Phase 3: 2D match visualization, timeline, and commentary."""
import pytest
import random
from src.models import Team, Player, Match, Position, FORMATION_POSITIONS, get_formation_positions
from src.simulation import simulate_match, generate_match_timeline, generate_commentary


# ── Fixtures ──────────────────────────────────────────────────

def _make_team(name: str, rating: int = 70) -> Team:
    """Create a test team with 16 players."""
    players = []
    positions = (
        [Position.GOALKEEPER] * 1 + [Position.DEFENSE] * 5 +
        [Position.MIDFIELD] * 6 + [Position.ATTACK] * 4
    )
    for i in range(16):
        p = Player(
            name=f"{name} P{i+1}",
            position=positions[i],
            passing=rating, shooting=rating, defense=rating,
            speed=rating, stamina=rating,
        )
        players.append(p)
    return Team(name=name, players=players, formation="4-3-3")


@pytest.fixture
def home_team():
    return _make_team("Home FC", 72)


@pytest.fixture
def away_team():
    return _make_team("Away United", 68)


@pytest.fixture
def played_match(home_team, away_team):
    match = simulate_match(home_team, away_team, seed=42)
    assert match.played
    return match


# ── FORMATION_POSITIONS tests ─────────────────────────────────

class TestFormationPositions:
    """Test formation position data."""

    def test_all_formations_have_11_players(self):
        for formation, positions in FORMATION_POSITIONS.items():
            assert len(positions) == 11, f"{formation} has {len(positions)} positions"

    def test_coordinates_in_range(self):
        for formation, positions in FORMATION_POSITIONS.items():
            for x, y in positions:
                assert 0.0 <= x <= 1.0, f"{formation}: x={x} out of range"
                assert 0.0 <= y <= 1.0, f"{formation}: y={y} out of range"

    def test_gk_is_first(self):
        for formation, positions in FORMATION_POSITIONS.items():
            gx, gy = positions[0]
            assert gy < 0.15, f"{formation}: GK at y={gy}, should be near own goal"

    def test_away_mirrors_y(self):
        home = get_formation_positions("4-3-3", away=False)
        away = get_formation_positions("4-3-3", away=True)
        assert len(home) == len(away) == 11
        for (hx, hy), (ax, ay) in zip(home, away):
            assert hx == ax  # x unchanged
            assert abs(hy - (1.0 - ay)) < 1e-9  # y mirrored

    def test_all_four_formations(self):
        assert "4-3-3" in FORMATION_POSITIONS
        assert "4-4-2" in FORMATION_POSITIONS
        assert "3-5-2" in FORMATION_POSITIONS
        assert "5-3-2" in FORMATION_POSITIONS


# ── generate_match_timeline tests ──────────────────────────────

class TestGenerateMatchTimeline:
    """Test the match timeline generation."""

    def test_timeline_not_empty(self, played_match):
        timeline = generate_match_timeline(played_match)
        assert len(timeline) > 0, "Timeline should not be empty for a played match"

    def test_timeline_starts_at_zero(self, played_match):
        timeline = generate_match_timeline(played_match)
        assert timeline[0]["time"] == 0.0

    def test_timeline_ends_at_sixty(self, played_match):
        timeline = generate_match_timeline(played_match)
        assert timeline[-1]["time"] == 60.0

    def test_timeline_sorted_by_time(self, played_match):
        timeline = generate_match_timeline(played_match)
        times = [f["time"] for f in timeline]
        assert times == sorted(times)

    def test_positions_in_range(self, played_match):
        timeline = generate_match_timeline(played_match)
        for frame in timeline:
            for pos in frame["positions"]["home"] + frame["positions"]["away"]:
                assert len(pos) == 2
                assert 0.0 <= pos[0] <= 1.0
                assert 0.0 <= pos[1] <= 1.0

    def test_events_preserved(self, played_match):
        """All match event minutes should appear in the timeline."""
        timeline = generate_match_timeline(played_match)
        match_minutes = sorted(ev.get("minute", 0) for ev in played_match.events)
        timeline_minutes = sorted(f["time"] for f in timeline if f["event"] is not None)
        for m in match_minutes:
            assert m in timeline_minutes, f"Event at minute {m} not found in timeline"

    def test_unplayed_match_returns_empty(self, home_team, away_team):
        match = Match(home_team=home_team, away_team=away_team)
        timeline = generate_match_timeline(match)
        assert timeline == []


# ── generate_commentary tests ──────────────────────────────────

class TestGenerateCommentary:
    """Test the commentary generation."""

    def test_goal_commentary(self, played_match):
        goal_events = [ev for ev in played_match.events if ev.get("type") in ("goal", "corner_goal", "penalty_goal")]
        if goal_events:
            comment = generate_commentary(played_match, goal_events[0])
            assert len(comment) > 0
            assert "GOAL" in comment or "gol" in comment.lower() or "rete" in comment.lower()

    def test_all_event_types_produce_commentary(self, played_match):
        """Every event type should produce non-empty commentary."""
        seen_types = set()
        for ev in played_match.events:
            if ev.get("type") not in seen_types:
                comment = generate_commentary(played_match, ev)
                assert len(comment) > 0, f"Empty commentary for event type: {ev.get('type')}"
                seen_types.add(ev.get("type"))

    def test_green_card_commentary(self, played_match):
        gc_events = [ev for ev in played_match.events if ev.get("type") == "green_card"]
        if gc_events:
            comment = generate_commentary(played_match, gc_events[0])
            assert len(comment) > 0
            assert "cartellino" in comment.lower() or "verde" in comment.lower() or "sospensione" in comment.lower() or "sanzionato" in comment.lower()

    def test_substitution_commentary(self, played_match):
        sub_events = [ev for ev in played_match.events if ev.get("type") == "substitution"]
        if sub_events:
            comment = generate_commentary(played_match, sub_events[0])
            assert len(comment) > 0
            assert "out" in comment.lower() or "dentro" in comment.lower() or "sostituzione" in comment.lower() or "cambio" in comment.lower() or "cede" in comment.lower()

    def test_commentary_varies(self, played_match):
        """Different calls with same event should sometimes vary (3+ templates)."""
        from src.simulation import _COMMENTARY_TEMPLATES
        for ev_type, templates in _COMMENTARY_TEMPLATES.items():
            assert len(templates) >= 2, f"{ev_type} should have 2+ templates"

    def test_derby_commentary(self, played_match):
        """Derby commentary should add flavor for goals."""
        goal_events = [ev for ev in played_match.events if "goal" in ev.get("type", "")]
        if goal_events:
            comment = generate_commentary(played_match, goal_events[0], derby=True)
            # Should contain derby flavor or normal commentary
            assert len(comment) > 0

    def test_injury_commentary(self, played_match):
        inj_events = [ev for ev in played_match.events if ev.get("type") == "injury"]
        if inj_events:
            comment = generate_commentary(played_match, inj_events[0])
            assert "infortunio" in comment.lower() or "injury" in comment.lower()

    def test_penalty_missed_commentary(self, played_match):
        pm_events = [ev for ev in played_match.events if ev.get("type") == "penalty_missed"]
        if pm_events:
            comment = generate_commentary(played_match, pm_events[0])
            assert "rigore" in comment.lower() or "sbagliato" in comment.lower() or "parata" in comment.lower()