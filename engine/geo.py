from dataclasses import dataclass
from math import hypot

@dataclass
class Position:
    x: float  # metri
    y: float  # metri

def distance_m(a: "Position", b: "Position") -> float:
    return hypot(a.x - b.x, a.y - b.y)
