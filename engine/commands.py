from typing import Callable, Dict, List
from engine.io import say
from engine.state import Location

class CommandRegistry:
    def __init__(self):
        self._cmds: Dict[str, Callable] = {}
        self._aliases: Dict[str, str] = {}

    def register(self, name: str, func: Callable, aliases: List[str] | None = None):
        self._cmds[name] = func
        for a in (aliases or []):
            self._aliases[a] = name

    def resolve(self, token: str) -> Callable | None:
        key = token.lower().strip()
        if key in self._cmds: return self._cmds[key]
        if key in self._aliases: return self._cmds.get(self._aliases[key])
        return None

    def list(self) -> Dict[str, Callable]:
        return dict(self._cmds)

REGISTRY = CommandRegistry()

# --- base commands (ENGLISH NAMES) ---

def cmd_help(ctx, *args):
    say("Comandi disponibili:")
    for k in sorted(REGISTRY.list().keys()):
        say(f" - {k}")

def cmd_look(ctx, *args):
    loc = ctx.world[ctx.state.location_key]
    # Narrativa in ITA
    say(f"{loc.name}\n{loc.desc}")
    if loc.items:
        items = ", ".join([f"{n} x{q}" for n, q in loc.items.items()])
        say(f"Vedi: {items}")
    if loc.exits:
        exits = ", ".join([f"{d} -> {dest}" for d, dest in loc.exits.items()])
        say(f"Uscite: {exits}")

def cmd_go(ctx, *args):
    if not args:
        say("Andare dove?")
        return
    direction = args[0].lower()
    loc: Location = ctx.world[ctx.state.location_key]
    if direction not in loc.exits:
        say("Non puoi andare in quella direzione.")
        return
    ctx.state.location_key = loc.exits[direction]
    cmd_look(ctx)

def cmd_take(ctx, *args):
    if not args:
        say("Prendere cosa?")
        return
    item = args[0].lower()
    loc: Location = ctx.world[ctx.state.location_key]
    qty = loc.items.get(item, 0)
    if qty <= 0:
        say(f"Non vedi il {item} qui.")
        return
    # prendi 1
    loc.items[item] = qty - 1
    if loc.items[item] <= 0:
        del loc.items[item]
    inv = ctx.state.player.inventory
    inv[item] = inv.get(item, 0) + 1
    say(f"Hai preso il {item}.")

def cmd_inventory(ctx, *args):
    inv = ctx.state.player.inventory
    if not inv:
        say("Il tuo inventario è vuoto.")
        return
    items = ", ".join([f"{k} x{v}" for k, v in inv.items()])
    say(f"Inventory: {items}")

def cmd_talk(ctx, *args):
    # Placeholder dialoghi (ENG), narrativa resta ITA altrove
    target = (args[0].lower() if args else "").strip()
    if target in ("clem", "clementine"):
        say('Clementine: "We move at dawn. Stay ready, Frank."')
    else:
        say("Nessuno ha risposto.")

REGISTRY.register("help", cmd_help, aliases=["h", "?"])
REGISTRY.register("look", cmd_look, aliases=["l"])
REGISTRY.register("go", cmd_go)
REGISTRY.register("take", cmd_take)
REGISTRY.register("inventory", cmd_inventory, aliases=["inv", "bag"])
REGISTRY.register("talk", cmd_talk)
