"""Tests for database persistence of new fields (potential, prestige, youth)."""
import pytest
from src.models import Player, Team, Position
from src.database import Database
from src.season import generate_youth_prospects, promote_youth_player


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
            potential=90 if i < 3 else 80,
        )
        for i, pos in enumerate(positions)
    ]
    return Team(name=name, players=players, prestige=15)


class TestDatabaseNewFields:
    def test_save_load_potential(self, tmp_path):
        """Player potential should be saved and loaded correctly."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        team = make_team("Test FC")
        db.save_team(team)
        loaded = db.load_team("Test FC")
        assert loaded is not None
        for p in loaded.players:
            assert hasattr(p, "potential")
        # Check specific values
        assert loaded.players[0].potential == 90
        assert loaded.players[3].potential == 80

    def test_save_load_prestige(self, tmp_path):
        """Team prestige should be saved and loaded correctly."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        team = make_team("Test FC")
        db.save_team(team)
        loaded = db.load_team("Test FC")
        assert loaded is not None
        assert loaded.prestige == 15

    def test_save_load_youth_players(self, tmp_path):
        """Youth players should be saved and loaded separately."""
        import random
        db = Database(str(tmp_path / "test.db"))
        db.init()
        team = make_team("Test FC")
        rng = random.Random(42)
        prospects = generate_youth_prospects(team, rng)
        team.youth_players = prospects
        db.save_team(team)
        loaded = db.load_team("Test FC")
        assert loaded is not None
        assert len(loaded.youth_players) == len(prospects)
        assert len(loaded.players) == 16  # Main squad unchanged
        for yp in loaded.youth_players:
            assert yp.age <= 18
            assert yp.potential >= 70

    def test_default_prestige_zero(self, tmp_path):
        """Teams without explicit prestige should default to 0."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        team = Team(name="Basic", players=[
            Player(name="P1", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80)
        ])
        db.save_team(team)
        loaded = db.load_team("Basic")
        assert loaded.prestige == 0

    def test_default_potential_99(self, tmp_path):
        """Players without explicit potential should default to 99."""
        db = Database(str(tmp_path / "test.db"))
        db.init()
        team = Team(name="Basic", players=[
            Player(name="P1", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80)
        ])
        db.save_team(team)
        loaded = db.load_team("Basic")
        assert loaded.players[0].potential == 99