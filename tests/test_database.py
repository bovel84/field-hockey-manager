"""Tests for database: init, CRUD operations."""
import pytest
import os
import tempfile
from src.database import Database
from src.models import Player, Team, Match, Position


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    database.init()
    yield database
    os.unlink(path)


class TestDatabaseInit:
    def test_init_creates_tables(self, db):
        # Tables should exist
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "teams" in tables
        assert "players" in tables
        assert "matches" in tables
        assert "standings" in tables
        assert "game_state" in tables


class TestTeamCRUD:
    def test_save_and_load_team(self, db):
        players = [
            Player(name="P1", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80),
            Player(name="P2", position=Position.DEFENSE, passing=65, shooting=40, defense=85, speed=70, stamina=80),
        ]
        team = Team(name="HC Cagliari", players=players, points=3, goals_for=5, goals_against=2, wins=1, draws=0, losses=0)
        db.save_team(team)
        loaded = db.load_team("HC Cagliari")
        assert loaded is not None
        assert loaded.name == "HC Cagliari"
        assert len(loaded.players) == 2
        assert loaded.players[0].name == "P1"
        assert loaded.players[0].position == Position.GOALKEEPER
        assert loaded.points == 3
        assert loaded.goals_for == 5
        assert loaded.goals_against == 2

    def test_load_nonexistent_team(self, db):
        loaded = db.load_team("Nonexistent")
        assert loaded is None

    def test_save_multiple_teams(self, db):
        t1 = Team(name="HC Cagliari", players=[
            Player(name="P1", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80)
        ])
        t2 = Team(name="HC Roma", players=[
            Player(name="P2", position=Position.ATTACK, passing=70, shooting=85, defense=40, speed=80, stamina=75)
        ])
        db.save_team(t1)
        db.save_team(t2)
        all_teams = db.load_all_teams()
        assert len(all_teams) == 2
        names = {t.name for t in all_teams}
        assert "HC Cagliari" in names
        assert "HC Roma" in names

    def test_update_team(self, db):
        team = Team(name="HC Cagliari", players=[
            Player(name="P1", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80)
        ])
        db.save_team(team)
        team.points = 6
        team.wins = 2
        db.save_team(team)
        loaded = db.load_team("HC Cagliari")
        assert loaded.points == 6
        assert loaded.wins == 2

    def test_save_load_extended_fields(self, db):
        """Test that extended fields (age, morale, injured, budget, formation, intensity) are saved and loaded."""
        players = [
            Player(name="P1", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80,
                   speed=50, stamina=80, age=22, morale=85, injured=True, injury_duration=3),
        ]
        team = Team(name="HC Test", players=players, budget=300, formation="5-3-2", intensity="Difensiva")
        db.save_team(team)
        loaded = db.load_team("HC Test")
        assert loaded is not None
        assert loaded.budget == 300
        assert loaded.formation == "5-3-2"
        assert loaded.intensity == "Difensiva"
        assert loaded.players[0].age == 22
        assert loaded.players[0].morale == 85
        assert loaded.players[0].injured is True
        assert loaded.players[0].injury_duration == 3


class TestMatchCRUD:
    def test_save_and_load_match(self, db):
        home = Team(name="HC Cagliari", players=[])
        away = Team(name="HC Roma", players=[])
        match = Match(home_team=home, away_team=away, home_score=3, away_score=1, played=True,
                      events=[{"type": "goal", "quarter": 1, "minute": 10, "team": "home", "scorer": "P1"}])
        db.save_match(match, round_num=1)
        matches = db.load_matches()
        assert len(matches) == 1
        assert matches[0]["home_team"] == "HC Cagliari"
        assert matches[0]["away_team"] == "HC Roma"
        assert matches[0]["home_score"] == 3
        assert matches[0]["away_score"] == 1
        assert matches[0]["round"] == 1

    def test_load_matches_by_round(self, db):
        home = Team(name="HC Cagliari", players=[])
        away = Team(name="HC Roma", players=[])
        m1 = Match(home_team=home, away_team=away, home_score=1, away_score=0, played=True)
        m2 = Match(home_team=away, away_team=home, home_score=2, away_score=2, played=True)
        db.save_match(m1, round_num=1)
        db.save_match(m2, round_num=2)
        r1 = db.load_matches(round_num=1)
        r2 = db.load_matches(round_num=2)
        assert len(r1) == 1
        assert len(r2) == 1


class TestStandingsCRUD:
    def test_save_and_load_standings(self, db):
        db.save_standings_entry("HC Cagliari", points=9, wins=3, draws=0, losses=0, goals_for=10, goals_against=2)
        standings = db.load_standings()
        assert len(standings) == 1
        assert standings[0]["team_name"] == "HC Cagliari"
        assert standings[0]["points"] == 9

    def test_update_standings(self, db):
        db.save_standings_entry("HC Cagliari", points=3, wins=1, draws=0, losses=0, goals_for=2, goals_against=1)
        db.save_standings_entry("HC Cagliari", points=6, wins=2, draws=0, losses=0, goals_for=4, goals_against=2)
        standings = db.load_standings()
        assert len(standings) == 1
        assert standings[0]["points"] == 6


class TestGameStateCRUD:
    def test_save_and_load_state(self, db):
        state = {"next_round_idx": 5, "trainings_done": 2, "standings_history": [{"round": 1, "position": 2}]}
        db.save_state(state)
        loaded = db.load_state()
        assert loaded is not None
        assert loaded["next_round_idx"] == 5
        assert loaded["trainings_done"] == 2
        assert loaded["standings_history"] == [{"round": 1, "position": 2}]

    def test_load_empty_state(self, db):
        loaded = db.load_state()
        assert loaded is None

    def test_clear_state(self, db):
        db.save_state({"test": True})
        db.clear_state()
        loaded = db.load_state()
        assert loaded is None