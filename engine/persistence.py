import json
import os
import time
import re
from typing import Optional, List, Dict

SAVE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "saves"))

def ensure_dirs():
    os.makedirs(SAVE_DIR, exist_ok=True)

def _save_path(name: str) -> str:
    ensure_dirs()
    safe = f"{name}.json" if not name.endswith(".json") else name
    return os.path.join(SAVE_DIR, safe)

def save_state(name: str, payload: dict) -> str:
    """Crea/sovrascrive un salvataggio."""
    path = _save_path(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path

def load_state(name: str) -> Optional[dict]:
    """Carica un salvataggio, None se non esiste."""
    path = _save_path(name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def delete_state(name: str) -> bool:
    """Elimina uno specifico salvataggio. Ritorna True se eliminato."""
    path = _save_path(name)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False

def list_saves() -> List[Dict[str, str | int | float]]:
    """
    Restituisce metadati dei salvataggi ordinati per mtime decrescente.
    """
    ensure_dirs()
    out: List[Dict[str, str | int | float]] = []
    for fn in os.listdir(SAVE_DIR):
        if not fn.endswith(".json"):
            continue
        full = os.path.join(SAVE_DIR, fn)
        try:
            st = os.stat(full)
            name = fn[:-5]  # senza .json
            mtime = st.st_mtime
            out.append({
                "name": name,
                "size": st.st_size,
                "mtime": mtime,
                "mtime_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
            })
        except OSError:
            continue
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out

def next_save_name(prefix: str = "save") -> str:
    """
    Trova il prossimo nome libero: save1, save2, ...
    Cerca file esistenti che matchano ^save\\d+\\.json
    """
    ensure_dirs()
    pat = re.compile(rf"^{re.escape(prefix)}(\d+)\.json$")
    max_n = 0
    for fn in os.listdir(SAVE_DIR):
        m = pat.match(fn)
        if m:
            try:
                n = int(m.group(1))
                if n > max_n:
                    max_n = n
            except ValueError:
                continue
    return f"{prefix}{max_n + 1}"
