
# Patch Notes
## Alpha 0.4 (Phase 2.1 Realtime Combat Evolution)
**Focus:** Rimozione residui turn-based e integrazione pressione temporale legata a clock reale.

### Novità
- Combattimento ora ticka automaticamente ogni ciclo di input: gli attacchi nemici emergono senza turno esplicito.
- Inattività punita: se il giocatore resta ~3 secondi reali senza eseguire un'azione valida in combattimento, il timer del prossimo attacco nemico viene forzato a "adesso" generando immediatamente un QTE difensivo (o facendo atterrare un attacco già caricato alla scadenza della sua finestra).
- Tracciato `last_player_action_real` nella sessione combat e parametro `inactivity_attack_seconds` (default 3).
- Loop CLI aggiorna il clock simulato ad ogni iterazione prima dell'input e processa `tick_combat` (eventi possono apparire prima che l'utente scriva qualcosa).
- Documentata la relazione: 1s reale = 1 minuto simulato (scala variabile tramite `time_scale`) e come l'inattività sfrutti direttamente il tempo reale.

### Aggiornamenti recenti (23-09-2025)
- QTE complessi alfanumerici (3–5 caratteri) per Offense e Defense: abilitabili via config; nel CLI sono abilitati di default. Il giocatore può digitare direttamente il codice mostrato (non è più obbligatorio `qte <tasto>`).
- Auto-tick in background nel CLI: un thread daemon chiama periodicamente `tick_combat` così gli eventi compaiono anche mentre il prompt è in attesa (pressione costante anche senza input).
- Anti-spam QTE difensivo: i messaggi "<nemico> prepara un attacco!" e il prompt "Difesa!" vengono emessi una sola volta per finestra; il prossimo `next_attack_total` del nemico viene ripianificato quando entra in stato "incoming".
- Inattività migliorata: su inattività forzata aggiorniamo i timer per ogni nemico vivo (`next_attack_total`), non solo l'alias legacy; questo garantisce QTE immediato coerente in multi‑nemico.
- Config centralizzata (`config.py`) con override via variabili d'ambiente (es. `SV_COMPLEX_QTE`, `SV_QTE_LEN_MIN/MAX`, `SV_QTE_ALPHABET`, `SV_QTE_DEF_WINDOW_MIN`, `SV_QTE_OFF_WINDOW_MIN`, `SV_INACTIVITY_SEC`, `SV_TICK_INTERVAL_SEC`, `SV_ATTACK_ALL_COOLDOWN_MIN`).

### Motivazione
Rendere percepibile urgenza: il giocatore non può "pensare all'infinito"; il sistema avanza e reagisce.

### Prossimi step possibili
- (completato) Auto‑ticking in thread separato per pressione anche durante digitazione lenta.
- Scala dinamica del timeout inattività in base a difficoltà o stato del nemico.
- Penalità aggiuntive (es: micro posture drain) oltre all'accelerazione attacco.

### Aggiornamento (Multi‑Nemico & Spawn Dinamico)
- Introdotta struttura interna per gestire una lista di nemici contemporanei (`session['enemies']`).
- Nuovo comando `spawn <enemy_id> [count]` che:
	- Se non sei in combattimento avvia il combattimento con il primo nemico (come prima).
	- Se sei già in combattimento aggiunge 1 o più nuovi nemici alla battaglia (count opzionale, default 1).
	- Gestione automatica di suffissi univoci per ID e nome: `walker_basic`, `walker_basic_2`, `walker_basic_3`, ecc.
- Comando `attack` ora supporta indice: `attack 2` colpisce il secondo nemico vivo (fallback sul primo vivo se indice mancante o non valido).
- `status` mostra elenco sintetico di tutti i nemici con HP.
- QTE difensivi associati a un nemico specifico (`enemy_index`), mantenendo compatibilità con i campi legacy per i test esistenti.
- Attaccare durante un QTE difensivo conta come errore: l'attacco in arrivo colpisce immediatamente (danno punitivo) e il QTE viene chiuso.
- Parata riuscita aggiorna correttamente il timer di attacco del nemico specifico, evitando retrigger immediato.
 - Jitter iniziale sugli attacchi dei nuovi nemici: ogni nemico spawnato riceve un offset casuale al suo primo `next_attack_total` per desincronizzare le finestre difensive.
 - Comando `focus <index>`: consente di fissare un bersaglio prioritario. Gli `attack` senza indice usano automaticamente il bersaglio focalizzato se vivo (indicatori `F` nello status).
 - Comando `attack all`: attacco ad area che colpisce tutti i nemici vivi con il 50% del danno (scalabile in futuro). Produce evento `area_attack` con elenco dei bersagli e danni.
 - Output `status` multi‑linea: ogni nemico elencato su riga dedicata con flag:
	 - `F` bersaglio focus
	 - `I:xm` attacco in arrivo e minuti residui
	 - `X` nemico sconfitto
 - Eventi arricchiti con `enemy_index` per correlare log e timeline.
 - Penalità coerente per ignorare QTE difensivo (impatto immediato + chiusura finestra) anche in presenza di più nemici.
 - Attack All avanzato: danno percentuale scala leggermente col numero di bersagli, costo stamina extra per ogni nemico oltre il primo e cooldown dinamico basato sugli intervalli medi di attacco nemici.
 - Cooldown attack all: impedisce spam, messaggio se usato prima della ricarica.
 - Auto-switch focus: se il nemico focalizzato muore il focus passa automaticamente al prossimo vivo (evento `focus_auto_switch`).
 - RNG deterministico esteso: `set_combat_seed` ora propaga al resolver per rendere riproducibili gli esiti (hit/miss) nei test futuri.

### Note Tecniche
- Introdotto helper `_sync_primary_alias` per mantenere allineati i campi legacy (`enemy_hp`, `incoming_attack_deadline`, ecc.).
- Estratto `_create_enemy_entry` per riuso tra avvio combat e spawn aggiuntivi.
- Struttura pronta per futuri miglioramenti: AI multi-target, priorità bersagli, effetti ad area.
 - Introduzione evento `focus_set` e `area_attack` per telemetria tattica.

---

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
