#!/usr/bin/env python3
"""Debug combat damage calculation."""

from engine.core.combat import *
from engine.core.combat_system.models import *
from engine.core.combat_system.resolver import CombatResolver
from engine.core.loader.content_loader import load_combat_content
import random

# Load content
weapons, mobs = load_combat_content()  
inject_content(weapons, mobs)

print("Weapons loaded:", list(WEAPONS.keys()))
print("Mobs loaded:", list(MOBS.keys()))

# Get walker data
walker_data = MOBS['walker_basic']
print("\nWalker resistances:", walker_data.get('resistances', {}))

# Create knife move manually
knife_data = WEAPONS['knife']
light_moveset = knife_data['movesets']['light']

light_move = MoveSpec(
    id="knife_light",
    name="Light Slash",
    move_type="light", 
    stamina_cost=light_moveset['stamina_cost'],
    damage_base=knife_data['damage'] * light_moveset['damage_multiplier'],
    damage_type=DamageType(knife_data['damage_type'])
)
print("Light move damage_base:", light_move.damage_base)
print("Walker slash resistance:", walker_data['resistances']['slash'])
print("Expected final damage:", light_move.damage_base * walker_data['resistances']['slash'])

# Create resolver and test  
resolver = CombatResolver()
player_data = {'max_stamina': 100, 'max_posture': 100.0, 'weapon_handling': 0.6, 'resistances': {}}
enemy_data = walker_data.copy()

resolver.initialize_entity('player', player_data)  
resolver.initialize_entity('walker_basic', enemy_data)

# Test attack
print(f"\n--- Attack Test ---")
ctx = CombatContext('player', 'walker_basic', light_move)
random.seed(42)  
result = resolver.resolve_attack(ctx, player_data, enemy_data)

print('Success:', result.success)
print('Hit quality:', result.hit_quality)
if result.damage_dealt:
    for dmg in result.damage_dealt:
        print(f'  Final damage: {dmg.amount:.2f} {dmg.damage_type.value}')
else:
    print('  No damage dealt')
print('Stamina consumed:', result.stamina_consumed)
print('Events:', [e.get('type') for e in result.events])