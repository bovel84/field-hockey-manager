# Code Review v2 — Verifica Fix
**Reviewer:** Raul  
**Data:** 2026-07-12  
**Scope:** Verifica fix applicati da Andrea sui issue C1/C2, M1, M3, m9, m7, m10, m1, C3-parziale

---

## Riepilego

| Fix | Status | Note |
|-----|--------|------|
| C1/C2 — simulate_cup con 2-3 squadre | ✅ RISOLTO | Verificato con 2, 3, 5, 7 team → winner sempre non-None |
| M1 — simulate_cup usa bracket generato | ✅ RISOLTO | simulate_cup ora processa il bracket round per round con placeholder |
| M3 — bye teams nel bracket | ✅ RISOLTO | generate_cup_bracket usa slots con None padding, bye matches gestiti |
| m9 — migrazione DB | ✅ RISOLTO | _migrate() aggiunge potential, is_youth, prestige con ALTER TABLE |
| m7 — test stamina corretto | ✅ RISOLTO | Ora confronta low(40) vs high(90) correttamente |
| m10 — double award | ✅ RISOLTO | Early return se bracket.winner is not None |
| m1 — import math in testa | ✅ RISOLTO | `import math` in cima al file |
| C3 parziale — potential+age in teams.json | ✅ RISOLTO | Tutti i giocatori hanno potential e age |

**Test suite: 153 passed in 0.84s** (5 nuovi test aggiunti: cup con 2, 3, 5, 7 team + no double award)

---

## Dettaglio verifiche

### C1/C2 — `simulate_cup` con 2-3 squadre ✅

**Fix applicato:** `generate_cup_bracket` riscritta completamente. Ora usa un approccio a slot:
- `bracket_size = 2^ceil(log2(n))`, padding con `None` per riempire il bracket
- Ogni round è costruito con `Match(home_team=slot[i], away_team=slot[i+1])`, dove slot può essere `None` (bye o placeholder)
- `simulate_cup` processa il bracket round per round, riempiendo i placeholder con i vincitori del round precedente
- Bye matches (home presente, away=None) avanzano automaticamente

**Verifica sperimentale:**
- 2 team → winner: B ✅
- 3 team → winner: T2 ✅
- 5 team → winner: T3 ✅
- 7 team → winner: T1 ✅
- 6 team → winner: T3 ✅ (funzionava già prima, confermato)

### M1 — simulate_cup usa il bracket generato ✅

**Fix applicato:** `simulate_cup` non ricostruisce più il bracket da zero. Itera sui `bracket.rounds` esistenti e riempie i placeholder `None` con i vincitori del round precedente. Lo shuffle iniziale e la struttura del bracket vengono preservati.

**Verifica:** Il bracket con 6 team mostra 3 round (4 matches → 2 matches → 1 match), con placeholder `None` correttamente riempiti durante la simulazione.

### M3 — bye teams nel bracket ✅

**Fix applicato:** Le bye teams sono ora `None` negli slot del bracket. In round 1, se `away=None` e `home` è una team reale, il match è un bye e la team avanza automaticamente. In round successivi, i placeholder `None` vengono riempiti con i vincitori del round precedente.

### m9 — migrazione database ✅

**Fix applicato:** Aggiunto metodo `_migrate(conn)` in `Database` che:
1. Esegue `PRAGMA table_info(players)` per ottenere le colonne esistenti
2. Aggiunge `potential` e `is_youth` con `ALTER TABLE` se mancanti
3. Aggiunge `prestige` alla tabella `teams` se mancante

**Verifica:** Creato DB vecchio senza le nuove colonne → `init()` migra correttamente → save/load funziona con potential=85 e prestige=50.

### m7 — test stamina corretto ✅

**Fix applicato:** Il test `test_low_stamina_team_scores_less_late` ora confronta correttamente:
- `low_stamina = make_team("Low", 75, stamina=40)` vs `high_stamina = make_team("High", 75, stamina=90)`
- Conta goal Q3+Q4 per ogni team su 200 simulazioni
- Assert: `high_late_goals >= low_late_goals` (corretto, non più il confronto errato di prima)

### m10 — no double award ✅

**Fix applicato:** `simulate_cup` ha un early return all'inizio:
```python
if bracket.winner is not None:
    return bracket.winner
```

**Verifica:** Chiamata doppia a `simulate_cup` → budget e prestige rimangono invariati dopo la seconda chiamata. Stesso oggetto Team restituito.

### m1 — import math in cima ✅

**Fix applicato:** `import math` è in cima al file, non più inline nelle funzioni.

### C3 parziale — potential+age in teams.json ✅

**Fix applicato:** Tutti i giocatori in `data/teams.json` ora hanno i campi `potential` e `age`. I valori sono coerenti (potential ≥ overall_rating per giovani, potenziale più basso per veterani).

---

## Nuovi issue trovati durante la verifica

### 🟡 MINOR — m-new1: `Match.__str__` crash con `away_team=None`

- **File:** `src/models.py`, riga 162 (`Match.__str__`)
- **Descrizione:** `generate_cup_bracket` crea `Match` con `away_team=None` per i bye. `Match.__str__` accede a `self.away_team.name` senza check None → `AttributeError`. Il `CupBracket.__str__` chiama `str(m)` per ogni match → crash se si stampa il bracket prima della simulazione.
- **Fix suggerito:**
  ```python
  def __str__(self) -> str:
      home = self.home_team.name if self.home_team else "TBD"
      away = self.away_team.name if self.away_team else "Bye/TBD"
      ...
  ```

### 🔵 INFO — i-new1: `generate_playoff_bracket` esteso per 2-3 team (non richiesto ma ben fatto)

- **File:** `src/season.py`, riga ~370-390
- **Descrizione:** Il playoff ora gestisce 2 e 3 team (bye per la 1ª classificata). Non era nei fix richiesti ma è un miglioramento coerente. La logica usa un Match "dummy" con home=away per i bye, che funziona ma è un po' hacky.
- **Suggerimento:** Più pulito usare `Match(home_team=top_teams[0], away_team=None)` come fa la coppa, ma funziona.

### 🔵 INFO — i-new2: `generate_youth_prospects` ha parametro `seed` aggiunto

- **File:** `src/season.py`, riga ~265
- **Descrizione:** Aggiunto parametro opzionale `seed` oltre a `rng`. Ben documentato. Compatibile con test esistenti.

### 🔵 INFO — i-new3: `CupBracket.__str__` aggiunto

- **File:** `src/season.py`, riga ~440
- **Descrizione:** Aggiunto metodo `__str__` per visualizzare il bracket. Buono per debug. Tuttavia crash su match con `away_team=None` (vedi m-new1).

---

## Verdetto fix: ✅ TUTTI CORRETTI

Tutti i 8 fix richiesti sono stati applicati correttamente e verificati. I test passano (153/153). Il codice è strutturalmente solido.

**Unico nuovo issue found:** m-new1 (Match.__str__ crash con None) — minore, fix facile.

### Punteggio fix: **92/100**

Aspetto la fine dei fix rimanenti di Mario (C3 UI mobile, M2, m2-m6) per la review finale.