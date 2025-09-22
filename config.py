"""Configurazione centrale per Seconda Vita.

Qui puoi definire costanti e funzioni di utilità per parametri globali
come velocità del tempo, feature flags, ecc.

Per il momento gestiamo solo la scala del tempo.
"""
from __future__ import annotations
import os

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

__all__ = ["DEFAULT_TIME_SCALE", "get_time_scale", "ENV_TIME_SCALE"]
