
# Patch Notes

## Alpha 0.1C
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
