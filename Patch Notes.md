
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

### Varie
- README aggiornato con sezione combat (fase 1) e documentazione QTE.
- Base pronta per: multi‑nemico, loot reale, stati negativi, spawn dinamici.

---

## 0.2.0 (2025-09-24)
Focus: Realtime Combat Fase 2.1, armi ranged/throwable/heavy, tutorial, fix rounding danni, refactor assets armi

Novità
- Realtime combat 2.1: niente fase enemy; attacchi nemici a timer con QTE difensivi; QTE offensivi post-azione.
- Integrazione armi da fuoco: `attack aimed` / `attack snap`, munizioni con `ammo_in_clip/clip_size/ammo_reserve`, `reload`.
- Armi da lancio: comando `throw`, consumi `uses`, splash damage con `aoe_factor`, HUD “Usi”.
- Armi pesanti: cleave su bersagli aggiuntivi con `cleave_targets` e `cleave_factor`.
- Effetti di stato per-mossa ripristinati; supporto a `status_effects` a livello arma; sinonimi comuni mappati (es. stun→concussed).
- Loader contenuti: supporto a file per categoria in `assets/weapons/` (melee/ranged/heavy/throwable) e merge flessibile.
- Tutorial completo accessibile dal menu principale.
- Fix coerenza arrotondamenti danni (mostrato = applicato, anche per DoT/AoE).

Varie
- README aggiornato con suggerimenti rapidi per ranged/throwable/heavy.
- Telemetria eventi combattimento estesa: `player_attack`, `area_attack`, `throw`, `throw_splash`, `heavy_cleave`, `status_tick`, ecc.

Compatibilità
- I test esistenti restano verdi; comportamento legacy preservato quando i campi nuovi non sono presenti.

## 0.2.1 (2025-09-24)
Focus: Sistema NPC con dialoghi, integrazione opzionale Ollama, miglioramenti qualità

Novità
- Sistema NPC data‑driven: loader `assets/npcs/*.json`, registry runtime (posizioni, schedule), comandi `talk`/`say`.
- Dialoghi AI opzionali con Ollama (locale): attivabili via env; fallback automatico a risposte statiche se non disponibile.
- Mapping schedule in italiano→stati NPC (busy/sleeping), mood tracking e memorie conversazioni.

Configurazione
- Nuove variabili in `config.py`:
	- `SV_OLLAMA_ENABLED`, `SV_OLLAMA_BASE_URL`, `SV_OLLAMA_MODEL`, `SV_OLLAMA_TIMEOUT`, `SV_OLLAMA_TEMPERATURE`, `SV_OLLAMA_MAX_TOKENS`.

Documentazione
- README: sezione “Dialoghi NPC con Ollama (opzionale)” con istruzioni Windows e variabili d’ambiente.

Compatibilità
- Nessuna rottura: se Ollama è disabilitato o non raggiungibile, i dialoghi usano risposte predefinite.

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
