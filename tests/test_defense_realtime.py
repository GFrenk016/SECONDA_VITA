import time
from engine.core.state import GameState
from engine.core.loader.world_loader import build_world_from_dict
from engine.core.registry import ContentRegistry
from engine.core import actions

def build_world():
    data = {'id':'cw','name':'CombatWorld','description':'w','macro_rooms':[{'id':'m','name':'M','description':'d','micro_rooms':[{'id':'r','name':'Stanza','short':'Stanza','description':'desc','exits':[],'tags':[],'interactables':[]}]}]}
    world = build_world_from_dict(data)
    reg = ContentRegistry(world)
    reg.strings = {'aree': {'r': {'nome': 'Stanza', 'descrizione': 'desc'}}, 'oggetti': {}}
    state = GameState(world_id=world.id, current_macro='m', current_micro='r')
    state.recompute_from_real(time.time())
    state.player_weapon_id = 'knife'
    return reg, state

ENEMY = {
    'id': 'walker', 'name': 'Walker', 'hp': 5, 'attack': 2,
    'qte_chance': 0.0, 'qte_prompt': '', 'qte_expected': '', 'qte_window_minutes': 2,
    'attack_interval_minutes': 2, 'defensive_qte_window': 1
}

def test_defensive_qte_parry():
    reg, state = build_world()
    actions.engage(state, reg, ENEMY)
    # Avanza il tempo fino al prossimo attacco nemico: manipola manual_offset_minutes e recompute.
    sess = state.combat_session
    target = sess['next_enemy_attack_total']
    # Calcola differenza minuti rispetto ora
    now_total = state.day_count*24*60 + state.time_minutes
    delta = (target - now_total)
    state.manual_offset_minutes += delta
    state.recompute_from_real(time.time())
    # Chiedi status per processare eventi realtime
    r_status = actions.combat_action(state, reg, 'status')
    # Ora dovrebbe essere comparso un QTE difensivo
    assert state.combat_session['phase'] == 'qte'
    assert state.combat_session['qte']['type'] == 'defense'
    # Esegui parata corretta
    r_qte = actions.combat_action(state, reg, 'qte', 'd')
    assert any('Parata riuscita' in l for l in r_qte['lines'])
    assert state.combat_session['phase'] == 'player'
