# Seconda Vita

Motore narrativo testuale (single‑player) post‑apocalittico. Il giocatore interpreta Frank esplorando un mondo gerarchico (World → MacroRooms → MicroRooms), osserva, compie scelte e avanza con stato persistente.

## Stato attuale (Vertical Slice Iniziale)
- Caricamento mondo da JSON (`assets/world/world.json`) – ambientazione: Bosco Antico.
- Comandi base: `look`, `go <direzione>`, `help`, `quit`.
- Navigazione tra micro stanze con uscite direzionate.
- Architettura modulare pronta per eventi, salvataggi, inspect, inventario.

## Struttura Progetto (parziale)
```
engine/
  core/
    model/            # dataclass di base (World, MacroRoom, MicroRoom, Exit, ecc.)
    state.py          # GameState runtime
    registry.py       # Indici globali (rooms, items, events)
    actions.py        # API high-level (look, go, ecc.)
    loader/
      world_loader.py # Parsing e validazione world.json
game/
  bootstrap.py        # Costruzione mondo + creazione GameState
assets/
  world/world.json    # Definizione gerarchica Bosco
data/
  saves/              # (vuoto) Salvataggi futuri
run.py                # Entry point CLI
```

## Esecuzione Locale
Prerequisito: Python 3.11+ (consigliato).

```
python run.py
```

Esempio:
```
> help
> look
> go n
> look
> go w
```

## Estensioni Pianificate
| Fase | Feature | Note |
|------|---------|------|
| 1 | Eventi on_enter | events.json + trigger/effects |
| 1 | Salvataggi | snapshot JSON versione + slot nominati |
| 2 | inspect <id> | Interazione con oggetti e indizi |
| 2 | Proximity hints avanzati | Frasi ambientali dinamiche |
| 2 | Timeline log | Traccia eventi chiave |
| 3 | Scelte ramificate | apply_choice(), flag consequenziali |
| 3 | Sistema condizioni | lock/unlock uscite, gating narrativo |
| 3 | Migrazioni state | Gestione version upgrade |

## Design Principi Chiave
- Data‑driven: contenuti in JSON, engine generico.
- Azioni pure: ogni comando restituisce un `ActionResult` serializzabile.
- Eventi idempotenti: flag in `fired_events` per prevenire duplicazioni.
- Separazione I/O: facile sostituire CLI con web / UI futura.

## Lavorare da iPhone
Opzione rapida:
1. Pubblica repo su GitHub.
2. Apri con Codespaces (browser o app GitHub).
3. Esegui `python run.py` nel terminale integrato.
4. Modifica JSON / codice, commit, test live.

## Convenzioni Direzioni
`n, s, e, w, ne, nw, se, sw, up, down` (attualmente usiamo le cardinali base).

## Contributi
- Aggiungi nuove micro stanze modificando `assets/world/world.json`.
- Mantieni ID stabili (evita di riutilizzare un ID per una stanza diversa).

## Prossimi Passi Consigliati
1. Introdurre `events.json` + loader.
2. Implementare pipeline `on_enter`.
3. Aggiungere `persistence.py` (save/load).
4. Coprire `look` e `go` con test di regressione.

## Licenza
Da definire (consigliato: MIT o Apache 2.0).
