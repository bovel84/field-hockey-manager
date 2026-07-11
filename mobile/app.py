"""Main Kivy App for Field Hockey Manager mobile UI."""
from __future__ import annotations
import json
import os
import sys
import random

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.models import Player, Team, Match, Position
from src.database import Database
from src.season import (
    generate_calendar, Standings, train_player,
    generate_free_agents, player_price,
    MAX_TRAININGS_PER_WEEK, TRAINING_ATTRIBUTES,
)
from src.simulation import simulate_match

from mobile.screens import (
    MenuScreen, RosaScreen, CalendarioScreen, ClassificaScreen,
    PartitaScreen, StatisticheScreen, AllenamentiScreen, MercatoScreen,
)

Window.clearcolor = (0.102, 0.102, 0.180, 1)  # #1a1a2e

POS_MAP = {
    "Portiere": Position.GOALKEEPER,
    "Difesa": Position.DEFENSE,
    "Centrocampo": Position.MIDFIELD,
    "Attacco": Position.ATTACK,
}


class FieldHockeyManagerApp(App):
    """Main Kivy application for Field Hockey Manager."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db: Database | None = None
        self.teams: list[Team] = []
        self.user_team: Team | None = None
        self.user_team_idx: int = 0
        self.calendar: list[dict] = []
        self.current_round: int = 0
        self.trainings_used: int = 0
        self.free_agents: list[Player] = []
        self.sm: ScreenManager | None = None

    def build(self):
        self._init_game()
        self.sm = ScreenManager(transition=SlideTransition(direction="left"))

        self.sm.add_widget(MenuScreen(self, name="menu"))
        self.sm.add_widget(RosaScreen(self, name="rosa"))
        self.sm.add_widget(CalendarioScreen(self, name="calendario"))
        self.sm.add_widget(ClassificaScreen(self, name="classifica"))
        self.sm.add_widget(PartitaScreen(self, name="partita"))
        self.sm.add_widget(StatisticheScreen(self, name="statistiche"))
        self.sm.add_widget(AllenamentiScreen(self, name="allenamenti"))
        self.sm.add_widget(MercatoScreen(self, name="mercato"))

        return self.sm

    def _init_game(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Packaged application files are read-only on Android. Store the
        # mutable SQLite database in Kivy's private, writable app directory.
        os.makedirs(self.user_data_dir, exist_ok=True)
        db_path = os.path.join(self.user_data_dir, "fhm.db")
        teams_path = os.path.join(project_root, "data", "teams.json")

        self.db = Database(db_path)
        self.db.init()

        with open(teams_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.teams = []
        for t_data in data["teams"]:
            players = []
            for p_data in t_data["players"]:
                players.append(Player(
                    name=p_data["name"],
                    position=POS_MAP[p_data["position"]],
                    passing=p_data["passing"],
                    shooting=p_data["shooting"],
                    defense=p_data["defense"],
                    speed=p_data["speed"],
                    stamina=p_data["stamina"],
                ))
            team = Team(name=t_data["name"], players=players)
            self.teams.append(team)

        self.user_team_idx = 0
        self.user_team = self.teams[0] if self.teams else None
        self.calendar = generate_calendar(self.teams, self.user_team_idx)
        self.current_round = 0
        self.trainings_used = 0
        self.free_agents = generate_free_agents(5)

    def get_next_match(self) -> dict | None:
        for entry in self.calendar:
            if entry["round"] >= self.current_round:
                return entry
        return None

    def next_match_info(self) -> str:
        m = self.get_next_match()
        if m:
            home = self.teams[m["home"]]
            away = self.teams[m["away"]]
            return f"Prossima: {home.name} vs {away.name}"
        return "Stagione completata! 🎉"

    def play_next_match(self, formation: str, intensity: str) -> Match | None:
        entry = self.get_next_match()
        if not entry:
            return None
        home = self.teams[entry["home"]]
        away = self.teams[entry["away"]]

        # Apply user formation/intensity
        if self.user_team:
            self.user_team.formation = formation
            self.user_team.intensity = intensity

        # Determine formations/intensities
        if entry["home"] == self.user_team_idx:
            match = simulate_match(home, away, seed=None,
                                    home_formation=formation, home_intensity=intensity)
        else:
            match = simulate_match(home, away, seed=None,
                                    away_formation=formation, away_intensity=intensity)

        self._apply_result(match, entry)
        self.current_round = entry["round"] + 1
        self.trainings_used = 0  # reset trainings for new round
        return match

    def _apply_result(self, match: Match, entry: dict):
        home = match.home_team
        away = match.away_team
        home.goals_for += match.home_score
        home.goals_against += match.away_score
        away.goals_for += match.away_score
        away.goals_against += match.home_score

        if match.home_score > match.away_score:
            home.points += 3
            home.wins += 1
            away.losses += 1
            for p in home.players:
                p.apply_morale(10)
            for p in away.players:
                p.apply_morale(-10)
        elif match.home_score < match.away_score:
            away.points += 3
            away.wins += 1
            home.losses += 1
            for p in away.players:
                p.apply_morale(10)
            for p in home.players:
                p.apply_morale(-10)
        else:
            home.points += 1
            away.points += 1
            home.draws += 1
            away.draws += 1

        for p in home.players + away.players:
            p.appearances += 1
            p.heal_one_match()

        for ev in match.events:
            if ev.get("type") == "goal":
                scorer_name = ev.get("player", "")
                team_players = home.players if ev.get("team") == home.name else away.players
                for p in team_players:
                    if p.name == scorer_name:
                        p.goals += 1
                        break

    def get_standings(self) -> list[Team]:
        return sorted(self.teams, key=lambda t: (t.points, t.goals_for - t.goals_against), reverse=True)

    def train_player_attr(self, player: Player, attr: str) -> str:
        if self.trainings_used >= MAX_TRAININGS_PER_WEEK:
            return "❌ Nessun allenamento rimasto questa settimana!"
        result = train_player(player, attr)
        self.trainings_used += 1
        if result > 0:
            return f"✅ {player.name} ha migliorato {attr} (+{result})"
        return f"⚠️ {player.name} non ha migliorato {attr}"

    def buy_player(self, player: Player) -> bool:
        if not self.user_team:
            return False
        price = player_price(player)
        if self.user_team.budget < price:
            return False
        same_pos = [p for p in self.user_team.players if p.position == player.position]
        if same_pos:
            weakest = min(same_pos, key=lambda p: p.overall_rating())
            self.user_team.players.remove(weakest)
        self.user_team.players.append(player)
        self.user_team.budget -= price
        if player in self.free_agents:
            self.free_agents.remove(player)
        return True

    def get_player_price(self, player: Player) -> int:
        return player_price(player)

    def save_game(self):
        if not self.db:
            return
        for team in self.teams:
            self.db.save_team(team)