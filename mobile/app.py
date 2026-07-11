"""Main Kivy App for Field Hockey Manager mobile UI."""
from __future__ import annotations
import json
import os
import sys
import random
import traceback

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.resources import resource_find
from kivy.uix.label import Label

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.models import Player, Team, Match, Position
from src.database import Database
from src.season import (
    generate_calendar, Standings, train_player,
    generate_free_agents, player_price,
    MAX_TRAININGS_PER_WEEK, TRAINING_ATTRIBUTES,
    age_player_one_year, season_aging,
)
from src.simulation import simulate_match

from mobile.screens import (
    MenuScreen, RosaScreen, CalendarioScreen, ClassificaScreen,
    PartitaScreen, StatisticheScreen, AllenamentiScreen, MercatoScreen,
    CarrieraScreen,
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
        self.season_number: int = 1
        self.manager_reputation: int = 50
        self.board_confidence: int = 65
        self.supporters: int = 1200
        self.season_objective: str = "Qualificazione playoff"
        self.career_news: list[str] = ["Benvenuto nella tua nuova carriera da manager."]

    def build(self):
        try:
            self._init_game()
        except Exception:
            error_text = traceback.format_exc()
            try:
                os.makedirs(self.user_data_dir, exist_ok=True)
                with open(os.path.join(self.user_data_dir, "startup_error.txt"), "w",
                          encoding="utf-8") as error_file:
                    error_file.write(error_text)
            except Exception:
                pass
            return Label(
                text="[b]Errore di avvio[/b]\n\n" + error_text[-1800:],
                markup=True,
                color=(1, 0.35, 0.35, 1),
                halign="left",
                valign="top",
                text_size=(Window.width - 30, None),
            )

        self.sm = ScreenManager(transition=SlideTransition(direction="left"))

        self.sm.add_widget(MenuScreen(self, name="menu"))
        self.sm.add_widget(RosaScreen(self, name="rosa"))
        self.sm.add_widget(CalendarioScreen(self, name="calendario"))
        self.sm.add_widget(ClassificaScreen(self, name="classifica"))
        self.sm.add_widget(PartitaScreen(self, name="partita"))
        self.sm.add_widget(StatisticheScreen(self, name="statistiche"))
        self.sm.add_widget(AllenamentiScreen(self, name="allenamenti"))
        self.sm.add_widget(MercatoScreen(self, name="mercato"))
        self.sm.add_widget(CarrieraScreen(self, name="carriera"))

        return self.sm

    def _init_game(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Packaged application files are read-only on Android. Store the
        # mutable SQLite database in Kivy's private, writable app directory.
        os.makedirs(self.user_data_dir, exist_ok=True)
        db_path = os.path.join(self.user_data_dir, "fhm.db")
        teams_path = (
            resource_find("data/teams.json")
            or resource_find("teams.json")
            or os.path.join(project_root, "data", "teams.json")
        )
        if not teams_path or not os.path.exists(teams_path):
            raise FileNotFoundError(
                "Risorsa data/teams.json non inclusa nell'APK"
            )

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

        saved_teams = self.db.load_all_teams()
        state = self.db.load_state() or {}
        if saved_teams and len(saved_teams) == len(self.teams):
            by_name = {team.name: team for team in saved_teams}
            self.teams = [by_name.get(team.name, team) for team in self.teams]

        self.user_team_idx = 0
        self.user_team = self.teams[0] if self.teams else None
        self.calendar = generate_calendar(self.teams, self.user_team_idx)
        self.current_round = int(state.get("current_round", 0))
        self.trainings_used = int(state.get("trainings_used", 0))
        self.season_number = int(state.get("season_number", 1))
        self.manager_reputation = int(state.get("manager_reputation", 50))
        self.board_confidence = int(state.get("board_confidence", 65))
        self.supporters = int(state.get("supporters", 1200))
        self.season_objective = state.get("season_objective", "Qualificazione playoff")
        self.career_news = state.get(
            "career_news", ["Benvenuto nella tua nuova carriera da manager."]
        )
        self.free_agents = generate_free_agents(8)

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
        self._update_career_after_match(match, entry)
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
                scorer_name = ev.get("scorer") or ev.get("player", "")
                team_players = home.players if ev.get("team") in ("home", home.name) else away.players
                for p in team_players:
                    if p.name == scorer_name:
                        p.goals += 1
                        break

    def _update_career_after_match(self, match: Match, entry: dict):
        """Update reputation, board confidence, supporters and news."""
        is_home = entry["home"] == self.user_team_idx
        user_score = match.home_score if is_home else match.away_score
        opponent_score = match.away_score if is_home else match.home_score
        opponent = match.away_team if is_home else match.home_team
        if user_score > opponent_score:
            self.manager_reputation = min(100, self.manager_reputation + 2)
            self.board_confidence = min(100, self.board_confidence + 4)
            self.supporters += 80
            headline = f"Vittoria contro {opponent.name}: la dirigenza è soddisfatta."
        elif user_score == opponent_score:
            self.board_confidence = min(100, self.board_confidence + 1)
            self.supporters += 15
            headline = f"Pareggio contro {opponent.name}: prestazione solida."
        else:
            self.manager_reputation = max(0, self.manager_reputation - 1)
            self.board_confidence = max(0, self.board_confidence - 4)
            self.supporters = max(100, self.supporters - 35)
            headline = f"Sconfitta contro {opponent.name}: aumenta la pressione."
        self.career_news.insert(0, headline)
        self.career_news = self.career_news[:6]

    def start_new_season(self) -> bool:
        """Advance the career after the current championship is complete."""
        if self.get_next_match() is not None:
            return False
        prize = max(100, 700 - self.get_standings().index(self.user_team) * 80)
        for team in self.teams:
            team.points = team.goals_for = team.goals_against = 0
            team.wins = team.draws = team.losses = 0
            for player in team.players:
                season_aging(player)
                age_player_one_year(player)
                player.appearances = 0
                player.goals = 0
        if self.user_team:
            self.user_team.budget += prize
        self.season_number += 1
        self.current_round = 0
        self.trainings_used = 0
        self.calendar = generate_calendar(self.teams, self.user_team_idx)
        self.free_agents = generate_free_agents(8)
        self.season_objective = (
            "Vincere il campionato" if self.manager_reputation >= 75
            else "Qualificazione playoff"
        )
        self.career_news.insert(0, f"Stagione {self.season_number}: budget premio +{prize}.")
        self.save_game()
        return True

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
        self.db.save_state({
            "current_round": self.current_round,
            "trainings_used": self.trainings_used,
            "season_number": self.season_number,
            "manager_reputation": self.manager_reputation,
            "board_confidence": self.board_confidence,
            "supporters": self.supporters,
            "season_objective": self.season_objective,
            "career_news": self.career_news,
        })