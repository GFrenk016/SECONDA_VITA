"""Game state container for runtime mutable data.

Separated from static world definition. This will later be serialized by
persistence utilities (not yet implemented).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any

@dataclass
class GameState:
    world_id: str
    current_macro: str
    current_micro: str
    flags: Dict[str, object] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)  # Legacy inventory - kept for compatibility
    fired_events: Set[str] = field(default_factory=set)
    timeline: List[Dict[str, object]] = field(default_factory=list)
    version: int = 3  # Updated version for new inventory/stats system
    
    # New inventory and stats system
    player_stats: Optional[Dict[str, Any]] = None  # Will be initialized as PlayerStats data
    player_inventory: Optional[Dict[str, Any]] = None  # Will be initialized as Inventory data
    player_equipment: Optional[Dict[str, Any]] = None  # Will be initialized as Equipment data
    
    # Container states (location -> container_id -> contents)
    container_states: Dict[str, Dict[str, List[Dict[str, Any]]]] = field(default_factory=dict)
    
    # NPC conversation state
    active_conversation: Optional[Dict[str, Any]] = None
    
    # Resource node cooldowns (location -> node_id -> cooldown_end_tick)
    resource_cooldowns: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # World element states
    world_element_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
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
    # Tracciamento oggetti visibili per micro stanza (per evidenziare nuovi elementi apparsi)
    micro_last_visible: Dict[str, Set[str]] = field(default_factory=dict)
    # --- Ambient Snippet Rate Limiting ---
    # Per evitare spam di linee atmosferiche ad ogni azione, imponiamo un
    # intervallo minimo (in minuti simulati) tra due emissioni successive.
    # Se non è trascorso almeno ambient_min_gap_minutes dal precedente
    # snippet, _ambient_line() restituisce None.
    ambient_min_gap_minutes: int = 8
    # total_minutes dell'ultima emissione; inizializzato a valore negativo per
    # consentire un primo snippet immediato.
    last_ambient_emit_total: int = -10000
    # --- TEST / deterministic support ---
    # Per alcuni test è utile forzare la prossima emissione ambientale scegliendo
    # una chiave specifica di _AMBIENT_SNIPPETS oppure un testo esatto. I test
    # possono impostare uno di questi attributi e la funzione _ambient_line li
    # consumerà e poi azzererà per non influenzare emissioni successive.
    force_ambient_key: str | None = None
    force_ambient_exact: str | None = None
    # --- Combat core (fase 1: singolo nemico, arma singola) ---
    player_hp: int = 10
    player_max_hp: int = 10
    player_weapon_id: str | None = None  # id arma equipaggiata (per ora una sola)
    # Struttura sessione combat attiva, None se non in combattimento.
    # Esempio:
    # combat_session = {
    #   'enemy_id': 'walker',
    #   'enemy_name': 'Walker',
    #   'enemy_hp': 6,
    #   'enemy_max_hp': 6,
    #   'phase': 'player' | 'qte' | 'enemy' | 'ended',
    #   'qte': { 'prompt': 'Premi A', 'expected': 'a', 'deadline_total': <minuti_totali_scadenza> },
    # }
    combat_session: dict | None = None

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
        
        # Update NPC states if available
        if hasattr(self, '_npc_registry_ref') and self._npc_registry_ref:
            self._npc_registry_ref.update_npc_states(total_minutes)
        
        # Restituisce anche il totale minuti per uso esterno se necessario
        return total_minutes

    def set_time_scale(self, new_scale: float):
        """Aggiorna dinamicamente la velocità del tempo (minuti di gioco per secondo reale).

        Mantiene invariato l'orario simulato corrente ricalibrando ``real_start_ts``.
        Esempio: se passi da 1.0 (1s=1min) a 0.25, il tempo scorrerà 4 volte più lentamente.

        new_scale: deve essere > 0.
        """
        if new_scale <= 0:
            raise ValueError("time_scale deve essere > 0")
        # Calcola minuti simulati totali attuali usando la scala precedente
        now_ts = __import__("time").time()
        current_total_minutes = self.recompute_from_real(now_ts)
        # Aggiorna la scala
        self.time_scale = new_scale
        # Ricalibra l'ancora reale affinché recompute_from_real mantenga i minuti correnti
        # total_minutes = int((now - real_start_ts)*scale) + offset  ~= current_total_minutes
        # => real_start_ts = now - (current_total_minutes - offset)/scale
        # Usiamo float preciso (niente int) per minimizzare drift.
        simulated_without_offset = current_total_minutes - self.manual_offset_minutes
        self.real_start_ts = now_ts - (simulated_without_offset / self.time_scale)
        # Forza un recompute per aggiornare campi derivati coerenti
        self.recompute_from_real(now_ts)

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
