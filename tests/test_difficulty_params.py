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

BASE_ENEMY = {
    'id': 'tester', 'name': 'Tester', 'hp': 5, 'attack': 2,
    'qte_chance': 0.0, 'qte_prompt': '', 'qte_expected': '', 'qte_window_minutes': 2,
    'attack_interval_minutes': 2, 'defensive_qte_window': 1
}

def advance_to_next_attack(state):
    sess = state.combat_session
    target = sess['next_enemy_attack_total']
    now_total = state.day_count*24*60 + state.time_minutes
    delta = (target - now_total)
    state.manual_offset_minutes += delta
    state.recompute_from_real(time.time())
    actions.combat_action(state, None, 'status')  # process events (registry not needed for status)


def test_damage_multiplier_affects_incoming_damage():
    reg, state = build_world()
    strong_enemy = BASE_ENEMY | {'id':'strong','attack':2,'attack_damage_multiplier':2.5}
    actions.engage(state, reg, strong_enemy)
    start_hp = state.player_hp
    advance_to_next_attack(state)
    # Il QTE difensivo appare: lasciamo scadere finestra
    sess = state.combat_session
    # Forza scadenza finestra
    state.manual_offset_minutes += sess['defensive_qte_window']
    state.recompute_from_real(time.time())
    actions.combat_action(state, reg, 'status')
    assert state.player_hp < start_hp - 3  # 2 * 2.5 = 5 danni attesi, quindi >3


def test_interval_multiplier_makes_attacks_faster():
    reg, state = build_world()
    fast_enemy = BASE_ENEMY | {'id':'fast','attack_interval_multiplier':0.5,'attack_interval_minutes':4}
    actions.engage(state, reg, fast_enemy)
    sess = state.combat_session
    base_interval = 4
    expected_interval = max(1, int(base_interval * 0.5))
    assert sess['enemy_attack_interval'] == expected_interval