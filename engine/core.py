import argparse
from dataclasses import dataclass
from typing import Dict
from engine.commands import REGISTRY
from engine.io import prompt, say
from engine.persistence import save_state, load_state
from engine.state import GameState, Location
from game.scenes import build_world
from game.scripting import on_bootstrap, on_tick

@dataclass
class Context:
    state: GameState
    world: Dict[str, Location]
    settings: dict
    autosave_counter: int = 0

class Game:
    def __init__(self, settings: dict):
        self.settings = settings
        self.ctx: Context | None = None

    def bootstrap(self):
        args = self._parse_args()
        state = self._load_or_new(args.save or self.settings.get("default_save"))
        world = build_world()

        # Fallback location se il salvataggio punta a una chiave non presente
        if state.location_key not in world:
            state.location_key = "foresta"

        self.ctx = Context(state=state, world=world, settings=self.settings)
        on_bootstrap(self.ctx)

    def loop(self):
        assert self.ctx is not None
        say("Digita 'help' per i comandi (in inglese).")
        while True:
            raw = prompt(self.settings.get("prompt", "> "))
            if not raw:
                continue
            low = raw.lower().strip()
            if low in ("exit", "quit"):
                self._autosave(force=True)
                say("Fine. La notte trattiene il respiro.")
                break
            self._dispatch_command(raw)
            self._tick()

    # internals
    def _dispatch_command(self, raw: str):
        token, *args = raw.strip().split()
        fn = REGISTRY.resolve(token)
        if fn is None:
            say("Unknown command. Type 'help'.")
            return
        fn(self.ctx, *args)

    def _tick(self):
        self.ctx.state.tick += 1

        # Effetto fatica semplice: -1 energy a ogni turno (clamp 0–100)
        p = self.ctx.state.player
        p.energy = max(0, min(100, p.energy - 1))

        on_tick(self.ctx)
        self._autosave()

    def _autosave(self, force: bool = False):
        every = self.settings.get("autosave_every", 0)
        self.ctx.autosave_counter += 1
        if force or (every and self.ctx.autosave_counter % every == 0):
            payload = self.ctx.state.to_dict()
            name = self.settings.get("default_save", "autosave")
            save_state(name, payload)

    def _load_or_new(self, slot_name: str) -> GameState:
        data = load_state(slot_name)
        if data:
            return GameState.from_dict(data)
        return GameState()

    @staticmethod
    def _parse_args():
        p = argparse.ArgumentParser()
        p.add_argument("--save", help="slot di salvataggio", default=None)
        p.add_argument("--debug", action="store_true")
        return p.parse_args()
