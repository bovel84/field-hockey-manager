"""Tests for models: Player, Team, Match dataclasses."""
import pytest
from src.models import Player, Team, Match, Position


class TestPlayer:
    def test_create_player(self):
        p = Player(name="Mario Rossi", position=Position.GOALKEEPER, passing=70, shooting=30, defense=85, speed=50, stamina=80)
        assert p.name == "Mario Rossi"
        assert p.position == Position.GOALKEEPER
        assert p.passing == 70
        assert p.shooting == 30
        assert p.defense == 85
        assert p.speed == 50
        assert p.stamina == 80
        assert p.goals == 0
        assert p.appearances == 0
        # Extended fields
        assert p.age == 25
        assert p.morale == 50
        assert p.injured is False
        assert p.injury_duration == 0

    def test_player_overall_rating(self):
        p = Player(name="Luigi Bianchi", position=Position.ATTACK, passing=80, shooting=90, defense=40, speed=85, stamina=75)
        overall = p.overall_rating()
        assert 0 <= overall <= 100
        # weighted: shooting and speed matter more for attack
        assert overall > 70

    def test_goalkeeper_overall(self):
        p = Player(name="GK", position=Position.GOALKEEPER, passing=60, shooting=20, defense=90, speed=50, stamina=85)
        overall = p.overall_rating()
        assert overall > 70  # defense-heavy

    def test_defender_overall(self):
        p = Player(name="DEF", position=Position.DEFENSE, passing=65, shooting=40, defense=88, speed=70, stamina=80)
        overall = p.overall_rating()
        assert overall > 65

    def test_midfielder_overall(self):
        p = Player(name="MID", position=Position.MIDFIELD, passing=82, shooting=60, defense=70, speed=75, stamina=85)
        overall = p.overall_rating()
        assert overall > 70

    def test_player_str(self):
        p = Player(name="Test", position=Position.ATTACK, passing=70, shooting=80, defense=50, speed=75, stamina=70)
        s = str(p)
        assert "Test" in s
        assert "Attacco" in s or "ATTACK" in s

    def test_effective_rating_normal_morale(self):
        p = Player(name="Test", position=Position.MIDFIELD, passing=80, shooting=70, defense=70, speed=75, stamina=80, morale=50, happiness=50)
        assert p.effective_rating() == p.overall_rating()

    def test_effective_rating_high_morale(self):
        p = Player(name="Test", position=Position.MIDFIELD, passing=80, shooting=70, defense=70, speed=75, stamina=80, morale=90, happiness=50)
        eff = p.effective_rating()
        base = p.overall_rating()
        assert eff == int(round(base * 1.05))
        assert eff > base

    def test_effective_rating_low_morale(self):
        p = Player(name="Test", position=Position.MIDFIELD, passing=80, shooting=70, defense=70, speed=75, stamina=80, morale=20, happiness=50)
        eff = p.effective_rating()
        base = p.overall_rating()
        assert eff == int(round(base * 0.90))
        assert eff < base

    def test_effective_rating_injured(self):
        p = Player(name="Test", position=Position.MIDFIELD, passing=80, shooting=70, defense=70, speed=75, stamina=80,
                   injured=True, injury_duration=2)
        assert p.effective_rating() == 0

    def test_can_play(self):
        p = Player(name="Test", position=Position.MIDFIELD)
        assert p.can_play() is True
        p.injured = True
        assert p.can_play() is False

    def test_heal_one_match(self):
        p = Player(name="Test", position=Position.MIDFIELD, injured=True, injury_duration=3)
        p.heal_one_match()
        assert p.injured is True
        assert p.injury_duration == 2
        p.heal_one_match()
        assert p.injured is True
        assert p.injury_duration == 1
        p.heal_one_match()
        assert p.injured is False
        assert p.injury_duration == 0

    def test_apply_morale(self):
        p = Player(name="Test", position=Position.MIDFIELD, morale=50)
        p.apply_morale(10)
        assert p.morale == 60
        p.apply_morale(-20)
        assert p.morale == 40
        p.apply_morale(-100)
        assert p.morale == 0
        p.apply_morale(200)
        assert p.morale == 100


class TestTeam:
    def test_create_team(self):
        players = [
            Player(name=f"P{i}", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80)
            for i in range(1)
        ]
        t = Team(name="HC Cagliari", players=players)
        assert t.name == "HC Cagliari"
        assert len(t.players) == 1
        assert t.points == 0
        assert t.goals_for == 0
        assert t.goals_against == 0
        assert t.wins == 0
        assert t.draws == 0
        assert t.losses == 0
        # Extended fields
        assert t.budget == 500
        assert t.formation == "4-3-3"
        assert t.intensity == "Bilanciata"

    def test_team_rating(self):
        players = [
            Player(name=f"P{i}", position=Position.MIDFIELD, passing=80, shooting=70, defense=70, speed=75, stamina=80)
            for i in range(16)
        ]
        t = Team(name="HC Roma", players=players)
        rating = t.team_rating()
        assert 0 <= rating <= 100
        assert rating > 60  # rating now includes condition/form/happiness defaults

    def test_team_rating_empty(self):
        t = Team(name="Empty FC", players=[])
        assert t.team_rating() == 0

    def test_get_starters(self):
        players = [
            Player(name=f"P{i:02d}", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80)
            for i in range(16)
        ]
        t = Team(name="HC Test", players=players)
        starters = t.get_starters()
        assert len(starters) == 11

    def test_get_starters_excludes_injured(self):
        players = [
            Player(name=f"GK{i}", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80)
            for i in range(2)
        ]
        players[0].injured = True
        players[0].injury_duration = 2
        for pos in [Position.DEFENSE] * 4 + [Position.MIDFIELD] * 5 + [Position.ATTACK] * 6:
            players.append(Player(name=f"P{len(players)}", position=pos, passing=70, shooting=60, defense=60, speed=70, stamina=70))
        t = Team(name="HC Test", players=players)
        starters = t.get_starters()
        assert all(not p.injured for p in starters)

    def test_team_str(self):
        players = [Player(name="P1", position=Position.GOALKEEPER, passing=60, shooting=20, defense=80, speed=50, stamina=80)]
        t = Team(name="HC Test", players=players)
        s = str(t)
        assert "HC Test" in s


class TestMatch:
    def test_create_match(self):
        home = Team(name="HC Cagliari", players=[])
        away = Team(name="HC Roma", players=[])
        m = Match(home_team=home, away_team=away)
        assert m.home_team.name == "HC Cagliari"
        assert m.away_team.name == "HC Roma"
        assert m.home_score == 0
        assert m.away_score == 0
        assert m.events == []
        assert m.played is False

    def test_match_result(self):
        home = Team(name="HC Cagliari", players=[])
        away = Team(name="HC Roma", players=[])
        m = Match(home_team=home, away_team=away, home_score=3, away_score=1, played=True)
        assert m.home_score == 3
        assert m.away_score == 1
        assert m.played is True

    def test_match_str(self):
        home = Team(name="HC Cagliari", players=[])
        away = Team(name="HC Roma", players=[])
        m = Match(home_team=home, away_team=away, home_score=2, away_score=2, played=True)
        s = str(m)
        assert "HC Cagliari" in s
        assert "HC Roma" in s
        assert "2" in s