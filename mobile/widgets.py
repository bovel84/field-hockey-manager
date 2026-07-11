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
        self.height = 120
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
        name_lbl.bind(size=lambda inst: inst.set_texture_size())
        pos_lbl = Label(
            text=f"{POS_EMOJI.get(player.position, '')} {player.position.value}",
            font_size="14sp",
            color=pc,
            size_hint_x=0.35,
            halign="right",
        )
        pos_lbl.bind(size=lambda inst: inst.set_texture_size())
        top.add_widget(name_lbl)
        top.add_widget(pos_lbl)

        # Mid row: OVR bar + age + morale
        mid = BoxLayout(orientation="horizontal", size_hint_y=0.30, spacing=4)
        ovr_bar = RatingBar("OVR", ovr, size_hint_x=0.55)
        age_lbl = Label(
            text=f"Età {player.age}",
            font_size="13sp",
            color=(0.7, 0.7, 0.8, 1),
            size_hint_x=0.20,
        )
        mor_color = (0.2, 0.78, 0.35, 1) if player.morale > 60 else ((0.95, 0.55, 0.2, 1) if player.morale > 30 else (0.86, 0.2, 0.2, 1))
        mor_lbl = Label(
            text=f"Mor {player.morale}",
            font_size="13sp",
            color=mor_color,
            size_hint_x=0.25,
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
        status_lbl = Label(
            text="🔴" if player.injured else "✅",
            font_size="13sp",
            color=(0.86, 0.2, 0.2, 1) if player.injured else (0.2, 0.78, 0.35, 1),
            size_hint_x=0.25,
        )
        bot.add_widget(gol_lbl)
        bot.add_widget(pres_lbl)
        bot.add_widget(eff_lbl)
        bot.add_widget(status_lbl)

        self.add_widget(top)
        self.add_widget(mid)
        self.add_widget(bot)

    def _update_rect(self, *_):
        self.canvas_before.clear()
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
        home_lbl.bind(size=lambda inst: inst.set_texture_size())

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
        away_lbl.bind(size=lambda inst: inst.set_texture_size())

        self.add_widget(home_lbl)
        self.add_widget(score_lbl)
        self.add_widget(away_lbl)

    def _update_rect(self, *_):
        self.canvas_before.clear()
        with self.canvas.before:
            bg = CARD_COLOR
            Color(*bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[6])