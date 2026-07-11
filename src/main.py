"""Entry point for Field Hockey Manager."""
from __future__ import annotations
import argparse
import json
import os
import sys
import random
import time

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Player, Team, Position, Match
from src.database import Database
from src.simulation import simulate_match
from src.season import (
    Standings, generate_calendar, train_player, TRAINING_ATTRIBUTES,
    MAX_TRAININGS_PER_WEEK, generate_free_agents, player_price,
    season_aging, age_player_one_year,
)
from src.ui import (
    main_menu, show_team, show_calendar, show_standings,
    show_stats, play_match, clear_screen, print_header, print_banner,
    show_training, show_transfer_market, choose_tactics, show_advanced_stats,
)
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

console = Console()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "data", "fhm.db")
TEAMS_JSON = os.path.join(DATA_DIR, "teams.json")


def load_teams_from_json(path: str) -> list[Team]:
    """Load team definitions from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    teams = []
    for td in data["teams"]:
        players = []
        for pd in td["players"]:
            players.append(Player(
                name=pd["name"],
                position=Position(pd["position"]),
                passing=pd["passing"],
                shooting=pd["shooting"],
                defense=pd["defense"],
                speed=pd["speed"],
                stamina=pd["stamina"],
                age=pd.get("age", random.randint(18, 32)),
                morale=pd.get("morale", 50),
            ))
        teams.append(Team(name=td["name"], players=players))
    return teams


def init_season(db: Database, teams: list[Team]) -> None:
    """Initialize a new season: save teams, clear matches and standings."""
    db.init()
    db.clear_matches()
    db.clear_standings()
    db.clear_state()
    for t in teams:
        db.save_team(t)


def save_full_state(db: Database, teams: list[Team], standings: Standings,
                    next_round_idx: int, trainings_done: int,
                    standings_history: list[dict], free_agents: list[dict]) -> None:
    """Save the full game state to the database."""
    # Save teams
    for t in teams:
        db.save_team(t)
    # Save standings
    for r in standings.get_ranking():
        db.save_standings_entry(
            r["team_name"], r["points"], r["wins"], r["draws"],
            r["losses"], r["goals_for"], r["goals_against"],
        )
    # Save game state
    state = {
        "next_round_idx": next_round_idx,
        "trainings_done": trainings_done,
        "standings_history": standings_history,
        "free_agents": [
            {
                "name": p.name,
                "position": p.position.value,
                "passing": p.passing,
                "shooting": p.shooting,
                "defense": p.defense,
                "speed": p.speed,
                "stamina": p.stamina,
                "age": p.age,
                "morale": p.morale,
            }
            for p in free_agents
        ],
    }
    db.save_state(state)


def load_full_state(db: Database) -> dict | None:
    """Load the full game state from the database."""
    return db.load_state()


def run_game() -> None:
    """Main game loop."""
    db = Database(DB_PATH)
    db.init()

    # Load teams
    if not os.path.exists(TEAMS_JSON):
        console.print(f"[red]Errore: file {TEAMS_JSON} non trovato.[/red]")
        return

    teams = load_teams_from_json(TEAMS_JSON)

    # Check if we have a saved season
    saved_teams = db.load_all_teams()
    state = load_full_state(db)

    if saved_teams and len(saved_teams) == len(teams) and state:
        teams = saved_teams
        print_banner()
        console.print("  [green]✅ Stagione caricata dal database.[/green]")
        time.sleep(1)
    else:
        init_season(db, teams)
        print_banner()
        console.print("  [green]✅ Nuova stagione inizializzata.[/green]")
        time.sleep(1)

    # Generate calendar
    calendar = generate_calendar(teams, user_team_index=0)

    # Build standings from saved matches
    standings = Standings()
    saved_matches = db.load_matches()
    for sm in saved_matches:
        if sm["played"]:
            home_team = next((t for t in teams if t.name == sm["home_team"]), None)
            away_team = next((t for t in teams if t.name == sm["away_team"]), None)
            if home_team and away_team:
                m = Match(home_team=home_team, away_team=away_team,
                          home_score=sm["home_score"], away_score=sm["away_score"], played=True)
                standings.update(m)

    # Load state
    next_round_idx = state.get("next_round_idx", 0) if state else 0
    trainings_done = state.get("trainings_done", 0) if state else 0
    standings_history = state.get("standings_history", []) if state else []
    free_agents_data = state.get("free_agents", []) if state else []

    # Reconstruct free agents
    free_agents = []
    for fa in free_agents_data:
        free_agents.append(Player(
            name=fa["name"],
            position=Position(fa["position"]),
            passing=fa["passing"],
            shooting=fa["shooting"],
            defense=fa["defense"],
            speed=fa["speed"],
            stamina=fa["stamina"],
            age=fa["age"],
            morale=fa["morale"],
        ))

    # Find next unplayed round if not in state
    if not state:
        played_rounds = {sm["round"] for sm in saved_matches if sm["played"]}
        next_round_idx = 0
        for i, entry in enumerate(calendar):
            if entry["round"] not in played_rounds:
                next_round_idx = i
                break

    user_team = teams[0]

    while True:
        try:
            choice = main_menu(user_team, next_round_idx, trainings_done)
        except KeyboardInterrupt:
            # Ctrl+C: ask if user wants to save before exiting
            console.print("\n  [yellow]⚠️  Ctrl+C rilevato.[/yellow]")
            save_choice = Prompt.ask("  Salvare prima di uscire?", choices=["s", "n"], default="s")
            if save_choice.lower() == "s":
                save_full_state(db, teams, standings, next_round_idx, trainings_done,
                               standings_history, free_agents)
                console.print("  [green]💾 Stato salvato.[/green]")
            console.print("  [dim]Arrivederci! 🏑[/dim]")
            break
        if choice == "1":
            show_team(user_team)
        elif choice == "2":
            show_calendar(calendar, teams, db)
        elif choice == "3":
            show_standings(standings)
        elif choice == "4":
            show_stats(user_team)
        elif choice == "5":
            if next_round_idx >= len(calendar):
                clear_screen()
                print_banner()
                console.print(Panel(Text("  🏆 Stagione finita! Tutte le partite sono state giocate.", style="bold yellow"),
                                    border_style="yellow"))
                Prompt.ask("\n  Premi INVIO per tornare al menu", default="")
            else:
                entry = calendar[next_round_idx]
                home_idx = entry["home"]
                away_idx = entry["away"]
                if home_idx == 0:
                    opponent = teams[away_idx]
                    play_match(user_team, opponent, entry["round"], db, standings, seed=entry["round"] * 100 + 42)
                else:
                    opponent = teams[home_idx]
                    play_match(opponent, user_team, entry["round"], db, standings, seed=entry["round"] * 100 + 42)

                # Track standings position
                ranking = standings.get_ranking()
                for i, r in enumerate(ranking, 1):
                    if r["team_name"] == user_team.name:
                        standings_history.append({"round": entry["round"], "position": i})
                        break

                # Reset trainings for new round
                trainings_done = 0
                next_round_idx += 1
        elif choice == "6":
            choose_tactics(user_team)
        elif choice == "7":
            trainings_done, _ = show_training(user_team, trainings_done)
        elif choice == "8":
            if not free_agents:
                free_agents = generate_free_agents(5)
            show_transfer_market(user_team, free_agents)
        elif choice == "9":
            show_advanced_stats(user_team, standings_history)
        elif choice.lower() == "s":
            # Save and exit
            save_full_state(db, teams, standings, next_round_idx, trainings_done,
                           standings_history, free_agents)
            clear_screen()
            print_banner()
            console.print(Panel(Text("  💾 Stato salvato. Arrivederci! 🏑", style="bold green"),
                                border_style="green"))
            break
        elif choice == "0":
            clear_screen()
            console.print("  [dim]Arrivederci! 🏑[/dim]")
            break
        else:
            Prompt.ask("  [red]Scelta non valida.[/red] Premi INVIO per continuare", default="")


def main():
    parser = argparse.ArgumentParser(description="Field Hockey Manager")
    parser.add_argument("--init", action="store_true", help="Initialize the database with default teams")
    args = parser.parse_args()

    if args.init:
        if not os.path.exists(TEAMS_JSON):
            print(f"Errore: file {TEAMS_JSON} non trovato.")
            sys.exit(1)
        teams = load_teams_from_json(TEAMS_JSON)
        db = Database(DB_PATH)
        init_season(db, teams)
        print(f"Database inizializzato: {DB_PATH}")
        print(f"Squadre caricate: {len(teams)}")
        for t in teams:
            print(f"  {t.name} — {len(t.players)} giocatori, rating {t.team_rating()}")
        print("Pronto per giocare! Esegui 'python3 src/main.py' per iniziare.")
    else:
        run_game()


if __name__ == "__main__":
    main()