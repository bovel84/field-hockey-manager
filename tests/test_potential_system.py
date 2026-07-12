"""Tests for the potential system (3.2) and youth academy (3.1)."""
import pytest
import random
from src.models import Player, Team, Position
from src.season import (
    train_player, generate_free_agents, generate_youth_prospects,
    promote_youth_player,
)


def make_player(name="Test", rating=50, age=20, potential=80, position=Position.MIDFIELD):
    """Helper: create a player with given attributes."""
    return Player(
        name=name,
        position=position,
        passing=rating,
        shooting=rating,
        defense=rating,
        speed=rating,
        stamina=rating,
        age=age,
        potential=potential,
    )


class TestPotentialField:
    def test_player_has_potential(self):
        """Player should have a potential field with default 99."""
        p = Player(name="Test", position=Position.MIDFIELD)
        assert hasattr(p, "potential")
        assert p.potential == 99

    def test_potential_set_via_constructor(self):
        """Potential should be settable via constructor."""
        p = Player(name="Test", position=Position.MIDFIELD, potential=85)
        assert p.potential == 85

    def test_show_potential_under_23(self):
        """show_potential should return True for players under 23."""
        p = make_player(age=22, potential=90)
        assert p.show_potential() is True

        p = make_player(age=18, potential=85)
        assert p.show_potential() is True

    def test_show_potential_23_and_over(self):
        """show_potential should return False for players 23 or older."""
        p = make_player(age=23, potential=90)
        assert p.show_potential() is False

        p = make_player(age=30, potential=85)
        assert p.show_potential() is False


class TestTrainingWithPotential:
    def test_training_capped_by_potential(self):
        """Training should not raise an attribute above the player's potential."""
        p = make_player(rating=78, age=20, potential=80)
        rng = random.Random(42)
        # Train multiple times — should cap at potential (80)
        for _ in range(20):
            train_player(p, "passing", rng)
        assert p.passing <= 80

    def test_training_capped_by_potential_high(self):
        """Training should allow growth up to 99 if potential is high."""
        p = make_player(rating=95, age=18, potential=99)
        rng = random.Random(42)
        train_player(p, "passing", rng)
        # Should be able to grow since potential is 99
        assert p.passing <= 99

    def test_training_potential_exactly_at_current(self):
        """If potential equals current rating, training should not increase it."""
        p = make_player(rating=70, age=20, potential=70)
        rng = random.Random(42)
        original = p.passing
        for _ in range(10):
            train_player(p, "passing", rng)
        assert p.passing == original  # Cannot exceed potential


class TestFreeAgentsWithPotential:
    def test_free_agents_have_potential(self):
        """Generated free agents should have a potential value."""
        rng = random.Random(42)
        agents = generate_free_agents(5, rng)
        for a in agents:
            assert hasattr(a, "potential")
            assert 55 <= a.potential <= 99

    def test_young_free_agents_have_higher_potential(self):
        """Young free agents (<=22) should have potential higher than their rating."""
        rng = random.Random(42)
        agents = generate_free_agents(20, rng)
        young_agents = [a for a in agents if a.age <= 22]
        assert len(young_agents) > 0
        for a in young_agents:
            assert a.potential > a.overall_rating()

    def test_old_free_agents_potential_close_to_rating(self):
        """Old free agents (>28) should have potential close to their rating."""
        rng = random.Random(42)
        agents = generate_free_agents(30, rng)
        old_agents = [a for a in agents if a.age > 28]
        assert len(old_agents) > 0
        for a in old_agents:
            assert a.potential <= a.overall_rating() + 5


class TestYouthAcademy:
    def test_generate_youth_prospects_count(self):
        """Should generate 1-2 youth prospects."""
        team = Team(name="Test FC", players=[])
        rng = random.Random(42)
        prospects = generate_youth_prospects(team, rng)
        assert 1 <= len(prospects) <= 2

    def test_youth_prospects_age_range(self):
        """Youth prospects should be 16-18 years old."""
        team = Team(name="Test FC", players=[])
        rng = random.Random(42)
        # Generate multiple batches to check
        for _ in range(10):
            prospects = generate_youth_prospects(team, rng)
            for p in prospects:
                assert 16 <= p.age <= 18

    def test_youth_prospects_rating_range(self):
        """Youth prospects should have ratings in the 40-60 range."""
        team = Team(name="Test FC", players=[])
        rng = random.Random(42)
        for _ in range(10):
            prospects = generate_youth_prospects(team, rng)
            for p in prospects:
                assert 37 <= p.passing <= 63  # base 40-60 + ±3 variance
                assert 37 <= p.shooting <= 63
                assert 37 <= p.defense <= 63

    def test_youth_prospects_high_potential(self):
        """Youth prospects should have high potential (70-95)."""
        team = Team(name="Test FC", players=[])
        rng = random.Random(42)
        for _ in range(10):
            prospects = generate_youth_prospects(team, rng)
            for p in prospects:
                assert 70 <= p.potential <= 95

    def test_youth_prospects_deterministic_with_seed(self):
        """Same seed should produce same prospects."""
        team = Team(name="Test FC", players=[])
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        p1 = generate_youth_prospects(team, rng1)
        p2 = generate_youth_prospects(team, rng2)
        assert len(p1) == len(p2)
        for a, b in zip(p1, p2):
            assert a.name == b.name
            assert a.age == b.age
            assert a.potential == b.potential

    def test_prestige_bonus_to_potential(self):
        """Teams with high prestige should produce slightly better youth prospects."""
        low_prestige = Team(name="Low", players=[], prestige=0)
        high_prestige = Team(name="High", players=[], prestige=50)
        rng = random.Random(42)
        # Generate many prospects to see the trend
        low_pots = []
        high_pots = []
        for _ in range(50):
            for p in generate_youth_prospects(low_prestige, rng):
                low_pots.append(p.potential)
            for p in generate_youth_prospects(high_prestige, rng):
                high_pots.append(p.potential)
        avg_low = sum(low_pots) / len(low_pots)
        avg_high = sum(high_pots) / len(high_pots)
        assert avg_high >= avg_low

    def test_promote_youth_player(self):
        """promote_youth_player should move a prospect to the main squad."""
        team = Team(name="Test FC", players=[])
        rng = random.Random(42)
        prospects = generate_youth_prospects(team, rng)
        team.youth_players = prospects
        initial_squad_size = len(team.players)
        initial_youth_size = len(team.youth_players)

        prospect_to_promote = prospects[0]
        result = promote_youth_player(team, prospect_to_promote)

        assert result is True
        assert len(team.players) == initial_squad_size + 1
        assert len(team.youth_players) == initial_youth_size - 1
        assert prospect_to_promote in team.players

    def test_promote_nonexistent_youth_player(self):
        """promote_youth_player should return False if player not in youth_players."""
        team = Team(name="Test FC", players=[])
        random_player = make_player(name="Outsider")
        result = promote_youth_player(team, random_player)
        assert result is False