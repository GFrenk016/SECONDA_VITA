import json, os, glob
import math
from engine.state import Location
from functools import lru_cache

_ASSETS_DIR = os.path.join("assets", "world")

# --- PATCH: POI/landmark dai JSON di mappa -------------------------------

def landmark_at(world: str, x: int, z: int) -> str | None:
    """Ritorna il nome del landmark (bbox) che contiene (x,z), se esiste."""
    data = _load_world_json(world)
    for lm in data.get("landmarks", []):
        bbox = lm.get("bbox")
        if not bbox:
            continue
        if bbox["x0"] <= x <= bbox["x1"] and bbox["z0"] <= z <= bbox["z1"]:
            return lm.get("name", lm.get("id", "landmark"))
    return None

def obstacle_at(world: str, x: int, z: int) -> str | None:
    """
    Ritorna il 'tipo' dell'ostacolo che occupa la cella (x,z), se presente.
    I tuoi ostacoli sono rect stretti (linee-muro): basta testare l'inclusione.
    Puoi aggiungere 'label' nel JSON per nomi più belli.
    """
    data = _load_world_json(world)
    for ob in data.get("obstacles", []):
        if ob.get("type") == "rect":
            if ob["x0"] <= x <= ob["x1"] and ob["z0"] <= z <= ob["z1"]:
                # se in futuro aggiungi "label", usala, altrimenti tipo
                return ob.get("label") or ob.get("type")
    return None

# Se non l'hai ancora, questa interest_points unisce POI espliciti e landmark-centroid:
def interest_points(world: str):
    pts: list[tuple[int,int,int,str]] = []
    pts.extend(_pois_from_json(world))             # opzionale, sezione "pois"
    pts.extend(_landmark_centers_from_json(world)) # centroidi dei bbox
    return pts

@lru_cache(maxsize=None)
def _load_world_json(world: str) -> dict:
    """
    Carica e cacha il file della mappa:
      'overworld' -> assets/world/overworld.json
      'house'     -> assets/world/house.json
    """
    path = os.path.join(_ASSETS_DIR, f"{world}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Mappa JSON non trovata: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _centroid_from_bbox(bbox: dict) -> tuple[int, int]:
    """
    Ritorna il centro (x,z) intero del rettangolo {x0,x1,z0,z1}.
    """
    x0, x1 = int(bbox["x0"]), int(bbox["x1"])
    z0, z1 = int(bbox["z0"]), int(bbox["z1"])
    cx = (x0 + x1) // 2
    cz = (z0 + z1) // 2
    return cx, cz

def _pois_from_json(world: str) -> list[tuple[int,int,int,str]]:
    """
    Estrae POI “espliciti” dal JSON (sezione opzionale 'pois' con campi name,x,z[,y]).
    Ritorna [(x,y,z,name)] in coordinate di CELLA.
    """
    data = _load_world_json(world)
    fixed_y = int(data.get("meta", {}).get("fixed_y", 0))
    out: list[tuple[int,int,int,str]] = []
    for p in data.get("pois", []):
        name = p.get("name", "POI")
        x = int(p.get("x", 0))
        z = int(p.get("z", 0))
        y = int(p.get("y", fixed_y))
        out.append((x, y, z, name))
    return out

def _landmark_centers_from_json(world: str) -> list[tuple[int,int,int,str]]:
    """
    Usa i LANDMARKS del JSON come punti d'interesse, piazzando il POI al CENTRO del bbox.
    Ritorna [(x,y,z,name)] in CELLE.
    """
    data = _load_world_json(world)
    fixed_y = int(data.get("meta", {}).get("fixed_y", 0))
    out: list[tuple[int,int,int,str]] = []
    for lm in data.get("landmarks", []):
        name = lm.get("name", lm.get("id", "landmark"))
        bbox = lm.get("bbox")
        if not bbox: 
            continue
        cx, cz = _centroid_from_bbox(bbox)
        out.append((int(cx), fixed_y, int(cz), name))
    return out

def interest_points(world: str):
    """
    Restituisce [(x, y, z, name), ...] in coordinate di CELLA per:
      1) POI espliciti nel JSON (sezione 'pois', opzionale)
      2) Centroidi dei LANDMARK (bbox) come “landmark-POI”
    (Compatibile con cmd_where e con i messaggi di prossimità in commands.py)
    """
    pts: list[tuple[int,int,int,str]] = []
    pts.extend(_pois_from_json(world))
    pts.extend(_landmark_centers_from_json(world))
    return pts

# ========= Loader di tutte le mappe =========

def _load_worlds():
    base = os.path.dirname(os.path.dirname(__file__))  # .../game
    path = os.path.join(base, "assets", "world", "*.json")
    worlds = {}
    for fn in glob.glob(path):
        with open(fn, "r", encoding="utf-8") as f:
            data = json.load(f)
        wid = data["meta"]["id"]
        worlds[wid] = data
    if "overworld" not in worlds:
        raise RuntimeError("Mappa 'overworld' mancante in assets/world/")
    return worlds

_WORLDS = _load_worlds()

# ========= Meta (valori di default dall'overworld) =========
_OVER = _WORLDS["overworld"]
DEFAULT_CELL_M = _OVER["meta"].get("cell_size_m", 2)
FIXED_Y_DEFAULT = _OVER["meta"].get("fixed_y", 150)

# ========= Key utils =========

def make_key(world: str, x: int, y: int, z: int) -> str:
    return f"w:{world}|x{x}_y{y}_z{z}"

def parse_key(key: str) -> tuple[str, int, int, int]:
    # w:<world>|x{X}_y{Y}_z{Z}
    wpart, cpart = key.split("|", 1)
    world = wpart.split(":", 1)[1]
    p = cpart.split("_")
    x = int(p[0][1:]); y = int(p[1][1:]); z = int(p[2][1:])
    return world, x, y, z

# --- Spawn & normalizzazione chiavi legacy ---

def spawn_key(world: str = "overworld") -> str:
    meta = world_meta(world)
    sx, sy, sz = meta["spawn"]
    return make_key(world, sx, sy, sz)

def normalize_key(maybe_key: str | None) -> str:
    """
    Accetta:
        - già nuovo formato: 'w:overworld|x150_y150_z150' -> ok
        - legacy coords: 'x150_y150_z150' -> mappa 'overworld'
        - nomi vecchi tipo 'foresta' -> manda a spawn overworld
        - None/empty -> spawn overworld
    """
    if not maybe_key:
        return spawn_key("overworld")
    if "|" in maybe_key:
        return maybe_key
    # legacy coordinata senza world
    if maybe_key.startswith("x") and "_y" in maybe_key and "_z" in maybe_key:
        p = maybe_key.split("_")
        try:
            x = int(p[0][1:]); y = int(p[1][1:]); z = int(p[2][1:])
            return make_key("overworld", x, y, z)
        except Exception:
            return spawn_key("overworld")
    # qualsiasi altro alias/chiave vecchia -> spawn
    return spawn_key("overworld")

# ========= Accesso dati per world =========

def world_meta(world: str):
    m = _WORLDS[world]["meta"]
    return {
        "id": m["id"],
        "name": m.get("name", world),
        "size_x": m["size"]["x"],
        "size_z": m["size"]["z"],
        "fixed_y": m.get("fixed_y", FIXED_Y_DEFAULT),
        "cell_m": m.get("cell_size_m", DEFAULT_CELL_M),
        "spawn": m.get("spawn")  # [x,y,z] opzionale per non-overworld
    }

def _landmarks(world: str):
    return _WORLDS[world].get("landmarks", [])

def _obstacles(world: str):
    return _WORLDS[world].get("obstacles", [])

def _portals(world: str):
    return _WORLDS[world].get("portals", [])

# ========= Bounds & passabilità (2D) =========

def in_bounds(x: int, y: int, z: int, world: str | None = None) -> bool:
    if world is None:
        world = "overworld"
    meta = world_meta(world)
    return (y == meta["fixed_y"]) and (0 <= x < meta["size_x"]) and (0 <= z < meta["size_z"])

def is_passable(x: int, y: int, z: int, world: str | None = None) -> bool:
    if world is None:
        world = "overworld"
    if not in_bounds(x, y, z, world):
        return False
    for r in _obstacles(world):
        if r.get("type") != "rect":
            continue
        if "y" in r:
            if y != r["y"]:
                continue
            if r["x0"] <= x <= r["x1"] and r["z0"] <= z <= r["z1"]:
                return False
        elif all(k in r for k in ("x0","x1","y0","y1","z0","z1")):
            if (r["x0"] <= x <= r["x1"] and
                r["y0"] <= y <= r["y1"] and
                r["z0"] <= z <= r["z1"]):
                return False
    return True

# ========= Landmarks & descrizioni =========

def _pt_in_2dbox(x: int, z: int, box: dict) -> bool:
    return (box["x0"] <= x <= box["x1"]) and (box["z0"] <= z <= box["z1"])

def _match_landmark(world: str, x: int, z: int):
    for lm in _landmarks(world):
        if _pt_in_2dbox(x, z, lm["bbox"]):
            return lm
    return None

def name_here(world: str, x: int, y: int, z: int) -> str:
    lm = _match_landmark(world, x, z)
    return lm["name"] if lm else world_meta(world)["name"]

def desc_here(world: str, x: int, y: int, z: int) -> str:
    lm = _match_landmark(world, x, z)
    if lm: return lm.get("desc", "")
    mod = (x * 31 + z * 13) % 4
    return [
        "Aghi di pino scricchiolano sotto i passi.",
        "Un corvo rompe il silenzio, poi svanisce.",
        "L’aria sa di resina e terra bagnata.",
        "Le fronde coprono il cielo: claustrofobia verde."
    ][mod]

def items_here(world: str, x: int, y: int, z: int) -> dict:
    lm = _match_landmark(world, x, z)
    if lm: return dict(lm.get("items", {}))
    return {}

# ========= Uscite (solo X/Z) =========

def exits_for(world: str, x: int, y: int, z: int) -> dict:
    ex = {}
    if is_passable(x + 1, y, z, world): ex["east"]  = make_key(world, x + 1, y, z)
    if is_passable(x - 1, y, z, world): ex["west"]  = make_key(world, x - 1, y, z)
    if is_passable(x, y, z + 1, world): ex["north"] = make_key(world, x, y, z + 1)
    if is_passable(x, y, z - 1, world): ex["south"] = make_key(world, x, y, z - 1)
    return ex

# ========= Portali =========

def portal_dest(world: str, x: int, z: int):
    """Se c'è un portale sulla cella, ritorna (world_to, x, y, z). Altrimenti None."""
    for p in _portals(world):
        fx, fz = p["from"]["x"], p["from"]["z"]
        if x == fx and z == fz:
            to = p["to"]
            w2 = to["world"]
            meta2 = world_meta(w2)
            y2 = meta2["fixed_y"]
            return (w2, to["x"], y2, to["z"])
    return None

# ===== Helper: nome world “umano” =====

def world_display_name(world_id: str) -> str:
    return world_meta(world_id)["name"]

# ===== Helper: landmark corrente =====

def _match_landmark(world: str, x: int, z: int):
    for lm in _landmarks(world):
        if _pt_in_2dbox(x, z, lm["bbox"]):
            return lm
    return None

def landmark_name_at(world: str, x: int, z: int) -> str | None:
    lm = _match_landmark(world, x, z)
    return lm["name"] if lm else None

# ===== Porte: qui e nei dintorni (4-neighbors) =====

def portal_here(world: str, x: int, z: int):
    """Ritorna (world_to, x, y, z) se la cella è un portale, altrimenti None."""
    return portal_dest(world, x, z)

def portals_around(world: str, x: int, z: int):
    """
    Ritorna lista di tuple (dir, world_to) per porte nelle 4 celle adiacenti.
    Esempio: [('east','house'), ('north','bunker'), ...]
    """
    res = []
    dirs = {
        "east":  (x + 1, z),
        "west":  (x - 1, z),
        "north": (x, z + 1),
        "south": (x, z - 1),
    }
    for d, (nx, nz) in dirs.items():
        dest = portal_dest(world, nx, nz)
        if dest:
            w2, _, _, _ = dest
            res.append((d, w2))
    return res

# ===== Confini tra landmark: differenza nelle celle adiacenti =====

def neighbor_zone_transitions(world: str, x: int, z: int):
    """
    Ritorna lista di (dir, landmark_name) se la cella adiacente appartiene
    a un landmark diverso dal tuo (segnale di “cambio zona”).
    """
    here = landmark_name_at(world, x, z)
    hints = []
    dirs = {
        "east":  (x + 1, z),
        "west":  (x - 1, z),
        "north": (x, z + 1),
        "south": (x, z - 1),
    }
    for d, (nx, nz) in dirs.items():
        if not in_bounds(nx, world_meta(world)["fixed_y"], nz, world):
            continue
        if not is_passable(nx, world_meta(world)["fixed_y"], nz, world):
            # anche se è muro, può comunque cambiare landmark dietro il muro: opzionale
            pass
        other = landmark_name_at(world, nx, nz)
        if other and other != here:
            hints.append((d, other))
    return hints

# ===== Landmark lookup & rotta verso bbox ===================================

def landmark_by_id(world: str, lm_id: str) -> dict | None:
    for lm in _landmarks(world):
        if lm.get("id") == lm_id:
            return lm
    return None

def closest_point_in_bbox(x: int, z: int, box: dict) -> tuple[int, int]:
    """Clampa (x,z) nel rettangolo e ritorna il punto più vicino dentro al bbox."""
    px = min(max(x, box["x0"]), box["x1"])
    pz = min(max(z, box["z0"]), box["z1"])
    return px, pz

def route_hint_to_landmark(world: str, x: int, z: int, landmark_id: str):
    """
    Calcola un hint di rotta verso il landmark (per es. 'atrio').
    Ritorna dict: {"name", "dx", "dz", "steps"} oppure None se non trovato.
    """
    lm = landmark_by_id(world, landmark_id)
    if not lm:
        return None
    box = lm["bbox"]
    tx, tz = closest_point_in_bbox(x, z, box)
    dx, dz = tx - x, tz - z
    steps = abs(dx) + abs(dz)
    return {"name": lm["name"], "dx": dx, "dz": dz, "steps": steps}

# ========= Costruzione Location =========

def make_location(world: str, x: int, y: int, z: int) -> Location:
    return Location(
        key=make_key(world, x, y, z),
        name=name_here(world, x, y, z),
        desc=desc_here(world, x, y, z),
        exits=exits_for(world, x, y, z),
        items=items_here(world, x, y, z),
    )

def ensure_location(cache: dict, key: str) -> Location:
    if key in cache: return cache[key]
    world, x, y, z = parse_key(key)
    loc = make_location(world, x, y, z)
    cache[key] = loc
    return loc

# ========= Seed iniziale =========

def build_world():
    """
    Crea il dizionario location cache e seed di alcune posizioni utili:
    - spawn overworld
    - centro di ogni landmark in ogni world
    """
    cache = {}
    over = world_meta("overworld")
    sx, sy, sz = over["spawn"]
    spawn_key = make_key("overworld", sx, sy, sz)
    cache[spawn_key] = make_location("overworld", sx, sy, sz)

    for wid, data in _WORLDS.items():
        meta = world_meta(wid)
        y = meta["fixed_y"]
        for lm in _landmarks(wid):
            b = lm["bbox"]
            cx = (b["x0"] + b["x1"]) // 2
            cz = (b["z0"] + b["z1"]) // 2
            cache[make_key(wid, cx, y, cz)] = make_location(wid, cx, y, cz)
    return cache

# ========= Punti d’interesse per WHERE =========

def interest_points(current_world: str) -> list[tuple[int,int,int,str]]:
    pts = []
    y = world_meta(current_world)["fixed_y"]
    for lm in _landmarks(current_world):
        b = lm["bbox"]
        cx = (b["x0"] + b["x1"]) // 2
        cz = (b["z0"] + b["z1"]) // 2
        pts.append((cx, y, cz, lm["name"]))
    return pts

# ========= Helpers per cmd_enter =========

def try_portal(key: str) -> str | None:
    """Se la cella corrente è un portale, restituisce la key della destinazione, altrimenti None."""
    world, x, y, z = parse_key(key)
    dest = portal_dest(world, x, z)
    if dest:
        w2, x2, y2, z2 = dest
        return make_key(w2, x2, y2, z2)
    return None

# ========= Esport util singoli =========
CELL_SIZE_METERS = DEFAULT_CELL_M

# --- PATCH: trova item vicini nel raggio (metri) -------------------------

def _cell_size_m(world: str) -> float:
    data = _load_world_json(world)
    return float(data.get("meta", {}).get("cell_size_m", 1.0))

def _dist_cells_to_bbox(cx: int, cz: int, bbox: dict) -> float:
    """Distanza (in CELLE) dal punto (cx,cz) al rettangolo bbox {x0,x1,z0,z1} (0 se dentro)."""
    dx = 0.0
    if cx < bbox["x0"]:
        dx = bbox["x0"] - cx
    elif cx > bbox["x1"]:
        dx = cx - bbox["x1"]
    dz = 0.0
    if cz < bbox["z0"]:
        dz = bbox["z0"] - cz
    elif cz > bbox["z1"]:
        dz = cz - bbox["z1"]
    return math.hypot(dx, dz)

def find_items_in_radius(world: str, cx: int, cz: int, radius_m: float):
    """
    Ritorna lista di tuple (dist_m, item_id, qty, container_name)
    cercando item nei LANDMARK che hanno 'items' nel JSON.
    Distanza = minima distanza dal bbox del landmark (0 se sei dentro).
    """
    data = _load_world_json(world)
    cs = _cell_size_m(world)
    out = []
    for lm in data.get("landmarks", []):
        items = lm.get("items", {})
        if not items:
            continue
        bbox = lm.get("bbox")
        if not bbox:
            continue
        dist_cells = _dist_cells_to_bbox(cx, cz, bbox)
        dist_m = dist_cells * cs
        if dist_m <= radius_m:
            name = lm.get("name", lm.get("id", "area"))
            for item_id, qty in items.items():
                out.append((dist_m, str(item_id), int(qty), name))
    out.sort(key=lambda t: t[0])
    return out

# --- LIVE ITEMS RADIUS (usa lo stato, non i JSON fissi) -------------------
def find_items_in_radius_live(ctx, radius_m: float):
    """
    Ritorna [(dist_m, item_id, qty, x, z)] cercando negli stati Location
    attorno al player entro raggio (in metri). Così gli item già presi spariscono.
    """
    from game.scenes import ensure_location, parse_key, CELL_SIZE_METERS
    import math

    world, cx, cy, cz = parse_key(ctx.state.location_key)
    r_cells = int(math.ceil(radius_m / CELL_SIZE_METERS))
    found = {}

    for x in range(cx - r_cells, cx + r_cells + 1):
        for z in range(cz - r_cells, cz + r_cells + 1):
            dxm = (x - cx) * CELL_SIZE_METERS
            dzm = (z - cz) * CELL_SIZE_METERS
            dist = (dxm*dxm + dzm*dzm) ** 0.5
            if dist > radius_m:
                continue
            loc = ensure_location(ctx.world, make_key(world, x, cy, z))
            if not getattr(loc, "items", None):
                continue
            for item_id, qty in loc.items.items():
                if qty <= 0:
                    continue
                key = (item_id, x, z)
                # se più celle hanno lo stesso item, mantieni la più vicina
                if key not in found or dist < found[key][0]:
                    found[key] = (dist, item_id, qty, x, z)

    return sorted(found.values(), key=lambda t: t[0])
