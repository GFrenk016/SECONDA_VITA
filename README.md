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

## ✅ Stato attuale del progetto (alpha 0.3 base)

### 🔹 Struttura generale

* **`engine/`**

  * `core.py` → gestisce bootstrap, loop, normalizzazione chiavi, ritorno al menù.
  * `commands.py` → registro comandi (`look`, `go`, `take`, `inventory`, `stats`, `talk`, `journal`, `attack`, `where`, `save`, `menu`).
  * `state.py` → definisce `Player`, `Location`, `GameState`.
  * altri moduli: `persistence`, `combat`, `journal`, ecc.
* **`game/`**

  * `scenes.py` → carica i mondi JSON, genera celle, landmark, portali, ostacoli.
  * `scripting.py` → eventi narrativi all’avvio / per tick.
* **`assets/world/`**

  * `overworld.json`, `house.json` → definiscono mappa griglia 2D, landmark, porte, ecc.

---

### 🔹 Movimento

* Ora usiamo una **griglia 2D (X,Z)** con `CELL_SIZE_METERS` = 2m.
* Comando:

  ```bash
  go east 10
  ```

  → ti sposti di 10 celle (\~20m), fermandoti se incontri ostacoli o bordi.
* Niente “volare” con `up/down`: movimento verticale solo se c’è una scala/porta definita in JSON.

---

### 🔹 JSON del mondo

* Ogni mondo (`overworld`, `house`, ecc.) è descritto da JSON:

  * `meta`: dimensioni, spawn point.
  * `landmarks`: zone (Foresta Infinita, Radura, Casa Facciata, Atrio…).
  * `doors`: coppie inside/outside per i portali tra mondi.
  * `obstacles`: muri/blocchi rettangolari.
* Puoi ingrandire le zone modificando solo i `bbox` senza toccare codice.

---

### 🔹 Portali e landmark

* Se sei **sopra** a un portale: `look` mostra
  👉 *"Qui c'è un ingresso per Casa Abbandonata (enter)"*.
* Se sei **vicino** (cella adiacente): `look` mostra
  👉 *"Intravedi un ingresso: east → Casa Abbandonata"*.
* Se sei **al confine** tra due landmark: `look` mostra
  👉 *"A confine di zona: north → Radura Luminosa"*.

---

### 🔹 Hint per l’Atrio

* Dentro la mappa `house`, ogni `look` ti dice anche **come arrivare all’Atrio** (se non ci sei già):
  👉 *"Per raggiungere Casa — Interno (Atrio): east 2, north 1 (\~3 passi)"*.

---

### 🔹 Salvataggi & menù

* Non c’è più autosave automatico.
* Comandi:

  * `save` / `save +` → crea/aggiorna slot.
  * `menu` → ritorna al menù principale.
* `main.py` gestisce **New Game**, **Continue** (scegli salvataggio), **Delete Save**.

---

### 🔹 Journal

* Registra eventi principali (`go`, `take`, `save`, ecc.).
* Comando `journal` → stampa cronologia della sessione.

---

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
     "migliorato"

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

[X] Mappa 2D + Landmarks

[] Zone pericolose con spawn speciali

💽 Salvataggi (dal menù)

[X] New Game auto-slot (save1, save2, …)

[X] Continue: lista, Load/Delete

[X] In-game: save, save +, save <name>, menu

[X] Sessioni isolate (journal/stats separati per slot)

[] Autosave

# Struttura progetto

├── README.md
├── start_game.bat
├── config.py
├── main.py
├── engine
|   ├── combat.py
│   ├── core.py
│   ├── commands.py
|   ├── events.py
│   ├── state.py
│   ├── persistence.py
│   ├── io.py
│   ├── journal.py
│   ├── plugins.py
│   └── __init__.py
├── game
│   ├── scenes.py
│   ├── scripting.py
│   ├── director.py
│   └── __init__.py
├── data
|   ├── saves
└── assets
    ├── world
    │   ├── overworld.json
    │   └── house.json
    └── banner.txt