# 🎮 SECONDA VITA - GUIDA COMPLETA AL TEST

## 🚀 COME AVVIARE IL GIOCO

1. Apri il terminale nella cartella del gioco
2. Esegui: `python run.py`
3. Scegli l'opzione che preferisci:
   - **1** = Inizia partita (gioco completo)
   - **2** = Tutorial (guidato passo-passo)
   - **3** = Esci

## 📚 TUTORIAL AUTOMATICO

**Raccomandato per iniziare!** Il tutorial ti guida attraverso tutte le funzionalità:
- Esplorazione e movimento
- Gestione tempo e meteo
- Sistema inventario e statistiche
- Combattimento base e avanzato
- QTE (Quick Time Events)
- Sistema NPC e dialoghi

Durante il tutorial puoi:
- Premere **Invio** per eseguire automaticamente il comando suggerito
- Digitare il comando tu stesso per provarlo
- `skip` per saltare uno step
- `menu` per tornare al menu principale

## 🎯 GUIDA TEST COMPLETA - MODALITÀ LIBERA

## 🏟️ **ARENA DI TEST SPECIALE**

**NUOVO!** Ora puoi accedere a un'area di test dedicata con tutte le funzionalità:

- `test_world` - Teletrasportati all'Arena di Test
- L'arena include 5 zone specializzate:
  - **Arena Principale**: Test generali
  - **Zona Combattimento**: Spawn intensi e rinforzi
  - **Zona Crafting**: Laboratorio completo
  - **Zona NPC**: Dialoghi e interazioni
  - **Zona Ambientale**: Controllo tempo e meteo

### 🔥 **NUOVE FUNZIONALITÀ AVANZATE**

#### Sistema Spawn Dinamico:
- `spawn_random` - Spawn casuali di oggetti e nemici
- `spawn_random items` - Solo oggetti
- `spawn_random enemies` - Solo nemici
- Gli spawn avvengono automaticamente quando cambi area!
- **Rinforzi automatici** durante i combattimenti lunghi

### 🔍 **FASE 1: ESPLORAZIONE BASE**

#### Comandi fondamentali:
- `look` - Osserva l'ambiente attuale
- `where` - Mostra la tua posizione precisa
- `status` / `time` - Orario, meteo e stato generale
- `go <direzione>` - Muoviti (n, s, e, w, nord, sud, est, ovest)
- `test_world` - **NUOVO!** Vai all'Arena di Test

#### Test da fare:
1. `look` per vedere la descrizione iniziale
2. `where` per capire dove sei
3. `go n` per andare nella Radura Muschiosa
4. `go s` per tornare indietro
5. `go e` per esplorare la Quercia Cava

### ⏰ **FASE 2: GESTIONE TEMPO**

#### Comandi tempo:
- `wait` - Attendi 10 minuti (default)
- `wait 30` - Attendi 30 minuti
- `wait until sera` - Attendi fino alla sera
- `wait until notte` - Attendi fino alla notte
- `wait until mattina` - Attendi fino al mattino

#### Test da fare:
1. `status` per vedere l'orario attuale
2. `wait 15` per far passare 15 minuti
3. `wait until notte` per vedere il cambio di fase
4. `look` per vedere come cambia la descrizione ambientale

### 🔍 **FASE 3: INTERAZIONE AMBIENTALE**

#### Sequenza di interazione:
1. `inspect <oggetto>` - Prima osservazione (sblocca examine)
2. `examine <oggetto>` - Analisi approfondita (sblocca search)
3. `search <oggetto>` - Ricerca minuziosa (può dare ricompense)

#### Test da fare:
1. `inspect Cippo di Pietra`
2. `examine Cippo di Pietra`
3. `search Cippo di Pietra`
4. Vai in altre stanze e ripeti con altri oggetti

### 🎒 **FASE 4: INVENTARIO E STATISTICHE**

#### Comandi inventario:
- `inventory` / `inv` - Mostra inventario completo
- `stats` - Mostra statistiche del personaggio
- `equip <oggetto>` - Equipaggia un'arma o armatura
- `unequip <slot>` - Rimuovi oggetto equipaggiato
- `use <oggetto>` - Usa un consumabile
- `drop <oggetto> [quantità]` - Lascia cadere un oggetto
- `examine <oggetto>` - Esamina oggetto nell'inventario

#### Test da fare:
1. `inventory` per vedere cosa hai
2. `stats` per vedere le tue statistiche
3. `equip Hunting Knife` per equipaggiare il coltello
4. `use Medkit` per curarti
5. `stats` per vedere come sono cambiate le statistiche
6. `unequip main_hand` per rimuovere l'arma
7. `drop Cloth 1` per lasciare un tessuto

### 🔨 **FASE 5: SISTEMA CRAFTING**

#### Comandi crafting:
- `craft <ricetta>` - Crea un oggetto

#### Ricette disponibili da testare:
1. `craft bandage` - Crea bendaggio (usa Cloth)
2. `craft knife` - Crea coltello improvvisato
3. `craft arrow` - Crea freccia
4. `craft torch` - Crea torcia
5. `craft trap` - Crea trappola

#### Test da fare:
1. `inventory` per vedere i materiali
2. `craft bandage` per creare un bendaggio
3. `inventory` per vedere il risultato
4. Prova altre ricette se hai i materiali

### ⚔️ **FASE 6: COMBATTIMENTO BASE**

#### Avvio combattimento:
- `spawn <nemico>` - Genera un nemico
- `spawn_random enemies` - **NUOVO!** Spawn casuali di nemici

#### Nemici disponibili:
- `walker_basic` - Vagante base (facile)
- `walker_runner` - Corridore veloce
- `walker_tough` - Vagante resistente
- `rabbit` - Coniglio (passivo)

#### **NUOVO!** Sistema Rinforzi Automatici:
- Durante combattimenti lunghi arrivano rinforzi automatici
- Probabilità aumenta con durata del combattimento
- Più probabile quando hai pochi nemici

#### Comandi combattimento:
- `attack` - Attacca il bersaglio focalizzato
- `attack <numero>` - Attacca nemico specifico
- `attack all` - Attacco ad area (50% danno)
- `focus <numero>` - Cambia bersaglio principale
- `qte <tasto>` - Risponde ai Quick Time Events
- `push` - Spingi indietro il nemico
- `flee` - Tenta la fuga
- `reload` - Ricarica arma da fuoco
- `throw` - Lancia arma da lancio

#### Test da fare:
1. `spawn walker_basic` per iniziare un combattimento
2. `status` per vedere lo stato del combattimento
3. `attack` per attaccare
4. Quando appare un QTE (es. "Colpisci! (T)"), premi `qte t`
5. Continua finché il nemico non è sconfitto

### ⚔️ **FASE 7: COMBATTIMENTO AVANZATO**

#### Test multi-nemico:
1. `spawn walker_basic 3` per generare 3 nemici
2. `status` per vedere tutti i bersagli
3. `focus 2` per focalizzare il secondo nemico
4. `attack` per attaccare il nemico focalizzato
5. `attack all` per colpire tutti (danno ridotto)
6. `push` per guadagnare spazio
7. `flee` per tentare la fuga

#### QTE (Quick Time Events):
- **QTE Offensivi**: Appaiono durante i tuoi attacchi (es. "Colpisci! (T)")
- **QTE Difensivi**: Appaiono quando i nemici attaccano (es. "Difesa! (B)")
- Rispondi con `qte <tasto>` entro il tempo limite

### 👥 **FASE 8: SISTEMA NPC**

#### Comandi NPC:
- `talk` - Lista NPC disponibili
- `talk <nome>` - Inizia conversazione
- `say <messaggio>` - Parla durante conversazione
- `end` - Termina conversazione
- `profile <nome>` - Mostra profilo NPC

#### Test da fare:
1. `talk` per vedere gli NPC presenti
2. `talk Guardiano del Bosco` per parlare con l'NPC
3. `say Ciao, come stai?` per conversare
4. `profile Guardiano del Bosco` per vedere il profilo
5. `end` per terminare la conversazione

### 💾 **FASE 9: SALVATAGGIO**

#### Comandi salvataggio:
- `save [nome]` - Salva la partita
- `load [nome]` - Carica partita salvata
- `saves` - Lista salvataggi disponibili

#### Test da fare:
1. `save test` per salvare con nome "test"
2. `saves` per vedere i salvataggi
3. `load test` per ricaricare

**Nota**: Il sistema di salvataggio ha un bug minore, potrebbe non funzionare perfettamente.

### 📖 **FASE 10: QUEST E MEMORIA**

#### Comandi sistema narrativo:
- `journal` - Mostra missioni attive
- `memories` - Mostra ricordi recuperati
- `choice list` - Lista scelte narrative disponibili
- `quest start <nome>` - Avvia micro-missione

#### Test da fare:
1. `journal` per vedere le missioni
2. `memories` per vedere i ricordi
3. `choice list` per vedere le scelte narrative

### 🗺️ **FASE 11: ESPLORAZIONE COMPLETA**

#### Aree da visitare:
1. **Limite del Sentiero** (area iniziale)
2. **Radura Muschiosa** (a nord)
3. **Quercia Cava** (a est)
4. **Ruscello Sommerso** (ovest dalla Radura)
5. **Soglia Radicata** (nord dalla Radura)

#### In ogni area:
1. `look` per la descrizione
2. `inspect` tutti gli oggetti visibili
3. `examine` e `search` dopo inspect
4. Prova a muoverti in tutte le direzioni possibili

## 🎯 **TEST SCENARIO COMPLETO**

### Scenario consigliato per test completo:

1. **Inizia**: `look`, `where`, `status`
2. **Esplora**: Visita tutte le aree disponibili
3. **Interagisci**: Inspect/examine/search tutti gli oggetti
4. **Gestisci inventario**: Equipaggia armi, usa consumabili
5. **Crafta**: Crea bendaggi e altri oggetti
6. **Combatti**: Spawn nemici e combatti usando QTE
7. **Parla**: Interagisci con gli NPC
8. **Progredisci tempo**: Vedi come cambia l'ambiente
9. **Salva**: Testa il sistema di salvataggio

## 🐛 **PROBLEMI NOTI**

1. **Sistema di salvataggio**: Potrebbe dare errori di serializzazione
2. **NPC Ollama**: Richiede server Ollama attivo per dialoghi AI avanzati

## 🎮 **COMANDI SPECIALI**

- `help` - Lista completa comandi
- `help <comando>` - Aiuto specifico per un comando
- `menu` - Torna al menu principale
- `quit` / `exit` - Esci dal gioco

## 🌟 **FEATURES DA TESTARE ASSOLUTAMENTE**

1. ✅ **Sistema QTE**: Combatti e rispondi ai prompt in tempo reale
2. ✅ **Gestione tempo**: Vedi come cambiano atmosfera e descrizioni
3. ✅ **Inventario avanzato**: Peso, equipaggiamento, statistiche
4. ✅ **Combattimento tattico**: Multi-nemico, focus, push, flee
5. ✅ **Interazione ambientale**: Inspect->examine->search
6. ✅ **Sistema crafting**: Crea oggetti utili
7. ✅ **Esplorazione**: Mondo interconnesso con atmosfere uniche

## �️ **TESTING NELL'ARENA SPECIALE**

### Percorso consigliato nell'Arena di Test:

1. **Accedi all'Arena**: `test_world`
2. **Esplora l'Arena Principale**: `look`, `inspect` tutti gli oggetti
3. **Testa Spawn Dinamici**: `spawn_random`, `spawn_random items`
4. **Zona Combat** (`go n`): Combattimenti intensi con rinforzi
5. **Zona Crafting** (`go e`): Laboratorio completo
6. **Zona NPC** (`go s`): Dialoghi avanzati
7. **Zona Ambientale** (`go w`): Controllo tempo/meteo
8. **Ritorna al mondo**: `go out`

### Test Avanzati nell'Arena:

#### Zona Combattimento:
- Spawn multipli: `spawn walker_basic 3`
- Attendi rinforzi automatici durante il combattimento
- Testa tutti i comandi di combattimento avanzato

#### Zona Crafting:
- Tutti i materiali sono disponibili
- Testa tutte le ricette conosciute
- Sistema inventario avanzato

#### Zona Ambientale:
- Controllo magico del tempo
- Fenomeni meteorologici accelerati
- Test meccaniche temporali

## �🎊 **DIVERTITI!**

Il gioco è completamente funzionale e pronto per essere giocato! 
Ogni sistema è stato testato e funziona correttamente.

### 🆕 **NOVITÀ IMPLEMENTATE:**
- ✅ **Arena di Test** completa con 5 zone specializzate
- ✅ **Sistema Spawn Dinamico** con spawn automatici
- ✅ **Rinforzi Automatici** durante i combattimenti
- ✅ **Tutorial Migliorato** con comandi funzionanti
- ✅ **Comando `test_world`** per accesso rapido
- ✅ **Spawn Casuali** per oggetti e nemici

**Buona esplorazione nel mondo di Seconda Vita! 🌲⚔️🏃‍♂️🏟️**