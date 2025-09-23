#!/usr/bin/env python3
"""Debug the failing test."""

import time, random, pytest
from engine.core.state import GameState
from engine.core.loader.world_loader import build_world_from_dict
from engine.core.registry import ContentRegistry
from engine.core import actions

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

# Test the attack
reg, state = build_world()
print("Starting combat...")
result = actions.engage(state, reg, ENEMY)
print("Engage result:", result)

print("\nState after engage:")
print("  Combat session:", state.combat_session)

print("\nExecuting attack...")
r1 = actions.combat_action(state, reg, 'attack')
print("Attack result lines:", r1['lines'])
print("Attack result:", r1)

print("\nState after attack:")
print("  Player HP:", state.player_hp)
print("  Combat session phase:", state.combat_session.get('phase'))
print("  Enemy HP:", state.combat_session.get('enemy_hp'))