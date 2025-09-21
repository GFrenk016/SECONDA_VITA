"""Runtime registries for loaded content.

These act as in-memory indices for quick lookup without having to traverse
nested structures repeatedly.
"""
from __future__ import annotations
from typing import Dict, Optional
from .world import World, MicroRoom, MacroRoom

class ContentRegistry:
    def __init__(self, world: World):
        self.world = world
        self.micro_index: Dict[str, MicroRoom] = {}
        self.macro_index: Dict[str, MacroRoom] = world.macro_rooms.copy()
        for macro in world.macro_rooms.values():
            for micro in macro.micro_rooms.values():
                self.micro_index[micro.id] = micro

    def get_micro(self, micro_id: str) -> Optional[MicroRoom]:
        return self.micro_index.get(micro_id)

    def get_macro(self, macro_id: str) -> Optional[MacroRoom]:
        return self.macro_index.get(macro_id)
