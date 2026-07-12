"""Tests for match-day realism systems."""
from src.models import Player, Position


def make_player(**overrides):
    values = {
        "name": "Test Player",
        "position": Position.MIDFIELD,
        "passing": 70,
        "shooting": 70,
        "defense": 70,
        "speed": 70,
        "stamina": 70,
    }
    values.update(overrides)
    return Player(**values)


def test_condition_reduces_effective_rating():
    fresh = make_player(condition=100, form=50)
    tired = make_player(condition=40, form=50)
    assert tired.effective_rating() < fresh.effective_rating()


def test_positive_form_improves_effective_rating():
    normal = make_player(form=50)
    in_form = make_player(form=90)
    assert in_form.effective_rating() > normal.effective_rating()


def test_match_load_depends_on_intensity():
    balanced = make_player(condition=100)
    attacking = make_player(condition=100)
    balanced.apply_match_load("Bilanciata")
    attacking.apply_match_load("Offensiva")
    assert attacking.condition < balanced.condition
    assert attacking.matches_since_rest == 1


def test_rest_recovers_and_resets_workload():
    player = make_player(condition=55, matches_since_rest=4)
    player.apply_match_load(played=False)
    assert player.condition == 73
    assert player.matches_since_rest == 0


def test_form_is_bounded():
    player = make_player(form=99)
    player.update_form(won=True, scored=True)
    assert player.form == 100
    player.form = 1
    player.update_form(won=False)
    assert player.form == 0


def test_injured_player_has_zero_effective_rating():
    player = make_player(injured=True, injury_duration=2)
    assert player.effective_rating() == 0


def test_team_selection_uses_match_day_readiness():
    from src.models import Team

    fresh = make_player(name="Fresh", condition=100, form=70)
    tired = make_player(
        name="Tired Star", passing=85, shooting=85, defense=85,
        speed=85, stamina=85, condition=20, form=20,
    )
    fillers = [
        make_player(name=f"Player {index}", condition=100, form=50)
        for index in range(10)
    ]
    team = Team(name="Test XI", players=[fresh, tired] + fillers)
    starters = team.get_starters()
    assert fresh in starters
    assert tired not in starters


def test_healing_clears_medical_diagnosis():
    player = make_player(
        injured=True,
        injury_duration=1,
        injury_type="Contusione",
    )
    player.heal_one_match()
    assert player.injured is False
    assert player.injury_duration == 0
    assert player.injury_type == ""


def test_initial_squad_roles_create_hierarchy_and_payroll():
    from src.models import Team

    players = [
        make_player(name=f"Player {index}", passing=60 + index)
        for index in range(14)
    ]
    team = Team(name="Contracts FC", players=players)
    team.initialize_squad_roles()
    roles = {player.squad_role for player in players}
    assert "Chiave" in roles
    assert "Titolare" in roles
    assert "Rotazione" in roles
    assert team.payroll_per_round() == sum(player.wage for player in players)


def test_key_player_loses_happiness_when_benched():
    player = make_player(squad_role="Chiave", happiness=60)
    player.update_happiness_for_selection(started=False)
    assert player.happiness == 55


def test_rotation_player_gains_happiness_when_selected():
    player = make_player(squad_role="Rotazione", happiness=60)
    player.update_happiness_for_selection(started=True)
    assert player.happiness == 63


def test_contract_renewal_rejects_unrealistic_wage():
    player = make_player(squad_role="Chiave", happiness=60)
    assert player.renew_contract(years=3, wage=1) is False
    assert player.happiness == 55


def test_contract_renewal_accepts_credible_offer():
    player = make_player(squad_role="Titolare", happiness=60)
    assert player.renew_contract(years=4, wage=8) is True
    assert player.contract_years == 4
    assert player.wage == 8
    assert player.happiness == 65
