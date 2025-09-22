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
    return combat.start_combat(state, registry, enemy_def)

def combat_action(state: GameState, registry: ContentRegistry, command: str, arg: str | None = None) -> Dict[str, object]:
    """Esegue un'azione durante il combattimento: attack | status | qte <input> | push | flee."""
    return combat.resolve_combat_action(state, registry, command, arg)

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

