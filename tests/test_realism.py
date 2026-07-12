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
