# FHM Task Board — 2026-07-12

## Pipeline: Leonardo → Mario → Raul → Tommy (loop)

### Task FHM-01: Game Design Suggestions
- **State:** ✅ Done
- **Owner:** Leonardo
- **Artifact:** `shared/leonardo_suggestions.md`
- **Output:** 15 suggerimenti, 5 must-have

### Task FHM-02: Implement 5 Must-Have Features
- **State:** 🔄 In Progress (R1 — fix post-review)
- **Owner:** Mario
- **Artifact:** `src/models.py`, `src/simulation.py`, `src/season.py`, `src/database.py`, `mobile/screens.py`, `mobile/app.py`
- **Done quando:** 153+ test passano, Raul approva, UI mobile integra le 5 feature
- **R1 review:** Raul 62/100 — RIFIUTATO (7 fix obbligatori)
- **Fix applicati da Zeus:** C1/C2/M1/M3 (coppa), m9 (DB migration), m7 (test), m10 (double-award), m1 (import), C3 parziale (teams.json)
- **Fix in corso Mario:** C3 (UI mobile), M2, m2-m6
- **Limiti:** non toccare `main.py`, non rompere i 96 test originali

### Task FHM-03: Code Review Round 2
- **State:** 🔄 In Progress
- **Owner:** Raul
- **Artifact input:** commit `9218f8a` + output Mario
- **Done quando:** review salvata in `shared/reviews/raul-review-r2.md` con voto 0-100
- **Limiti:** review su codice, non su design

### Task FHM-04: QA Final
- **State:** ⏳ Inbox
- **Owner:** Tommy
- **Artifact input:** output Raul R2
- **Done quando:** 100/100 test passano, verdict APPROVATO o lista fix
- **Limiti:** se <100, rimanda a Mario con lista specifica

## Anti-Rimbalzo
- Mario timeout al R1: Zeus ha fatto i fix critici direttamente, poi rilanciato Mario con task più stretto
- Raul killed al R1 per richieste approvazione: rilanciato con task solo-verifica
- Max 2 lane parallele: Mario (build) + Raul (verify fix Zeus) = ok

## Decision Log
- **2026-07-12:** Cambiato routing da "Mario=builder, Raul=reviewer" a "Zeus fa i fix critici, Mario fa UI mobile, Raul verifica" — motivazione: Mario timeout su bug logici, Zeus più veloce su fix mirati
- **2026-07-12:** Agenti persistenti (non spawnare nuovi, mandare messaggi alle sessioni esistenti)