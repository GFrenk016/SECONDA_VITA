"""Hybrid turn-based/timed combat system (Phase 2).

Design goals:
- Hybrid turn-based with time pressure (QTE) elements
- Stamina and Posture (Poise) management for tactical depth
- Damage types with resistances/vulnerabilities
- Status effects with duration and tick mechanics
- Hit quality system (graze/normal/crit) based on multiple factors
- Weapon movesets with reach, windup, recovery, noise
- Tactical AI with states and stamina management
- Extensible event system for telemetry and plugins
- Maintain backward compatibility with existing API

Public API:
- resolve_attack(ctx, attacker, defender, move) -> CombatResult (new unified API)
- start_combat(state, registry, enemy_def) -> dict (legacy compatibility)
- resolve_combat_action(state, registry, command, arg) -> dict (legacy compatibility)

The system now uses internal modules for:
- CombatResolver: Core resolution logic
- StaminaSystem: Stamina costs and penalties
- PostureSystem: Poise/stagger mechanics
- StatusEffectSystem: DoT and debuff management
- TacticalAI: AI decision making

Legacy support maintains all existing behavior while adding new capabilities.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import random
import time
from .state import GameState
from .registry import ContentRegistry
from .combat_system.resolver import CombatResolver
from .combat_system.models import (
    CombatContext, CombatResult, MoveSpec, DamageType, StatusEffect, 
    HitQuality, AIState, StatusEffectInstance
)
from .combat_system.ai import TacticalAI

# Enhanced weapon definitions with new attributes
WEAPONS: Dict[str, Dict[str, Any]] = {
    'knife': {
        'id': 'knife', 
        'name': 'Coltello', 
        'damage': 3,
        'damage_type': 'slash',
        'reach': 1,
        'noise_level': 1,
        'movesets': {
            'light': {'stamina_cost': 10, 'windup': 1, 'recovery': 1, 'damage_multiplier': 0.8},
            'heavy': {'stamina_cost': 25, 'windup': 2, 'recovery': 2, 'damage_multiplier': 1.4},
            'thrust': {'stamina_cost': 15, 'windup': 1, 'recovery': 1, 'damage_multiplier': 1.1},
        }
    },
}

MOBS: Dict[str, Dict[str, Any]] = {}

# Global combat resolver instance
_combat_resolver: Optional[CombatResolver] = None
_tactical_ai: Optional[TacticalAI] = None

def _get_combat_resolver() -> CombatResolver:
    """Get or create global combat resolver."""
    global _combat_resolver, _tactical_ai
    if _combat_resolver is None:
        _combat_resolver = CombatResolver()
        _tactical_ai = TacticalAI(_combat_resolver.stamina, _combat_resolver.posture, _combat_resolver.effects)
    return _combat_resolver

def _get_tactical_ai() -> TacticalAI:
    """Get tactical AI instance."""
    global _tactical_ai
    if _tactical_ai is None:
        _get_combat_resolver()  # This will initialize both
    return _tactical_ai

def inject_content(weapons: Dict[str, Any], mobs: Dict[str, Any]):
    """Inject loaded JSON weapon/mob definitions with enhanced attributes."""
    if weapons:
        # Enhance weapon definitions with defaults for new attributes
        for weapon_id, weapon_data in weapons.items():
            enhanced_weapon = weapon_data.copy()
            
            # Add defaults for new attributes if not present
            if 'damage_type' not in enhanced_weapon:
                enhanced_weapon['damage_type'] = 'slash' if 'blade' in enhanced_weapon.get('tags', []) else 'blunt'
            if 'reach' not in enhanced_weapon:
                enhanced_weapon['reach'] = 1
            if 'noise_level' not in enhanced_weapon:
                enhanced_weapon['noise_level'] = 1
            if 'movesets' not in enhanced_weapon:
                # Generate basic movesets based on weapon type
                base_damage = enhanced_weapon.get('damage', 1)
                enhanced_weapon['movesets'] = {
                    'light': {'stamina_cost': 10, 'windup': 1, 'recovery': 1, 'damage_multiplier': 0.8},
                    'heavy': {'stamina_cost': 25, 'windup': 2, 'recovery': 2, 'damage_multiplier': 1.4},
                    'thrust': {'stamina_cost': 15, 'windup': 1, 'recovery': 1, 'damage_multiplier': 1.1},
                }
            
            WEAPONS[weapon_id] = enhanced_weapon
    
    if mobs:
        # Enhance mob definitions with defaults for new attributes
        for mob_id, mob_data in mobs.items():
            enhanced_mob = mob_data.copy()
            
            # Add defaults for new attributes if not present
            if 'max_stamina' not in enhanced_mob:
                enhanced_mob['max_stamina'] = 80
            if 'max_posture' not in enhanced_mob:
                enhanced_mob['max_posture'] = 60.0
            if 'stagger_threshold' not in enhanced_mob:
                enhanced_mob['stagger_threshold'] = 0.3
            if 'weapon_handling' not in enhanced_mob:
                enhanced_mob['weapon_handling'] = 0.5
            if 'resistances' not in enhanced_mob:
                enhanced_mob['resistances'] = {}
            if 'ai_state' not in enhanced_mob:
                enhanced_mob['ai_state'] = 'aggressive'
            if 'ai_traits' not in enhanced_mob:
                enhanced_mob['ai_traits'] = {}
            
            MOBS[mob_id] = enhanced_mob

def resolve_attack(ctx: CombatContext, attacker_data: Dict[str, Any], defender_data: Dict[str, Any]) -> CombatResult:
    """New unified combat resolution API.
    
    This is the main public API for the new hybrid combat system.
    
    Args:
        ctx: Combat context with attacker, defender, move, and situational modifiers
        attacker_data: Entity data for attacker (HP, stats, resistances, etc.)
        defender_data: Entity data for defender
        
    Returns:
        CombatResult with damage dealt, status effects, stamina consumed, etc.
    """
    resolver = _get_combat_resolver()
    
    # Initialize entities if not already done
    if ctx.attacker_id not in resolver._entity_data:
        resolver.initialize_entity(ctx.attacker_id, attacker_data)
    if ctx.defender_id not in resolver._entity_data:
        resolver.initialize_entity(ctx.defender_id, defender_data)
    
    # Resolve the attack
    return resolver.resolve_attack(ctx, attacker_data, defender_data)

class CombatError(Exception):
    pass

def _total_minutes(state: GameState) -> int:
    return state.day_count * 24 * 60 + state.time_minutes

def _create_move_from_weapon(weapon_data: Dict[str, Any], move_type: str = 'light') -> MoveSpec:
    """Create a MoveSpec from weapon data and move type."""
    movesets = weapon_data.get('movesets', {})
    moveset = movesets.get(move_type, {'stamina_cost': 10, 'damage_multiplier': 1.0})
    
    damage_type_str = weapon_data.get('damage_type', 'blunt')
    try:
        damage_type = DamageType(damage_type_str)
    except ValueError:
        damage_type = DamageType.BLUNT
    
    return MoveSpec(
        id=f"{weapon_data['id']}_{move_type}",
        name=f"{weapon_data['name']} ({move_type})",
        move_type=move_type,
        stamina_cost=moveset['stamina_cost'],
        reach=weapon_data.get('reach', 1),
        windup_time=moveset.get('windup', 1),
        recovery_time=moveset.get('recovery', 1),
        noise_level=weapon_data.get('noise_level', 1),
        damage_base=weapon_data.get('damage', 1) * moveset.get('damage_multiplier', 1.0),
        damage_type=damage_type
    )

def _get_player_data(state: GameState) -> Dict[str, Any]:
    """Get player data for new combat system."""
    return {
        'max_stamina': 100,
        'max_posture': 100.0,
        'stagger_threshold': 0.3,
        'weapon_handling': 0.6,  # Player has good weapon handling
        'resistances': {},  # No special resistances for player
        'ai_state': 'aggressive',  # Not used for player
        'ai_traits': {}
    }

def _get_enemy_data(enemy_def: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy enemy definition to new format."""
    enhanced = enemy_def.copy()
    
    # Add new system defaults if not present
    if 'max_stamina' not in enhanced:
        enhanced['max_stamina'] = 80
    if 'max_posture' not in enhanced:
        enhanced['max_posture'] = 60.0
    if 'stagger_threshold' not in enhanced:
        enhanced['stagger_threshold'] = 0.3
    if 'weapon_handling' not in enhanced:
        enhanced['weapon_handling'] = 0.4  # Enemies have lower weapon handling
    if 'resistances' not in enhanced:
        enhanced['resistances'] = {}
    if 'ai_state' not in enhanced:
        enhanced['ai_state'] = 'aggressive'
    if 'ai_traits' not in enhanced:
        enhanced['ai_traits'] = {}
    
    return enhanced

def _legacy_damage_to_hp(state: GameState, damage_instances: List, target_is_player: bool = True):
    """Apply damage instances to legacy HP system."""
    total_damage = sum(d.amount for d in damage_instances)
    if target_is_player:
        state.player_hp = max(0, state.player_hp - int(total_damage))
    else:
        if state.combat_session:
            state.combat_session['enemy_hp'] = max(0, state.combat_session['enemy_hp'] - int(total_damage))

def _emit_combat_event(event_type: str, payload: Dict[str, Any]):
    """Emit structured combat event for telemetry (placeholder for now)."""
    # In a full implementation, this would log to a structured logging system
    # For now, we'll just store it in a simple way that tests can verify
    pass

def start_combat(state: GameState, registry: ContentRegistry, enemy: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy combat start function - maintains compatibility while using new system."""
    if state.combat_session and state.combat_session.get('phase') != 'ended':
        raise CombatError('Sei già in combattimento.')
    
    # Initialize the new combat systems
    resolver = _get_combat_resolver()
    ai = _get_tactical_ai()
    
    # Initialize player and enemy in the new system
    player_data = _get_player_data(state)
    enemy_data = _get_enemy_data(enemy)
    
    player_id = 'player'
    enemy_id = enemy['id']
    
    resolver.initialize_entity(player_id, player_data)
    resolver.initialize_entity(enemy_id, enemy_data)
    
    # Initialize AI for enemy
    ai_state_str = enemy_data.get('ai_state', 'aggressive')
    try:
        ai_state = AIState(ai_state_str)
    except ValueError:
        ai_state = AIState.AGGRESSIVE
    
    ai.initialize_entity(enemy_id, ai_state, enemy_data.get('ai_traits', {}))
    
    # Legacy session structure for backward compatibility
    qte_pool: List[Dict[str, Any]] = enemy.get('qte_prompts', []) or []
    session = {
        'enemy_id': enemy['id'],
        'enemy_name': enemy.get('name', enemy['id']),
        'enemy_hp': enemy['hp'],
        'enemy_max_hp': enemy['hp'],
        'enemy_attack': enemy.get('attack', 1),
        'qte_chance': enemy.get('qte_chance', 0.0),
        'qte_prompt': enemy.get('qte_prompt', ''),
        'qte_expected': enemy.get('qte_expected', ''),
        'qte_window': enemy.get('qte_window_minutes', 2),
        'phase': 'player',
        'result': None,
        'qte': None,
        'qte_pool': qte_pool,
        'distance': 0,
        'push_decay': 0,
        # New system integration
        'player_id': player_id,
        'new_system_active': True,
    }
    state.combat_session = session
    lines = [
        f"Un {session['enemy_name']} ti si avvicina minaccioso.", 
        f"HP Nemico: {session['enemy_hp']}/{session['enemy_max_hp']} | I tuoi HP: {state.player_hp}/{state.player_max_hp}"
    ]
    
    # Emit combat started event
    _emit_combat_event('combat_started', {
        'player_id': player_id,
        'enemy_id': enemy_id,
        'enemy_name': enemy.get('name', enemy_id)
    })
    
    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'started'}}

def _weapon_damage(state: GameState) -> int:
    """Legacy weapon damage calculation - now integrated with new system."""
    if state.player_weapon_id and state.player_weapon_id in WEAPONS:
        weapon_data = WEAPONS[state.player_weapon_id]
        return int(weapon_data.get('damage', 1))  # Use base damage for legacy compatibility
    return 1

def _get_available_moves(state: GameState) -> List[MoveSpec]:
    """Get available moves for player based on equipped weapon."""
    if not state.player_weapon_id or state.player_weapon_id not in WEAPONS:
        # Default unarmed moves
        return [
            MoveSpec(
                id='unarmed_light',
                name='Pugno',
                move_type='light',
                stamina_cost=5,
                damage_base=1.0,
                damage_type=DamageType.BLUNT
            )
        ]
    
    weapon_data = WEAPONS[state.player_weapon_id]
    moves = []
    
    # Create moves for each moveset
    movesets = weapon_data.get('movesets', {'light': {}})
    for move_type in movesets.keys():
        moves.append(_create_move_from_weapon(weapon_data, move_type))
    
    return moves

def _choose_enemy_move(state: GameState, enemy_data: Dict[str, Any]) -> MoveSpec:
    """Choose move for enemy using AI system."""
    resolver = _get_combat_resolver()
    ai = _get_tactical_ai()
    
    enemy_id = state.combat_session['enemy_id']
    
    # Create basic enemy moves (simplified for legacy compatibility)
    enemy_moves = [
        MoveSpec(
            id='enemy_attack',
            name='Attacco',
            move_type='light',
            stamina_cost=15,
            damage_base=float(enemy_data.get('attack', 1)),
            damage_type=DamageType.BLUNT
        )
    ]
    
    # Let AI choose
    situation = {
        'enemy_count': 1,
        'allied_count': 1
    }
    
    chosen_move = ai.choose_move(enemy_id, enemy_moves, ['player'], situation)
    return chosen_move or enemy_moves[0]

def _check_end(state: GameState):
    """Check for combat end conditions."""
    s = state.combat_session
    if not s:
        return
    if s['enemy_hp'] <= 0:
        s['enemy_hp'] = 0
        s['phase'] = 'ended'
        s['result'] = 'victory'
        
        # Emit victory event
        _emit_combat_event('combat_ended', {
            'result': 'victory',
            'player_id': s.get('player_id', 'player'),
            'enemy_id': s['enemy_id']
        })
    elif state.player_hp <= 0:
        state.player_hp = 0
        s['phase'] = 'ended'
        s['result'] = 'defeat'
        
        # Emit defeat event
        _emit_combat_event('combat_ended', {
            'result': 'defeat',
            'player_id': s.get('player_id', 'player'),
            'enemy_id': s['enemy_id']
        })

def _maybe_trigger_qte(state: GameState):
    """Legacy QTE trigger - maintained for backward compatibility."""
    s = state.combat_session
    if not s or s['phase'] != 'enemy':
        return
    if s['qte_chance'] <= 0 or not s['qte_prompt']:
        pass
    
    # Use pool if available for variety
    chosen_prompt = None
    if s.get('qte_pool'):
        chosen_prompt = random.choice(s['qte_pool'])
    
    trigger = random.random() < s['qte_chance']
    if trigger and (chosen_prompt or s['qte_prompt']):
        deadline = _total_minutes(state) + s['qte_window']
        if chosen_prompt:
            prompt_text = chosen_prompt.get('prompt', s['qte_prompt'])
            expected = chosen_prompt.get('expected', s['qte_expected'])
            effect = chosen_prompt.get('effect')
        else:
            prompt_text = s['qte_prompt']
            expected = s['qte_expected']
            effect = None
        s['phase'] = 'qte'
        s['qte'] = {
            'prompt': prompt_text,
            'expected': expected,
            'deadline_total': deadline,
            'effect': effect,
        }

def _enemy_attack(state: GameState):
    """Legacy enemy attack using new combat system where possible."""
    s = state.combat_session
    if not s or s['phase'] not in ('enemy', 'qte'):
        return []
    
    # Try to use new system if available
    if s.get('new_system_active'):
        resolver = _get_combat_resolver()
        enemy_data = _get_enemy_data({'attack': s['enemy_attack']})
        enemy_move = _choose_enemy_move(state, enemy_data)
        
        # Create combat context
        ctx = CombatContext(
            attacker_id=s['enemy_id'],
            defender_id=s.get('player_id', 'player'),
            move=enemy_move
        )
        
        # Resolve attack
        result = resolver.resolve_attack(ctx, enemy_data, _get_player_data(state))
        
        # Apply damage to legacy HP system
        _legacy_damage_to_hp(state, result.damage_dealt, target_is_player=True)
        
        # Process system ticks
        tick_damage = resolver.tick_systems(s.get('player_id', 'player'))
        _legacy_damage_to_hp(state, tick_damage, target_is_player=True)
        
        lines = []
        if result.success and result.damage_dealt:
            dmg = sum(d.amount for d in result.damage_dealt)
            lines.append(f"Il {s['enemy_name']} ti colpisce infliggendo {dmg:.0f} danni. (HP: {state.player_hp}/{state.player_max_hp})")
        else:
            lines.append(f"Il {s['enemy_name']} manca l'attacco.")
        
        _check_end(state)
        if s['phase'] != 'ended':
            s['phase'] = 'player'
            s['qte'] = None
        
        return lines
    else:
        # Fallback to legacy system
        dmg = s['enemy_attack']
        state.player_hp -= dmg
        lines = [f"Il {s['enemy_name']} ti colpisce infliggendo {dmg} danni. (HP: {state.player_hp}/{state.player_max_hp})"]
        _check_end(state)
        if s['phase'] != 'ended':
            s['phase'] = 'player'
            s['qte'] = None
        return lines

def resolve_combat_action(state: GameState, registry: ContentRegistry, command: str, arg: str | None = None) -> Dict[str, Any]:
    """Legacy combat action resolution - enhanced with new combat system."""
    if not state.combat_session:
        raise CombatError('Non sei in combattimento.')
    s = state.combat_session
    lines: list[str] = []
    
    # Update potential QTE timeout before action
    if s['phase'] == 'qte' and s.get('qte'):
        if _total_minutes(state) >= s['qte']['deadline_total']:
            lines.append('Fallisci il tempo di reazione!')
            lines.extend(_enemy_attack(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
    
    if s['phase'] == 'ended':
        return {'lines': ['Il combattimento è già concluso.'], 'hints': [], 'events_triggered': [], 'changes': {}}

    command = command.lower().strip()
    
    # Status command with enhanced info
    if command == 'status':
        status_line = f"Nemico {s['enemy_name']} HP {s['enemy_hp']}/{s['enemy_max_hp']} | Tu {state.player_hp}/{state.player_max_hp} | Fase: {s['phase']}"
        
        # Add stamina/posture info if new system is active
        if s.get('new_system_active'):
            resolver = _get_combat_resolver()
            player_id = s.get('player_id', 'player')
            enemy_id = s['enemy_id']
            
            player_stamina = resolver.stamina.get_stamina(player_id)
            player_posture = resolver.posture.get_posture(player_id)
            enemy_stamina = resolver.stamina.get_stamina(enemy_id)
            enemy_posture = resolver.posture.get_posture(enemy_id)
            
            status_line += f" | Stamina: {player_stamina}/100 | Postura: {player_posture:.0f}/100"
            status_line += f" | Nemico Stamina: {enemy_stamina}/80 | Nemico Postura: {enemy_posture:.0f}/60"
        
        if s['phase'] == 'qte' and s['qte']:
            remaining = max(0, s['qte']['deadline_total'] - _total_minutes(state))
            status_line += f" | QTE: {s['qte']['prompt']} (restano {remaining} minuti)"
        
        return {'lines': [status_line], 'hints': [], 'events_triggered': [], 'changes': {}}

    # Attack command - enhanced with new system
    if command == 'attack':
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        
        # Use new system if available
        if s.get('new_system_active'):
            resolver = _get_combat_resolver()
            player_id = s.get('player_id', 'player')
            enemy_id = s['enemy_id']
            
            # Get available moves and choose default light attack
            available_moves = _get_available_moves(state)
            chosen_move = available_moves[0] if available_moves else None
            
            if not chosen_move:
                raise CombatError('Nessuna mossa disponibile.')
            
            # Create combat context
            ctx = CombatContext(
                attacker_id=player_id,
                defender_id=enemy_id,
                move=chosen_move
            )
            
            # Resolve attack
            player_data = _get_player_data(state)
            enemy_data = _get_enemy_data({'hp': s['enemy_hp'], 'attack': s['enemy_attack']})
            
            result = resolver.resolve_attack(ctx, player_data, enemy_data)
            
            if not result.success:
                lines.extend(result.description)
                # Still consume stamina and end turn
                s['phase'] = 'enemy'
                _maybe_trigger_qte(state)
                if s['phase'] == 'qte':
                    lines.append(s['qte']['prompt'])
                    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
                lines.extend(_enemy_attack(state))
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            
            # Apply damage to legacy HP system
            _legacy_damage_to_hp(state, result.damage_dealt, target_is_player=False)
            
            # Build description
            total_damage = sum(d.amount for d in result.damage_dealt)
            quality_text = {
                HitQuality.GRAZE: "di striscio",
                HitQuality.NORMAL: "",
                HitQuality.CRITICAL: "critico"
            }.get(result.hit_quality, "")
            
            damage_text = f"infliggendo {total_damage:.0f} danni" if total_damage > 0 else "senza danni"
            lines.append(f"Colpisci {quality_text} il {s['enemy_name']} {damage_text}. ({s['enemy_hp']}/{s['enemy_max_hp']})")
            
            # Apply status effects
            for effect in result.status_effects_applied:
                if effect.effect == StatusEffect.STAGGERED:
                    lines.append("Il nemico barcolla!")
            
            _check_end(state)
            if s['phase'] == 'ended':
                lines.append('Hai vinto.')
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
            
            # Process system ticks
            tick_damage = resolver.tick_systems(enemy_id)
            if tick_damage:
                tick_total = sum(d.amount for d in tick_damage)
                lines.append(f"Effetti stato causano {tick_total:.0f} danni aggiuntivi.")
                _legacy_damage_to_hp(state, tick_damage, target_is_player=False)
                _check_end(state)
                if s['phase'] == 'ended':
                    lines.append('Hai vinto.')
                    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
            
            # Enemy phase
            s['phase'] = 'enemy'
            _maybe_trigger_qte(state)
            if s['phase'] == 'qte':
                lines.append(s['qte']['prompt'])
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            
            lines.extend(_enemy_attack(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
        else:
            # Fallback to legacy system
            dmg = _weapon_damage(state)
            s['enemy_hp'] -= dmg
            lines.append(f"Colpisci il {s['enemy_name']} infliggendo {dmg} danni. ({s['enemy_hp']}/{s['enemy_max_hp']})")
            _check_end(state)
            if s['phase'] == 'ended':
                lines.append('Hai vinto.')
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
            
            s['phase'] = 'enemy'
            _maybe_trigger_qte(state)
            if s['phase'] == 'qte':
                lines.append(s['qte']['prompt'])
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            
            lines.extend(_enemy_attack(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    if command == 'push':
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        # Push increases distance; at distance>0 enemy must spend one enemy phase to close in (no attack)
        s['distance'] += 1
        s['push_decay'] = 1
        lines.append(f"Spingi il {s['enemy_name']} e guadagni spazio (distanza {s['distance']}).")
        s['phase'] = 'enemy'
        # Enemy tries to close distance instead of attack
        if s['distance'] > 0:
            s['distance'] -= 1
            lines.append(f"Il {s['enemy_name']} avanza per ridurre la distanza.")
            s['phase'] = 'player'
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
        # fallback if somehow distance 0 already
        _maybe_trigger_qte(state)
        if s['phase'] == 'qte':
            lines.append(s['qte']['prompt'])
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
        lines.extend(_enemy_attack(state))
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    if command == 'flee':
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        # Simple flee mechanic: higher chance if distance>0 or enemy low hp
        base = 0.3
        if s['distance'] > 0:
            base += 0.3
        if s['enemy_hp'] <= s['enemy_max_hp'] * 0.4:
            base += 0.2
        if random.random() < base:
            lines.append('Riesci a sganciarti e fuggire.')
            s['phase'] = 'ended'
            s['result'] = 'escaped'
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'escaped'}}
        else:
            lines.append('Tentativo di fuga fallito!')
            # Enemy immediate reaction (attack or qte)
            s['phase'] = 'enemy'
            _maybe_trigger_qte(state)
            if s['phase'] == 'qte':
                lines.append(s['qte']['prompt'])
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            lines.extend(_enemy_attack(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    if command == 'qte':
        if s['phase'] != 'qte' or not s.get('qte'):
            raise CombatError('Nessun QTE attivo.')
        if not arg:
            raise CombatError('Inserisci input QTE.')
        expected = s['qte']['expected']
        if arg.lower() == expected.lower():
            effect = s['qte'].get('effect')
            if effect == 'bonus_damage':
                bonus = max(1, _weapon_damage(state))
                s['enemy_hp'] -= bonus
                lines.append(f"Colpo mirato! Bonus {bonus} danni. ({s['enemy_hp']}/{s['enemy_max_hp']})")
                _check_end(state)
                if s['phase'] == 'ended':
                    lines.append('Hai vinto.')
                    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
            elif effect == 'reduce_next_damage':
                s['enemy_attack'] = max(0, s['enemy_attack'] - 1)
                lines.append('Blocchi le braccia: danni in arrivo ridotti.')
            elif effect == 'stagger':
                lines.append('Il nemico barcolla: salti direttamente al tuo turno.')
                s['phase'] = 'player'
                s['qte'] = None
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            elif effect == 'push':
                s['distance'] += 1
                lines.append('Spinta efficace: guadagni distanza.')
            else:
                lines.append('Reazione riuscita: eviti il colpo.')
            # Pass to player phase without damage
            s['phase'] = 'player'
            s['qte'] = None
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
        else:
            lines.append('Input errato!')
            lines.extend(_enemy_attack(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    raise CombatError(f'Azione sconosciuta in combattimento: {command}')

def spawn_enemy(enemy_id: str) -> Dict[str, Any]:
    if enemy_id not in MOBS:
        raise CombatError(f'Nemico inesistente: {enemy_id}')
    return MOBS[enemy_id]

__all__ = [
    'start_combat', 'resolve_combat_action', 'resolve_attack', 'CombatError', 
    'WEAPONS', 'MOBS', 'inject_content', 'spawn_enemy',
    # New system classes and models for direct use
    'CombatContext', 'CombatResult', 'MoveSpec', 'DamageType', 'StatusEffect', 'HitQuality'
]
