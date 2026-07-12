"""Database layer: SQLite init and CRUD operations."""
from __future__ import annotations
from datetime import datetime
import json
import os
import sqlite3
from typing import Optional
from .models import Player, Team, Match, Position


class Database:
    """SQLite database wrapper for Field Hockey Manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def init(self) -> None:
        """Create all tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS teams (
                    name         TEXT PRIMARY KEY,
                    points       INTEGER DEFAULT 0,
                    goals_for    INTEGER DEFAULT 0,
                    goals_against INTEGER DEFAULT 0,
                    wins         INTEGER DEFAULT 0,
                    draws        INTEGER DEFAULT 0,
                    losses       INTEGER DEFAULT 0,
                    budget       INTEGER DEFAULT 500,
                    formation    TEXT DEFAULT '4-3-3',
                    intensity    TEXT DEFAULT 'Bilanciata',
                    prestige     INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS players (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name         TEXT NOT NULL,
                    name              TEXT NOT NULL,
                    position          TEXT NOT NULL,
                    passing           INTEGER DEFAULT 50,
                    shooting          INTEGER DEFAULT 50,
                    defense           INTEGER DEFAULT 50,
                    speed             INTEGER DEFAULT 50,
                    stamina           INTEGER DEFAULT 50,
                    goals             INTEGER DEFAULT 0,
                    appearances       INTEGER DEFAULT 0,
                    age               INTEGER DEFAULT 25,
                    morale            INTEGER DEFAULT 50,
                    injured           INTEGER DEFAULT 0,
                    injury_duration   INTEGER DEFAULT 0,
                    potential         INTEGER DEFAULT 99,
                    is_youth          INTEGER DEFAULT 0,
                    FOREIGN KEY (team_name) REFERENCES teams(name)
                );

                CREATE TABLE IF NOT EXISTS matches (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    round_num   INTEGER,
                    home_team   TEXT NOT NULL,
                    away_team   TEXT NOT NULL,
                    home_score  INTEGER DEFAULT 0,
                    away_score  INTEGER DEFAULT 0,
                    played      INTEGER DEFAULT 0,
                    events      TEXT DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS standings (
                    team_name     TEXT PRIMARY KEY,
                    points        INTEGER DEFAULT 0,
                    wins          INTEGER DEFAULT 0,
                    draws         INTEGER DEFAULT 0,
                    losses        INTEGER DEFAULT 0,
                    goals_for     INTEGER DEFAULT 0,
                    goals_against INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS game_state (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS save_slots (
                    slot      INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    state     TEXT NOT NULL
                );
            """)
            # Migration: add columns to existing databases (m9)
            self._migrate(conn)
            conn.commit()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Add missing columns to existing databases (backward compat)."""
        # Check players table columns
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(players)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        migrations = {
            "potential": "ALTER TABLE players ADD COLUMN potential INTEGER DEFAULT 99",
            "is_youth": "ALTER TABLE players ADD COLUMN is_youth INTEGER DEFAULT 0",
        }
        for col, sql in migrations.items():
            if col not in existing_cols:
                conn.execute(sql)
        # Check teams table for prestige
        cursor.execute("PRAGMA table_info(teams)")
        existing_team_cols = {row[1] for row in cursor.fetchall()}
        if "prestige" not in existing_team_cols:
            conn.execute("ALTER TABLE teams ADD COLUMN prestige INTEGER DEFAULT 0")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ------------------------------------------------------------------
    # Game state (save/load)
    # ------------------------------------------------------------------

    def save_state(self, state: dict) -> None:
        """Save full game state as JSON."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                ("full_state", json.dumps(state)),
            )
            conn.commit()

    def load_state(self) -> Optional[dict]:
        """Load full game state."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM game_state WHERE key = ?", ("full_state",))
            row = cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def clear_state(self) -> None:
        """Remove saved game state."""
        with self._connect() as conn:
            conn.execute("DELETE FROM game_state")
            conn.commit()

    def save_game(self, slot: int, game_state: dict) -> bool:
        """Persist a save slot with a JSON-serializable game state.

        Args:
            slot: Save slot number, supported range 1..3.
            game_state: Serializable game state payload.

        Returns:
            True when the save succeeds, False for an invalid slot.
        """
        if slot not in (1, 2, 3):
            return False
        payload = dict(game_state)
        timestamp = str(payload.get("timestamp") or datetime.now().isoformat(timespec="seconds"))
        payload["timestamp"] = timestamp
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO save_slots (slot, timestamp, state) VALUES (?, ?, ?)",
                (slot, timestamp, json.dumps(payload)),
            )
            conn.commit()
        return True

    def load_game(self, slot: int) -> Optional[dict]:
        """Load a serialized save slot.

        Args:
            slot: Save slot number, supported range 1..3.

        Returns:
            The saved state dict, or None if the slot is empty/invalid.
        """
        if slot not in (1, 2, 3):
            return None
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT state FROM save_slots WHERE slot = ?", (slot,))
            row = cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def list_saves(self) -> list[dict]:
        """Return metadata for all occupied save slots."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT slot, timestamp, state FROM save_slots ORDER BY slot")
            rows = cursor.fetchall()

        saves: list[dict] = []
        for slot, timestamp, state_json in rows:
            state = json.loads(state_json)
            saves.append({
                "slot": slot,
                "team_name": state.get("user_team_name") or state.get("team_name") or "—",
                "league_name": state.get("league_name") or state.get("league_id") or "—",
                "season": int(state.get("season_number", state.get("season", 1))),
                "timestamp": state.get("timestamp") or timestamp,
            })
        return saves

    def delete_save(self, slot: int) -> bool:
        """Delete a save slot.

        Returns:
            True if a row was deleted, False otherwise.
        """
        if slot not in (1, 2, 3):
            return False
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM save_slots WHERE slot = ?", (slot,))
            conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Team CRUD
    # ------------------------------------------------------------------

    def save_team(self, team: Team) -> None:
        """Insert or replace a team and its players."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO teams (name, points, goals_for, goals_against, wins, draws, losses, budget, formation, intensity, prestige)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (team.name, team.points, team.goals_for, team.goals_against,
                 team.wins, team.draws, team.losses, team.budget, team.formation, team.intensity, team.prestige),
            )
            # Delete old players for this team
            conn.execute("DELETE FROM players WHERE team_name = ?", (team.name,))
            for p in team.players:
                conn.execute(
                    """INSERT INTO players
                       (team_name, name, position, passing, shooting, defense, speed, stamina,
                        goals, appearances, age, morale, injured, injury_duration, potential, is_youth)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (team.name, p.name, p.position.value, p.passing, p.shooting,
                     p.defense, p.speed, p.stamina, p.goals, p.appearances,
                     p.age, p.morale, 1 if p.injured else 0, p.injury_duration,
                     p.potential, 0),
                )
            # Save youth players with is_youth=1
            for p in team.youth_players:
                conn.execute(
                    """INSERT INTO players
                       (team_name, name, position, passing, shooting, defense, speed, stamina,
                        goals, appearances, age, morale, injured, injury_duration, potential, is_youth)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (team.name, p.name, p.position.value, p.passing, p.shooting,
                     p.defense, p.speed, p.stamina, p.goals, p.appearances,
                     p.age, p.morale, 1 if p.injured else 0, p.injury_duration,
                     p.potential, 1),
                )
            conn.commit()

    def load_team(self, name: str) -> Optional[Team]:
        """Load a team by name, including its players."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, points, goals_for, goals_against, wins, draws, losses, budget, formation, intensity, prestige "
                "FROM teams WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute(
                """SELECT name, position, passing, shooting, defense, speed, stamina,
                          goals, appearances, age, morale, injured, injury_duration, potential, is_youth
                   FROM players WHERE team_name = ?""",
                (name,),
            )
            prows = cursor.fetchall()
        players = []
        youth_players = []
        for prow in prows:
            p = Player(
                name=prow[0],
                position=Position(prow[1]),
                passing=prow[2],
                shooting=prow[3],
                defense=prow[4],
                speed=prow[5],
                stamina=prow[6],
                goals=prow[7],
                appearances=prow[8],
                age=prow[9],
                morale=prow[10],
                injured=bool(prow[11]),
                injury_duration=prow[12],
                potential=prow[13],
            )
            if prow[14]:  # is_youth
                youth_players.append(p)
            else:
                players.append(p)
        return Team(
            name=row[0],
            players=players,
            points=row[1],
            goals_for=row[2],
            goals_against=row[3],
            wins=row[4],
            draws=row[5],
            losses=row[6],
            budget=row[7],
            formation=row[8],
            intensity=row[9],
            prestige=row[10] if len(row) > 10 else 0,
            youth_players=youth_players,
        )

    def load_all_teams(self) -> list[Team]:
        """Load all teams from the database."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM teams ORDER BY name")
            names = [row[0] for row in cursor.fetchall()]
        return [t for t in (self.load_team(n) for n in names) if t is not None]

    # ------------------------------------------------------------------
    # Match CRUD
    # ------------------------------------------------------------------

    def save_match(self, match: Match, round_num: int = 0) -> None:
        """Save a match result."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO matches (round_num, home_team, away_team, home_score, away_score, played, events)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    round_num,
                    match.home_team.name,
                    match.away_team.name,
                    match.home_score,
                    match.away_score,
                    1 if match.played else 0,
                    json.dumps(match.events),
                ),
            )
            conn.commit()

    def load_matches(self, round_num: Optional[int] = None) -> list[dict]:
        """Load matches, optionally filtered by round."""
        with self._connect() as conn:
            cursor = conn.cursor()
            if round_num is not None:
                cursor.execute(
                    "SELECT round_num, home_team, away_team, home_score, away_score, played, events FROM matches WHERE round_num = ?",
                    (round_num,),
                )
            else:
                cursor.execute(
                    "SELECT round_num, home_team, away_team, home_score, away_score, played, events FROM matches ORDER BY round_num"
                )
            rows = cursor.fetchall()
        return [
            {
                "round": r[0],
                "home_team": r[1],
                "away_team": r[2],
                "home_score": r[3],
                "away_score": r[4],
                "played": bool(r[5]),
                "events": json.loads(r[6]) if r[6] else [],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Standings CRUD
    # ------------------------------------------------------------------

    def save_standings_entry(
        self,
        team_name: str,
        points: int = 0,
        wins: int = 0,
        draws: int = 0,
        losses: int = 0,
        goals_for: int = 0,
        goals_against: int = 0,
    ) -> None:
        """Insert or replace a standings entry."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO standings
                   (team_name, points, wins, draws, losses, goals_for, goals_against)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (team_name, points, wins, draws, losses, goals_for, goals_against),
            )
            conn.commit()

    def load_standings(self) -> list[dict]:
        """Load all standings entries sorted by points (desc), then goal difference (desc)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT team_name, points, wins, draws, losses, goals_for, goals_against
                   FROM standings
                   ORDER BY points DESC, (goals_for - goals_against) DESC, goals_for DESC"""
            )
            rows = cursor.fetchall()
        return [
            {
                "team_name": r[0],
                "points": r[1],
                "wins": r[2],
                "draws": r[3],
                "losses": r[4],
                "goals_for": r[5],
                "goals_against": r[6],
            }
            for r in rows
        ]

    def clear_standings(self) -> None:
        """Remove all standings entries."""
        with self._connect() as conn:
            conn.execute("DELETE FROM standings")
            conn.commit()

    def clear_matches(self) -> None:
        """Remove all matches."""
        with self._connect() as conn:
            conn.execute("DELETE FROM matches")
            conn.commit()
