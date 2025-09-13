
# Text Adventure Engine — Strutturato

Avvio rapido (Windows):
1. Installa Python 3.10+.
2. Doppio click su `start_game.bat` **oppure**:

 ```bash
python main.py
 ```
 
Opzioni:
python main.py --save autosave --debug
- `--save <nome>`: forza il nome dello slot di salvataggio
- `--debug`: stampa info aggiuntive su caricamento, comandi e scene
Struttura: - engine/ : motore - game/ : contenuti del gioco (stanze, descrizioni, scripting) - assets/ :
risorse testuali (banner, ecc.) - data/saves/ : salvataggi JSON
Personalizzazione: - Modifica/aggiungi stanze in game/scenes.py - Registra nuovi comandi in
engine/commands.py - Aggiungi trigger/condizioni in game/scripting.py