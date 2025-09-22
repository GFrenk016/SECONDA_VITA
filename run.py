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
from engine.core.actions import look, go, wait, status, wait_until, inspect, examine, search, where, ActionError, engage, combat_action, spawn
from engine.core.combat import inject_content
from engine.core.loader.content_loader import load_combat_content

PROMPT = "> "

def help_lines():
    return [
        "Comandi disponibili:",
        " look                       - descrive l'area attuale",
        " go <dir>                   - muoviti nella direzione indicata (n, s, e, w, ...)",
        " wait [min]                 - attendi un certo numero di minuti (default 10)",
        " wait until <fase>          - salta alla fase (mattina|giorno|sera|notte)",
        " status | time              - mostra orario, giorno, meteo e clima",
        " where                      - macro -> micro corrente e tag stanza",
        " inspect <obj>              - osservazione base (sblocca livelli successivi)",
        " examine <obj>              - ispezione approfondita (richiede inspect precedente)",
        " search <obj>               - ricerca minuziosa (richiede inspect ed examine)",
        " spawn <enemy_id>           - genera un nemico e avvia combattimento (debug/manuale)",
        " attack                     - attacca il nemico (se in combattimento)",
        " qte <input>                - risposta al prompt QTE attivo (lettera)",
        " push                       - spingi indietro il nemico (guadagni distanza)",
        " flee                       - tenta la fuga dal combattimento",
        " menu                       - torna al menu principale senza uscire dal programma",
        " help                       - mostra questo elenco di comandi",
        " quit | exit                - esci dalla partita corrente (o dal menu principale)",
    ]

def game_loop():
    registry, state = load_world_and_state()
    # Carica asset combattimento dinamici
    weapons, mobs = load_combat_content()
    inject_content(weapons, mobs)
    print("-- Nuova partita avviata. Digita 'help' per l'elenco comandi. --")
    while True:
        cmd = input(PROMPT).strip()
        if not cmd:
            continue
        if cmd in {"quit", "exit"}:
            print("Arrivederci.")
            break
        if cmd == "menu":
            print("Ritorno al menu principale...")
            return  # ritorna al menu esterno
        if cmd == "help":
            for line in help_lines():
                print(line)
            continue
        try:
            if cmd == "look":
                res = look(state, registry)
            elif cmd.startswith("go "):
                direction = cmd[3:].strip()
                res = go(state, registry, direction)
            elif cmd in {"status", "time"}:
                res = status(state, registry)
            elif cmd == "where":
                res = where(state, registry)
            elif cmd.startswith("inspect "):
                target = cmd[len("inspect "):].strip()
                if not target:
                    print("Uso: inspect <id|alias>")
                    continue
                res = inspect(state, registry, target)
            elif cmd.startswith("examine "):
                target = cmd[len("examine "):].strip()
                if not target:
                    print("Uso: examine <id|alias>")
                    continue
                res = examine(state, registry, target)
            elif cmd.startswith("search "):
                target = cmd[len("search "):].strip()
                if not target:
                    print("Uso: search <id|alias>")
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
            elif cmd.startswith("spawn "):
                enemy_id = cmd.split(maxsplit=1)[1].strip()
                res = spawn(state, registry, enemy_id)
            elif cmd == "attack":
                res = combat_action(state, registry, 'attack')
            elif cmd.startswith("qte "):
                arg = cmd.split(maxsplit=1)[1].strip()
                res = combat_action(state, registry, 'qte', arg)
            elif cmd == "push":
                res = combat_action(state, registry, 'push')
            elif cmd == "flee":
                res = combat_action(state, registry, 'flee')
            else:
                print("Comando sconosciuto.")
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
            # Ristampa il menu dopo il ritorno dal game loop
            print(deco)
            print(title)
            print(deco)
            print("1) Inizia partita")
            print("2) Esci")
        elif choice in {"2", "q", "quit", "exit"}:
            print("Arrivederci.")
            break
        elif choice == "help":  # accessibile anche qui per comodità
            for line in help_lines():
                print(line)
        else:
            print("Seleziona 1 per iniziare o 2 per uscire (help per elenco comandi di gioco)")

def main():
    main_menu()

if __name__ == "__main__":
    main()
