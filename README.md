game/
data/
# Seconda Vita

Seconda Vita è un motore narrativo testuale ambientato in un bosco, con profondità narrativa e ambiente dinamico.

## Funzionalità principali
- Esplorazione di aree con descrizioni immersive e dettagli sensoriali
- Oggetti interattivi e dettagli ambientali che cambiano in base a meteo, clima e ora del giorno
- Clock realtime puro: default rallentato (0.25) => 1 secondo reale = 0.25 minuti di gioco (~96 minuti reali per un giorno intero) configurabile via variabile d'ambiente (niente più comando runtime)
- Sistema meteo/clima probabilistico rivalutato ogni 30 minuti simulati (anche durante `wait`)
- Memoria visite: prima visita descrizione completa, revisite sintetiche, varianti se cambia (fascia oraria | meteo)
- Linee ambientali contestuali non ripetitive per arricchire l'atmosfera
- Comando `wait` per far scorrere il tempo senza muoversi
- Tutti i testi (nomi, descrizioni, messaggi) sono centralizzati in `assets/strings.json` per una facile localizzazione e modifica
- Sistema di combattimento minimale ibrido (fase 1): turno giocatore / QTE in stile Telltale per schivare attacchi di un singolo nemico

## Comandi base
- `look` — osserva l'ambiente attuale
- `go <direzione>` — muoviti nella direzione indicata
- `wait [min]` — fai passare il tempo senza muoverti (default 10 minuti se omesso). Aggiorna orario, potenzialmente meteo e linea ambientale.
- `wait until <fase>` — salta alla prossima occorrenza della fase (`mattina`, `giorno`, `sera`, `notte`)
- `status` / `time` — riepilogo stato temporale e ambientale attuale
- `inspect <oggetto>` — ispeziona un oggetto/elemento presente nell'area
- `quit` — esci dal gioco

### Combattimento (fase 1)
Sistema ibrido: turno semplice + QTE stile Telltale.

**Comandi CLI disponibili:**
- `spawn <enemy_id>`: genera un nemico (debug/manuale per ora) e avvia il combattimento.
- `attack`: attacca con l'arma equip (base 1 danno; `knife` 3 danni).
- `qte <tasto>`: risponde a un prompt QTE (lettera indicata nel messaggio).
- `push`: spingi il nemico per guadagnare distanza (il nemico spende il prossimo turno per avvicinarsi se possibile).
- `flee`: tenta la fuga (chance aumentata se distanza > 0 o nemico ferito).
- (interno) `engage(...)` / `combat_action(...)` per script/test.

**QTE mirati ed Effetti:** (dal pool definito nel mob JSON)
- braccia → `reduce_next_damage`: riduce l'attacco del nemico (-1 cumulativo minimo 0)
- gamba → `stagger`: salta subito al tuo turno (il nemico perde l'attacco)
- testa → `bonus_damage`: infligge danno bonus immediato pari almeno al danno arma
- busto → `push`: aggiunge distanza (sinergia con `flee`)

Se fallisci (input errato o tempo scaduto) subisci l'attacco. Se riesci, l'effetto si applica e torni (o resti) al tuo turno.

**Distanza:**
`push` aumenta la distanza. Finché distanza > 0, il nemico deve prima riavvicinarsi (nessun danno quel giro). La distanza decresce quando il nemico avanza.

**Fuga:**
Probabilità base 30%, +30% se distanza > 0, +20% se HP nemico ≤ 40% del massimo.

**Asset Combat Data‑Driven:**
- `assets/weapons/knife.json` – definisce il coltello.
- `assets/mobs/walker_basic.json` – definisce un Vagante con pool QTE e loot placeholder.

**Esempio ridotto definizione mob:**
```
{
  "id": "walker_basic",
  "name": "Vagante",
  "hp": 8,
  "attack": 2,
  "qte_chance": 0.6,
  "qte_window_minutes": 2,
  "qte_prompts": [
    {"part": "testa", "prompt": "Colpisci la testa! (T)", "expected": "t", "effect": "bonus_damage"}
  ]
}
```

**Estensioni previste:** multi‑nemico, stati (sanguinamento, infezione), loot effettivo, progressione armi, spawn dinamici ambientali.

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
Il gioco usa un clock realtime: per default 1 secondo reale = 0.25 minuti simulati (quindi una giornata di 24h dura ~96 minuti reali).

Per modificare la velocità del tempo imposta prima di avviare: `SV_TIME_SCALE=0.5` (ecc.). Il valore rappresenta minuti di gioco che avanzano ogni secondo reale.

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
| 2 | inspect <id> | Interazione con oggetti e indizi (parzialmente implementato) |
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

## Test Automatizzati (pytest)

È stato aggiunto un setup minimale di test automatici con `pytest`.

File principali:
- `tests/test_core.py` – copre:
  - comando `where` (presenza linee Posizione/Tag)
  - gating multi‑livello `inspect`/`examine`/`search` (errori se ordine errato)
  - formato linea `Uscite:` (verifica presenza base; mock parziale per uscite bloccate)
  - rate limiting delle linee ambientali (nessun incremento immediato, ritorno dopo gap)
- `pytest.ini` – configurazione base (ricerca `test_*.py`, esecuzione quiet `-q`).

Esecuzione test (da root progetto):
```
pytest
```
Oppure con output dettagliato:
```
pytest -vv
```

Nota: alcuni aspetti (es. exit realmente bloccata) richiederebbero costruzione di un mondo di test dedicato; il test attuale verifica il formato minimo senza mutare il dataclass immutabile. Per test più profondi si può introdurre un world fixture ridotto.

Prossimi ampliamenti test suggeriti:
- Snapshot test di `look()` in condizioni (mattina/notte, meteo diverso) con finto seeding RNG.
- Test di visibilità condizionata (oggetti `is_night`, ecc.).
- Test per suggerimenti di livello successivo (linee "Possibile: examine/search").

## Licenza
Da definire (consigliato: MIT o Apache 2.0).
