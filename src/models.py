"""Data models for Field Hockey Manager."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Position(Enum):
    """Player positions on the field."""
    GOALKEEPER = "Portiere"
    DEFENSE = "Difesa"
    MIDFIELD = "Centrocampo"
    ATTACK = "Attacco"


# Normalized formation positions (0.0-1.0). y=0 is own goal, y=1 is opponent goal.
# Each formation lists 11 positions: 1 GK + DEF + MID + ATT
FORMATION_POSITIONS: dict[str, list[tuple[float, float]]] = {
    "4-3-3": [
        (0.50, 0.05),  # GK
        (0.20, 0.25), (0.40, 0.22), (0.60, 0.22), (0.80, 0.25),  # 4 DEF
        (0.25, 0.48), (0.50, 0.45), (0.75, 0.48),  # 3 MID
        (0.25, 0.72), (0.50, 0.75), (0.75, 0.72),  # 3 ATT
    ],
    "4-4-2": [
        (0.50, 0.05),  # GK
        (0.20, 0.25), (0.40, 0.22), (0.60, 0.22), (0.80, 0.25),  # 4 DEF
        (0.15, 0.48), (0.38, 0.45), (0.62, 0.45), (0.85, 0.48),  # 4 MID
        (0.40, 0.72), (0.60, 0.72),  # 2 ATT
    ],
    "3-5-2": [
        (0.50, 0.05),  # GK
        (0.30, 0.22), (0.50, 0.20), (0.70, 0.22),  # 3 DEF
        (0.15, 0.45), (0.35, 0.48), (0.50, 0.42), (0.65, 0.48), (0.85, 0.45),  # 5 MID
        (0.40, 0.72), (0.60, 0.72),  # 2 ATT
    ],
    "5-3-2": [
        (0.50, 0.05),  # GK
        (0.12, 0.25), (0.30, 0.20), (0.50, 0.18), (0.70, 0.20), (0.88, 0.25),  # 5 DEF
        (0.25, 0.48), (0.50, 0.45), (0.75, 0.48),  # 3 MID
        (0.40, 0.72), (0.60, 0.72),  # 2 ATT
    ],
}


def get_formation_positions(formation: str, away: bool = False) -> list[tuple[float, float]]:
    """Return 11 normalized positions for a formation.
    If away=True, mirror y coordinates (y → 1-y)."""
    positions = FORMATION_POSITIONS.get(formation, FORMATION_POSITIONS["4-3-3"])
    if away:
        return [(x, 1.0 - y) for (x, y) in positions]
    return list(positions)


# Weighting for overall rating by position
_POSITION_WEIGHTS: dict[Position, dict[str, float]] = {
    Position.GOALKEEPER: {"passing": 0.10, "shooting": 0.05, "defense": 0.45, "speed": 0.15, "stamina": 0.25},
    Position.DEFENSE:    {"passing": 0.20, "shooting": 0.10, "defense": 0.40, "speed": 0.15, "stamina": 0.15},
    Position.MIDFIELD:   {"passing": 0.30, "shooting": 0.15, "defense": 0.20, "speed": 0.15, "stamina": 0.20},
    Position.ATTACK:     {"passing": 0.20, "shooting": 0.35, "defense": 0.10, "speed": 0.20, "stamina": 0.15},
}


@dataclass
class Player:
    """A hockey player with attributes and stats."""
    name: str
    position: Position
    passing: int = 50
    shooting: int = 50
    defense: int = 50
    speed: int = 50
    stamina: int = 50
    goals: int = 0
    appearances: int = 0
    # Extended fields (default values keep backward compatibility)
    age: int = 25
    morale: int = 50
    injured: bool = False
    injury_duration: int = 0  # matches remaining
    injury_type: str = ""  # Human-readable medical diagnosis
    potential: int = 99  # Maximum reachable rating (for growth system)
    condition: int = 100  # Physical readiness, 0-100
    form: int = 50  # Recent performance, 0-100
    matches_since_rest: int = 0
    wage: int = 2  # Wage units paid each league round
    contract_years: int = 3
    squad_role: str = "Rotazione"  # Chiave, Titolare, Rotazione, Prospetto
    happiness: int = 60

    def overall_rating(self) -> int:
        """Calculate overall rating using position-specific weights."""
        weights = _POSITION_WEIGHTS[self.position]
        raw = (
            self.passing * weights["passing"]
            + self.shooting * weights["shooting"]
            + self.defense * weights["defense"]
            + self.speed * weights["speed"]
            + self.stamina * weights["stamina"]
        )
        return int(round(raw))

    def effective_rating(self) -> int:
        """Return match-day rating adjusted by morale, form and condition."""
        base = self.overall_rating()
        if self.injured:
            return 0
        morale_factor = 0.90 if self.morale < 30 else (1.05 if self.morale > 80 else 1.0)
        # Form changes performance by at most ±8%; condition can cost up to 25%.
        form_factor = 1.0 + ((self.form - 50) / 50.0) * 0.08
        condition_factor = 0.75 + (max(0, min(100, self.condition)) / 100.0) * 0.25
        happiness_factor = 0.95 + (max(0, min(100, self.happiness)) / 100.0) * 0.10
        return max(1, int(round(
            base * morale_factor * form_factor * condition_factor * happiness_factor
        )))

    def apply_match_load(
        self,
        intensity: str = "Bilanciata",
        played: bool = True,
        pressing: str = "Medio",
        tempo: str = "Bilanciato",
    ) -> None:
        """Apply fatigue from intensity, pressing, tempo and player stamina."""
        if played:
            fatigue = {"Difensiva": 12, "Bilanciata": 16, "Offensiva": 21}.get(
                intensity, 16
            )
            fatigue += {"Basso": -2, "Medio": 0, "Alto": 4}.get(pressing, 0)
            fatigue += {"Controllato": -2, "Bilanciato": 0, "Rapido": 3}.get(
                tempo, 0
            )
            fatigue += max(0, 65 - self.stamina) // 10
            self.condition = max(20, self.condition - fatigue)
            self.matches_since_rest += 1
        else:
            self.condition = min(100, self.condition + 18)
            self.matches_since_rest = 0

    def recover_between_matches(self) -> None:
        """Recover condition between fixtures; high stamina improves recovery."""
        recovery = 8 + max(0, self.stamina - 50) // 10
        self.condition = min(100, self.condition + recovery)

    def update_form(self, won: bool, drew: bool = False, scored: bool = False) -> None:
        """Update recent form with bounded, gradual changes."""
        delta = 3 if won else (1 if drew else -3)
        if scored:
            delta += 2
        self.form = max(0, min(100, self.form + delta))

    def update_happiness_for_selection(self, started: bool) -> None:
        """Update happiness according to playing time and promised squad role."""
        expected_to_start = self.squad_role in ("Chiave", "Titolare")
        if started:
            delta = 2 if expected_to_start else 3
        else:
            delta = -5 if self.squad_role == "Chiave" else (
                -3 if self.squad_role == "Titolare" else 1
            )
        self.happiness = max(0, min(100, self.happiness + delta))

    def renew_contract(self, years: int, wage: int) -> bool:
        """Renew a contract when the proposal is credible for the player's status."""
        if years < 1 or years > 5 or wage < 1:
            return False
        minimum = max(1, self.overall_rating() // 12)
        if self.squad_role == "Chiave":
            minimum += 2
        if wage < minimum:
            self.happiness = max(0, self.happiness - 5)
            return False
        self.contract_years = years
        self.wage = wage
        self.happiness = min(100, self.happiness + 5)
        return True

    def can_play(self) -> bool:
        """Return True if the player is available (not injured)."""
        return not self.injured

    def heal_one_match(self) -> None:
        """Decrement injury duration; heal if duration reaches 0."""
        if self.injured:
            self.injury_duration -= 1
            if self.injury_duration <= 0:
                self.injured = False
                self.injury_duration = 0
                self.injury_type = ""

    def apply_morale(self, delta: int) -> None:
        """Adjust morale by delta, clamped to [0, 100]."""
        self.morale = max(0, min(100, self.morale + delta))

    def show_potential(self) -> bool:
        """Return True if potential should be displayed (only for under-23 players)."""
        return self.age < 23

    def __str__(self) -> str:
        inj = (
            f" 🔴{self.injury_type or 'Infortunio'} ({self.injury_duration})"
            if self.injured else ""
        )
        return (
            f"{self.name} [{self.position.value}] OVR:{self.overall_rating()} "
            f"FORMA:{self.form} COND:{self.condition} G:{self.goals} "
            f"A:{self.appearances} Età:{self.age} Mor:{self.morale} "
            f"Fel:{self.happiness} Contr:{self.contract_years}a{inj}"
        )


@dataclass
class Team:
    """A hockey team with players and standings."""
    name: str
    players: list[Player] = field(default_factory=list)
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    # Extended fields
    budget: int = 500
    formation: str = "4-3-3"
    intensity: str = "Bilanciata"
    pressing: str = "Medio"
    tempo: str = "Bilanciato"
    prestige: int = 0  # Prestige from cup wins and playoff results
    youth_players: list[Player] = field(default_factory=list)  # Youth academy prospects
    rivals: list[str] = field(default_factory=list)  # Feature 2: rival teams for derby detection

    def initialize_squad_roles(self, force: bool = False) -> None:
        """Assign credible initial roles and wages from squad hierarchy."""
        if not force and any(
            player.squad_role != "Rotazione" or player.wage != 2
            for player in self.players
        ):
            return
        ranked = sorted(self.players, key=lambda player: player.overall_rating(), reverse=True)
        for index, player in enumerate(ranked):
            if player.age <= 21 and index >= 7:
                player.squad_role = "Prospetto"
                player.wage = max(1, player.overall_rating() // 35)
            elif index < 3:
                player.squad_role = "Chiave"
                player.wage = max(4, player.overall_rating() // 20)
            elif index < 11:
                player.squad_role = "Titolare"
                player.wage = max(3, player.overall_rating() // 24)
            else:
                player.squad_role = "Rotazione"
                player.wage = max(2, player.overall_rating() // 30)

    def payroll_per_round(self) -> int:
        """Return the total wage bill charged after a league fixture."""
        return sum(max(0, player.wage) for player in self.players)

    def team_rating(self) -> int:
        """Average rating of the 11 starters (using effective_rating)."""
        starters = self.get_starters()
        if not starters:
            return 0
        return int(round(sum(p.effective_rating() for p in starters) / len(starters)))

    def get_starters(self) -> list[Player]:
        """Return the best 11 available players (1 GK + 4 DEF + 5 MID + 6 ATT if available)."""
        by_pos: dict[Position, list[Player]] = {
            Position.GOALKEEPER: [],
            Position.DEFENSE: [],
            Position.MIDFIELD: [],
            Position.ATTACK: [],
        }
        for p in self.players:
            if p.can_play():
                by_pos[p.position].append(p)
        # Pick the best match-day options: form, morale and condition matter.
        for pos in by_pos:
            by_pos[pos].sort(key=lambda p: p.effective_rating(), reverse=True)
        starters = (
            by_pos[Position.GOALKEEPER][:1]
            + by_pos[Position.DEFENSE][:4]
            + by_pos[Position.MIDFIELD][:5]
            + by_pos[Position.ATTACK][:6]
        )
        # If we don't have enough by position, fill from remaining
        if len(starters) < 11 and len(self.players) >= 11:
            selected_ids = {id(p) for p in starters}
            remaining = [p for p in self.players if id(p) not in selected_ids and p.can_play()]
            remaining.sort(key=lambda p: p.effective_rating(), reverse=True)
            starters.extend(remaining[: 11 - len(starters)])
        return starters[:11]

    def __str__(self) -> str:
        return f"{self.name} — Rating:{self.team_rating()} Pts:{self.points} W:{self.wins} D:{self.draws} L:{self.losses} GF:{self.goals_for} GA:{self.goals_against} Pr:{self.prestige}"


@dataclass
class Match:
    """A match between two teams."""
    home_team: Team
    away_team: Team
    home_score: int = 0
    away_score: int = 0
    events: list[dict] = field(default_factory=list)
    played: bool = False

    def __str__(self) -> str:
        home_name = self.home_team.name if self.home_team else "TBD"
        away_name = self.away_team.name if self.away_team else "TBD"
        if self.played:
            return f"{home_name} {self.home_score} - {self.away_score} {away_name}"
        return f"{home_name} vs {away_name} (not played)"