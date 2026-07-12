"""Tests for multi-slot save/load feature."""
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


class TestSaveSlots:
    """Tests for save_slots table and CRUD operations."""

    def test_save_slots_table_exists(self, db):
        """save_slots table should be created on init."""
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "save_slots" in tables

    def test_save_game_creates_slot(self, db):
        """Saving to slot 1 should create a row."""
        state = {"season_number": 1, "user_team_name": "Team A", "league_name": "Serie A"}
        result = db.save_game(1, state)
        assert result is True

    def test_load_game_returns_state(self, db):
        """Loading a saved slot should return the state dict."""
        state = {"season_number": 3, "user_team_name": "Team B", "league_name": "Hoofdklasse"}
        db.save_game(2, state)
        loaded = db.load_game(2)
        assert loaded is not None
        assert loaded["season_number"] == 3
        assert loaded["user_team_name"] == "Team B"

    def test_load_empty_slot_returns_none(self, db):
        """Loading an empty slot should return None."""
        result = db.load_game(1)
        assert result is None

    def test_load_invalid_slot_returns_none(self, db):
        """Loading slot 0 or 5 should return None."""
        assert db.load_game(0) is None
        assert db.load_game(5) is None

    def test_save_invalid_slot_returns_false(self, db):
        """Saving to slot 0 or 4 should return False."""
        assert db.save_game(0, {}) is False
        assert db.save_game(4, {}) is False

    def test_save_overwrites_slot(self, db):
        """Saving to an occupied slot should overwrite."""
        db.save_game(1, {"user_team_name": "Team A"})
        db.save_game(1, {"user_team_name": "Team B"})
        loaded = db.load_game(1)
        assert loaded["user_team_name"] == "Team B"

    def test_list_saves_empty(self, db):
        """list_saves on empty database returns []."""
        assert db.list_saves() == []

    def test_list_saves_returns_metadata(self, db):
        """list_saves should return slot, team_name, season, timestamp."""
        db.save_game(1, {"user_team_name": "Team A", "league_name": "Serie A", "season_number": 2})
        db.save_game(3, {"user_team_name": "Team C", "league_name": "EHL", "season_number": 5})
        saves = db.list_saves()
        assert len(saves) == 2
        assert saves[0]["slot"] == 1
        assert saves[0]["team_name"] == "Team A"
        assert saves[0]["season"] == 2
        assert saves[1]["slot"] == 3
        assert saves[1]["team_name"] == "Team C"
        assert saves[1]["season"] == 5

    def test_delete_save(self, db):
        """Deleting a save slot should remove it."""
        db.save_game(1, {"user_team_name": "Team A"})
        assert db.delete_save(1) is True
        assert db.load_game(1) is None

    def test_delete_empty_slot_returns_false(self, db):
        """Deleting an empty slot should return False."""
        assert db.delete_save(2) is False

    def test_delete_invalid_slot_returns_false(self, db):
        """Deleting slot 0 or 5 should return False."""
        assert db.delete_save(0) is False
        assert db.delete_save(5) is False

    def test_save_preserves_timestamp(self, db):
        """Saving with explicit timestamp should preserve it."""
        state = {"user_team_name": "Team X", "timestamp": "2026-01-15T10:30:00"}
        db.save_game(1, state)
        loaded = db.load_game(1)
        assert loaded["timestamp"] == "2026-01-15T10:30:00"

    def test_save_generates_timestamp_if_missing(self, db):
        """Saving without timestamp should auto-generate one."""
        db.save_game(1, {"user_team_name": "Team Y"})
        loaded = db.load_game(1)
        assert "timestamp" in loaded
        assert len(loaded["timestamp"]) > 0

    def test_three_slots_independent(self, db):
        """All 3 slots should be independently usable."""
        for slot in (1, 2, 3):
            db.save_game(slot, {"user_team_name": f"Team {slot}", "season_number": slot})
        saves = db.list_saves()
        assert len(saves) == 3
        for save in saves:
            assert save["team_name"] == f"Team {save['slot']}"
            assert save["season"] == save["slot"]

    def test_list_saves_ordered_by_slot(self, db):
        """list_saves should return slots in ascending order."""
        db.save_game(3, {"user_team_name": "C"})
        db.save_game(1, {"user_team_name": "A"})
        db.save_game(2, {"user_team_name": "B"})
        saves = db.list_saves()
        assert [s["slot"] for s in saves] == [1, 2, 3]