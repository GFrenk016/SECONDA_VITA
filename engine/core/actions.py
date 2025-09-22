"""Core player actions: look() and go().

Returns ActionResult dicts with keys:
- lines: List[str] narrative lines to display
- hints: List[str] proximity hints (exits summary for now)
- events_triggered: list (placeholder; events system not yet implemented)
- changes: dict summarizing state changes
"""
from __future__ import annotations
from typing import Dict, List
from .state import GameState
from .registry import ContentRegistry
from .world import MicroRoom, Exit
import textwrap
import random
import time

def _wrap(text: str, width: int = 78) -> list[str]:
    blocks = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            blocks.append("")
            continue
        blocks.extend(textwrap.wrap(paragraph, width=width))
    return blocks

_AMBIENT_SNIPPETS = {
    "mattina": [
        "Una corrente d’aria fresca porta l’odore dell’erba bagnata.",
        "La luce obliqua rivela dettagli che a mezzogiorno svaniranno.",
    ],
    "giorno": [
        "Un ronzio diffuso di insetti scandisce la quiete.",
        "Una foglia cade roteando lentamente.",
    ],
    "sera": [
        "Toni ambrati tingono le superfici esposte.",
        "Un richiamo lontano viene inghiottito dal bosco.",
    ],
    "notte": [
        "Una luminescenza appena percettibile pulsa tra il fogliame.",
        "Il bosco sembra trattenere ogni suono superfluo.",
    ],
    "pioggia": [
        "Gocce irregolari compongono un ritmo organico.",
        "Il terreno rilascia vapori terrosi.",
    ],
    "nebbia": [
        "Profili distanti si dissolvono in latte diffuso.",
        "L’umidità condensa in perle sulle superfici rugose.",
    ],
}

def _ambient_line(state: GameState) -> str | None:
    daytime = state.daytime
    weather = state.weather
    options: list[str] = []
    options.extend(_AMBIENT_SNIPPETS.get(weather, []))
    options.extend(_AMBIENT_SNIPPETS.get(daytime, []))
    if not options:
        return None
    # Evita ripetizione consecutiva
    if state.last_ambient_line and len(options) > 1:
        filtered = [o for o in options if o != state.last_ambient_line]
        if filtered:
            options = filtered
    choice = random.choice(options)
    state.last_ambient_line = choice
    return choice

class ActionError(Exception):
    pass

def wait(state: GameState, registry: ContentRegistry, minutes: int = 10) -> Dict[str, object]:
    """Attende un certo numero di minuti di gioco.

    In realtime puro non manipoliamo il clock direttamente; per simulare l'attesa
    aumentiamo l'offset manuale così che il mapping tempo reale -> tempo simulato
    risulti avanzato di 'minutes'. Questo evita busy-wait e mantiene consistenza.
    Vengono applicate tutte le regole di aggiornamento meteo come se il tempo fosse trascorso.
    Restituisce una descrizione sintetica dell'area dopo l'attesa.
    """
    if minutes <= 0:
        return {"lines": ["Non passa alcun tempo."], "hints": [], "events_triggered": [], "changes": {}}
    # Avanza offset
    state.manual_offset_minutes += minutes
    # Forza ricalcolo e meteo
    _advance_time_and_weather(state)
    micro = registry.get_micro(state.current_micro)
    if micro is None:
        raise ActionError("Posizione corrente non trovata dopo wait.")
    header = f"[{state.time_string()} Giorno {state.day_count} | {state.daytime.title()} | {state.weather.title()} | {state.climate.title()}]"
    core = f"Lasci trascorrere {minutes} minuti immerso nel contesto." \
           f" Il tempo ora è {state.time_string().lower()} e l'atmosfera sembra {state.weather}."
    ambient = _ambient_line(state)
    lines: List[str] = [header]
    for seg in _wrap(core):
        lines.append(seg)
    if ambient:
        lines.extend(_wrap(ambient))
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {"waited": minutes}}

def look(state: GameState, registry: ContentRegistry) -> Dict[str, object]:
    # Avanza ora/meteo prima di mostrare la descrizione
    _advance_time_and_weather(state)
    micro = registry.get_micro(state.current_micro)
    if micro is None:
        raise ActionError(f"Location not found: {state.current_micro}")
    # Intestazione ambiente con orario e giorno
    first_visit = micro.id not in state.visited_micro
    signature = f"{state.daytime}|{state.weather}"
    last_sig = state.micro_last_signature.get(micro.id)
    dynamic_desc = registry.compose_area_description(micro.id, state.daytime, state.weather)
    header = f"[{state.time_string()} Giorno {state.day_count} | {state.daytime.title()} | {state.weather.title()} | {state.climate.title()}]"
    lines: List[str] = [header]
    # Determina modalità descrizione
    if first_visit:
        core_text = dynamic_desc
    else:
        # Se firma cambiata (meteo/ora), mostra una descrizione intermedia
        if last_sig != signature:
            # Estraggo solo le varianti (differenza) per enfatizzare cambiamento
            base = registry.get_area_description(micro.id)
            variation_part = dynamic_desc[len(base):].strip() if dynamic_desc.startswith(base) else dynamic_desc
            core_text = f"{registry.get_area_name(micro.id)} — {variation_part}".strip()
        else:
            core_text = registry.get_area_name(micro.id)
    ambient_extra = _ambient_line(state) if not first_visit else None
    # Wrap
    for seg in _wrap(core_text):
        lines.append(seg)
    if ambient_extra:
        lines.extend(_wrap(ambient_extra))
    # Mostra oggetti interattivi visibili in base a meteo/ora/flag
    visible_objs = []
    for obj in micro.interactables:
        # visibilità condizionata da flag/meteo/ora
        if obj.visible_flag:
            if obj.visible_flag == "is_daytime" and state.daytime not in ("mattina", "giorno"):
                continue
            if obj.visible_flag == "is_morning" and state.daytime != "mattina":
                continue
            if obj.visible_flag == "is_rainy" and state.weather != "pioggia":
                continue
            if obj.visible_flag == "is_spring" and state.climate != "umido":
                continue
            if obj.visible_flag == "has_examined_marker" and not state.flags.get("has_examined_marker"):
                continue
        visible_objs.append(obj.id)
    if visible_objs:
        lines.append("Qui noti:")
        for oid in visible_objs:
            obj_line = f"- {registry.get_object_name(oid)}: {registry.get_object_description(oid)}"
            lines.extend(_wrap(obj_line))
    exits_desc = []
    for ex in micro.exits:
        exits_desc.append(f"{ex.direction}: {registry.get_micro(ex.target_micro).name if registry.get_micro(ex.target_micro) else ex.target_micro}")
    if exits_desc:
        lines.append("Uscite: " + ", ".join(exits_desc))
    # Segna visita (dopo generazione testo per avere first_visit corretto)
    state.visited_micro.add(micro.id)
    state.visit_counts[micro.id] = state.visit_counts.get(micro.id, 0) + 1
    state.micro_last_signature[micro.id] = signature
    return {
        "lines": lines,
        "hints": exits_desc,
        "events_triggered": [],
        "changes": {}
    }
    # unreachable

def go(state: GameState, registry: ContentRegistry, direction: str) -> Dict[str, object]:
    direction = direction.lower().strip()
    current = registry.get_micro(state.current_micro)
    if current is None:
        raise ActionError(f"Current micro room missing: {state.current_micro}")
    target_exit: Exit | None = None
    for ex in current.exits:
        if ex.direction.lower() == direction:
            target_exit = ex
            break
    if target_exit is None:
        raise ActionError(f"Nessuna uscita '{direction}' da qui.")
    if target_exit.locked and not (target_exit.lock_flag and state.flags.get(target_exit.lock_flag)):
        raise ActionError("L'uscita è bloccata.")
    # Update location (macro doesn't change in this initial slice)
    state.current_micro = target_exit.target_micro
    # Build result narrative via look after move
    look_result = look(state, registry)
    look_result["changes"] = {"location": state.location_key()}
    return look_result

# --- Logica di avanzamento tempo/meteo ---
def _advance_time_and_weather(state: GameState):
    # Ricalcola il clock in base al tempo reale trascorso
    now = time.time()
    total_minutes = state.recompute_from_real(now)
    # Riconsidera il meteo ogni 30 minuti simulati (gestisce più salti, es. wait lungo)
    while total_minutes - state.last_weather_eval_total >= 30:
        state.last_weather_eval_total += 30
        if state.climate == "temperato":
            weights = [0.55, 0.25, 0.15, 0.05]
        elif state.climate == "umido":
            weights = [0.25, 0.25, 0.4, 0.1]
        elif state.climate == "freddo":
            weights = [0.35, 0.25, 0.1, 0.3]
        else:
            weights = [0.6, 0.25, 0.1, 0.05]
        new_weather = random.choices(["sereno", "nuvoloso", "pioggia", "nebbia"], weights=weights)[0]
        if state.weather == "pioggia" and new_weather == "pioggia" and random.random() < 0.05:
            state.climate = "umido"
        state.weather = new_weather

