# Task List — Field Hockey Manager MVP

## Fase 1: Fondamenta dati
- [ ] T1.1: Definire dataclass Player (nome, ruolo, rating per attributo, gol, presenze)
- [ ] T1.2: Definire dataclass Team (nome, giocatori, punti, gf, gs)
- [ ] T1.3: Definire dataclass Match (squadra_casa, squadra_ospite, risultato, eventi)
- [ ] T1.4: Creare schema SQLite (CREATE TABLE teams, players, matches, standings)
- [ ] T1.5: Implementare database.py (init, save_team, load_team, save_match, load_standings)
- [ ] T1.6: Scrivere test_models.py
- [ ] T1.7: Scrivere test_database.py

## Fase 2: Motore simulazione
- [ ] T2.1: Implementare simulate_match(team_a, team_b, seed) → Match
- [ ] T2.2: Algoritmo: rating squadra + fattore random → probabilità gol per quarto
- [ ] T2.3: Generazione eventi (gol, minuto, giocatore)
- [ ] T2.4: Scrivere test_simulation.py (seed fisso → risultato deterministico)

## Fase 3: Stagione
- [ ] T3.1: Creare 6 squadre predefinite in data/teams.json
- [ ] T3.2: Implementare generate_calendar(teams) → lista partite round-robin
- [ ] T3.3: Implementare update_standings(match_result, standings)
- [ ] T3.4: Scrivere test_season.py

## Fase 4: UI terminale
- [ ] T4.1: Menu principale con 5 opzioni
- [ ] T4.2: View rosa (tabella giocatori con rating)
- [ ] T4.3: View calendario (lista partite con risultati)
- [ ] T4.4: View classifica (tabella ordinata per punti)
- [ ] T4.5: View statistiche giocatore
- [ ] T4.6: Loop interattivo principale

## Fase 5: Persistenza
- [ ] T5.1: save_game(state) → SQLite
- [ ] T5.2: load_game() → state completo
- [ ] T5.3: Nuova stagione / Riprendi stagione all'avvio
- [ ] T5.4: Test salvataggio/caricamento

## Definition of Done
- Tutti i test passano con pytest
- Gioco giocabile da terminale
- Stato salvato tra sessioni
- Codice PEP8 compliant
