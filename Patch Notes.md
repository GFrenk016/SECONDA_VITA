# Patch Notes

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
