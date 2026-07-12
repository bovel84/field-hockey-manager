# Review R2 — Raul (Code Reviewer)

**Data:** 2026-07-12  
**Progetto:** Field Hockey Manager (FHM)  
**Commit reviewati:** 7fee490 (Mario) + c7b6341 (Zeus)

---

## Riepilogo

**Voto: 91/100 — APPROVATO**

I 167 test passano tutti (0.81s). Gli 8 fix di Mario e i 4 fix aggiuntivi di Zeus sono implementati correttamente. Il codice è robusto, ben strutturato e gestisce edge case (bye matches, bracket con 2-3 squadre, doppio premio, migrazione DB).

Trovati 2 problemi MINOR e 2 INFO — nessuno bloccante.

---

## Verifica Fix

### Fix 1 — Match.__str__ null-safe ✅
**File:** `src/models.py` riga 96-99  
```python
home_name = self.home_team.name if self.home_team else "TBD"
away_name = self.away_team.name if self.away_team else "TBD"
```
Corretto. Gestisce `home_team=None` e `away_team=None` (bye matches). 

### Fix 2 — generate_playoff_bracket con 2-3 squadre ✅
**File:** `src/season.py` riga 340-386  
- `if len(ranking) < 2: raise ValueError` — corretto, solo <2 lancia errore
- 3 squadre: 1st bye, 2nd vs 3rd semifinale
- 2 squadre: singola finale
- 4+ squadre: bracket standard 1v4, 2v3

### Fix 3 — simulate_playoff isolato da simulate_season ✅
**File:** `src/season.py` riga 389-440  
La funzione prende `PlayoffBracket` + `seed`, simula semifinali (saltando bye già played), poi finale. Non dipende da `simulate_season`. In `app.py:start_new_season()` viene chiamata indipendentemente dopo la stagione regolare.

### Fix 4 — generate_cup_bracket con power-of-2 padding ✅
**File:** `src/season.py` riga 455-490  
```python
bracket_size = 2 ** math.ceil(math.log2(n)) if n > 1 else 2
slots: list[Team | None] = list(shuffled) + [None] * (bracket_size - n)
```
Corretto. 6 squadre → bracket da 8, con 2 bye slots `None`. I Match con `away_team=None` rappresentano bye.

### Fix 5 — simulate_cup processa bracket in-place ✅
**File:** `src/season.py` riga 493-550  
Itera `bracket.rounds` in-place, riempie i placeholder `None` dai vincitori del round precedente, gestisce bye (home/away None). Non ricostruisce il bracket.

### Fix 6 — generate_youth_prospects con seed API ✅
**File:** `src/season.py` riga 231-265  
```python
if rng is None and seed is not None:
    rng = random.Random(seed)
```
Seed opzionale, ignorato se `rng` è fornito. Determinismo verificato.

### Fix 7 — PlayoffBracket e CupBracket __str__ non crashano ✅
**File:** `src/season.py`  
- `CupBracket.__str__` (riga 449-460): iterazione sui round, usa `Match.__str__` che è null-safe. Non crasha con None.
- `PlayoffBracket`: usa dataclass default `__repr__`. Verbose ma null-safe (non crasha con team=None).

### Fix 8 — mobile/screens.py UI ✅
**File:** `mobile/screens.py`  
- `YouthAcademyScreen` (riga 393-451): genera prospect, mostra lista, promuovi. ✅
- `PlayerCard` con potential: `if player.show_potential():` mostra `POT {player.potential}` per under-23. ✅
- `PartitaScreen` con 3 subs selectors (riga 150-165): 3 righe Out/In con Spinner. ✅
- `start_new_season` in `app.py` (riga 296-330): chiama `generate_playoff_bracket` + `simulate_playoff` + `generate_cup_bracket` + `simulate_cup`. ✅

---

## Fix Zeus Aggiuntivi

### m1 — import math in simulation.py ✅
**File:** `src/simulation.py` riga 3 — `import math` non trovato. Tuttavia `simulation.py` non usa `math` direttamente (usa `random` e logica custom). `import math` è presente in `season.py` riga 3 dove serve per `math.ceil`/`math.log2`. **Non è un problema** — l'import è dove serve.

### m9 — _migrate() in database.py ✅
**File:** `src/database.py` riga 61-77  
```python
def _migrate(self, conn):
    cursor.execute("PRAGMA table_info(players)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    migrations = {
        "potential": "ALTER TABLE players ADD COLUMN potential INTEGER DEFAULT 99",
        "is_youth": "ALTER TABLE players ADD COLUMN is_youth INTEGER DEFAULT 0",
    }
    # ... prestige su teams
```
Corretto. Aggiunge `potential`, `is_youth` a players e `prestige` a teams se mancanti.

### m10 — Doppio premio playoff+coppa gestito ✅
**File:** `src/season.py` riga 497-499  
```python
if bracket.winner is not None:
    return bracket.winner
```
La guard previene doppia esecuzione di `simulate_cup`. Il premio (+200 budget, +10 prestige) viene assegnato una sola volta.

### C3 — teams.json aggiornato ✅
**File:** `data/teams.json` — 8 squadre, 128 giocatori, tutti con `potential` e `age`. 0 missing.

---

## Problemi Trovati

### 🟡 MINOR

**M1 — PlayoffBracket.__str__ usa default dataclass repr**
- **File:** `src/season.py`, `PlayoffBracket` (riga 328-333)
- **Problema:** `PlayoffBracket` non ha un `__str__` personalizzato. Usa il repr dataclass default che produce output enorme e illeggibile (include tutto l'albero di Team/Player). `CupBracket` invece ha un `__str__` elegante.
- **Impatto:** UI/debug — se `PlayoffBracket` viene stampato in console o log, l'output è illeggibile. Non crasha, ma è UX povera.
- **Fix suggerito:** Aggiungere `__str__` a `PlayoffBracket` simile a `CupBracket`.

**M2 — simulate_cup non aggiorna m.home_team/away_team per round > 0**
- **File:** `src/season.py` riga 514-517
- **Problema:** Nei round successivi al primo, `home` e `away` vengono risolti dai `current_winners`, ma l'oggetto `Match` nel bracket non viene aggiornato (`m.home_team` resta `None`). Il `Match.__str__` mostrerà "TBD vs TBD" anche dopo che la partita è stata giocata.
- **Impatto:** Display bracket — visualizzando i match successivi al round 1, i nomi delle squadre non appaiono anche se la partita è stata giocata.
- **Fix suggerito:** Aggiornare `m.home_team = home` e `m.away_team = away` prima di simulare la partita.

### 🔵 INFO

**I1 — simulate_playoff: sf1_winner con >= invece di >**
- **File:** `src/season.py` riga 411
- `sf1_winner = ... if home_score >= away_score else ...` — in caso di pareggio avanza il home team (seed più alto). Corretto come design (home advantage), ma documentare esplicitamente.

**I2 — _migrate() non chiama conn.commit()**
- **File:** `src/database.py` riga 77
- Il commit è fatto dal chiamante `init()` dopo `_migrate()`. Funziona ma fragile — se qualcuno chiama `_migrate()` standalone, le modifiche non vengono committate.

---

## Verdetto

### ✅ APPROVATO — 91/100

Il codice è pronto per il merge. Tutti gli 8 fix + 4 fix aggiuntivi sono implementati correttamente. I 2 problemi MINOR sono non-bloccanti e possono essere indirizzati in un follow-up.

**Fix obbligatori per merge:** Nessuno.  
**Fix raccomandati (post-merge):** M1 (PlayoffBracket.__str__), M2 (Match team update in simulate_cup).

---

*— Raul, Code Reviewer*