from copy import deepcopy
from engine.core import Game
from engine.io import print_banner, prompt, say
from config import SETTINGS
from engine.persistence import list_saves, load_state, delete_state, next_save_name, save_state
from engine.state import GameState
import sys

def main_menu():
    print_banner()
    say("=== MENU ===")
    say("1) Continue (load/delete)")
    say("2) New Game")
    say("3) Exit")

    while True:
        choice = prompt("Select option (1-3): ").strip()
        if choice == "1":
            return "continue"
        elif choice == "2":
            return "new"
        elif choice == "3":
            say("Chiudi gli occhi, il mondo si ferma e aspetta il tuo ritorno")
            sys.exit(0)
        else:
            say("Invalid option.")

def choose_save_interactive() -> str | None:
    rows = list_saves()
    if not rows:
        say("No saves found.")
        return None

    while True:
        say("Available saves:")
        for i, s in enumerate(rows, 1):
            say(f"{i}) {s['name']}  [{s['mtime_str']}]")
        say("Actions: L<number> = Load, D<number> = Delete, Enter = Back")
        raw = prompt("> ").strip().lower()
        if raw == "":
            return None
        if (raw.startswith("l") or raw.startswith("d")) and len(raw) > 1:
            num_str = raw[1:].strip()
            try:
                idx = int(num_str)
                if not (1 <= idx <= len(rows)):
                    raise ValueError()
            except ValueError:
                say("Invalid index.")
                continue
            name = rows[idx - 1]["name"]
            if raw.startswith("l"):
                return name
            else:
                ok = delete_state(name)
                if ok:
                    say(f"Deleted '{name}'.")
                    rows = list_saves()  # refresh
                else:
                    say(f"Cannot delete '{name}'.")
        else:
            say("Use L# to load or D# to delete (e.g., L1, D2).")

def start_new_game():
    # genera slot: save1, save2, ...
    slot = next_save_name("save")

    # settings con default_save = slot
    settings = deepcopy(SETTINGS)
    settings["default_save"] = slot

    # stato nuovo e prima save immediata (per avere subito il file)
    state = GameState()
    save_state(slot, state.to_dict())

    game = Game(settings=settings)
    game.bootstrap(initial_state=state, slot_name=slot)
    say(f"New game started in slot '{slot}'.")
    game.loop()

def main():
    while True:
        action = main_menu()
        if action == "continue":
            slot = choose_save_interactive()
            if slot:
                data = load_state(slot)
                if data:
                    from game.scenes import build_world
                    state = GameState.from_dict(data)
                    world = build_world()
                    if state.location_key not in world:
                        state.location_key = "foresta"

                    settings = deepcopy(SETTINGS)
                    settings["default_save"] = slot

                    game = Game(settings=settings)
                    game.bootstrap(initial_state=state, slot_name=slot)
                    say(f"Loaded save '{slot}'.")
                    game.loop()
                    continue
            # torna al menu se non ha caricato nulla
            continue
        elif action == "new":
            start_new_game()

if __name__ == "__main__":
    main()
