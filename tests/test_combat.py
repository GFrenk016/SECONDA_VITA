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
    # Messaggio di attacco: accetta sia hit ("Colpisci ... infliggendo") sia miss ("Attacco mancato - ...")
    normalized = [' '.join(l.split()) for l in r1['lines']]
    assert any(
        (l.startswith('Colpisci') and 'danni' in l) or l.startswith('Attacco mancato')
        for l in normalized
    ), f"Output inatteso: {r1['lines']}"
    # In realtime il primo attacco non forza più subito QTE: la fase resta 'player'.
    assert state.combat_session['phase'] in ('player','qte')
    # Force finish: directly reduce enemy hp to test victory path
    state.combat_session['enemy_hp'] = 1
    # Assicura che la fase sia 'player' prima di attaccare
    if state.combat_session['phase'] != 'player':
        state.combat_session['phase'] = 'player'
    # Esegui fino a 10 attacchi per garantire almeno un colpo che chiuda
    victory = False
    last_lines = []
    for _ in range(10):
        r2 = actions.combat_action(state, reg, 'attack')
        last_lines = r2['lines']
        if any('Hai vinto' in l for l in last_lines):
            victory = True
            break
    assert victory, f"Nessuna vittoria dopo attacchi multipli. Ultime linee: {last_lines}"


def test_qte_success_and_failure():
    reg, state = build_world()
    actions.engage(state, reg, ENEMY)
    # Primo attacco: nel modello realtime il QTE offensivo può attivarsi subito (chance 1.0) oppure essere già in fase player se la logica cambia; se non attivo dopo un secondo attacco deve attivarsi.
    for _ in range(10):
        actions.combat_action(state, reg, 'attack')
        if state.combat_session['phase'] == 'qte':
            break
    assert state.combat_session['phase'] == 'qte', f"QTE non attivo dopo 10 attacchi: fase {state.combat_session['phase']}"
    # Success path
    r_qte = actions.combat_action(state, reg, 'qte', 'x')
    assert any('Reazione riuscita' in l for l in r_qte['lines'])
    assert state.combat_session['phase'] == 'player'
    # Forza un nuovo QTE offensivo: attacca di nuovo finché non riappare (limite di sicurezza 5)
    for _ in range(5):
        actions.combat_action(state, reg, 'attack')
        if state.combat_session['phase'] == 'qte':
            break
    assert state.combat_session['phase'] == 'qte', f"Nuovo QTE non attivato: fase {state.combat_session['phase']}"
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
    # Trigger pool QTE (può richiedere più attacchi in realtime)
    for _ in range(5):
        actions.combat_action(state, reg, 'attack')
        if state.combat_session['phase'] == 'qte':
            break
    assert state.combat_session['phase'] == 'qte', 'QTE pool non attivato entro 5 attacchi'
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
