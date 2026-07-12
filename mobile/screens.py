"""Kivy screens for Field Hockey Manager mobile UI."""
from __future__ import annotations
import os
import sys

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.models import Player, Team, Match, Position
from src.season import (
    TRAINING_ATTRIBUTES, MAX_TRAININGS_PER_WEEK,
    generate_youth_prospects, promote_youth_player,
)

from mobile.widgets import (
    BG_COLOR, ACCENT_COLOR, TEXT_COLOR, CARD_COLOR,
    PlayerCard, MatchResult, RatingBar, BannerLabel,
    pos_color, POS_EMOJI, rating_to_color,
)

ATTR_LABELS = {
    "passing": "Passaggio", "shooting": "Tiro", "defense": "Difesa",
    "speed": "Velocità", "stamina": "Resistenza",
}


def make_screen_bg(widget):
    with widget.canvas.before:
        Color(*BG_COLOR)
        RoundedRectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda inst, v: _update_bg_rect(inst), size=lambda inst, v: _update_bg_rect(inst))


def _update_bg_rect(widget):
    """Redraw the background rectangle after a layout change."""
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*BG_COLOR)
        RoundedRectangle(pos=widget.pos, size=widget.size)


def styled_button(text, callback, bg_color=None, height=52):
    btn = Button(
        text=text, font_size="16sp", size_hint_y=None, height=height,
        background_color=bg_color or ACCENT_COLOR, color=TEXT_COLOR,
    )
    btn.bind(on_press=callback)
    return btn


def section_title(text):
    return Label(
        text=text, font_size="20sp", bold=True, color=ACCENT_COLOR,
        size_hint_y=None, height=44,
    )


# ── Menu ────────────────────────────────────────────────────────

class MenuScreen(Screen):
    """Adaptive career dashboard for desktop and mobile layouts."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)

        self.scroll = ScrollView(do_scroll_x=False)
        self.content = BoxLayout(
            orientation="vertical", padding=18, spacing=12,
            size_hint_y=None,
        )
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        self.add_widget(self.scroll)
        Window.bind(size=self._on_window_size)

    def _card(self, title, value, subtitle="", accent=None):
        card = BoxLayout(
            orientation="vertical", padding=12, spacing=2,
            size_hint_y=None, height=92,
        )
        with card.canvas.before:
            Color(*(accent or CARD_COLOR))
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[10])
        card.bind(
            pos=lambda inst, _v: setattr(inst._bg, "pos", inst.pos),
            size=lambda inst, _v: setattr(inst._bg, "size", inst.size),
        )
        card.add_widget(Label(
            text=title.upper(), font_size="11sp", bold=True,
            color=(0.60, 0.68, 0.78, 1), halign="left",
            text_size=(None, None),
        ))
        card.add_widget(Label(
            text=str(value), font_size="22sp", bold=True,
            color=TEXT_COLOR, halign="left",
        ))
        if subtitle:
            card.add_widget(Label(
                text=subtitle, font_size="11sp",
                color=(0.68, 0.74, 0.82, 1), halign="left",
            ))
        return card

    def _action(self, text, screen, primary=False):
        color = ACCENT_COLOR if primary else (0.16, 0.21, 0.31, 1)
        return styled_button(
            text, lambda _btn, target=screen: setattr(self.app.sm, "current", target),
            bg_color=color, height=54,
        )

    def _on_window_size(self, *_args):
        if self.manager:
            self.refresh()

    def on_enter(self):
        self.refresh()

    def refresh(self):
        self.content.clear_widgets()
        app = self.app
        team = app.user_team
        team_name = team.name if team else "Nessuna squadra"
        budget = getattr(team, "budget", 0) if team else 0
        standings = app.get_standings() if team else []
        position = standings.index(team) + 1 if team in standings else "-"
        compact = Window.width < 760

        header = BoxLayout(
            orientation="vertical" if compact else "horizontal",
            size_hint_y=None, height=118 if compact else 82, spacing=8,
        )
        identity = BoxLayout(orientation="vertical")
        identity.add_widget(Label(
            text="[b]FIELD HOCKEY MANAGER[/b]", markup=True,
            font_size="25sp", color=ACCENT_COLOR,
            halign="left", valign="middle",
        ))
        identity.add_widget(Label(
            text=f"{team_name}  •  Stagione {app.season_number}",
            font_size="14sp", color=TEXT_COLOR, halign="left",
        ))
        header.add_widget(identity)
        header.add_widget(styled_button(
            "🏒 GIOCA PROSSIMA PARTITA",
            lambda _btn: setattr(app.sm, "current", "partita"),
            bg_color=(0.08, 0.55, 0.34, 1), height=56,
        ))
        self.content.add_widget(header)

        kpis = GridLayout(
            cols=2 if compact else 4, spacing=8,
            size_hint_y=None, height=192 if compact else 92,
        )
        kpis.add_widget(self._card("Classifica", f"{position}°", "posizione attuale"))
        payroll = team.payroll_per_round() if team else 0
        expiring = sum(
            1 for player in (team.players if team else [])
            if player.contract_years <= 1
        )
        kpis.add_widget(self._card(
            "Budget", f"{budget:,}",
            f"Stipendi turno {payroll} · {expiring} in scadenza",
        ))
        kpis.add_widget(self._card("Fiducia", f"{app.board_confidence}%", "dirigenza"))
        kpis.add_widget(self._card("Reputazione", f"{app.manager_reputation}%", "manager"))
        self.content.add_widget(kpis)

        overview = GridLayout(
            cols=1 if compact else 3, spacing=10,
            size_hint_y=None, height=300 if compact else 176,
        )
        overview.add_widget(self._card(
            "Prossima partita", app.next_match_info(),
            f"Turno {app.current_round + 1}",
            accent=(0.12, 0.22, 0.34, 1),
        ))
        latest_news = app.career_news[0] if app.career_news else "Nessuna notizia"
        overview.add_widget(self._card(
            "Notizie dal club", latest_news,
            f"{app.supporters:,} sostenitori",
            accent=(0.23, 0.17, 0.12, 1),
        ))
        squad = team.players if team else []
        injured = [player for player in squad if player.injured]
        avg_condition = (
            round(sum(player.condition for player in squad) / len(squad))
            if squad else 0
        )
        medical_value = (
            f"{len(injured)} indisponibili" if injured else "Rosa disponibile"
        )
        overview.add_widget(self._card(
            "Centro medico", medical_value,
            f"Condizione media {avg_condition}%",
            accent=(0.16, 0.24, 0.18, 1) if not injured else (0.34, 0.15, 0.16, 1),
        ))
        self.content.add_widget(overview)

        self.content.add_widget(section_title("Centro manageriale"))
        actions = GridLayout(
            cols=2 if compact else 4, spacing=8,
            size_hint_y=None, height=340 if compact else 174,
        )
        for label, target in [
            ("💼 Carriera", "carriera"), ("🥅 Rosa", "rosa"),
            ("📋 Tattiche e partita", "partita"), ("🏋 Allenamenti", "allenamenti"),
            ("📅 Calendario", "calendario"), ("🏆 Classifica", "classifica"),
            ("📊 Statistiche", "statistiche"), ("💰 Mercato", "mercato"),
            ("🌱 Vivaio", "youth"), ("📑 Contratti", "contratti"),
            ("💾 Salva / Carica", "saveload"),
        ]:
            actions.add_widget(self._action(label, target))
        self.content.add_widget(actions)

        exit_row = BoxLayout(size_hint_y=None, height=48)
        exit_row.add_widget(styled_button(
            "Esci dal gioco", lambda _btn: app.stop(),
            bg_color=(0.42, 0.16, 0.18, 1), height=44,
        ))
        self.content.add_widget(exit_row)


# ── Contracts ───────────────────────────────────────────────────

class ContractsScreen(Screen):
    """Manage renewals, wages and promised squad roles."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        layout = BoxLayout(orientation="vertical", padding=18, spacing=10)
        layout.add_widget(section_title("📑 Contratti e spogliatoio"))

        self.summary = Label(
            text="", font_size="14sp", color=TEXT_COLOR,
            size_hint_y=None, height=62, halign="left", valign="middle",
        )
        self.summary.bind(
            size=lambda inst, _value=None: setattr(inst, "text_size", inst.size)
        )
        layout.add_widget(self.summary)

        self.player_spinner = Spinner(
            text="Seleziona giocatore", values=[],
            size_hint_y=None, height=48, font_size="15sp",
        )
        self.player_spinner.bind(text=self._refresh_player_info)
        layout.add_widget(self.player_spinner)

        self.player_info = Label(
            text="", font_size="14sp", color=(0.72, 0.80, 0.90, 1),
            size_hint_y=None, height=76,
        )
        layout.add_widget(self.player_info)

        offers = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=48, spacing=8,
        )
        self.years_spinner = Spinner(
            text="3 anni", values=[f"{year} anni" for year in range(1, 6)],
        )
        self.wage_spinner = Spinner(
            text="5", values=[str(value) for value in range(1, 16)],
        )
        offers.add_widget(self.years_spinner)
        offers.add_widget(self.wage_spinner)
        layout.add_widget(offers)

        layout.add_widget(Label(
            text="Durata proposta                         Stipendio per turno",
            font_size="12sp", color=(0.62, 0.68, 0.76, 1),
            size_hint_y=None, height=26,
        ))
        layout.add_widget(styled_button(
            "Proponi rinnovo", self._renew,
            bg_color=(0.08, 0.55, 0.34, 1),
        ))
        self.result = Label(
            text="", font_size="14sp", color=TEXT_COLOR,
            size_hint_y=None, height=70,
        )
        layout.add_widget(self.result)
        layout.add_widget(styled_button(
            "⬅️ Indietro", lambda _btn: setattr(app.sm, "current", "menu"),
        ))
        self.add_widget(layout)

    def on_enter(self):
        team = self.app.user_team
        players = team.players if team else []
        self.player_spinner.values = [player.name for player in players]
        payroll = team.payroll_per_round() if team else 0
        expiring = sum(1 for player in players if player.contract_years <= 1)
        self.summary.text = (
            f"Budget: {getattr(team, 'budget', 0)}  •  Monte stipendi: {payroll} per turno\n"
            f"Contratti in scadenza: {expiring}"
        )
        if players and self.player_spinner.text not in self.player_spinner.values:
            self.player_spinner.text = players[0].name
        self._refresh_player_info()
        self.result.text = ""

    def _selected_player(self):
        team = self.app.user_team
        if not team:
            return None
        return next(
            (player for player in team.players if player.name == self.player_spinner.text),
            None,
        )

    def _refresh_player_info(self, *_args):
        player = self._selected_player()
        if not player:
            self.player_info.text = ""
            return
        self.player_info.text = (
            f"{player.squad_role}  •  Felicità {player.happiness}\n"
            f"Contratto {player.contract_years} anni  •  Stipendio {player.wage}"
        )
        self.wage_spinner.text = str(min(15, max(1, player.wage + 1)))

    def _renew(self, _btn):
        player = self._selected_player()
        team = self.app.user_team
        if not player or not team:
            return
        years = int(self.years_spinner.text.split()[0])
        wage = int(self.wage_spinner.text)
        signing_bonus = wage * years
        if team.budget < signing_bonus:
            self.result.text = "❌ Budget insufficiente per il bonus alla firma."
            self.result.color = (0.86, 0.2, 0.2, 1)
            return
        if not player.renew_contract(years, wage):
            self.result.text = "❌ Offerta rifiutata: stipendio non adeguato al ruolo."
            self.result.color = (0.86, 0.2, 0.2, 1)
            self._refresh_player_info()
            return
        team.budget -= signing_bonus
        self.app.save_game()
        self.on_enter()
        self.result.text = (
            f"✅ Rinnovo firmato per {years} anni. Bonus alla firma: {signing_bonus}."
        )
        self.result.color = (0.2, 0.78, 0.35, 1)


# ── Save / Load ───────────────────────────────────────────────

class SaveLoadScreen(Screen):
    """Screen for managing 3 save slots."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("💾 Salva / Carica"))

        self.scroll = ScrollView(size_hint_y=0.80)
        self.slots_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=10)
        self.slots_layout.bind(minimum_height=self.slots_layout.setter("height"))
        self.scroll.add_widget(self.slots_layout)
        self.layout.add_widget(self.scroll)

        self.layout.add_widget(styled_button("⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        """Refresh slot list when entering the screen."""
        self.slots_layout.clear_widgets()
        saves = {s["slot"]: s for s in self.app.list_save_slots()}

        for slot in (1, 2, 3):
            info = saves.get(slot)
            box = BoxLayout(orientation="horizontal", size_hint_y=None, height=70, spacing=6)

            if info:
                label = Label(
                    text=f"Slot {slot}: {info['team_name']} - Stagione {info['season']}\n{info['timestamp']}",
                    font_size="13sp", color=TEXT_COLOR, halign="left", valign="middle",
                    size_hint_x=0.50,
                )
                label.bind(size=lambda inst, v: setattr(inst, "text_size", (inst.width, None)))
                box.add_widget(label)
                box.add_widget(styled_button("💾 Salva", lambda _, s=slot: self._save_slot(s), height=40, bg_color=(0.2, 0.5, 0.8, 1)))
                box.add_widget(styled_button("📂 Carica", lambda _, s=slot: self._load_slot(s), height=40, bg_color=(0.2, 0.7, 0.3, 1)))
                box.add_widget(styled_button("🗑️", lambda _, s=slot: self._delete_slot(s), height=40, bg_color=(0.7, 0.2, 0.2, 1)))
            else:
                label = Label(
                    text=f"Slot {slot}: <vuoto>",
                    font_size="14sp", color=(0.5, 0.5, 0.6, 1), halign="left", valign="middle",
                    size_hint_x=0.50,
                )
                label.bind(size=lambda inst, v: setattr(inst, "text_size", (inst.width, None)))
                box.add_widget(label)
                box.add_widget(styled_button("💾 Salva", lambda _, s=slot: self._save_slot(s), height=40))
                # Empty slot buttons take same space for alignment
                box.add_widget(Label(text="", size_hint_x=0.25))
                box.add_widget(Label(text="", size_hint_x=0.10))

            self.slots_layout.add_widget(box)

    def _save_slot(self, slot: int):
        self.app.save_game(slot)
        self.on_enter()  # refresh

    def _load_slot(self, slot: int):
        if self.app.load_game_slot(slot):
            self.app.sm.current = "menu"

    def _delete_slot(self, slot: int):
        self.app.delete_save_slot(slot)
        self.on_enter()  # refresh


# ── Rosa ────────────────────────────────────────────────────────

class RosaScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("🥅 Rosa Squadra"))

        self.scroll = ScrollView(size_hint_y=0.85)
        self.list_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        self.layout.add_widget(self.scroll)
        self.layout.add_widget(styled_button("⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        self.list_layout.clear_widgets()
        team = self.app.user_team
        if not team:
            return
        for p in team.players:
            self.list_layout.add_widget(PlayerCard(p))


# ── Calendario ─────────────────────────────────────────────────

class CalendarioScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("📅 Calendario"))

        self.scroll = ScrollView(size_hint_y=0.85)
        self.list_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        self.layout.add_widget(self.scroll)
        self.layout.add_widget(styled_button("⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        self.list_layout.clear_widgets()
        user_name = self.app.user_team.name if self.app.user_team else ""
        for entry in self.app.calendar:
            home = self.app.teams[entry["home"]]
            away = self.app.teams[entry["away"]]
            played = entry["round"] < self.app.current_round
            home_score = getattr(entry, 'home_score', 0) if played else 0
            away_score = getattr(entry, 'away_score', 0) if played else 0
            is_user = user_name in (home.name, away.name)
            # Feature 2: Highlight derby matches with 🔥
            is_derby = away.name in (home.rivals or [])
            row = MatchResult(
                home.name, away.name, home_score, away_score, played, is_user,
            )
            if is_derby:
                # Prepend fire emoji to the row label for derby visibility
                derby_label = Label(
                    text="🔥 Derby", font_size="12sp", color=(0.95, 0.4, 0.1, 1),
                    size_hint_y=None, height=18,
                )
                self.list_layout.add_widget(derby_label)
            self.list_layout.add_widget(row)


# ── Classifica ──────────────────────────────────────────────────

class ClassificaScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("🏆 Classifica"))

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=32)
        for h in ["Squadra", "Pt", "V", "P", "S", "GF", "GS"]:
            header.add_widget(Label(text=h, font_size="13sp", bold=True, color=ACCENT_COLOR))
        self.layout.add_widget(header)

        self.scroll = ScrollView(size_hint_y=0.78)
        self.list_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=3)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        self.layout.add_widget(self.scroll)
        self.layout.add_widget(styled_button("⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        self.list_layout.clear_widgets()
        standings = self.app.get_standings()
        user_name = self.app.user_team.name if self.app.user_team else ""
        for team in standings:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=30)
            is_user = team.name == user_name
            bg = ACCENT_COLOR if is_user else CARD_COLOR
            with row.canvas.before:
                Color(*bg)
                RoundedRectangle(pos=row.pos, size=row.size, radius=[4])
            row.bind(pos=lambda inst, v: _update_bg_rect(inst), size=lambda inst, v: _update_bg_rect(inst))
            row.add_widget(Label(text=team.name[:14], font_size="13sp", color=TEXT_COLOR))
            row.add_widget(Label(text=str(team.points), font_size="13sp", color=TEXT_COLOR))
            row.add_widget(Label(text=str(team.wins), font_size="13sp", color=TEXT_COLOR))
            row.add_widget(Label(text=str(team.draws), font_size="13sp", color=TEXT_COLOR))
            row.add_widget(Label(text=str(team.losses), font_size="13sp", color=TEXT_COLOR))
            row.add_widget(Label(text=str(team.goals_for), font_size="13sp", color=TEXT_COLOR))
            row.add_widget(Label(text=str(team.goals_against), font_size="13sp", color=TEXT_COLOR))
            self.list_layout.add_widget(row)


# ── Partita ─────────────────────────────────────────────────────

class PartitaScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=10)
        self.layout.add_widget(section_title("⚽ Gioca Partita"))

        self.info_label = Label(text="", font_size="16sp", color=TEXT_COLOR, size_hint_y=None, height=40)
        self.layout.add_widget(self.info_label)

        self.formation_spinner = Spinner(
            text="4-3-3", values=["4-3-3", "4-4-2", "3-5-2", "5-3-2"],
            size_hint_y=None, height=44, font_size="16sp",
        )
        self.layout.add_widget(Label(text="Formazione:", font_size="14sp", color=TEXT_COLOR, size_hint_y=None, height=28))
        self.layout.add_widget(self.formation_spinner)

        self.intensity_spinner = Spinner(
            text="Bilanciata", values=["Difensiva", "Bilanciata", "Offensiva"],
            size_hint_y=None, height=44, font_size="16sp",
        )
        self.layout.add_widget(Label(text="Intensità:", font_size="14sp", color=TEXT_COLOR, size_hint_y=None, height=28))
        self.layout.add_widget(self.intensity_spinner)

        # --- Substitution selection (C3) ---
        self.subs_label = Label(
            text="Sostituzioni (max 3, opzionale):",
            font_size="14sp", color=TEXT_COLOR, size_hint_y=None, height=28,
        )
        self.layout.add_widget(self.subs_label)
        self.sub_spinners: list[Spinner] = []
        for i in range(3):
            sub_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=44, spacing=4)
            out_spin = Spinner(text="-", values=[], size_hint_x=0.5, font_size="13sp")
            in_spin = Spinner(text="-", values=[], size_hint_x=0.5, font_size="13sp")
            self.sub_spinners.append(out_spin)
            self.sub_spinners.append(in_spin)
            sub_row.add_widget(Label(text="Out:", font_size="12sp", color=(0.86,0.2,0.2,1), size_hint_x=0.15))
            sub_row.add_widget(out_spin)
            sub_row.add_widget(Label(text="In:", font_size="12sp", color=(0.2,0.78,0.35,1), size_hint_x=0.15))
            sub_row.add_widget(in_spin)
            self.layout.add_widget(sub_row)

        self.play_btn = styled_button("🏒 Simula Partita", self._play_match)
        self.layout.add_widget(self.play_btn)

        self.result_label = Label(text="", font_size="18sp", bold=True, color=TEXT_COLOR, size_hint_y=None, height=40)
        self.layout.add_widget(self.result_label)

        # 2D match field widget
        from mobile.widgets import MatchFieldWidget
        self.field_widget = MatchFieldWidget(size_hint_y=0.45)
        self.layout.add_widget(self.field_widget)

        # Speed controls
        speed_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=6)
        self.pause_btn = styled_button("⏸️ Pausa", self._toggle_pause)
        self.speed_1x = styled_button("1x", lambda _: self._set_speed(1.0))
        self.speed_2x = styled_button("2x", lambda _: self._set_speed(2.0))
        self.speed_4x = styled_button("4x", lambda _: self._set_speed(4.0))
        self.skip_btn = styled_button("⏭️ Salta", self._skip_to_end)
        speed_row.add_widget(self.pause_btn)
        speed_row.add_widget(self.speed_1x)
        speed_row.add_widget(self.speed_2x)
        speed_row.add_widget(self.speed_4x)
        speed_row.add_widget(self.skip_btn)
        self.layout.add_widget(speed_row)

        # Commentary feed
        self.commentary_label = Label(
            text="", font_size="12sp", color=(0.85, 0.9, 0.95, 1),
            size_hint_y=None, height=100, valign="top", halign="left",
        )
        self.commentary_label.bind(size=lambda inst, _value=None: setattr(inst, "text_size", inst.size))
        self.layout.add_widget(self.commentary_label)

        self.layout.add_widget(styled_button("⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        entry = self.app.get_next_match()
        if entry:
            home = self.app.teams[entry["home"]]
            away = self.app.teams[entry["away"]]
            self.info_label.text = f"{home.name} vs {away.name}"
            self.play_btn.disabled = False
            # Populate substitution spinners with squad players
            team = self.app.user_team
            if team:
                player_names = [p.name for p in team.players if p.can_play()]
                for spin in self.sub_spinners:
                    spin.values = ["-"] + player_names
                    spin.text = "-"
        else:
            self.info_label.text = "Stagione finita! 🎉"
            self.play_btn.disabled = True
        self.result_label.text = ""
        self.commentary_label.text = ""
        self.field_widget.canvas.clear()

    def _play_match(self, _):
        # Collect user-chosen substitutions (pairs: out, in)
        user_subs: list[dict] = []
        for i in range(0, len(self.sub_spinners), 2):
            out_name = self.sub_spinners[i].text
            in_name = self.sub_spinners[i + 1].text
            if out_name != "-" and in_name != "-":
                user_subs.append({"quarter": 3, "out": out_name, "in": in_name})
        match = self.app.play_next_match(
            self.formation_spinner.text,
            self.intensity_spinner.text,
            user_subs=user_subs or None,
        )
        if not match:
            return
        c = (0.2, 0.78, 0.35, 1) if match.home_score > match.away_score else (
            (0.86, 0.2, 0.2, 1) if match.home_score < match.away_score else (0.95, 0.83, 0.2, 1)
        )
        self.result_label.text = f"{match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}"
        self.result_label.color = c

        # Generate 2D timeline and start animation
        from src.simulation import generate_match_timeline, generate_commentary
        timeline = generate_match_timeline(match)
        self.field_widget.set_match(match, timeline)
        self.field_widget.start_animation()

        # Generate commentary feed
        is_derby = match.away_team.name in (match.home_team.rivals or [])
        comments = []
        for ev in match.events:
            comments.append(generate_commentary(match, ev, derby=is_derby))
        self.commentary_label.text = "\n".join(comments) if comments else "Nessun evento"

    def _toggle_pause(self, _):
        if self.field_widget.paused:
            self.field_widget.resume()
            self.pause_btn.text = "⏸️ Pausa"
        else:
            self.field_widget.pause()
            self.pause_btn.text = "▶️ Riprendi"

    def _set_speed(self, speed):
        self.field_widget.set_speed(speed)

    def _skip_to_end(self, _):
        self.field_widget.stop_animation()
        self.field_widget.match_time = 60.0
        if self.field_widget.timeline:
            self.field_widget._apply_frame(self.field_widget.timeline[-1])
        self.field_widget._redraw()


# ── Statistiche ─────────────────────────────────────────────────

class StatisticheScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("📊 Statistiche"))

        self.scroll = ScrollView(size_hint_y=0.82)
        self.list_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=8)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        self.layout.add_widget(self.scroll)
        self.layout.add_widget(styled_button("⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        self.list_layout.clear_widgets()
        team = self.app.user_team
        if not team:
            return
        scorer = max(team.players, key=lambda p: p.goals) if team.players else None
        if scorer and scorer.goals > 0:
            self.list_layout.add_widget(Label(
                text=f"⚽ Capocannoniere: {scorer.name} ({scorer.goals} gol)",
                font_size="15sp", color=TEXT_COLOR, size_hint_y=None, height=36,
            ))
        most_apps = max(team.players, key=lambda p: p.appearances) if team.players else None
        if most_apps:
            self.list_layout.add_widget(Label(
                text=f"📊 Più presenze: {most_apps.name} ({most_apps.appearances})",
                font_size="15sp", color=TEXT_COLOR, size_hint_y=None, height=36,
            ))
        avg = sum(p.overall_rating() for p in team.players) / len(team.players) if team.players else 0
        self.list_layout.add_widget(Label(
            text=f"📈 Rating medio: {avg:.1f}",
            font_size="15sp", color=TEXT_COLOR, size_hint_y=None, height=36,
        ))
        self.list_layout.add_widget(Label(
            text=f"🏆 Punti: {team.points} | V:{team.wins} P:{team.draws} S:{team.losses}",
            font_size="15sp", color=TEXT_COLOR, size_hint_y=None, height=36,
        ))
        self.list_layout.add_widget(Label(
            text=f"🥅 Gol fatti: {team.goals_for} | Gol subiti: {team.goals_against}",
            font_size="15sp", color=TEXT_COLOR, size_hint_y=None, height=36,
        ))


# ── Allenamenti ─────────────────────────────────────────────────

class AllenamentiScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("🏋️ Allenamenti"))

        self.info_label = Label(text="", font_size="14sp", color=TEXT_COLOR, size_hint_y=None, height=30)
        self.layout.add_widget(self.info_label)

        self.attr_spinner = Spinner(
            text="Passaggio",
            values=[ATTR_LABELS[a] for a in TRAINING_ATTRIBUTES],
            size_hint_y=None, height=44, font_size="16sp",
        )
        self.layout.add_widget(Label(text="Attributo:", font_size="14sp", color=TEXT_COLOR, size_hint_y=None, height=28))
        self.layout.add_widget(self.attr_spinner)

        self.player_spinner = Spinner(
            text="", values=[], size_hint_y=None, height=44, font_size="16sp",
        )
        self.layout.add_widget(Label(text="Giocatore:", font_size="14sp", color=TEXT_COLOR, size_hint_y=None, height=28))
        self.layout.add_widget(self.player_spinner)

        self.train_btn = styled_button("🏋️ Allena", self._train)
        self.layout.add_widget(self.train_btn)

        self.result_label = Label(text="", font_size="14sp", color=(0.2, 0.78, 0.35, 1), size_hint_y=None, height=36)
        self.layout.add_widget(self.result_label)

        self.layout.add_widget(styled_button("⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        team = self.app.user_team
        if team:
            self.player_spinner.values = [p.name for p in team.players]
            self.player_spinner.text = self.player_spinner.values[0] if self.player_spinner.values else ""
            remaining = MAX_TRAININGS_PER_WEEK - self.app.trainings_used
            self.info_label.text = f"Allenamenti rimasti: {remaining}/{MAX_TRAININGS_PER_WEEK}"
        self.result_label.text = ""

    def _train(self, _):
        team = self.app.user_team
        if not team:
            return
        label_to_attr = {v: k for k, v in ATTR_LABELS.items()}
        attr = label_to_attr.get(self.attr_spinner.text, "passing")
        player_name = self.player_spinner.text
        player = next((p for p in team.players if p.name == player_name), None)
        if not player:
            return
        msg = self.app.train_player_attr(player, attr)
        self.result_label.text = msg
        remaining = MAX_TRAININGS_PER_WEEK - self.app.trainings_used
        self.info_label.text = f"Allenamenti rimasti: {remaining}/{MAX_TRAININGS_PER_WEEK}"


# ── Mercato ─────────────────────────────────────────────────────

class MercatoScreen(Screen):
    """Transfer hub with negotiations, wages and outgoing offers."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.selected_target = None
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=14, spacing=7)
        self.layout.add_widget(section_title("💰 Centro trasferimenti"))

        self.budget_label = Label(
            text="", font_size="15sp", color=(0.95, 0.83, 0.2, 1),
            size_hint_y=None, height=34,
        )
        self.layout.add_widget(self.budget_label)

        self.scroll = ScrollView(size_hint_y=0.38)
        self.list_layout = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=5,
        )
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        self.layout.add_widget(self.scroll)

        self.target_label = Label(
            text="Seleziona un obiettivo", font_size="13sp", color=TEXT_COLOR,
            size_hint_y=None, height=42,
        )
        self.layout.add_widget(self.target_label)

        offer_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=44, spacing=5,
        )
        self.fee_spinner = Spinner(text="Cartellino", values=[])
        self.wage_spinner = Spinner(
            text="Stipendio", values=[str(value) for value in range(1, 16)],
        )
        self.years_spinner = Spinner(
            text="3 anni", values=[f"{value} anni" for value in range(1, 6)],
        )
        self.role_spinner = Spinner(
            text="Rotazione",
            values=["Chiave", "Titolare", "Rotazione", "Prospetto"],
        )
        for widget in (
            self.fee_spinner, self.wage_spinner,
            self.years_spinner, self.role_spinner,
        ):
            offer_row.add_widget(widget)
        self.layout.add_widget(offer_row)
        self.layout.add_widget(styled_button(
            "Invia offerta", self._submit_offer,
            bg_color=(0.08, 0.55, 0.34, 1), height=46,
        ))

        sale_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=46, spacing=6,
        )
        self.sale_spinner = Spinner(text="Scegli giocatore da cedere", values=[])
        sale_row.add_widget(self.sale_spinner)
        sale_row.add_widget(styled_button(
            "Accetta offerta", self._sell_selected,
            bg_color=(0.55, 0.30, 0.12, 1), height=44,
        ))
        self.layout.add_widget(sale_row)

        self.feedback = Label(
            text="", font_size="13sp", color=TEXT_COLOR,
            size_hint_y=None, height=46,
        )
        self.layout.add_widget(self.feedback)
        self.layout.add_widget(styled_button(
            "⬅️ Indietro", lambda _btn: setattr(app.sm, "current", "menu"),
            height=46,
        ))
        self.add_widget(self.layout)

    def on_enter(self):
        self._refresh()

    def _refresh(self, *_args):
        self.list_layout.clear_widgets()
        team = self.app.user_team
        if not team:
            return
        self.budget_label.text = (
            f"Budget {team.budget}  •  Rosa {len(team.players)}/24  •  "
            f"Stipendi {team.payroll_per_round()}/turno"
        )
        self.sale_spinner.values = [player.name for player in team.players]
        if self.sale_spinner.text not in self.sale_spinner.values:
            self.sale_spinner.text = (
                self.sale_spinner.values[0]
                if self.sale_spinner.values else "Nessun giocatore"
            )

        for player in self.app.get_transfer_targets():
            asking = self.app.get_player_price(player)
            club = self.app.get_player_club(player)
            button = Button(
                text=(
                    f"{player.name}  |  {club}  |  {player.position.value}  |  "
                    f"OVR {player.overall_rating()}  |  Valore {asking}  |  "
                    f"Ingaggio {player.wage}"
                ),
                font_size="13sp", size_hint_y=None, height=48,
                background_color=(0.16, 0.28, 0.38, 1),
                color=TEXT_COLOR,
            )
            button.bind(on_press=lambda _btn, target=player: self._select_target(target))
            self.list_layout.add_widget(button)

    def _select_target(self, player):
        self.selected_target = player
        asking = self.app.get_player_price(player)
        fees = sorted({
            max(10, int(asking * factor))
            for factor in (0.80, 0.90, 1.00, 1.10)
        })
        self.fee_spinner.values = [str(value) for value in fees]
        self.fee_spinner.text = str(asking)
        self.wage_spinner.text = str(max(1, min(15, player.wage)))
        self.target_label.text = (
            f"{player.name}: valore {asking}, contratto attuale "
            f"{player.contract_years} anni, felicità {player.happiness}"
        )
        self.feedback.text = ""

    def _submit_offer(self, _btn):
        player = self.selected_target
        if not player or not self.fee_spinner.text.isdigit():
            self.feedback.text = "Seleziona prima un giocatore dalla lista."
            return
        years = int(self.years_spinner.text.split()[0])
        ok, message = self.app.negotiate_transfer(
            player=player,
            fee=int(self.fee_spinner.text),
            wage=int(self.wage_spinner.text),
            years=years,
            squad_role=self.role_spinner.text,
        )
        self.feedback.text = ("✅ " if ok else "❌ ") + message
        self.feedback.color = (
            (0.2, 0.78, 0.35, 1) if ok else (0.86, 0.2, 0.2, 1)
        )
        if ok:
            self.selected_target = None
            self.target_label.text = "Trattativa conclusa"
            self._refresh()

    def _sell_selected(self, _btn):
        team = self.app.user_team
        if not team:
            return
        player = next(
            (item for item in team.players if item.name == self.sale_spinner.text),
            None,
        )
        if not player:
            self.feedback.text = "Nessun giocatore selezionato."
            return
        preview = self.app.get_incoming_offer(player)
        interest = 70 + max(-10, min(20, (player.form - 50) // 2))
        ok, message, fee = self.app.sell_player(player, interest=interest)
        self.feedback.text = (
            f"✅ {player.name} ceduto per {fee}."
            if ok else f"❌ {message} (offerta prevista {preview})"
        )
        self.feedback.color = (
            (0.2, 0.78, 0.35, 1) if ok else (0.86, 0.2, 0.2, 1)
        )
        self._refresh()


# ── Centro Carriera ─────────────────────────────────────────────

class CarrieraScreen(Screen):
    """Manager career dashboard with board, supporters and season progression."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("💼 Centro Carriera"))
        self.summary = Label(text="", font_size="16sp", color=TEXT_COLOR,
                             size_hint_y=None, height=150, halign="left", valign="middle")
        self.summary.bind(size=lambda inst, _value=None: setattr(inst, "text_size", inst.size))
        self.layout.add_widget(self.summary)
        self.layout.add_widget(section_title("📰 Notizie e spogliatoio"))
        self.news = Label(text="", font_size="14sp", color=(0.75, 0.82, 0.95, 1),
                          halign="left", valign="top")
        self.news.bind(size=lambda inst, _value=None: setattr(inst, "text_size", inst.size))
        self.layout.add_widget(self.news)
        self.new_season_btn = styled_button(
            "🏆 Avvia nuova stagione", self._new_season,
            bg_color=(0.20, 0.55, 0.32, 1))
        self.layout.add_widget(self.new_season_btn)
        self.feedback = Label(text="", font_size="13sp", color=(0.95, 0.83, 0.2, 1),
                              size_hint_y=None, height=32)
        self.layout.add_widget(self.feedback)
        self.layout.add_widget(styled_button(
            "⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        team = self.app.user_team
        budget = team.budget if team else 0
        position = str(self.app.get_standings().index(team) + 1) if team else "-"
        self.summary.text = (
            f"Stagione: {self.app.season_number}\n"
            f"Club: {team.name if team else '—'} | Posizione: {position}a\n"
            f"Obiettivo: {self.app.season_objective}\n"
            f"Fiducia dirigenza: {self.app.board_confidence}/100\n"
            f"Reputazione manager: {self.app.manager_reputation}/100\n"
            f"Tifosi: {self.app.supporters} | Budget: {budget} crediti"
        )
        # Show season goals if any
        goals_text = ""
        if hasattr(self.app, 'season_goals') and self.app.season_goals:
            goals_lines = []
            for goal in self.app.season_goals:
                status_icon = {"active": "🔄", "completed": "✅", "failed": "❌"}.get(goal["status"], "❓")
                goals_lines.append(f"{status_icon} {goal['description']}")
            goals_text = "\n🎯 Obiettivi stagionali:\n" + "\n".join(goals_lines) + "\n\n"
        self.news.text = goals_text + "\n".join(f"• {item}" for item in self.app.career_news)
        self.new_season_btn.disabled = self.app.get_next_match() is not None
        self.feedback.text = ("Completa il campionato per avanzare."
                              if self.new_season_btn.disabled
                              else "La stagione è conclusa: prepara il nuovo anno.")

    def _new_season(self, _):
        if self.app.start_new_season():
            self.feedback.text = "Nuova stagione avviata!"
            self.on_enter()
        else:
            self.feedback.text = "Devi prima completare tutte le partite."


# ── Youth Academy ──────────────────────────────────────────────

class YouthAcademyScreen(Screen):
    """Youth academy screen: view prospects and promote them to the first team."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("🌱 Youth Academy"))

        self.info_label = Label(
            text="", font_size="14sp", color=TEXT_COLOR,
            size_hint_y=None, height=36,
        )
        self.layout.add_widget(self.info_label)

        self.scroll = ScrollView(size_hint_y=0.60)
        self.list_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        self.layout.add_widget(self.scroll)

        self.layout.add_widget(styled_button(
            "🔄 Genera nuovi talenti", self._generate_prospects,
            bg_color=(0.20, 0.55, 0.32, 1),
        ))
        self.layout.add_widget(styled_button(
            "⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        self._refresh()

    def _refresh(self, *_):
        self.list_layout.clear_widgets()
        team = self.app.user_team
        if not team:
            return
        if not team.youth_players:
            self.info_label.text = "Nessun giovane talento nell'accademia. Genera nuovi talenti!"
            return
        self.info_label.text = f"{len(team.youth_players)} giovani talenti nell'accademia:"
        for p in team.youth_players:
            card = PlayerCard(p)
            # Add promote button below each card
            promote_btn = Button(
                text=f"⬆️ Promuovi {p.name}",
                font_size="14sp", size_hint_y=None, height=44,
                background_color=(0.20, 0.55, 0.32, 1), color=TEXT_COLOR,
            )
            promote_btn.bind(on_press=lambda _, pl=p: self._promote(pl))
            self.list_layout.add_widget(card)
            self.list_layout.add_widget(promote_btn)

    def _generate_prospects(self, _):
        team = self.app.user_team
        if not team:
            return
        new_prospects = generate_youth_prospects(team)
        team.youth_players.extend(new_prospects)
        self._refresh()

    def _promote(self, prospect):
        team = self.app.user_team
        if not team:
            return
        ok = promote_youth_player(team, prospect)
        if ok:
            self.info_label.text = f"✅ {prospect.name} promosso in prima squadra!"
        else:
            self.info_label.text = f"❌ Impossibile promuovere {prospect.name}."
        self._refresh()
