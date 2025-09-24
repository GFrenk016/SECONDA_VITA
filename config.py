"""Configurazione centrale per Seconda Vita.

Qui centralizziamo i parametri modificabili del gioco (velocità del tempo,
QTE, finestre, inattività, tick CLI, ecc.). Tutti i valori hanno un default
sensato e possono essere sovrascritti via variabili d'ambiente.
"""
from __future__ import annotations
import os
import string

def _get_int_env(name: str, default: int, minval: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        v = int(raw)
        if minval is not None and v < minval:
            return default
        return v
    except ValueError:
        return default


def _get_float_env(name: str, default: float, minval: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        v = float(raw)
        if minval is not None and v < minval:
            return default
        return v
    except ValueError:
        return default


def _get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    val = raw.strip().lower()
    return val in {"1", "true", "yes", "on"}


# ---------------- Tempo simulato ----------------
# Valore di default (minuti simulati che passano per ogni secondo reale)
DEFAULT_TIME_SCALE: float = 0.25

# Nome variabile d'ambiente per override
ENV_TIME_SCALE = "SV_TIME_SCALE"


def get_time_scale() -> float:
    """Ritorna la time scale da usare.

    Ordine di precedenza:
    1. Variabile d'ambiente SV_TIME_SCALE (se valida > 0)
    2. DEFAULT_TIME_SCALE
    """
    raw = os.getenv(ENV_TIME_SCALE)
    if raw is None:
        return DEFAULT_TIME_SCALE
    try:
        val = float(raw)
        if val <= 0:
            raise ValueError
        return val
    except ValueError:
        # fallback silenzioso (potremmo loggare un warning se necessario)
        return DEFAULT_TIME_SCALE


# ---------------- QTE & Combattimento ----------------
# QTE complessi (alfanumerici 3-5) abilitati di default?
DEFAULT_COMPLEX_QTE_ENABLED: bool = _get_bool_env("SV_COMPLEX_QTE", False)

# Lunghezza codice QTE (min/max)
QTE_CODE_LENGTH_MIN: int = _get_int_env("SV_QTE_LEN_MIN", 3, minval=1)
QTE_CODE_LENGTH_MAX: int = _get_int_env("SV_QTE_LEN_MAX", 5, minval=QTE_CODE_LENGTH_MIN)

# Alfabeto per i codici QTE
QTE_CODE_ALPHABET: str = os.getenv("SV_QTE_ALPHABET", string.ascii_uppercase + string.digits)

# Finestra predefinita QTE difensivo (minuti simulati)
DEFAULT_DEFENSIVE_QTE_WINDOW_MIN: int = _get_int_env("SV_QTE_DEF_WINDOW_MIN", 4, minval=1)

# Finestra predefinita QTE offensivo (minuti simulati)
DEFAULT_OFFENSIVE_QTE_WINDOW_MIN: int = _get_int_env("SV_QTE_OFF_WINDOW_MIN", 4, minval=1)

# Secondi reali di inattività per forzare l'attacco nemico
INACTIVITY_ATTACK_SECONDS: int = _get_int_env("SV_INACTIVITY_SEC", 5, minval=1)

# Minimo cooldown (minuti simulati) per l'attacco ad area
MIN_ATTACK_ALL_COOLDOWN_MINUTES: int = _get_int_env("SV_ATTACK_ALL_COOLDOWN_MIN", 2, minval=1)


# ---------------- CLI realtime ----------------
# Intervallo di tick (secondi) del thread di background nel CLI
CLI_TICK_INTERVAL_SECONDS: float = _get_float_env("SV_TICK_INTERVAL_SEC", 0.2, minval=0.05)


__all__ = [
    # Tempo
    "DEFAULT_TIME_SCALE", "get_time_scale", "ENV_TIME_SCALE",
    # QTE/Combat
    "DEFAULT_COMPLEX_QTE_ENABLED", "QTE_CODE_LENGTH_MIN", "QTE_CODE_LENGTH_MAX", "QTE_CODE_ALPHABET",
    "DEFAULT_DEFENSIVE_QTE_WINDOW_MIN", "DEFAULT_OFFENSIVE_QTE_WINDOW_MIN",
    "INACTIVITY_ATTACK_SECONDS", "MIN_ATTACK_ALL_COOLDOWN_MINUTES",
    # CLI
    "CLI_TICK_INTERVAL_SECONDS",
    # Ollama
    "get_ollama_enabled", "get_ollama_base_url", "get_ollama_model",
    "get_ollama_timeout", "get_ollama_temperature", "get_ollama_max_tokens",
]


# ---------------- Ollama AI (Dialoghi NPC) ----------------

def get_ollama_enabled() -> bool:
    """Abilita l'integrazione con Ollama (default: False). Var: SV_OLLAMA_ENABLED."""
    return _get_bool_env("SV_OLLAMA_ENABLED", False)


def get_ollama_base_url() -> str:
    """Base URL del server Ollama. Var: SV_OLLAMA_BASE_URL (default http://localhost:11434)."""
    return os.getenv("SV_OLLAMA_BASE_URL", "http://localhost:11434").strip()


def get_ollama_model() -> str:
    """Nome modello Ollama da usare (es. 'llama3.2:3b'). Var: SV_OLLAMA_MODEL."""
    return os.getenv("SV_OLLAMA_MODEL", "llama3.2:3b").strip()


def get_ollama_timeout() -> float:
    """Timeout richieste HTTP in secondi. Var: SV_OLLAMA_TIMEOUT (default 10.0)."""
    return _get_float_env("SV_OLLAMA_TIMEOUT", 10.0, minval=1.0)


def get_ollama_temperature() -> float:
    """Temperatura sampling modello. Var: SV_OLLAMA_TEMPERATURE (default 0.7)."""
    val = _get_float_env("SV_OLLAMA_TEMPERATURE", 0.7, minval=0.0)
    return max(0.0, min(2.0, val))


def get_ollama_max_tokens() -> int:
    """Max token output. Var: SV_OLLAMA_MAX_TOKENS (default 150)."""
    return _get_int_env("SV_OLLAMA_MAX_TOKENS", 150, minval=16)
