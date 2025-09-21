"""Game state container for runtime mutable data.

Separated from static world definition. This will later be serialized by
persistence utilities (not yet implemented).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set

@dataclass
class GameState:
    world_id: str
    current_macro: str
    current_micro: str
    flags: Dict[str, object] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    fired_events: Set[str] = field(default_factory=set)
    timeline: List[Dict[str, object]] = field(default_factory=list)
    version: int = 1

    def location_key(self) -> str:
        return f"{self.current_macro}:{self.current_micro}"
