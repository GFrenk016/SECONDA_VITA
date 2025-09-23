import time, random
from engine.core.loader.world_loader import build_world_from_dict
from engine.core.registry import ContentRegistry
from engine.core.state import GameState
from engine.core import actions
from engine.core.combat import set_combat_seed, helper_reset_player_phase, helper_force_focus_autoswitch

def build_world():
    data = {'id':'cw','name':'CombatWorld','description':'w','macro_rooms':[{'id':'m','name':'M','description':'d','micro_rooms':[{'id':'r','name':'R','short':'R','description':'d','exits':[],'tags':[],'interactables':[]}]}]}
    world = build_world_from_dict(data)
    reg = ContentRegistry(world)
    reg.strings = {'aree': {'r': {'nome': 'R', 'descrizione': 'd'}}, 'oggetti': {}}
    state = GameState(world_id=world.id, current_macro='m', current_micro='r')
    state.recompute_from_real(time.time())
    state.player_weapon_id = 'knife'
    return reg, state

BASIC = {'id': 'walker_basic', 'name': 'Vagante', 'hp': 5, 'attack': 2, 'qte_chance': 0.0}

def test_attack_all_cooldown_and_focus_autoswitch():
    reg, state = build_world()
    set_combat_seed(123)
    actions.engage(state, reg, BASIC)
    actions.combat_action(state, reg, 'spawn walker_basic 2')  # total 3
    # Primo attack all
    res = actions.combat_action(state, reg, 'attack all')
    assert any('Colpisci tutti i nemici' in l for l in res['lines'])
    cd_total = state.combat_session.get('attack_all_cooldown_total')
    assert cd_total is not None
    # Tentativo immediato -> cooldown message
    res_cd = actions.combat_action(state, reg, 'attack all')
    assert any('non è pronto' in l for l in res_cd['lines'])
    # Avanziamo tempo simulato fino a cooldown
    target_min = cd_total - state.combat_session['enemies'][0]['attack_interval'] + 1
    # Forziamo orologio direttamente (simulate) incrementando state.time_minutes
    while state.time_minutes < cd_total:
        state.time_minutes += 1
    # Reset eventuale QTE e forza fase player
    helper_reset_player_phase(state)
    # Nuovo attack all ora consentito
    res2 = actions.combat_action(state, reg, 'attack all')
    assert any('Colpisci tutti i nemici' in l for l in res2['lines'])
    # Uccidi manualmente il nemico focus e verifica auto-switch
    helper_reset_player_phase(state)
    actions.combat_action(state, reg, 'focus 1')
    focus_id = state.combat_session.get('focus_enemy_id')
    # Portiamo a 0 hp focus
    for e in state.combat_session['enemies']:
        if e['id'] == focus_id:
            e['hp'] = 0
    # Trigger status (che causa auto switch via prossime azioni di sync se presenti)
    actions.combat_action(state, reg, 'status')
    helper_force_focus_autoswitch(state)
    helper_reset_player_phase(state)
    actions.combat_action(state, reg, 'focus 1')
    new_focus = state.combat_session.get('focus_enemy_id')
    assert new_focus is None or new_focus != focus_id  # se tutti morti focus rimosso
