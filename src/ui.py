"""Rich terminal UI for Field Hockey Manager."""
from __future__ import annotations
import os
import sys
import time
import random
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from .models import Team, Player, Position, Match
from .database import Database
from .simulation import simulate_match
from .season import Standings, generate_calendar, train_player, TRAINING_ATTRIBUTES, MAX_TRAININGS_PER_WEEK

console = Console()

# Position colors
POS_STYLES: dict[Position, str] = {
    Position.GOALKEEPER: "bold red",
    Position.DEFENSE: "bold blue",
    Position.MIDFIELD: "bold green",
    Position.ATTACK: "bold yellow",
}

POS_EMOJI: dict[Position, str] = {
    Position.GOALKEEPER: "🥅",
    Position.DEFENSE: "🛡️",
    Position.MIDFIELD: "⚙️",
    Position.ATTACK: "⚔️",
}

# Training attribute labels (module constant to avoid duplication)
TRAINING_LABELS: dict[str, str] = {
    "passing": "Passaggio",
    "shooting": "Tiro",
    "defense": "Difesa",
    "speed": "Velocità",
    "stamina": "Resistenza",
}


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_banner() -> None:
    """Display the ASCII art banner."""
    banner = r"""
 ███████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██╗   ██╗███████╗██╗  ██╗██╗██████╗
██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██║   ██║██╔════╝██║ ██╔╝██║██╔══██╗
███████╗██║   ██║██████╔╝█████╗  ██║   ██║██║   ██║███████╗█████╔╝ ██║██║  ██║╔╝
╚════██║██║   ██║██╔══██╗██╔══╝  ██║   ██║██║   ██║╚════██║██╔═██╗ ██║██║██╔══██╗
███████║╚██████╔╝██║  ██║███████╗╚██████╔╝╚██████╔╝███████║██║  ██╗██║██║██████╔╝
╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝  ╚═══╝ ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝
    """
    clear_screen()
    console.print(Align.center(Text(banner, style="bold cyan")))
    console.print(Align.center(Text("🏒  Il manager di hockey su prato definitivo  🏑", style="bold magenta")))
    console.print()


def print_header(title: str) -> None:
    console.print(Panel(Text(f"🏑 {title}", style="bold white"), border_style="cyan", expand=True))


def print_separator() -> None:
    console.print("─" * 60, style="dim")


def rating_bar(value: int, max_val: int = 99) -> str:
    """Create a progress bar string for a rating: [████████░░] 82"""
    filled = int(round(value / max_val * 10))
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {value}"


def show_team(team: Team) -> None:
    """Display the team roster using a rich table."""
    clear_screen()
    print_header(f"Rosa {team.name}")

    # Team info panel
    info = Text()
    info.append(f"  ⭐ Rating Squadra: {team.team_rating()}\n", style="bold")
    info.append(f"  📊 Punti: {team.points}  ✅ W:{team.wins}  🤝 D:{team.draws}  ❌ L:{team.losses}\n")
    info.append(f"  ⚽ Gol Fatti: {team.goals_for}  🥅 Gol Subiti: {team.goals_against}\n")
    info.append(f"  💰 Budget: {team.budget} crediti  📋 Formazione: {team.formation}  🔥 Intensità: {team.intensity}")
    console.print(Panel(info, border_style="blue"))

    table = Table(box=box.ROUNDED, border_style="cyan", header_style="bold white on blue")
    table.add_column("Nome", style="white", min_width=20)
    table.add_column("Ruolo", style="bold", min_width=12)
    table.add_column("OVR", justify="center", style="bold")
    table.add_column("Pass", justify="center")
    table.add_column("Tiro", justify="center")
    table.add_column("Dif", justify="center")
    table.add_column("Vel", justify="center")
    table.add_column("Res", justify="center")
    table.add_column("Età", justify="center", style="magenta")
    table.add_column("Mor", justify="center")
    table.add_column("Gol", justify="center", style="bold yellow")
    table.add_column("Pres", justify="center")

    for p in team.players:
        pos_style = POS_STYLES.get(p.position, "")
        pos_emoji = POS_EMOJI.get(p.position, "")
        inj_marker = " 🔴" if p.injured else ""
        name_display = f"{p.name}{inj_marker}"
        morale_display = f"{p.morale}"
        if p.morale > 80:
            morale_display = f"[green]{p.morale}[/green]"
        elif p.morale < 30:
            morale_display = f"[red]{p.morale}[/red]"

        table.add_row(
            name_display,
            Text(f"{pos_emoji} {p.position.value}", style=pos_style),
            str(p.overall_rating()),
            str(p.passing),
            str(p.shooting),
            str(p.defense),
            str(p.speed),
            str(p.stamina),
            str(p.age),
            morale_display,
            str(p.goals),
            str(p.appearances),
        )

    console.print(table)
    Prompt.ask("\n  Premi INVIO per tornare al menu", default="")


def show_calendar(calendar: list[dict], teams: list[Team], db: Database) -> None:
    """Display the season calendar using a rich table."""
    clear_screen()
    print_header("📅 Calendario Stagione")

    matches = db.load_matches()
    played_by_round: dict[int, dict] = {}
    for m in matches:
        played_by_round[m["round"]] = m

    table = Table(box=box.ROUNDED, border_style="cyan", header_style="bold white on blue")
    table.add_column("Giornata", justify="center", style="bold")
    table.add_column("Casa", style="white")
    table.add_column("Risultato", justify="center")
    table.add_column("Ospite", style="white")

    for entry in calendar:
        rnd = entry["round"]
        home_name = teams[entry["home"]].name
        away_name = teams[entry["away"]].name
        if rnd in played_by_round:
            m = played_by_round[rnd]
            result = f"[bold green]{m['home_score']} - {m['away_score']}[/bold green]"
        else:
            result = "[dim]vs (da giocare)[/dim]"
        table.add_row(str(rnd), home_name, result, away_name)

    console.print(table)
    Prompt.ask("\n  Premi INVIO per tornare al menu", default="")


def show_standings(standings: Standings) -> None:
    """Display the league standings using a rich table."""
    clear_screen()
    print_header("🏆 Classifica")

    ranking = standings.get_ranking()
    if not ranking:
        console.print("  [dim]Nessuna partita giocata ancora.[/dim]")
    else:
        table = Table(box=box.ROUNDED, border_style="cyan", header_style="bold white on blue")
        table.add_column("#", justify="center", style="bold")
        table.add_column("Squadra", style="white", min_width=20)
        table.add_column("Pt", justify="center", style="bold yellow")
        table.add_column("G", justify="center")
        table.add_column("V", justify="center", style="green")
        table.add_column("N", justify="center", style="yellow")
        table.add_column("S", justify="center", style="red")
        table.add_column("GF", justify="center")
        table.add_column("GS", justify="center")
        table.add_column("DR", justify="center")

        for i, r in enumerate(ranking, 1):
            gd = r["goals_for"] - r["goals_against"]
            gd_str = f"[green]+{gd}[/green]" if gd > 0 else (f"[red]{gd}[/red]" if gd < 0 else "0")
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else str(i)))
            table.add_row(
                medal,
                r["team_name"],
                str(r["points"]),
                str(r["wins"] + r["draws"] + r["losses"]),
                str(r["wins"]),
                str(r["draws"]),
                str(r["losses"]),
                str(r["goals_for"]),
                str(r["goals_against"]),
                gd_str,
            )

        console.print(table)

    Prompt.ask("\n  Premi INVIO per tornare al menu", default="")


def show_stats(team: Team) -> None:
    """Display player statistics using rich tables."""
    clear_screen()
    print_header(f"📊 Statistiche {team.name}")

    # Top scorers table
    table = Table(box=box.ROUNDED, border_style="cyan", header_style="bold white on blue")
    table.add_column("Nome", style="white", min_width=20)
    table.add_column("Ruolo", style="bold", min_width=12)
    table.add_column("Gol", justify="center", style="bold yellow")
    table.add_column("Pres", justify="center")
    table.add_column("OVR", justify="center", style="bold")
    table.add_column("Rating Bar", justify="left")

    for p in sorted(team.players, key=lambda x: x.goals, reverse=True):
        pos_style = POS_STYLES.get(p.position, "")
        pos_emoji = POS_EMOJI.get(p.position, "")
        table.add_row(
            p.name,
            Text(f"{pos_emoji} {p.position.value}", style=pos_style),
            str(p.goals),
            str(p.appearances),
            str(p.overall_rating()),
            rating_bar(p.overall_rating()),
        )

    console.print(table)

    # Advanced stats
    console.print()
    stats_panel = Text()
    if team.players:
        top_scorer = max(team.players, key=lambda x: x.goals)
        most_apps = max(team.players, key=lambda x: x.appearances)
        avg_rating = sum(p.overall_rating() for p in team.players) / len(team.players)
        stats_panel.append(f"  🥅 Capocannoniere: {top_scorer.name} ({top_scorer.goals} gol)\n", style="bold yellow")
        stats_panel.append(f"  🏃 Più presenze: {most_apps.name} ({most_apps.appearances} presenze)\n", style="bold cyan")
        stats_panel.append(f"  📈 Rating medio squadra: {avg_rating:.1f}\n", style="bold green")
    console.print(Panel(stats_panel, title="Statistiche Avanzate", border_style="magenta"))

    Prompt.ask("\n  Premi INVIO per tornare al menu", default="")


def show_training(team: Team, trainings_done: int = 0) -> tuple[int, list[str]]:
    """Training menu. Returns (new_trainings_count, list of trained attributes)."""
    clear_screen()
    print_header(f"🏋️ Allenamenti — {team.name}")
    remaining = MAX_TRAININGS_PER_WEEK - trainings_done
    console.print(f"  Allenamenti rimanenti questa settimana: [bold]{remaining}[/bold]\n")

    if remaining <= 0:
        console.print("  [red]Hai raggiunto il limite di allenamenti per questa settimana![/red]")
        Prompt.ask("\n  Premi INVIO per tornare al menu", default="")
        return trainings_done, []

    console.print("  Attributi allenabili:")
    for i, attr in enumerate(TRAINING_ATTRIBUTES, 1):
        console.print(f"    [bold]{i}[/bold]. {TRAINING_LABELS[attr]} {attr}")

    console.print(f"    [bold]0[/bold]. Torna al menu\n")

    choice = IntPrompt.ask("  Scegli un attributo", default=0)
    if choice == 0 or choice < 1 or choice > len(TRAINING_ATTRIBUTES):
        return trainings_done, []

    attr = TRAINING_ATTRIBUTES[choice - 1]

    # Show players and let user pick
    clear_screen()
    print_header(f"🏋️ Allenamento {TRAINING_LABELS[attr]}")

    table = Table(box=box.ROUNDED, border_style="cyan", header_style="bold white on blue")
    table.add_column("#", justify="center", style="bold")
    table.add_column("Nome", style="white", min_width=20)
    table.add_column("Ruolo", style="bold", min_width=12)
    table.add_column("Età", justify="center", style="magenta")
    table.add_column(attr.capitalize(), justify="center")
    table.add_column("Status", justify="center")

    for i, p in enumerate(team.players, 1):
        pos_style = POS_STYLES.get(p.position, "")
        pos_emoji = POS_EMOJI.get(p.position, "")
        status = "[red]🔴 Infortunato[/red]" if p.injured else "[green]✅ Disponibile[/green]"
        table.add_row(
            str(i),
            p.name,
            Text(f"{pos_emoji} {p.position.value}", style=pos_style),
            str(p.age),
            str(getattr(p, attr)),
            status,
        )

    console.print(table)
    console.print()
    idx = IntPrompt.ask("  Scegli il giocatore (0 per annullare)", default=0)

    if idx == 0 or idx < 1 or idx > len(team.players):
        return trainings_done, []

    player = team.players[idx - 1]
    if player.injured:
        console.print("  [red]Il giocatore è infortunato e non può allenarsi![/red]")
        Prompt.ask("\n  Premi INVIO per continuare", default="")
        return trainings_done, []

    gain = train_player(player, attr)
    if gain > 0:
        console.print(f"\n  [green]✅ {player.name} ha migliorato {TRAINING_LABELS[attr]} di +{gain}! "
                      f"Nuovo valore: {getattr(player, attr)}[/green]")
    else:
        console.print(f"\n  [yellow]⚠️ {player.name} non è migliorato in {TRAINING_LABELS[attr]}.[/yellow]")

    Prompt.ask("\n  Premi INVIO per continuare", default="")
    return trainings_done + 1, [attr]


def show_transfer_market(team: Team, free_agents: list[Player]) -> Player | None:
    """Display the transfer market. Returns a purchased player or None."""
    clear_screen()
    print_header("💰 Mercato Trasferimenti")
    console.print(f"  Budget disponibile: [bold green]{team.budget}[/bold green] crediti\n")

    table = Table(box=box.ROUNDED, border_style="cyan", header_style="bold white on blue")
    table.add_column("#", justify="center", style="bold")
    table.add_column("Nome", style="white", min_width=20)
    table.add_column("Ruolo", style="bold", min_width=12)
    table.add_column("OVR", justify="center", style="bold")
    table.add_column("Età", justify="center", style="magenta")
    table.add_column("Prezzo", justify="center", style="bold yellow")

    from .season import player_price
    for i, p in enumerate(free_agents, 1):
        pos_style = POS_STYLES.get(p.position, "")
        pos_emoji = POS_EMOJI.get(p.position, "")
        price = player_price(p)
        table.add_row(
            str(i),
            p.name,
            Text(f"{pos_emoji} {p.position.value}", style=pos_style),
            str(p.overall_rating()),
            str(p.age),
            f"{price} 💰",
        )

    console.print(table)
    console.print()
    idx = IntPrompt.ask("  Scegli un giocatore da comprare (0 per annullare)", default=0)

    if idx == 0 or idx < 1 or idx > len(free_agents):
        return None

    chosen = free_agents[idx - 1]
    price = player_price(chosen)

    if team.budget < price:
        console.print(f"  [red]❌ Budget insufficiente! Ti servono {price - team.budget} crediti in più.[/red]")
        Prompt.ask("\n  Premi INVIO per continuare", default="")
        return None

    # Choose which player to replace
    clear_screen()
    print_header(f"Sostituisci giocatore per acquistare {chosen.name}")
    console.print(f"  Nuovo giocatore: [bold]{chosen.name}[/bold] OVR:{chosen.overall_rating()} "
                  f"{chosen.position.value} Età:{chosen.age}\n")
    console.print("  Scegli il giocatore da sostituire:\n")

    table2 = Table(box=box.ROUNDED, border_style="cyan", header_style="bold white on blue")
    table2.add_column("#", justify="center", style="bold")
    table2.add_column("Nome", style="white", min_width=20)
    table2.add_column("Ruolo", style="bold", min_width=12)
    table2.add_column("OVR", justify="center")
    table2.add_column("Età", justify="center", style="magenta")

    for i, p in enumerate(team.players, 1):
        pos_style = POS_STYLES.get(p.position, "")
        pos_emoji = POS_EMOJI.get(p.position, "")
        table2.add_row(
            str(i),
            p.name,
            Text(f"{pos_emoji} {p.position.value}", style=pos_style),
            str(p.overall_rating()),
            str(p.age),
        )

    console.print(table2)
    console.print()
    replace_idx = IntPrompt.ask("  Scegli chi sostituire (0 per annullare)", default=0)

    if replace_idx == 0 or replace_idx < 1 or replace_idx > len(team.players):
        return None

    replaced = team.players[replace_idx - 1]
    team.players[replace_idx - 1] = chosen
    team.budget -= price

    # BUG-3 fix: Remove purchased player from free_agents list
    free_agents.pop(idx - 1)

    console.print(f"\n  [green]✅ {chosen.name} sostituisce {replaced.name}! "
                  f"Budget rimanente: {team.budget} crediti[/green]")
    Prompt.ask("\n  Premi INVIO per continuare", default="")
    return chosen


def choose_tactics(team: Team) -> None:
    """Let the user choose formation and intensity before a match."""
    clear_screen()
    print_header("📋 Tattiche Pre-Partita")

    console.print("  Formazioni disponibili:")
    formations = ["4-3-3", "4-4-2", "3-5-2", "5-3-2"]
    formation_info = {
        "4-3-3": "⚡ Più attacco",
        "4-4-2": "⚖️ Bilanciata",
        "3-5-2": "⚙️ Centrocampo forte",
        "5-3-2": "🛡️ Più difesa",
    }
    for i, f in enumerate(formations, 1):
        marker = " ← attuale" if f == team.formation else ""
        console.print(f"    [bold]{i}[/bold]. {f} — {formation_info[f]}{marker}")

    choice = IntPrompt.ask("\n  Scegli formazione", default=formations.index(team.formation) + 1)
    if 1 <= choice <= len(formations):
        team.formation = formations[choice - 1]

    console.print("\n  Intensità disponibili:")
    intensities = ["Difensiva", "Bilanciata", "Offensiva"]
    intensity_info = {
        "Difensiva": "🛡️ Meno gol subiti, meno gol fatti",
        "Bilanciata": "⚖️ Equilibrio",
        "Offensiva": "⚔️ Più gol fatti, più gol subiti",
    }
    for i, inten in enumerate(intensities, 1):
        marker = " ← attuale" if inten == team.intensity else ""
        console.print(f"    [bold]{i}[/bold]. {inten} — {intensity_info[inten]}{marker}")

    choice = IntPrompt.ask("\n  Scegli intensità", default=intensities.index(team.intensity) + 1)
    if 1 <= choice <= len(intensities):
        team.intensity = intensities[choice - 1]

    console.print(f"\n  [green]✅ Formazione: {team.formation} | Intensità: {team.intensity}[/green]")
    Prompt.ask("\n  Premi INVIO per continuare", default="")


def show_match_result(match: Match, team: Team) -> None:
    """Display match result in a rich panel."""
    is_home = match.home_team.name == team.name
    our_score = match.home_score if is_home else match.away_score
    their_score = match.away_score if is_home else match.home_score

    if our_score > their_score:
        result_text = "VITTORIA! 🎉"
        result_style = "bold green"
    elif our_score < their_score:
        result_text = "SCONFITTA 😔"
        result_style = "bold red"
    else:
        result_text = "PAREGGIO 🤝"
        result_style = "bold yellow"

    header = f"{match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}"
    console.print(Panel(Text(f"  {result_text}\n  {header}", style=result_style),
                        title="⚽ Risultato Partita", border_style=result_style))

    # Events
    if match.events:
        events_table = Table(box=box.ROUNDED, border_style="dim", header_style="bold")
        events_table.add_column("Q", justify="center", style="dim")
        events_table.add_column("Min", justify="center")
        events_table.add_column("Evento", style="white")
        events_table.add_column("Squadra", style="dim")

        for e in match.events:
            if e["type"] == "goal":
                side = match.home_team.name if e["team"] == "home" else match.away_team.name
                event_str = f"⚽ Gol di {e['scorer']}"
                events_table.add_row(f"Q{e['quarter']}", str(e["minute"]), event_str, side)
            elif e["type"] == "injury":
                side = match.home_team.name if e["team"] == "home" else match.away_team.name
                event_str = f"🔴 Infortunio: {e['player']} ({e['duration']} partite)"
                events_table.add_row("—", "—", event_str, side)

        console.print(events_table)
    else:
        console.print("  [dim]Nessun gol nella partita.[/dim]")


def play_match(
    team: Team,
    opponent: Team,
    round_num: int,
    db: Database,
    standings: Standings,
    seed: int = 0,
) -> None:
    """Simulate and display a match result with animation."""
    clear_screen()
    print_header(f"🏟️ Partita: {team.name} vs {opponent.name}")

    # Loading animation
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Simulazione partita in corso..."), console=console) as progress:
        progress.add_task("simulating", total=1)
        time.sleep(1.5)  # dramatic effect

    match = simulate_match(
        team, opponent, seed=seed,
        home_formation=team.formation, home_intensity=team.intensity,
        away_formation=opponent.formation, away_intensity=opponent.intensity,
    )

    console.print()
    show_match_result(match, team)

    # Determine result for morale from each team's perspective
    # team is the first param, opponent is the second
    # simulate_match always puts first param as home_team
    team_is_home = match.home_team.name == team.name
    team_score = match.home_score if team_is_home else match.away_score
    opp_score = match.away_score if team_is_home else match.home_score

    if team_score > opp_score:
        team_morale_delta = 10
        opponent_morale_delta = -10
    elif team_score < opp_score:
        team_morale_delta = -10
        opponent_morale_delta = 10
    else:
        team_morale_delta = 0
        opponent_morale_delta = 0

    # Update team stats — correctly identify home/away
    if match.home_score > match.away_score:
        match.home_team.wins += 1
        match.home_team.points += 3
        match.away_team.losses += 1
    elif match.home_score < match.away_score:
        match.away_team.wins += 1
        match.away_team.points += 3
        match.home_team.losses += 1
    else:
        match.home_team.draws += 1
        match.away_team.draws += 1
        match.home_team.points += 1
        match.away_team.points += 1
    match.home_team.goals_for += match.home_score
    match.home_team.goals_against += match.away_score
    match.away_team.goals_for += match.away_score
    match.away_team.goals_against += match.home_score

    # Update player appearances and goals
    for p in match.home_team.get_starters():
        p.appearances += 1
    for p in match.away_team.get_starters():
        p.appearances += 1
    for e in match.events:
        if e["type"] == "goal":
            target_team = match.home_team if e["team"] == "home" else match.away_team
            for p in target_team.players:
                if p.name == e["scorer"]:
                    p.goals += 1
                    break

    # Apply morale changes to both teams
    for p in team.players:
        p.apply_morale(team_morale_delta)
    for p in opponent.players:
        p.apply_morale(opponent_morale_delta)

    # Heal injured players by one match
    for p in team.players:
        p.heal_one_match()
    for p in opponent.players:
        p.heal_one_match()

    # Save to DB
    db.save_match(match, round_num=round_num)
    db.save_team(team)
    db.save_team(opponent)
    standings.update(match)

    Prompt.ask("\n  Premi INVIO per continuare", default="")


def show_advanced_stats(team: Team, standings_history: list[dict]) -> None:
    """Display advanced statistics including chart of standings over time."""
    clear_screen()
    print_header(f"📈 Statistiche Avanzate — {team.name}")

    # Season stats
    table = Table(box=box.ROUNDED, border_style="cyan", header_style="bold white on blue")
    table.add_column("Statistica", style="white", min_width=25)
    table.add_column("Valore", justify="center", style="bold")

    if team.players:
        top_scorer = max(team.players, key=lambda x: x.goals)
        most_apps = max(team.players, key=lambda x: x.appearances)
        avg_rating = sum(p.overall_rating() for p in team.players) / len(team.players)
        table.add_row("🥅 Capocannoniere squadra", f"{top_scorer.name} ({top_scorer.goals} gol)")
        table.add_row("🏃 Più presenze", f"{most_apps.name} ({most_apps.appearances} presenze)")
        table.add_row("📊 Rating medio rosa", f"{avg_rating:.1f}")
        table.add_row("⚽ Gol fatti totali", str(team.goals_for))
        table.add_row("🥅 Gol subiti totali", str(team.goals_against))
        table.add_row("✅ Vittorie", str(team.wins))
        table.add_row("🤝 Pareggi", str(team.draws))
        table.add_row("❌ Sconfitte", str(team.losses))

    console.print(table)

    # Standings position chart
    if standings_history:
        console.print()
        chart = Text()
        chart.append("  📊 Posizione in classifica nel tempo:\n\n", style="bold cyan")
        for entry in standings_history:
            rnd = entry["round"]
            pos = entry["position"]
            # Build a simple bar chart
            bar = "▏" * (pos) + f" {pos}°"
            chart.append(f"  Giornata {rnd:>2}: {bar}\n")
        console.print(Panel(chart, border_style="green", title="Andamento Stagione"))

    Prompt.ask("\n  Premi INVIO per tornare al menu", default="")


def main_menu(team: Team, next_round: int, trainings_done: int) -> str:
    """Display the main menu and return the user's choice."""
    clear_screen()
    print_banner()

    menu_panel = Text()
    menu_panel.append("  🏟️  1. Visualizza Rosa\n", style="white")
    menu_panel.append("  📅  2. Visualizza Calendario\n", style="white")
    menu_panel.append("  🏆  3. Visualizza Classifica\n", style="white")
    menu_panel.append("  📊  4. Statistiche Giocatori\n", style="white")
    menu_panel.append("  ⚽  5. Gioca Prossima Partita\n", style="bold green")
    menu_panel.append("  📋  6. Tattiche\n", style="white")
    menu_panel.append("  🏋️  7. Allenamenti", style="white")
    if trainings_done >= MAX_TRAININGS_PER_WEEK:
        menu_panel.append(" [dim](limite raggiunto)[/dim]", style="dim")
    menu_panel.append("\n")
    menu_panel.append("  💰  8. Mercato Trasferimenti\n", style="white")
    menu_panel.append("  📈  9. Statistiche Avanzate\n", style="white")
    menu_panel.append("  💾  S. Salva e Esci\n", style="bold yellow")
    menu_panel.append("  🚪  0. Esci\n", style="white")

    console.print(Panel(menu_panel, title=f"🏒 Field Hockey Manager — {team.name}", border_style="cyan"))
    return Prompt.ask("  Scelta", default="")