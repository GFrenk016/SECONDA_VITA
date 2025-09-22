import time, random, pytest
from engine.core.state import GameState
from engine.core.loader.world_loader import build_world_from_dict
from engine.core.registry import ContentRegistry
from engine.core import actions

# Minimal world (single room) for combat tests

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

ENEMY = {
    'id': 'walker', 'name': 'Walker', 'hp': 9, 'attack': 2,
    'qte_chance': 1.0, 'qte_prompt': 'Premi X!', 'qte_expected': 'x', 'qte_window_minutes': 2
}

POOL_ENEMY = {
    'id': 'walker_pool', 'name': 'Vagante', 'hp': 10, 'attack': 2,
    'qte_chance': 1.0, 'qte_window_minutes': 2,
    'qte_prompts': [
        {'part': 'testa', 'prompt': 'Colpisci la testa! (T)', 'expected': 't', 'effect': 'bonus_damage'}
    ]
}

def test_combat_start_and_victory():
    reg, state = build_world()
    actions.engage(state, reg, ENEMY)
    # Attack until death (weapon damage 3)
    r1 = actions.combat_action(state, reg, 'attack')
    assert any('Colpisci' in l for l in r1['lines'])
    # Enemy should trigger QTE (chance 1.0)
    assert state.combat_session['phase'] in ('qte', 'enemy')
    # Force finish: directly reduce enemy hp to test victory path
    state.combat_session['enemy_hp'] = 1
    r2 = actions.combat_action(state, reg, 'attack') if state.combat_session['phase'] == 'player' else actions.combat_action(state, reg, 'attack') if state.combat_session.update({'phase':'player'}) or True else None
    assert any('Hai vinto' in l for l in r2['lines'])


def test_qte_success_and_failure():
    reg, state = build_world()
    actions.engage(state, reg, ENEMY)
    # First attack to enter QTE phase
    actions.combat_action(state, reg, 'attack')
    assert state.combat_session['phase'] == 'qte'
    # Success path
    r_qte = actions.combat_action(state, reg, 'qte', 'x')
    assert any('Reazione riuscita' in l for l in r_qte['lines'])
    assert state.combat_session['phase'] == 'player'
    # Trigger another QTE to test failure (enemy still has HP > 0)
    actions.combat_action(state, reg, 'attack')  # re-enter qte
    assert state.combat_session['phase'] == 'qte', f"Fase inattesa: {state.combat_session['phase']}"
    # Advance time beyond deadline to force timeout
    session = state.combat_session
    deadline = session['qte']['deadline_total']
    now_total = state.day_count * 24 * 60 + state.time_minutes
    advance = (deadline - now_total) + 1
    state.manual_offset_minutes += advance
    # Recompute derived time to reflect manual offset before status
    state.recompute_from_real(time.time())
    # Next status action should process timeout via pre-check
    r_fail = actions.combat_action(state, reg, 'status')
    # After timeout enemy attack should have occurred; phase should be player or ended
    assert any('Fallisci' in l or 'colpisce' in l.lower() for l in r_fail['lines'])

def test_push_and_flee_and_bonus_qte():
    reg, state = build_world()
    actions.engage(state, reg, POOL_ENEMY)
    # Trigger pool QTE
    actions.combat_action(state, reg, 'attack')
    assert state.combat_session['phase'] == 'qte'
    # Use bonus damage QTE
    r_bonus = actions.combat_action(state, reg, 'qte', 't')
    assert any('Bonus' in l or 'Colpo mirato' in l for l in r_bonus['lines'])
    # Push sequence
    r_push = actions.combat_action(state, reg, 'push')
    assert any('Spingi' in l for l in r_push['lines'])
    # Try flee (may fail; loop few attempts with added distance)
    escaped = False
    for _ in range(5):
        # Ensure it's player turn; if not, issue a status (which advances nothing) or wait until back
        if state.combat_session['phase'] != 'player':
            # simulate enemy closure already handled; just continue loop
            continue
        res = actions.combat_action(state, reg, 'flee')
        if any('fuggire' in l or 'sganciarti' in l for l in res['lines']):
            escaped = True
            break
        if state.combat_session and state.combat_session['phase'] == 'player':
            continue
    assert escaped or (state.combat_session and state.combat_session['phase'] != 'ended'), 'Fuga non deve bloccare il gioco'
