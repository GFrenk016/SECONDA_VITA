from typing import Callable, Dict, List
from math import hypot
from config import SETTINGS
from engine.assets import load_melee_weapons
from engine.assets import load_walkers
from engine.io import say
from engine.state import Location
from engine.journal import print_journal, log
from engine.persistence import save_state, next_save_name
from engine.combat import enter_combat_with_walker, in_combat
from engine.combat import attack as attack_cmd, push as push_cmd, flee as flee_cmd

from game.scenes import (
    parse_key, make_key, ensure_location, in_bounds, is_passable,
    interest_points, try_portal, CELL_SIZE_METERS,
    world_display_name, portal_here, portals_around, neighbor_zone_transitions,
    route_hint_to_landmark, landmark_at, obstacle_at, find_items_in_radius, find_items_in_radius_live
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
    """
    Restituisce le direzioni bloccate e, se possibile, il tipo di ostacolo.
    Esempio: ['east (recinzione)', 'north (muro)'].
    """
    blocked = []
    neigh = {
        "east":  (x+1, y, z),
        "west":  (x-1, y, z),
        "north": (x, y, z+1),
        "south": (x, y, z-1),
    }
    for d, (nx, ny, nz) in neigh.items():
        if not in_bounds(nx, ny, nz, world) or not is_passable(nx, ny, nz, world):
            # prova a identificare l'ostacolo presente sulla cella di arrivo
            reason = obstacle_at(world, nx, nz) or "ostacolo"
            blocked.append(f"{d} ({reason})")
    return blocked

def _proximity_lines(world: str, cx: int, cz: int) -> List[str]:
    """
    Avvisi di prossimità entro raggio in METRI, escludendo il landmark attuale.
    """
    radius_m = SETTINGS.get("proximity_radius_m", 40.0)
    pts = interest_points(world) or []
    if not pts:
        return []

    # Escludi il landmark in cui ti trovi
    current_lm = landmark_at(world, cx, cz)

    lines: List[str] = []
    near: List[tuple[float, str]] = []  # (dist_m, name)

    for (px, _py, pz, name) in pts:
        # se il punto coincide col landmark in cui sei, non segnalarlo
        if current_lm and name == current_lm:
            continue
        dx = (px - cx) * CELL_SIZE_METERS
        dz = (pz - cz) * CELL_SIZE_METERS
        dist_m = hypot(dx, dz)
        if 0.0 < dist_m <= radius_m:
            near.append((dist_m, name))

    if not near:
        return []

    near.sort(key=lambda t: t[0])
    for dist_m, name in near[:2]:
        md = int(round(dist_m))
        lines.append(f"Senti la presenza di **{name}** a circa {md} metri.")
    return lines

def _show_loc(ctx):
    loc = ensure_location(ctx.world, ctx.state.location_key)
    world, x, y, z = parse_key(loc.key)
    say(f"{loc.name}  (World: {world} | X={x}, Y={y}, Z={z})")
    say(loc.desc)

    # Ostacoli adiacenti
    blocked = _blocked_dirs(world, x, y, z)
    if blocked:
        say("Ostacoli: " + ", ".join(blocked))


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

    # --- HINT: Prossimità POI/Landmark (entro raggio in metri) ---
    prox = _proximity_lines(world, x, z)
    if prox:
        for line in prox:
            say(line)

def _item_name(item_id: str) -> str:
    melee = load_melee_weapons()
    if item_id in melee:
        return melee[item_id].get("name", item_id)
    return item_id

def _resolve_item_id_in_here(token: str, loc) -> str | None:
    """
    Prova a risolvere ciò che l’utente ha scritto (id o nome umano)
    contro gli items presenti nella location corrente.
    Ritorna l'ID valido (es. 'knife') oppure None.
    """
    token = token.lower().strip()
    # 1) id esatto
    if token in loc.items:
        return token
    # 2) match per nome umano da catalogo melee -> id
    melee = load_melee_weapons()
    name_to_id = { melee[w]["name"].lower(): w for w in melee }
    wid = name_to_id.get(token)
    if wid and wid in loc.items:
        return wid
    return None

# ---------------- Comandi ----------------
def cmd_help(ctx, *args):
    say("Comandi disponibili:")
    for k in sorted(REGISTRY.list().keys()):
        say(f" - {k}")

def cmd_look(ctx, *args):
    _show_loc(ctx)

def cmd_go(ctx, *args):
    """
    go <dir> [steps] [sprint|stealth]
      dir: east|west|north|south (alias e/w/n/s)
      steps: intero positivo (default 1)
      mode: sprint -> +metri, costo×1.5, noise+2
            stealth -> -metri, costo×0.8, noise+0
    """
    if not args:
        say("Andare dove?")
        return

    aliases = {"e": "east", "w": "west", "n": "north", "s": "south"}
    d = aliases.get(args[0].lower(), args[0].lower())
    if d not in ("east", "west", "north", "south"):
        say("Direzione sconosciuta. Usa east/west/north/south (o e/w/n/s).")
        return

    steps = 1
    mode = None
    if len(args) >= 2:
        try:
            steps = max(1, int(args[1]))
            if len(args) >= 3:
                mode = args[2].lower()
        except ValueError:
            # forse hanno scritto 'go east sprint' senza steps
            mode = args[1].lower()
            steps = 1

    dx = 1 if d == "east" else -1 if d == "west" else 0
    dz = 1 if d == "north" else -1 if d == "south" else 0

    world, cx, cy, cz = parse_key(ctx.state.location_key)
    prev_landmark = landmark_at(world, cx, cz)

    # Modificatori
    spd_mult = 1.0
    cost_mult = 1.0
    noise = 0
    if mode == "sprint":
        spd_mult = SETTINGS.get("sprint_speed_mult", 1.5)
        cost_mult = SETTINGS.get("sprint_energy_mult", 1.5)
        noise = 2
    elif mode == "stealth":
        spd_mult = SETTINGS.get("stealth_speed_mult", 0.5)
        cost_mult = SETTINGS.get("stealth_energy_mult", 0.8)
        noise = 0

    # Applichiamo il modificatore alla distanza in passi (arrotonda per eccesso)
    eff_steps = max(1, int(round(steps * spd_mult)))

    moved = 0
    for _ in range(eff_steps):
        nx, ny, nz = cx + dx, cy, cz + dz
        if not in_bounds(nx, ny, nz, world) or not is_passable(nx, ny, nz, world):
            reason = obstacle_at(world, nx, nz) or "ostacolo"
            if moved == 0:
                say(f"Qualcosa ti sbarra la strada ({reason}).")
            else:
                say(f"Non puoi proseguire ({reason}). Ti fermi dopo {moved} passi.")
            break
        cx, cz = nx, nz
        moved += 1

    if moved == 0:
        return

    ctx.state.location_key = make_key(world, cx, cy, cz)
    ensure_location(ctx.world, ctx.state.location_key)

    metri = moved * CELL_SIZE_METERS
    epm = SETTINGS.get("energy_per_meter", 0.02)
    spent = metri * epm * cost_mult

    p = ctx.state.player
    before = getattr(p, "energy", 10.0)
    after = max(0.0, before - spent)
    p.energy = after

    # Feedback
    extra = f" [{mode}]" if mode in ("sprint","stealth") else ""
    say(f"Ti muovi verso {d}{extra} per {moved} passi (~{metri} m).")
    log(ctx, f"Frank si muove {d}{extra} di {moved} passi (~{metri} m). Energia {before:.2f}→{after:.2f} (−{spent:.2f}).")

    # Rumore → Director (hook semplice)
    if hasattr(ctx, "director") and hasattr(ctx.director, "on_noise"):
        try:
            ctx.director.on_noise(ctx, noise)
        except Exception:
            pass

    # Journal: ingresso in nuovo landmark
    new_landmark = landmark_at(world, cx, cz)
    if new_landmark and new_landmark != prev_landmark:
        log(ctx, f"Frank entra in {new_landmark}.")
        # Autosave smart
        if SETTINGS.get("autosave_every", 0) is not None:
            try:
                from engine.persistence import save_state, next_save_name
                name = getattr(ctx, "current_slot", None) or next_save_name("autosave")
                save_state(name, ctx.state.to_dict())
                ctx.current_slot = name
            except Exception:
                pass
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

    loc: Location = ensure_location(ctx.world, ctx.state.location_key)

    # risolvi ciò che ha digitato l’utente (id o nome umano)
    asked = args[0]
    item_id = _resolve_item_id_in_here(asked, loc)
    if not item_id:
        say(f"Non vedi '{asked}' qui.")
        return

    qty = loc.items.get(item_id, 0)
    if qty <= 0:
        say(f"Non vedi {_item_name(item_id)} qui.")
        return

    # rimuovi dalla cella
    loc.items[item_id] = qty - 1
    if loc.items[item_id] <= 0:
        del loc.items[item_id]

    # aggiungi all’inventario
    inv = ctx.state.player.inventory
    inv[item_id] = inv.get(item_id, 0) + 1

    # messaggio con NOME leggibile
    say(f"Hai preso {_item_name(item_id)}.")
    log(ctx, f"Frank raccoglie {_item_name(item_id)}.")

def cmd_inventory(ctx, *args):
    inv = ctx.state.player.inventory
    if not inv:
        say("Il tuo inventario è vuoto.")
        return
    items = ", ".join([f"{_item_name(k)} x{v}" for k, v in inv.items()])
    say(f"Inventory: {items}")

def cmd_stats(ctx, *args):
    p = ctx.state.player
    say(f"Stats -> Health: {p.health}, Energy: {p.energy:.1f}, Morale: {p.morale}")

def cmd_talk(ctx, *args):
    target = (args[0].lower() if args else "").strip()
    if target in ("clem", "clementine"):
        say('Clementine: "We move at dawn. Stay ready, Frank."')
    else:
        say("Nessuno ha risposto.")

def cmd_journal(ctx, *args):
    print_journal(ctx)

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

def cmd_scan(ctx, *args):
    """
    scan [radius_m]
      - Consuma energia fissa
      - Mostra fino a 3 POI/landmark nel raggio
      - Mostra gli ITEM vicini dal world vivo (spariscono se li prendi)
      - Se niente nel raggio, indica il POI più vicino fuori raggio
    """
    # input
    radius = None
    if args:
        try:
            radius = float(args[0])
        except ValueError:
            radius = None

    radius_m = radius or SETTINGS.get("scan_radius_m", 80.0)
    cost = SETTINGS.get("scan_energy_cost", 0.6)

    # energia
    p = ctx.state.player
    before = getattr(p, "energy", 10.0)
    if before <= 0.0:
        say("Sei troppo esausto per concentrarti.")
        return
    p.energy = max(0.0, before - cost)

    # posizione
    world, cx, cy, cz = parse_key(ctx.state.location_key)

    # --- POI/landmark ---
    pts = interest_points(world) or []
    found_poi, nearest = [], None
    for (px, _py, pz, name) in pts:
        dx = (px - cx) * CELL_SIZE_METERS
        dz = (pz - cz) * CELL_SIZE_METERS
        dist = (dx*dx + dz*dz) ** 0.5
        if nearest is None or dist < nearest[0]:
            nearest = (dist, name)
        if 0.0 < dist <= radius_m:
            found_poi.append((dist, name))
    found_poi.sort(key=lambda t: t[0])
    top_poi = found_poi[:3]

    # --- ITEM LIVE entro raggio ---
    live_items = find_items_in_radius_live(ctx, radius_m)
    # mostrane fino a 5
    top_items = live_items[:5]

    fatigue_hint = " La mente ronza; la concentrazione vacilla." if p.energy < 0.3 else ""
    say("Chiudi gli occhi. Ascolti il territorio…" + fatigue_hint)

    if top_poi:
        say("Punti d'interesse:")
        for d, name in top_poi:
            say(f"- {name} ~{int(d)} m")

    if top_items:
        say("Oggetti nelle vicinanze:")
        for d, item_id, qty, x, z in top_items:
            say(f"- {_item_name(item_id)} x{qty} ~{int(d)} m (X={x}, Z={z})")

    if not top_poi and not top_items:
        if nearest:
            say(f"Niente entro {int(radius_m)} m. Più vicino: {nearest[1]} (~{int(nearest[0])} m).")
        else:
            say("Solo vento tra i rami. Nessun segno distinto.")

    from engine.journal import log
    log(ctx, f"Frank effettua uno scan (raggio {radius_m} m, costo {cost}).")

def cmd_rest(ctx, *args):
    """
    rest [ticks]
      - Recupera energia (SETTINGS['rest_energy_per_tick'] per tick)
      - Espone 'exposure' al Director (rischio eventi)
    """
    ticks = 1
    if args:
        try:
            ticks = max(1, int(args[0]))
        except ValueError:
            ticks = 1

    gain_per = SETTINGS.get("rest_energy_per_tick", 0.5)
    total_gain = gain_per * ticks

    p = ctx.state.player
    before = getattr(p, "energy", 10.0)
    p.energy = min(p.max_energy if hasattr(p, "max_energy") else 10.0, before + total_gain)

    say(f"Ti fermi. Respiri. Recuperi ~{total_gain:.1f} energia.")
    log(ctx, f"Frank riposa per {ticks} ticks (+{total_gain:.1f} energia).")

    # Hook al Director: esposizione al rischio (più rest, più chance eventi)
    if hasattr(ctx, "director") and hasattr(ctx.director, "on_exposure"):
        try:
            ctx.director.on_exposure(ctx, ticks)
        except Exception:
            pass
            
def cmd_spawn(ctx, *args):
    """
    spawn [mob_id]
      - Forza lo spawn di un mob (per ora walkers).
      - Default: 'shambler'.
      - Se sei già in combat, non spawna.
    """
    if in_combat(ctx):
        say("Sei già in lotta: pensa a sopravvivere prima 😉")
        return

    walkers = load_walkers()
    mob_id = (args[0].lower() if args else "shambler")
    if mob_id not in walkers:
        # feedback utile: lista disponibili
        available = ", ".join(sorted(walkers.keys()))
        say(f"Mob '{mob_id}' non trovato. Disponibili: {available}")
        return

    enter_combat_with_walker(ctx, mob_id=mob_id)

def cmd_equip(ctx, *args):
    """
    equip <arma>
      - Accetta id (es. knife) o nome umano (es. Coltello).
      - Richiede che tu abbia almeno 1 unità in inventario.
    """
    if not args:
        cur = getattr(ctx.state.player, "equipped", None)
        if cur:
            say(f"Hai già equipaggiato: {_item_name(cur)}.")
        else:
            say("Non hai nulla equipaggiato. Usa: equip <arma>")
        return

    token = " ".join(args).lower().strip()
    melee = load_melee_weapons()
    name_to_id = { v.get("name","").lower(): k for k, v in melee.items() }

    wid = None
    if token in melee:
        wid = token
    elif token in name_to_id:
        wid = name_to_id[token]

    if not wid:
        say(f"Arma '{token}' non trovata.")
        return

    inv = ctx.state.player.inventory
    if inv.get(wid, 0) <= 0:
        say(f"Non possiedi {_item_name(wid)}.")
        return

    ctx.state.player.equipped = wid
    say(f"Impugni {_item_name(wid)}.")
    from engine.journal import log
    log(ctx, f"Frank equipaggia {_item_name(wid)}.")

def cmd_attack(ctx, *args):
    try:
        from engine import combat as _combat
        return _combat.attack(ctx, *args)
    except Exception as e:
        from engine.io import say
        say(f"Attack non disponibile: {e}")

def cmd_push(ctx, *args):
    try:
        from engine import combat as _combat
        return _combat.push(ctx, *args)
    except Exception as e:
        from engine.io import say
        say(f"Push non disponibile: {e}")

def cmd_flee(ctx, *args):
    try:
        from engine import combat as _combat
        return _combat.flee(ctx, *args)
    except Exception as e:
        from engine.io import say
        say(f"Flee non disponibile: {e}")

def cmd_qte(ctx, *args):
    from engine import combat as _combat
    _combat.qte_input(ctx, *args)

# ---------------- Registrazione ----------------
REGISTRY.register("help", cmd_help, aliases=["h", "?"])
REGISTRY.register("scan", cmd_scan)
REGISTRY.register("rest", cmd_rest)
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
REGISTRY.register("spawn", cmd_spawn)
REGISTRY.register("equip", cmd_equip)
REGISTRY.register("push", cmd_push)
REGISTRY.register("flee", cmd_flee)
REGISTRY.register("qte", cmd_qte)
