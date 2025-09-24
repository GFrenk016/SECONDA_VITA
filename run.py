"""Minimal CLI loop to test 'look' and 'go' commands.

Usage (example):
    python run.py
Then type commands:
    look
    go n
    go e
"""
from __future__ import annotations
from game.bootstrap import load_world_and_state
import difflib
from engine.core.actions import look, go, wait, status, wait_until, inspect, examine, search, where, ActionError, engage, combat_action, spawn, inventory, stats, use_item, equip_item, unequip_item, drop_item, examine_item, talk, say
from engine.core.combat import inject_content, tick_combat, set_complex_qte
from config import DEFAULT_COMPLEX_QTE_ENABLED, CLI_TICK_INTERVAL_SECONDS
from engine.core.loader.content_loader import load_combat_content

PROMPT = "> "

COMMAND_HELP = {
    'look': {'usage': 'look', 'desc': 'Descrive l\'area attuale con eventuale linea ambientale.'},
    'go': {'usage': 'go <direzione>', 'desc': 'Muove verso una direzione valida (n, s, e, w, ...).'},
    'wait': {'usage': 'wait [minuti]  |  wait until <fase>', 'desc': 'Avanza il tempo simulato; until: mattina|giorno|sera|notte.'},
    'status': {'usage': 'status', 'desc': 'Mostra orario/meteo/clima e (se in combattimento) stato nemici.'},
    'time': {'usage': 'time', 'desc': 'Alias di status.'},
    'where': {'usage': 'where', 'desc': 'Mostra macro->micro e tag stanza.'},
    'inspect': {'usage': 'inspect <oggetto>', 'desc': 'Osservazione base; sblocca examine e search.'},
    'examine': {'usage': 'examine <oggetto>', 'desc': 'Analisi approfondita (richiede inspect precedente).'},
    'search': {'usage': 'search <oggetto>', 'desc': 'Ricerca minuziosa (richiede examine precedente).'},
    'spawn': {'usage': 'spawn <enemy_id> [count]', 'desc': 'Genera 1 o più nemici (se in combattimento li aggiunge alla battaglia).'},
    'attack': {'usage': 'attack [index] | attack all', 'desc': 'Attacca il bersaglio (indice) oppure tutti (all, 50% danno).'},
    'focus': {'usage': 'focus <index>', 'desc': 'Imposta il bersaglio focalizzato usato dagli attacchi senza indice.'},
    'qte': {'usage': 'qte <tasto>', 'desc': 'Risponde a QTE attivo (offense/defense).'},
    'push': {'usage': 'push', 'desc': 'Spingi indietro il nemico, ritardando il prossimo attacco.'},
    'flee': {'usage': 'flee', 'desc': 'Tenta di fuggire; chance aumentata con distanza o nemico ferito.'},
    # New inventory and stats commands
    'inventory': {'usage': 'inventory | inv', 'desc': 'Mostra inventario con peso e oggetti equipaggiati.'},
    'stats': {'usage': 'stats', 'desc': 'Mostra statistiche giocatore, resistenze e buff attivi.'},
    'use': {'usage': 'use <oggetto>', 'desc': 'Usa un oggetto dall\'inventario (consumabili).'},
    'equip': {'usage': 'equip <oggetto>', 'desc': 'Equipaggia un oggetto dall\'inventario.'},
    'unequip': {'usage': 'unequip <slot|oggetto>', 'desc': 'Rimuove oggetto equipaggiato.'},
    'drop': {'usage': 'drop <oggetto> [quantità]', 'desc': 'Lascia cadere oggetto dall\'inventario.'},
    'examine': {'usage': 'examine <oggetto>', 'desc': 'Analisi approfondita (richiede inspect precedente).'},
    'talk': {'usage': 'talk [nome_npc]', 'desc': 'Parla con gli NPC presenti. Senza nome mostra la lista.'},
    'say': {'usage': 'say <messaggio>', 'desc': 'Continua una conversazione attiva con un NPC.'},
    'help': {'usage': 'help [comando]', 'desc': 'Senza argomenti elenca tutto; con argomento mostra usage dettagliato.'},
    'menu': {'usage': 'menu', 'desc': 'Ritorna al menu principale.'},
    'quit': {'usage': 'quit | exit', 'desc': 'Esce dalla partita.'},
}

def help_lines():
    lines = ["Comandi disponibili:"]
    max_usage = max(len(info['usage']) for info in COMMAND_HELP.values())
    for name, info in COMMAND_HELP.items():
        usage = info['usage']
        desc = info['desc']
        lines.append(f" {usage.ljust(max_usage)}  - {desc}")
    return lines

def game_loop():
    registry, state = load_world_and_state()
    weapons, mobs = load_combat_content()
    inject_content(weapons, mobs)
    
    # Initialize inventory and stats systems
    from engine.items import create_default_items, load_items_from_assets
    from engine.loot import create_default_loot_tables, load_loot_tables_from_assets
    from engine.crafting import create_default_recipes, load_recipes_from_assets
    from engine.effects import create_default_effects
    
    # Load default content
    create_default_items()
    create_default_loot_tables()
    create_default_recipes()
    create_default_effects()
    
    # Try to load from assets
    try:
        items_loaded = load_items_from_assets()
        loot_loaded = load_loot_tables_from_assets()
        recipes_loaded = load_recipes_from_assets()
        print(f"-- Caricati {items_loaded} oggetti, {loot_loaded} tabelle loot, {recipes_loaded} ricette --")
    except Exception as e:
        print(f"Warning: Failed to load some assets: {e}")
    
    # Abilita QTE complessi in base alla config
    try:
        set_complex_qte(DEFAULT_COMPLEX_QTE_ENABLED)
    except Exception:
        pass
    print("-- Nuova partita avviata. Digita 'help' per l'elenco comandi. --")
    import time as _t
    # Avvia un ticker in background per far progredire il combattimento anche durante l'input bloccante
    import threading as _th
    _stop_event = _th.Event()

    def _bg_ticker():
        while not _stop_event.is_set():
            try:
                now_r = _t.time()
                # Aggiorna il tempo reale e processa eventi di combattimento
                state.recompute_from_real(now_r)
                lines = tick_combat(state)
                if lines:
                    for l in lines:
                        print(l)
                    # Ripresenta il prompt, dato che potremmo aver stampato durante input()
                    try:
                        print(PROMPT, end="", flush=True)
                    except Exception:
                        pass
                # Frequenza di tick configurabile
                _stop_event.wait(CLI_TICK_INTERVAL_SECONDS)
            except Exception:
                # In caso di errore inatteso, rallenta e continua
                _stop_event.wait(0.5)

    _ticker = _th.Thread(target=_bg_ticker, name="combat-ticker", daemon=True)
    _ticker.start()
    while True:
        cmd = input(PROMPT).strip()
        # Shortcut QTE handling: se siamo in QTE accetta direttamente l'input digitato,
        # sia singolo carattere, sia stringa alfanumerica (per QTE complessi 3-5).
        try:
            if cmd:
                sess = getattr(state, 'combat_session', None)
                if sess and sess.get('phase') == 'qte' and sess.get('qte'):
                    # Passa direttamente l'input così com'è alla logica QTE
                    res = combat_action(state, registry, 'qte', cmd)
                    for line in res["lines"]:
                        print(line)
                    continue  # passa al prossimo input loop
        except Exception:
            # Non deve interrompere il loop in caso di problemi marginali
            pass
        if not cmd:
            continue
        if cmd in {"quit", "exit"}:
            print("Arrivederci.")
            try:
                _stop_event.set()
                _ticker.join(timeout=1.0)
            finally:
                pass
            break
        if cmd == "menu":
            print("Ritorno al menu principale...")
            try:
                _stop_event.set()
                _ticker.join(timeout=1.0)
            finally:
                pass
            return
        if cmd.startswith("help"):
            parts = cmd.split(maxsplit=1)
            if len(parts) == 1:
                for line in help_lines():
                    print(line)
            else:
                topic = parts[1].strip()
                info = COMMAND_HELP.get(topic)
                if info:
                    print(f"Uso: {info['usage']}\n{info['desc']}")
                else:
                    close = difflib.get_close_matches(topic, COMMAND_HELP.keys(), n=3)
                    if close:
                        print(f"Comando '{topic}' non trovato. Forse intendevi: {', '.join(close)}")
                    else:
                        print(f"Comando '{topic}' non trovato.")
            continue
        try:
            if cmd == "look":
                res = look(state, registry)
            elif cmd.startswith("go"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: go <direzione> (es: go n)")
                    continue
                direction = parts[1].strip()
                if not direction:
                    print("Uso: go <direzione>")
                    continue
                res = go(state, registry, direction)
            elif cmd in {"status", "time"}:
                res = status(state, registry)
            elif cmd == "where":
                res = where(state, registry)
            elif cmd.startswith("inspect"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: inspect <oggetto>")
                    continue
                target = parts[1].strip()
                if not target:
                    print("Uso: inspect <oggetto>")
                    continue
                res = inspect(state, registry, target)
            elif cmd.startswith("examine"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: examine <oggetto>")
                    continue
                target = parts[1].strip()
                if not target:
                    print("Uso: examine <oggetto>")
                    continue
                # Try new item examine first, then fall back to old examine
                try:
                    res = examine_item(state, registry, target)
                    # If item not found, try the old examine command
                    if res["lines"] and "non trovato" in res["lines"][0]:
                        res = examine(state, registry, target)
                except Exception:
                    # Fall back to old examine
                    res = examine(state, registry, target)
            elif cmd.startswith("search"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: search <oggetto>")
                    continue
                target = parts[1].strip()
                if not target:
                    print("Uso: search <oggetto>")
                    continue
                res = search(state, registry, target)
            elif cmd.startswith("wait"):
                parts = cmd.split()
                if len(parts) >= 3 and parts[1] == "until":
                    target = parts[2]
                    res = wait_until(state, registry, target)
                else:
                    if len(parts) > 1:
                        try:
                            mins = int(parts[1])
                        except ValueError:
                            print("Formato: wait [minuti] oppure 'wait until <fase>'")
                            continue
                    else:
                        mins = 10
                    res = wait(state, registry, mins)
            elif cmd.startswith("spawn"):
                # Supporta count: spawn <enemy_id> [count]
                parts = cmd.split()
                if len(parts) < 2:
                    print("Uso: spawn <enemy_id> [count]")
                    continue
                enemy_id = parts[1]
                count = 1
                if len(parts) >= 3 and parts[2].isdigit():
                    count = max(1, int(parts[2]))
                # Se non in combattimento usa engage singolo; altrimenti usa comando combat_action interno
                if not state.combat_session or state.combat_session.get('phase') == 'ended':
                    # Spawna primo nemico: se count>1 il resto viene aggiunto via comando spawn interno dopo engage
                    res = spawn(state, registry, enemy_id)
                    if count > 1:
                        # delega alle azioni combat per aggiungere gli altri
                        combat_action(state, registry, f"spawn {enemy_id} {count-1}")
                else:
                    res = combat_action(state, registry, f"spawn {enemy_id} {count}")
            elif cmd.startswith("attack"):
                # attack o attack <index>
                res = combat_action(state, registry, cmd)
            elif cmd.startswith("focus"):
                res = combat_action(state, registry, cmd)
            elif cmd.startswith("qte"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: qte <tasto>")
                    continue
                arg = parts[1].strip()
                if not arg:
                    print("Uso: qte <tasto>")
                    continue
                res = combat_action(state, registry, 'qte', arg)
            elif cmd == "push":
                res = combat_action(state, registry, 'push')
            elif cmd == "flee":
                res = combat_action(state, registry, 'flee')
            # New inventory and stats commands
            elif cmd in {"inventory", "inv"}:
                res = inventory(state, registry)
            elif cmd == "stats":
                res = stats(state, registry)
            elif cmd.startswith("use"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: use <oggetto>")
                    continue
                item_name = parts[1].strip()
                if not item_name:
                    print("Uso: use <oggetto>")
                    continue
                res = use_item(state, registry, item_name)
            elif cmd.startswith("equip"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: equip <oggetto>")
                    continue
                item_name = parts[1].strip()
                if not item_name:
                    print("Uso: equip <oggetto>")
                    continue
                res = equip_item(state, registry, item_name)
            elif cmd.startswith("unequip"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: unequip <slot|oggetto>")
                    continue
                slot_or_item = parts[1].strip()
                if not slot_or_item:
                    print("Uso: unequip <slot|oggetto>")
                    continue
                res = unequip_item(state, registry, slot_or_item)
            elif cmd.startswith("drop"):
                parts = cmd.split()
                if len(parts) == 1:
                    print("Uso: drop <oggetto> [quantità]")
                    continue
                item_name = parts[1]
                quantity = 1
                if len(parts) >= 3 and parts[2].isdigit():
                    quantity = int(parts[2])
                res = drop_item(state, registry, item_name, quantity)
            elif cmd.startswith("examine"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: examine <oggetto>")
                    continue
                item_name = parts[1].strip()
                if not item_name:
                    print("Uso: examine <oggetto>")
                    continue
                # Try new item examine first, then fall back to old examine
                try:
                    res = examine_item(state, registry, item_name)
                    # If item not found, try the old examine command
                    if res["lines"] and "non trovato" in res["lines"][0]:
                        res = examine(state, registry, item_name)
                except Exception:
                    # Fall back to old examine
                    res = examine(state, registry, item_name)
            elif cmd.startswith("talk"):
                parts = cmd.split(maxsplit=1)
                npc_name = parts[1].strip() if len(parts) > 1 else None
                res = talk(state, registry, npc_name)
            elif cmd.startswith("say"):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    print("Uso: say <messaggio>")
                    continue
                message = parts[1].strip()
                if not message:
                    print("Uso: say <messaggio>")
                    continue
                res = say(state, registry, message)
            else:
                close = difflib.get_close_matches(cmd, COMMAND_HELP.keys(), n=3)
                if close:
                    print(f"Comando sconosciuto: '{cmd}'. Forse intendevi: {', '.join(close)}")
                else:
                    print(f"Comando sconosciuto: '{cmd}'. Digita 'help' per elenco oppure 'help <comando>' per dettagli.")
                continue
            for line in res["lines"]:
                print(line)
        except ActionError as e:
            print(f"[ERRORE] {e}")
        except Exception as e:
            print(f"[EXCEPTION] {e}")

def main_menu():
    title = " SECONDA VITA "
    deco = "=" * len(title)
    print(deco)
    print(title)
    print(deco)
    print("1) Inizia partita")
    print("2) Esci")
    while True:
        choice = input(PROMPT).strip().lower()
        if choice in {"1", "i", "inizia", "start", "s"}:
            game_loop()
            print(deco)
            print(title)
            print(deco)
            print("1) Inizia partita")
            print("2) Esci")
        elif choice in {"2", "q", "quit", "exit"}:
            print("Arrivederci.")
            break
        elif choice == "help":
            for line in help_lines():
                print(line)
        else:
            print("Seleziona 1 per iniziare o 2 per uscire (help per elenco comandi di gioco)")

def main():
    main_menu()

if __name__ == "__main__":
    main()
