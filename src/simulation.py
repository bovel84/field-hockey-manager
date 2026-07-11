"""Match simulation engine for Field Hockey Manager."""
from __future__ import annotations
import random
from .models import Match, Team, Player, Position


# Formation modifiers: (defense_bonus, attack_bonus)
_FORMATION_MODIFIERS: dict[str, tuple[float, float]] = {
    "4-3-3": (0.0, 0.10),   # more attack
    "4-4-2": (0.0, 0.0),    # balanced
    "3-5-2": (-0.05, 0.05), # slight attack, less defense
    "5-3-2": (0.10, -0.05), # more defense
}

# Intensity modifiers: (home_goal_factor_mult, away_goal_factor_mult)
_INTENSITY_MODIFIERS: dict[str, tuple[float, float]] = {
    "Difensiva": (0.8, 1.2),
    "Bilanciata": (1.0, 1.0),
    "Offensiva": (1.2, 0.8),
}


def simulate_match(
    home: Team,
    away: Team,
    seed: int = 0,
    home_formation: str = "4-3-3",
    home_intensity: str = "Bilanciata",
    away_formation: str = "4-3-3",
    away_intensity: str = "Bilanciata",
) -> Match:
    """
    Simulate a hockey match between two teams.

    Algorithm:
    - Compute team ratings (0-100) for both sides, using effective_rating (morale-adjusted).
    - Add home advantage (+5).
    - Apply formation and intensity modifiers.
    - For each of 4 quarters, compute expected goals based on rating difference.
    - Use a Poisson-like random draw to determine actual goals.
    - Generate goal events with scorer and minute.
    - Check for injuries (5-10% chance per match for a random player).
    """
    rng = random.Random(seed)

    home_rating = home.team_rating() + 5  # home advantage
    away_rating = away.team_rating()

    # Apply formation modifiers
    home_def, home_atk = _FORMATION_MODIFIERS.get(home_formation, (0.0, 0.0))
    away_def, away_atk = _FORMATION_MODIFIERS.get(away_formation, (0.0, 0.0))

    home_rating = int(round(home_rating * (1 + home_atk - away_def * 0.5)))
    away_rating = int(round(away_rating * (1 + away_atk - home_def * 0.5)))

    # Base expected goals per quarter
    base_home = 0.35
    base_away = 0.35

    # Rating difference influences expected goals
    diff = home_rating - away_rating
    home_factor = base_home + max(-0.2, min(0.3, diff * 0.015))
    away_factor = base_away + max(-0.2, min(0.3, -diff * 0.015))

    # Apply intensity modifiers
    home_int, away_int = _INTENSITY_MODIFIERS.get(home_intensity, (1.0, 1.0))
    home_factor *= home_int
    away_factor *= away_int

    match = Match(home_team=home, away_team=away)
    match.events = []

    home_score = 0
    away_score = 0

    for quarter in range(1, 5):
        # Goals in this quarter — Poisson-like via random samples
        quarter_home_goals = _poisson_sample(home_factor, rng)
        quarter_away_goals = _poisson_sample(away_factor, rng)

        for _ in range(quarter_home_goals):
            minute = rng.randint((quarter - 1) * 15 + 1, quarter * 15)
            scorer = _pick_scorer(home, rng)
            event = {
                "type": "goal",
                "quarter": quarter,
                "minute": minute,
                "team": "home",
                "scorer": scorer.name if scorer else "Unknown",
            }
            match.events.append(event)
            home_score += 1

        for _ in range(quarter_away_goals):
            minute = rng.randint((quarter - 1) * 15 + 1, quarter * 15)
            scorer = _pick_scorer(away, rng)
            event = {
                "type": "goal",
                "quarter": quarter,
                "minute": minute,
                "team": "away",
                "scorer": scorer.name if scorer else "Unknown",
            }
            match.events.append(event)
            away_score += 1

    match.home_score = home_score
    match.away_score = away_score
    match.played = True

    # Sort events by minute
    match.events.sort(key=lambda e: e.get("minute", 0))

    # Injury check: 5-10% chance per team per match
    _check_injuries(home, rng, match)
    _check_injuries(away, rng, match)

    return match


def _check_injuries(team: Team, rng: random.Random, match: Match) -> None:
    """Check for injuries after a match. 5-10% chance for a random player."""
    available = [p for p in team.players if p.can_play()]
    if not available:
        return
    injury_chance = rng.uniform(0.05, 0.10)
    if rng.random() < injury_chance:
        victim = rng.choice(available)
        duration = rng.randint(1, 3)
        victim.injured = True
        victim.injury_duration = duration
        match.events.append({
            "type": "injury",
            "team": "home" if team == match.home_team else "away",
            "player": victim.name,
            "duration": duration,
        })


def _poisson_sample(lam: float, rng: random.Random) -> int:
    """Sample from a Poisson distribution using Knuth's algorithm."""
    if lam <= 0:
        return 0
    L = pow(2.7182818284590452, -lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def _pick_scorer(team: Team, rng: random.Random) -> Player | None:
    """Pick a goal scorer — attackers are more likely to score."""
    if not team.players:
        return None
    starters = team.get_starters()
    if not starters:
        return None
    # Weight: ATTACK x6, MIDFIELD x3, DEFENSE x1, GOALKEEPER x0.1
    weighted: list[Player] = []
    for p in starters:
        if p.position == Position.ATTACK:
            weighted.extend([p] * 6)
        elif p.position == Position.MIDFIELD:
            weighted.extend([p] * 3)
        elif p.position == Position.DEFENSE:
            weighted.append(p)
        elif p.position == Position.GOALKEEPER:
            # Very rare
            if rng.random() < 0.05:
                weighted.append(p)
    if not weighted:
        return starters[0]
    return rng.choice(weighted)