#  Patch Notes - Versione Alpha 0.4A

🌍 World & Movement

[✔] POI detection: se sei vicino a un landmark (<40m) viene segnalato.

[✔] Energy drain: muovendoti consumi energia proporzionale ai metri.

[✔] Fix: se sei già dentro un POI, non mostra più il messaggio “Senti la presenza di …”.

🧭 Commands

[✔] go migliorato:

correzione bug su world non definito.

mostra ostacoli vicini (con nome).

[✔] scan sostituisce look: rivela POI e items vicini entro raggio, con nomi umani.

[✔] take ora mostra il nome leggibile (“Coltello” invece di “knife”).

[✔] where rifinito: trova landmark più vicino con direzione e stima passi.

🗃 Assets & Data

[✔] Creata struttura in assets/ per:

weapons/ → JSON con armi melee (es. knife, baseball bat).

mobs/ → JSON con mob base (walker/vagante).

[✔] Mappe (overworld.json) ora possono spawnare items collegati a weapon JSON.

⚔️ Combat System (base)

[✔] Comandi: attack, push, flee, spawn.

[✔] Banner “COMBAT” all’ingresso.

[✔] Equip system: puoi equip <arma> per usarla negli attacchi.

[✔] Regole arma:

Coltello = one-shot kill.

Pugni = non uccidono, walker resta a 1 HP.

Armi hanno durabilità, energy_cost, crit chance.

[✔] QTE system (Telltale-like):

walker attacca dopo un intervallo (combat_attack_interval_s).

quando ti afferra → appare sequenza da digitare: qte WASD.

se fallisci entro il tempo → morso automatico.

finché sei bloccato in QTE, attack/push/flee sono disabilitati.

[✔] Timer di reset: dopo ogni azione, next_attack_at si aggiorna.

🛠 Refactor / Fix

[✔] _dispatch_command riscritto con whitelist combat/QTE, gestione errori pulita.

[✔] Game.loop aggiornato con hook per combat_tick (anche se input fermo → da completare con thread/async).

[✔] Fix messaggi di log: ora nel journal compaiono eventi coerenti (“entra in un POI”, “walker colpito”, ecc.).

#  Patch notes — Versione Alpha 0.3B
✨ Added

Energy system migliorato:
Il comando go <dir> [steps] consuma energia in base ai metri percorsi (steps * CELL_SIZE_METERS * energy_per_meter).

POI & Landmark dai JSON:
Ora i punti d’interesse sono caricati direttamente dai file delle mappe (overworld.json, house.json).

Supporto a una sezione opzionale "pois" nei JSON.

I landmark esistenti vengono usati come POI (posizione = centro del bbox).

🔄 Changed

Prossimità:

Se sei già dentro un landmark/POI, non viene più mostrato l’avviso di prossimità.

Migliorata la precisione dei messaggi (es. la Radura Luminosa ora viene rilevata correttamente).

Journal:

Muovendosi, logga ora distanza ed energia spesa.

Quando varchi un confine, aggiunge: “Frank entra in <landmark>”.

L’azione enter logga ora “Frank entra in <destinazione>” invece di un generico “Attraversa un portale”.

🛠 Fixed

Risolto UnboundLocalError in cmd_go quando il player non si muoveva (blocco immediato).

Corretta gestione degli ostacoli: ora in console appare quale ostacolo blocca (es. recinzione, muro).

Rimosso codice legacy (game.poi_data), tutta la logica di prossimità proviene dai JSON.