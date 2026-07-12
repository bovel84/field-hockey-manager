"""Tests for Phase 3 Sprint 4: Finance, Sponsor & Facilities."""
import pytest
import random
from src.models import Team, Player, Position, Sponsor, Stadium, Facilities, generate_sponsors, generate_stadium


def _make_team(name="Test FC", players=None, prestige=0):
    if players is None:
        players = [Player(name=f"P{i}", position=Position.MIDFIELD,
                          passing=70, shooting=70, defense=70, speed=70, stamina=70)
                   for i in range(16)]
    return Team(name=name, players=players, budget=500, prestige=prestige)


class TestSponsor:
    """Test Sponsor dataclass."""

    def test_sponsor_basic(self):
        s = Sponsor(name="TestCorp", base_amount=100, bonus_per_win=5, bonus_per_goal=2)
        assert s.name == "TestCorp"
        assert s.base_amount == 100

    def test_seasonal_income_no_bonuses(self):
        s = Sponsor(name="TestCorp", base_amount=100)
        assert s.seasonal_income(wins=0, goals=0) == 100

    def test_seasonal_income_with_bonuses(self):
        s = Sponsor(name="TestCorp", base_amount=100, bonus_per_win=5, bonus_per_goal=2)
        income = s.seasonal_income(wins=10, goals=30)
        assert income == 100 + 50 + 60  # base + win bonus + goal bonus

    def test_advance_season(self):
        s = Sponsor(name="TestCorp", base_amount=100, duration_years=2)
        assert s.advance_season() is True  # still active
        assert s.duration_years == 1
        assert s.advance_season() is False  # expired
        assert s.duration_years == 0

    def test_generate_sponsors_count(self):
        rng = random.Random(42)
        sponsors = generate_sponsors(rng, count=3, prestige=0)
        assert len(sponsors) == 3
        for s in sponsors:
            assert s.base_amount > 0
            assert s.duration_years >= 1

    def test_generate_sponsors_prestige_effect(self):
        rng = random.Random(42)
        low = generate_sponsors(rng, count=1, prestige=0)
        rng2 = random.Random(42)
        high = generate_sponsors(rng2, count=1, prestige=10)
        assert high[0].base_amount >= low[0].base_amount


class TestStadium:
    """Test Stadium dataclass."""

    def test_stadium_basic(self):
        s = Stadium(name="Test Arena", capacity=2000, ticket_price=10)
        assert s.name == "Test Arena"
        assert s.capacity == 2000

    def test_match_revenue(self):
        s = Stadium(name="Arena", capacity=1000, ticket_price=10)
        revenue = s.match_revenue(attendance_ratio=0.5)
        assert revenue == 5000  # 500 * 10

    def test_seasonal_maintenance(self):
        s = Stadium(name="Arena", maintenance_cost=50, level=2)
        assert s.seasonal_maintenance() == 100  # 50 * 2

    def test_upgrade_cost(self):
        s = Stadium(name="Arena", level=2)
        assert s.upgrade_cost() == 600  # 300 * 2

    def test_upgrade(self):
        s = Stadium(name="Arena", capacity=1000, level=1, maintenance_cost=40)
        assert s.upgrade() is True
        assert s.level == 2
        assert s.capacity == 1500
        assert s.maintenance_cost == 60

    def test_upgrade_max_level(self):
        s = Stadium(name="Arena", level=5)
        assert s.upgrade() is False

    def test_generate_stadium(self):
        s = generate_stadium("Amsicora Cagliari", prestige=2)
        assert "Amsicora" in s.name or "Stadio" in s.name
        assert s.capacity >= 1500


class TestFacilities:
    """Test Facilities dataclass."""

    def test_facilities_basic(self):
        f = Facilities()
        assert f.academy_level == 1
        assert f.medical_level == 1
        assert f.training_level == 1

    def test_upgrade_cost(self):
        f = Facilities(academy_level=2)
        assert f.upgrade_cost("academy") == 500  # 250 * 2

    def test_upgrade(self):
        f = Facilities()
        assert f.upgrade("academy") is True
        assert f.academy_level == 2
        assert f.upgrade("medical") is True
        assert f.medical_level == 2
        assert f.upgrade("training") is True
        assert f.training_level == 2

    def test_upgrade_max(self):
        f = Facilities(academy_level=5)
        assert f.upgrade("academy") is False

    def test_academy_bonus(self):
        f = Facilities(academy_level=3)
        assert abs(f.academy_bonus() - 0.2) < 1e-9  # (3-1) * 0.1

    def test_medical_recovery_bonus(self):
        f = Facilities(medical_level=4)
        assert abs(f.medical_recovery_bonus() - 0.3) < 1e-9

    def test_training_bonus(self):
        f = Facilities(training_level=5)
        assert abs(f.training_bonus() - 0.4) < 1e-9


class TestTeamFinance:
    """Test Team finance integration."""

    def test_init_finances(self):
        team = _make_team("Test FC", prestige=2)
        team.init_finances(prestige=2)
        assert len(team.sponsors) >= 1
        assert team.stadium is not None
        assert team.facilities is not None
        assert team.stadium.capacity >= 1500

    def test_sponsor_income(self):
        team = _make_team()
        team.init_finances(0)
        income = team.sponsor_income(wins=5, goals=20)
        assert income > 0

    def test_stadium_revenue_per_match(self):
        team = _make_team()
        team.init_finances(0)
        rev = team.stadium_revenue_per_match(0.6)
        assert rev > 0

    def test_facilities_maintenance(self):
        team = _make_team()
        team.init_finances(0)
        maint = team.facilities_maintenance()
        assert maint > 0

    def test_season_balance(self):
        team = _make_team()
        team.init_finances(0)
        team.season_revenue = 500
        team.season_expenses = 300
        team.season_prize_money = 100
        assert team.season_balance() == 300  # 500 + 100 - 300

    def test_season_balance_negative(self):
        team = _make_team()
        team.season_revenue = 100
        team.season_expenses = 400
        team.season_prize_money = 0
        assert team.season_balance() == -300


class TestSeasonFinance:
    """Test season finance processing."""

    def test_process_match_finances_home(self):
        from src.season import process_match_finances
        team = _make_team()
        team.init_finances(0)
        initial_budget = team.budget
        process_match_finances(team, is_home=True, result="win", goals_scored=3, goals_conceded=1)
        # Home win: ticket revenue added, payroll deducted
        assert team.budget != initial_budget
        assert team.season_revenue > 0
        assert team.season_expenses > 0

    def test_process_match_finances_away(self):
        from src.season import process_match_finances
        team = _make_team()
        team.init_finances(0)
        initial_budget = team.budget
        process_match_finances(team, is_home=False, result="loss", goals_scored=0, goals_conceded=2)
        # Away: no ticket revenue, only payroll deducted
        assert team.budget < initial_budget
        assert team.season_expenses > 0

    def test_process_season_finances(self):
        from src.season import process_season_finances
        team = _make_team("Test FC", prestige=1)
        team.init_finances(1)
        process_season_finances(team, wins=8, goals_scored=25, league_position=3, total_teams=8)
        # Should have sponsor income + prize money - maintenance
        assert team.season_revenue > 0
        assert team.season_prize_money > 0
        assert team.season_expenses > 0

    def test_sponsor_expiry_and_renewal(self):
        from src.season import process_season_finances
        team = _make_team()
        team.init_finances(0)
        # Set all sponsors to expire
        for s in team.sponsors:
            s.duration_years = 1
        process_season_finances(team, wins=0, goals_scored=0, league_position=8, total_teams=8)
        # Sponsors should be renewed (at least 1)
        assert len(team.sponsors) >= 1