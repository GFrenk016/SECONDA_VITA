# Seconda Vita – Mini (senza venv)

Avvio:
- Doppio click su `start_game.bat`, oppure:
  ```bash
  python main.py

Comandi (in inglese):
help
look
go <north|south|east|west>
take <item>
inventory
talk <name> # placeholder per futuri dialoghi
exit | quit

Note:
Narrazione: ITA
Comandi & dialoghi: ENG

# Schema Progetto

👤 User

[X] Inserisce input (console, ENG)

[X] Riceve output (narrativa ITA + dialoghi/risposte ENG)

🗝 Parser

[X] Split comando + argomenti (go north, take knife)

[X] Alias supportati (inv, bag, l)

[] Riconoscimento errori avanzati (es. suggerire comandi simili)

🔀 Command Router

[X] Registry dei comandi (REGISTRY)

[X] Dispatch corretto funzione → comando

[] Priorità/stack comandi multipli (macro, alias complessi)

⚙️ Engine

[X] Game loop (input → parse → exec → autosave)

[X] Tick system (ogni azione = +1 tick)

[X] Effetto Fatica: -1 Energy per tick

[X] Menu iniziale (Continue: load/delete; New Game: saveN)

[X] Ritorno al menu con comando menu

[X] Game Over → menu

[] Validators (clamp globale stats, limiti inventario, ecc.)

💾 State

[X] Player → inventario

[X] Player → stats (health, energy, morale)

[X] Locations → con exits + items

[X] Flags → per eventi (vento, ecc.)

[X] Director (gestione eventi dinamici / spawn walker)

[] Relationships (Clem, AJ, Louis…)

[] Log/Memory delle azioni

🗡 Modules agganciati allo State

[X] Combat (spawn walker + comando attack)

[X] Events (random atmosferici o incontri)

[X] Narrative Director (orchestrazione per tick)

[X] Memory/Journal (recap azioni, indizi raccolti)

🎨 Renderer

[x] Output in ITA per narrativa

[x] Output ENG per comandi e dialoghi

[] Colori/evidenziazione (health rosso basso, morale blu, ecc.)

[] Output formattato a più righe stile “log”

📦 Assets

[x] Banner ASCII

[x] Oggetti base: coltello, foto

[] Database/JSON per oggetti estesi (cibo, armi, risorse)

🌲 World

[x] 2 location di base (Foresta, Casa abbandonata)

[] Mappa ampliata (New Richmond, Ericson, ecc.)

[] Zone pericolose con spawn speciali

💽 Salvataggi (dal menù)

[X] New Game auto-slot (save1, save2, …)

[X] Continue: lista, Load/Delete

[X] In-game: save, save +, save <name>, menu

[X] Sessioni isolate (journal/stats separati per slot)

[] Autosave