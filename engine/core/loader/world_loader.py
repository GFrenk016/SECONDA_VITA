"""World loading and validation utilities.

Separates construction logic from raw JSON (dict) into model dataclasses.
No I/O performed here; caller is responsible for reading JSON from disk.
"""
from __future__ import annotations
from typing import Dict, Any, List
from ..model.base import (
    World,
    MacroRoom,
    MicroRoom,
    Exit,
    ConditionRef,
    InteractableRef,
)

__all__ = ["build_world_from_dict", "validate_world"]

def build_world_from_dict(data: Dict[str, Any]) -> World:
    macro_map: Dict[str, MacroRoom] = {}
    for m in data.get("macro_rooms", []):
        micro_map: Dict[str, MicroRoom] = {}
        for r in m.get("micro_rooms", []):
            exits = [
                Exit(
                    direction=e["direction"],
                    target_micro=e["target_micro"],
                    target_macro=e.get("target_macro"),
                    locked=e.get("locked", False),
                    lock_flag=e.get("lock_flag"),
                    description=e.get("description"),
                    conditions=[
                        ConditionRef(
                            type=c["type"],
                            key=c["key"],
                            value=c.get("value"),
                            negate=c.get("negate", False),
                        )
                        for c in e.get("conditions", [])
                    ],
                )
                for e in r.get("exits", [])
            ]
            interactables = [
                InteractableRef(
                    id=i["id"],
                    alias=i.get("alias"),
                    visible_flag=i.get("visible_flag"),
                )
                for i in r.get("interactables", [])
            ]
            micro = MicroRoom(
                id=r["id"],
                name=r["name"],
                short=r["short"],
                description=r["description"],
                exits=exits,
                tags=r.get("tags", []),
                on_enter_events=r.get("on_enter_events", []),
                interactables=interactables,
                props=r.get("props", {}),
            )
            micro_map[micro.id] = micro
        macro_room = MacroRoom(
            id=m["id"],
            name=m["name"],
            description=m.get("description", ""),
            micro_rooms=micro_map,
        )
        macro_map[macro_room.id] = macro_room
    world = World(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        macro_rooms=macro_map,
    )
    return world

def validate_world(world: World) -> List[str]:
    issues: List[str] = []
    seen_micro: Dict[str, str] = {}
    for macro in world.macro_rooms.values():
        for micro_id in macro.micro_rooms:
            if micro_id in seen_micro:
                issues.append(
                    f"Duplicate micro id '{micro_id}' in macro '{macro.id}' (already in '{seen_micro[micro_id]}')"
                )
            else:
                seen_micro[micro_id] = macro.id
    for macro in world.macro_rooms.values():
        for micro in macro.micro_rooms.values():
            for ex in micro.exits:
                if not ex.direction:
                    issues.append(f"Micro '{micro.id}' has exit with empty direction")
                target_macro_id = ex.target_macro or macro.id
                if target_macro_id not in world.macro_rooms:
                    issues.append(
                        f"Exit from '{micro.id}' points to missing macro '{target_macro_id}'"
                    )
                    continue
                target_macro = world.macro_rooms[target_macro_id]
                if ex.target_micro not in target_macro.micro_rooms:
                    issues.append(
                        f"Exit from '{micro.id}' points to missing micro '{ex.target_micro}' (macro '{target_macro_id}')"
                    )
    return issues
