# 📝 Changelog — Versione Alpha 0.3B
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