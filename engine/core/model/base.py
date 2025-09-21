"""Data model definitions for the world hierarchy (Seconda Vita).

This module only contains pure dataclasses without loading or validation logic.
They are intended to be immutable structural representations of world content.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

__all__ = [
    "ConditionRef",
    "Exit",
    "InteractableRef",
    "MicroRoom",
    "MacroRoom",
    "World",
]

@dataclass(frozen=True)
class ConditionRef:
    type: str
    key: str
    value: Optional[Any] = None
    negate: bool = False

@dataclass(frozen=True)
class Exit:
    direction: str
    target_micro: str
    target_macro: Optional[str] = None
    locked: bool = False
    lock_flag: Optional[str] = None
    description: Optional[str] = None
    conditions: List[ConditionRef] = field(default_factory=list)

@dataclass(frozen=True)
class InteractableRef:
    id: str
    alias: Optional[str] = None
    visible_flag: Optional[str] = None

@dataclass(frozen=True)
class MicroRoom:
    id: str
    name: str
    short: str
    description: str
    exits: List[Exit]
    tags: List[str] = field(default_factory=list)
    on_enter_events: List[str] = field(default_factory=list)
    interactables: List[InteractableRef] = field(default_factory=list)
    props: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class MacroRoom:
    id: str
    name: str
    description: str
    micro_rooms: Dict[str, MicroRoom]

@dataclass(frozen=True)
class World:
    id: str
    name: str
    description: str
    macro_rooms: Dict[str, MacroRoom]

    def find_micro(self, macro_id: str, micro_id: str) -> MicroRoom:
        return self.macro_rooms[macro_id].micro_rooms[micro_id]

    def all_micro_rooms(self) -> List[MicroRoom]:
        rooms: List[MicroRoom] = []
        for macro in self.macro_rooms.values():
            rooms.extend(macro.micro_rooms.values())
        return rooms
