game/
data/
# Seconda Vita

Seconda Vita è un motore narrativo testuale ambientato in un bosco, con profondità narrativa e ambiente dinamico.

## Funzionalità principali
- Esplorazione di aree con descrizioni immersive e dettagli sensoriali
- Oggetti interattivi e dettagli ambientali che cambiano in base a meteo, clima e ora del giorno
- Clock realtime puro: 1 secondo reale = 1 minuto di gioco (scalabile) con fasce orarie dinamiche
- Sistema meteo/clima probabilistico rivalutato ogni 30 minuti simulati (anche durante `wait`)
- Memoria visite: prima visita descrizione completa, revisite sintetiche, varianti se cambia (fascia oraria | meteo)
- Linee ambientali contestuali non ripetitive per arricchire l'atmosfera
- Comando `wait` per far scorrere il tempo senza muoversi
- Tutti i testi (nomi, descrizioni, messaggi) sono centralizzati in `assets/strings.json` per una facile localizzazione e modifica

## Comandi base
- `look` — osserva l'ambiente attuale
- `go <direzione>` — muoviti nella direzione indicata
- `wait [min]` — fai passare il tempo senza muoverti (default 10 minuti se omesso). Aggiorna orario, potenzialmente meteo e linea ambientale.
- `wait until <fase>` — salta alla prossima occorrenza della fase (`mattina`, `giorno`, `sera`, `notte`)
- `status` / `time` — riepilogo stato temporale e ambientale attuale
- `quit` — esci dal gioco

## Struttura Progetto
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
  strings.json        # Tutti i testi narrativi e i nomi
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
> wait 45
> look
```

## Tempo, Fasce Orarie e Meteo
Il gioco usa un clock realtime: 1 secondo reale = 1 minuto simulato (configurabile via `time_scale`).

Fasce orarie:
- 06:00–11:59 → mattina
- 12:00–17:59 → giorno
- 18:00–21:59 → sera
- 22:00–05:59 → notte

Il meteo viene rivalutato ogni 30 minuti simulati (30 secondi reali a scala default). Il comando `wait` avanza l'offset temporale, applicando tutte le rivalutazioni necessarie in blocco. Alcune condizioni (pioggia persistente) possono lentamente mutare il clima.

Memoria delle visite:
- Prima visita: descrizione completa + varianti ambientali.
- Revisita senza cambi: solo il nome dell'area.
- Revisita dopo cambio (fascia oraria o meteo): descrizione sintetica evidenziando la variazione.

Linee ambientali: frasi contestuali non ripetute consecutivamente, estratte da set dipendenti da fascia oraria e meteo.

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
- Realtime mapping: lo stato temporale è derivato (idempotente) da tempo reale + offset, evitando drift e semplificando salvataggi.

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
