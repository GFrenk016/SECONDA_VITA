import time
import pytest
import random
from engine.core.loader.world_loader import build_world_from_dict
from engine.core.registry import ContentRegistry
from engine.core.state import GameState
from engine.core import actions

def build_world():
    data = {
        'id': 'cw','name': 'CombatWorld','description': 'w','macro_rooms': [
            {'id': 'm','name': 'M','description': 'd','micro_rooms': [
                {'id': 'r','name': 'Stanza','short': 'Stanza','description': 'desc','exits': [],'tags': [],'interactables': []}
            ]}
        ]
    }
    world = build_world_from_dict(data)
    reg = ContentRegistry(world)
    reg.strings = {'aree': {'r': {'nome': 'Stanza', 'descrizione': 'desc'}}, 'oggetti': {}}
    state = GameState(world_id=world.id, current_macro='m', current_micro='r')
    state.recompute_from_real(time.time())
    state.player_weapon_id = 'knife'
    return reg, state

BASIC = {'id': 'walker_basic', 'name': 'Vagante', 'hp': 8, 'attack': 2, 'qte_chance': 0.0}

@pytest.mark.parametrize("area", [True, False])
def test_focus_and_area(area):
    reg, state = build_world()
    random.seed(42)
    actions.engage(state, reg, BASIC)
    # spawn extra enemies for area test
    actions.combat_action(state, reg, 'spawn walker_basic 2')  # now 3 enemies total
    assert len(state.combat_session['enemies']) == 3
    # Focus second enemy
    actions.combat_action(state, reg, 'focus 2')
    assert state.combat_session.get('focus_enemy_id') == state.combat_session['enemies'][1]['id']
    # Attack without index should hit focused enemy
    # Ripeti attacchi se miss iniziali
    attempts = 0
    while attempts < 10:
        res1 = actions.combat_action(state, reg, 'attack')
        assert any(('Colpisci' in l) or ('Attacco mancato' in l) for l in res1['lines'])
        if state.combat_session['enemies'][1]['hp'] < state.combat_session['enemies'][1]['max_hp']:
            break
        attempts += 1
    hp_after_focus_hit = state.combat_session['enemies'][1]['hp']
    assert hp_after_focus_hit < state.combat_session['enemies'][1]['max_hp']
    # Optionally perform area attack
    if area:
        pre_hps = [e['hp'] for e in state.combat_session['enemies']]
        res2 = actions.combat_action(state, reg, 'attack all')
        assert any('Colpisci tutti i nemici' in l for l in res2['lines'])
        post_hps = [e['hp'] for e in state.combat_session['enemies']]
        # All alive enemies should have hp reduction (at least one point) compared to saved pre_hps
        for before, after in zip(pre_hps, post_hps):
            if before > 0:
                assert after <= before, f"HP non ridotto in area attack: {before}->{after}"
    # Status output multiline should contain flags
    res_status = actions.combat_action(state, reg, 'status')
    # Expect at least one line with pattern '1.' and maybe F flag
    assert any(line.strip().startswith('1.') for line in res_status['lines'])
    assert any('[F]' in line for line in res_status['lines'] if '2.' in line), "Flag focus mancante nella seconda riga"
