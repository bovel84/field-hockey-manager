"""Season management: calendar generation, standings, and training."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from itertools import combinations
from .models import Match, Team, Player, Position


def generate_calendar(teams: list[Team], user_team_index: int = 0) -> list[dict]:
    """
    Generate a round-robin calendar.

    With 6 teams, each team plays 10 matches (home and away vs every other team).
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
    # Distribute across rounds — 3 matches per round for 6 teams
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
    new_val = min(99, current + gain)
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
    """Generate random free agents for the transfer market."""
    if rng is None:
        rng = random.Random()
    positions = list(Position)
    agents = []
    for _ in range(count):
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        pos = rng.choice(positions)
        base_rating = rng.randint(55, 88)
        agent = Player(
            name=name,
            position=pos,
            passing=base_rating + rng.randint(-5, 5),
            shooting=base_rating + rng.randint(-5, 5),
            defense=base_rating + rng.randint(-5, 5),
            speed=base_rating + rng.randint(-5, 5),
            stamina=base_rating + rng.randint(-5, 5),
            age=rng.randint(16, 35),
            morale=50,
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