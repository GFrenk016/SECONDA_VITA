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
        # Dizionario testi (iniettato da bootstrap)
        self.strings: dict = {}
        # NPC registry (iniettato da bootstrap se disponibile)
        self.npc_registry = None

    def get_micro(self, micro_id: str) -> Optional[MicroRoom]:
        return self.micro_index.get(micro_id)

    def get_macro(self, macro_id: str) -> Optional[MacroRoom]:
        return self.macro_index.get(macro_id)

    # --- Accesso testi centralizzati ---
    def get_object_name(self, obj_id: str) -> str:
        return self.strings.get("oggetti", {}).get(obj_id, {}).get("nome", obj_id)

    def get_object_description(self, obj_id: str) -> str:
        return self.strings.get("oggetti", {}).get(obj_id, {}).get("descrizione", "")

    def get_area_name(self, micro_id: str) -> str:
        return self.strings.get("aree", {}).get(micro_id, {}).get("nome", micro_id)

    def get_area_description(self, micro_id: str) -> str:
        return self.strings.get("aree", {}).get(micro_id, {}).get("descrizione", "")

    def compose_area_description(self, micro_id: str, daytime: str, weather: str) -> str:
        base = self.get_area_description(micro_id)
        area_data = self.strings.get("aree", {}).get(micro_id, {})
        varianti = area_data.get("varianti", {})
        seg = []
        # Priorità: variante meteo + variante fascia oraria (se presenti)
        if weather in varianti:
            seg.append(varianti[weather])
        if daytime in varianti:
            seg.append(varianti[daytime])
        if seg:
            return base + " " + " ".join(seg)
        return base
