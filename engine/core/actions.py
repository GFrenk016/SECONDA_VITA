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
from . import combat
from . import persistence
from . import events
from . import choices
from . import ambient_events
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
    "indoor": [
        "L'aria ferma amplifica il più lieve movimento.",
        "Un odore secco di legno antico persiste sulle superfici.",
    ],
    "shelter": [
        "Il silenzio ovattato filtra i rumori del mondo esterno.",
        "Pareti naturali attenuano ogni eco in un respiro caldo.",
    ],
    # Variante specifica per la pioggia percepita indoor / riparo
    "indoor_pioggia": [
        "Gocciolii ovattati scandiscono un ritmo distante oltre le pareti naturali.",
        "La pioggia è un fruscio smorzato; ogni tanto un rivolo trova un varco e cade in una pozza nascosta.",
        "Il tamburellare esterno arriva come vibrazione diffusa più che come suono distinto.",
    ],
}

def _ambient_line(state: GameState, micro: MicroRoom | None = None) -> str | None:
    """Restituisce una linea ambientale opzionale.

    Novità:
    - Frequenza controllata: emette al massimo uno snippet ogni
      ``state.ambient_min_gap_minutes`` minuti simulati.
    - Indoor sotto la pioggia: se l'area ha tag indoor/shelter e il meteo è
      pioggia, usa snippet attenuati (chiave 'indoor_pioggia').
    """
    total_minutes = state.day_count * 24 * 60 + state.time_minutes
    if total_minutes - state.last_ambient_emit_total < state.ambient_min_gap_minutes:
        return None
    daytime = state.daytime
    weather = state.weather
    options: list[str] = []
    indoor_like = False
    if micro and getattr(micro, 'tags', None):
        indoor_like = any(t in ("indoor", "shelter") for t in micro.tags)
    if weather == "pioggia" and indoor_like and "indoor_pioggia" in _AMBIENT_SNIPPETS:
        options.extend(_AMBIENT_SNIPPETS.get("indoor_pioggia", []))
    else:
        options.extend(_AMBIENT_SNIPPETS.get(weather, []))
    options.extend(_AMBIENT_SNIPPETS.get(daytime, []))
    if micro and getattr(micro, 'tags', None):
        for tag in micro.tags:
            if tag in ("indoor", "shelter"):
                options.extend(_AMBIENT_SNIPPETS.get(tag, []))
    if not options:
        return None
    # Percorso deterministico per test: priorità a force_ambient_exact, poi force_ambient_key
    forced: str | None = None
    if state.force_ambient_exact:
        forced = state.force_ambient_exact
        state.force_ambient_exact = None
    elif state.force_ambient_key:
        key = state.force_ambient_key
        state.force_ambient_key = None
        # Recupera lista associata alla chiave se esiste
        from typing import cast
        forced_list = _AMBIENT_SNIPPETS.get(key, [])
        if forced_list:
            forced = forced_list[0]
    if state.last_ambient_line and len(options) > 1 and not forced:
        filtered = [o for o in options if o != state.last_ambient_line]
        if filtered:
            options = filtered
    choice = forced or random.choice(options)
    state.last_ambient_line = choice
    state.last_ambient_emit_total = total_minutes
    return choice

class ActionError(Exception):
    pass

_PHASES_ORDER = ["mattina", "giorno", "sera", "notte"]

def _do_inspect(state: GameState, registry: ContentRegistry, target: str, depth: int) -> Dict[str, object]:
    """Implementazione generica multi-livello.

    depth 1 = inspect (base)
    depth 2 = examine (secondo livello)
    depth 3 = search (terzo livello)

    Un oggetto può avere in inspectables.json campi:
      - prima_volta / successive (livello 1) già esistenti
      - examine (livello 2) opzionale
      - search (livello 3) opzionale
    Se il livello richiesto non esiste, si degrada al massimo livello disponibile precedente.
    """
    _advance_time_and_weather(state)
    micro = registry.get_micro(state.current_micro)
    if micro is None:
        raise ActionError("Posizione corrente non trovata.")
    norm = target.strip().lower()
    # Ricava oggetti visibili (riuso logica look - duplicata per isolamento)
    candidates = []
    for obj in micro.interactables:
        if obj.visible_flag:
            if obj.visible_flag == "is_daytime" and state.daytime not in ("mattina", "giorno"):
                continue
            if obj.visible_flag == "is_morning" and state.daytime != "mattina":
                continue
            if obj.visible_flag == "is_night" and state.daytime != "notte":
                continue
            if obj.visible_flag == "is_rainy" and state.weather != "pioggia":
                continue
            if obj.visible_flag == "is_spring" and state.climate != "umido":
                continue
            if obj.visible_flag == "has_examined_marker" and not state.flags.get("has_examined_marker"):
                continue
        candidates.append(obj)
    # Costruisce mapping per matching
    match_infos = []  # list[tuple[obj, list[str], display_name]]
    for obj in candidates:
        loc_name = registry.get_object_name(obj.id)
        titolo = None
        if hasattr(registry, "inspectables"):
            data_try = registry.inspectables.get(obj.id)  # type: ignore[attr-defined]
            if data_try:
                titolo = data_try.get("titolo")
        display = titolo or loc_name
        strings = {obj.id.lower(), loc_name.lower(), display.lower()}
        if obj.alias:
            strings.add(obj.alias.lower())
        if titolo:
            strings.add(titolo.lower())
        match_infos.append((obj, list(strings), display))
    # Primo pass: match esatto
    exact_matches = [obj for (obj, strs, _disp) in match_infos if norm in strs]
    target_obj = None
    if len(exact_matches) == 1:
        target_obj = exact_matches[0]
    elif len(exact_matches) > 1:
        names = {registry.get_object_name(o.id) for o in exact_matches}
        raise ActionError("Riferimento ambiguo: " + ", ".join(sorted(names)))
    else:
        # Secondo pass: match parziale (substring in entrambe le direzioni)
        partial = []
        for obj, strs, _disp in match_infos:
            for s in strs:
                if norm in s or s in norm:
                    partial.append(obj)
                    break
        if len(partial) == 1:
            target_obj = partial[0]
        elif len(partial) > 1:
            names = {registry.get_object_name(o.id) for o in partial}
            raise ActionError("Riferimento ambiguo: " + ", ".join(sorted(names)))
    if target_obj is None:
        raise ActionError("Non vedi nulla del genere da esaminare.")
    obj_id = target_obj.id
    base_flag = f"inspected:{obj_id}"
    examine_flag = f"examined:{obj_id}"
    search_flag = f"searched:{obj_id}"
    # --- Gating sequenziale richiesto: depth 2 richiede aver fatto depth 1; depth 3 richiede aver fatto depth 2 ---
    if depth == 2 and not state.flags.get(base_flag):
        raise ActionError("Prima devi eseguire 'inspect' su questo oggetto per poterne fare un esame più approfondito (examine).")
    if depth == 3:
        if not state.flags.get(base_flag):
            raise ActionError("Prima devi eseguire 'inspect' e poi 'examine' prima di poter fare una ricerca minuziosa (search).")
        if not state.flags.get(examine_flag):
            raise ActionError("Prima devi eseguire 'examine' su questo oggetto prima di poter fare 'search'.")
    # Determina livello effettivo disponibile
    data = getattr(registry, "inspectables", {}).get(obj_id) if hasattr(registry, "inspectables") else None
    available_depth = 1
    if data and data.get("examine"):
        available_depth = 2
    if data and data.get("search"):
        available_depth = 3
    eff_depth = min(depth, available_depth)
    # Prima volta per ogni livello
    first_time_level = False
    if eff_depth == 1 and not state.flags.get(base_flag):
        first_time_level = True
        state.flags[base_flag] = True
    elif eff_depth == 2 and not state.flags.get(examine_flag):
        first_time_level = True
        state.flags[examine_flag] = True
    elif eff_depth == 3 and not state.flags.get(search_flag):
        first_time_level = True
        state.flags[search_flag] = True
    # Costruzione titolo e testo
    name = registry.get_object_name(obj_id)
    default_desc = registry.get_object_description(obj_id)
    text = default_desc
    if data:
        custom_title = data.get("titolo")
        if custom_title:
            name = custom_title
        # flag_on_inspect sempre dalla prima ispezione base
        if data.get("flag_on_inspect") and state.flags.get(base_flag):
            state.flags[data["flag_on_inspect"]] = True
        if eff_depth == 1:
            if state.flags.get(base_flag) and not first_time_level:
                # revisita base
                text = data.get("successive") or default_desc
            else:
                text = data.get("prima_volta") or default_desc
        elif eff_depth == 2:
            text = data.get("examine") or data.get("successive") or data.get("prima_volta") or default_desc
        else:  # eff_depth == 3
            text = data.get("search") or data.get("examine") or data.get("successive") or data.get("prima_volta") or default_desc
    if not text:
        text = "Non trovi dettagli rilevanti." if first_time_level else "Nulla di nuovo."  
    header = f"[{state.time_string()} Giorno {state.day_count} | {state.daytime.title()} | {state.weather.title()} | {micro.name}]"
    verb = {1: "Inspect", 2: "Examine", 3: "Search"}[eff_depth]
    prefix = verb + (" (first)" if first_time_level else "")
    core = f"{prefix} {name}. {text}".strip()
    lines: List[str] = [header]
    for seg in _wrap(core):
        lines.append(seg)
    # Suggerimento livello successivo se disponibile e non ancora effettuato
    suggestion = None
    if eff_depth == 1 and available_depth >= 2 and not state.flags.get(examine_flag):
        suggestion = f"Possibile: examine {name.lower()}"
    elif eff_depth == 2 and available_depth >= 3 and not state.flags.get(search_flag):
        suggestion = f"Possibile: search {name.lower()}"
    if suggestion:
        lines.append(suggestion)
    
    # Check for memory triggers based on the inspected object
    memory_messages = maybe_trigger_memory(state, f"inspect_{obj_id}", state.location_key())
    if memory_messages:
        lines.extend([""] + memory_messages)
    
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {"object": obj_id, "depth": eff_depth, "first_time": first_time_level}}

def inspect(state: GameState, registry: ContentRegistry, target: str) -> Dict[str, object]:
    return _do_inspect(state, registry, target, 1)

def examine(state: GameState, registry: ContentRegistry, target: str) -> Dict[str, object]:
    return _do_inspect(state, registry, target, 2)

def search(state: GameState, registry: ContentRegistry, target: str) -> Dict[str, object]:
    return _do_inspect(state, registry, target, 3)

def status(state: GameState, registry: ContentRegistry) -> Dict[str, object]:
    """Riepilogo stato ambientale attuale senza modificare memoria visite."""
    _advance_time_and_weather(state)
    micro = registry.get_micro(state.current_micro)
    location = micro.name if micro else state.current_micro
    # Calcola prossima fase
    current_idx = _PHASES_ORDER.index(state.daytime)
    next_phase = _PHASES_ORDER[(current_idx + 1) % len(_PHASES_ORDER)]
    lines = [
        f"Orario: {state.time_string()} (Giorno {state.day_count})",
        f"Fase: {state.daytime}",
        f"Prossima fase: {next_phase}",
        f"Meteo: {state.weather} (clima {state.climate})",
        f"Luogo: {location}",
    ]
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}

def _minutes_to_phase(state: GameState, target: str) -> int:
    """Calcola i minuti da aggiungere per raggiungere la prossima occorrenza della fase target."""
    if target not in _PHASES_ORDER:
        raise ActionError(f"Fase sconosciuta: {target}")
    # Mappa fasce agli intervalli
    intervals = {
        "mattina": (6*60, 12*60),
        "giorno": (12*60, 18*60),
        "sera": (18*60, 22*60),
        "notte": (22*60, 24*60 + 6*60),  # notte attraversa la mezzanotte
    }
    m = state.time_minutes
    start, end = intervals[target]
    if target == "notte":
        # intervallo spezzato: 22:00-24:00 e 00:00-06:00 (modellato come 22:00-30:00)
        if m >= 22*60:
            return 0  # già nella parte 22-24
        if m < 6*60:
            return 0  # già nella parte 00-06
        # altrimenti calcola minuti fino a 22:00
        return 22*60 - m
    # Per le altre fasce se siamo già dentro ritorna 0; altrimenti minuti fino all'inizio
    if start <= m < end:
        return 0
    if m < start:
        return start - m
    # oltre la fascia: andiamo al giorno successivo
    return (24*60 - m) + start

def wait_until(state: GameState, registry: ContentRegistry, target_phase: str) -> Dict[str, object]:
    """Avanza il tempo fino all'inizio della prossima (o corrente, se già dentro) fase indicata."""
    target_phase = target_phase.lower().strip()
    minutes = _minutes_to_phase(state, target_phase)
    if minutes == 0:
        # Usa status per coerenza ma con messaggio
        res = status(state, registry)
        res["lines"].insert(0, f"Sei già nella fase '{target_phase}'.")
        return res
    state.manual_offset_minutes += minutes
    _advance_time_and_weather(state)
    micro = registry.get_micro(state.current_micro)
    header = f"[{state.time_string()} Giorno {state.day_count} | {state.daytime.title()} | {state.weather.title()} | {state.climate.title()} | {micro.name if micro else state.current_micro}]"
    lines = [header]
    lines.extend(_wrap(f"Attendi fino alla fase '{target_phase}' (passano {minutes} minuti)."))
    ambient = _ambient_line(state, micro)
    if ambient:
        lines.extend(_wrap(ambient))
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {"waited": minutes, "target_phase": target_phase}}

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
    header = f"[{state.time_string()} Giorno {state.day_count} | {state.daytime.title()} | {state.weather.title()} | {state.climate.title()} | {micro.name}]"
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
    header = f"[{state.time_string()} Giorno {state.day_count} | {state.daytime.title()} | {state.weather.title()} | {state.climate.title()} | {micro.name}]"
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
    ambient_extra = _ambient_line(state, micro) if not first_visit else None
    # Wrap
    for seg in _wrap(core_text):
        lines.append(seg)
    if ambient_extra:
        lines.extend(_wrap(ambient_extra))
    # Mostra oggetti interattivi visibili in base a meteo/ora/flag
    visible_objs: list[str] = []
    for obj in micro.interactables:
        # visibilità condizionata da flag/meteo/ora
        if obj.visible_flag:
            if obj.visible_flag == "is_daytime" and state.daytime not in ("mattina", "giorno"):
                continue
            if obj.visible_flag == "is_morning" and state.daytime != "mattina":
                continue
            if obj.visible_flag == "is_night" and state.daytime != "notte":
                continue
            if obj.visible_flag == "is_rainy" and state.weather != "pioggia":
                continue
            if obj.visible_flag == "is_spring" and state.climate != "umido":
                continue
            if obj.visible_flag == "has_examined_marker" and not state.flags.get("has_examined_marker"):
                continue
        visible_objs.append(obj.id)
    if visible_objs:
        # Calcola nuovi elementi rispetto all'ultima fotografia
        prev = state.micro_last_visible.get(micro.id, set())
        current_set = set(visible_objs)
        new_items = [oid for oid in visible_objs if oid not in prev]
        if new_items:
            if len(new_items) == 1:
                lines.append(f"Qualcosa di nuovo attira la tua attenzione: {registry.get_object_name(new_items[0])}.")
            else:
                elenco = ", ".join(registry.get_object_name(i) for i in new_items)
                lines.append(f"Nuovi elementi visibili: {elenco}.")
        lines.append("Qui noti:")
        any_marker = False
        for oid in visible_objs:
            name = registry.get_object_name(oid)
            desc = registry.get_object_description(oid)
            marker = ""
            data = getattr(registry, "inspectables", {}).get(oid) if hasattr(registry, "inspectables") else None
            if data:
                # Calcola livelli disponibili
                avail = 1 + (1 if data.get("examine") else 0) + (1 if data.get("search") else 0)
                # Verifica progressi
                inspected = state.flags.get(f"inspected:{oid}")
                examined = state.flags.get(f"examined:{oid}")
                searched = state.flags.get(f"searched:{oid}")
                # Se esistono livelli più profondi non ancora raggiunti, aggiungi marker
                if avail >= 2 and not examined:
                    marker = "*"  # almeno un livello approfondito disponibile
                elif avail >= 3 and examined and not searched:
                    marker = "**"  # ultimo livello (search) ancora disponibile
                if marker:
                    any_marker = True
            obj_line = f"- {name}{(' ' + marker) if marker else ''}: {desc}"
            lines.extend(_wrap(obj_line))
        if any_marker:
            lines.append("Legenda: * examine disponibile | ** search disponibile")
        # Aggiorna snapshot visibilità
        state.micro_last_visible[micro.id] = current_set
    exits_desc = []
    any_locked = False
    for ex in micro.exits:
        target_ref = registry.get_micro(ex.target_micro)
        target_name = target_ref.name if target_ref else ex.target_micro
        locked_now = False
        if ex.locked:
            # Se esiste una lock_flag ed è soddisfatta, l'uscita non viene più considerata bloccata
            if ex.lock_flag:
                if not state.flags.get(ex.lock_flag):
                    locked_now = True
            else:
                locked_now = True
        label = f"{ex.direction}: {target_name}"
        if locked_now:
            label += " (bloccata)"
            any_locked = True
        exits_desc.append(label)
    if exits_desc:
        lines.append("Uscite: " + ", ".join(exits_desc))
        if any_locked:
            lines.append("Legenda: (bloccata) uscita attualmente inaccessibile")
    # Segna visita (dopo generazione testo per avere first_visit corretto)
    state.visited_micro.add(micro.id)
    state.visit_counts[micro.id] = state.visit_counts.get(micro.id, 0) + 1
    state.micro_last_signature[micro.id] = signature
    
    # Check for pending ambient messages
    if hasattr(state, 'pending_ambient_messages') and state.pending_ambient_messages:
        lines.extend([""] + state.pending_ambient_messages)
        state.pending_ambient_messages.clear()
    
    # Check for pending loot messages
    if hasattr(state, 'pending_loot_messages') and state.pending_loot_messages:
        lines.extend([""] + state.pending_loot_messages)
        state.pending_loot_messages.clear()
    
    # Check for memory triggers
    memory_messages = maybe_trigger_memory(state, "look", state.location_key())
    if memory_messages:
        lines.extend([""] + memory_messages)
    
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
    
    # Process room entry events
    new_location = state.location_key()
    event_messages = events.process_events("on_enter", new_location, state, registry)
    
    # Build result narrative via look after move
    look_result = look(state, registry)
    
    # Add event messages to the result
    if event_messages:
        look_result["lines"].extend([""] + event_messages)
        look_result["events_triggered"] = event_messages
    
    look_result["changes"] = {"location": new_location}
    return look_result

def where(state: GameState, registry: ContentRegistry) -> Dict[str, object]:
    """Ritorna una breve descrizione della posizione corrente (macro -> micro) e tag."""
    _advance_time_and_weather(state)
    micro = registry.get_micro(state.current_micro)
    if micro is None:
        raise ActionError("Posizione corrente non trovata.")
    macro = registry.get_macro(state.current_macro)
    macro_name = macro.name if macro else state.current_macro
    header = f"[{state.time_string()} Giorno {state.day_count} | {state.daytime.title()} | {state.weather.title()} | {state.climate.title()} | {micro.name}]"
    tags = ", ".join(micro.tags) if micro.tags else "(nessun tag)"
    lines = [header, f"Posizione: {macro_name} -> {micro.name}", f"Tag: {tags}"]
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}

# --- Combat wrappers (fase 1) ---
def engage(state: GameState, registry: ContentRegistry, enemy_def: dict) -> Dict[str, object]:
    """Avvia un combattimento contro un singolo nemico.

    enemy_def minimo: {id, name, hp, attack, qte_chance, qte_prompt, qte_expected, qte_window_minutes}
    """
    result = combat.start_combat(state, registry, enemy_def)
    # Tick immediato per gestire eventuali eventi (in futuro: spawn multipli ecc.)
    tick_lines = combat.tick_combat(state)
    if tick_lines:
        result['lines'].extend(tick_lines)
    return result

def combat_action(state: GameState, registry: ContentRegistry, command: str, arg: str | None = None) -> Dict[str, object]:
    """Esegue un'azione durante il combattimento: attack | status | qte <input> | push | flee.

    Prima dell'azione processa un tick realtime (timer attacchi / scadenze QTE), poi esegue il comando,
    infine esegue un secondo tick per catturare eventuali attacchi che vanno a segno nel frattempo.
    """
    pre_lines = combat.tick_combat(state)
    core = combat.resolve_combat_action(state, registry, command, arg)
    post_lines = combat.tick_combat(state)
    if pre_lines:
        core['lines'] = pre_lines + core['lines']
    if post_lines:
        core['lines'].extend(post_lines)
    return core

def spawn(state: GameState, registry: ContentRegistry, enemy_id: str) -> Dict[str, object]:
    enemy_def = combat.spawn_enemy(enemy_id)
    return combat.start_combat(state, registry, enemy_def)

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
    
    # Check for ambient events (environmental storytelling)
    ambient_messages = ambient_events.check_ambient_events(state)
    if ambient_messages:
        # Store ambient messages for retrieval by calling functions
        if not hasattr(state, 'pending_ambient_messages'):
            state.pending_ambient_messages = []
        state.pending_ambient_messages.extend(ambient_messages)


# --- New Inventory and Stats Commands ---

def inventory(state: GameState, registry: ContentRegistry) -> Dict[str, Any]:
    """Display player inventory with weight and equipment status."""
    from ..inventory import Inventory
    from ..items import get_item_registry
    from ..stats import PlayerStats
    
    lines = []
    
    # Initialize systems if not present
    player_inventory = _get_player_inventory(state)
    player_stats = _get_player_stats(state)
    
    # Get inventory items
    items = player_inventory.list_items()
    
    if not items:
        lines.append("Inventario vuoto.")
        return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}
    
    # Header
    total_weight = player_inventory.get_total_weight()
    carry_capacity = player_stats.get_carry_capacity()
    weight_pct = (total_weight / carry_capacity) * 100 if carry_capacity > 0 else 0
    
    lines.append(f"=== Inventario ===")
    lines.append(f"Peso: {total_weight:.1f}/{carry_capacity:.1f}kg ({weight_pct:.1f}%)")
    lines.append("")
    
    # Group items by type
    equipped_items = []
    consumables = []
    weapons = []
    armor = []
    materials = []
    quest_items = []
    other_items = []
    
    item_registry = get_item_registry()
    
    for item_id, quantity, is_equipped in items:
        item = item_registry.get_item(item_id)
        item_name = item.name if item else item_id
        
        item_line = f"  {item_name}"
        if quantity > 1:
            item_line += f" x{quantity}"
        if is_equipped:
            item_line += " [EQUIPAGGIATO]"
            equipped_items.append(item_line)
        elif item and item.type == 'consumable':
            consumables.append(item_line)
        elif item and item.type == 'weapon':
            weapons.append(item_line)
        elif item and item.type == 'armor':
            armor.append(item_line)
        elif item and item.type == 'material':
            materials.append(item_line)
        elif item and item.type == 'quest':
            quest_items.append(item_line)
        else:
            other_items.append(item_line)
    
    # Display items by category
    if equipped_items:
        lines.append("Equipaggiamento:")
        lines.extend(equipped_items)
        lines.append("")
    
    if consumables:
        lines.append("Consumabili:")
        lines.extend(consumables)
        lines.append("")
    
    if weapons:
        lines.append("Armi:")
        lines.extend(weapons)
        lines.append("")
    
    if armor:
        lines.append("Armature:")
        lines.extend(armor)
        lines.append("")
    
    if quest_items:
        lines.append("Oggetti Missione:")
        lines.extend(quest_items)
        lines.append("")
    
    if materials:
        lines.append("Materiali:")
        lines.extend(materials)
        lines.append("")
    
    if other_items:
        lines.append("Altro:")
        lines.extend(other_items)
    
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}


def stats(state: GameState, registry: ContentRegistry) -> Dict[str, Any]:
    """Display player statistics."""
    lines = []
    
    # Initialize stats if not present
    player_stats = _get_player_stats(state)
    
    lines.append("=== Statistiche Giocatore ===")
    lines.append("")
    
    # Health, Energy, Morale with bars
    health_bar = _create_progress_bar(player_stats.health, player_stats.max_health)
    energy_bar = _create_progress_bar(player_stats.energy, player_stats.max_energy)
    morale_bar = _create_progress_bar(player_stats.morale, player_stats.max_morale)
    
    lines.append(f"Salute:  {health_bar} {player_stats.health}/{player_stats.max_health}")
    lines.append(f"Energia: {energy_bar} {player_stats.energy}/{player_stats.max_energy}")
    lines.append(f"Morale:  {morale_bar} {player_stats.morale}/{player_stats.max_morale}")
    lines.append("")
    
    # Base attributes
    lines.append("Attributi:")
    lines.append(f"  Forza:      {player_stats.get_modified_stat('strength'):.0f}")
    lines.append(f"  Agilità:    {player_stats.get_modified_stat('agility'):.0f}")
    lines.append(f"  Intelletto: {player_stats.get_modified_stat('intellect'):.0f}")
    lines.append(f"  Percezione: {player_stats.get_modified_stat('perception'):.0f}")
    lines.append(f"  Carisma:    {player_stats.get_modified_stat('charisma'):.0f}")
    lines.append(f"  Fortuna:    {player_stats.get_modified_stat('luck'):.0f}")
    lines.append("")
    
    # Derived stats
    lines.append("Statistiche Derivate:")
    lines.append(f"  Capacità Carico: {player_stats.get_carry_capacity():.1f}kg")
    lines.append(f"  Chance Critico:  {player_stats.get_crit_chance() * 100:.1f}%")
    lines.append(f"  Evasione:        {player_stats.get_evasion() * 100:.1f}%")
    lines.append(f"  Raggio Visione:  {player_stats.get_vision_range()}")
    lines.append("")
    
    # Resistances
    lines.append("Resistenze:")
    lines.append(f"  Sanguinamento: {player_stats.bleed_resistance}%")
    lines.append(f"  Veleno:        {player_stats.poison_resistance}%")
    lines.append(f"  Fuoco:         {player_stats.fire_resistance}%")
    lines.append(f"  Freddo:        {player_stats.cold_resistance}%")
    
    # Active buffs
    active_buffs = player_stats.get_active_buffs()
    if active_buffs:
        lines.append("")
        lines.append("Effetti Attivi:")
        for buff in active_buffs:
            if buff['is_permanent']:
                lines.append(f"  {buff['stat']}: {buff['amount']:+.1f} (permanente)")
            else:
                lines.append(f"  {buff['stat']}: {buff['amount']:+.1f} ({buff['remaining_ticks']} tick rimanenti)")
    
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}


def use_item(state: GameState, registry: ContentRegistry, item_name: str) -> Dict[str, Any]:
    """Use an item from inventory."""
    from ..stats import apply_item_effects
    from ..items import get_item_registry
    
    lines = []
    
    # Initialize systems
    player_inventory = _get_player_inventory(state)
    player_stats = _get_player_stats(state)
    
    # Find item by name or ID
    item_registry = get_item_registry()
    matching_items = item_registry.find_items_by_name(item_name, partial=True)
    
    if not matching_items:
        lines.append(f"Oggetto '{item_name}' non trovato.")
        return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}
    
    item = matching_items[0]  # Use first match
    
    # Try to use the item
    success, message, effects = player_inventory.use_item(item.id)
    
    if not success:
        lines.append(message)
        return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}
    
    lines.append(message)
    
    # Apply effects
    if effects:
        effect_messages = apply_item_effects(player_stats, effects)
        lines.extend(effect_messages)
    
    # Update state
    _save_player_inventory(state, player_inventory)
    _save_player_stats(state, player_stats)
    
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {"used_item": item.id}}


def equip_item(state: GameState, registry: ContentRegistry, item_name: str) -> Dict[str, Any]:
    """Equip an item from inventory."""
    from ..items import get_item_registry
    
    lines = []
    
    # Initialize systems
    player_inventory = _get_player_inventory(state)
    
    # Find item by name or ID
    item_registry = get_item_registry()
    matching_items = item_registry.find_items_by_name(item_name, partial=True)
    
    if not matching_items:
        lines.append(f"Oggetto '{item_name}' non trovato.")
        return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}
    
    item = matching_items[0]
    
    # Try to equip
    success, message, old_item_id = player_inventory.equip(item.id)
    lines.append(message)
    
    if success and old_item_id:
        old_item = item_registry.get_item(old_item_id)
        old_name = old_item.name if old_item else old_item_id
        lines.append(f"Precedentemente equipaggiato {old_name} riposto nell'inventario.")
    
    # Update state
    _save_player_inventory(state, player_inventory)
    
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {"equipped_item": item.id if success else None}}


def unequip_item(state: GameState, registry: ContentRegistry, slot_or_item: str) -> Dict[str, Any]:
    """Unequip an item by slot or item name."""
    lines = []
    
    # Initialize systems
    player_inventory = _get_player_inventory(state)
    
    # Try to unequip
    success, message, item_id = player_inventory.unequip(slot_or_item)
    lines.append(message)
    
    # Update state
    _save_player_inventory(state, player_inventory)
    
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {"unequipped_item": item_id if success else None}}


def drop_item(state: GameState, registry: ContentRegistry, item_name: str, quantity: int = 1) -> Dict[str, Any]:
    """Drop item from inventory."""
    from ..items import get_item_registry
    
    lines = []
    
    # Initialize systems
    player_inventory = _get_player_inventory(state)
    
    # Find item by name or ID
    item_registry = get_item_registry()
    matching_items = item_registry.find_items_by_name(item_name, partial=True)
    
    if not matching_items:
        lines.append(f"Oggetto '{item_name}' non trovato.")
        return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}
    
    item = matching_items[0]
    
    # Try to drop
    success, message = player_inventory.drop_item(item.id, quantity)
    lines.append(message)
    
    # TODO: Add dropped item to current location's ground items
    
    # Update state
    _save_player_inventory(state, player_inventory)
    
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {"dropped_item": item.id if success else None}}


def examine_item(state: GameState, registry: ContentRegistry, item_name: str) -> Dict[str, Any]:
    """Examine an item in detail."""
    from ..items import get_item_registry
    
    lines = []
    
    # Find item by name or ID
    item_registry = get_item_registry()
    matching_items = item_registry.find_items_by_name(item_name, partial=True)
    
    if not matching_items:
        lines.append(f"Oggetto '{item_name}' non trovato.")
        return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}
    
    item = matching_items[0]
    
    lines.append(f"=== {item.name} ===")
    lines.append(f"Tipo: {item.type.title()}")
    lines.append(f"Peso: {item.weight}kg")
    
    if item.stack_max > 1:
        lines.append(f"Stack massimo: {item.stack_max}")
    
    if item.value > 0:
        lines.append(f"Valore: {item.value}")
    
    if item.durability:
        lines.append(f"Durabilità: {item.durability}")
    
    if item.equip_slot:
        lines.append(f"Slot equipaggiamento: {item.equip_slot}")
    
    if item.tags:
        lines.append(f"Tag: {', '.join(item.tags)}")
    
    if item.description:
        lines.append("")
        lines.append(item.description)
    
    if item.effects:
        lines.append("")
        lines.append("Effetti:")
        for effect in item.effects:
            lines.append(f"  {_format_effect(effect)}")
    
    return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}


# --- Helper Functions ---

def _get_player_inventory(state: GameState):
    """Get or initialize player inventory."""
    from ..inventory import Inventory
    from ..items import get_item_registry
    
    item_registry = get_item_registry()
    inventory = Inventory(item_registry)
    
    if state.player_inventory:
        # Load from state
        inventory_data = state.player_inventory
        
        # Restore stacks
        for stack_data in inventory_data.get('stacks', []):
            inventory.add(stack_data['item_id'], stack_data['quantity'])
        
        # Restore equipment
        equipment_data = inventory_data.get('equipment', {})
        for slot, item_id in equipment_data.items():
            if item_id:
                setattr(inventory.equipment, slot, item_id)
    else:
        # Initialize with default items
        inventory.add("medkit", 1)
        inventory.add("canned_beans", 2)
        inventory.add("cloth", 3)
        inventory.add("hunting_knife", 1)  # Add for testing
    
    return inventory


def _save_player_inventory(state: GameState, inventory):
    """Save player inventory to state."""
    state.player_inventory = {
        'stacks': [{'item_id': stack.item_id, 'quantity': stack.quantity} for stack in inventory.stacks],
        'equipment': {
            'main_hand': inventory.equipment.main_hand,
            'off_hand': inventory.equipment.off_hand,
            'head': inventory.equipment.head,
            'body': inventory.equipment.body,
            'legs': inventory.equipment.legs,
            'feet': inventory.equipment.feet,
            'accessory1': inventory.equipment.accessory1,
            'accessory2': inventory.equipment.accessory2,
        }
    }


def _get_player_stats(state: GameState):
    """Get or initialize player stats."""
    from ..stats import PlayerStats, StatModifier
    
    if state.player_stats:
        # Load from state
        stats_data = state.player_stats
        stats = PlayerStats()
        
        # Load basic stats
        for field in ['health', 'max_health', 'energy', 'max_energy', 'morale', 'max_morale',
                     'strength', 'agility', 'intellect', 'perception', 'charisma', 'luck',
                     'bleed_resistance', 'poison_resistance', 'fire_resistance', 'cold_resistance',
                     'current_tick']:
            if field in stats_data:
                setattr(stats, field, stats_data[field])
        
        # Load modifiers
        modifiers_data = stats_data.get('modifiers', [])
        stats.modifiers = []
        for mod_data in modifiers_data:
            modifier = StatModifier(
                stat=mod_data['stat'],
                amount=mod_data['amount'],
                duration_ticks=mod_data['duration_ticks'],
                applied_tick=mod_data['applied_tick'],
                source=mod_data.get('source', 'unknown')
            )
            stats.modifiers.append(modifier)
        
        return stats
    else:
        # Initialize with defaults
        return PlayerStats()


def _save_player_stats(state: GameState, stats):
    """Save player stats to state."""
    state.player_stats = {
        'health': stats.health,
        'max_health': stats.max_health,
        'energy': stats.energy,
        'max_energy': stats.max_energy,
        'morale': stats.morale,
        'max_morale': stats.max_morale,
        'strength': stats.strength,
        'agility': stats.agility,
        'intellect': stats.intellect,
        'perception': stats.perception,
        'charisma': stats.charisma,
        'luck': stats.luck,
        'bleed_resistance': stats.bleed_resistance,
        'poison_resistance': stats.poison_resistance,
        'fire_resistance': stats.fire_resistance,
        'cold_resistance': stats.cold_resistance,
        'current_tick': stats.current_tick,
        'modifiers': [
            {
                'stat': mod.stat,
                'amount': mod.amount,
                'duration_ticks': mod.duration_ticks,
                'applied_tick': mod.applied_tick,
                'source': mod.source
            }
            for mod in stats.modifiers
        ]
    }


def _create_progress_bar(current: int, maximum: int, width: int = 10) -> str:
    """Create a text progress bar."""
    if maximum <= 0:
        return "[" + "?" * width + "]"
    
    filled = int((current / maximum) * width)
    empty = width - filled
    return "[" + "█" * filled + "░" * empty + "]"


def _format_effect(effect: Dict[str, Any]) -> str:
    """Format an item effect for display."""
    if 'heal' in effect:
        return f"Cura {effect['heal']} HP"
    elif 'restore' in effect:
        restore = effect['restore']
        if 'energy' in restore:
            return f"Ripristina {restore['energy']} energia"
    elif 'buff' in effect:
        buff = effect['buff']
        stat = buff.get('stat', 'unknown')
        amount = buff.get('amount', 0)
        duration = buff.get('duration_ticks', 0)
        if duration > 0:
            return f"{stat} {amount:+.1f} per {duration} tick"
        else:
            return f"{stat} {amount:+.1f} (permanente)"
    elif 'damage_over_time' in effect or 'dot' in effect:
        dot = effect.get('damage_over_time', effect.get('dot', {}))
        damage_type = dot.get('type', 'poison')
        amount = dot.get('amount', 1)
        duration = dot.get('duration', 60)
        return f"{amount} danno {damage_type} per {duration} tick"
    elif 'resist' in effect:
        resist = effect['resist']
        resist_type = resist.get('type')
        amount = resist.get('amount', 0)
        duration = resist.get('duration', 300)
        return f"+{amount} resistenza {resist_type} per {duration} tick"
    
    return str(effect)


# --- NPC Dialogue Actions ---

def talk(state: GameState, registry: ContentRegistry, npc_name: str = None) -> Dict[str, Any]:
    """Start or list available NPCs for conversation."""
    # Check if NPC registry is available
    if not hasattr(registry, 'npc_registry') or registry.npc_registry is None:
        return {"lines": ["Non ci sono persone con cui parlare qui."], "hints": [], "events_triggered": [], "changes": {}}
    
    current_location = state.location_key()
    parts = current_location.split(":")
    if len(parts) != 2:
        return {"lines": ["Errore nella posizione corrente."], "hints": [], "events_triggered": [], "changes": {}}
    
    macro_id, micro_id = parts
    talkable_npcs = registry.npc_registry.get_talkable_npcs(macro_id, micro_id)
    
    if not talkable_npcs:
        return {"lines": ["Non ci sono persone con cui parlare qui."], "hints": [], "events_triggered": [], "changes": {}}
    
    if npc_name is None:
        # List available NPCs
        lines = ["Persone presenti:"]
        for npc in talkable_npcs:
            state_desc = ""
            if npc.current_state.value != "neutral":
                state_desc = f" ({npc.current_state.value})"
            lines.append(f"- {npc.name}{state_desc}")
        lines.append("Usa 'talk <nome>' per iniziare una conversazione.")
        return {"lines": lines, "hints": [], "events_triggered": [], "changes": {}}
    
    # Find specific NPC
    target_npc = None
    for npc in talkable_npcs:
        if npc.name.lower() == npc_name.lower() or npc.id.lower() == npc_name.lower():
            target_npc = npc
            break
    
    if target_npc is None:
        return {"lines": [f"Non riesco a trovare {npc_name} qui."], "hints": [], "events_triggered": [], "changes": {}}
    
    # Start conversation
    from .npc.dialogue import AIDialogueEngine
    from .npc.models import DialogueContext
    
    dialogue_engine = AIDialogueEngine()
    context = DialogueContext(
        npc_id=target_npc.id,
        player_name="Giocatore",
        current_location=current_location,
        game_time=str(state.time_minutes),
        weather=state.weather,
        recent_events=[],
        relationship_status=target_npc.relationship,
        npc_mood=target_npc.mood,
        conversation_history=[]
    )
    
    result = dialogue_engine.start_conversation(target_npc, context)
    
    # Store active conversation in state
    state.active_conversation = {
        'npc_id': target_npc.id,
        'context': context,
        'engine': dialogue_engine
    }
    
    return {
        "lines": result['lines'],
        "hints": result['hints'],
        "events_triggered": [],
        "changes": {"started_conversation": target_npc.id}
    }


def say(state: GameState, registry: ContentRegistry, message: str) -> Dict[str, Any]:
    """Continue conversation with active NPC."""
    if not hasattr(state, 'active_conversation') or state.active_conversation is None:
        return {"lines": ["Non stai parlando con nessuno. Usa 'talk <nome>' per iniziare una conversazione."], 
                "hints": [], "events_triggered": [], "changes": {}}
    
    if not hasattr(registry, 'npc_registry') or registry.npc_registry is None:
        return {"lines": ["Sistema NPC non disponibile."], "hints": [], "events_triggered": [], "changes": {}}
    
    conversation = state.active_conversation
    npc = registry.npc_registry.get_npc(conversation['npc_id'])
    
    if npc is None:
        state.active_conversation = None
        return {"lines": ["L'NPC non è più disponibile."], "hints": [], "events_triggered": [], "changes": {}}
    
    dialogue_engine = conversation['engine']
    context = conversation['context']
    
    # Update context with current game state
    context.game_time = str(state.time_minutes)
    context.weather = state.weather
    
    result = dialogue_engine.process_dialogue_turn(npc, message, context)
    
    # End conversation if needed
    if not result['conversation_active']:
        state.active_conversation = None
        end_result = dialogue_engine.end_conversation(npc, context)
        result['lines'].extend(end_result['lines'])
    
    return {
        "lines": result['lines'],
        "hints": result['hints'],
        "events_triggered": [],
        "changes": {"dialogue_turn": message}
    }

# --- Save/Load System ---

def save_game(state: GameState, registry: ContentRegistry, slot_name: str = "quicksave") -> Dict[str, Any]:
    """Save the current game state to a named slot."""
    try:
        filepath = persistence.save_game(state, slot_name)
        return {
            "lines": [f"Gioco salvato in: {slot_name}", f"File: {filepath}"],
            "hints": [],
            "events_triggered": [],
            "changes": {"saved": True, "slot": slot_name}
        }
    except persistence.SaveError as e:
        return {
            "lines": [f"Errore nel salvataggio: {e}"],
            "hints": [],
            "events_triggered": [],
            "changes": {"saved": False, "error": str(e)}
        }

def load_game(current_state: GameState, registry: ContentRegistry, slot_name: str = None, filepath: str = None) -> Dict[str, Any]:
    """Load game state from a save file. Returns the loaded state in changes."""
    try:
        loaded_state = persistence.load_game(slot_name=slot_name, filepath=filepath)
        source = filepath or slot_name or "unknown"
        return {
            "lines": [f"Gioco caricato da: {source}", f"Posizione: {loaded_state.location_key()}", f"Giorno {loaded_state.day_count}, {loaded_state.time_string()}"],
            "hints": [],
            "events_triggered": [],
            "changes": {"loaded": True, "new_state": loaded_state, "source": source}
        }
    except persistence.SaveError as e:
        return {
            "lines": [f"Errore nel caricamento: {e}"],
            "hints": [],
            "events_triggered": [],
            "changes": {"loaded": False, "error": str(e)}
        }

def list_saves(state: GameState, registry: ContentRegistry) -> Dict[str, Any]:
    """List all available save files."""
    try:
        saves = persistence.list_saves()
        if not saves:
            return {
                "lines": ["Nessun salvataggio trovato."],
                "hints": [],
                "events_triggered": [],
                "changes": {}
            }
        
        lines = ["=== Salvataggi Disponibili ==="]
        for save in saves[:10]:  # Show max 10 recent saves
            time_str = f"{save['time_minutes'] // 60:02d}:{save['time_minutes'] % 60:02d}"
            lines.append(f"• {save['slot_name']} - Giorno {save['day_count']} {time_str} - {save['date_saved'][:16]}")
            lines.append(f"  Posizione: {save['location']}")
        
        if len(saves) > 10:
            lines.append(f"... e altri {len(saves) - 10} salvataggi")
            
        return {
            "lines": lines,
            "hints": [],
            "events_triggered": [],
            "changes": {"saves_count": len(saves)}
        }
    except Exception as e:
        return {
            "lines": [f"Errore nell'elenco salvataggi: {e}"],
            "hints": [],
            "events_triggered": [],
            "changes": {"error": str(e)}
        }

# --- Choice System ---

def choice(state: GameState, registry: ContentRegistry, action: str = None, target: str = None) -> Dict[str, Any]:
    """Handle narrative choices. Usage: choice list|present <id>|choose <option_id>|history"""
    if not action:
        return {
            "lines": ["Uso: choice list|present <id>|choose <option_id>|history"],
            "hints": [],
            "events_triggered": [],
            "changes": {}
        }
    
    action = action.lower()
    
    if action == "list":
        # List available choices (simplified - in full game would check conditions)
        available_choices = ["investigate_stone_marker", "respond_to_whisper", "npc_interaction_style"]
        return {
            "lines": ["Scelte disponibili:"] + [f"• {choice_id}" for choice_id in available_choices],
            "hints": [],
            "events_triggered": [],
            "changes": {}
        }
    
    elif action == "present" and target:
        result = choices.present_choice(target, state)
        if "error" in result:
            return {
                "lines": [f"Errore: {result['error']}"],
                "hints": [],
                "events_triggered": [],
                "changes": {}
            }
        
        lines = [
            f"=== {result['title']} ===",
            result['description'],
            "",
            "Opzioni disponibili:"
        ]
        for i, option in enumerate(result['options'], 1):
            lines.append(f"{i}. {option['text']}")
            if option['description']:
                lines.append(f"   {option['description']}")
        
        lines.append("")
        lines.append("Usa 'choice choose <numero>' per selezionare.")
        
        return {
            "lines": lines,
            "hints": [f"choice choose {i}" for i in range(1, len(result['options'])+1)],
            "events_triggered": [],
            "changes": {"presented_choice": result['choice_id']}
        }
    
    elif action == "choose" and target:
        try:
            # Handle numeric choice (1, 2, 3) or direct option ID
            if target.isdigit():
                choice_num = int(target) - 1
                if choices.choice_system.active_choice and 0 <= choice_num < len(choices.choice_system.active_choice.options):
                    option_id = choices.choice_system.active_choice.options[choice_num].id
                else:
                    return {
                        "lines": ["Numero di scelta non valido"],
                        "hints": [],
                        "events_triggered": [],
                        "changes": {}
                    }
            else:
                option_id = target
            
            result = choices.make_choice(option_id, state, registry)
            if "error" in result:
                return {
                    "lines": [f"Errore: {result['error']}"],
                    "hints": [],
                    "events_triggered": [],
                    "changes": {}
                }
            
            return result
            
        except (ValueError, IndexError):
            return {
                "lines": ["Scelta non valida"],
                "hints": [],
                "events_triggered": [],
                "changes": {}
            }
    
    elif action == "history":
        history = choices.get_choice_history(state)
        if not history:
            return {
                "lines": ["Nessuna scelta effettuata finora"],
                "hints": [],
                "events_triggered": [],
                "changes": {}
            }
        
        lines = ["=== Cronologia Scelte ==="]
        for entry in history:
            time_str = f"{entry['timestamp'] // 60:02d}:{entry['timestamp'] % 60:02d}"
            lines.append(f"Giorno {entry['day']} {time_str} - {entry['choice_id']}: {entry['option_id']}")
        
        return {
            "lines": lines,
            "hints": [],
            "events_triggered": [],
            "changes": {"history_length": len(history)}
        }
    
    else:
        return {
            "lines": ["Uso: choice list|present <id>|choose <option_id>|history"],
            "hints": [],
            "events_triggered": [],
            "changes": {}
        }


def process_npc_turn(npc, player, world, scene_context):
    """Process an NPC AI turn with structured output validation.
    
    This is a hook for the new NPC AI adapter system that enforces
    JSON schema validation and semantic correctness.
    
    Args:
        npc: NPC object
        player: Player state object
        world: World state
        scene_context: Dict with current scene information
        
    Returns:
        Dict with NPC response (validated JSON structure)
    """
    from ..npc.llm_adapter import npc_turn
    
    def llm_call(system=None, user=None, **kwargs):
        """LLM backend adapter - integrate with existing backend or mock."""
        # TODO: Integrate with actual LLM backend (Ollama/OpenAI/LM Studio)
        # For now, return a mock response for testing
        if hasattr(world, 'llm_backend'):
            return world.llm_backend.generate(system=system, user=user, **kwargs)
        else:
            # Mock response for testing
            import json
            mock_response = {
                "npc_id": npc.id,
                "mood": "neutral", 
                "intent": "greet",
                "action": None,
                "say": f"Hello, I am {npc.name}.",
                "memory_write": [],
                "relationship_delta": 0,
                "confidence": 0.8,
                "stop_speaking_after": 1
            }
            return json.dumps(mock_response)
    
    return npc_turn(llm_call, npc, player, world, scene_context)

# --- Protagonist Memory System ---

def maybe_trigger_memory(state: GameState, context: str = "", location: str = "") -> List[str]:
    """Check if a memory should be triggered and return memory messages."""
    memories = []
    
    # Memory triggers based on context and current state
    memory_triggers = {
        "first_forest_entry": {
            "condition": lambda s: s.flags.get("visited_bosco") and len(s.memory_fragments) == 0,
            "memory": "Un ricordo confuso affiora: eri già stato in un bosco simile, molto tempo fa. Le immagini sono sfocate, ma la sensazione di familiarità è forte."
        },
        "ancient_stone": {
            "condition": lambda s: s.flags.get("inspected_cippo") and not any(m.get("type") == "stone_memory" for m in s.memory_fragments),
            "memory": "Toccando la pietra antica, un frammento di memoria si cristallizza: qualcuno che conoscevi ti aveva parlato di questi simboli, ma non riesci a ricordare chi."
        },
        "forest_whisper": {
            "condition": lambda s: s.flags.get("heard_whisper") and s.flags.get("forest_connection"),
            "memory": "Il sussurro risveglia un'eco profonda nella tua mente. Una voce familiare, forse della tua infanzia, che ti chiamava con lo stesso tono misterioso."
        },
        "midnight_vision": {
            "condition": lambda s: s.flags.get("midnight_vision"),
            "memory": "La luce eterea ti ricorda un sogno ricorrente che hai fatto per anni. In quel sogno, seguivi sempre una luce simile verso qualcosa di importante."
        },
        "respectful_approach": {
            "condition": lambda s: s.flags.get("respectful_explorer") and context == "nature_interaction",
            "memory": "La tua cautela nel trattare con la natura ti ricorda gli insegnamenti di qualcuno del tuo passato: 'Rispetta sempre ciò che non comprendi.'"
        }
    }
    
    # Check memory triggers
    for memory_id, trigger in memory_triggers.items():
        if trigger["condition"](state):
            # Create memory fragment
            memory_fragment = {
                "type": "memory",
                "memory_id": memory_id,
                "text": trigger["memory"],
                "timestamp": state.time_minutes,
                "day": state.day_count,
                "location": state.location_key(),
                "context": context
            }
            
            state.memory_fragments.append(memory_fragment)
            state.timeline.append(memory_fragment)
            memories.append(f"[RICORDO] {trigger['memory']}")
    
    # Check for memory fragments triggered by ambient events
    if state.flags.get("memory_check_pending"):
        state.flags["memory_check_pending"] = False
        
        # Random memory based on current circumstances
        random_memories = [
            "Un profumo di terra umida ti riporta alla mente un giardino della tua infanzia.",
            "Il suono del vento tra le foglie evoca il ricordo di una ninna nanna dimenticata.",
            "La luce filtrata tra i rami ti ricorda una mattina speciale del passato.",
            "Un senso di nostalgia ti avvolge, come se questo posto custodisse parte della tua storia."
        ]
        
        memory_text = random.choice(random_memories)
        memory_fragment = {
            "type": "ambient_memory",
            "text": memory_text,
            "timestamp": state.time_minutes,
            "day": state.day_count,
            "location": state.location_key(),
            "context": "ambient"
        }
        
        state.memory_fragments.append(memory_fragment)
        memories.append(f"[RICORDO] {memory_text}")
    
    return memories

def memories(state: GameState, registry: ContentRegistry) -> Dict[str, Any]:
    """Display protagonist's memory fragments."""
    if not state.memory_fragments:
        return {
            "lines": ["Non hai ancora recuperato nessun ricordo significativo."],
            "hints": [],
            "events_triggered": [],
            "changes": {}
        }
    
    lines = ["=== Frammenti di Memoria ==="]
    
    # Sort memories by timestamp
    sorted_memories = sorted(state.memory_fragments, key=lambda m: (m.get("day", 0), m.get("timestamp", 0)))
    
    for memory in sorted_memories:
        time_str = f"{memory.get('timestamp', 0) // 60:02d}:{memory.get('timestamp', 0) % 60:02d}"
        day_str = f"Giorno {memory.get('day', 0)}"
        lines.append(f"{day_str} {time_str} - {memory['text']}")
    
    return {
        "lines": lines,
        "hints": [],
        "events_triggered": [],
        "changes": {"memory_count": len(state.memory_fragments)}
    }

