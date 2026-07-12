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
    home_subs: list[dict] | None = None,
    away_subs: list[dict] | None = None,
) -> Match:
    """
    Simulate a hockey match between two teams.

    Algorithm:
    - Compute team ratings (0-100) for both sides, using effective_rating (morale-adjusted).
    - Add home advantage (+5).
    - Apply formation and intensity modifiers.
    - For each of 4 quarters, compute expected goals based on rating difference.
    - Apply stamina decay in quarters 3 and 4: tired starters lose rating.
    - Process substitutions: each team can make up to 3 subs, replacing tired players.
    - Use a Poisson-like random draw to determine actual goals.
    - Generate goal events with scorer and minute.
    - Check for injuries (5-10% chance per match for a random player).

    Substitution format:
        home_subs/away_subs is a list of dicts: {"quarter": int, "out": str, "in": str}
        where "out" and "in" are player names. Max 3 subs per team.
    """
    rng = random.Random(seed)

    # Feature 2: Derby home advantage — if away team is a rival of home team,
    # home advantage is +10 instead of the default +5
    is_derby = away.name in (home.rivals or [])
    home_advantage = 10 if is_derby else 5
    home_rating = home.team_rating() + home_advantage  # home advantage
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

    # --- Substitution tracking ---
    home_sub_events = home_subs or []
    away_sub_events = away_subs or []
    # Clamp to max 3 subs per team
    home_sub_events = home_sub_events[:3]
    away_sub_events = away_sub_events[:3]
    # Auto-subs: if no manual subs provided, generate automatic ones (m2)
    if not home_sub_events:
        home_sub_events = generate_auto_subs(home, home.get_starters())
    if not away_sub_events:
        away_sub_events = generate_auto_subs(away, away.get_starters())

    match = Match(home_team=home, away_team=away)
    match.events = []

    home_score = 0
    away_score = 0

    # Track active starters for each team (for stamina decay and subs)
    home_active = list(home.get_starters())
    away_active = list(away.get_starters())

    for quarter in range(1, 5):
        # --- Stamina decay: tired starters lose rating in quarters 3 and 4 ---
        home_decay = _stamina_decay(home_active, quarter)
        away_decay = _stamina_decay(away_active, quarter)

        # Apply decay to goal factors for this quarter
        quarter_home_factor = home_factor * (1.0 - home_decay)
        quarter_away_factor = away_factor * (1.0 - away_decay)

        # --- Process substitutions for this quarter ---
        home_subs_count = len([e for e in match.events if e.get("type") == "substitution" and e.get("team") == "home"])
        for sub in home_sub_events:
            if sub.get("quarter") == quarter and home_subs_count < 3:
                sub_event = _make_substitution(home, sub, home_active, "home")
                if sub_event:
                    match.events.append(sub_event)
                    home_subs_count += 1
                    home_decay = _stamina_decay(home_active, quarter)
                    quarter_home_factor = home_factor * (1.0 - home_decay)

        away_subs_count = len([e for e in match.events if e.get("type") == "substitution" and e.get("team") == "away"])
        for sub in away_sub_events:
            if sub.get("quarter") == quarter and away_subs_count < 3:
                sub_event = _make_substitution(away, sub, away_active, "away")
                if sub_event:
                    match.events.append(sub_event)
                    away_subs_count += 1
                    away_decay = _stamina_decay(away_active, quarter)
                    quarter_away_factor = away_factor * (1.0 - away_decay)

        # --- Feature: Rigori, corti angoli, cartellini verdi ---
        # Green card check (8-10% per team per quarter)
        home_green = _check_green_card(rng)
        away_green = _check_green_card(rng)
        if home_green:
            home_green["team"] = "home"
            match.events.append(home_green)
            quarter_home_factor *= 0.92  # -8% attack for this quarter
        if away_green:
            away_green["team"] = "away"
            match.events.append(away_green)
            quarter_away_factor *= 0.92

        # Penalty corner check (15-20% per team per quarter)
        home_corner = _check_penalty_corner(home, away, rng, quarter, "home")
        if home_corner:
            match.events.append(home_corner)
            if home_corner["type"] == "corner_goal":
                home_score += 1

        away_corner = _check_penalty_corner(away, home, rng, quarter, "away")
        if away_corner:
            match.events.append(away_corner)
            if away_corner["type"] == "corner_goal":
                away_score += 1

        # Penalty stroke check (4-6% per team per quarter)
        home_penalty = _check_penalty(home, away, rng, quarter, "home")
        if home_penalty:
            match.events.append(home_penalty)
            if home_penalty["type"] == "penalty_goal":
                home_score += 1

        away_penalty = _check_penalty(away, home, rng, quarter, "away")
        if away_penalty:
            match.events.append(away_penalty)
            if away_penalty["type"] == "penalty_goal":
                away_score += 1

        # Goals in this quarter — Poisson-like via random samples
        quarter_home_goals = _poisson_sample(quarter_home_factor, rng)
        quarter_away_goals = _poisson_sample(quarter_away_factor, rng)

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


def _stamina_decay(active_players: list[Player], quarter: int) -> float:
    """Calculate team-level stamina decay factor for a given quarter.

    Tired starters (low stamina) lose more rating in later quarters.
    Returns a float between 0.0 and 0.15 representing the team-wide
    rating reduction factor for this quarter.

    - Quarters 1-2: no decay
    - Quarters 3-4: decay based on average stamina of active players
    """
    if quarter <= 2:
        return 0.0
    if not active_players:
        return 0.0
    avg_stamina = sum(p.stamina for p in active_players) / len(active_players)
    # Lower stamina = more decay. Map stamina 50→0.10, stamina 90→0.02
    decay = max(0.0, min(0.15, (90 - avg_stamina) * 0.0025))
    return decay


def _make_substitution(team: Team, sub: dict, active_list: list[Player], side: str = "home") -> dict | None:
    """Process a substitution request during a match.

    Replaces a player in the active list with a bench player.
    Args:
        team: The team making the substitution.
        sub: Dict with keys "out" (player name to remove) and "in" (player name to add).
        active_list: Mutable list of currently active players (modified in place).
        side: "home" or "away" — which team is making the sub.
    Returns:
        Event dict if substitution was successful, None otherwise.
    """
    out_name = sub.get("out", "")
    in_name = sub.get("in", "")
    quarter = sub.get("quarter", 1)

    # Find the player to substitute out
    out_player = None
    for p in active_list:
        if p.name == out_name:
            out_player = p
            break
    if out_player is None:
        return None

    # Find the replacement from bench (not in active list, not injured)
    active_ids = {id(p) for p in active_list}
    replacement = None
    for p in team.players:
        if id(p) not in active_ids and p.can_play() and p.name == in_name:
            replacement = p
            break
    if replacement is None:
        return None

    # Perform the substitution
    idx = active_list.index(out_player)
    active_list[idx] = replacement

    return {
        "type": "substitution",
        "quarter": quarter,
        "minute": quarter * 15 - 1,
        "team": side,
        "out": out_name,
        "in": in_name,
    }


def generate_auto_subs(team: Team, active_players: list[Player] | None = None) -> list[dict]:
    """Generate up to 3 automatic substitutions for a team.

    Picks the 3 bench players with the highest overall rating and replaces
    the 3 active starters with the lowest stamina. If the user does not
    choose substitutions manually, this function provides sensible defaults.

    Args:
        team: The team making substitutions.
        active_players: Currently active starters (defaults to team.get_starters()).
    Returns:
        List of substitution dicts: [{"quarter": 3, "out": name, "in": name}, ...]
    """
    if active_players is None:
        active_players = list(team.get_starters())

    active_ids = {id(p) for p in active_players}
    bench = [p for p in team.players if id(p) not in active_ids and p.can_play()]
    if not bench or not active_players:
        return []

    # Sort bench by overall rating (descending)
    bench.sort(key=lambda p: p.overall_rating(), reverse=True)
    # Sort active by stamina (ascending — most tired first)
    active_sorted = sorted(active_players, key=lambda p: p.stamina)

    subs: list[dict] = []
    for i in range(min(3, len(bench), len(active_sorted))):
        subs.append({
            "quarter": 3,
            "out": active_sorted[i].name,
            "in": bench[i].name,
        })
    return subs


# --- Feature: Rigori, corti angoli, cartellini verdi ---

def _check_green_card(rng: random.Random) -> dict | None:
    """Check if a green card is awarded this quarter (8-10% chance).

    A green card suspends a random player for 2 minutes.
    The team plays with reduced attack for that quarter.
    """
    if rng.random() < 0.09:  # 8-10% chance
        return {
            "type": "green_card",
            "minute": rng.randint(1, 15),
            "duration": 2,  # 2 minute suspension
        }
    return None


def _check_penalty_corner(atk: Team, def_: Team, rng: random.Random, quarter: int, side: str) -> dict | None:
    """Check if a penalty corner is awarded this quarter (15-20% chance).

    A penalty corner is the most common set piece in hockey.
    The attacking team gets a scoring opportunity based on attack rating
    vs defense rating of the defending team.
    """
    if rng.random() < 0.18:  # 15-20% chance
        atk_rating = atk.team_rating()
        def_rating = def_.team_rating()
        # Scoring probability: 30-50% based on rating difference
        prob = 0.30 + max(0.0, min(0.20, (atk_rating - def_rating) * 0.005))
        if rng.random() < prob:
            scorer = _pick_scorer(atk, rng)
            return {
                "type": "corner_goal",
                "quarter": quarter,
                "minute": rng.randint((quarter - 1) * 15 + 1, quarter * 15),
                "team": side,
                "scorer": scorer.name if scorer else "Unknown",
            }
        else:
            return {
                "type": "penalty_corner",
                "quarter": quarter,
                "minute": rng.randint((quarter - 1) * 15 + 1, quarter * 15),
                "team": side,
                "result": "missed",
            }
    return None


def _check_penalty(atk: Team, def_: Team, rng: random.Random, quarter: int, side: str) -> dict | None:
    """Check if a penalty stroke is awarded this quarter (4-6% chance).

    A penalty stroke is a 1v1 against the goalkeeper.
    The shooter has 75% base probability to score, modified by shooting vs defense.
    """
    if rng.random() < 0.05:  # 4-6% chance
        # Pick best shooter
        starters = atk.get_starters()
        if not starters:
            return None
        shooter = max(starters, key=lambda p: p.shooting)
        goalkeeper = max(def_.get_starters(), key=lambda p: p.defense) if def_.get_starters() else None
        base_prob = 0.75
        if goalkeeper:
            base_prob += (shooter.shooting - goalkeeper.defense) * 0.003
        base_prob = max(0.50, min(0.95, base_prob))
        if rng.random() < base_prob:
            return {
                "type": "penalty_goal",
                "quarter": quarter,
                "minute": rng.randint((quarter - 1) * 15 + 1, quarter * 15),
                "team": side,
                "scorer": shooter.name,
            }
        else:
            return {
                "type": "penalty_missed",
                "quarter": quarter,
                "minute": rng.randint((quarter - 1) * 15 + 1, quarter * 15),
                "team": side,
                "shooter": shooter.name,
            }
    return None

# --- Phase 3: Match timeline + commentary ---

def generate_match_timeline(match: Match) -> list[dict]:
    """Generate a timeline of match states for 2D visualization.

    Each element: {"time": float, "event": dict|None, "positions": {"home": [...], "away": [...]}}
    Time goes from 0 to 60 (match minutes). Events are placed at their minute.
    Between events, players oscillate slightly around their formation positions.

    Args:
        match: A played Match object with events.
    Returns:
        Sorted list of timeline frames.
    """
    from .models import get_formation_positions

    if not match.played:
        return []

    home_formation = match.home_team.formation
    away_formation = match.away_team.formation
    home_base = get_formation_positions(home_formation, away=False)
    away_base = get_formation_positions(away_formation, away=True)

    rng = random.Random(hash(match.home_team.name + match.away_team.name) & 0xFFFFFFFF)

    # Collect all event times
    event_times = []
    for ev in match.events:
        minute = ev.get("minute", 0)
        event_times.append(minute)
    event_times.sort()

    # Generate frames at each event time + start (0) + end (60)
    all_times = sorted(set([0.0] + event_times + [60.0]))
    timeline = []

    for t in all_times:
        # Find event at this time (if any)
        event_at_t = None
        for ev in match.events:
            if ev.get("minute", 0) == t:
                event_at_t = ev
                break

        # Generate positions with small random offset for liveliness
        home_pos = []
        for (bx, by) in home_base:
            ox = (rng.random() - 0.5) * 0.04
            oy = (rng.random() - 0.5) * 0.04
            home_pos.append((max(0.0, min(1.0, bx + ox)), max(0.0, min(1.0, by + oy))))

        away_pos = []
        for (bx, by) in away_base:
            ox = (rng.random() - 0.5) * 0.04
            oy = (rng.random() - 0.5) * 0.04
            away_pos.append((max(0.0, min(1.0, bx + ox)), max(0.0, min(1.0, by + oy))))

        timeline.append({
            "time": float(t),
            "event": event_at_t,
            "positions": {"home": home_pos, "away": away_pos},
        })

    return timeline


# Commentary templates for each event type
_COMMENTARY_TEMPLATES: dict[str, list[str]] = {
    "goal": [
        "📻 {minute}' — GOAL! {scorer} ({team}) brilla e segna! {score}",
        "📻 {minute}' — Che gol! {scorer} ({team}) non sbaglia! {score}",
        "📻 {minute}' — Rete! {scorer} ({team}) regala l'esultanza ai tifosi! {score}",
        "📻 {minute}' — Palla in fondo alla rete! {scorer} ({team}) firma il gol. {score}",
    ],
    "corner_goal": [
        "📻 {minute}' — Corto angolo perfetto! {scorer} ({team}) converte! {score}",
        "📡 {minute}' — Penalty corner e GOAL! {scorer} ({team}) è implacabile! {score}",
        "📻 {minute}' — Truffa difensiva sul corto angolo: {scorer} ({team}) segna! {score}",
    ],
    "penalty_goal": [
        "🎯 {minute}' — Rigore trasformato! {scorer} ({team}) è freddo come il ghiaccio! {score}",
        "📻 {minute}' — Penalty stroke e gol! {scorer} ({team}) non ha esitazioni! {score}",
        "🎯 {minute}' — Massima tensione, ma {scorer} ({team}) segna! {score}",
    ],
    "penalty_missed": [
        "❌ {minute}' — Rigore sbagliato! {shooter} ({team}) trema dal dispiacere!",
        "🥅 {minute}' — Parata miracolosa! {shooter} ({team}) non trova la rete!",
        "❌ {minute}' — Penalty stroke perso! {shooter} ({team}) non ci crede!",
    ],
    "penalty_corner": [
        "📐 {minute}' — Corto angolo per {team}, ma la difesa respinge!",
        "📐 {minute}' — Penalty corner {team}: la palla esce, occasione persa.",
    ],
    "green_card": [
        "🟢 {minute}' — Cartellino verde per {player} ({team}): 2 minuti di sospensione!",
        "🟢 {minute}' — {player} ({team}) viene sanzionato: la squadra resta in 10!",
    ],
    "injury": [
        "🔴 {minute}' — Infortunio per {player} ({team})! Sarà fuori {duration} partite.",
        "🏥 {minute}' — {player} ({team}) esca per infortunio: giornata sfortunata!",
    ],
    "substitution": [
        "🔄 {minute}' — Sostituzione {team}: fuori {out}, dentro {in}!",
        "🔄 {minute}' — Cambio {team}: {out} cede il posto a {in}.",
    ],
    "quarter_end": [
        "⏱️ Fine del {quarter}° quarto. Risultato: {score}",
        "📋 Fine {quarter}° quarto. {score}",
    ],
}

_DERBY_COMMENTS = [
    "Derby infuocato! Il tifo è da pelle d'oca!",
    "Rivalità accesa: ogni palla è una battaglia!",
    "Il derby non perdona: intensità al massimo!",
]


def generate_commentary(match: Match, event: dict, derby: bool = False) -> str:
    """Generate a live commentary string for a match event.

    Args:
        match: The Match object (for context: team names, score, derby).
        event: Event dict with type, minute, team, scorer/player/shooter, etc.
        derby: If True, add derby flavor to the commentary.
    Returns:
        Commentary string.
    """
    ev_type = event.get("type", "")
    minute = event.get("minute", 0)
    team = event.get("team", "")
    scorer = event.get("scorer", "")
    shooter = event.get("shooter", "")
    player = event.get("player", "")
    out_name = event.get("out", "")
    in_name = event.get("in", "")
    duration = event.get("duration", 0)
    quarter = event.get("quarter", 0)

    # Build score string at this point in the match
    score = f"{match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}"

    templates = _COMMENTARY_TEMPLATES.get(ev_type, ["📻 {minute}' — Evento: {type}"])
    # Seeded choice based on match + minute for reproducibility
    rng = random.Random(hash(match.home_team.name + str(minute) + ev_type) & 0xFFFFFFFF)
    template = rng.choice(templates)

    comment = template.format(
        minute=minute, team=team, scorer=scorer, shooter=shooter,
        player=player, **{"out": out_name, "in": in_name}, duration=duration,
        quarter=quarter, score=score, type=ev_type,
    )

    if derby and ev_type in ("goal", "corner_goal", "penalty_goal"):
        derby_comment = rng.choice(_DERBY_COMMENTS)
        comment += f" {derby_comment}"

    return comment
