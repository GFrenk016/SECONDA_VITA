import argparse
from dataclasses import dataclass
from typing import Dict

from engine.commands import REGISTRY
from engine.io import prompt, say
from engine.persistence import save_state, load_state
from engine.state import GameState, Location
from game.scenes import build_world
from game.scripting import on_bootstrap, on_tick
from engine.plugins import Hooks

@dataclass
class Context:
    state: GameState
    world: Dict[str, Location]
    settings: dict
    hooks: Hooks
    autosave_counter: int = 0

class Game:
    def __init__(self, settings: dict):
        self.settings = settings
        self.ctx: Context | None = None
        
    def bootstrap(self):
        args = self._parse_args()
        state = self._load_or_new(args.save or
        self.settings.get("default_save"))
        world = build_world()
        hooks = Hooks()

        # scripting hooks
        hooks.on_tick(on_tick) # registra il tick custom
        self.ctx = Context(state=state, world=world,    settings=self.settings,
        hooks=hooks)
        on_bootstrap(self.ctx)
        
    def loop(self):
        assert self.ctx is not None
        say("Type 'help' for commands.")
        while True:
            raw = prompt(self.settings.get("prompt", "> "))
            if not raw:
                continue
            if raw.lower() in ("quit", "exit"):
                self._autosave(force=True)
                say("Goodbye.")
                break
            
            self.ctx.hooks.dispatch_command(self.ctx, raw)
            self._dispatch_command(raw)
            self._tick()
            
    # --- internals ---
    def _dispatch_command(self, raw: str):
        token, *args = raw.strip().split()
        fn = REGISTRY.resolve(token)
        if fn is None:
            say("Unknown command. Type 'help'.")
            return
        fn(self.ctx, *args)
        
    def _tick(self):
        self.ctx.state.tick += 1
        self.ctx.hooks.dispatch_tick(self.ctx)
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
        parser = argparse.ArgumentParser()
        parser.add_argument("--save", help="slot di salvataggio",
        default=None)
        parser.add_argument("--debug", action="store_true")
        return parser.parse_args()