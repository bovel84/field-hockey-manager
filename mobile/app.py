"""Main Kivy App for Field Hockey Manager mobile UI."""
from __future__ import annotations
import json
import os
import sys
import traceback

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.resources import resource_find
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.models import Player, Team, Match, Position
from src.database import Database
from src.season import (
    generate_calendar, train_player,
    generate_free_agents, player_price, minimum_wage,
    evaluate_transfer_offer, incoming_offer_value,
    MAX_TRAININGS_PER_WEEK, TRAINING_ATTRIBUTES,
    age_player_one_year, season_aging,
)
from src.simulation import simulate_match

from mobile.screens import (
    MenuScreen, RosaScreen, CalendarioScreen, ClassificaScreen,
    PartitaScreen, StatisticheScreen, AllenamentiScreen, MercatoScreen,
    CarrieraScreen, YouthAcademyScreen, SaveLoadScreen, ContractsScreen,
    LineupScreen,
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
        self._played_matches_history: list[Match] = []

    def build(self):
        """Show a real Kivy window immediately, then initialize the career."""
        self.root_container = BoxLayout(orientation="vertical", padding=24)
        self.loading_label = Label(
            text="[b]Field Hockey Manager[/b]\n\nAvvio carriera in corso...",
            markup=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle",
        )
        self.loading_label.bind(
            size=lambda inst, _value=None: setattr(inst, "text_size", inst.size)
        )
        self.root_container.add_widget(self.loading_label)
        Clock.schedule_once(self._finish_startup, 0.25)
        return self.root_container

    def _finish_startup(self, _dt):
        try:
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
            self.sm.add_widget(YouthAcademyScreen(self, name="youth"))
            self.sm.add_widget(CarrieraScreen(self, name="carriera"))
            self.sm.add_widget(SaveLoadScreen(self, name="saveload"))
            self.sm.add_widget(ContractsScreen(self, name="contratti"))
            self.sm.add_widget(LineupScreen(self, name="formazione"))
            self.root_container.clear_widgets()
            self.root_container.add_widget(self.sm)
        except Exception:
            error_text = traceback.format_exc()
            try:
                os.makedirs(self.user_data_dir, exist_ok=True)
                with open(
                    os.path.join(self.user_data_dir, "startup_error.txt"),
                    "w", encoding="utf-8"
                ) as error_file:
                    error_file.write(error_text)
            except Exception:
                pass
            self.root_container.clear_widgets()
            error_label = Label(
                text="[b]Errore di avvio[/b]\n\n" + error_text[-2400:],
                markup=True,
                color=(1, 0.35, 0.35, 1),
                halign="left",
                valign="top",
            )
            error_label.bind(
                size=lambda inst, _value=None: setattr(inst, "text_size", inst.size)
            )
            self.root_container.add_widget(error_label)

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
            team = Team(name=t_data["name"], players=players, budget=t_data.get("budget", 500),
                        rivals=t_data.get("rivals", []))
            self.teams.append(team)

        saved_teams = self.db.load_all_teams()
        state = self.db.load_state() or {}
        if saved_teams and len(saved_teams) == len(self.teams):
            by_name = {team.name: team for team in saved_teams}
            self.teams = [by_name.get(team.name, team) for team in self.teams]

        for team in self.teams:
            team.initialize_squad_roles()

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
        self._played_matches_history = []
        self.season_goals = state.get("season_goals", [])
        if not self.season_goals:
            self.season_goals = self._generate_season_goals()

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

    def get_scouting_report(self) -> str:
        """Return a compact pre-match report for the next opponent."""
        entry = self.get_next_match()
        if not entry or not self.user_team:
            return "Nessun rapporto disponibile."
        opponent_idx = (
            entry["away"] if entry["home"] == self.user_team_idx else entry["home"]
        )
        opponent = self.teams[opponent_idx]
        available = [player for player in opponent.players if player.can_play()]
        key_player = max(
            available, key=lambda player: player.effective_rating(), default=None,
        )
        avg_condition = (
            round(sum(player.condition for player in available) / len(available))
            if available else 0
        )
        injuries = sum(1 for player in opponent.players if player.injured)
        advice = "Mantieni un piano equilibrato."
        if opponent.pressing == "Alto":
            advice = "Supera il primo pressing con passaggi rapidi."
        elif opponent.formation == "5-3-2":
            advice = "Allarga il gioco contro il blocco difensivo."
        elif avg_condition < 72:
            advice = "Aumenta il ritmo: l'avversario è affaticato."
        return (
            f"SCOUTING: {opponent.name} | Rating {opponent.team_rating()} | "
            f"{opponent.formation}, pressing {opponent.pressing}, ritmo {opponent.tempo}\n"
            f"Condizione {avg_condition}% | Indisponibili {injuries} | "
            f"Uomo chiave: {key_player.name if key_player else '—'}\n"
            f"Consiglio: {advice}"
        )

    def play_next_match(
        self,
        formation: str,
        intensity: str,
        pressing: str = "Medio",
        tempo: str = "Bilanciato",
        user_subs: list[dict] | None = None,
    ) -> Match | None:
        entry = self.get_next_match()
        if not entry:
            return None
        home = self.teams[entry["home"]]
        away = self.teams[entry["away"]]
        user_is_home = entry["home"] == self.user_team_idx

        if self.user_team:
            self.user_team.formation = formation
            self.user_team.intensity = intensity
            self.user_team.pressing = pressing
            self.user_team.tempo = tempo

        match = simulate_match(
            home,
            away,
            seed=None,
            home_formation=formation if user_is_home else home.formation,
            home_intensity=intensity if user_is_home else home.intensity,
            home_pressing=pressing if user_is_home else home.pressing,
            home_tempo=tempo if user_is_home else home.tempo,
            away_formation=away.formation if user_is_home else formation,
            away_intensity=away.intensity if user_is_home else intensity,
            away_pressing=away.pressing if user_is_home else pressing,
            away_tempo=away.tempo if user_is_home else tempo,
            home_subs=user_subs if user_is_home else None,
            away_subs=None if user_is_home else user_subs,
        )

        self._apply_result(match, entry)
        self._update_career_after_match(match, entry)
        self.current_round = entry["round"] + 1
        self.trainings_used = 0
        self.save_game()
        return match

    def _apply_result(self, match: Match, entry: dict):
        # Track match for playoff/cup isolation (M2)
        self._played_matches_history.append(match)
        home = match.home_team
        away = match.away_team
        # Feature 2: Derby detection for doubled morale delta
        is_derby = away.name in (home.rivals or [])
        morale_delta = 20 if is_derby else 10
        home.goals_for += match.home_score
        home.goals_against += match.away_score
        away.goals_for += match.away_score
        away.goals_against += match.home_score

        if match.home_score > match.away_score:
            home.points += 3
            home.wins += 1
            away.losses += 1
            for p in home.get_starters():
                p.apply_morale(morale_delta)
            for p in away.get_starters():
                p.apply_morale(-morale_delta)
        elif match.home_score < match.away_score:
            away.points += 3
            away.wins += 1
            home.losses += 1
            for p in away.get_starters():
                p.apply_morale(morale_delta)
            for p in home.get_starters():
                p.apply_morale(-morale_delta)
        else:
            home.points += 1
            away.points += 1
            home.draws += 1
            away.draws += 1

        home_starters = home.get_starters()
        away_starters = away.get_starters()
        home_scorers = {
            ev.get("scorer") or ev.get("player", "")
            for ev in match.events
            if ev.get("type") in ("goal", "corner_goal", "penalty_goal")
            and ev.get("team") in ("home", home.name)
        }
        away_scorers = {
            ev.get("scorer") or ev.get("player", "")
            for ev in match.events
            if ev.get("type") in ("goal", "corner_goal", "penalty_goal")
            and ev.get("team") in ("away", away.name)
        }

        home_won = match.home_score > match.away_score
        away_won = match.away_score > match.home_score
        drew = match.home_score == match.away_score

        # Match load, recovery and form now affect future team selection/results.
        for team, starters, won, scorers in (
            (home, home_starters, home_won, home_scorers),
            (away, away_starters, away_won, away_scorers),
        ):
            starter_ids = {id(player) for player in starters}
            for player in team.players:
                player.heal_one_match()
                started = id(player) in starter_ids
                if started:
                    player.appearances += 1
                    player.apply_match_load(
                        team.intensity,
                        played=True,
                        pressing=team.pressing,
                        tempo=team.tempo,
                    )
                    player.update_form(won=won, drew=drew, scored=player.name in scorers)
                else:
                    player.apply_match_load(played=False)
                player.update_happiness_for_selection(started=started)
                player.recover_between_matches()
            team.budget = max(0, team.budget - team.payroll_per_round())

        for ev in match.events:
            if ev.get("type") in ("goal", "corner_goal", "penalty_goal"):
                scorer_name = ev.get("scorer") or ev.get("player", "")
                team_players = home.players if ev.get("team") in ("home", home.name) else away.players
                for player in team_players:
                    if player.name == scorer_name:
                        player.goals += 1
                        break

    def _update_career_after_match(self, match: Match, entry: dict):
        """Update reputation, board confidence, supporters and news."""
        is_home = entry["home"] == self.user_team_idx
        user_score = match.home_score if is_home else match.away_score
        opponent_score = match.away_score if is_home else match.home_score
        opponent = match.away_team if is_home else match.home_team
        # Feature 2: Derby detection — double morale/supporters delta
        user_team = self.user_team
        is_derby = (
            user_team is not None
            and opponent.name in (user_team.rivals or [])
        )
        morale_mult = 2 if is_derby else 1
        supporters_mult = 2 if is_derby else 1
        if user_score > opponent_score:
            self.manager_reputation = min(100, self.manager_reputation + 2)
            self.board_confidence = min(100, self.board_confidence + 4)
            self.supporters += 80 * supporters_mult
            headline = f"Vittoria contro {opponent.name}: la dirigenza è soddisfatta."
            if is_derby:
                headline = f"🔥 Derby vinto contro {opponent.name}! Tifosi in visibilio!"
        elif user_score == opponent_score:
            self.board_confidence = min(100, self.board_confidence + 1)
            self.supporters += 15 * supporters_mult
            headline = f"Pareggio contro {opponent.name}: prestazione solida."
            if is_derby:
                headline = f"🔥 Derby pareggiato contro {opponent.name}."
        else:
            self.manager_reputation = max(0, self.manager_reputation - 1)
            self.board_confidence = max(0, self.board_confidence - 4)
            self.supporters = max(100, self.supporters - 35 * supporters_mult)
            headline = f"Sconfitta contro {opponent.name}: aumenta la pressione."
            if is_derby:
                headline = f"🔥 Derby perso contro {opponent.name}: tifosi furiosi!"
        payroll = user_team.payroll_per_round() if user_team else 0
        headline += f" Monte stipendi del turno: {payroll}."
        if user_team and user_team.budget <= payroll * 2:
            headline += " ⚠️ Budget sotto pressione."
            self.board_confidence = max(0, self.board_confidence - 1)
        self.career_news.insert(0, headline)
        self.career_news = self.career_news[:6]

        # Feature 2: Double morale delta for derby in _apply_result
        # Applied via match.events — actual morale change happens in _apply_result
        # We mark derby matches for doubled morale there
        if is_derby:
            match.events.append({"type": "derby", "teams": [user_team.name if user_team else "", opponent.name]})

    def _generate_season_goals(self) -> list[dict]:
        """Generate 2-3 dynamic season objectives based on manager reputation."""
        import random as _rng
        rng = _rng.Random(self.season_number * 42 + self.manager_reputation)
        goals = []
        # Goal 1: Position-based (always present)
        if self.manager_reputation >= 75:
            goals.append({
                "id": "champion",
                "description": "Vinci il campionato",
                "type": "position",
                "target": 1,
                "reward_budget": 300,
                "reward_reputation": 5,
                "status": "active",
            })
        else:
            goals.append({
                "id": "top3",
                "description": "Qualificati per i playoff (top 3)",
                "type": "position",
                "target": 3,
                "reward_budget": 200,
                "reward_reputation": 3,
                "status": "active",
            })
        # Goal 2: Goals scored (varies by reputation)
        target_goals = 20 if self.manager_reputation < 50 else 25
        goals.append({
            "id": "goals",
            "description": f"Segna almeno {target_goals} gol in stagione",
            "type": "goals_scored",
            "target": target_goals,
            "reward_budget": 100,
            "reward_reputation": 2,
            "status": "active",
        })
        # Goal 3: Win streak (50% chance)
        if rng.random() < 0.5:
            goals.append({
                "id": "streak",
                "description": "Non perdere più di 2 partite consecutive",
                "type": "max_consecutive_losses",
                "target": 2,
                "reward_budget": 150,
                "reward_reputation": 3,
                "status": "active",
            })
        return goals

    def _evaluate_season_goals(self) -> list[str]:
        """Evaluate season goals at end of season. Returns news headlines."""
        headlines = []
        standings = self.get_standings()
        user_position = standings.index(self.user_team) + 1 if self.user_team in standings else len(standings)
        total_goals = self.user_team.goals_for if self.user_team else 0
        # Count consecutive losses
        max_consecutive = 0
        current_streak = 0
        for m in self._played_matches_history:
            is_home = m.home_team == self.user_team
            user_score = m.home_score if is_home else m.away_score
            opp_score = m.away_score if is_home else m.home_score
            if user_score < opp_score:
                current_streak += 1
                max_consecutive = max(max_consecutive, current_streak)
            else:
                current_streak = 0

        for goal in self.season_goals:
            if goal["status"] != "active":
                continue
            achieved = False
            if goal["type"] == "position":
                achieved = user_position <= goal["target"]
            elif goal["type"] == "goals_scored":
                achieved = total_goals >= goal["target"]
            elif goal["type"] == "max_consecutive_losses":
                achieved = max_consecutive <= goal["target"]

            if achieved:
                goal["status"] = "completed"
                if self.user_team:
                    self.user_team.budget += goal["reward_budget"]
                self.manager_reputation = min(100, self.manager_reputation + goal["reward_reputation"])
                self.board_confidence = min(100, self.board_confidence + 5)
                headlines.append(f"✅ Obiettivo raggiunto: {goal['description']} (+{goal['reward_budget']} budget)")
            else:
                goal["status"] = "failed"
                self.board_confidence = max(0, self.board_confidence - 5)
                if self.user_team:
                    self.user_team.budget = max(0, self.user_team.budget - 50)
                headlines.append(f"❌ Obiettivo mancato: {goal['description']}")
        return headlines

    def start_new_season(self) -> bool:
        """Advance the career after the current championship is complete."""
        if self.get_next_match() is not None:
            return False

        # --- Playoff scudetto (top 4 teams) ---
        from src.season import (
            Standings, generate_playoff_bracket, simulate_playoff,
            generate_playoff_headlines,
        )
        standings = Standings()
        for m in self._played_matches_history:
            standings.update(m)
        try:
            bracket = generate_playoff_bracket(self.teams, standings)
            playoff_winner = simulate_playoff(bracket, seed=self.season_number * 100)
            self.career_news.insert(0, f"🏆 Playoff: {playoff_winner.name} vince lo scudetto!")
            if playoff_winner == self.user_team:
                self.manager_reputation = min(100, self.manager_reputation + 5)
                self.board_confidence = min(100, self.board_confidence + 10)
                self.supporters += 200
            # Feature 1: Integra le headline narrative dei playoff
            for headline in generate_playoff_headlines(bracket):
                self.career_news.insert(0, headline)
        except Exception:
            pass  # Not enough teams for playoff

        # --- Coppa Nazionale ---
        from src.season import (
            generate_cup_bracket, simulate_cup, generate_cup_headlines,
        )
        try:
            cup_bracket = generate_cup_bracket(self.teams)
            cup_winner = simulate_cup(cup_bracket, seed=self.season_number * 200)
            if cup_winner:
                self.career_news.insert(0, f"️ Coppa Nazionale: {cup_winner.name} vince!")
                if cup_winner == self.user_team:
                    self.manager_reputation = min(100, self.manager_reputation + 3)
                    self.supporters += 100
                # Feature 1: Integra le headline narrative della coppa
                for headline in generate_cup_headlines(cup_bracket):
                    self.career_news.insert(0, headline)
        except Exception:
            pass  # Not enough teams for cup

        prize = max(100, 700 - self.get_standings().index(self.user_team) * 80)
        for team in self.teams:
            team.points = team.goals_for = team.goals_against = 0
            team.wins = team.draws = team.losses = 0
            for player in team.players:
                season_aging(player)
                age_player_one_year(player)
                player.contract_years = max(0, player.contract_years - 1)
                if player.contract_years == 0:
                    player.happiness = max(0, player.happiness - 10)
                player.appearances = 0
                player.goals = 0
        if self.user_team:
            self.user_team.budget += prize
            expired = [
                player.name for player in self.user_team.players
                if player.contract_years == 0
            ]
            if expired:
                self.career_news.insert(
                    0,
                    "⚠️ Contratti scaduti: " + ", ".join(expired[:4]),
                )
        self.season_number += 1
        self.current_round = 0
        self.trainings_used = 0
        self.calendar = generate_calendar(self.teams, self.user_team_idx)
        self.free_agents = generate_free_agents(8)
        self._played_matches_history = []
        self.season_objective = (
            "Vincere il campionato" if self.manager_reputation >= 75
            else "Qualificazione playoff"
        )
        # Evaluate previous season goals
        goal_headlines = self._evaluate_season_goals()
        for headline in goal_headlines:
            self.career_news.insert(0, headline)
        # Generate new season goals
        self.season_goals = self._generate_season_goals()
        for goal in self.season_goals:
            self.career_news.insert(0, f"🎯 Nuovo obiettivo: {goal['description']}")
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

    def negotiate_transfer(
        self,
        player: Player,
        fee: int,
        wage: int,
        years: int,
        squad_role: str = "Rotazione",
    ) -> tuple[bool, str]:
        """Negotiate and complete an incoming transfer."""
        team = self.user_team
        if not team:
            return False, "Nessuna squadra selezionata."
        if len(team.players) >= 24:
            return False, "Rosa completa: vendi un giocatore prima di acquistare."
        total_cost = fee + wage * years
        if team.budget < total_cost:
            return False, f"Servono {total_cost} crediti tra cartellino e bonus."
        accepted, message = evaluate_transfer_offer(
            player, fee, wage, years, squad_role,
        )
        if not accepted:
            player.happiness = max(0, player.happiness - 2)
            return False, message

        source_team = next(
            (
                other for other in self.teams
                if other is not team and player in other.players
            ),
            None,
        )
        if source_team:
            source_team.players.remove(player)
            source_team.budget += fee
        player.wage = wage
        player.contract_years = years
        player.squad_role = squad_role
        player.happiness = min(100, player.happiness + 8)
        team.players.append(player)
        team.budget -= total_cost
        if player in self.free_agents:
            self.free_agents.remove(player)
        self.career_news.insert(
            0,
            f"Nuovo acquisto: {player.name} per {fee}, contratto di {years} anni.",
        )
        self.career_news = self.career_news[:6]
        self.save_game()
        return True, "Trasferimento completato."

    def buy_player(self, player: Player) -> bool:
        """Backward-compatible purchase using a fair default proposal."""
        role = "Rotazione"
        accepted, _message = self.negotiate_transfer(
            player,
            player_price(player),
            minimum_wage(player, role),
            3,
            role,
        )
        return accepted

    def sell_player(self, player: Player, interest: int = 75) -> tuple[bool, str, int]:
        """Accept an external offer for a squad player."""
        team = self.user_team
        if not team or player not in team.players:
            return False, "Giocatore non disponibile.", 0
        if len(team.players) <= 12:
            return False, "La rosa non può scendere sotto 12 giocatori.", 0
        fee = incoming_offer_value(player, interest)
        team.players.remove(player)
        team.budget += fee
        player.squad_role = "Rotazione"
        player.happiness = 60
        if player not in self.free_agents:
            self.free_agents.append(player)
        self.career_news.insert(0, f"Cessione: {player.name} per {fee} crediti.")
        self.career_news = self.career_news[:6]
        self.save_game()
        return True, "Offerta accettata.", fee

    def get_transfer_targets(self) -> list[Player]:
        """Return free agents plus realistic targets from AI-controlled clubs."""
        targets = list(self.free_agents)
        for team in self.teams:
            if team is self.user_team or len(team.players) <= 12:
                continue
            available = sorted(
                team.players,
                key=lambda player: (
                    player.squad_role == "Chiave",
                    -player.happiness,
                    player.contract_years,
                ),
            )
            targets.extend(available[:2])
        return targets

    def get_player_club(self, player: Player) -> str:
        for team in self.teams:
            if player in team.players:
                return team.name
        return "Svincolato"

    def get_player_price(self, player: Player) -> int:
        return player_price(player)

    def get_incoming_offer(self, player: Player) -> int:
        interest = 70 + max(-10, min(20, (player.form - 50) // 2))
        return incoming_offer_value(player, interest)

    def save_game(self, slot: int = 1):
        """Save current game state to a save slot (1-3)."""
        if not self.db:
            return
        for team in self.teams:
            self.db.save_team(team)
        state = {
            "current_round": self.current_round,
            "trainings_used": self.trainings_used,
            "season_number": self.season_number,
            "manager_reputation": self.manager_reputation,
            "board_confidence": self.board_confidence,
            "supporters": self.supporters,
            "season_objective": self.season_objective,
            "career_news": self.career_news,
            "user_team_name": self.user_team.name if self.user_team else "—",
            "league_name": "Serie A Élite",
            "season_goals": self.season_goals,
        }
        self.db.save_state(state)
        # Also persist to save_slots table for multi-slot save/load
        self.db.save_game(slot, state)

    def load_game_slot(self, slot: int) -> bool:
        """Load a game from a save slot (1-3). Returns True on success."""
        if not self.db:
            return False
        state = self.db.load_game(slot)
        if state is None:
            return False
        # Restore teams from database
        saved_teams = self.db.load_all_teams()
        if saved_teams and len(saved_teams) == len(self.teams):
            by_name = {team.name: team for team in saved_teams}
            self.teams = [by_name.get(team.name, team) for team in self.teams]
        user_team_name = state.get("user_team_name")
        if user_team_name:
            for i, t in enumerate(self.teams):
                if t.name == user_team_name:
                    self.user_team = t
                    self.user_team_idx = i
                    break
        self.current_round = int(state.get("current_round", 0))
        self.trainings_used = int(state.get("trainings_used", 0))
        self.season_number = int(state.get("season_number", 1))
        self.manager_reputation = int(state.get("manager_reputation", 50))
        self.board_confidence = int(state.get("board_confidence", 65))
        self.supporters = int(state.get("supporters", 1200))
        self.season_objective = state.get("season_objective", "Qualificazione playoff")
        self.career_news = state.get("career_news", ["Benvenuto nella tua nuova carriera da manager."])
        self.season_goals = state.get("season_goals", [])
        self.calendar = generate_calendar(self.teams, self.user_team_idx)
        self._played_matches_history = []
        return True

    def list_save_slots(self) -> list[dict]:
        """Return metadata for all occupied save slots."""
        if not self.db:
            return []
        return self.db.list_saves()

    def delete_save_slot(self, slot: int) -> bool:
        """Delete a save slot. Returns True if deleted."""
        if not self.db:
            return False
        return self.db.delete_save(slot)
