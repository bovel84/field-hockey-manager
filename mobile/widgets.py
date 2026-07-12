"""Reusable Kivy widgets for Field Hockey Manager mobile UI."""
from __future__ import annotations
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex

from src.models import Player, Position

# Palette
BG_COLOR = (0.102, 0.102, 0.180, 1)       # #1a1a2e
ACCENT_COLOR = (0.914, 0.271, 0.376, 1)    # #e94560
TEXT_COLOR = (1, 1, 1, 1)                  # #ffffff
CARD_COLOR = (0.086, 0.129, 0.243, 1)      # #16213e
CARD_BORDER = (0.2, 0.3, 0.5, 1)

# Position colors
POS_COLORS: dict[Position, tuple] = {
    Position.GOALKEEPER: (0.86, 0.20, 0.20, 1),   # red
    Position.DEFENSE:    (0.20, 0.40, 0.86, 1),    # blue
    Position.MIDFIELD:   (0.20, 0.78, 0.35, 1),    # green
    Position.ATTACK:     (0.95, 0.83, 0.20, 1),    # yellow
}

POS_EMOJI: dict[Position, str] = {
    Position.GOALKEEPER: "🥅",
    Position.DEFENSE: "🛡️",
    Position.MIDFIELD: "⚙️",
    Position.ATTACK: "⚔️",
}


def pos_color(pos: Position) -> tuple:
    return POS_COLORS.get(pos, TEXT_COLOR)


def rating_to_color(rating: int) -> tuple:
    """Map a 0-99 rating to a color (red→yellow→green)."""
    if rating < 40:
        return (0.86, 0.20, 0.20, 1)
    elif rating < 60:
        return (0.95, 0.55, 0.20, 1)
    elif rating < 75:
        return (0.95, 0.83, 0.20, 1)
    else:
        return (0.20, 0.78, 0.35, 1)


class BannerLabel(Label):
    """Styled title label."""
    pass


class RatingBar(BoxLayout):
    """A rating bar with label + colored progress."""

    def __init__(self, label: str = "", value: int = 0, max_val: int = 99, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = 30
        self.spacing = 6

        self.lbl = Label(
            text=label,
            size_hint_x=0.35,
            font_size="14sp",
            color=TEXT_COLOR,
            halign="right",
        )
        self.bar = ProgressBar(
            max=max_val,
            value=value,
            size_hint_x=0.45,
        )
        self.val = Label(
            text=str(value),
            size_hint_x=0.20,
            font_size="14sp",
            color=rating_to_color(value),
            halign="left",
        )
        self.add_widget(self.lbl)
        self.add_widget(self.bar)
        self.add_widget(self.val)

    def set_value(self, value: int, max_val: int = 99):
        self.bar.max = max_val
        self.bar.value = value
        self.val.text = str(value)
        self.val.color = rating_to_color(value)


class PlayerCard(BoxLayout):
    """A card showing a single player's info."""

    def __init__(self, player: Player, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = 162
        self.spacing = 4
        self.padding = [8, 6]

        pc = pos_color(player.position)
        ovr = player.overall_rating()

        with self.canvas.before:
            Color(*CARD_COLOR)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.bind(pos=self._update_rect, size=self._update_rect)

        # Top row: name + position emoji
        top = BoxLayout(orientation="horizontal", size_hint_y=0.35)
        inj = " 🔴" if player.injured else ""
        name_lbl = Label(
            text=f"{player.name}{inj}",
            font_size="15sp",
            bold=True,
            color=TEXT_COLOR,
            size_hint_x=0.65,
            halign="left",
            valign="middle",
        )
        name_lbl.bind(size=lambda inst, _value=None: setattr(inst, "text_size", inst.size))
        pos_lbl = Label(
            text=f"{POS_EMOJI.get(player.position, '')} {player.position.value}",
            font_size="14sp",
            color=pc,
            size_hint_x=0.35,
            halign="right",
        )
        pos_lbl.bind(size=lambda inst, _value=None: setattr(inst, "text_size", inst.size))
        top.add_widget(name_lbl)
        top.add_widget(pos_lbl)

        # Mid row: OVR bar + age + morale
        mid = BoxLayout(orientation="horizontal", size_hint_y=0.30, spacing=4)
        ovr_bar = RatingBar("OVR", ovr, size_hint_x=0.45)
        age_lbl = Label(
            text=f"Età {player.age}",
            font_size="13sp",
            color=(0.7, 0.7, 0.8, 1),
            size_hint_x=0.20,
        )
        # Show potential for young players (under 23)
        if player.show_potential():
            pot_lbl = Label(
                text=f"POT {player.potential}",
                font_size="13sp",
                color=(0.6, 0.85, 0.95, 1),
                size_hint_x=0.20,
            )
            mid.add_widget(ovr_bar)
            mid.add_widget(age_lbl)
            mid.add_widget(pot_lbl)
        else:
            mor_color = (0.2, 0.78, 0.35, 1) if player.morale > 60 else ((0.95, 0.55, 0.2, 1) if player.morale > 30 else (0.86, 0.2, 0.2, 1))
            mor_lbl = Label(
                text=f"Mor {player.morale}",
                font_size="13sp",
                color=mor_color,
                size_hint_x=0.35,
            )
            mid.add_widget(ovr_bar)
            mid.add_widget(age_lbl)
            mid.add_widget(mor_lbl)

        # Bottom row: goals + appearances
        bot = BoxLayout(orientation="horizontal", size_hint_y=0.25, spacing=4)
        gol_lbl = Label(
            text=f"⚽ {player.goals}",
            font_size="13sp",
            color=(0.95, 0.83, 0.2, 1),
            size_hint_x=0.25,
        )
        pres_lbl = Label(
            text=f"📊 {player.appearances}",
            font_size="13sp",
            color=(0.6, 0.8, 0.95, 1),
            size_hint_x=0.25,
        )
        eff = player.effective_rating()
        eff_lbl = Label(
            text=f"Eff {eff}",
            font_size="13sp",
            color=rating_to_color(eff),
            size_hint_x=0.25,
        )
        readiness = min(player.condition, player.form)
        status_text = (
            f"🏥 {player.injury_type or 'Infortunio'} · {player.injury_duration} gare"
            if player.injured
            else f"Cond {player.condition}  Forma {player.form}"
        )
        status_lbl = Label(
            text=status_text,
            font_size="12sp",
            color=(0.86, 0.2, 0.2, 1) if player.injured else rating_to_color(readiness),
            size_hint_x=0.38,
        )
        bot.add_widget(gol_lbl)
        bot.add_widget(pres_lbl)
        bot.add_widget(eff_lbl)
        bot.add_widget(status_lbl)

        contract = BoxLayout(orientation="horizontal", size_hint_y=0.24, spacing=4)
        happiness_color = rating_to_color(player.happiness)
        contract.add_widget(Label(
            text=f"Ruolo: {player.squad_role}",
            font_size="12sp", color=(0.70, 0.80, 0.95, 1),
        ))
        contract.add_widget(Label(
            text=f"Contratto: {player.contract_years} anni",
            font_size="12sp",
            color=(0.90, 0.45, 0.35, 1) if player.contract_years <= 1 else TEXT_COLOR,
        ))
        contract.add_widget(Label(
            text=f"Stipendio: {player.wage}",
            font_size="12sp", color=(0.45, 0.85, 0.55, 1),
        ))
        contract.add_widget(Label(
            text=f"Felicità: {player.happiness}",
            font_size="12sp", color=happiness_color,
        ))

        self.add_widget(top)
        self.add_widget(mid)
        self.add_widget(bot)
        self.add_widget(contract)

    def _update_rect(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*CARD_COLOR)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[8])


class TeamBadge(Label):
    """A colored team name label."""

    def __init__(self, name: str, color: tuple | None = None, **kwargs):
        c = color or ACCENT_COLOR
        super().__init__(
            text=name,
            font_size="16sp",
            bold=True,
            color=c,
            size_hint_y=None,
            height=36,
            **kwargs,
        )


class MatchResult(BoxLayout):
    """A row showing a match result with color coding."""

    def __init__(self, home_team: str, away_team: str,
                 home_score: int = 0, away_score: int = 0,
                 played: bool = False, is_user: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = 44
        self.spacing = 4

        bg = CARD_COLOR if played else (0.08, 0.08, 0.12, 1)
        with self.canvas.before:
            Color(*bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[6])
        self.bind(pos=self._update_rect, size=self._update_rect)

        home_lbl = Label(
            text=home_team,
            font_size="13sp",
            color=TEXT_COLOR,
            size_hint_x=0.35,
            halign="right",
        )
        home_lbl.bind(size=lambda inst, _value=None: setattr(inst, "text_size", inst.size))

        if played:
            score_text = f"{home_score} - {away_score}"
            score_color = TEXT_COLOR
            if is_user:
                if home_score > away_score:
                    score_color = (0.2, 0.78, 0.35, 1)   # green win
                elif home_score < away_score:
                    score_color = (0.86, 0.2, 0.2, 1)     # red loss
                else:
                    score_color = (0.95, 0.83, 0.2, 1)    # yellow draw
        else:
            score_text = "vs"
            score_color = (0.4, 0.4, 0.5, 1)

        score_lbl = Label(
            text=score_text,
            font_size="14sp",
            bold=True,
            color=score_color,
            size_hint_x=0.30,
        )

        away_lbl = Label(
            text=away_team,
            font_size="13sp",
            color=TEXT_COLOR,
            size_hint_x=0.35,
            halign="left",
        )
        away_lbl.bind(size=lambda inst, _value=None: setattr(inst, "text_size", inst.size))

        self.add_widget(home_lbl)
        self.add_widget(score_lbl)
        self.add_widget(away_lbl)

    def _update_rect(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            bg = CARD_COLOR
            Color(*bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[6])

# --- Phase 3: Match 2D Visualization ---

import random as _random
from kivy.uix.widget import Widget
from kivy.graphics import Ellipse, Line, Color, Rectangle, PushMatrix, PopMatrix, Translate
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel


# Field colors
FIELD_GREEN = (0.05, 0.36, 0.18, 1)
FIELD_LINE = (1, 1, 1, 1)
HOME_COLOR = (0.914, 0.271, 0.376, 1)   # #e94560 red
AWAY_COLOR = (0.231, 0.510, 0.965, 1)  # #3b82f6 blue
GK_COLOR = (0.95, 0.62, 0.20, 1)       # orange for goalkeeper
BALL_COLOR = (1, 1, 1, 1)
FLASH_COLOR = (1, 1, 1, 0.8)


class MatchFieldWidget(Widget):
    """2D top-down hockey field showing players, ball, and events in real time."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timeline: list[dict] = []
        self.match = None
        self.current_index = 0
        self.match_time = 0.0
        self.speed = 1.0
        self.paused = False
        self.event_overlay_text = ""
        self.event_overlay_timer = 0.0
        self.flash_timer = 0.0
        self._anim_event = None
        self._home_positions = []
        self._away_positions = []
        self._ball_pos = (0.5, 0.5)
        self._blink_players: set[int] = set()  # indices of players blinking
        self._blink_timer = 0.0
        self.bind(size=self._redraw, pos=self._redraw)

    def set_match(self, match, timeline: list[dict] | None = None):
        """Set the match data and timeline to visualize."""
        self.match = match
        if timeline is None:
            from src.simulation import generate_match_timeline
            timeline = generate_match_timeline(match)
        self.timeline = timeline
        self.current_index = 0
        self.match_time = 0.0
        self.paused = False
        self.speed = 1.0
        if self.timeline:
            self._apply_frame(self.timeline[0])

    def start_animation(self):
        """Start playing the match animation."""
        if not self._anim_event:
            self._anim_event = Clock.schedule_interval(self._tick, 1.0 / 30.0)

    def stop_animation(self):
        """Stop the match animation."""
        if self._anim_event:
            self._anim_event.cancel()
            self._anim_event = None

    def set_speed(self, speed: float):
        self.speed = speed

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def _tick(self, dt):
        if self.paused or not self.timeline:
            return
        # Advance match time: 60 match-minutes in 60/speed real seconds
        self.match_time += dt * self.speed
        if self.match_time >= 60.0:
            self.match_time = 60.0
            self._apply_frame_at(60.0)
            self.stop_animation()
            return
        self._apply_frame_at(self.match_time)
        # Update overlay timers
        if self.event_overlay_timer > 0:
            self.event_overlay_timer -= dt
            if self.event_overlay_timer <= 0:
                self.event_overlay_text = ""
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self._blink_timer > 0:
            self._blink_timer -= dt
            if self._blink_timer <= 0:
                self._blink_players.clear()
        self._redraw()

    def _apply_frame_at(self, t: float):
        """Find and apply the timeline frame at time t."""
        if not self.timeline:
            return
        # Find the last frame with time <= t
        idx = 0
        for i, frame in enumerate(self.timeline):
            if frame["time"] <= t:
                idx = i
            else:
                break
        # Check if we advanced to a new event
        if idx != self.current_index:
            self.current_index = idx
            self._apply_frame(self.timeline[idx])

    def _apply_frame(self, frame: dict):
        """Apply a timeline frame: positions + event overlay."""
        self._home_positions = frame.get("positions", {}).get("home", [])
        self._away_positions = frame.get("positions", {}).get("away", [])
        ev = frame.get("event")
        if ev:
            self._trigger_event_overlay(ev)
        # Ball follows the action: move toward team in possession
        self._ball_pos = self._estimate_ball_pos(ev)

    def _estimate_ball_pos(self, event: dict | None) -> tuple[float, float]:
        """Estimate ball position based on event."""
        if not event:
            return (0.5, 0.5)
        ev_type = event.get("type", "")
        team = event.get("team", "home")
        if "goal" in ev_type:
            return (0.5, 0.95 if team == "home" else 0.05)
        elif ev_type == "green_card":
            return (0.5, 0.5)
        elif "penalty" in ev_type or "corner" in ev_type:
            return (0.5, 0.85 if team == "home" else 0.15)
        return (0.5, 0.5)

    def _trigger_event_overlay(self, event: dict):
        """Show overlay text for an event."""
        ev_type = event.get("type", "")
        overlays = {
            "goal": f"GOAL! {event.get('scorer', '')}",
            "corner_goal": f"GOAL! {event.get('scorer', '')} (corto angolo)",
            "penalty_goal": f"GOAL! {event.get('scorer', '')} (rigore)",
            "penalty_missed": f"RIGORE SBAGLIATO! {event.get('shooter', '')}",
            "penalty_corner": "PENALTY CORNER",
            "green_card": f"🟢 Cartellino verde — {event.get('player', '')}",
            "injury": f"🏥 Infortunio — {event.get('player', '')}",
            "substitution": f"🔄 OUT: {event.get('out', '')} → IN: {event.get('in', '')}",
        }
        self.event_overlay_text = overlays.get(ev_type, ev_type)
        self.event_overlay_timer = 3.0  # show for 3 seconds

        # Special effects
        if "goal" in ev_type:
            self.flash_timer = 0.3  # white flash
        if ev_type == "green_card":
            # Blink the penalized player
            team = event.get("team", "home")
            self._blink_players = {0 if team == "home" else 11}  # simplified
            self._blink_timer = 2.0

    def _redraw(self, *_):
        """Redraw the field and all elements."""
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return

        w, h = self.width, self.height

        with self.canvas:
            # Field background
            Color(*FIELD_GREEN)
            Rectangle(pos=self.pos, size=(w, h))

            # Flash effect for goals
            if self.flash_timer > 0:
                alpha = self.flash_timer / 0.3 * 0.6
                Color(1, 1, 1, alpha)
                Rectangle(pos=self.pos, size=(w, h))

            Color(*FIELD_LINE)

            # Field border
            margin = 4
            Line(rectangle=(self.x + margin, self.y + margin, w - 2 * margin, h - 2 * margin), width=1.5)

            # Center line (horizontal at middle of field)
            cy = self.y + h / 2
            Line(points=[self.x + margin, cy, self.x + w - margin, cy], width=1.5)

            # Center circle
            cx = self.x + w / 2
            r = min(w, h) * 0.08
            Line(circle=(cx, cy, r), width=1.5)
            # Center dot
            Ellipse(pos=(cx - 2, cy - 2), size=(4, 4))

            # 23m areas (top and bottom)
            area_h = h * 0.2
            Line(rectangle=(self.x + margin, self.y + margin, w - 2 * margin, area_h), width=1)
            Line(rectangle=(self.x + margin, self.y + h - margin - area_h, w - 2 * margin, area_h), width=1)

            # Goal areas (smaller rectangles inside 23m)
            goal_w = w * 0.3
            goal_x = cx - goal_w / 2
            goal_area_h = area_h * 0.5
            Line(rectangle=(goal_x, self.y + margin, goal_w, goal_area_h), width=1)
            Line(rectangle=(goal_x, self.y + h - margin - goal_area_h, goal_w, goal_area_h), width=1)

            # Penalty spots
            Ellipse(pos=(cx - 2, self.y + margin + goal_area_h - 2), size=(4, 4))
            Ellipse(pos=(cx - 2, self.y + h - margin - goal_area_h - 2), size=(4, 4))

            # Draw players
            self._draw_players(w, h)

            # Draw ball
            self._draw_ball(w, h)

            # Event overlay text
            if self.event_overlay_text and self.event_overlay_timer > 0:
                alpha = min(1.0, self.event_overlay_timer / 1.0)
                Color(1, 1, 1, alpha * 0.9)
                # Background rectangle for text
                lbl = CoreLabel(text=self.event_overlay_text, font_size=16)
                lbl.refresh()
                tw, th = lbl.size
                bx = cx - tw / 2 - 8
                by = cy - th / 2 - 4
                Color(0, 0, 0, alpha * 0.7)
                Rectangle(pos=(bx, by), size=(tw + 16, th + 8))
                Color(1, 1, 1, alpha)
                # Draw the text texture
                if lbl.texture:
                    Rectangle(pos=(cx - tw / 2, cy - th / 2), size=(tw, th), texture=lbl.texture)

    def _draw_players(self, w, h):
        """Draw all 22 players as colored circles with numbers."""
        radius = max(6, min(w, h) * 0.025)
        all_positions = list(self._home_positions) + list(self._away_positions)
        for i, pos in enumerate(all_positions):
            if not pos or len(pos) < 2:
                continue
            px = self.x + pos[0] * w
            py = self.y + pos[1] * h

            # Determine color
            if i < 11:
                if i == 0:
                    color = GK_COLOR  # goalkeeper
                else:
                    color = HOME_COLOR
            else:
                if i == 11:
                    color = GK_COLOR  # away goalkeeper
                else:
                    color = AWAY_COLOR

            # Blink effect for penalized players
            if i in self._blink_players and self._blink_timer > 0:
                if int(self._blink_timer * 10) % 2 == 0:
                    color = (0.5, 0.5, 0.5, 1)

            with self.canvas:
                Color(*color)
                Ellipse(pos=(px - radius, py - radius), size=(radius * 2, radius * 2))
                # White border
                Color(1, 1, 1, 0.8)
                Line(circle=(px, py, radius), width=1)
                # Player number
                num = (i % 11) + 1
                lbl = CoreLabel(text=str(num), font_size=int(radius * 0.9))
                lbl.refresh()
                if lbl.texture:
                    tw, th = lbl.size
                    Color(1, 1, 1, 1)
                    Rectangle(pos=(px - tw / 2, py - th / 2), size=(tw, th), texture=lbl.texture)

    def _draw_ball(self, w, h):
        """Draw the ball as a small white circle."""
        if not self._ball_pos or len(self._ball_pos) < 2:
            return
        px = self.x + self._ball_pos[0] * w
        py = self.y + self._ball_pos[1] * h
        radius = max(3, min(w, h) * 0.012)
        with self.canvas:
            Color(*BALL_COLOR)
            Ellipse(pos=(px - radius, py - radius), size=(radius * 2, radius * 2))
            Color(0.8, 0.8, 0.8, 1)
            Line(circle=(px, py, radius), width=0.5)
