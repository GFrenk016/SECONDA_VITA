import argparse
from dataclasses import dataclass
from typing import Dict

from engine.commands import REGISTRY
from engine.io import prompt, say
from engine.persistence import save_state, load_state
from engine.state import GameState, Location
from game.scenes import build_world, normalize_key, spawn_key  # normalizzazione chiavi
from game.scripting import on_bootstrap, on_tick


@dataclass
class Context:
    state: GameState
    world: Dict[str, Location]
    settings: dict
    current_slot: str | None = None


class Game:
    def __init__(self, settings: dict):
        self.settings = settings
        self.ctx: Context | None = None

    # ---------------- Boot ----------------
    def bootstrap(self, initial_state: GameState | None = None, slot_name: str | None = None):
        """
        Prepara il mondo e lo stato. Se initial_state è None, crea un nuovo GameState().
        Qualsiasi location_key legacy/vecchia viene normalizzata al formato:
            w:<world>|x{X}_y{Y}_z{Z}
        """
        args = self._parse_args()

        # Stato
        state = initial_state if initial_state is not None else self._load_or_new(
            args.save or self.settings.get("default_save")
        )

        # Normalizza la chiave posizione (gestisce anche vecchi salvataggi)
        state.location_key = normalize_key(getattr(state, "location_key", ""))

        # Mondo
        world = build_world()

        # Context
        self.ctx = Context(state=state, world=world, settings=self.settings, current_slot=slot_name)

        # Hook di bootstrap (messaggi iniziali ecc.)
        on_bootstrap(self.ctx)

    # ---------------- Main loop ----------------
    def loop(self):
        assert self.ctx is not None
        say("Digita 'help' per i comandi (in inglese).")
        while True:
            raw = prompt(self.settings.get("prompt", "> "))
            if not raw:
                continue

            low = raw.lower().strip()
            if low in ("exit", "quit"):
                say("Fine. La notte trattiene il respiro.")
                break

            self._dispatch_command(raw)
            if self._should_return_to_menu():
                # il menù esterno (main.py) intercetterà la fine del loop
                break

            self._tick()

    # ---------------- Internals ----------------
    def _dispatch_command(self, raw: str):
        token, *args = raw.strip().split()
        fn = REGISTRY.resolve(token)
        if fn is None:
            say("Unknown command. Type 'help'.")
            return
        fn(self.ctx, *args)

    def _tick(self):
        self.ctx.state.tick += 1
        on_tick(self.ctx)

    def _should_return_to_menu(self) -> bool:
        return bool(self.ctx.state.flags.get("return_to_menu"))

    def _load_or_new(self, slot_name: str | None) -> GameState:
        if slot_name:
            data = load_state(slot_name)
            if data:
                return GameState.from_dict(data)
        # nuovo stato: posizione verrà impostata a spawn da normalize_key() in bootstrap
        return GameState()

    @staticmethod
    def _parse_args():
        p = argparse.ArgumentParser()
        p.add_argument("--save", help="slot di salvataggio", default=None)
        p.add_argument("--debug", action="store_true")
        return p.parse_args()
