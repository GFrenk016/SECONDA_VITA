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
from engine.core.actions import look, go, wait, ActionError

PROMPT = "> "

def main():
    registry, state = load_world_and_state()
    print("Seconda Vita - Prototype (Foresta)")
    print("Digita 'look' per osservare, 'go <direzione>' per muoverti, 'wait [min]' per far passare tempo, 'quit' per uscire.")
    while True:
        cmd = input(PROMPT).strip()
        if not cmd:
            continue
        if cmd in {"quit", "exit"}:
            print("Arrivederci.")
            break
        try:
            if cmd == "look":
                res = look(state, registry)
            elif cmd.startswith("go "):
                direction = cmd[3:].strip()
                res = go(state, registry, direction)
            elif cmd.startswith("wait"):
                parts = cmd.split()
                if len(parts) > 1:
                    try:
                        mins = int(parts[1])
                    except ValueError:
                        print("Formato: wait [minuti]")
                        continue
                else:
                    mins = 10
                res = wait(state, registry, mins)
            else:
                print("Comando sconosciuto.")
                continue
            for line in res["lines"]:
                print(line)
        except ActionError as e:
            print(f"[ERRORE] {e}")
        except Exception as e:
            print(f"[EXCEPTION] {e}")

if __name__ == "__main__":
    main()
