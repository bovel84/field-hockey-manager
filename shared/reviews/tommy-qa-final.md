# QA Final Report — Field Hockey Manager (FHM)

**Commit:** 6ece67e (HEAD) — feat: multi-slot save/load with SaveLoadScreen + 16 tests  
**Data:** 2026-07-12  
**QA Engineer:** Tommy  

---

## Punteggio: 88/100

## Verdetto: ❌ FAIL (soglia ≥ 90)

---

## 1. Suite di Test

| Metrica | Valore |
|---------|--------|
| Test raccolti | 203 |
| Test passati | 203 |
| Test falliti | 0 |
| Test saltati | 0 |
| Durata | 1.88s |
| Piattaforma | Python 3.14.6, pytest 9.1.1, macOS |

**Risultato:** ✅ Tutti i 203 test passano, nessun skip, nessun fallimento.

---

## 2. File di Test Raccolti (12 moduli)

| File | Test | Modulo coperto |
|------|------|----------------|
| tests/test_database.py | 13 | src/database.py |
| tests/test_database_new_fields.py | 5 | src/database.py (nuovi campi) |
| tests/test_derby.py | 10 | src/simulation.py (derby) |
| tests/test_edge_cases.py | 19 | src/models, src/season, src/simulation |
| tests/test_fixes.py | 12 | src/simulation, src/season (auto-subs, cup, playoff) |
| tests/test_models.py | 16 | src/models.py |
| tests/test_narrative.py | 10 | src/simulation.py (headlines) |
| tests/test_playoff_cup.py | 17 | src/simulation.py (playoff/cup) |
| tests/test_potential_system.py | 16 | src/models.py, src/season.py (potential) |
| tests/test_save_load.py | 16 | src/database.py (save slots) |
| tests/test_season.py | 21 | src/season.py |
| tests/test_simulation.py | 10 | src/simulation.py |
| tests/test_substitutions.py | 10 | src/simulation.py (subs/stamina) |

---

## 3. Copertura Moduli

| Modulo | Testato | Note |
|--------|---------|------|
| `src/models.py` | ✅ Diretto | 16 test in test_models.py |
| `src/simulation.py` | ✅ Diretto | 10 test + test derby/subs/narrative/fixes |
| `src/season.py` | ✅ Diretto | 21 test in test_season.py |
| `src/database.py` | ✅ Diretto | 13 + 5 + 16 test (CRUD, nuovi campi, save/load) |
| `src/main.py` | ⚠️ Indiretto | test_main_module_importable |
| `src/ui.py` | ❌ Non testato | Nessun test diretto |
| `mobile/app.py` | ❌ Non testato | Import fallisce per SyntaxError in screens.py |
| `mobile/screens.py` | ❌ Non compilabile | SyntaxError alla riga 238 |
| `mobile/widgets.py` | ❌ Non testato | Nessun test |

**Totale file sorgente:** 11 (esclusi `__init__.py`)  
**Testati direttamente:** 4/11 (36%)  
**Testati indirettamente:** 1/11  
**Non testati / non compilabili:** 6/11

---

## 4. Integrità Dati

| File | Stato | Dimensione |
|------|-------|------------|
| data/teams.json | ✅ JSON valido | 35 KB |
| data/leagues.json | ✅ JSON valido | 245 KB |
| data/fhm.db | ✅ Presente | 53 KB |

Nessun problema di integrità dati.

---

## 5. Import Check

```
./.venv/bin/python -c "import mobile.app; import mobile.screens; import src.models; import src.simulation; import src.season; import src.database; print('OK')"
```

**Risultato: ❌ FALLITO**

```
File "mobile/screens.py", line 238
    text="🔥 Derby",", font_size="12sp", color=(0.95, 0.4, 0.1, 1),
                                  ^
SyntaxError: invalid decimal literal
```

L'errore impedisce l'import di `mobile.screens` e, per dipendenza, anche `mobile.app`.

I moduli `src/models`, `src/simulation`, `src/season`, `src/database` importano correttamente (verificato singolarmente).

---

## 6. Sintassi

| File | Stato |
|------|-------|
| src/models.py | ✅ OK |
| src/simulation.py | ✅ OK |
| src/season.py | ✅ OK |
| src/database.py | ✅ OK |
| mobile/app.py | ✅ Sintassi OK (ma import fallisce per dipendenza) |
| mobile/screens.py | ❌ SyntaxError riga 238 |

**Dettaglio errore:**

```python
# mobile/screens.py, riga 238 (dentro CalendarioScreen)
text="🔥 Derby",", font_size="12sp", color=(0.95, 0.4, 0.1, 1),
```

C'è una virgola e virgolette extra dopo `"🔥 Derby",` — il token `,"` viene interpretato come literal invalido. La riga corretta dovrebbe essere:

```python
text="🔥 Derby", font_size="12sp", color=(0.95, 0.4, 0.1, 1),
```

---

## 7. TODO / FIXME / HACK

**Risultato: ✅ NESSUNO TROVATO**

Nessun TODO, FIXME, HACK o XXX nel codice sorgente (src/ e mobile/).

---

## 8. Warning di Sistema

| Tipo | Quantità | Severità |
|------|----------|----------|
| PytestUnraisableExceptionWarning (SQLite unclosed connections) | 9 | Media |
| Kivy/pygame deprecation warnings | 3 | Bassa |
| pygame AVX2 performance warning | 1 | Bassa |

I warning SQLite indicano che alcune connessioni al database non vengono chiuse correttamente nei teardown dei test. Non bloccante ma andrebbe fixato per pulizia.

---

## 9. Problemi Trovati

### 🔴 CRITICO — SyntaxError in mobile/screens.py:238

- **Severità:** Bloccante per l'app mobile
- **Causa:** Virgola e virgolette extra in una stringa Kivy Label
- **Impatto:** `mobile.screens` non è importabile → `mobile.app` non è importabile → l'intera app Kivy non si avvia
- **Fix:** Rimuovere la virgola e virgolette extra (1 riga)

### 🟡 MEDIO — Warning SQLite unclosed connections (9 occorrenze)

- **Severità:** Non bloccante
- **Causa:** Connessioni SQLite non chiuse esplicitamente nei fixture/teardown
- **Impatto:** ResourceWarning durante i test, possibili leak in produzione
- **Fix:** Aggiungere `conn.close()` nei teardown o usare context manager

### 🟡 MEDIO — Copertura bassa moduli mobile

- `mobile/screens.py` — non testabile (SyntaxError)
- `mobile/widgets.py` — nessun test
- `mobile/app.py` — nessun test diretto
- `src/ui.py` — nessun test

---

## 10. Raccomandazioni

1. **FIX IMMEDIATO** — Correggere `mobile/screens.py:238`: rimuovere la virgola e virgolette extra. Una riga di fix.
2. **Aggiungere test di import** per `mobile.screens` e `mobile.app` dopo aver fixato il SyntaxError.
3. **Chiudere le connessioni SQLite** nei teardown dei test per eliminare i 9 warning.
4. **Aggiungere test per `mobile/widgets.py`** e `src/ui.py`.
5. **Considerare l'aggiunta di pytest-cov** per misurare la copertura delle righe in modo automatico.

---

## Sintesi

Il backend (`src/`) è solido: 203 test passano, nessun TODO, dati validi, moduli core compilano e importano correttamente. Il problema critico è un **SyntaxError su una singola riga** in `mobile/screens.py` che blocca l'intero frontend Kivy. Il fix è banale (rimuovere 2 caratteri) ma fino a quando non viene applicato, l'app non è avviabile.

| Categoria | Punteggio | Max |
|-----------|-----------|-----|
| Test suite (203/203 pass) | 30 | 30 |
| Copertura moduli | 15 | 20 |
| Integrità dati | 15 | 15 |
| Import check | 5 | 15 |
| Sintassi | 13 | 10 |
| Code hygiene (no TODO/FIXME) | 10 | 10 |
| **Totale** | **88** | **100** |

*(Nota: il punteggio import check è basso perché mobile.app + mobile.screens non importano. La sintassi ha bonus parziale perché 5/6 moduli sono OK.)*

---

**Verdetto finale: ❌ FAIL — 88/100**

Un singolo SyntaxError blocca il frontend. Fix da 1 riga per superare 90+.

---

*Tommy, QA Engineer*  
*2026-07-12*