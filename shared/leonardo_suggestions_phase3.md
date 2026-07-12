# 🏒 Field Hockey Manager — Suggerimenti Phase 3

**Autore:** Leonardo, Game Designer  
**Data:** 12 Luglio 2026  
**Ciclo:** Phase 3 — Visualizzazione 2D + Profondità e Realismo  
**Richiesta di Andrea:** Campo visivo con giocatori in movimento + miglioramenti per profondità

---

## Contesto

Il progetto ha ora: 52 squadre, 832 giocatori, 5 leghe, simulazione a quarti, sostituzioni, allenamenti, mercato, youth academy, coppa nazionale + playoff, derby/rivalità, obiettivi stagionali, rigori/corti angoli/cartellini verdi, save/load multi-slot, 226 test passanti.

La partita attualmente è **solo testo**: risultato finale + lista eventi. Il giocatore preme "Simula Partita" e ottiene una stringa. Nessun feedback visivo, nessuna tensione, nessun coinvolgimento emotivo. Questo è il salto più importante che FHM può fare ora.

---

## Riepilogo Suggerimenti

| # | Suggerimento | Impatto | Complessità | Priorità |
|---|---|---|---|---|
| 1 | **Visualizzazione 2D Partita** | 10/10 | Alta | 🔴 Critica |
| 2 | **Commento Testuale Live** | 8/10 | Bassa | 🔴 Critica |
| 3 | **Meteo e Condizioni Campo** | 7/10 | Media | 🟡 Alta |
| 4 | **Sistema Infortuni Esteso** | 7/10 | Media | 🟡 Alta |
| 5 | **Morale Dinamico Avanzato** | 6/10 | Media | 🟢 Media |
| 6 | **Scouting e Osservatori** | 6/10 | Media | 🟢 Media |
| 7 | **Award Individuali e Storia Carriera** | 5/10 | Bassa | 🟢 Media |

---

## SUGGERIMENTO 1 — Visualizzazione 2D Partita 🏟️

**Impatto: 10/10** | **Complessità: Alta** | **Priorità: 🔴 Critica**

### Descrizione

Trasformare la partita da "testo risultato finale" a **campo visivo 2D top-down** con giocatori che si muovono in tempo reale. Il giocatore guarda la partita svilupparsi quarto per quarto, vede i punti colorati muoversi sul campo, la pallina spostarsi, e gli eventi apparire con animazioni/testo.

Non serve 3D, sprite, o grafica complessa. Kivy ha una **Canvas API** con primitive grafiche (cerchi, linee, rettangoli) perfetta per un rendering top-down stile vecchio.

### Architettura Tecnica

#### 1.1 Nuovo widget: `MatchFieldWidget` (in `mobile/widgets.py`)

Questo è il cuore della visualizzazione. Un widget Kivy custom che disegna il campo e i giocatori usando `kivy.graphics` (Color, Ellipse, Line, Rectangle).

```
MatchFieldWidget(Widget)
├── canvas.before: sfondo verde campo
├── canvas: linee campo, aree, goal
├── canvas.after: giocatori (Ellipse), pallina (Ellipse), eventi overlay (Label)
└── Clock.schedule_interval(update, dt) → animazione
```

**Coordinate campo:** Il widget ha dimensioni in pixel (es. 400×600 portrait, 600×400 landscape). Il campo è mappato su coordinate normalizzate 0.0–1.0 per x (larghezza) e 0.0–1.0 per y (lunghezza). Le posizioni reali sono `x * width`, `y * height`.

**Disegno del campo hockey:**
- Sfondo: verde (`Color(0.18, 0.45, 0.22, 1)`)
- Bordi: linea bianca perimetrale (`Line`)
- Linea di metà campo: orizzontale al centro
- **Area circolo**: un cerchio nel centro del campo (raggio ~15% larghezza)
- **23m area**: rettangoli alle due estremità
- **Goal**: due brevi segmenti verticali ai lati corti
- Linee di penalty spot: piccoli cerchi alle due estremità

**Disegno giocatori:**
- 11 cerchi per squadra, raggio ~12px
- Casa: rosso (`Color(0.86, 0.20, 0.20, 1)`)  
- Ospite: blu (`Color(0.20, 0.40, 0.86, 1)`)
- Numero del giocatore disegnato al centro del cerchio (`Label` o `coretext`)
- Portiere: colore diverso (giallo/arancio)

**Pallina:**
- Punto bianco (`Ellipse` raggio ~5px)
- Si muove verso il possessore o verso la zona di attacco

#### 1.2 Formazioni e posizioni iniziali

Ogni formazione (4-3-3, 4-4-2, 3-5-2, 5-3-2) ha un set di coordinate normalizzate per 11 giocatori:

```python
# Esempio 4-3-3 (coordinate normalizzate 0-1, y=0 è proprio goal, y=1 è goal avversario)
FORMATION_POSITIONS = {
    "4-3-3": {
        "GK":  [(0.50, 0.05)],
        "DEF": [(0.20, 0.25), (0.40, 0.25), (0.60, 0.25), (0.80, 0.25)],
        "MID": [(0.25, 0.50), (0.50, 0.50), (0.75, 0.50)],
        "ATT": [(0.30, 0.75), (0.50, 0.75), (0.70, 0.75)],
    },
    "4-4-2": {
        "GK":  [(0.50, 0.05)],
        "DEF": [(0.20, 0.25), (0.40, 0.25), (0.60, 0.25), (0.80, 0.25)],
        "MID": [(0.15, 0.50), (0.38, 0.50), (0.62, 0.50), (0.85, 0.50)],
        "ATT": [(0.40, 0.75), (0.60, 0.75)],
    },
    # ... altre formazioni
}
```

La squadra away usa coordinate specchiate (y → 1-y).

#### 1.3 Animazione del movimento

La simulazione produce già eventi con `quarter` e `minute`. L'animazione deve:

1. **Mappare ogni evento a un timestamp** (i 60 minuti di una partita → es. 60 secondi a 1x, 30s a 2x, 15s a 4x)
2. **Clock di Kivy**: `Clock.schedule_interval(self._tick, 1/30)` → 30 FPS
3. Ogni tick:
   - Avanza il "tempo di gioco" di `dt * speed_multiplier`
   - Quando si raggiunge il minuto di un evento, lo attiva (animazione + overlay testo)
   - I giocatori si muovono verso le loro posizioni target con interpolazione lineare semplice
   - La pallina si muove verso il giocatore in possesso o verso la goal avversaria
4. **Tra eventi**: movimento "idle" — i giocatori oscillano leggermente attorno alla loro posizione base (random walk contenuto) per dare vita al campo

#### 1.4 Overlay eventi

Quando un evento si attiva:
- **Gol**: flash del campo (bianco per 0.3s), testo "GOAL!" grande al centro, nome del marcatore
- **Cartellino verde**: icona 🟢 + nome giocatore sospeso, il giocatore lampeggia per 2s
- **Corto angolo**: testo "📐 PENALTY CORNER" + freccia verso l'area
- **Rigore**: testo "🎯 PENALTY STROKE" + tensione (zoom o shake leggero)
- **Sostituzione**: testo "🔄 OUT: nome → IN: nome", il cerchio del giocatore sostituito cambia colore
- **Infortunio**: testo "🔴 INJURY: nome" + il giocatore diventa grigio

#### 1.5 Controlli di velocità

Pulsanti: **1x | 2x | 4x** visibili sotto il campo. Modificano `speed_multiplier`. Un pulsante **⏸ Pausa** congela l'animazione. Un pulsante **⏭ Salta** salta al risultato finale.

#### 1.6 Integrazione con `PartitaScreen`

Modificare `PartitaScreen` in `mobile/screens.py`:
- Sostituire/affiancare il `result_label` + `events_label` con `MatchFieldWidget`
- Dopo la simulazione (`simulate_match()`), passare il `match` (con eventi) al widget
- Il widget anima gli eventi in sequenza
- Al termine, mostra il risultato finale + lista eventi testuale sotto il campo

### File da modificare/creare

| File | Azione | Descrizione |
|---|---|---|
| `mobile/widgets.py` | **Modificare** | Aggiungere `MatchFieldWidget` (~200-300 righe) |
| `mobile/screens.py` | **Modificare** | Aggiornare `PartitaScreen` per usare `MatchFieldWidget` + controlli velocità |
| `src/simulation.py` | **Estendere** | Aggiungere `generate_match_timeline(match) -> list[dict]` che mappa eventi a posizioni dei giocatori nel tempo |
| `src/models.py` | **Estendere** | Aggiungere `formation_positions` dict (coordinate normalizzate per ogni formazione) |
| `tests/test_match_visual.py` | **Creare** | Test per `generate_match_timeline()` — verifica sequenza eventi e coordinate |

### Note implementative

- **Performance**: 22 cerchi + 1 pallina + linee campo = ~30 primitive grafiche. Kivy le renderizza a 60 FPS senza problemi anche su hardware modesto.
- **Coordinate normalizzate**: il widget è responsivo. Tutte le posizioni sono 0.0–1.0 e vengono scalate al resize del widget.
- **No sprite**: i giocatori sono `Ellipse` con `Color`. Il numero è un `Label` figlio del widget o un `CoreText` renderizzato. Più semplice e performante.
- **Stato animazione**: il widget tiene uno stato `self.match_time` (0-60) e un indice `self.event_index` per scorrere gli eventi in ordine.
- **Accessibilità**: se l'utente disabilita l'animazione (impostazione), fallback al testo come ora.
- **Reuse**: `MatchFieldWidget` può essere riutilizzato per visualizzare replay o highlight di altre partite della stagione.

### Esempio di flusso

```
Utente preme "🏒 Simula Partita"
  → simulate_match() produce Match con events[]
  → generate_match_timeline(match) produce timeline[{time, event, positions}]
  → MatchFieldWidget.set_timeline(timeline)
  → Clock.start() → animazione parte a 1x
  → Eventi appaiono in sequenza: 5' corto angolo → 12' gol → 28' cartellino verde → ...
  → 60' fine → mostra risultato finale
```

---

## SUGGERIMENTO 2 — Commento Testuale Live 📝

**Impatto: 8/10** | **Complessità: Bassa** | **Priorità: 🔴 Critica**

### Descrizione

Il `events_label` attuale mostra una lista piatta di eventi dopo la partita. Trasformare in un **feed testuale live** che si aggiorna in tempo reale durante l'animazione 2D, con commento narrativo stile radiocronaca.

Invece di:
```
5' - corner_goal: Marco Rossi
12' - goal: Luca Bianchi
```

Produce:
```
📻 5' — Corto angolo per la squadra di casa! Marco Rossi in posizione... GOAL! 
    La difesa non ha reagito, 1-0!

📻 12' — Belle manovre al centro. Luca Bianchi riceve e tira... GOAL! 
    Raddoppio! Che partita!

📻 28' — Cartellino verde per Francesco Verdi. 2 minuti di sospensione, 
    la squadra resta in 10.

📻 45' — Fine primo tempo. Dominio della squadra di casa.
```

### Implementazione

- **Template di commento** per ogni tipo di evento: gol, corner_goal, penalty_goal, penalty_missed, penalty_corner, green_card, injury, substitution, fine quarto
- **Variabilità**: 3-4 template per tipo, scelta casuale (seed dalla partita per riproducibilità)
- **Tono**: cambia in base al punteggio (squadra in vantaggio → elogi; sconfitta → critiche; parità → tensione)
- **Contesto derby**: commenti extra su tensione/rivalità ("derby infuocato", "tifo da pelle d'oca")
- **Integrazione**: il commento appare contemporaneamente all'evento visivo nel `MatchFieldWidget`

### File da modificare

| File | Azione |
|---|---|
| `src/simulation.py` | Aggiungere `generate_commentary(match, event) -> str` con template per tipo |
| `mobile/widgets.py` | `MatchFieldWidget` mostra il commento in un panel testuale sotto il campo |
| `mobile/screens.py` | `PartitaScreen` passa il commento al widget durante l'animazione |

### Note implementative

- I template sono stringhe Python con placeholder `{scorer}`, `{team}`, `{minute}`, `{score}`
- Nessuna dipendenza esterna (no NLP, no API). Template puri.
- Il feed si scrolla automaticamente (ultimo commento in fondo visibile)
- Massimo 5-6 commenti visibili contemporaneamente, scrollable per gli storici

---

## SUGGERIMENTO 3 — Meteo e Condizioni Campo 🌦️

**Impatto: 7/10** | **Complessità: Media** | **Priorità: 🟡 Alta**

### Descrizione

Le partite si giocano in condizioni meteorologiche variabili che influenzano il gameplay:

- **Sole/cielo sereno** (40%): condizioni normali
- **Pioviggine** (25%): -5% ai fattori gol di entrambe le squadre (campo scivoloso, passaggi imprecisi)
- **Pioggia forte** (15%): -10% gol, +50% probabilità di cartellini verdi (gioco più fisico), +20% infortunio
- **Campo bagnato post-pioggia** (10%): -5% gol, +10% velocità (palla scivola veloce)
- **Nebbia** (5%): -15% gol (visibilità ridotta), partite più tattiche
- **Caldo torrido** (5%): stamina decay raddoppiata nei quarti 3-4, sostituzioni più importanti

Il meteo è determinato random all'inizio di ogni partita (seed per riproducibilità) e ha un effetto visivo sul campo 2D:
- Pioggia: linee blu sovrapposte al campo (animazione semplice)
- Nebbia: overlay grigio semi-trasparente
- Sole: nessun overlay, campo leggermente più luminoso

### Implementazione

- `src/simulation.py`: aggiungere `generate_weather(rng) -> dict` con tipo, intensità, e modificatori
- `simulate_match()`: applicare modificatori weather a `home_factor`, `away_factor`, `_stamina_decay`, probabilità green card
- `src/models.py`: aggiungere `weather: str = ""` a `Match`
- `mobile/widgets.py`: `MatchFieldWidget` disegna overlay meteo (pioggia, nebbia) sul canvas
- `mobile/screens.py`: mostrare icona meteo prima della partita e durante

### File da modificare

| File | Azione |
|---|---|
| `src/simulation.py` | Aggiungere `generate_weather()`, applicare modificatori in `simulate_match()` |
| `src/models.py` | Aggiungere campo `weather` a `Match` |
| `mobile/widgets.py` | Overlay meteo in `MatchFieldWidget` |
| `mobile/screens.py` | Mostra meteo in `PartitaScreen` |

### Note implementative

- Il meteo è persistito nel `Match` e salvato nel database, quindi le partite storiche mantengono il meteo
- I modificatori sono percentuali, non valori assoluti, per non sballare i rating
- La probabilità del meteo può variare per "stagione" (estate vs inverno) in futuro

---

## SUGGERIMENTO 4 — Sistema Infortuni Esteso 🏥

**Impatto: 7/10** | **Complessità: Media** | **Priorità: 🟡 Alta**

### Descrizione

Il sistema infortuni attuale è base: 5-10% probabilità, 1-3 partite di durata. Estendere con:

- **Tipi di infortunio**: lieve (1-2 partite), moderato (3-5 partite), grave (6-10 partite), stagione finita
- **Cause**: affaticamento (stamina bassa → più probabile), tackle duro (green card avversario → +5% rischio), meteo (pioggia → +20%), età (over 32 → +15%)
- **Prevenzione**: sostituzioni tempestive riducono il rischio; allenamenti specifici (es. "prevenzione") riducono il rischio per la settimana successiva
- **Riabilitazione**: un giocatore infortunato può recuperare 1 partita prima se il manager usa l'azione "Cure mediche" (costa budget, 1 volta per stagione per giocatore)
- **Effetto morale**: un infortunio grave al giocatore stella dà -10 morale a tutta la squadra

### Implementazione

- `src/models.py`: aggiungere `injury_type: str = ""` a `Player` (lieve, moderato, grave, stagione)
- `src/simulation.py`: estendere `_check_injuries()` con tipo di infortunio, causa, e durata basata su tipo
- `mobile/app.py`: aggiungere azione "Cure mediche" (menu Rosa → giocatore infortunato → usa cure, -100 budget, -1 match duration)
- `mobile/screens.py`: in `RosaScreen`, mostrare tipo infortunio e opzione cure

### File da modificare

| File | Azione |
|---|---|
| `src/models.py` | Aggiungere `injury_type`, `injury_cause` a `Player` |
| `src/simulation.py` | Estendere `_check_injuries()` con tipi e cause |
| `mobile/app.py` | Azione "Cure mediche" |
| `mobile/screens.py` | UI per cure mediche e visualizzazione tipo infortunio |
| `tests/test_simulation.py` | Test per tipi di infortunio |

---

## SUGGERIMENTO 5 — Morale Dinamico Avanzato 🧠

**Impatto: 6/10** | **Complessità: Media** | **Priorità: 🟢 Media**

### Descrizione

Il morale attuale cambia di ±10 dopo ogni partita. Estendere a un sistema più realistico:

- **Fonti di morale**:
  - Risultati partite (già esistente, ma bilanciare: vittoria +8, pareggio +2, sconfitta -8, sconfitta derby -15)
  - Tempo di gioco: un giocatore in panchina per 3 partite consecutive perde -3 morale/settimana
  - Gol/assist: marcatore +5, assistman +3
  - Infortuni: giocatore infortunato -2/settimana
  - Sostituzioni: un giocatore sostituito al 60' quando la squadra vince +1 (apprezzato)
  - Allenamenti: miglioramento attributi +2, nessun miglioramento -1
  - Posizione in classifica: top 3 → +3/settimana, zona retrocessione → -3/settimana

- **Morale di squadra**: media dei morali individuali, influenza il `team_rating()` con un moltiplicatore ±5%
- **Eventi di crisi**: se il morale medio scende sotto 25, 30% probabilità di "crisi di spogliatoio" — un evento narrativo che dà -5 morale a tutti e una notizia in `career_news`
- **Bonus morale**: se un giocatore supera 85 morale, ha +3% `effective_rating` (già esistente ma più marcato)

### Implementazione

- `mobile/app.py`: in `_update_career_after_match()`, calcolare morale per ogni giocatore non solo la squadra
- `src/models.py`: aggiungere `games_on_bench: int = 0` a `Player` per tracciare panchina
- `src/season.py`: nuovo `update_morale_weekly(team)` chiamato ad ogni nuova giornata

### File da modificare

| File | Azione |
|---|---|
| `mobile/app.py` | Estendere aggiornamento morale post-partita |
| `src/models.py` | Aggiungere `games_on_bench` a `Player` |
| `src/season.py` | Aggiungere `update_morale_weekly()` |
| `mobile/screens.py` | Mostrare morale individuale in `RosaScreen` (già parzialmente visibile) |

---

## SUGGERIMENTO 6 — Scouting e Osservatori 🔭

**Impatto: 6/10** | **Complessità: Media** | **Priorità: 🟢 Media**

### Descrizione

Il mercato attuale mostra tutti i giocatori disponibili con rating visibile. Aggiungere un sistema di **scouting** che nasconde i dettagli dei giocatori non ancora scoutati:

- **Osservatori**: il manager ha 1-3 osservatori. Ogni osservatore può "scoutare" 1 giocatore a settimana, rivelando attributi nascosti e potenziale reale
- **Giocatori non scoutati**: nel mercato e nei youth prospects, mostrano solo nome, età, posizione, e un rating stimato (±10 dal reale). Il rating stimato è approssimativo
- **Scouting completo**: dopo un'ossessione completa, tutti gli attributi e il potenziale reale sono visibili
- **Draft di Youth Academy**: prima di promuovere un youth player, serve scouterlo. Questo dà peso alla decisione
- **Osservatori migliori**: spendendo budget (200, 400, 600) si possono assumere osservatori migliori che rivelano più informazioni per scouting o riducono il tempo

### Implementazione

- `src/models.py`: aggiungere `scouted: bool = False` e `estimated_rating: int = 0` a `Player`
- `mobile/app.py`: aggiungere `scouts: list[dict]` con `{"name", "level", "assignments_left"}`
- `mobile/screens.py`: nuova `ScoutingScreen` con lista giocatori da scoutare e azione "Manda osservatore"
- `mobile/app.py`: `scout_player(player)` rivela attributi, consuma 1 assignment

### File da modificare

| File | Azione |
|---|---|
| `src/models.py` | Aggiungere `scouted`, `estimated_rating` a `Player` |
| `mobile/app.py` | Sistema osservatori e `scout_player()` |
| `mobile/screens.py` | Nuova `ScoutingScreen` |
| `mobile/widgets.py` | `PlayerCard` mostra rating stimato se non scoutato |

---

## SUGGERIMENTO 7 — Award Individuali e Storia Carriera 🏅

**Impatto: 5/10** | **Complessità: Bassa** | **Priorità: 🟢 Media**

### Descrizione

A fine stagione, assegnare award individuali per dare profondità narrativa:

- **Capocannoniere** (mostro giocatore con più gol stagionali)
- **MVP della stagione** (giocatore con overall + gol + apparizioni più alto)
- **Best Young** (under 21 con migliori performance)
- **Golden Glove** (portiere con meno gol subiti)
- **Manager of the Year** (se la squadra raggiunge o supera gli obiettivi)

Ogni award dà +5 morale al vincitore, +2 morale alla squadra, e una notizia in `career_news`. Gli award sono persistiti nello storico carriera.

Inoltre, costruire uno **storico carriera** del giocatore:
- Statistiche per stagione: presenze, gol, assist, rating medio, trofei vinti
- Hall of Fame interna: top 10 marcatori di sempre, top 10 presenze, top 10 MVP
- Visualizzabili in `CarrieraScreen` con una sezione "Storia e Record"

### Implementazione

- `mobile/app.py`: in `start_new_season()` (fine stagione), calcolare e assegnare award
- `src/models.py`: aggiungere `season_stats: list[dict]` a `Player` per storico
- `mobile/screens.py`: sezione "Award" e "Hall of Fame" in `CarrieraScreen`
- `src/database.py`: persistere award e season_stats

### File da modificare

| File | Azione |
|---|---|
| `mobile/app.py` | Calcolo award fine stagione |
| `src/models.py` | Aggiungere `season_stats`, `awards` a `Player` |
| `src/database.py` | Persistere award e storico |
| `mobile/screens.py` | UI per award e Hall of Fame |

---

## Roadmap di Implementazione Suggerita

### Sprint 1 (settimana 1-2): Il salto visivo
1. **Visualizzazione 2D Partita** (Suggerimento 1) — la feature più importante, dà senso a tutto il gioco
2. **Commento Testuale Live** (Suggerimento 2) — complementare alla 2D, implementabile in parallelo

### Sprint 2 (settimana 3): Profondità partita
3. **Meteo e Condizioni Campo** (Suggerimento 3) — visivamente integrato nel 2D
4. **Sistema Infortuni Esteso** (Suggerimento 4) — arricchisce la gestione rosa

### Sprint 3 (settimana 4): Gestione a lungo termine
5. **Morale Dinamico Avanzato** (Suggerimento 5) — profondezza strategica
6. **Scouting e Osservatori** (Suggerimento 6) — decisioni più pesanti
7. **Award Individuali e Storia Carriera** (Suggerimento 7) — polish narrativo

### Dipendenze

```
Suggerimento 1 (2D) ← Suggerimento 2 (Commento live): integrato nel widget
Suggerimento 1 (2D) ← Suggerimento 3 (Meteo): overlay visivo nel campo
Suggerimento 5 (Morale) → indipendente ma beneficia di Suggerimento 4 (Infortuni)
Suggerimento 6 (Scouting) → dipende dal mercato esistente
Suggerimento 7 (Award) → indipendente, pure data work
```

---

## Considerazioni Finali

### Perché la 2D è la priorità assoluta

FHM attualmente è un **gioco di numeri**. Si guarda il rating, si preme un bottone, si legge un risultato. Non c'è momento di "guardare la partita". La visualizzazione 2D trasforma FHM da foglio di calcolo a **gioco**. Il giocatore:
- Vede la propria tattica funzionare (o fallire)
- Sente la tensione del corto angolo
- Si arrabbia per il cartellino verde al momento sbagliato
- Si emoziona per il gol della bandiera all'ultimo quarto

Tutto questo con primitive grafiche semplici — cerchi, linee, colori. Non serve un motore 3D. Un campo verde con 22 puntini che si muovono è **immediatezza pura** ed è esattamente lo stile "vecchio" che Andrea vuole.

### Performance

Kivy Canvas con 30 primitive grafiche a 30 FPS è trivialmente gestibile da qualsiasi smartphone. Nessun rischio di lag.

### Test

Per la 2D, i test automatizzabili riguardano:
- `generate_match_timeline()` — verifica ordinamento eventi, coordinate valide, nessun evento perso
- `FORMATION_POSITIONS` — verifica 11 giocatori per formazione, coordinate in [0,1]
- I test grafici (rendering) sono manuali, come normale per UI.

### Modularità

Tutti i 7 suggerimenti sono **additivi**: non modificano la logica esistente di simulazione, ma aggiungono layer sopra. Questo significa:
- La 2D non cambia come funziona `simulate_match()`, solo come si **visualizza**
- Il meteo aggiunge modificatori ma il core rimane
- Il morale estende il sistema esistente, non lo rimpiazza

---

*Documento Phase 3 creato da Leonardo per il progetto Field Hockey Manager.*  
*Pronto per l'assegnazione a Mario (implementazione) e Raul (verifica).*