from __future__ import annotations
import json, os
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple, List

ASSETS_DIR = os.path.join("assets")
WEAPS_DIR  = os.path.join(ASSETS_DIR, "weapons")
MOBS_DIR   = os.path.join(ASSETS_DIR, "mobs")

def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@lru_cache(maxsize=None)
def load_melee_weapons() -> Dict[str, Dict[str, Any]]:
    """
    Ritorna dict {weapon_id: weapon_data} da assets/weapons/melee.json
    """
    path = os.path.join(WEAPS_DIR, "melee.json")
    data = _load_json(path)
    out = {}
    for w in data.get("weapons", []):
        out[w["id"]] = w
    return out

@lru_cache(maxsize=None)
def load_walkers() -> Dict[str, Dict[str, Any]]:
    """
    Ritorna dict {mob_id: mob_data} da assets/mobs/walkers.json
    """
    path = os.path.join(MOBS_DIR, "walkers.json")
    data = _load_json(path)
    out = {}
    for m in data.get("mobs", []):
        out[m["id"]] = m
    return out

def pick_best_melee_from_inventory(inv: Dict[str, int]) -> Tuple[str, Dict[str, Any]]:
    """
    Sceglie l'arma corpo a corpo 'migliore' nell'inventario:
    criterio semplice: max(damage), tie-break: min(energy_cost).
    Se non c'è nulla, fallback ai 'pugni'.
    """
    melee = load_melee_weapons()
    candidates: List[Tuple[str, Dict[str, Any]]] = []
    for wid, qty in inv.items():
        if qty <= 0: 
            continue
        if wid in melee:
            candidates.append((wid, melee[wid]))
    if not candidates:
        return ("fists", {"id":"fists","name":"Pugni","desc":"Niente in mano.","damage":1,"energy_cost":0.5,"hit_bonus":-0.10,"crit_chance":0.0,"durability":9999})
    # sort by (-damage, +energy_cost)
    candidates.sort(key=lambda t: (-t[1].get("damage",0), t[1].get("energy_cost",1e9)))
    return candidates[0]
