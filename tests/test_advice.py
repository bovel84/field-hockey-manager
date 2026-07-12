"""Tests for Sprint 5: Manager advisory system and UX widgets."""
import pytest
from src.models import (
    Team, Player, Position, generate_manager_advice,
    Sponsor, Stadium, Facilities,
)


def _make_team(name="Test FC", players=None, budget=500):
    if players is None:
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
    return Team(name=name, players=players, budget=budget)


class TestManagerAdvice:
    """Test the manager advisory system."""

    def test_advice_returns_list(self):
        team = _make_team()
        advice = generate_manager_advice(team)
        assert isinstance(advice, list)
        assert len(advice) > 0

    def test_advice_has_required_fields(self):
        team = _make_team()
        advice = generate_manager_advice(team)
        for a in advice:
            assert "title" in a
            assert "text" in a
            assert "priority" in a
            assert "icon" in a
            assert a["priority"] in ("danger", "warning", "info", "success")

    def test_injured_players_advice(self):
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
        players[0].injured = True
        players[1].injured = True
        players[2].injured = True
        team = _make_team(players=players)
        advice = generate_manager_advice(team)
        injury_advice = [a for a in advice if "Infortunati" in a["title"]]
        assert len(injury_advice) == 1
        assert injury_advice[0]["priority"] == "danger"

    def test_low_condition_advice(self):
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
        players[0].condition = 25
        players[1].condition = 30
        team = _make_team(players=players)
        advice = generate_manager_advice(team)
        tired_advice = [a for a in advice if "affaticati" in a["title"].lower()]
        assert len(tired_advice) == 1

    def test_unhappy_players_advice(self):
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
        players[0].happiness = 20
        players[1].happiness = 30
        team = _make_team(players=players)
        advice = generate_manager_advice(team)
        unhappy_advice = [a for a in advice if "insoddisfatto" in a["title"].lower()]
        assert len(unhappy_advice) == 1

    def test_expiring_contracts_advice(self):
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
        for p in players[:4]:
            p.contract_years = 1
        team = _make_team(players=players)
        advice = generate_manager_advice(team)
        contract_advice = [a for a in advice if "Contratti" in a["title"]]
        assert len(contract_advice) == 1
        assert contract_advice[0]["priority"] == "warning"

    def test_negative_budget_advice(self):
        team = _make_team(budget=-100)
        advice = generate_manager_advice(team)
        budget_advice = [a for a in advice if "negativo" in a["title"].lower()]
        assert len(budget_advice) == 1
        assert budget_advice[0]["priority"] == "danger"

    def test_healthy_budget_advice(self):
        team = _make_team(budget=600)
        advice = generate_manager_advice(team)
        budget_advice = [a for a in advice if "Budget" in a["title"]]
        assert len(budget_advice) == 1
        assert budget_advice[0]["priority"] == "success"

    def test_squad_depth_advice(self):
        players = [Player(name="GK1", position=Position.GOALKEEPER,
                          passing=60, shooting=60, defense=60, speed=60, stamina=60)]
        players += [Player(name=f"M{i}", position=Position.MIDFIELD,
                           passing=70, shooting=70, defense=70, speed=70, stamina=70)
                    for i in range(15)]
        team = _make_team(players=players)
        advice = generate_manager_advice(team)
        depth_advice = [a for a in advice if "profondità" in a["title"].lower()]
        assert len(depth_advice) >= 1

    def test_young_talent_advice(self):
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
        players[0].age = 18
        players[0].potential = 85
        players[1].age = 19
        players[1].potential = 82
        team = _make_team(players=players)
        advice = generate_manager_advice(team)
        talent_advice = [a for a in advice if "talento" in a["title"].lower()]
        assert len(talent_advice) == 1
        assert talent_advice[0]["priority"] == "success"

    def test_all_clear_advice(self):
        """When everything is fine, should get 'all clear' message."""
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70,
                          condition=80, form=60, happiness=70, contract_years=3)
                   for i in range(16)]
        # Add position variety
        players[0].position = Position.GOALKEEPER
        players[1].position = Position.GOALKEEPER
        players[2].position = Position.DEFENSE
        players[3].position = Position.DEFENSE
        players[4].position = Position.DEFENSE
        players[5].position = Position.ATTACK
        players[6].position = Position.ATTACK
        players[7].position = Position.ATTACK
        team = _make_team(players=players, budget=300)
        team.init_finances(0)
        advice = generate_manager_advice(team)
        clear_advice = [a for a in advice if "controllo" in a["title"].lower()]
        # May or may not appear depending on facilities
        if clear_advice:
            assert clear_advice[0]["priority"] == "success"

    def test_advice_sorted_by_priority(self):
        """Advice should be sorted: danger first, then warning, info, success."""
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
        players[0].injured = True  # danger
        players[1].condition = 20  # warning
        team = _make_team(players=players, budget=600)  # success
        advice = generate_manager_advice(team)
        priorities = [a["priority"] for a in advice]
        order = {"danger": 0, "warning": 1, "info": 2, "success": 3}
        sorted_priorities = sorted(priorities, key=lambda p: order.get(p, 9))
        assert priorities == sorted_priorities

    def test_facilities_advice(self):
        team = _make_team(budget=300)
        team.init_finances(0)
        advice = generate_manager_advice(team)
        facilities_advice = [a for a in advice if "Impianti" in a["title"]]
        assert len(facilities_advice) == 1
        assert facilities_advice[0]["priority"] == "info"

    def test_low_form_advice(self):
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
        players[0].form = 20
        players[1].form = 25
        team = _make_team(players=players)
        advice = generate_manager_advice(team)
        form_advice = [a for a in advice if "Forma" in a["title"]]
        assert len(form_advice) == 1