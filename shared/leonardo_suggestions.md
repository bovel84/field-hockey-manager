# 🏒 Field Hockey Manager — Suggerimenti di Game Design

**Autore:** Leonardo, Game Designer  
**Data:** 12 Luglio 2026  
**Versione progetto:** 96 test, 6 squadre, 10 partite/stagione, multi-stagione con aging

---

## 1. GAMEPLAY CORE — Meccaniche che rendono il gioco più divertente e profondo

### 1.1 Sostituzioni in-partita
**Descrizione:** Permetti al manager di effettuare fino a 3 sostituzioni durante la simulazione, scegliendo quando (minuto) e quali giocatori inserire. I titolari stanchi calano di rating nei quarti finali.  
**Implementazione:** Aggiungere `_stamina_decay()` in `simulation.py` che riduce `effective_rating` in base ai minuti giocati e `stamina`. Nuovo metodo `make_substitution()` in `app.py`. Schermata partita da estendere con sezione panchina.  
**Complessità:** Media  
**Priorità:** 1

### 1.2 Chimica di squadra
**Descrizione:** Introduci un valore di "chimica" (0-100) che aumenta quando gli stessi 11 giocatori scendono in campo partita dopo partita, e si resetta con nuovi acquisti o troppe rotazioni. Chimica alta = +3 al team rating, chimica bassa = -3.  
**Implementazione:** Nuovo campo `chemistry: int = 50` in `Team` (`models.py`). Incremento in `_apply_result()` (`app.py`) se stessi titolari. Modificatore in `team_rating()` o `simulate_match()`.  
**Complessità:** Media  
**Priorità:** 2

### 1.3 Tattiche avanzate: pressing e contropiede
**Descrizione:** Oltre a formazione/intensità, aggiungi due toggle tattici: **Pressing** (più fallo, più recupero palla, più stanchezza) e **Contropiede** (difesa bassa + transizione rapida, efficace contro squadre offensive).  
**Implementazione:** Nuovi parametri `pressing: bool` e `counterattack: bool` in `simulate_match()` (`simulation.py`). Nuovi modificatori in `_INTENSITY_MODIFIERS` o dizionario separato. UI: due toggle button in `PartitaScreen`.  
**Complessità:** Bassa  
**Priorità:** 2

### 1.4 Rigori, corti e punizioni
**Descrizione:** Aggiungi eventi speciali: rigori (5% probabilità per partita), corto angoli (corner) che possono generare gol con probabilità basata sul rating difensivo. Questi eventi creano momenti di tensione anche in partite Otherwise piatte.  
**Implementazione:** Nuove funzioni `_check_penalty()` e `_check_corner()` in `simulation.py`. Nuovi tipi di evento `"penalty"` e `"corner"` nel match events.  
**Complessità:** Bassa  
**Priorità:** 2

---

## 2. REALISMO — Elementi che aumentano l'immersione

### 2.1 Nazionale e convocazioni
**Descrizione:** A fine stagione, i migliori giocatori (OVR ≥ 80) possono essere convocati in nazionale. Tornano con +1 morale ma potrebbero saltare le prime 2 partite per stanchezza. Evento narrativo nella schermata carriera.  
**Implementazione:** Funzione `check_national_callups()` in `season.py` eseguita in `start_new_season()`. Flag `national_callup: bool` e `national_fatigue: int` in `Player`.  
**Complessità:** Media  
**Priorità:** 2

### 2.2 Coppa Nazionale (knockout)
**Descrizione:** Oltre al campionato, una coppa a eliminazione diretta con sorteggio casuale. Partite singole, non andata/ritorno. La vincitrice ottiene budget extra e prestigio. Doppio obiettivo = doppia tensione.  
**Implementazione:** Nuova funzione `generate_cup_bracket()` in `season.py`. Nuovo stato `cup_round` in `app.py` e `database.py` (tabella `cup_matches`). Schermata aggiuntiva o sezione in `CarrieraScreen`.  
**Complessità:** Alta  
**Priorità:** 1

### 2.3 Contratti dei giocatori
**Descrizione:** Ogni giocatore ha un contratto con durata (1-3 stagioni). A scadenza, il giocatore può rinnovare (se morale alto) o lasciare gratis. Aggiunge decisioni su budget: rinnovare un campione costa, lasciarlo andare libera risorse.  
**Implementazione:** Campo `contract_years: int` in `Player` (`models.py`). Funzione `expire_contracts()` in `season.py` eseguita in `start_new_season()`. Logica rinnovo basata su morale + budget.  
**Complessità:** Media  
**Priorità:** 2

---

## 3. PROGRESSIONE — Sistemi che danno senso di avanzamento

### 3.1 Youth Academy
**Descrizione:** Ogni stagione, la squadra genera 1-2 giovani talenti (16-18 anni, rating 40-60 ma con potenziale alto). Il manager può promuoverli in prima squadra o lasciarli in academy per sviluppo. Dà un senso di costruzione a lungo termine.  
**Implementazione:** Funzione `generate_youth_prospects()` in `season.py`. Lista `youth_players` in `Team` o gestita a livello app. Nuova schermata `YouthScreen` o sezione in `RosaScreen`.  
**Complessità:** Media  
**Priorità:** 1

### 3.2 Sistema potenziale e crescita
**Descrizione:** Ogni giocatore ha un valore `potential` (rating massimo raggiungibile). Gli allenamenti non possono superare il potenziale. Giovani con potenziale alto ma rating basso = progetti a lungo termine. Mostra il potenziale solo per giocatori under-23.  
**Implementazione:** Campo `potential: int` in `Player` (`models.py`), generato in `generate_free_agents()` e creazione squadre. Check in `train_player()` (`season.py`).  
**Complessità:** Bassa  
**Priorità:** 1

### 3.3 Obiettivi stagionali dinamici con ricompense
**Descrizione:** Ogni stagione la dirigenza fissa 2-3 obiettivi specifici (es. "arriva top-3", "segna 20+ gol", "non perdere più di 3 di fila"). Completarli dà budget extra, reputazione e fiducia. Fallirli ha conseguenze.  
**Implementazione:** Lista `season_goals: list[dict]` in `app.py`, generata in `start_new_season()`. Check in `_update_career_after_match()` e fine stagione.  
**Complessità:** Media  
**Priorità:** 2

### 3.4 Allenatore specializzato
**Descrizione:** Il manager può assumere un allenatore specializzato (es. "Allenatore difensivo" = +1 difesa agli allenamenti, "Allenatore attacco" = +1 tiro). Un allenatore alla volta, costo iniziale + stipendio stagionale.  
**Implementazione:** Nuovo modello `Coach` in `models.py` con `specialty`, `level`, `salary`. Stato in `app.py` e persistenza in `database.py`.  
**Complessità:** Media  
**Priorità:** 3

---

## 4. TENSIONE/DRAMA — Eventi che creano emozione

### 4.1 Playoff scudetto e playout salvezza
**Descrizione:** A fine campionato, le prime 4 accedono ai playoff (semifinali + finale secca). L'ultima va ai playout contro la 5ª. Il titolo si decide in una finale unica ad alta tensione. Questo trasforma le ultime giornate in battaglie per ogni posizione.  
**Implementazione:** Funzioni `generate_playoff_bracket()` e `simulate_playoff()` in `season.py`. Eseguiti dopo l'ultima giornata in `start_new_season()` o in un nuovo metodo `end_season()`.  
**Complessità:** Alta  
**Priorità:** 1

### 4.2 Derby e rivalità
**Descrizione:** Definisci coppie di rivali nel `teams.json`. Nei derby, il morale di tifosi e giocatori è influenzato dal risultato in modo raddoppiato. Eventi speciali pre-partita ("tifo infuocato", "pressione mediatica").  
**Implementazione:** Campo `rivals: list[str]` in `Team` (`models.py`) o mappa separata. Modificatore in `_update_career_after_match()` (`app.py`) e in `simulate_match()` (home advantage raddoppiato).  
**Complessità:** Bassa  
**Priorità:** 2

### 4.3 Crisi di spogliatoio e ribellioni
**Descrizione:** Se la squadra accumula 3+ sconfitte consecutive con morale medio < 40, scatta un evento "crisi": il capitano può ribellarsi, i tifosi protestano, la dirigenza minaccia il licenziamento. Il manager deve prendere una decisione (disciplina, incontro, o cambia formazione).  
**Implementazione:** Funzione `check_crisis()` in `app.py` chiamata dopo ogni partita. Nuovi eventi narrativi in `career_news`. Possibile game over se la board confidence scende a 0.  
**Complessità:** Media  
**Priorità:** 2

### 4.4 Finale di stagione: Awards individuali
**Descrizione:** A fine stagione, assegna riconoscimenti individuali: MVP (miglior giocatore della lega per rating), Capocannoniere (più gol), Miglior Portiere (meno gol subiti tra i titolari). I vincitori ottengono +10 morale e interesse sul mercato.  
**Implementazione:** Funzione `compute_season_awards()` in `season.py`, chiamata in `start_new_season()`. Risultati mostrati in `CarrieraScreen` come news.  
**Complessità:** Bassa  
**Priorità:** 2

---

## 5. POLISH — Piccoli dettagli che fanno la differenza

### 5.1 Commento testuale dinamico
**Descrizione:** Genera un breve commento testuale per ogni partita che descrive il momento chiave (es. "Rallenti al 55', gol decisivo di Rossi che ribaltaava il risultato"). Attualmente il feed eventi è solo una lista tecnica.  
**Implementazione:** Funzione `generate_match_commentary(match)` in `simulation.py` o nuovo modulo `commentary.py`. Stringhe template con placeholders. Mostrato in `PartitaScreen` sotto il risultato.  
**Complessità:** Bassa  
**Priorità:** 2

### 5.2 Storia e record di carriera
**Descrizione:** Mantieni una hall of fame: stagioni giocate, vittorie totali, gol totali, trofei vinti. Accessibile da una schermata "Carriera → Albo d'oro". Dà senso di legacy e accumulo.  
**Implementazione:** Nuovi campi in `game_state` (`database.py`): `career_stats: dict`, `trophies: list`. Aggiornamento in `start_new_season()`. Schermata o sezione in `CarrieraScreen`.  
**Complessità:** Bassa  
**Priorità:** 3

### 5.3 Formazione visualizzata a campo
**Descrizione:** Nella schermata Rosa/Partita, mostra i titolari disposti su un campo di hockey (portiere in basso, difesa, centrocampo, attacco). Aiuta a visualizzare la formazione scelta e identificare gap.  
**Implementazione:** Nuovo widget `FormationField` in `mobile/widgets.py` con posizionamento calcolato dalla formazione (4-3-3, ecc.). Integrato in `PartitaScreen` o nuova schermata `FormazioneScreen`.  
**Complessità:** Media  
**Priorità:** 3

---

## Riepilogo Priorità

| Priorità | Idee |
|----------|------|
| **1 (Must have)** | Sostituzioni, Playoff, Coppa Nazionale, Youth Academy, Sistema potenziale |
| **2 (Nice to have)** | Chimica, Tattiche avanzate, Rigori/corti, Nazionale, Contratti, Obiettivi dinamici, Derby, Crisi, Awards, Commento testuale |
| **3 (Cool but optional)** | Allenatore specializzato, Hall of fame, Formazione a campo |

**Totale suggerimenti:** 15

---

*Documento creato da Leonardo per il progetto Field Hockey Manager.*  
*Pronto per la revisione del team.*