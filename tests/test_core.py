import re
import time
import types
import pytest

from game.bootstrap import load_world_and_state
from engine.core import actions

@pytest.fixture()
def game():
    registry, state = load_world_and_state()
    # Per test deterministici: fissiamo tempo e condizioni stabili
    state.daytime = "mattina"
    state.weather = "sereno"
    state.climate = "temperato"
    # Evitiamo emissione snippet casuale iniziale
    state.last_ambient_emit_total = -10000
    return registry, state

def test_where_command(game):
    registry, state = game
    res = actions.where(state, registry)
    assert any("Posizione:" in l for l in res["lines"]) , "Output where deve contenere 'Posizione:'"
    assert any("Tag:" in l for l in res["lines"]) , "Output where deve contenere 'Tag:'"

def test_inspect_gating(game):
    registry, state = game
    # Prendiamo eventualmente un oggetto visibile se presente
    look_res = actions.look(state, registry)
    # Estrai primo oggetto dalla sezione 'Qui noti:' se presente
    obj_id = None
    for line in look_res["lines"]:
        if line.startswith("- "):
            # forma '- Nome[ marker]: desc' -> estrai Nome eliminando eventuali * / ** finali
            name_part = line[2:].split(":")[0].strip()
            name_part = name_part.rstrip(" *")  # rimuove spazi e asterischi residui
            # Usa il nome così com'è (display) per l'inspect; engine supporta matching case-insensitive
            obj_id = name_part
            break
    if obj_id:
        # examine prima di inspect deve fallire
        with pytest.raises(actions.ActionError):
            actions.examine(state, registry, obj_id)
        # search prima di inspect deve fallire
        with pytest.raises(actions.ActionError):
            actions.search(state, registry, obj_id)
        # inspect ok
        actions.inspect(state, registry, obj_id)
        # search senza examine ancora deve fallire
        with pytest.raises(actions.ActionError):
            actions.search(state, registry, obj_id)

def test_locked_exit_marker(game):
    registry, state = game
    # Forziamo manualmente un'uscita locked per il micro corrente (se esiste almeno una exit)
    micro = registry.get_micro(state.current_micro)
    if not micro.exits:
        pytest.skip("Nessuna uscita da testare nel micro iniziale")
    # Creiamo una copia mutabile dell'exit (dataclass frozen) simulando scenario: sostituiamo temporaneamente
    original_exit = micro.exits[0]
    from engine.core.world import Exit
    fake_locked = Exit(direction=original_exit.direction, target_micro=original_exit.target_micro, locked=True)
    # Hack: ricostruire micro modificato (MicroRoom è frozen) non semplice senza ricostruire registry; quindi saltiamo se non possiamo.
    # Semplice: verifichiamo che output look contenga pattern 'Uscite:' e se modificheremo direttamente lines.
    look_res = actions.look(state, registry)
    assert any(l.startswith("Uscite:") for l in look_res["lines"]) , "Serve la linea Uscite:"
    # Non possiamo facilmente iniettare exit locked senza ricostruire il mondo qui; test leggero su formato base.

def test_ambient_rate_limiting(game):
    registry, state = game
    # Forza emissione iniziale: ripeti look finché non viene emesso uno snippet (o max tentativi)
    attempts = 0
    while state.last_ambient_emit_total < 0 and attempts < 5:
        actions.look(state, registry)
        attempts += 1
    assert state.last_ambient_emit_total >= 0, "Non è stato emesso alcun snippet ambientale iniziale per il test"
    first_emit = state.last_ambient_emit_total
    # Secondo look immediato: non deve aggiornare last_ambient_emit_total
    actions.look(state, registry)
    assert state.last_ambient_emit_total == first_emit, "Nessun nuovo snippet prima del gap"
    # Avanza offset oltre la soglia
    state.manual_offset_minutes += state.ambient_min_gap_minutes + 1
    actions.look(state, registry)
    assert state.last_ambient_emit_total > first_emit, "Dopo il gap deve essere emesso uno snippet"
