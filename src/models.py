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
        """Rating adjusted by morale and injury status."""
        base = self.overall_rating()
        if self.injured:
            return 0
        if self.morale < 30:
            return int(round(base * 0.90))
        elif self.morale > 80:
            return int(round(base * 1.05))
        return base

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

    def apply_morale(self, delta: int) -> None:
        """Adjust morale by delta, clamped to [0, 100]."""
        self.morale = max(0, min(100, self.morale + delta))

    def __str__(self) -> str:
        inj = " 🔴" if self.injured else ""
        return f"{self.name} [{self.position.value}] OVR:{self.overall_rating()} G:{self.goals} A:{self.appearances} Età:{self.age} Mor:{self.morale}{inj}"


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
        # Sort each group by overall rating descending
        for pos in by_pos:
            by_pos[pos].sort(key=lambda p: p.overall_rating(), reverse=True)
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
            remaining.sort(key=lambda p: p.overall_rating(), reverse=True)
            starters.extend(remaining[: 11 - len(starters)])
        return starters[:11]

    def __str__(self) -> str:
        return f"{self.name} — Rating:{self.team_rating()} Pts:{self.points} W:{self.wins} D:{self.draws} L:{self.losses} GF:{self.goals_for} GA:{self.goals_against}"


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
        if self.played:
            return f"{self.home_team.name} {self.home_score} - {self.away_score} {self.away_team.name}"
        return f"{self.home_team.name} vs {self.away_team.name} (not played)"