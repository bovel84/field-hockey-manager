# Code Review — Field Hockey Manager (FHM)
**Reviewer:** Raul  
**Data:** 2026-07-12  
**Autore implementazione:** Mario  
**Feature reviewate:** Youth Academy, Potential System, Stamina Decay & Substitutions, Playoff, Coppa Nazionale, Database persistence

---

## Riepilogo

| Categoria | Status |
|---|---|
| Test suite (148 totali) | ✅ Tutti passano (0.72s) |
| Backward compat (96 test originali) | ✅ Preservata |
| Logica feature | ⚠️ Bug critici in Coppa Nazionale |
| Edge cases | ⚠️ Mancati edge case importanti |
| Qualità test | 🟡 Buona ma con gap |
| Persistenza DB | ✅ Funziona correttamente |
| Integrazione UI mobile | 🔴 Nessuna integrazione |

### Voto: **62/100 — RIFIUTATO**

---

## 🔴 CRITICAL

### C1. `simulate_cup()` restituisce `None` con 2 o 3 squadre
- **File:** `src/season.py`, riga ~310-340 (`simulate_cup`)
- **Descrizione:** `generate_cup_bracket()` inserisce nel bracket solo le `playing_teams`, non le `bye_teams`. Le bye teams vengono piazzate in `round2_matches` di `generate_cup_bracket`, ma `simulate_cup()` **rigenera il bracket da zero** estraendo le squadre dal bracket esistente (riga ~318: `all_teams` raccolto solo da `bracket.rounds`). Con 3 squadre: bracket_size=4, num_byes=1, ma la bye team non appare in nessun Match del bracket. `simulate_cup` riestrae solo 2 squadre, ricalcola bracket_size=2, num_byes=0 → dopo round1 c'è 1 vincitore, round2 ha 1 team solo → nessun match → `current_winners=[]` → `winner=None`.
  - Con 2 squadre: stesso problema (bracket_size=2, 1 match, 1 vincitore, poi `round2_teams=[winner]` len=1, no match, `current_winners=[]`, `winner=None`).
  - Verificato sperimentalmente: `simulate_cup` con 2 e 3 squadre restituisce `None`.
- **Fix suggerito:** `simulate_cup` non dovrebbe riestrarre le squadre dal bracket. O invece:
  ```python
  # Opzione A: simulate_cup usa le squadre originali passate come parametro
  def simulate_cup(bracket: CupBracket, seed: int = 0, teams: list[Team] = None) -> Team:
      if teams is None:
          # fallback: estrai dal bracket
          ...
  ```
  Oppure **Opzione B (consigliata):** riscrivere `generate_cup_bracket` per includere TUTTE le squadre nel bracket come Match placeholder (le bye teams hanno `away_team=None` o match con se stesse), e `simulate_cup` processa il bracket così com'è senza ricostruirlo.

### C2. `generate_cup_bracket()` perde le bye teams nella struttura del bracket
- **File:** `src/season.py`, riga ~260-290 (`generate_cup_bracket`)
- **Descrizione:** Le bye teams vengono messe in `round2_matches` solo se possono essere accoppiate fra loro (`for i in range(0, max(len(bye_teams), r1_winners_slots), 2)`). Con 1 sola bye team (caso 3 squadre), `len(bye_teams)=1`, il ciclo non crea nessun Match (serve `i+1 < len(bye_teams)` che è falso per i=0). La bye team viene **completamente persa** dal bracket.
- **Fix suggerito:** Creare Match placeholder per le bye teams, o ristrutturare il bracket per tenere traccia di bye teams separatamente.

### C3. Nessuna integrazione UI mobile per le 5 nuove feature
- **File:** `mobile/app.py`, `mobile/screens.py`, `mobile/widgets.py`
- **Descrizione:** Nessuna delle 5 nuove feature è accessibile dall'UI mobile:
  - **Youth Academy:** nessuna schermata per vedere/promuovere youth prospects
  - **Potential System:** `show_potential()` non viene mai chiamato nelle PlayerCard
  - **Substitutions:** `simulate_match` in `app.py` (riga ~130) non passa mai `home_subs`/`away_subs`
  - **Playoff:** nessuna schermata o logica per generare/simulare playoff a fine stagione
  - **Coppa Nazionale:** nessuna schermata o logica per la coppa
  - `start_new_season()` in `app.py` non genera playoff né coppa
  - I dati JSON di `teams.json` non includono il campo `potential` → i giocatori caricati all'avvio hanno `potential=99` (default), rendendo il sistema potential inutile nel gioco mobile
- **Fix suggerito:** 
  1. Aggiungere `potential` ai dati JSON in `data/teams.json` per tutti i giocatori
  2. Aggiungere schermata Youth Academy con promozione
  3. Mostrare `potential` in PlayerCard per giocatori under-23 (`show_potential()`)
  4. Aggiungere UI per sostituzioni in PartitaScreen
  5. Aggiungere logica playoff/coppa al termine della stagione in `start_new_season()`

---

## 🟠 MAJOR

### M1. `simulate_cup()` ricostruisce il bracket ignorando quello generato
- **File:** `src/season.py`, riga ~310-370 (`simulate_cup`)
- **Descrizione:** `simulate_cup` estrae tutte le squadre dal bracket esistente, le reshuffla, e ricalcola da zero il bracket. Questo significa che `generate_cup_bracket` è essenzialmente **inutile** — la sua struttura viene scartata. Il seed della generazione e lo shuffle iniziale vengono persi.
- **Fix suggerito:** `simulate_cup` dovrebbe processare il bracket così com'è stato generato da `generate_cup_bracket`, simulando i match round per round e riempiendo i placeholder con i vincitori.

### M2. Playoff: le squadre non vengono mutate (non c'è reset punti/stats)
- **File:** `src/season.py`, `simulate_playoff` (riga ~230)
- **Descrizione:** `simulate_playoff` usa gli oggetti `Team` originali che hanno `points`, `wins`, `draws`, `losses` dalla stagione regolare. I match playoff aggiornano i `Match` ma non i Team standings. Le squadre mantengono le statistiche della stagione regolare, il che potrebbe confondere il sistema di classifiche se viene richiamato `get_ranking()`.
- **Fix suggerito:** Documentare esplicitamente che il playoff non modifica le standing, oppure usare copie delle squadre per il playoff.

### M3. `generate_cup_bracket()` round2 non accoppia bye teams con round1 winners
- **File:** `src/season.py`, riga ~280-285
- **Descrizione:** Il codice crea `round2_matches` solo accoppiando bye teams fra loro. Se ci sono 2 bye teams e 2 round1 winners, le bye teams giocano fra loro, ma non c'è meccanismo per far giocare i round1 winners. I round1 winners vengono completamente ignorati nella struttura del bracket.
- **Fix suggerito:** Creare Match placeholder per i round1 winners, o ristrutturare il bracket in modo che `simulate_cup` possa riempirli dinamicamente.

### M4. `_stamina_decay` non modifica effettivamente i giocatori
- **File:** `src/simulation.py`, riga ~170 (`_stamina_decay`)
- **Descrizione:** `_stamina_decay` calcola un fattore di decay a livello squadra, ma **non riduce la stamina dei singoli giocatori**. Il decay è applicato solo come moltiplicatore al goal factor del quarto corrente. Non c'è accumulo di fatica: un giocatore con stamina 50 ha lo stesso decay al quarto 3 e al quarto 4. Nella realtà, la stamina dovrebbe degradare progressivamente.
- **Fix suggerito:** Per semplicità questo può essere accettabile, ma andrebbe documentato. In alternativa, tenere traccia della stamina corrente (non max) durante la partita e ridurla ogni quarto.

### M5. Sostituzioni: la stamina decay non viene ricalcolata dopo sostituzioni nel quarto corrente
- **File:** `src/simulation.py`, riga ~95-110
- **Descrizione:** Dopo una sostituzione, `home_decay` viene ricalcolato con `_stamina_decay(home_active, quarter)` ma solo per la squadra che ha fatto la sub. Se entrambe le squadre fanno sub nello stesso quarto, la decay dell'altra viene ricalcolata nella sezione successiva. Tuttavia, se una squadra fa 2 sub nello stesso quarto, la decay viene ricalcolata 2 volte ma il `quarter_home_factor` viene sovrascritto, non accumulato. Questo è corretto ma confuso.
- **Fix suggerito:** Refactoring per chiarezza — calcolare la decay una sola volta per quarto dopo tutte le sostituzioni.

---

## 🟡 MINOR

### m1. `import math` dentro la funzione
- **File:** `src/season.py`, riga ~257 e riga ~325
- **Descrizione:** `import math` è fatto all'interno delle funzioni `generate_cup_bracket` e `simulate_cup`. Spostare in cima al file.
- **Fix:** `import math` in cima al file.

### m2. `show_potential()` metodo con nome fuorviante
- **File:** `src/models.py`, riga ~80
- **Descrizione:** `show_potential()` restituisce un bool, non "mostra" il potential. Un nome migliore sarebbe `has_growth_potential()` o `is_prospect()`.
- **Fix:** Rinominare in `is_prospect()` o `can_show_potential()`.

### m3. Playoff: pareggi gestiti con "home team avanza" — non documentato
- **File:** `src/season.py`, `simulate_playoff`, riga ~235-240
- **Descrizione:** In caso di pareggio, la squadra di casa (seed più alto) avanza. Questo è sensato ma non è documentato nei docstring né testato esplicitamente.
- **Fix:** Aggiungere test per verificare che in caso di pareggio avanzi il seed più alto. Documentare nel docstring.

### m4. Coppa: pareggi gestiti con "home team vince" — incoerenza con playoff
- **File:** `src/season.py`, `simulate_cup`, riga ~345
- **Descrizione:** In Coppa, il "home team" è determinato dallo shuffle casuale, non dal seeding. Quindi in caso di pareggio vince chi capita come home, non il seed più alto. Incoerenza con il playoff dove il seed più alto è sempre home.
- **Fix:** Per coerenza, ordinare le squadre per rating o seeding prima di simulare i match della coppa, o usare i rigori/extra time invece di dare la vittoria al home team.

### m5. `_make_substitution` non verifica che il giocatore sostituito sia effettivamente stanco
- **File:** `src/simulation.py`, riga ~175
- **Descrizione:** La sostituzione non ha logica automatica basata sulla stamina. Si basa interamente sui parametri `home_subs`/`away_subs` passati dal chiamante. Per il gameplay automatico (AI), non c'è nessuna logica di sostituzione automatica.
- **Fix:** Aggiungere un metodo `_auto_substitutions()` che suggerisce o esegue sostituzioni automatiche per l'AI basate sulla stamina.

### m6. `generate_youth_prospects` non aggiunge i prospect a `team.youth_players`
- **File:** `src/season.py`, `generate_youth_prospects`
- **Descrizione:** La funzione ritorna una lista di prospect ma non li aggiunge a `team.youth_players`. Il chiamante deve farlo manualmente. Nei test questo viene fatto esplicitamente (`team.youth_players = prospects`). Questo è un pattern API inconsistent — `generate_free_agents` ritorna una lista separata, ma youth prospects sono concettualmente legati al team.
- **Fix:** Documentare chiaramente, o aggiungere un parametro `auto_add=True` che aggiunge i prospect a `team.youth_players`.

### m7. Test `test_low_stamina_team_scores_less_late` usa tolleranza molto larga
- **File:** `tests/test_substitutions.py`, riga ~120
- **Descrizione:** Il test verifica `high_late_goals >= low_late_goals * 0.9` — una tolleranza del 10% è molto larga e potrebbe mascherare regressioni. Inoltre, il test confronta `low_stamina vs low_stamina` (entrambe le squadre hanno stamina 40), non `low vs high`.
- **Fix:** Correggere il test per confrontare low_stamina team vs high_stamina team nei late goals, e usare una tolleranza più stretta (es. 0.95 o confronto diretto).

### m8. `Player.__str__` non mostra `potential` né `age` in modo completo
- **File:** `src/models.py`, riga ~85
- **Descrizione:** `__str__` mostra età e morale ma non potential. Per il sistema di crescita, sarebbe utile mostrare il potential per i giovani.
- **Fix:** Aggiungere `Pot:{self.potential}` alla stringa se `self.show_potential()`.

### m9. Database: manca migrazione per database esistenti
- **File:** `src/database.py`, `init()`
- **Descrizione:** `CREATE TABLE IF NOT EXISTS` con il nuovo campo `potential` funziona solo per database nuovi. Se un database esistente (già creato prima dell'aggiornamento) viene aperto, la colonna `potential` non esiste nella tabella `players` e `save_team`/`load_team` falliranno con `sqlite3.OperationalError: table players has no column named potential`.
- **Fix:** Aggiungere logica di migrazione con `ALTER TABLE players ADD COLUMN potential INTEGER DEFAULT 99` se la colonna non esiste. Stesso per `is_youth`, `prestige`.

### m10. `simulate_cup` award di budget/prestige può applicarsi più volte se chiamata più volte
- **File:** `src/season.py`, `simulate_cup`, riga ~370
- **Descrizione:** Se `simulate_cup` viene chiamata due volte sullo stesso bracket (es. per retry), il vincitore riceve +200 budget e +10 prestige ogni volta. Non c'è guardia contro doppia esecuzione.
- **Fix:** Aggiungere un flag `bracket.winner is not None` all'inizio e return early se già simulato.

---

## 🔵 INFO

### i1. Formazione giocatori youth: attributi non clampati a potenziale
- **File:** `src/season.py`, `generate_youth_prospects`
- **Descrizione:** Gli attributi dei prospect (40-60 ± 3) possono eccedere il potenziale (70-95). Per esempio, un prospect con base 60 + 3 = 63 in tutti gli attributi avrebbe overall_rating ~63, che è inferiore a potenziale 70. Questo è ok, ma non c'è un clamp esplicito.
- **Suggerimento:** Non un bug, ma garantire che `overall_rating() <= potential` alla creazione per coerenza.

### i2. `CupBracket` dataclass con `rounds` come `list[list[Match]]`
- **File:** `src/season.py`
- **Descrizione:** Il tipo `list[list[Match]]` non supporta match placeholder (Match con `away_team=None`). Per un bracket vero servirebbe un tipo più flessibile.
- **Suggerimento:** Considerare un `Optional[Team]` per i placeholder, o una classe `BracketMatch` dedicata.

### i3. Test coverage: mancano test per simulate_cup con 2, 3, 5 squadre
- **File:** `tests/test_playoff_cup.py`
- **Descrizione:** I test coprono 4 e 6 squadre, ma non 2, 3, 5. I bug critici C1/C2 non sono stati catturati.
- **Suggerimento:** Aggiungere test parametrizzati per 2, 3, 4, 5, 6, 7, 8 squadre.

### i4. Test: `test_cup_deterministic_with_seed` non garantisce determinismo
- **File:** `tests/test_playoff_cup.py`
- **Descrizione:** Il test usa `rng=random.Random(42)` per `generate_cup_bracket` e `seed=42` per `simulate_cup`. Ma `simulate_cup` fa un ulteriore shuffle con `rng.shuffle(teams_list)`, e il rng interno ha seed diverso. Il determinismo dipende dall'ordine di estrazione delle squadre dal bracket, che potrebbe cambiare se la struttura del bracket cambia.
- **Suggerimento:** Test valido ma fragile. Documentare l'assunzione di determinismo.

### i5. `_check_injuries` identifica il team con confronto `team == match.home_team`
- **File:** `src/simulation.py`, riga ~140
- **Descrizione:** Usa `==` su dataclass, che per default confronta per identità di campo. Funziona perché `Team` è un dataclass con `eq=True` (default). Se due team hanno gli stessi campi, potrebbero essere confusi. Nella pratica non succede perché i nomi sono unici.
- **Suggerimento:** Usare `is` invece di `==` per clarity, o assicurarsi che i nomi siano sempre unici.

### i6. `generate_calendar` non è round-robin vero
- **File:** `src/season.py`, `generate_calendar`
- **Descrizione:** Il calendario usa `combinations(range(n), 2)` che genera tutte le coppie ma non le distribuisce in round veramente round-robin (alcuni team potrebbero giocare 2 match nello stesso round). Con 6 team e 3 match per round, ogni team dovrebbe giocare esattamente 1 match per round. L'implementazione attuale potrebbe avere team che giocano 0 o 2 match in un round.
- **Suggerimento:** Usare l'algoritmo standard del round-robin (Berger tables). Non introdotto da Mario ma preesistente.

---

## Fix Obbligatori prima della valutazione di Tommy

1. **C1 + C2:** Correggere `generate_cup_bracket` e `simulate_cup` per gestire correttamente 2, 3, 5, 7 squadre (bye teams non devono essere perse)
2. **C3:** Integrare almeno Youth Academy e Potential nell'UI mobile (schermata + PlayerCard). Aggiungere `potential` a `data/teams.json`
3. **M1:** Riscrivere `simulate_cup` per usare il bracket generato invece di ricostruirlo
4. **M3:** Correggere `generate_cup_bracket` round2 per accoppiare bye teams con round1 winners
5. **m9:** Aggiungere migrazione database per database esistenti (ALTER TABLE)
6. **m7:** Correggere il test `test_low_stamina_team_scores_less_late` (confronto errato)
7. **i3:** Aggiungere test per `simulate_cup` con 2, 3, 5 squadre

## Fix Consigliati (non bloccanti)

- M2: Documentare o isolare le statistiche playoff dalla stagione regolare
- M4: Considerare decay progressivo della stamina durante la partita
- m1: Spostare `import math` in cima al file
- m3: Aggiungere test per pareggi nel playoff
- m4: Garantire coerenza nel trattamento dei pareggi tra playoff e coppa
- m5: Aggiungere logica di sostituzione automatica per l'AI
- m10: Aggiungere guardia contro doppia esecuzione di `simulate_cup`

---

## Verdetto: **RIFIUTATO** (62/100)

Il codice è strutturato bene, i test originali passano tutti, e la logica di base è solida per la maggior parte delle feature. Tuttavia, ci sono **bug critici nella Coppa Nazionale** (simulate_cup restituisce None con 2-3 squadre), **nessuna integrazione mobile** per le 5 nuove feature, e un **problema di migrazione database** che causerà crash su installazioni esistenti. Questi fix sono obbligatori prima di procedere alla QA di Tommy.