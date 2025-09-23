"""Load dynamic combat content: weapons and mobs.

Scans assets/weapons/*.json and assets/mobs/*.json returning dictionaries.
Each JSON must contain an 'id' field.
"""
from __future__ import annotations
import json, os
from typing import Dict, Any, Tuple

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'assets')
WEAPONS_DIR = os.path.join(ASSETS_DIR, 'weapons')
MOBS_DIR = os.path.join(ASSETS_DIR, 'mobs')

def _load_dir(path: str) -> Dict[str, dict]:
    data: Dict[str, dict] = {}
    if not os.path.isdir(path):
        return data
    for fname in os.listdir(path):
        if not fname.endswith('.json'):
            continue
        full = os.path.join(path, fname)
        try:
            with open(full, 'r', encoding='utf-8') as f:
                obj = json.load(f)
            _id = obj.get('id')
            if not _id:
                continue
            data[_id] = obj
        except Exception:
            # Skip malformed
            continue
    return data

def load_combat_content() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    weapons = _load_dir(WEAPONS_DIR)
    mobs = _load_dir(MOBS_DIR)
    return weapons, mobs

__all__ = ['load_combat_content']
