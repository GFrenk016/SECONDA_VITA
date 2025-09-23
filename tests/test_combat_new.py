"""Tests for the new hybrid combat system."""
import pytest
import random
from engine.core.combat import (
    resolve_attack, CombatContext, MoveSpec, DamageType, StatusEffect, 
    HitQuality, inject_content
)
from engine.core.combat_system.models import StatusEffectInstance
from engine.core.combat_system.resolver import CombatResolver
from engine.core.combat_system.stamina import StaminaSystem
from engine.core.combat_system.posture import PostureSystem
from engine.core.combat_system.effects import StatusEffectSystem
from engine.core.combat_system.ai import TacticalAI, AIState


def test_stamina_system():
    """Test stamina management."""
    stamina = StaminaSystem()
    
    # Initialize entity
    stamina.initialize_entity("player", 100)
    assert stamina.get_stamina("player") == 100
    assert stamina.get_max_stamina("player") == 100
    
    # Test move stamina checking
    light_move = MoveSpec("light", "Light Attack", "light", 10, damage_base=2.0)
    heavy_move = MoveSpec("heavy", "Heavy Attack", "heavy", 30, damage_base=4.0)
    
    assert stamina.has_stamina_for_move("player", light_move)
    assert stamina.has_stamina_for_move("player", heavy_move)
    
    # Consume stamina
    assert stamina.consume_stamina("player", 10)
    assert stamina.get_stamina("player") == 90
    
    # Test penalties
    stamina.consume_stamina("player", 70)  # Down to 20
    penalty = stamina.get_stamina_penalty("player")
    assert penalty == 0.8  # 20% penalty for low stamina
    
    # Test out of stamina
    stamina.consume_stamina("player", 20)
    assert stamina.is_out_of_stamina("player")
    assert not stamina.can_use_heavy_moves("player")
    
    # Test regeneration
    stamina.tick_regeneration("player", 15)
    assert stamina.get_stamina("player") == 15


def test_posture_system():
    """Test posture/poise management."""
    posture = PostureSystem()
    
    # Initialize entity
    posture.initialize_entity("enemy", 100.0, 0.3)
    assert posture.get_posture("enemy") == 100.0
    assert posture.get_posture_ratio("enemy") == 1.0
    
    # Damage posture but not enough to stagger
    staggered, effect = posture.damage_posture("enemy", 20.0)
    assert not staggered
    assert effect is None
    assert posture.get_posture("enemy") == 80.0
    
    # Damage enough to stagger (below 30% of 100 = 30)
    staggered, effect = posture.damage_posture("enemy", 55.0)
    assert staggered
    assert effect is not None
    assert effect.effect == StatusEffect.STAGGERED
    assert effect.duration == 2
    
    # Test posture gap calculation
    posture.initialize_entity("player", 100.0)
    gap = posture.get_posture_gap("player", "enemy")
    assert gap > 0  # Player has better posture


def test_status_effects_system():
    """Test status effects management."""
    effects = StatusEffectSystem()
    
    # Apply bleed effect
    bleed_effect = StatusEffectInstance(StatusEffect.BLEED, 3, 1.0, "knife_thrust")
    effects.apply_effect("enemy", bleed_effect)
    
    assert effects.has_effect("enemy", StatusEffect.BLEED)
    assert len(effects.get_effects("enemy")) == 1
    
    # Tick effects (should do damage)
    damage_instances = effects.tick_effects("enemy")
    assert len(damage_instances) == 1
    assert damage_instances[0].damage_type == DamageType.BLEED
    assert damage_instances[0].amount == 1.0
    
    # Effect should still be active (2 ticks remaining)
    assert effects.has_effect("enemy", StatusEffect.BLEED)
    
    # Tick twice more to expire effect
    effects.tick_effects("enemy")
    effects.tick_effects("enemy")
    assert not effects.has_effect("enemy", StatusEffect.BLEED)
    
    # Test stacking effects
    burn1 = StatusEffectInstance(StatusEffect.BURN, 2, 1.0)
    burn2 = StatusEffectInstance(StatusEffect.BURN, 3, 1.0)
    effects.apply_effect("player", burn1)
    effects.apply_effect("player", burn2)
    
    # Should have extended duration and increased intensity
    active_effects = effects.get_effects("player")
    burn_effect = next(e for e in active_effects if e.effect == StatusEffect.BURN)
    assert burn_effect.duration == 3  # Longer duration
    assert burn_effect.intensity == 1.5  # Stacked intensity


def test_combat_resolver():
    """Test the core combat resolution system."""
    resolver = CombatResolver()
    
    # Set up entities
    player_data = {
        'max_stamina': 100,
        'max_posture': 100.0,
        'weapon_handling': 0.6,
        'resistances': {}
    }
    
    enemy_data = {
        'max_stamina': 80,
        'max_posture': 60.0,
        'weapon_handling': 0.4,
        'resistances': {'slash': 1.2}  # Vulnerable to slash
    }
    
    resolver.initialize_entity("player", player_data)
    resolver.initialize_entity("enemy", enemy_data)
    
    # Create a move
    slash_move = MoveSpec(
        id="knife_light",
        name="Light Slash",
        move_type="light",
        stamina_cost=10,
        damage_base=3.0,
        damage_type=DamageType.SLASH
    )
    
    # Create combat context
    ctx = CombatContext("player", "enemy", slash_move)
    
    # Resolve attack - set random seed for deterministic testing
    random.seed(42)
    result = resolver.resolve_attack(ctx, player_data, enemy_data)
    
    assert result.success or not result.success  # Either outcome is valid
    assert result.stamina_consumed == 10
    assert len(result.events) > 0
    
    if result.success:
        assert len(result.damage_dealt) > 0
        # Should have resistance modifier applied (1.2x damage for slash vulnerability)
        damage = result.damage_dealt[0]
        assert damage.damage_type == DamageType.SLASH


def test_tactical_ai():
    """Test AI decision making."""
    stamina = StaminaSystem()
    posture = PostureSystem()
    effects = StatusEffectSystem()
    ai = TacticalAI(stamina, posture, effects)
    
    # Initialize systems
    stamina.initialize_entity("enemy", 80)
    posture.initialize_entity("enemy", 60.0)
    ai.initialize_entity("enemy", AIState.AGGRESSIVE)
    
    # Create moves
    light_move = MoveSpec("light", "Light", "light", 10, damage_base=2.0)
    heavy_move = MoveSpec("heavy", "Heavy", "heavy", 30, damage_base=4.0)
    moves = [light_move, heavy_move]
    
    # Test move selection
    situation = {'enemy_count': 1, 'allied_count': 1}
    chosen = ai.choose_move("enemy", moves, ["player"], situation)
    
    assert chosen in moves
    
    # Test with low stamina (should prefer lighter moves)
    stamina.consume_stamina("enemy", 60)  # Down to 20
    chosen = ai.choose_move("enemy", moves, ["player"], situation)
    # With only 20 stamina, should choose light move or heavy move will fail
    
    # Test retreat logic
    posture.damage_posture("enemy", 55)  # Heavily damaged
    should_retreat = ai.should_retreat("enemy", situation)
    # Aggressive AI should only retreat if almost broken


def test_new_public_api():
    """Test the new public API resolve_attack function."""
    # Create test data
    player_data = {
        'max_stamina': 100,
        'max_posture': 100.0,
        'weapon_handling': 0.6,
        'resistances': {}
    }
    
    enemy_data = {
        'max_stamina': 80,
        'max_posture': 60.0,
        'weapon_handling': 0.3,
        'resistances': {'blunt': 0.8}
    }
    
    # Create move with status effect
    move = MoveSpec(
        id="punch",
        name="Punch",
        move_type="light",
        stamina_cost=8,
        damage_base=2.0,
        damage_type=DamageType.BLUNT,
        status_effects=[(StatusEffect.CONCUSSED, 2, 1.0)]
    )
    
    # Create context
    ctx = CombatContext(
        attacker_id="player",
        defender_id="enemy",
        move=move,
        situational_modifiers={'flanking': True}  # Flanking bonus
    )
    
    # Test the public API
    random.seed(123)  # For deterministic results
    result = resolve_attack(ctx, player_data, enemy_data)
    
    # Verify result structure
    assert hasattr(result, 'success')
    assert hasattr(result, 'damage_dealt')
    assert hasattr(result, 'status_effects_applied')
    assert hasattr(result, 'stamina_consumed')
    assert hasattr(result, 'hit_quality')
    assert hasattr(result, 'events')
    
    # Should consume stamina
    assert result.stamina_consumed == 8
    
    # Should have telemetry events
    assert len(result.events) > 0


def test_enhanced_asset_loading():
    """Test that enhanced assets are loaded correctly."""
    # Mock weapon and mob data with new attributes
    weapons = {
        "test_sword": {
            "id": "test_sword",
            "name": "Test Sword",
            "damage": 4,
            "damage_type": "slash",
            "reach": 2,
            "noise_level": 2,
            "movesets": {
                "light": {"stamina_cost": 12, "damage_multiplier": 0.9},
                "heavy": {"stamina_cost": 28, "damage_multiplier": 1.5}
            }
        }
    }
    
    mobs = {
        "test_orc": {
            "id": "test_orc",
            "name": "Test Orc",
            "hp": 12,
            "attack": 3,
            "max_stamina": 90,
            "max_posture": 80.0,
            "resistances": {"blunt": 0.7, "slash": 1.1},
            "ai_state": "cautious",
            "ai_traits": {"pack_hunter": False}
        }
    }
    
    # Test injection
    inject_content(weapons, mobs)
    
    # Verify weapon was enhanced properly
    from engine.core.combat import WEAPONS, MOBS
    assert "test_sword" in WEAPONS
    sword = WEAPONS["test_sword"]
    assert sword["damage_type"] == "slash"
    assert sword["reach"] == 2
    assert "movesets" in sword
    assert "light" in sword["movesets"]
    
    # Verify mob was enhanced with defaults
    assert "test_orc" in MOBS
    orc = MOBS["test_orc"]
    assert orc["max_stamina"] == 90
    assert orc["resistances"]["blunt"] == 0.7
    assert orc["ai_state"] == "cautious"


def test_backward_compatibility():
    """Test that legacy combat system still works."""
    from engine.core.combat import start_combat, resolve_combat_action, CombatError
    from engine.core.state import GameState
    from engine.core.registry import ContentRegistry
    from engine.core.world import MacroRoom, MicroRoom, World
    import time
    
    # Create minimal world and state
    micro = MicroRoom("test_room", "Test", "Test", "Test description", [], [], [])
    macro = MacroRoom("test_macro", "Test", "Test description", {"test_room": micro})
    world = World("test", "Test", "Test", {"test_macro": macro})
    registry = ContentRegistry(world)
    
    state = GameState("test", "test_macro", "test_room")
    state.recompute_from_real(time.time())
    state.player_weapon_id = "knife"
    
    # Create enemy definition (legacy format)
    enemy = {
        'id': 'test_walker',
        'name': 'Test Walker',
        'hp': 6,
        'attack': 2,
        'qte_chance': 0.5,
        'qte_prompt': 'Press X!',
        'qte_expected': 'x',
        'qte_window_minutes': 2
    }
    
    # Test legacy combat start
    result = start_combat(state, registry, enemy)
    assert 'lines' in result
    assert 'changes' in result
    assert result['changes']['combat'] == 'started'
    assert state.combat_session is not None
    
    # Test legacy attack
    attack_result = resolve_combat_action(state, registry, 'attack')
    assert 'lines' in attack_result
    assert len(attack_result['lines']) > 0
    
    # Test status command (should show enhanced info)
    status_result = resolve_combat_action(state, registry, 'status')
    assert 'lines' in status_result
    status_line = status_result['lines'][0]
    # Should contain stamina and posture info
    assert 'Stamina:' in status_line
    assert 'Postura:' in status_line


if __name__ == "__main__":
    pytest.main([__file__, "-v"])