import argparse
import threading, time
from dataclasses import dataclass
from typing import Dict
from engine.commands import REGISTRY
from engine.io import prompt, say
from engine.persistence import save_state, load_state
from engine.state import GameState, Location
from game.scenes import build_world, normalize_key, spawn_key  # normalizzazione chiavi
from game.scripting import on_bootstrap, on_tick
from config import SETTINGS
from engine.geo import Position
from engine.io import render_proximity_block
from engine.combat import in_combat, combat_idle_tick, combat_tick
from types import SimpleNamespace

ALLOWED_IN_COMBAT = {"attack", "push", "flee", "stats", "inventory", "help", "qte"}
ALLOWED_DURING_QTE = {"qte", "help", "stats", "inventory"}

@dataclass
class Context:
    state: GameState
    world: Dict[str, Location]
    settings: dict
    current_slot: str | None = None


class Game:
    def __init__(self, settings):
        self.settings = settings

        # ctx minimale: state, world (riempito da scenes), prompt, slot, rng
        self.ctx = SimpleNamespace()
        self.ctx.state = GameState()             # usa il costruttore che hai già
        self.ctx.world = {}                      # verrà usato da game.scenes/ensure_location
        self.ctx.prompt = settings.get("prompt", "> ")
        self.ctx.current_slot = None
        self.ctx.flags = {}                      # opzionale: se lo usi altrove

        # combat clock in background (se l’hai messo)
        import threading, time
        from engine.combat import combat_tick
        self._combat_stop = threading.Event()
        self._combat_clock = threading.Thread(
            target=_combat_clock_loop, args=(self.ctx, self._combat_stop), daemon=True
        )
        self._combat_clock.start()

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

    # ---------------- Internals ----------------
    # engine/core.py  (dentro la classe Game)
    
    def _dispatch_command(self, raw: str) -> None:
        """
        Legge una riga di input, risolve il comando e lo esegue.
        - Supporta argomenti con virgolette (shlex)
        - In combat con QTE: consente solo 'qte', 'help', 'stats', 'inventory'
        - In combat normale: consente solo {attack, push, flee, qte, stats, inventory, help}
        - Error handling senza far crashare il gioco
        - Dopo l'esecuzione fa ticcare il timer del combat
        """
        import shlex
        from engine.io import say
        from engine.commands import REGISTRY
        from engine.combat import in_combat, combat_tick

        # whitelist locali per evitare dipendenze globali
        ALLOWED_IN_COMBAT = {"attack", "push", "flee", "qte", "stats", "inventory", "help"}
        ALLOWED_DURING_QTE = {"qte", "help", "stats", "inventory"}

        line = (raw or "").strip()
        if not line:
            # anche a input vuoto, il timer deve poter avanzare nel loop esterno
            return

        # tokenizzazione robusta
        try:
            parts = shlex.split(line)
        except ValueError:
            parts = line.split()

        if not parts:
            return

        token = parts[0].lower()
        args = parts[1:]

        # Guardie combat/QTE
        if in_combat(self.ctx):
            qte_active = bool(self.ctx.state.flags.get("qte_active", False))
            if qte_active:
                if token not in ALLOWED_DURING_QTE:
                    say("Sei bloccato! Libérati prima: usa 'qte <sequenza>'.")
                    return
            else:
                if token not in ALLOWED_IN_COMBAT:
                    say("Sei in lotta! Puoi: attack / push / flee / qte / stats / inventory / help.")
                    return

        # Risolvi comando
        fn = REGISTRY.resolve(token)
        if fn is None:
            say(f"Comando sconosciuto: '{token}'. Prova 'help'.")
            return

        # Esegui + gestione timer post-azione
        try:
            fn(self.ctx, *args)
            # dopo l'esecuzione, aggiorna il timer del combat (attacchi automatici/QTE)
            combat_tick(self.ctx)
        except Exception as e:
            # log soft-fail
            try:
                from engine.journal import log
                log(self.ctx, f"Errore comando '{token}': {e}")
            except Exception:
                pass
            say("Qualcosa va storto. (errore comando)")

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

    def loop(self):
        from engine.io import prompt_line
        while True:
            raw = prompt_line(self.ctx)
            if raw is None:
                break
            self._dispatch_command(raw)
            if self.ctx.state.flags.get("return_to_menu"):
                break
        # chiusura pulita del clock
        if hasattr(self, "_combat_stop"):
            self._combat_stop.set()
    
def move_player(state, direction: str, meters: float | None = None) -> str:
    DIRS = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
    if direction not in DIRS:
        return "Non capisco la direzione."

    # inizializza posizione/energia se mancano (compat vecchi save)
    if not hasattr(state.player, "pos"):
        state.player.pos = Position(0.0, 0.0)
    if not hasattr(state.player, "energy"):
        state.player.energy = 10.0

    dx, dy = DIRS[direction]
    dist = meters if (meters and meters > 0) else SETTINGS["step_meters"]

    # spostamento in metri
    state.player.pos = Position(
        state.player.pos.x + dx * dist,
        state.player.pos.y + dy * dist
    )

    # costo energia proporzionale ai metri
    spent = dist * SETTINGS["energy_per_meter"]
    state.player.energy = max(0.0, state.player.energy - spent)

    # tick del mondo se disponibile
    if hasattr(state, "world") and hasattr(state.world, "ticks"):
        state.world.ticks += 1

    # messaggio di feedback + prossimità
    md = int(dist)
    prose = f"Ti muovi verso {direction} per circa {md} metri. Senti il fiato farsi più corto."
    prox = render_proximity_block(state)
    return prose if not prox else prose + "\n" + prox

def _combat_clock_loop(ctx, stop_evt: "threading.Event"):
    """Tic periodico: fa avanzare QTE/attacchi anche se l'utente non digita."""
    while not stop_evt.is_set():
        try:
            combat_tick(ctx)
        except Exception:
            pass
        time.sleep(0.2)  # 200ms

