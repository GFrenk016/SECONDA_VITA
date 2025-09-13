from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Player:
    name: str = "Frank"
    inventory: Dict[str, int] = field(default_factory=dict)

@dataclass
class Location:
    key: str
    name: str
    desc: str
    exits: Dict[str, str]  # direction -> location key
    items: Dict[str, int] = field(default_factory=dict)  # item -> qty

@dataclass
class GameState:
    tick: int = 0
    player: Player = field(default_factory=Player)
    location_key: str = "foresta"
    flags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "player": {"name": self.player.name, "inventory": self.player.inventory},
            "location_key": self.location_key,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        st = cls()
        st.tick = data.get("tick", 0)
        p = data.get("player", {})
        st.player.name = p.get("name", "Frank")
        st.player.inventory = p.get("inventory", {})
        st.location_key = data.get("location_key", "foresta")
        st.flags = data.get("flags", {})
        return st
