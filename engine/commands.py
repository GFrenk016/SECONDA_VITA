from typing import Callable, Dict, List
from engine.io import say
from engine.persistence import save_state, load_state
from engine.state import GameState

class CommandRegistry:
    def __init__(self):
        self._cmds: Dict[str, Callable] = {}
        self._aliases: Dict[str, str] = {}
        
    def register(self, name: str, func: Callable, aliases: List[str] | None =
None):
        self._cmds[name] = func
        for a in aliases or []:
            self._aliases[a] = name
            
    def resolve(self, token: str) -> Callable | None:
        key = token.lower().strip()
        if key in self._cmds:
            return self._cmds[key]
        if key in self._aliases:
            return self._cmds.get(self._aliases[key])
        return None
    
    def list(self) -> Dict[str, Callable]:
        return dict(self._cmds)
    
REGISTRY = CommandRegistry()

def cmd_help(ctx, *args):
    say("Available commands:")
    for name in sorted(REGISTRY.list().keys()):
        say(f" - {name}")
        
def cmd_look(ctx, *args):
    loc = ctx.state.location_key
    current = ctx.world[loc]
    say(f"{current.name}\n{current.desc}")
    if current.exits:
        exits = ", ".join([f"{k} -> {v}" for k, v in current.exits.items()])
        say(f"Exits: {exits}")
        
def cmd_go(ctx, *args):
    if not args:
        say("Go where?")
        return
    direction = args[0].lower()
    current = ctx.world[ctx.state.location_key]
    if direction not in current.exits:
        say("You can't go that way.")
        return
    ctx.state.location_key = current.exits[direction]
    cmd_look(ctx)
    
def cmd_take(ctx, *args):
    if not args:
        say("Take what?")
        return
    item = args[0].lower()
    inv = ctx.state.player.inventory
    inv[item] = inv.get(item, 0) + 1
    say(f"You take the {item}.")

def cmd_save(ctx, *args):
    name = args[0] if args else ctx.settings.get("default_save", "autosave")
    save_state(name, ctx.state.to_dict())
    say(f"Saved to '{name}'.")

def cmd_load(ctx, *args):
    name = args[0] if args else ctx.settings.get("default_save", "autosave")
    data = load_state(name)
    if not data:
        say(f"No save named '{name}'.")
        return
    ctx.state = GameState.from_dict(data)
    say(f"Loaded '{name}'.")

def cmd_use(ctx, *args):
    if not args:
        say("Use what?")
        return
    item = args[0].lower()
    if ctx.state.player.inventory.get(item, 0) <= 0:
        say(f"You don't have a {item}.")
        return
    say(f"You use the {item}, but nothing happens… yet.")

REGISTRY.register("save", cmd_save)
REGISTRY.register("load", cmd_load)
REGISTRY.register("help", cmd_help, aliases=["h", "?"])
REGISTRY.register("look", cmd_look, aliases=["l"])
REGISTRY.register("go", cmd_go)
REGISTRY.register("take", cmd_take)
REGISTRY.register("use", cmd_use)
