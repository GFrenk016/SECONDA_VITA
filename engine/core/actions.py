"""Core player actions: look() and go().

Returns ActionResult dicts with keys:
- lines: List[str] narrative lines to display
- hints: List[str] proximity hints (exits summary for now)
- events_triggered: list (placeholder; events system not yet implemented)
- changes: dict summarizing state changes
"""
from __future__ import annotations
from typing import Dict, List
from .state import GameState
from .registry import ContentRegistry
from .world import MicroRoom, Exit

class ActionError(Exception):
    pass

def look(state: GameState, registry: ContentRegistry) -> Dict[str, object]:
    # Avanza ora/meteo prima di mostrare la descrizione
    _advance_time_and_weather(state)
    micro = registry.get_micro(state.current_micro)
    if micro is None:
        raise ActionError(f"Location not found: {state.current_micro}")
    lines: List[str] = [f"[{state.daytime.title()} | {state.weather.title()} | {state.climate.title()}]", micro.short]
    # Mostra oggetti interattivi visibili in base a meteo/ora/flag
    visible_objs = []
    for obj in micro.interactables:
        # visibilità condizionata da flag/meteo/ora
        if obj.visible_flag:
            if obj.visible_flag == "is_daytime" and state.daytime not in ("mattina", "giorno"):
                continue
            if obj.visible_flag == "is_morning" and state.daytime != "mattina":
                continue
            if obj.visible_flag == "is_rainy" and state.weather != "pioggia":
                continue
            if obj.visible_flag == "is_spring" and state.climate != "umido":
                continue
            if obj.visible_flag == "has_examined_marker" and not state.flags.get("has_examined_marker"):
                continue
        visible_objs.append(obj.id)
    if visible_objs:
        lines.append("Qui noti: " + ", ".join(visible_objs))
    exits_desc = []
    for ex in micro.exits:
        exits_desc.append(f"{ex.direction}: {registry.get_micro(ex.target_micro).name if registry.get_micro(ex.target_micro) else ex.target_micro}")
    if exits_desc:
        lines.append("Uscite: " + ", ".join(exits_desc))
    return {
        "lines": lines,
        "hints": exits_desc,
        "events_triggered": [],
        "changes": {}
    }

def go(state: GameState, registry: ContentRegistry, direction: str) -> Dict[str, object]:
    direction = direction.lower().strip()
    current = registry.get_micro(state.current_micro)
    if current is None:
        raise ActionError(f"Current micro room missing: {state.current_micro}")
    target_exit: Exit | None = None
    for ex in current.exits:
        if ex.direction.lower() == direction:
            target_exit = ex
            break
    if target_exit is None:
        raise ActionError(f"Nessuna uscita '{direction}' da qui.")
    if target_exit.locked and not (target_exit.lock_flag and state.flags.get(target_exit.lock_flag)):
        raise ActionError("L'uscita è bloccata.")
    # Update location (macro doesn't change in this initial slice)
    state.current_micro = target_exit.target_micro
    # Build result narrative via look after move
    look_result = look(state, registry)
    look_result["changes"] = {"location": state.location_key()}
    return look_result

# --- Logica di avanzamento tempo/meteo ---
def _advance_time_and_weather(state: GameState):
    # Avanza ora del giorno
    order = ["mattina", "giorno", "sera", "notte"]
    idx = order.index(state.daytime) if state.daytime in order else 0
    state.daytime = order[(idx + 1) % len(order)]
    # Cambia meteo con probabilità influenzata dal clima
    import random
    if state.climate == "temperato":
        weights = [0.5, 0.3, 0.15, 0.05]
    elif state.climate == "umido":
        weights = [0.2, 0.3, 0.4, 0.1]
    elif state.climate == "freddo":
        weights = [0.3, 0.3, 0.1, 0.3]  # più nebbia
    else:
        weights = [0.6, 0.3, 0.05, 0.05]
    meteo = random.choices(["sereno", "nuvoloso", "pioggia", "nebbia"], weights=weights)[0]
    # Piccola probabilità di cambiare clima dopo pioggia prolungata
    if state.weather == "pioggia" and meteo == "pioggia" and random.random() < 0.1:
        state.climate = "umido"
    state.weather = meteo
