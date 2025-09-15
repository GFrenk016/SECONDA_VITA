from typing import Callable, Dict, List
from engine.io import say
from engine.state import Location
from engine.journal import print_journal, log
from engine.persistence import save_state, next_save_name
from engine.combat import attack as attack_cmd  # opzionale
from game.scenes import (
    parse_key, make_key, ensure_location, in_bounds, is_passable,
    interest_points, try_portal, CELL_SIZE_METERS,
    world_display_name, portal_here, portals_around, neighbor_zone_transitions,
    route_hint_to_landmark
)

# ---------------- Registry ----------------
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

# ---------------- Helpers ----------------
def _blocked_dirs(world: str, x: int, y: int, z: int) -> List[str]:
    blocked = []
    neigh = {
        "east":  (x+1, y, z),
        "west":  (x-1, y, z),
        "north": (x, y, z+1),
        "south": (x, y, z-1),
    }
    for d, (nx, ny, nz) in neigh.items():
        if not in_bounds(nx, ny, nz, world) or not is_passable(nx, ny, nz, world):
            blocked.append(d)
    return blocked

def _show_loc(ctx):
    loc = ensure_location(ctx.world, ctx.state.location_key)
    world, x, y, z = parse_key(loc.key)
    say(f"{loc.name}  (World: {world} | X={x}, Y={y}, Z={z})")
    say(loc.desc)

    # Ostacoli adiacenti
    blocked = _blocked_dirs(world, x, y, z)
    if blocked:
        say("Ostacoli: " + ", ".join(blocked))

    # Oggetti visibili
    if loc.items:
        items = ", ".join([f"{n} x{q}" for n, q in loc.items.items()])
        say(f"Vedi: {items}")

    # Direzioni disponibili
    if loc.exits:
        dirs = ", ".join(sorted(loc.exits.keys()))
        say(f"Direzioni possibili: {dirs}")

    # --- HINT: Porte qui / vicino ---
    here_portal = portal_here(world, x, z)
    if here_portal:
        w2, _, _, _ = here_portal
        say(f"Qui c'è un ingresso per **{world_display_name(w2)}**. (Comando: enter)")
    else:
        near = portals_around(world, x, z)
        if near:
            by_world = {}
            for d, w2 in near:
                by_world.setdefault(w2, []).append(d)
            parts = []
            for w2, dirs in by_world.items():
                dirs_str = "/".join(dirs)
                parts.append(f"{dirs_str} → {world_display_name(w2)}")
            say("Intravedi un ingresso: " + "; ".join(parts))

    # --- HINT: Confine tra landmark ---
    edges = neighbor_zone_transitions(world, x, z)
    if edges:
        parts = [f"{d} → {name}" for d, name in edges]
        say("A confine di zona: " + "; ".join(parts))

    # --- HINT: Percorso per l'Atrio (solo nella mappa 'house') ---
    if world == "house":
        hint = route_hint_to_landmark(world, x, z, "atrio")
        if hint and hint["steps"] > 0:
            dx, dz = hint["dx"], hint["dz"]
            moves = []
            if dx > 0:
                moves.append(f"east {dx}")
            if dx < 0:
                moves.append(f"west {abs(dx)}")
            if dz > 0:
                moves.append(f"north {dz}")
            if dz < 0:
                moves.append(f"south {abs(dz)}")
            path_str = ", ".join(moves)
            say(f"Per raggiungere {hint['name']}: {path_str} (~{hint['steps']} passi).")


# ---------------- Comandi ----------------
def cmd_help(ctx, *args):
    say("Comandi disponibili:")
    for k in sorted(REGISTRY.list().keys()):
        say(f" - {k}")

def cmd_look(ctx, *args):
    _show_loc(ctx)

def cmd_go(ctx, *args):
    """
    go <dir> [steps]
      dir: east|west|north|south (alias e/w/n/s)
      steps: intero positivo (default 1)
    """
    if not args:
        say("Andare dove?")
        return

    aliases = {"e":"east","w":"west","n":"north","s":"south"}
    d = aliases.get(args[0].lower(), args[0].lower())
    if d not in ("east","west","north","south"):
        say("Direzione sconosciuta. Usa east/west/north/south (o e/w/n/s).")
        return

    steps = 1
    if len(args) >= 2:
        try:
            steps = max(1, int(args[1]))
        except ValueError:
            say("Passi non validi. Usa un intero positivo (es. 'go east 10').")
            return

    dx = 1 if d == "east" else -1 if d == "west" else 0
    dz = 1 if d == "north" else -1 if d == "south" else 0

    world, cx, cy, cz = parse_key(ctx.state.location_key)
    moved = 0
    for _ in range(steps):
        nx, ny, nz = cx + dx, cy, cz + dz
        if not in_bounds(nx, ny, nz, world) or not is_passable(nx, ny, nz, world):
            break
        cx, cz = nx, nz
        moved += 1

    ctx.state.location_key = make_key(world, cx, cy, cz)
    ensure_location(ctx.world, ctx.state.location_key)

    if moved == 0:
        say("Qualcosa ti sbarra la strada.")
    else:
        metri = moved * CELL_SIZE_METERS
        say(f"Ti muovi verso {d} per {moved} passi (~{metri} m).")
        log(ctx, f"Frank si muove {d} di {moved} passi (~{metri} m).")

    _show_loc(ctx)

def cmd_enter(ctx, *args):
    """
    Entra/esci da un'area tramite portale (come nei vecchi Pokémon).
    Se sulla cella esiste un portale -> teletrasporta alla destinazione.
    """
    dest = try_portal(ctx.state.location_key)
    if not dest:
        say("Non c'è un ingresso/uscita qui.")
        return
    ctx.state.location_key = dest
    ensure_location(ctx.world, dest)
    say("Attraversi la soglia…")
    log(ctx, "Frank attraversa un portale.")
    _show_loc(ctx)

def cmd_take(ctx, *args):
    if not args:
        say("Prendere cosa?")
        return
    item = args[0].lower()
    loc: Location = ensure_location(ctx.world, ctx.state.location_key)
    qty = loc.items.get(item, 0)
    if qty <= 0:
        say(f"Non vedi il {item} qui.")
        return
    loc.items[item] = qty - 1
    if loc.items[item] <= 0:
        del loc.items[item]
    inv = ctx.state.player.inventory
    inv[item] = inv.get(item, 0) + 1
    say(f"Hai preso il {item}.")
    log(ctx, f"Frank raccoglie {item}.")

def cmd_inventory(ctx, *args):
    inv = ctx.state.player.inventory
    if not inv:
        say("Il tuo inventario è vuoto.")
        return
    items = ", ".join([f"{k} x{v}" for k, v in inv.items()])
    say(f"Inventory: {items}")

def cmd_stats(ctx, *args):
    p = ctx.state.player
    say(f"Stats -> Health: {p.health}, Energy: {p.energy}, Morale: {p.morale}")

def cmd_talk(ctx, *args):
    target = (args[0].lower() if args else "").strip()
    if target in ("clem", "clementine"):
        say('Clementine: "We move at dawn. Stay ready, Frank."')
    else:
        say("Nessuno ha risposto.")

def cmd_journal(ctx, *args):
    print_journal(ctx)

def cmd_attack(ctx, *args):
    attack_cmd(ctx, *args)

def cmd_where(ctx, *args):
    world, cx, cy, cz = parse_key(ctx.state.location_key)
    pts = interest_points(world)
    say(f"Position -> World: {world} | X={cx}, Y={cy}, Z={cz}")
    if not pts:
        say("Nessun landmark definito.")
        return
    best = None
    for (px, py, pz, name) in pts:
        dx, dz = px - cx, pz - cz
        dist2 = dx*dx + dz*dz
        if best is None or dist2 < best[0]:
            best = (dist2, (px, py, pz), name)
    _, (px, py, pz), name = best
    steps_est = abs(px - cx) + abs(pz - cz)
    say(f"Nearest -> {name}  (X={px}, Z={pz})  Steps≈{steps_est}")
    hints = []
    if px - cx > 0: hints.append("east")
    if px - cx < 0: hints.append("west")
    if pz - cz > 0: hints.append("north")
    if pz - cz < 0: hints.append("south")
    say("Hint -> move: " + (", ".join(hints) if hints else "sei già sul posto"))

def cmd_save(ctx, *args):
    if args and args[0] in ("+", "new"):
        name = next_save_name("save")
    elif args:
        name = args[0].strip()
    else:
        name = getattr(ctx, "current_slot", None) or next_save_name("save")
    save_state(name, ctx.state.to_dict())
    ctx.current_slot = name
    say(f"Salvato in '{name}'.")
    log(ctx, f"Stato salvato in '{name}'.")

def cmd_menu(ctx, *args):
    say("Ritorno al menù principale...")
    ctx.state.flags["return_to_menu"] = True

# ---------------- Registrazione ----------------
REGISTRY.register("help", cmd_help, aliases=["h", "?"])
REGISTRY.register("look", cmd_look, aliases=["l"])
REGISTRY.register("go", cmd_go)
REGISTRY.register("enter", cmd_enter)
REGISTRY.register("take", cmd_take)
REGISTRY.register("inventory", cmd_inventory, aliases=["inv", "bag"])
REGISTRY.register("stats", cmd_stats)
REGISTRY.register("talk", cmd_talk)
REGISTRY.register("journal", cmd_journal)
REGISTRY.register("attack", cmd_attack)
REGISTRY.register("where", cmd_where)
REGISTRY.register("save", cmd_save)
REGISTRY.register("menu", cmd_menu)
