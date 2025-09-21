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
    micro = registry.get_micro(state.current_micro)
    if micro is None:
        raise ActionError(f"Location not found: {state.current_micro}")
    lines: List[str] = [micro.short]
    # Future: differentiate first time vs subsequent look, integrate flags.
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
