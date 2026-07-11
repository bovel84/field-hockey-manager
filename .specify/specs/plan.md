# Implementation Plan — Field Hockey Manager MVP

## Fasi

### Fase 1: Fondamenta dati
- Schema SQLite (tabelle: teams, players, matches, standings)
- Modelli Python (dataclasses per Player, Team, Match)
- Database init/migration script
- Test unità modelli

### Fase 2: Motore di simulazione
- Algoritmo simulazione partita (rating + random seed)
- Generazione eventi partita (gol, cartellini)
- Test simulazione (risultati deterministici con seed fisso)

### Fase 3: Gestione stagione
- Generazione calendario round-robin
- Squadre avversarie predefinite (5 squadre)
- Aggiornamento classifica dopo partita
- Test logica classifica

### Fase 4: UI terminale
- Menu principale (Squadra, Calendario, Classifica, Statistiche, Salva)
- Visualizzazione rosa con tabella formattata
- Visualizzazione risultato partita
- Loop interattivo

### Fase 5: Persistenza
- Salvataggio stato su SQLite
- Caricamento stato all'avvio
- Test salvataggio/caricamento

## Struttura file
```
field-hockey-manager/
├── src/
│   ├── models.py        # dataclass Player, Team, Match
│   ├── database.py      # SQLite init, CRUD
│   ├── simulation.py    # motore partita
│   ├── season.py         # calendario, classifica
│   ├── ui.py             # menu terminali
│   └── main.py           # entry point
├── tests/
│   ├── test_models.py
│   ├── test_simulation.py
│   ├── test_season.py
│   └── test_database.py
├── data/
│   └── teams.json       # 6 squadre predefinite
└── requirements.txt
```
