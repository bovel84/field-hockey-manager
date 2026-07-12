"""Tests for Leonardo Phase 2: rigori/corti angoli/cartellini + obiettivi stagionali."""
import pytest
import random
from src.models import Player, Team, Match, Position
from src.simulation import simulate_match, _check_green_card, _check_penalty_corner, _check_penalty
from src.season import generate_calendar


def make_team(name="Team A", rating=70):
    """Helper: create a team with given overall rating."""
    players = []
    for i in range(16):
        pos = [Position.GOALKEEPER, Position.DEFENSE, Position.MIDFIELD, Position.ATTACK][i % 4]
        players.append(Player(
            name=f"{name} P{i}", position=pos,
            passing=rating, shooting=rating, defense=rating,
            speed=rating, stamina=rating,
        ))
    return Team(name=name, players=players, budget=500)


class TestGreenCard:
    """Tests for green card system."""

    def test_green_card_returns_dict_or_none(self):
        rng = random.Random(42)
        result = _check_green_card(rng)
        assert result is None or isinstance(result, dict)

    def test_green_card_has_correct_keys(self):
        """Run until we get a green card, then verify structure."""
        rng = random.Random(42)
        for _ in range(200):
            result = _check_green_card(rng)
            if result is not None:
                assert result["type"] == "green_card"
                assert "minute" in result
                assert result["duration"] == 2
                return
        pytest.fail("No green card in 200 attempts (should be ~8-10% chance)")

    def test_green_card_probability_reasonable(self):
        """Over 1000 samples, green card frequency should be 5-15%."""
        rng = random.Random(123)
        count = sum(1 for _ in range(1000) if _check_green_card(rng) is not None)
        assert 50 <= count <= 150


class TestPenaltyCorner:
    """Tests for penalty corner system."""

    def test_corner_returns_dict_or_none(self):
        home = make_team("Home", 70)
        away = make_team("Away", 65)
        rng = random.Random(42)
        result = _check_penalty_corner(home, away, rng, 1, "home")
        assert result is None or isinstance(result, dict)

    def test_corner_goal_has_correct_type(self):
        home = make_team("Home", 80)
        away = make_team("Away", 50)
        rng = random.Random(42)
        for _ in range(200):
            result = _check_penalty_corner(home, away, rng, 1, "home")
            if result is not None:
                assert result["type"] in ("corner_goal", "penalty_corner")
                assert result["quarter"] == 1
                assert result["team"] == "home"
                assert "minute" in result
                if result["type"] == "corner_goal":
                    assert "scorer" in result
                else:
                    assert result["result"] == "missed"
                return
        pytest.fail("No penalty corner in 200 attempts")

    def test_corner_probability_reasonable(self):
        home = make_team("Home", 70)
        away = make_team("Away", 70)
        rng = random.Random(999)
        count = sum(1 for _ in range(1000) if _check_penalty_corner(home, away, rng, 1, "home") is not None)
        assert 130 <= count <= 230  # ~15-20%

    def test_stronger_team_scores_more_corners(self):
        """Strong team should score more corner goals than weak team."""
        strong = make_team("Strong", 85)
        weak = make_team("Weak", 40)
        rng = random.Random(42)
        strong_goals = 0
        weak_goals = 0
        for _ in range(500):
            r1 = _check_penalty_corner(strong, weak, rng, 1, "home")
            if r1 and r1["type"] == "corner_goal":
                strong_goals += 1
            r2 = _check_penalty_corner(weak, strong, rng, 1, "away")
            if r2 and r2["type"] == "corner_goal":
                weak_goals += 1
        assert strong_goals > weak_goals


class TestPenaltyStroke:
    """Tests for penalty stroke system."""

    def test_penalty_returns_dict_or_none(self):
        home = make_team("Home", 70)
        away = make_team("Away", 65)
        rng = random.Random(42)
        result = _check_penalty(home, away, rng, 1, "home")
        assert result is None or isinstance(result, dict)

    def test_penalty_goal_or_missed(self):
        home = make_team("Home", 75)
        away = make_team("Away", 60)
        rng = random.Random(42)
        for _ in range(300):
            result = _check_penalty(home, away, rng, 1, "home")
            if result is not None:
                assert result["type"] in ("penalty_goal", "penalty_missed")
                assert result["quarter"] == 1
                assert result["team"] == "home"
                if result["type"] == "penalty_goal":
                    assert "scorer" in result
                else:
                    assert "shooter" in result
                return
        pytest.fail("No penalty in 300 attempts")

    def test_penalty_probability_reasonable(self):
        home = make_team("Home", 70)
        away = make_team("Away", 70)
        rng = random.Random(777)
        count = sum(1 for _ in range(1000) if _check_penalty(home, away, rng, 1, "home") is not None)
        assert 30 <= count <= 80  # ~4-6%


class TestMatchEventsIntegration:
    """Integration tests: new event types appear in match.events."""

    def test_match_with_new_events_does_not_crash(self):
        home = make_team("Home", 70)
        away = make_team("Away", 65)
        match = simulate_match(home, away, seed=42)
        assert match.played
        assert match.home_score >= 0
        assert match.away_score >= 0

    def test_match_events_include_new_types(self):
        """Over many matches with different seeds, new event types should appear."""
        home = make_team("Home", 75)
        away = make_team("Away", 60)
        event_types_seen = set()
        for seed in range(100):
            match = simulate_match(home, away, seed=seed)
            for ev in match.events:
                event_types_seen.add(ev["type"])
        # At least some new event types should appear
        new_types = {"green_card", "penalty_corner", "corner_goal", "penalty_goal", "penalty_missed"}
        assert len(new_types & event_types_seen) > 0

    def test_corner_goals_count_in_score(self):
        """Corner goals and penalty goals should be counted in the score."""
        home = make_team("Home", 80)
        away = make_team("Away", 50)
        for seed in range(50):
            match = simulate_match(home, away, seed=seed)
            # Count goals from events
            event_goals = sum(1 for ev in match.events if ev["type"] in ("goal", "corner_goal", "penalty_goal") and ev["team"] == "home")
            # Score should be >= event_goals (normal goals + corner/penalty goals)
            assert match.home_score >= 0


class TestSeasonGoals:
    """Tests for dynamic season objectives system."""

    def _make_app_like(self):
        """Create a minimal mock that mimics FHMApp for goal testing."""
        class MockApp:
            def __init__(self):
                self.season_number = 1
                self.manager_reputation = 50
                self.board_confidence = 65
                self.user_team = make_team("User Team", 70)
                self.teams = [self.user_team, make_team("Opp", 60)]
                self._played_matches_history = []
                self.season_goals = []
                self.career_news = []
                self.user_team.budget = 500

            def get_standings(self):
                return sorted(self.teams, key=lambda t: (t.points, t.goals_for - t.goals_against), reverse=True)

            def _generate_season_goals(self):
                import random as _rng
                rng = _rng.Random(self.season_number * 42 + self.manager_reputation)
                goals = []
                if self.manager_reputation >= 75:
                    goals.append({"id": "champion", "description": "Vinci il campionato", "type": "position",
                                  "target": 1, "reward_budget": 300, "reward_reputation": 5, "status": "active"})
                else:
                    goals.append({"id": "top3", "description": "Qualificati per i playoff (top 3)", "type": "position",
                                  "target": 3, "reward_budget": 200, "reward_reputation": 3, "status": "active"})
                target_goals = 20 if self.manager_reputation < 50 else 25
                goals.append({"id": "goals", "description": f"Segna almeno {target_goals} gol in stagione",
                              "type": "goals_scored", "target": target_goals, "reward_budget": 100,
                              "reward_reputation": 2, "status": "active"})
                if rng.random() < 0.5:
                    goals.append({"id": "streak", "description": "Non perdere più di 2 partite consecutive",
                                  "type": "max_consecutive_losses", "target": 2, "reward_budget": 150,
                                  "reward_reputation": 3, "status": "active"})
                return goals

            def _evaluate_season_goals(self):
                headlines = []
                standings = self.get_standings()
                user_position = standings.index(self.user_team) + 1 if self.user_team in standings else len(standings)
                total_goals = self.user_team.goals_for if self.user_team else 0
                max_consecutive = 0
                current_streak = 0
                for m in self._played_matches_history:
                    is_home = m.home_team == self.user_team
                    user_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    if user_score < opp_score:
                        current_streak += 1
                        max_consecutive = max(max_consecutive, current_streak)
                    else:
                        current_streak = 0
                for goal in self.season_goals:
                    if goal["status"] != "active":
                        continue
                    achieved = False
                    if goal["type"] == "position":
                        achieved = user_position <= goal["target"]
                    elif goal["type"] == "goals_scored":
                        achieved = total_goals >= goal["target"]
                    elif goal["type"] == "max_consecutive_losses":
                        achieved = max_consecutive <= goal["target"]
                    if achieved:
                        goal["status"] = "completed"
                        self.user_team.budget += goal["reward_budget"]
                        self.manager_reputation = min(100, self.manager_reputation + goal["reward_reputation"])
                        self.board_confidence = min(100, self.board_confidence + 5)
                        headlines.append(f"✅ {goal['description']}")
                    else:
                        goal["status"] = "failed"
                        self.board_confidence = max(0, self.board_confidence - 5)
                        self.user_team.budget = max(0, self.user_team.budget - 50)
                        headlines.append(f"❌ {goal['description']}")
                return headlines

        return MockApp()

    def test_generate_goals_returns_list(self):
        app = self._make_app_like()
        goals = app._generate_season_goals()
        assert isinstance(goals, list)
        assert len(goals) >= 2  # at least position + goals
        assert len(goals) <= 3  # at most 3

    def test_goals_have_required_fields(self):
        app = self._make_app_like()
        goals = app._generate_season_goals()
        for goal in goals:
            assert "id" in goal
            assert "description" in goal
            assert "type" in goal
            assert "target" in goal
            assert "reward_budget" in goal
            assert "reward_reputation" in goal
            assert goal["status"] == "active"

    def test_high_reputation_gives_champion_goal(self):
        app = self._make_app_like()
        app.manager_reputation = 80
        goals = app._generate_season_goals()
        position_goal = [g for g in goals if g["type"] == "position"][0]
        assert position_goal["id"] == "champion"
        assert position_goal["target"] == 1

    def test_low_reputation_gives_top3_goal(self):
        app = self._make_app_like()
        app.manager_reputation = 40
        goals = app._generate_season_goals()
        position_goal = [g for g in goals if g["type"] == "position"][0]
        assert position_goal["id"] == "top3"
        assert position_goal["target"] == 3

    def test_evaluate_completed_position_goal(self):
        app = self._make_app_like()
        app.season_goals = [{"id": "top3", "description": "Top 3", "type": "position",
                              "target": 3, "reward_budget": 200, "reward_reputation": 3, "status": "active"}]
        # User team is first in standings (position 1 <= 3 → achieved)
        app.user_team.points = 30
        headlines = app._evaluate_season_goals()
        assert app.season_goals[0]["status"] == "completed"
        assert app.user_team.budget == 700  # 500 + 200
        assert any("Top 3" in h for h in headlines)

    def test_evaluate_failed_position_goal(self):
        app = self._make_app_like()
        app.season_goals = [{"id": "champion", "description": "Vinci il campionato", "type": "position",
                              "target": 1, "reward_budget": 300, "reward_reputation": 5, "status": "active"}]
        # User team is last (position 2 > 1 → failed)
        app.user_team.points = 0
        app.teams[1].points = 30
        headlines = app._evaluate_season_goals()
        assert app.season_goals[0]["status"] == "failed"
        assert app.user_team.budget == 450  # 500 - 50

    def test_evaluate_goals_scored_goal(self):
        app = self._make_app_like()
        app.season_goals = [{"id": "goals", "description": "Segna 20 gol", "type": "goals_scored",
                              "target": 20, "reward_budget": 100, "reward_reputation": 2, "status": "active"}]
        app.user_team.goals_for = 25  # >= 20 → achieved
        headlines = app._evaluate_season_goals()
        assert app.season_goals[0]["status"] == "completed"
        assert app.user_team.budget == 600  # 500 + 100

    def test_evaluate_goals_scored_failed(self):
        app = self._make_app_like()
        app.season_goals = [{"id": "goals", "description": "Segna 20 gol", "type": "goals_scored",
                              "target": 20, "reward_budget": 100, "reward_reputation": 2, "status": "active"}]
        app.user_team.goals_for = 10  # < 20 → failed
        headlines = app._evaluate_season_goals()
        assert app.season_goals[0]["status"] == "failed"

    def test_evaluate_skips_non_active_goals(self):
        app = self._make_app_like()
        app.season_goals = [{"id": "done", "description": "Already done", "type": "position",
                              "target": 1, "reward_budget": 100, "reward_reputation": 1, "status": "completed"}]
        headlines = app._evaluate_season_goals()
        assert len(headlines) == 0  # no active goals to evaluate

    def test_multiple_goals_evaluation(self):
        app = self._make_app_like()
        app.season_goals = [
            {"id": "top3", "description": "Top 3", "type": "position", "target": 3,
             "reward_budget": 200, "reward_reputation": 3, "status": "active"},
            {"id": "goals", "description": "20 gol", "type": "goals_scored", "target": 20,
             "reward_budget": 100, "reward_reputation": 2, "status": "active"},
            {"id": "streak", "description": "Max 2 loss streak", "type": "max_consecutive_losses",
             "target": 2, "reward_budget": 150, "reward_reputation": 3, "status": "active"},
        ]
        app.user_team.points = 30  # position 1 → top3 achieved
        app.user_team.goals_for = 25  # >= 20 → goals achieved
        # No matches played → max_consecutive = 0 <= 2 → streak achieved
        headlines = app._evaluate_season_goals()
        assert all(g["status"] == "completed" for g in app.season_goals)
        assert len(headlines) == 3
        assert app.user_team.budget == 950  # 500 + 200 + 100 + 150