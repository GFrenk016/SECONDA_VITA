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
- Sistema di combattimento ibrido realtime (fase 2.1): timer nemici + QTE (difesa/offesa) con pressione temporale. Supporto multi‑nemico, attacco ad area, focus.

Suggerimenti rapidi combattimento:
- Armi da fuoco: `attack aimed` / `attack snap`, `reload` per ricaricare. Lo stato mostra le munizioni.
- Armi da lancio: `throw` (o `throw 2`) consuma 1 uso e infligge danno con splash (in base ad `aoe_factor`). Lo stato mostra `Usi`.
- Armi pesanti: gli attacchi possono fendere più bersagli se l'arma definisce `cleave_targets` (>0); danno ai bersagli extra scalato da `cleave_factor`.

## Comandi base
- `look` — osserva l'ambiente attuale
- `go <direzione>` — muoviti nella direzione indicata
- `wait [min]` — fai passare il tempo senza muoverti (default 10 minuti se omesso). Aggiorna orario, potenzialmente meteo e linea ambientale.
- `wait until <fase>` — salta alla prossima occorrenza della fase (`mattina`, `giorno`, `sera`, `notte`)
- `status` / `time` — riepilogo stato temporale e ambientale attuale
- `inspect <oggetto>` — ispeziona un oggetto/elemento presente nell'area
- `quit` — esci dal gioco

### Inventario e Statistiche
- `inventory` / `inv` — mostra inventario con peso, categorie e oggetti equipaggiati
- `stats` — mostra statistiche giocatore, attributi, resistenze e buff attivi
- `use <oggetto>` — usa un oggetto consumabile dall'inventario
- `equip <oggetto>` — equipaggia un oggetto dall'inventario
- `unequip <slot|oggetto>` — rimuove oggetto equipaggiato
- `drop <oggetto> [quantità]` — lascia cadere oggetti dall'inventario
- `examine <oggetto>` — esamina oggetto in dettaglio (inventario o mondo)

### Combattimento (fase 2.1 – realtime ibrido)
Nuovo modello realtime: niente più fase 'enemy'. Il tempo simulato scorre (derivato dal clock globale) e il nemico prepara attacchi a intervalli programmati. Quando un attacco sta per arrivare:
1. Viene schedulato un "incoming attack" con `next_enemy_attack_total`.
2. Allo scadere del timer si apre un QTE difensivo (fase `qte`, type `defense`) con finestra `defensive_qte_window` minuti simulati.
3. Se il giocatore preme il tasto corretto (`qte <tasto>`), l'attacco è annullato e il timer successivo viene posticipato.
4. Se fallisce (input errato o scadenza), il danno viene applicato e si riparte il ciclo.

Gli attacchi del giocatore possono innescare un QTE offensivo (type `offense`) immediatamente dopo l'azione (`qte_chance`). In quel caso il tempo nemico è temporaneamente sospeso finché il QTE non viene risolto (successo/fallimento/timeout). Nessun turno nemico dedicato: la pressione deriva dai timer.

Novità QTE avanzati:
- QTE complessi alfanumerici (3–5 caratteri) sia in Offense che in Defense. Da CLI puoi digitare direttamente il codice mostrato (anche senza anteporre `qte`).
- QTE legacy (singolo tasto) ancora disponibili se disabiliti la modalità complessa via config.

Fasi valide:
- `player`
- `qte` (offense/defense via `session.qte['type']`)
- `ended`

Parametri per nemico (JSON):
- `attack_interval_minutes`: intervallo base attacchi.
- `attack_interval_multiplier`: scala l'intervallo (es. 0.5 = più frequente).
- `defensive_qte_window`: finestra di reazione difensiva.
- `attack_damage_multiplier`: scala il danno base `attack`.
- `qte_chance`: probabilità di QTE offensivo dopo un tuo attacco riuscito.
- `qte_prompts`: pool di prompt offensivi (bonus, riduzioni danno, ecc.).

Determinismo per i test: invocare `set_combat_seed(seed)` prima di avviare o durante una sessione per rendere riproducibili i QTE (scelte random e chance). 

Auto‑tick CLI: il prompt avvia un thread di background che richiama periodicamente `tick_combat`, così gli attacchi/QTE appaiono anche mentre sei inattivo al prompt.

Logging eventi: ogni evento combat è aggiunto a `state.timeline` con campi `type='combat'`, `event`, `total_minutes`, payload (es: `player_attack`, `qte_offense_success`, `qte_defense_fail`, `combat_started`, `combat_ended`).

**Comandi CLI disponibili:**
- `spawn <enemy_id>`: genera un nemico (debug/manuale per ora) e avvia il combattimento.
- `attack`: attacca con l'arma equip (usa resolver con stamina/postura). Può attivare un QTE offensivo.
- `qte <tasto>`: risponde a un prompt QTE (offense o defense). Durante un QTE puoi anche digitare direttamente il codice senza il prefisso.
- `push`: guadagni distanza ritardando l'attacco nemico; il nemico consuma tempo per riavvicinarsi.
- `flee`: tenta la fuga (probabilità: 30% base +30% se distanza>0 +20% se HP nemico ≤40%). Fallimento anticipa il prossimo attacco.
- (interno) `engage(...)` / `combat_action(...)` per script/test.

**QTE mirati offensivi:** (dal pool definito nel mob JSON)
- braccia → `reduce_next_damage`: riduce l'attacco del nemico (-1 cumulativo minimo 0)
- gamba → `stagger`: salta subito al tuo turno (il nemico perde l'attacco)
- testa → `bonus_damage`: infligge danno bonus immediato pari almeno al danno arma
- busto → `push`: aggiunge distanza (sinergia con `flee`)

QTE Difensivo: appare quando l'attacco nemico entra in finestra. Successo = annulla danno e resetta timer; fallimento = applichi danno e riparte il ciclo.

Timeout QTE Offensivo: se scade la finestra, perdi il bonus e il timer nemico continua normalmente (leggera penalità: attacco prossimo anticipato di 1 minuto simulato).

**Distanza:**
`push` aumenta la distanza. Finché distanza > 0, il nemico deve prima riavvicinarsi (nessun danno quel giro). La distanza decresce quando il nemico avanza.

**Fuga:** probabilità base 30%, +30% se distanza > 0, +20% se HP nemico ≤ 40% del massimo. Fallimento: il prossimo attacco può triggerare prima (timer portato all'istante corrente).

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

**Estensioni previste:** multi‑nemico simultaneo, effetti di stato (sanguinamento, infezione), loot effettivo, progressione armi, spawn dinamici ambientali, posture break reaction cinematica.

### Patch Notes (estratto rapido Phase 2.1)
- Rimozione fase 'enemy', loop totalmente event/time‑driven
- Aggiunti parametri difficoltà (danno e intervallo) per mob
- QTE separati offense/defense con gestione distinta deadline
- Logging strutturato eventi combattimento in `state.timeline`
- Funzione `set_combat_seed` per RNG deterministico testabile
- Refactor code path e cleanup funzioni legacy `_enemy_attack`, `_maybe_trigger_qte`

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

## Configurazione (config.py + variabili d'ambiente)
Molti parametri del combat/CLI sono ora centralizzati in `config.py` e sovrascrivibili via env:
- SV_COMPLEX_QTE: abilita i QTE alfanumerici complessi nel CLI.
- SV_QTE_LEN_MIN / SV_QTE_LEN_MAX: lunghezze min/max dei codici QTE.
- SV_QTE_ALPHABET: alfabeto per i QTE (default A‑Z + 0‑9).
- SV_QTE_DEF_WINDOW_MIN / SV_QTE_OFF_WINDOW_MIN: finestre QTE difensiva/offensiva (in minuti simulati).
- SV_INACTIVITY_SEC: secondi reali di inattività prima di forzare un attacco/QTE.
- SV_ATTACK_ALL_COOLDOWN_MIN: cooldown minimo per `attack all` (minuti simulati).
- SV_TICK_INTERVAL_SEC: intervallo di tick del thread CLI.

Esempi:
```
export SV_COMPLEX_QTE=true
export SV_QTE_LEN_MIN=4
export SV_QTE_LEN_MAX=4
export SV_QTE_ALPHABET=0123456789
export SV_QTE_DEF_WINDOW_MIN=1
export SV_INACTIVITY_SEC=2
export SV_TICK_INTERVAL_SEC=0.1
python run.py
```

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
