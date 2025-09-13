import json, os
from typing import Optional

SAVE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "saves"))

def ensure_dirs():
    os.makedirs(SAVE_DIR, exist_ok=True)

def save_state(name: str, payload: dict) -> str:
    ensure_dirs()
    path = os.path.join(SAVE_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path

def load_state(name: str) -> Optional[dict]:
    path = os.path.join(SAVE_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
