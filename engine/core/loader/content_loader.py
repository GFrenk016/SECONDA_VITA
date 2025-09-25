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

def _load_dir(path: str, recursive: bool = False) -> Dict[str, dict]:
    data: Dict[str, dict] = {}
    if not os.path.isdir(path):
        return data
    
    def _process_json_file(file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                obj = json.load(f)
            # Support either a single-item JSON with 'id',
            # or a collection file (list of items),
            # or a dict of categories -> list of items (e.g., ranged, melee...).
            def _add_item(w: dict):
                _id = w.get('id')
                if _id:
                    data[_id] = w

            if isinstance(obj, dict) and 'id' in obj:
                _add_item(obj)
            elif isinstance(obj, list):
                for w in obj:
                    if isinstance(w, dict):
                        _add_item(w)
            elif isinstance(obj, dict):
                # Try category containers e.g. {"ranged":[...], "melee":[...]}
                for v in obj.values():
                    if isinstance(v, list):
                        for w in v:
                            if isinstance(w, dict):
                                _add_item(w)
        except Exception:
            # Skip malformed
            pass
    
    # Process files in current directory
    for fname in os.listdir(path):
        full_path = os.path.join(path, fname)
        
        if os.path.isfile(full_path) and fname.endswith('.json'):
            _process_json_file(full_path)
        elif recursive and os.path.isdir(full_path):
            # Recursively load from subdirectories
            subdir_data = _load_dir(full_path, recursive=True)
            data.update(subdir_data)
    
    return data

def _load_single_file(file_path: str) -> Dict[str, Any]:
    """Load a single JSON file and return the object."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def load_combat_content() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    weapons = _load_dir(WEAPONS_DIR)
    mobs = _load_dir(MOBS_DIR, recursive=True)  # Enable recursive loading for new mob structure
    return weapons, mobs

def load_mob_by_path(relative_path: str) -> Dict[str, Any]:
    """Load a single mob file by relative path from project root."""
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), relative_path)
    return _load_single_file(full_path)

__all__ = ['load_combat_content', 'load_mob_by_path']
