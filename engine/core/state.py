"""Game state container for runtime mutable data.

Separated from static world definition. This will later be serialized by
persistence utilities (not yet implemented).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set

@dataclass
class GameState:
    world_id: str
    current_macro: str
    current_micro: str
    flags: Dict[str, object] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    fired_events: Set[str] = field(default_factory=set)
    timeline: List[Dict[str, object]] = field(default_factory=list)
    version: int = 1
    # Nuovi campi per profondità ambientale
    weather: str = "sereno"  # es: sereno, pioggia, nebbia
    climate: str = "temperato"  # es: temperato, caldo, freddo, umido
    daytime: str = "giorno"  # es: mattina, giorno, sera, notte
    # Clock simulato (minuti trascorsi dal giorno 0, derivati dal tempo reale). 0 = 06:00 (start-of-day offset)
    time_minutes: int = 0  # mantenuto per retrocompatibilità ma sarà calcolato
    day_count: int = 0
    last_weather_eval_minute: int = 0
    # Tracciamento assoluto (in minuti simulati) dell'ultima valutazione meteo
    last_weather_eval_total: int = 0
    # Realtime mapping
    real_start_ts: float | None = None  # epoch alla partenza
    time_scale: float = 1.0  # minuti di gioco per secondo reale (default: 1s -> 1min)
    manual_offset_minutes: int = 6 * 60  # partiamo alle 06:00
    last_computed_real_seconds: float = 0.0
    visited_micro: Set[str] = field(default_factory=set)
    visit_counts: Dict[str, int] = field(default_factory=dict)
    micro_last_signature: Dict[str, str] = field(default_factory=dict)  # firma (daytime|weather)
    last_ambient_line: str | None = None

    def recompute_from_real(self, now_ts: float):
        if self.real_start_ts is None:
            self.real_start_ts = now_ts
        elapsed_sec = now_ts - self.real_start_ts
        self.last_computed_real_seconds = elapsed_sec
        # Minuti simulati totali dall'inizio (offset incluso)
        total_minutes = int(elapsed_sec * self.time_scale) + self.manual_offset_minutes
        self.day_count = total_minutes // (24 * 60)
        self.time_minutes = total_minutes % (24 * 60)
        self._recompute_daytime()
        # Restituisce anche il totale minuti per uso esterno se necessario
        return total_minutes

    # advance_minutes non serve più in realtime

    def _recompute_daytime(self):
        # 06:00-11:59 mattina, 12:00-17:59 giorno, 18:00-21:59 sera, 22:00-05:59 notte
        m = self.time_minutes
        if 6*60 <= m < 12*60:
            self.daytime = "mattina"
        elif 12*60 <= m < 18*60:
            self.daytime = "giorno"
        elif 18*60 <= m < 22*60:
            self.daytime = "sera"
        else:
            self.daytime = "notte"

    def time_string(self) -> str:
        h = (self.time_minutes // 60) % 24
        mi = self.time_minutes % 60
        return f"{h:02d}:{mi:02d}"

    def location_key(self) -> str:
        return f"{self.current_macro}:{self.current_micro}"
