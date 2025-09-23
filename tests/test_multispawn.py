import time
import pytest
from engine.core.loader.world_loader import build_world_from_dict
from engine.core.registry import ContentRegistry
from engine.core.state import GameState
from engine.core import actions
from engine.core.combat import MOBS

# Reuse minimal world setup

def build_world():
    data = {
        'id': 'cw',
        'name': 'CombatWorld',
        'description': 'w',
        'macro_rooms': [
            {
                'id': 'm', 'name': 'M', 'description': 'd', 'micro_rooms': [
                    {
                        'id': 'r', 'name': 'Stanza', 'short': 'Stanza', 'description': 'desc',
                        'exits': [], 'tags': [], 'interactables': []
                    }
                ]
            }
        ]
    }
    world = build_world_from_dict(data)
    reg = ContentRegistry(world)
    reg.strings = {'aree': {'r': {'nome': 'Stanza', 'descrizione': 'desc'}}, 'oggetti': {}}
    state = GameState(world_id=world.id, current_macro='m', current_micro='r')
    state.recompute_from_real(time.time())
    state.player_weapon_id = 'knife'
    return reg, state

BASIC = {
    'id': 'walker_basic', 'name': 'Vagante', 'hp': 6, 'attack': 2,
    'qte_chance': 0.0,  # disabilitiamo QTE offensivi per semplicità test multi spawn
}

def test_multi_spawn_additions():
    reg, state = build_world()
    # Inizia combattimento con primo nemico
    actions.engage(state, reg, BASIC)
    assert state.combat_session
    assert len(state.combat_session['enemies']) == 1
    base_name = state.combat_session['enemies'][0]['name']
    # Spawna un altro identico
    actions.combat_action(state, reg, 'spawn walker_basic')
    assert len(state.combat_session['enemies']) == 2
    names = [e['name'] for e in state.combat_session['enemies']]
    assert any('(2)' in n for n in names), f"Nome con suffisso mancante: {names}"
    # Spawna due insieme
    actions.combat_action(state, reg, 'spawn walker_basic 2')
    assert len(state.combat_session['enemies']) == 4
    ids = [e['id'] for e in state.combat_session['enemies']]
    # ID unici
    assert len(ids) == len(set(ids)), f"ID duplicati: {ids}"
    # Attacca specifico indice 3 (terzo nemico vivo)
    # Prova fino a 3 attacchi sul terzo nemico per assicurare almeno un colpo
    attempts = 0
    while attempts < 3:
        res = actions.combat_action(state, reg, 'attack 3')
        assert any(('Colpisci' in l) or ('Attacco mancato' in l) for l in res['lines'])
        if state.combat_session['enemies'][2]['hp'] < state.combat_session['enemies'][2]['max_hp']:
            break
        attempts += 1
    assert state.combat_session['enemies'][2]['hp'] < state.combat_session['enemies'][2]['max_hp']
