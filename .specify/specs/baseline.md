# Field Hockey Manager — Baseline Specification

## Vision
Un gioco manageriale di hockey su prato dove il giocatore gestisce una squadra: formazione, tattiche, calendario, trasferimenti e sviluppo dei giocatori.

## Obiettivi MVP
1. **Gestione squadra**: rosa giocatori con ruoli (portiere, difesa, centrocampo, attacco), rating abilità
2. **Calendario stagionale**: serie di partite con risultati generati da simulazione
3. **Risultati e classifiche**: punteggio, gol fatti/subiti, posizione in classifica
4. **UI terminale**: menu interattivi per navigare le sezioni

## Scope MVP (cosa è dentro)
- Creazione/Caricamento squadra con 16 giocatori
- Simulazione partita (algoritmo basato su rating squadra + random)
- Calendario di 10 partite (round-robin semplificato)
- Classifica con punti (3 vittoria, 1 pareggio, 0 sconfitta)
- Statistiche giocatore (gol, presenze, rating medio)
- Salvataggio/caricamento stato su SQLite

## Scope MVP (cosa è fuori)
- Trasferimenti mercati
- Allenamenti e sviluppo giocatori
- Tattiche avanzate
- AI avversario intelligente
- Multiplayer
- UI grafica

## User Stories
1. Come manager, voglio vedere la mia rosa con nome, ruolo, rating di ogni giocatore
2. Come manager, voglio simulare una partita e vedere il risultato
3. Come manager, voglio vedere il calendario della stagione
4. Come manager, voglio vedere la classifica aggiornata dopo ogni partita
5. Come manager, voglio vedere le statistiche dei miei giocatori
6. Come manager, voglio salvare e riprendere la stagione

## Regole di gioco
- Squadra: 16 giocatori (1 portiere, 4 difensori, 5 centrocampisti, 6 attaccanti)
- Rating giocatore: 1-100 per attributi (passaggio, tiro, difesa, velocità, resistenza)
- Rating squadra: media ponderata dei titolari (11 in campo)
- Partita: 4 quarti da 15 min, risultato basato su rating + fattore random
- Stagione: 10 partite round-robin contro 5 squadre avversarie
