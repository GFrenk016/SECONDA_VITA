import time, random, pytest
from engine.core.loader.world_loader import build_world_from_dict
from engine.core.registry import ContentRegistry
from engine.core.state import GameState
from engine.core import actions

# Mini world builder for isolated logic tests

def build_mini_world():
    data = {
        "id": "mini",
        "name": "Mini",
        "description": "Test world",
        "macro_rooms": [
            {
                "id": "macro",
                "name": "Macro",
                "description": "",
                "micro_rooms": [
                    {
                        "id": "hall",
                        "name": "Sala Centrale",
                        "short": "Sala",
                        "description": "Una sala neutra di test.",
                        "tags": ["indoor"],
                        "exits": [
                            {"direction": "e", "target_micro": "corridoio", "locked": True, "lock_flag": "door_unlocked"}
                        ],
                        "interactables": [
                            {"id": "tavolo", "alias": "tavolo_di_legno"},
                            {"id": "glifo", "visible_flag": "is_night"},
                        ],
                    },
                    {
                        "id": "corridoio",
                        "name": "Corridoio di Test",
                        "short": "Corridoio",
                        "description": "Un corridoio semplice.",
                        "tags": [],
                        "exits": [
                            {"direction": "w", "target_micro": "hall"}
                        ],
                        "interactables": []
                    }
                ],
            }
        ],
    }
    world = build_world_from_dict(data)
    registry = ContentRegistry(world)
    # Minimi strings per nomi/descrizioni oggetti
    registry.strings = {
        "aree": {
            "hall": {"nome": "Sala Centrale", "descrizione": "Una sala neutra di test."},
            "corridoio": {"nome": "Corridoio di Test", "descrizione": "Un corridoio semplice."},
        },
        "oggetti": {
            "tavolo": {"nome": "Tavolo", "descrizione": "Un tavolo robusto con superfici graffiate."},
            "glifo": {"nome": "Glifo", "descrizione": "Un glifo tenue che si percepisce solo al buio."},
        },
    }
    registry.inspectables = {
        "tavolo": {
            "titolo": "Tavolo di Prova",
            "prima_volta": "Il tavolo mostra segni di antiche lavorazioni.",
            "successive": "Il tavolo non è cambiato.",
            "examine": "A distanza ravvicinata noti micro incisioni.",
            "search": "Tra le fessure trovi una sequenza 1-3-2.",
        }
    }  # type: ignore
    state = GameState(world_id=world.id, current_macro="macro", current_micro="hall")
    state.recompute_from_real(time.time())
    # Per stabilità test
    state.weather = "pioggia"  # così test indoor rain
    state.daytime = "giorno"
    return registry, state

@pytest.fixture()
def mini():
    return build_mini_world()

def test_look_first_vs_revisit_and_change(mini):
    registry, state = mini
    first = actions.look(state, registry)
    assert any("Sala Centrale" in l for l in first["lines"]) and any("Una sala neutra" in l for l in first["lines"]) , "Prima visita deve avere descrizione completa"
    # Revisita immediata
    second = actions.look(state, registry)
    # Ora dovrebbe mostrare solo il nome (non ripetere la descrizione intera)
    body = [l for l in second["lines"] if not l.startswith("[")]
    # La descrizione lunga non deve comparire identica
    assert not any("Una sala neutra di test." in l for l in body[1:]), "Revisita sintetica attesa"
    # Cambia meteo per generare variante (firma diversa): vogliamo la forma sintetica con em dash
    state.weather = "nebbia"
    third = actions.look(state, registry)
    # Accettiamo due forme: con em dash (variazione) oppure, in fallback, solo il nome se la variazione è vuota.
    assert any("Sala Centrale —" in l or l.strip() == "Sala Centrale" for l in third["lines"]), "Dovrebbe mostrare variante sintetica (nome o nome —)"

def test_inspect_suggestions(mini):
    registry, state = mini
    # Prima inspect
    r1 = actions.inspect(state, registry, "tavolo")
    assert any("Possibile: examine" in l for l in r1["lines"]), "Dovrebbe suggerire examine"
    r2 = actions.examine(state, registry, "tavolo")
    assert any("Possibile: search" in l for l in r2["lines"]), "Dovrebbe suggerire search"
    r3 = actions.search(state, registry, "tavolo")
    assert not any("Possibile:" in l for l in r3["lines"]), "Nessun suggerimento dopo search"
    # Re-inspect successive
    r4 = actions.inspect(state, registry, "tavolo")
    assert any("Il tavolo non è cambiato" in l for l in r4["lines"]), "Dovrebbe usare il testo 'successive'"

def test_partial_and_ambiguous_matching(mini):
    registry, state = mini
    # Partial substring
    actions.inspect(state, registry, "tav")  # non deve alzare
    # Aggiungiamo un secondo oggetto con nome che crea ambiguità
    registry.strings["oggetti"]["tavolette"] = {"nome": "Tavolette", "descrizione": "Piccole tavolette."}
    # Simuliamo che l'oggetto esista come interactable (append temporaneo)
    hall = registry.get_micro("hall")
    from engine.core.world import InteractableRef
    hall.interactables.append(InteractableRef(id="tavolette"))  # type: ignore[attr-defined]
    with pytest.raises(actions.ActionError):
        actions.inspect(state, registry, "tavo")

def test_locked_exit_and_unlock(mini):
    registry, state = mini
    # Uscita est -> bloccata
    look1 = actions.look(state, registry)
    assert any("(bloccata)" in l for l in look1["lines"]) , "Marker bloccata atteso"
    # Sblocca flag
    state.flags["door_unlocked"] = True
    look2 = actions.look(state, registry)
    assert not any("(bloccata)" in l for l in look2["lines"]), "Marker deve sparire dopo unlock"

def test_night_visibility(mini):
    registry, state = mini
    # glifo visibile solo di notte
    look_day = actions.look(state, registry)
    assert not any("Glifo" in l for l in look_day["lines"]) , "Glifo non deve essere visibile di giorno"
    # Usa wait_until per coerenza con meccanismo engine
    actions.wait_until(state, registry, "notte")
    look_night = actions.look(state, registry)
    assert any("Glifo" in l for l in look_night["lines"]) , "Glifo deve essere visibile di notte"

def test_indoor_rain_snippet(mini):
    registry, state = mini
    # world già indoor + weather=pioggia da builder
    # Prima visita per fissare stato
    actions.look(state, registry)
    # Forziamo emissione deterministica al prossimo intervallo disponibile
    state.manual_offset_minutes += state.ambient_min_gap_minutes + 1
    state.force_ambient_key = "indoor_pioggia"
    res = actions.look(state, registry)
    joined = " ".join(res["lines"]).lower()
    assert any(k in joined for k in ["gocciolii", "fruscio", "tamburellare"]), "Snippet indoor_pioggia forzato non trovato"

def test_wait_until_phases(mini):
    registry, state = mini
    state.daytime = "mattina"
    # Already in phase
    r1 = actions.wait_until(state, registry, "mattina")
    assert any("Sei già" in l for l in r1["lines"]), "Messaggio 'Sei già' atteso"
    # Salta a notte
    r2 = actions.wait_until(state, registry, "notte")
    assert state.daytime == "notte", "Fase notturna raggiunta"
