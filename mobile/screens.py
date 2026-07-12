"""Kivy screens for Field Hockey Manager mobile UI."""
from __future__ import annotations
import os
import sys

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, RoundedRectangle

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
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        layout = BoxLayout(orientation="vertical", padding=20, spacing=8)

        layout.add_widget(BannerLabel(
            text="🏒 Field Hockey Manager", font_size="26sp", bold=True,
            color=ACCENT_COLOR, size_hint_y=None, height=60,
        ))

        team_name = app.user_team.name if app.user_team else "—"
        layout.add_widget(Label(
            text=f"Squadra: {team_name}", font_size="16sp", color=TEXT_COLOR,
            size_hint_y=None, height=36,
        ))
        layout.add_widget(Label(
            text=app.next_match_info(), font_size="14sp",
            color=(0.6, 0.7, 0.9, 1), size_hint_y=None, height=30,
        ))

        layout.add_widget(styled_button("💼 Centro Carriera", lambda _: setattr(app.sm, 'current', 'carriera')))
        layout.add_widget(styled_button("🥅 Rosa", lambda _: setattr(app.sm, 'current', 'rosa')))
        layout.add_widget(styled_button("📅 Calendario", lambda _: setattr(app.sm, 'current', 'calendario')))
        layout.add_widget(styled_button("🏆 Classifica", lambda _: setattr(app.sm, 'current', 'classifica')))
        layout.add_widget(styled_button("⚽ Gioca Partita", lambda _: setattr(app.sm, 'current', 'partita')))
        layout.add_widget(styled_button("📊 Statistiche", lambda _: setattr(app.sm, 'current', 'statistiche')))
        layout.add_widget(styled_button("🏋️ Allenamenti", lambda _: setattr(app.sm, 'current', 'allenamenti')))
        layout.add_widget(styled_button("💰 Mercato", lambda _: setattr(app.sm, 'current', 'mercato')))
        layout.add_widget(styled_button("🌱 Youth Academy", lambda _: setattr(app.sm, 'current', 'youth')))
        layout.add_widget(styled_button("💾 Salva / Carica", lambda _: setattr(app.sm, 'current', 'saveload')))
        layout.add_widget(styled_button("🚪 Esci", lambda _: app.stop(), bg_color=(0.5, 0.2, 0.2, 1)))

        self.add_widget(layout)


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
                    text=f"Slot {slot}: {info['team_name']} — Stagione {info['season']}\n{info['timestamp']}",
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
            out_spin = Spinner(text="—", values=[], size_hint_x=0.5, font_size="13sp")
            in_spin = Spinner(text="—", values=[], size_hint_x=0.5, font_size="13sp")
            self.sub_spinners.append(out_spin)
            self.sub_spinners.append(in_spin)
            sub_row.add_widget(Label(text="Out:", font_size="12sp", color=(0.86,0.2,0.2,1), size_hint_x=0.15))
            sub_row.add_widget(out_spin)
            sub_row.add_widget(Label(text="In:", font_size="12sp", color=(0.2,0.78,0.35,1), size_hint_x=0.15))
            sub_row.add_widget(in_spin)
            self.layout.add_widget(sub_row)

        self.play_btn = styled_button("🏒 Simula Partita", self._play_match)
        self.layout.add_widget(self.play_btn)

        self.result_label = Label(text="", font_size="18sp", bold=True, color=TEXT_COLOR, size_hint_y=None, height=50)
        self.layout.add_widget(self.result_label)

        self.events_label = Label(
            text="", font_size="13sp", color=(0.7, 0.8, 0.9, 1),
            size_hint_y=None, height=120, valign="top", halign="left",
        )
        self.events_label.bind(size=lambda inst, _value=None: setattr(inst, "text_size", inst.size))
        self.layout.add_widget(self.events_label)

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
                    spin.values = ["—"] + player_names
                    spin.text = "—"
        else:
            self.info_label.text = "Stagione finita! 🎉"
            self.play_btn.disabled = True
        self.result_label.text = ""
        self.events_label.text = ""

    def _play_match(self, _):
        # Collect user-chosen substitutions (pairs: out, in)
        user_subs: list[dict] = []
        for i in range(0, len(self.sub_spinners), 2):
            out_name = self.sub_spinners[i].text
            in_name = self.sub_spinners[i + 1].text
            if out_name != "—" and in_name != "—":
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
        events_text = "\n".join(
            f"{ev.get('minute', '?')}' — {ev.get('type', '')}: {ev.get('scorer') or ev.get('player', '')}"
            for ev in match.events
        )
        self.events_label.text = events_text or "Nessun evento"


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
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        make_screen_bg(self)
        self.layout = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.layout.add_widget(section_title("💰 Mercato"))

        self.budget_label = Label(text="", font_size="16sp", color=(0.95, 0.83, 0.2, 1), size_hint_y=None, height=36)
        self.layout.add_widget(self.budget_label)

        self.scroll = ScrollView(size_hint_y=0.70)
        self.list_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        self.layout.add_widget(self.scroll)

        self.layout.add_widget(styled_button("🔄 Aggiorna", lambda _: self._refresh()))
        self.layout.add_widget(styled_button("⬅️ Indietro", lambda _: setattr(app.sm, 'current', 'menu')))
        self.add_widget(self.layout)

    def on_enter(self):
        self._refresh()

    def _refresh(self, *_):
        self.list_layout.clear_widgets()
        team = self.app.user_team
        if not team:
            return
        self.budget_label.text = f"💰 Budget: {team.budget} crediti"
        for p in self.app.free_agents:
            price = self.app.get_player_price(p)
            can_afford = team.budget >= price
            btn = Button(
                text=f"{p.name} [{p.position.value}] OVR:{p.overall_rating()} — {price} crediti",
                font_size="14sp", size_hint_y=None, height=50,
                background_color=(0.2, 0.5, 0.2, 1) if can_afford else (0.3, 0.3, 0.3, 1),
                color=TEXT_COLOR, disabled=not can_afford,
            )
            btn.bind(on_press=lambda _, pl=p: self._buy(pl))
            self.list_layout.add_widget(btn)

    def _buy(self, player):
        ok = self.app.buy_player(player)
        if ok:
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
        position = str(self.app.get_standings().index(team) + 1) if team else "—"
        self.summary.text = (
            f"Stagione: {self.app.season_number}\n"
            f"Club: {team.name if team else '—'} | Posizione: {position}ª\n"
            f"Obiettivo: {self.app.season_objective}\n"
            f"Fiducia dirigenza: {self.app.board_confidence}/100\n"
            f"Reputazione manager: {self.app.manager_reputation}/100\n"
            f"Tifosi: {self.app.supporters} | Budget: {budget} crediti"
        )
        self.news.text = "\n".join(f"• {item}" for item in self.app.career_news)
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
