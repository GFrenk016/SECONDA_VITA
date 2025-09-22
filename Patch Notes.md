
# Patch Notes

## Alpha 0.3
**Focus:** Primo sistema di combattimento ibrido (Telltale + roguelike) e fondamenta data‑driven per mob e armi.

### Nuovo Combat System (Fase 1)
- Combattimento contro singolo nemico con turni leggeri.
- QTE mirati (braccia, gamba, testa, busto) con effetti: riduzione danno, bonus danno, barcollamento (salta turno nemico), push (distanza).
- Comandi CLI: `spawn <enemy_id>`, `attack`, `qte <tasto>`, `push`, `flee`.
- Meccaniche distanza: `push` crea spazio, il nemico spende un turno per riavvicinarsi.
- `flee` con probabilità influenzata da distanza e HP nemico.

### Asset Data‑Driven
- Cartelle `assets/weapons/` e `assets/mobs/` con JSON caricati automaticamente.
- Arma iniziale: `knife.json` (coltello). Attributi base + crit placeholders.
- Mob base: `walker_basic.json` (Vagante) con pool QTE e loot placeholder.

### Stato e API
- Estesi campi `GameState` (HP giocatore, arma equip, sessione combat).
- Modulo `combat.py` con funzioni: `start_combat`, `resolve_combat_action`, `spawn_enemy`, `inject_content`.
- Wrapper azioni in `actions.py`: `engage`, `combat_action`, `spawn`.

### CLI
- Caricamento automatico di weapons & mobs all'avvio partita.
- Help esteso con i nuovi comandi di combattimento.

### Testing
- Test automatizzati aggiornati: casi QTE successo/fallimento, bonus damage, push, tentativi fuga.
- Rifiniture su test ambientali con meccanismo deterministico snippet.

### Esplorazione & Mondo (rafforzamenti inclusi in 0.3)
- Sistema multi‑livello `inspect` / `examine` / `search` con gating sequenziale e suggerimenti automatici.
- Marker oggetti (* / **) nelle liste di `look` per indicare livelli di ispezione disponibili.
- Evidenziazione “Nuovi elementi visibili” quando appaiono oggetti condizionali (es. notte, meteo) in una stanza già visitata.
- Uscite bloccate annotate con `(bloccata)` + legenda; sblocco tramite flag (`lock_flag`).
- Comando `where` per macro -> micro + tag stanza.
- Revisite area sintetiche con variante se cambia firma (fascia oraria o meteo) e meccanismo em dash.
- Linee ambientali contestuali con rate limiting e variante indoor attenuata per pioggia (`indoor_pioggia`).
- Oggetti condizionali per fasce orarie/meteo (es. visibilità notturna testata con glifo).
- Comando `wait until <fase>` per salto preciso alla fase (mattina/giorno/sera/notte) mantenendo coerenza meteo.

### Varie
- README aggiornato con sezione combat (fase 1) e documentazione QTE.
- Base pronta per: multi‑nemico, loot reale, stati negativi, spawn dinamici.

---

## Alpha 0.2
- Clock ora in realtime puro: 1 secondo reale = 1 minuto di gioco (mapping con offset e scala)
- Aggiornamento meteo ora valutato ogni 30 minuti simulati anche su salti (es. `wait`), evitando drift a cavallo della mezzanotte
- Nuovo comando `wait [min]` (default 10) per far scorrere il tempo senza muoversi
- Gestione avanzata descrizioni in revisita: varianti se cambia firma (daytime|weather)
- Linee ambientali contestuali non ripetitive estese al comando di attesa

## Alpha 0.1B
- Aggiunto sistema di meteo, clima e ora del giorno dinamici
- Oggetti e dettagli ambientali ora reagiscono a meteo e ora
- Tutti i testi (nomi, descrizioni, messaggi) sono centralizzati in `assets/strings.json`
- Migliorate e arricchite le descrizioni delle aree e degli oggetti

## Alpha 0.1 (Iniziale)
- Struttura progetto creata.
- Caricamento mondo “Bosco Antico” da JSON.
- Datamodel World/MacroRoom/MicroRoom/Exit modularizzato.
- Comandi base: `look`, `go`, `help`, `quit`.
- Sistema di registry e GameState iniziale.

- Aggiunta events.json + trigger on_enter.
- Implementazione ActionResult esteso (events_triggered, changes).
- Persistenza salvataggi (save/load/list).

- Comando `inspect`.
- Proximity hints narrativi dinamici.
- Timeline log + comando `history`.

- Sistema choices ramificato.
- Effetti avanzati (unlock_exit, custom callbacks).
- Migrazione schema salvataggi (versionamento).
