"""Bootstrap utilities: load world JSON and create initial GameState + registry."""
from __future__ import annotations
import json
from pathlib import Path
from engine.core.world import build_world_from_dict, validate_world
from engine.core.registry import ContentRegistry
from engine.core.state import GameState
from engine.core.npc.loader import load_npcs_from_assets
from engine.core.npc.registry import NPCRegistry
import time
from config import get_time_scale

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "world"
WORLD_FILE = ASSETS_DIR / "world.json"

def load_world_and_state() -> tuple[ContentRegistry, GameState]:
    with WORLD_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Carica strings centralizzati
    strings_path = WORLD_FILE.parent.parent / "strings.json"
    strings_data = {}
    if strings_path.exists():
        with strings_path.open("r", encoding="utf-8") as sf:
            strings_data = json.load(sf)
    # Carica inspectables (dati estesi per azione inspect)
    inspectables_path = WORLD_FILE.parent.parent / "inspectables.json"
    inspectables_data = {}
    if inspectables_path.exists():
        with inspectables_path.open("r", encoding="utf-8") as inf:
            inspectables_data = json.load(inf)
    world = build_world_from_dict(data)
    issues = validate_world(world)
    if issues:
        # For now just print; later could raise or log in structured form.
        for i in issues:
            print(f"[WORLD WARNING] {i}")
    registry = ContentRegistry(world)
    # Attacco i testi al registry (semplice, futuro: classe dedicata)
    registry.strings = strings_data
    registry.inspectables = inspectables_data  # type: ignore[attr-defined]
    
    # Load events system
    try:
        from engine.core.events import load_events
        from engine.core.ambient_events import load_ambient_events
        load_events()
        load_ambient_events()
        print("-- Sistema eventi e eventi ambientali caricati --")
    except Exception as e:
        print(f"Warning: Failed to load events: {e}")
    
    # Load and register NPCs
    try:
        npcs = load_npcs_from_assets()
        if npcs:
            npc_registry = NPCRegistry()
            npc_registry.register_npcs(npcs)
            registry.npc_registry = npc_registry
            print(f"-- Caricati {len(npcs)} NPC --")
    except Exception as e:
        print(f"Warning: Failed to load NPCs: {e}")
        registry.npc_registry = None
    
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
    # Determina offset iniziale minuti in base alla fascia daytime randomizzata
    if daytime == "mattina":
        start_minutes = 6*60
    elif daytime == "giorno":
        start_minutes = 12*60
    elif daytime == "sera":
        start_minutes = 18*60
    else:  # notte
        # scegli una notte interna (22:00)
        start_minutes = 22*60
    # Recupera scala tempo centralizzata
    env_scale = get_time_scale()

    state = GameState(
        world_id=world.id,
        current_macro=first_macro.id,
        current_micro=first_micro.id,
        climate=climate,
        weather=weather,
        daytime=daytime,
        manual_offset_minutes=start_minutes,
        time_scale=env_scale  # scala configurabile
    )
    # Calcola i minuti correnti immediatamente (real_start_ts = now)
    now = time.time()
    total_minutes = state.recompute_from_real(now)
    
    # Update NPC states if available
    if registry.npc_registry:
        registry.npc_registry.update_npc_states(total_minutes)
        # Store reference for ongoing updates
        state._npc_registry_ref = registry.npc_registry
    
    return registry, state
