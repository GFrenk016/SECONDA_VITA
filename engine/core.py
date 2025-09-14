import argparse
from dataclasses import dataclass
from typing import Dict, Optional
from engine.commands import REGISTRY
from engine.io import prompt, say
from engine.state import GameState, Location
from engine.persistence import load_state
from game.scenes import build_world
from game.scripting import on_bootstrap, on_tick
from game.director import run_director  # Director eventi

@dataclass
class Context:
    state: GameState
    world: Dict[str, Location]
    settings: dict
    current_slot: Optional[str] = None  # slot di riferimento per i salvataggi manuali

class Game:
    def __init__(self, settings: dict):
        self.settings = settings
        self.ctx: Context | None = None

    def bootstrap(self, initial_state: GameState | None = None, slot_name: str | None = None):
        """
        Se initial_state è fornito, usa quello; altrimenti crea/carica.
        slot_name indica lo slot di default per i salvataggi manuali.
        """
        args = self._parse_args()
        if initial_state is None:
            state = self._load_or_new(args.save or self.settings.get("default_save"))
        else:
            state = initial_state

        world = build_world()

        # Fallback location se il salvataggio punta a una chiave non presente
        if state.location_key not in world:
            state.location_key = "foresta"

        current_slot = slot_name or args.save or self.settings.get("default_save")

        self.ctx = Context(state=state, world=world, settings=self.settings, current_slot=current_slot)
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
                say("Fine. La notte trattiene il respiro.")
                break

            self._dispatch_command(raw)
            self._tick()

            # Uscita al menù principale (comando 'menu' imposta il flag)
            if self.ctx.state.flags.get("return_to_menu"):
                break

            # Game Over
            if self.ctx.state.flags.get("game_over") or self.ctx.state.player.health <= 0:
                say("\nGAME OVER")
                prompt("Premi Invio per tornare al menù...")
                break

    # internals
    def _dispatch_command(self, raw: str):
        token, *args = raw.strip().split()
        fn = REGISTRY.resolve(token)
        if fn is None:
            say("Unknown command. Type 'help'.")
            return
        fn(self.ctx, *args)

    def _tick(self):
        # avanzamento turno
        self.ctx.state.tick += 1

        # Effetto fatica semplice
        p = self.ctx.state.player
        p.energy = max(0, min(100, p.energy - 1))

        # Hooks di gioco + Director eventi
        on_tick(self.ctx)
        run_director(self.ctx)

    def _load_or_new(self, slot_name: str | None) -> GameState:
        if slot_name:
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
