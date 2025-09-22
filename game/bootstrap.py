"""Bootstrap utilities: load world JSON and create initial GameState + registry."""
from __future__ import annotations
import json
from pathlib import Path
from engine.core.world import build_world_from_dict, validate_world
from engine.core.registry import ContentRegistry
from engine.core.state import GameState

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "world"
WORLD_FILE = ASSETS_DIR / "world.json"

def load_world_and_state() -> tuple[ContentRegistry, GameState]:
    with WORLD_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    world = build_world_from_dict(data)
    issues = validate_world(world)
    if issues:
        # For now just print; later could raise or log in structured form.
        for i in issues:
            print(f"[WORLD WARNING] {i}")
    registry = ContentRegistry(world)
    # Start position: first macro + first micro in definition order.
    first_macro = next(iter(world.macro_rooms.values()))
    first_micro = next(iter(first_macro.micro_rooms.values()))
    # Inizializzazione realistica di clima, meteo e ora del giorno
    import random
    daytime = random.choice(["mattina", "giorno", "sera", "notte"])
    climate = "temperato"  # Potresti variare in base all'area in futuro
    # Probabilità di meteo in base al clima
    if climate == "temperato":
        weather = random.choices(["sereno", "nuvoloso", "pioggia", "nebbia"], weights=[0.5, 0.3, 0.15, 0.05])[0]
    elif climate == "umido":
        weather = random.choices(["sereno", "nuvoloso", "pioggia", "nebbia"], weights=[0.2, 0.3, 0.4, 0.1])[0]
    else:
        weather = "sereno"
    state = GameState(
        world_id=world.id,
        current_macro=first_macro.id,
        current_micro=first_micro.id,
        climate=climate,
        weather=weather,
        daytime=daytime
    )
    return registry, state
