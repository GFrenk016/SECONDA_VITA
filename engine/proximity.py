from typing import List, Dict, Tuple
from engine.geo import Position, distance_m
from config import SETTINGS

def nearby_pois(player_pos: Position, pois: List[Dict], radius_m: float | None = None
               ) -> List[Tuple[float, Dict]]:
    r = radius_m if radius_m is not None else SETTINGS["proximity_radius_m"]
    found: List[Tuple[float, Dict]] = []
    for p in pois:
        d = distance_m(player_pos, p["pos"])
        if d <= r:
            found.append((d, p))
    found.sort(key=lambda t: t[0])
    return found
