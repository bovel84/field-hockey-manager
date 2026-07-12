# 🏒 Field Hockey Manager — Suggerimenti Fase 2

**Autore:** Leonardo, Game Designer  
**Data:** 12 Luglio 2026  
**Ciclo:** Post must-have (Mario ha implementato: sostituzioni, potenziale, youth academy, playoff, coppa nazionale)

---

## PARTE 1 — Revisione dei 10 nice-to-have

Ho riveduto i 10 suggerimenti priorità 2-3 dalla mia lista originale alla luce del codice attuale. Ecco la classifica aggiornata:

| # | Suggerimento | Complessità | Impatto | Dipendenze must-have | Verdetto |
|---|---|---|---|---|---|
| 1 | Derby e rivalità | Bassa | 8/10 | Nessuna | ✅ TOP 3 |
| 2 | Obiettivi stagionali dinamici | Media | 8/10 | Nessuna (si appoggia al sistema carriera) | ✅ TOP 3 |
| 3 | Rigori, corti e punizioni | Bassa | 7/10 | Nessuna | ✅ TOP 3 |
| 4 | Crisi di spogliatoio | Media | 7/10 | Nessuna | Prossimo ciclo |
| 5 | Awards individuali fine stagione | Bassa | 6/10 | Playoff (già fatto) | Prossimo ciclo |
| 6 | Chimica di squadra | Media | 6/10 | Sostituzioni (interazione) | Prossimo ciclo |
| 7 | Contratti dei giocatori | Media | 7/10 | Nessuna | Ciclo 3 |
| 8 | Tattiche avanzate (pressing/contropiede) | Bassa | 5/10 | Nessuna | Ciclo 3 |
| 9 | Nazionale e convocazioni | Media | 5/10 | Potenziale (già fatto) | Ciclo 3 |
| 10 | Commento testuale dinamico | Bassa | 4/10 | Nessuna | Ciclo 4 (polish) |

Esclusi dalla shortlist (priorità 3, ciclo futuro): allenatore specializzato, hall of fame, formazione a campo.

---

## PARTE 2 — I 3 migliori per il prossimo ciclo

### 2.1 Derby e rivalità 🔥

**Descrizione sintetica:**
Definisci coppie di rivali nel `teams.json`. Nei derby il home advantage raddoppia (+10 invece di +5), il morale post-partita ha impatto raddoppiato (±20 invece di ±10), e i tifosi reagiscono in modo esagerato (±160 invece di ±80). Eventi pre-partita narrativi ("tifo infuocato", "pressione mediatica") appaiono in `career_news`. Le rivalità creano giornate attese dal giocatore e danno peso a match che altrimenti sarebbero indifferenti.

**File da modificare:**
- `data/teams.json` — aggiungere campo `rivals: list[str]` per ogni squadra
- `src/models.py` — aggiungere `rivals: list[str] = field(default_factory=list)` in `Team`
- `src/simulation.py` — modificare home advantage in `simulate_match()`: se `away.name in home.rivals`, home advantage = +10 invece di +5
- `mobile/app.py` — in `_update_career_after_match()`: se derby, raddoppiare delta morale, supporters e headline speciale
- `mobile/screens.py` — in `CalendarioScreen`: evidenziare i derby con emoji/icona

**Complessità stimata:** Bassa  
**Impatto sul gameplay:** 8/10  
**Dipendenze dai must-have:** Nessuna. Funziona autonomamente.

---

### 2.2 Obiettivi stagionali dinamici 🎯

**Descrizione sintetica:**
All'inizio di ogni stagione, la dirigenza fissa 2-3 obiettivi specifici basati sulla reputazione del manager e sulla forza della squadra. Esempi: "Arriva top-3", "Segna almeno 20 gol", "Non perdere più di 3 partite consecutive", "Raggiungi le semifinali di coppa". Completarli dà bonus di budget (+100-300), reputazione (+5) e fiducia (+10). Fallirli ha conseguenze: -5 fiducia, -100 budget, eventuale "richiamo formale" in career_news. Gli obiettivi danno scopo ad ogni singola partita, non solo alla stagione nel complesso.

**File da modificare:**
- `mobile/app.py` — nuovo campo `season_goals: list[dict]`, generato in `start_new_season()`. Ogni goal: `{"id": str, "description": str, "type": str, "target": int, "reward_budget": int, "reward_reputation": int, "status": "active"|"completed"|"failed"}`
- `mobile/app.py` — in `_update_career_after_match()`: check progresso goal (es. gol fatti cumulativi, sconfitte consecutive, posizione in classifica)
- `mobile/app.py` — in `start_new_season()`: valutare goal della stagione appena conclusa, assegnare ricompense/penali, generare nuovi goal
- `mobile/screens.py` — in `CarrieraScreen`: mostrare goal attivi con progress bar (es. "Gol stagionali: 14/20 ███████░░░")
- `src/database.py` — persistere `season_goals` in `game_state`

**Complessità stimata:** Media  
**Impatto sul gameplay:** 8/10  
**Dipendenze dai must-have:** Nessuna diretta. Si integra naturalmente con il sistema carriera già esistente (reputazione, board_confidence, supporters). La coppa nazionale già implementata permette goal come "raggiungi le semifinali di coppa".

---

### 2.3 Rigori, corti angoli e punizioni ⚡

**Descrizione sintetica:**
Durante la simulazione di ogni partita, genera eventi speciali oltre ai gol normali:
- **Rigore** (4-6% probabilità per partita): se assegnato, il tiratore ha 75% probabilità di segnare (modificata dallo `shooting` del tiratore vs `defense` del portiere). Evento narrativo di tensione.
- **Corto angolo / penalty corner** (15-20% per partita): genera un'opportunità di gol con probabilità basata sul rating di attacco della squadra vs difesa avversaria. È l'evento più comune nell'hockey su prato reale.
- **Cartellino verde** (8-10% per partita): un giocatore viene sospeso per 2 minuti (quarto corrente), la squadra gioca in inferiorità numerica con -5 al team rating per quel quarto.

Questi eventi aggiungono varietà, realism e momenti di tensione alle partite, anche quando il risultato è già deciso.

**File da modificare:**
- `src/simulation.py` — nuove funzioni:
  - `_check_penalty(home, away, rng, quarter)` → ritorna evento penalty o None
  - `_check_penalty_corner(home, away, rng, quarter)` → ritorna evento corner o None  
  - `_check_green_card(team, rng, quarter)` → ritorna evento sospensione o None
  - Modificare il loop dei quarti in `simulate_match()` per chiamare questi check prima dei gol normali
  - I gol da rigore/corto angolo aggiungono al score ma con evento type diverso (`"penalty_goal"`, `"corner_goal"`)
- `src/models.py` — nessuna modifica necessaria (eventi sono dict)
- `mobile/screens.py` — in `PartitaScreen._play_match()`: riconoscere e formattare i nuovi tipi di evento con icone/emoji distintive (⚽ gol, 🎯 rigore, 📐 corto, 🟢 cartellino verde)
- `mobile/widgets.py` — eventuale `MatchEvent` widget per renderizzare eventi con icone

**Complessità stimata:** Bassa  
**Impatto sul gameplay:** 7/10  
**Dipendenze dai must-have:** Nessuna. Si integra nel loop di simulazione esistente. Le sostituzioni già implementate sono indipendenti.

---

## PARTE 3 — 2 suggerimenti nuovi (ispirati dal codice di Mario)

Dopo aver esaminato le implementazioni di Mario, ho identificato due lacune che meritano attenzione.

### 3.1 Sistema Sviluppo Youth Academy 🌱

**Descrizione sintetica:**
Mario ha implementato `generate_youth_prospects()` e `promote_youth_player()`, ma i giovani lasciati in academy non si sviluppano: restano fermi ai loro attributi iniziali. Serve un sistema di crescita automatica: a fine stagione, ogni youth player left in academy guadagna +1-3 in attributi casuali (basato su età e potenziale), fino al cap del `potential`. Dopo 2-3 stagioni un prospetto 40→65 diventa pronto per la prima squadra. Il manager decide quando promuovere (troppo presto = brucia il potenziale, troppo tardi = il giocatore si stanca e decade). Aggiunge un vero loop decisionale multi-stagione.

**File da modificare:**
- `src/season.py` — nuova funzione `develop_youth_players(team: Team, rng=None)`:
  - Per ogni `youth_player` in `team.youth_players`:
    - Seleziona 1-2 attributi casuali
    - Gain = +1 se age 16-17, +2 se age 18, basato su `potential` (non supera il cap)
    - probabilità di +1 aggiuntivo se `potential` alto (>80)
  - Chiamata in `start_new_season()` di `app.py`, prima del reset stagionale
- `mobile/app.py` — in `start_new_season()`: chiamare `develop_youth_players()` per tutte le squadre, non solo user
- `mobile/screens.py` — in `RosaScreen` o nuova `YouthScreen`: mostrare youth players con attributi, potenziale, e bottone "Promuovi" / "Rilascia"
- `src/database.py` — persistere `youth_players` per ogni team (nuova colonna o tabella separata `youth_players`)

**Complessità stimata:** Media  
**Impatto sul gameplay:** 7/10  
**Dipendenze dai must-have:** 
- ✅ Youth Academy (già implementata da Mario) — questo è un'estensione diretta
- ✅ Sistema potenziale (già implementato) — il cap di crescita usa `potential`

**Perché ora:** Senza sviluppo, la youth academy è un feature morta. I giocatori la usano una volta, vedono che i prospetti non migliorano, e la ignorano. Questo fix trasforma una feature statica in un sistema vivo.

---

### 3.2 Integrazione narrativa Coppa & Playoff 📰

**Descrizione sintetica:**
Mario ha implementato coppa e playoff con `simulate_cup()` e `simulate_playoff()`, ma i risultati non vengono raccontati al giocatore. Il `career_news` attualmente registra solo le partite di campionato dell'utente. I match di coppa, le sorprese (un bottom seed che batte il top seed), la finale di playoff — tutto silenzioso. Serve un layer narrativo che generi titoli e commenti per ogni evento significativo di coppa/playoff, integrandoli nel feed `career_news`. Esempi: "🚨 SORPRESA! Team C elimina Team A ai quarti di coppa", "🏆 Finale scudetto: Team B vs Team D — si decide tutto domenica". Questo dà presenza e peso alle competizioni secondarie.

**File da modificare:**
- `src/season.py` — nuova funzione `generate_cup_headlines(bracket: CupBracket) -> list[str]`:
  - Itera i round, identifica upset (team con rating inferiore che vince), finali, bye
  - Genera headline con template: "🚨 {winner} elimina {loser} al {round_name}!"
  - Per la finale: "🏆 {winner} vince la Coppa Nazionale!"
- `src/season.py` — nuova funzione `generate_playoff_headlines(bracket: PlayoffBracket) -> list[str]`:
  - Headline per ogni semifinale e finale
  - "🏆 {winner} CAMPIONE D'ITALIA!" con dettaglio sul punteggio
- `mobile/app.py` — dopo `simulate_cup()` e `simulate_playoff()` in `start_new_season()` (o dove vengono eseguiti), integrare le headline in `self.career_news`
- `mobile/screens.py` — in `CarrieraScreen`: le headline appaiono già nel feed news, ma aggiungere formattazione speciale per titoli di coppa/campionato (bold, colore oro per trofei)

**Complessità stimata:** Bassa  
**Impatto sul gameplay:** 6/10  
**Dipendenze dai must-have:**
- ✅ Coppa Nazionale (già implementata) — senza narrativa è invisibile
- ✅ Playoff (già implementato) — stesso problema

**Perché ora:** Mario ha costruito l'infrastruttura delle competizioni ma il giocatore non ne vede i risultati. Questo è il polish minimo per rendere i must-have effettivamente utilizzabili. Senza headlines, la coppa potrebbe non esistere e il giocatore non noterebbe la differenza.

---

## Riepilogo Next Cycle

| # | Suggerimento | Complessità | Impatto | Dipendenze |
|---|---|---|---|---|
| 1 | Derby e rivalità | Bassa | 8/10 | Nessuna |
| 2 | Obiettivi stagionali dinamici | Media | 8/10 | Nessuna |
| 3 | Rigori, corti e punizioni | Bassa | 7/10 | Nessuna |
| 4 | Sistema Sviluppo Youth Academy (nuovo) | Media | 7/10 | Youth Academy + Potenziale |
| 5 | Integrazione narrativa Coppa & Playoff (nuovo) | Bassa | 6/10 | Coppa + Playoff |

**Priorità di implementazione suggerita:**
1. Integrazione narrativa Coppa & Playoff (più urgente — rende visibili i must-have già fatti)
2. Derby e rivalità (più semplice, impatto immediato)
3. Rigori, corti e punizioni (arricchisce ogni partita)
4. Sistema Sviluppo Youth Academy (completa il loop youth)
5. Obiettivi stagionali dinamici (più complesso, ma dà scopo a lungo termine)

---

*Documento Fase 2 creato da Leonardo per il progetto Field Hockey Manager.*  
*Pronto per l'assegnazione a Mario (implementazione) e Raul (verifica).*