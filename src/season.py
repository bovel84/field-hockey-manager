"""Season management: calendar generation, standings, and training."""
from __future__ import annotations
import json
import math
import os
import random
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional
from .models import Match, Team, Player, Position
from .simulation import simulate_match


# ---------------------------------------------------------------------
# League loading from data/leagues.json
# ---------------------------------------------------------------------

_LEAGUES_CACHE: dict[str, dict] | None = None


def _load_leagues_file() -> dict:
    """Load and cache data/leagues.json."""
    global _LEAGUES_CACHE
    if _LEAGUES_CACHE is not None:
        return _LEAGUES_CACHE
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    path = os.path.join(project_root, "data", "leagues.json")
    with open(path, "r", encoding="utf-8") as f:
        _LEAGUES_CACHE = json.load(f)
    return _LEAGUES_CACHE


def list_leagues() -> list[dict]:
    """Return a list of available leagues with id and name.

    Returns:
        List of dicts: [{"id": "serie_a_elite", "name": "Serie A Élite", "team_count": 8}, ...]
    """
    data = _load_leagues_file()
    result = []
    for league_id, league in data.get("leagues", {}).items():
        result.append({
            "id": league_id,
            "name": league.get("name", league_id),
            "team_count": len(league.get("teams", [])),
        })
    return result


def load_league(league_id: str) -> dict:
    """Load league data from data/leagues.json.

    Args:
        league_id: e.g. "serie_a_elite", "hoofdklasse", "ehl"
    Returns:
        League dict with keys: name, country, teams (list of team names), girone
    Raises:
        KeyError if league_id not found.
    """
    data = _load_leagues_file()
    leagues = data.get("leagues", {})
    if league_id not in leagues:
        raise KeyError(f"League '{league_id}' not found in data/leagues.json")
    return leagues[league_id]


def _load_league_teams(league_id: str) -> list[Team]:
    """Build Team objects from data/leagues.json for a given league.

    Maps position codes: GK→GOALKEEPER, DEF→DEFENSE, MID→MIDFIELD, FWD→ATTACK.
    """
    _POS_MAP = {
        "GK": Position.GOALKEEPER,
        "DEF": Position.DEFENSE,
        "MID": Position.MIDFIELD,
        "FWD": Position.ATTACK,
    }
    data = _load_leagues_file()
    league = data["leagues"][league_id]
    team_names = league["teams"]
    all_teams_data = {t["name"]: t for t in data.get("teams", [])}

    teams: list[Team] = []
    for tname in team_names:
        tdata = all_teams_data.get(tname)
        if tdata is None:
            teams.append(Team(name=tname, players=[]))
            continue
        players = []
        for pdata in tdata.get("players", []):
            pos_str = pdata["position"]
            pos = _POS_MAP.get(pos_str, Position.MIDFIELD)
            players.append(Player(
                name=pdata["name"],
                position=pos,
                passing=pdata.get("passing", 50),
                shooting=pdata.get("shooting", 50),
                defense=pdata.get("defense", 50),
                speed=pdata.get("speed", 50),
                stamina=pdata.get("stamina", 50),
                age=pdata.get("age", 25),
                morale=pdata.get("morale", 50),
                potential=pdata.get("potential", 99),
            ))
        team = Team(
            name=tdata["name"],
            players=players,
            budget=tdata.get("budget", 500),
            prestige=tdata.get("prestige", 0),
            rivals=tdata.get("rivals", []),
        )
        teams.append(team)
    return teams


def init_season_for_league(league_id: str, team_name: str) -> tuple[list[Team], "Standings", int, list[dict]]:
    """Initialize a new season for a specific league and chosen team.

    Loads teams from data/leagues.json, generates the calendar, and
    initializes empty standings.

    Args:
        league_id: The league identifier (e.g. "serie_a_elite").
        team_name: The name of the user's chosen team.
    Returns:
        Tuple of (teams list, Standings, user_team_index, calendar).
    Raises:
        ValueError if team_name not found in the league.
    """
    teams = _load_league_teams(league_id)
    user_idx = -1
    for i, t in enumerate(teams):
        if t.name == team_name:
            user_idx = i
            break
    if user_idx == -1:
        raise ValueError(f"Team '{team_name}' not found in league '{league_id}'")
    standings = Standings()
    calendar = generate_calendar(teams, user_idx)
    return teams, standings, user_idx, calendar


def generate_calendar(teams: list[Team], user_team_index: int = 0) -> list[dict]:
    """
    Generate a round-robin calendar.

    Supports leagues with 2-20 teams.
    - 6 teams → 10 matches (home and away vs every other team)
    - 8 teams → 14 matches
    - 12 teams → 22 matches
    - 20 teams → 38 matches

    Returns a list of dicts: {"round": int, "home": team_index, "away": team_index}
    """
    n = len(teams)
    if n < 2:
        return []

    # All unique pairs (home and away)
    matches: list[dict] = []
    round_num = 1

    # First leg: each pair plays once
    pairs = list(combinations(range(n), 2))
    # Distribute across rounds — n//2 matches per round
    per_round = n // 2
    for i in range(0, len(pairs), per_round):
        chunk = pairs[i : i + per_round]
        for home_idx, away_idx in chunk:
            matches.append({"round": round_num, "home": home_idx, "away": away_idx})
        round_num += 1

    # Second leg: reverse fixtures
    reverse_pairs = [(b, a) for a, b in pairs]
    for i in range(0, len(reverse_pairs), per_round):
        chunk = reverse_pairs[i : i + per_round]
        for home_idx, away_idx in chunk:
            matches.append({"round": round_num, "home": home_idx, "away": away_idx})
        round_num += 1

    return matches


@dataclass
class Standings:
    """League standings tracker."""
    _teams: dict[str, dict] = field(default_factory=dict)

    def _ensure(self, name: str) -> dict:
        if name not in self._teams:
            self._teams[name] = {
                "points": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
            }
        return self._teams[name]

    def update(self, match: Match) -> None:
        """Update standings after a match."""
        home = self._ensure(match.home_team.name)
        away = self._ensure(match.away_team.name)

        home["goals_for"] += match.home_score
        home["goals_against"] += match.away_score
        away["goals_for"] += match.away_score
        away["goals_against"] += match.home_score

        if match.home_score > match.away_score:
            home["points"] += 3
            home["wins"] += 1
            away["losses"] += 1
        elif match.home_score < match.away_score:
            away["points"] += 3
            away["wins"] += 1
            home["losses"] += 1
        else:
            home["points"] += 1
            away["points"] += 1
            home["draws"] += 1
            away["draws"] += 1

    def get_points(self, name: str) -> int:
        return self._teams.get(name, {}).get("points", 0)

    def get_wins(self, name: str) -> int:
        return self._teams.get(name, {}).get("wins", 0)

    def get_draws(self, name: str) -> int:
        return self._teams.get(name, {}).get("draws", 0)

    def get_losses(self, name: str) -> int:
        return self._teams.get(name, {}).get("losses", 0)

    def get_goals_for(self, name: str) -> int:
        return self._teams.get(name, {}).get("goals_for", 0)

    def get_goals_against(self, name: str) -> int:
        return self._teams.get(name, {}).get("goals_against", 0)

    def get_ranking(self) -> list[dict]:
        """Return teams sorted by points, then goal difference, then goals for."""
        ranking = []
        for name, stats in self._teams.items():
            ranking.append({
                "team_name": name,
                "points": stats["points"],
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
                "goals_for": stats["goals_for"],
                "goals_against": stats["goals_against"],
                "goal_difference": stats["goals_for"] - stats["goals_against"],
            })
        ranking.sort(key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]), reverse=True)
        return ranking


# ---------------------------------------------------------------------
# Training system
# ---------------------------------------------------------------------

TRAINING_ATTRIBUTES = ["passing", "shooting", "defense", "speed", "stamina"]
MAX_TRAININGS_PER_WEEK = 3


def train_player(player: Player, attribute: str, rng: random.Random | None = None) -> int:
    """
    Train a player in a specific attribute.

    Improvement is +1 or +2 based on age:
    - <=22 years: 70% chance +2, 30% chance +1
    - 23-30 years: 60% chance +1, 10% chance +2, 30% chance 0
    - >30 years: 50% chance +1, 50% chance 0

    Training cannot raise an attribute above the player's potential.

    Returns the amount improved (0, 1, or 2).
    """
    if rng is None:
        rng = random.Random()
    if attribute not in TRAINING_ATTRIBUTES:
        return 0
    if not hasattr(player, attribute):
        return 0

    age = player.age
    if age <= 22:
        gain = 2 if rng.random() < 0.70 else 1
    elif age <= 30:
        roll = rng.random()
        if roll < 0.60:
            gain = 1
        elif roll < 0.70:
            gain = 2
        else:
            gain = 0
    else:
        gain = 1 if rng.random() < 0.50 else 0

    current = getattr(player, attribute)
    # Cap at player's potential — cannot exceed it through training
    max_val = min(99, player.potential)
    new_val = min(max_val, current + gain)
    setattr(player, attribute, new_val)
    return new_val - current


def season_aging(player: Player) -> None:
    """Apply end-of-season aging effects.
    - Players >30 degrade by -1 in all attributes (min 20).
    """
    if player.age > 30:
        for attr in TRAINING_ATTRIBUTES:
            current = getattr(player, attr)
            setattr(player, attr, max(20, current - 1))


def age_player_one_year(player: Player) -> None:
    """Increment player age by 1 year."""
    player.age += 1


# ---------------------------------------------------------------------
# Transfer market
# ---------------------------------------------------------------------

_FIRST_NAMES = [
    "Marco", "Luca", "Andrea", "Davide", "Stefano", "Paolo", "Federico",
    "Simone", "Giovanni", "Matteo", "Alessandro", "Filippo", "Lorenzo",
    "Francesco", "Giorgio", "Roberto", "Gianluca", "Fabio", "Mattia",
]
_LAST_NAMES = [
    "Rossi", "Bianchi", "Ferrari", "Russo", "Conti", "Marino", "Greco",
    "Costa", "Fontana", "Galli", "Moretti", "Bellini", "Romano", "Esposito",
    "Sacco", "De Luca", "Mancini", "Villa", "Rinaldi", "Lombardi",
]


def generate_free_agents(count: int = 5, rng: random.Random | None = None) -> list[Player]:
    """Generate random free agents for the transfer market.

    Each free agent gets a potential value: for young players (<=22),
    potential is higher than their current rating, representing room to grow.
    For older players, potential is close to their current rating.
    """
    if rng is None:
        rng = random.Random()
    positions = list(Position)
    agents = []
    for _ in range(count):
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        pos = rng.choice(positions)
        base_rating = rng.randint(55, 88)
        age = rng.randint(16, 35)
        # Young players get higher potential, older ones get potential close to current
        if age <= 22:
            potential = min(99, base_rating + rng.randint(5, 15))
        elif age < 28:
            potential = min(99, base_rating + rng.randint(0, 5))
        else:
            potential = min(99, base_rating + rng.randint(0, 2))
        agent = Player(
            name=name,
            position=pos,
            passing=base_rating + rng.randint(-5, 5),
            shooting=base_rating + rng.randint(-5, 5),
            defense=base_rating + rng.randint(-5, 5),
            speed=base_rating + rng.randint(-5, 5),
            stamina=base_rating + rng.randint(-5, 5),
            age=age,
            morale=50,
            potential=potential,
        )
        agents.append(agent)
    return agents


def player_price(player: Player) -> int:
    """Calculate the transfer price of a player based on rating and age."""
    base = player.overall_rating() * 5
    # Younger players cost more
    if player.age <= 22:
        base = int(base * 1.3)
    elif player.age > 30:
        base = int(base * 0.7)
    return max(10, base)


# ---------------------------------------------------------------------
# Youth Academy
# ---------------------------------------------------------------------

def generate_youth_prospects(team: Team, rng: random.Random | None = None, seed: int | None = None) -> list[Player]:
    """Generate 1-2 youth prospects for a team's academy.

    Each prospect is 16-18 years old with rating 40-60 and high potential
    (70-95). These players can be promoted to the first team or left
    in the academy for development.

    Args:
        team: The team generating youth prospects (used for prestige-based bonuses).
        rng: Optional random number generator for deterministic tests.
        seed: Optional integer seed — if provided, creates a deterministic RNG
              (ignored if *rng* is also supplied).
    Returns:
        List of 1-2 young Player objects.
    """
    if rng is None and seed is not None:
        rng = random.Random(seed)
    if rng is None:
        rng = random.Random()
    count = rng.randint(1, 2)
    positions = list(Position)
    prospects = []
    for _ in range(count):
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        pos = rng.choice(positions)
        base_rating = rng.randint(40, 60)
        # High potential: 70-95, scaled by team prestige
        prestige_bonus = min(10, team.prestige // 10)
        potential = min(95, rng.randint(70, 85) + prestige_bonus)
        prospect = Player(
            name=name,
            position=pos,
            passing=base_rating + rng.randint(-3, 3),
            shooting=base_rating + rng.randint(-3, 3),
            defense=base_rating + rng.randint(-3, 3),
            speed=base_rating + rng.randint(-3, 3),
            stamina=base_rating + rng.randint(-3, 3),
            age=rng.randint(16, 18),
            morale=60,
            potential=potential,
        )
        prospects.append(prospect)
    return prospects


def promote_youth_player(team: Team, prospect: Player) -> bool:
    """Promote a youth prospect to the first team.

    Moves a player from the team's youth academy (youth_players list)
    to the main squad (players list).

    Args:
        team: The team promoting the player.
        prospect: The youth player to promote.
    Returns:
        True if promotion was successful, False if player not found in youth_players.
    """
    if prospect not in team.youth_players:
        return False
    team.youth_players.remove(prospect)
    team.players.append(prospect)
    return True


# ---------------------------------------------------------------------
# Playoff system (top 4 teams, semifinals + final)
# ---------------------------------------------------------------------

@dataclass
class PlayoffBracket:
    """Bracket for the championship playoff."""
    semifinal1: Match
    semifinal2: Match
    final: Match | None = None
    winner: Team | None = None

    def __str__(self) -> str:
        """Human-readable bracket display."""
        lines: list[str] = []
        lines.append("  Semifinale 1:")
        lines.append(f"    {self.semifinal1}")
        lines.append("  Semifinale 2:")
        lines.append(f"    {self.semifinal2}")
        if self.final:
            lines.append("  Finale:")
            lines.append(f"    {self.final}")
        if self.winner:
            lines.append(f"  Vincitore: {self.winner.name}")
        return "\n".join(lines)


def generate_playoff_bracket(teams: list[Team], standings: Standings, rng: random.Random | None = None) -> PlayoffBracket:
    """Generate a playoff bracket for the top 4 teams.

    Seedings: 1st vs 4th, 2nd vs 3rd (single-leg semifinals).
    The final is also single-leg.

    If fewer than 4 teams are available, a smaller bracket is created:
    - 3 teams: 1st gets a bye to the final, 2nd vs 3rd play a semifinal.
    - 2 teams: a single final match.

    Args:
        teams: All teams in the league.
        standings: Final standings after the regular season.
        rng: Optional RNG for deterministic bracket generation.
    Returns:
        A PlayoffBracket with semifinal matches set up.
    """
    if rng is None:
        rng = random.Random()
    ranking = standings.get_ranking()
    if len(ranking) < 2:
        raise ValueError("Need at least 2 teams for playoff bracket")

    # Map team names to Team objects
    team_map = {t.name: t for t in teams}
    top_names = [r["team_name"] for r in ranking]
    top_teams = [team_map[name] for name in top_names if name in team_map]
    if len(top_teams) < 2:
        raise ValueError("Could not find enough teams for playoff bracket")

    if len(top_teams) >= 4:
        # Standard bracket: 1st vs 4th, 2nd vs 3rd
        sf1 = Match(home_team=top_teams[0], away_team=top_teams[3])
        sf2 = Match(home_team=top_teams[1], away_team=top_teams[2])
    elif len(top_teams) == 3:
        # 3 teams: 1st gets a bye, 2nd vs 3rd play semifinal
        # Use a dummy bye match for sf1 (1st advances automatically)
        sf1 = Match(home_team=top_teams[0], away_team=top_teams[0])  # bye
        sf1.home_score = 1
        sf1.away_score = 0
        sf1.played = True
        sf2 = Match(home_team=top_teams[1], away_team=top_teams[2])
    else:  # 2 teams
        # Single final: use sf1 as the final, sf2 is a placeholder
        sf1 = Match(home_team=top_teams[0], away_team=top_teams[1])
        sf2 = Match(home_team=top_teams[0], away_team=top_teams[0])  # bye placeholder
        sf2.home_score = 1
        sf2.away_score = 0
        sf2.played = True

    return PlayoffBracket(semifinal1=sf1, semifinal2=sf2)


def simulate_playoff(bracket: PlayoffBracket, seed: int = 0) -> Team:
    """Simulate a playoff bracket and return the winner.

    Semifinals and final are single-leg matches. The higher-seeded team
    gets home advantage. Byes (pre-played matches) are respected.

    Args:
        bracket: A PlayoffBracket with semifinals set up.
        seed: Random seed for deterministic simulation.
    Returns:
        The winning Team.
    """
    # Simulate semifinal 1 (skip if already played — bye match)
    if not bracket.semifinal1.played:
        sf1 = simulate_match(bracket.semifinal1.home_team, bracket.semifinal1.away_team,
                             seed=seed)
        bracket.semifinal1.home_score = sf1.home_score
        bracket.semifinal1.away_score = sf1.away_score
        bracket.semifinal1.played = True
        bracket.semifinal1.events = sf1.events
    # In case of draw, home team advances (higher seed advantage)
    sf1_winner = bracket.semifinal1.home_team if bracket.semifinal1.home_score >= bracket.semifinal1.away_score else bracket.semifinal1.away_team

    # Simulate semifinal 2 (skip if already played — bye match)
    if not bracket.semifinal2.played:
        sf2 = simulate_match(bracket.semifinal2.home_team, bracket.semifinal2.away_team,
                             seed=seed + 1)
        bracket.semifinal2.home_score = sf2.home_score
        bracket.semifinal2.away_score = sf2.away_score
        bracket.semifinal2.played = True
        bracket.semifinal2.events = sf2.events
    sf2_winner = bracket.semifinal2.home_team if bracket.semifinal2.home_score >= bracket.semifinal2.away_score else bracket.semifinal2.away_team

    # Simulate final
    final = Match(home_team=sf1_winner, away_team=sf2_winner)
    final_result = simulate_match(sf1_winner, sf2_winner, seed=seed + 2)
    final.home_score = final_result.home_score
    final.away_score = final_result.away_score
    final.played = True
    final.events = final_result.events
    bracket.final = final

    # Determine winner (home team = higher seed, wins ties)
    if final.home_score >= final.away_score:
        bracket.winner = sf1_winner
    else:
        bracket.winner = sf2_winner
    return bracket.winner


# ---------------------------------------------------------------------
# Coppa Nazionale (knockout cup)
# ---------------------------------------------------------------------

@dataclass
class CupBracket:
    """Bracket for the Coppa Nazionale (single-elimination knockout cup)."""
    rounds: list[list[Match]] = field(default_factory=list)  # Each round is a list of matches
    winner: Team | None = None

    def __str__(self) -> str:
        """Human-readable bracket display showing each round and its matches."""
        lines: list[str] = []
        for i, round_matches in enumerate(self.rounds):
            label = f"Round {i + 1}"
            lines.append(f"  {label}:")
            for m in round_matches:
                lines.append(f"    {m}")
        if self.winner:
            lines.append(f"  Vincitore: {self.winner.name}")
        return "\n".join(lines) if lines else "CupBracket (vuoto)"


def generate_cup_bracket(teams: list[Team], rng: random.Random | None = None) -> CupBracket:
    """Generate a random knockout bracket for the Coppa Nazionale.

   All teams are seeded randomly (single-elimination, single-leg matches).
   With 6 teams, the bracket has: 2 teams get a bye to semifinals,
   4 teams play in the quarterfinals.

    Args:
        teams: All participating teams (minimum 2).
        rng: Optional RNG for deterministic draws.
    Returns:
       A CupBracket with all rounds set up (matches not yet played).
    """
    if rng is None:
        rng = random.Random()
    if len(teams) < 2:
        raise ValueError("Need at least 2 teams for a cup bracket")

    shuffled = list(teams)
    rng.shuffle(shuffled)
    n = len(shuffled)

    # Next power of 2 >= n. Pad with None (bye) to fill the bracket.
    bracket_size = 2 ** math.ceil(math.log2(n)) if n > 1 else 2
    slots: list[Team | None] = list(shuffled) + [None] * (bracket_size - n)

    # Build rounds: each round halves the field.
    # Round 1 has all teams (some matches are byes with away=None).
    # Subsequent rounds have placeholder None that simulate_cup fills in.
    bracket = CupBracket()
    current = slots[:]

    while len(current) > 1:
        round_matches: list[Match] = []
        next_round: list[Team | None] = []
        for i in range(0, len(current), 2):
            home = current[i]
            away = current[i + 1] if i + 1 < len(current) else None
            m = Match(home_team=home, away_team=away)
            round_matches.append(m)
            next_round.append(None)  # placeholder for winner
        bracket.rounds.append(round_matches)
        current = next_round

    return bracket


def generate_cup_headlines(bracket: CupBracket) -> list[str]:
    """Generate narrative headlines for cup rounds.

    Iterates through the cup bracket rounds, identifying upsets (lower-rated
    team beating a higher-rated team) and the final. Returns a list of
    headline strings.

    Args:
        bracket: A simulated CupBracket with all matches played.
    Returns:
        List of headline strings.
    """
    headlines: list[str] = []
    round_names = [
        "Quarti di Finale",
        "Semifinale",
        "Finale",
    ]
    for round_idx, round_matches in enumerate(bracket.rounds):
        round_name = round_names[round_idx] if round_idx < len(round_names) else f"Round {round_idx + 1}"
        for m in round_matches:
            if not m.played:
                continue
            if m.home_team is None or m.away_team is None:
                continue
            # Skip bye matches
            if m.home_team.name == m.away_team.name:
                continue
            winner = m.home_team if m.home_score >= m.away_score else m.away_team
            loser = m.away_team if m.home_score >= m.away_score else m.home_team
            # Check for upset (winner has lower rating)
            winner_rating = winner.team_rating()
            loser_rating = loser.team_rating()
            if winner_rating < loser_rating - 5:
                headlines.append(f"🚨 {winner.name} elimina {loser.name} al {round_name}!")
    # Cup winner headline
    if bracket.winner:
        headlines.append(f"🏆 {bracket.winner.name} vince la Coppa Nazionale!")
    return headlines


def generate_playoff_headlines(bracket: PlayoffBracket) -> list[str]:
    """Generate narrative headlines for playoff matches.

    Creates headlines for semifinals and the final, including upset detection.

    Args:
        bracket: A simulated PlayoffBracket with all matches played.
    Returns:
        List of headline strings.
    """
    headlines: list[str] = []
    # Semifinal 1
    if bracket.semifinal1.played and bracket.semifinal1.home_team != bracket.semifinal1.away_team:
        sf1 = bracket.semifinal1
        winner = sf1.home_team if sf1.home_score >= sf1.away_score else sf1.away_team
        loser = sf1.away_team if sf1.home_score >= sf1.away_score else sf1.home_team
        if winner.team_rating() < loser.team_rating() - 5:
            headlines.append(f"🚨 {winner.name} elimina {loser.name} in Semifinale!")
        else:
            headlines.append(f"✅ {winner.name} accede alla Finale contro {loser.name}.")
    # Semifinal 2
    if bracket.semifinal2.played and bracket.semifinal2.home_team != bracket.semifinal2.away_team:
        sf2 = bracket.semifinal2
        winner = sf2.home_team if sf2.home_score >= sf2.away_score else sf2.away_team
        loser = sf2.away_team if sf2.home_score >= sf2.away_score else sf2.home_team
        if winner.team_rating() < loser.team_rating() - 5:
            headlines.append(f"🚨 {winner.name} elimina {loser.name} in Semifinale!")
        else:
            headlines.append(f"✅ {winner.name} accede alla Finale contro {loser.name}.")
    # Final
    if bracket.final and bracket.final.played:
        if bracket.winner:
            headlines.append(f"🏆 {bracket.winner.name} CAMPIONE D'ITALIA!")
    return headlines


def develop_youth_players(team: Team, rng: random.Random | None = None) -> list[str]:
    """Develop youth academy players over a season.

    For each youth player, selects 1-2 random attributes and improves them:
    - Age 16-17: +1 per attribute
    - Age 18: +2 per attribute
    - Bonus +1 if potential > 80
    Gains are capped at the player's potential.

    Args:
        team: The team whose youth players should develop.
        rng: Optional RNG for deterministic tests.
    Returns:
        List of development report strings.
    """
    if rng is None:
        rng = random.Random()
    reports: list[str] = []
    attrs = ["passing", "shooting", "defense", "speed", "stamina"]
    for yp in team.youth_players:
        n_attrs = rng.randint(1, 2)
        chosen = rng.sample(attrs, n_attrs)
        gains = []
        for attr in chosen:
            current = getattr(yp, attr)
            max_val = min(99, yp.potential)
            if yp.age <= 17:
                gain = 1
            else:
                gain = 2
            # Bonus for high potential
            if yp.potential > 80:
                gain += 1
            new_val = min(max_val, current + gain)
            actual_gain = new_val - current
            if actual_gain > 0:
                setattr(yp, attr, new_val)
                gains.append(f"{attr} +{actual_gain}")
        if gains:
            reports.append(f"{yp.name} (età {yp.age}): {', '.join(gains)}")
    return reports


def simulate_cup(bracket: CupBracket, seed: int = 0) -> Team:
    """Simulate the entire Coppa Nazionale bracket.

    Each match is single-leg. Home team wins ties (random draw advantage).
    The winner receives +200 budget and +10 prestige.

    Args:
       bracket: A CupBracket with rounds set up.
        seed: Random seed for deterministic simulation.
    Returns:
        The winning Team.
    """
    current_seed = seed
    if bracket.winner is not None:
        # Already simulated — prevent double awards (m10)
        return bracket.winner

    current_winners: list[Team | None] = []

    for round_idx, round_matches in enumerate(bracket.rounds):
        next_winners: list[Team | None] = []
        match_idx = 0

        for m in round_matches:
            home = m.home_team
            away = m.away_team

            # Fill placeholders from previous round winners
            if home is None and round_idx > 0:
                home = current_winners[match_idx * 2] if match_idx * 2 < len(current_winners) else None
                m.home_team = home  # M2: update Match for display
            if away is None and round_idx > 0:
                away = current_winners[match_idx * 2 + 1] if match_idx * 2 + 1 < len(current_winners) else None
                m.away_team = away  # M2: update Match for display

            # Bye match: home advances automatically
            if away is None and home is not None:
                m.home_score = 1
                m.away_score = 0
                m.played = True
                next_winners.append(home)
                match_idx += 1
                continue
            if home is None and away is not None:
                m.home_score = 0
                m.away_score = 1
                m.played = True
                next_winners.append(away)
                match_idx += 1
                continue
            if home is None and away is None:
                match_idx += 1
                continue

            # Normal match
            result = simulate_match(home, away, seed=current_seed)
            current_seed += 1
            m.home_score = result.home_score
            m.away_score = result.away_score
            m.played = True
            m.events = result.events
            winner = home if result.home_score >= result.away_score else away
            next_winners.append(winner)
            match_idx += 1

        current_winners = next_winners

    if current_winners and len(current_winners) >= 1:
        bracket.winner = current_winners[0]
    else:
        bracket.winner = None

    # Award prizes to winner
    if bracket.winner:
        bracket.winner.budget += 200
        bracket.winner.prestige += 10

    return bracket.winner