"""Realtime hybrid combat system (Phase 2.1).

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

Phases attuali (semplificate):
    - 'player' : il giocatore può inserire comandi (attack, push, flee, status)
    - 'qte'    : finestra rapida (offense o defense) con deadline simulato
    - 'ended'  : combattimento concluso (victory/defeat/escaped)

Rimosse le fasi legacy ('enemy'). Tutta la pressione temporale arriva da:
    - timer attacco nemico (next_enemy_attack_total)
    - finestra difensiva (defensive_qte_window)
    - scadenza QTE offensivo (qte.deadline_total)

Determinismo testabile: usare set_combat_seed(seed) prima di eseguire azioni.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import random
import time
import string
from .state import GameState
from config import (
    DEFAULT_COMPLEX_QTE_ENABLED,
    QTE_CODE_LENGTH_MIN, QTE_CODE_LENGTH_MAX, QTE_CODE_ALPHABET,
    DEFAULT_DEFENSIVE_QTE_WINDOW_MIN, DEFAULT_OFFENSIVE_QTE_WINDOW_MIN,
    INACTIVITY_ATTACK_SECONDS, MIN_ATTACK_ALL_COOLDOWN_MINUTES,
)
from .registry import ContentRegistry
from .combat_system.resolver import CombatResolver
from .combat_system.models import (
    CombatContext, CombatResult, MoveSpec, DamageType, StatusEffect, 
    HitQuality, AIState, StatusEffectInstance
)
from .combat_system.ai import TacticalAI

# Enhanced weapon definitions with new attributes
WEAPONS: Dict[str, Dict[str, Any]] = {
    # Default knife preserved for fallback; external assets may override/augment
    'knife': {
        'id': 'knife', 
        'name': 'Coltello', 
        'weapon_class': 'melee',
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
_RNG: Optional[random.Random] = None
_COMPLEX_QTE_ENABLED = DEFAULT_COMPLEX_QTE_ENABLED  # default can be overridden by env; tests can toggle

def set_complex_qte(enabled: bool):
    """Abilita o disabilita i QTE alfanumerici (3-5 char) per offense/defense."""
    global _COMPLEX_QTE_ENABLED
    _COMPLEX_QTE_ENABLED = bool(enabled)

def set_combat_seed(seed: int):
    """Imposta il seed per RNG deterministico nei test di combattimento."""
    global _RNG
    _RNG = random.Random(seed)
    # Propaga anche al resolver se già creato
    if _combat_resolver is not None:
        _combat_resolver.set_rng(_RNG)

def _get_combat_resolver() -> CombatResolver:
    """Get or create global combat resolver."""
    global _combat_resolver, _tactical_ai
    if _combat_resolver is None:
        _combat_resolver = CombatResolver()
        _tactical_ai = TacticalAI(_combat_resolver.stamina, _combat_resolver.posture, _combat_resolver.effects)
        if _RNG is not None:
            _combat_resolver.set_rng(_RNG)
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
            if 'weapon_class' not in enhanced_weapon:
                tags = set(enhanced_weapon.get('tags', []))
                if 'ranged' in tags:
                    enhanced_weapon['weapon_class'] = 'ranged'
                elif 'throwable' in tags:
                    enhanced_weapon['weapon_class'] = 'throwable'
                elif 'heavy' in tags:
                    enhanced_weapon['weapon_class'] = 'heavy'
                else:
                    enhanced_weapon['weapon_class'] = 'melee'
            if 'damage_type' not in enhanced_weapon:
                enhanced_weapon['damage_type'] = 'slash' if 'blade' in enhanced_weapon.get('tags', []) else 'blunt'
            if 'reach' not in enhanced_weapon:
                enhanced_weapon['reach'] = 1
            if 'noise_level' not in enhanced_weapon:
                enhanced_weapon['noise_level'] = 1
            if 'movesets' not in enhanced_weapon:
                # Generate basic movesets based on weapon class
                wclass = enhanced_weapon.get('weapon_class', 'melee')
                base_damage = enhanced_weapon.get('damage', 1)
                if wclass == 'ranged':
                    enhanced_weapon['movesets'] = {
                        'aimed': {'stamina_cost': 8, 'windup': 1, 'recovery': 1, 'damage_multiplier': 1.0},
                        'snap': {'stamina_cost': 6, 'windup': 0, 'recovery': 1, 'damage_multiplier': 0.8},
                    }
                    # Ranged defaults
                    enhanced_weapon.setdefault('damage_type', 'pierce')
                    enhanced_weapon.setdefault('reach', 5)
                    enhanced_weapon.setdefault('noise_level', 3)
                    # Ammo-related defaults
                    enhanced_weapon.setdefault('clip_size', 1)
                    enhanced_weapon.setdefault('ammo_in_clip', enhanced_weapon.get('clip_size', 1))
                    enhanced_weapon.setdefault('ammo_reserve', 0)
                    enhanced_weapon.setdefault('reload_time', 2)
                elif wclass == 'throwable':
                    enhanced_weapon['movesets'] = {
                        'throw': {'stamina_cost': 5, 'windup': 1, 'recovery': 0, 'damage_multiplier': 1.0},
                    }
                    enhanced_weapon.setdefault('aoe_factor', 0.6)  # portion of base damage applied to others
                    enhanced_weapon.setdefault('reach', 3)
                    enhanced_weapon.setdefault('noise_level', 2)
                    enhanced_weapon.setdefault('uses', 1)
                else:
                    # melee / heavy fall back to melee defaults
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

def _sync_primary_alias(state: GameState):
    s = state.combat_session
    if not s:
        return
    enemies = s.get('enemies', [])
    primary = None
    for e in enemies:
        if e['hp'] > 0:
            primary = e
            break
    if primary is None and enemies:
        primary = enemies[0]
    if not primary:
        return
    s['enemy_id'] = primary['id']
    s['enemy_name'] = primary['name']
    s['enemy_hp'] = primary['hp']
    s['enemy_max_hp'] = primary['max_hp']
    s['enemy_attack'] = primary['attack']
    # Legacy compatibility for incoming attack fields if derived from this primary
    if primary.get('incoming_attack'):
        s['incoming_attack'] = True
        s['incoming_attack_damage'] = primary.get('incoming_attack_damage', primary['attack'])
        s['incoming_attack_deadline'] = primary.get('incoming_attack_deadline')
        s['next_enemy_attack_total'] = primary.get('next_attack_total', s.get('next_enemy_attack_total'))
    else:
        s['incoming_attack'] = False
        s.pop('incoming_attack_deadline', None)

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

    # Parse optional status effects defined at moveset level (e.g., [["bleed", 3, 1.0]])
    move_status_effects = []
    for eff in moveset.get('status_effects', []) or []:
        # Expected shape: [effect_str, duration:int, intensity:float]
        try:
            eff_str, dur, inten = eff[0], int(eff[1]), float(eff[2])
            key = str(eff_str).lower()
            eff_enum = {
                'bleed': StatusEffect.BLEED,
                'bleeding': StatusEffect.BLEED,
                'burn': StatusEffect.BURN,
                'fire': StatusEffect.BURN,
                'concussed': StatusEffect.CONCUSSED,
                'stun': StatusEffect.CONCUSSED,
                'staggered': StatusEffect.STAGGERED,
                'stagger': StatusEffect.STAGGERED,
                'crippled': StatusEffect.CRIPPLED,
                'cripple': StatusEffect.CRIPPLED,
            }.get(key, None)
            if eff_enum is not None:
                move_status_effects.append((eff_enum, dur, inten))
        except Exception:
            # Ignore malformed entries
            continue
    # Also allow weapon-level status_effects (applies to all moves)
    for eff in weapon_data.get('status_effects', []) or []:
        try:
            eff_str, dur, inten = eff[0], int(eff[1]), float(eff[2])
            key = str(eff_str).lower()
            eff_enum = {
                'bleed': StatusEffect.BLEED,
                'bleeding': StatusEffect.BLEED,
                'burn': StatusEffect.BURN,
                'fire': StatusEffect.BURN,
                'concussed': StatusEffect.CONCUSSED,
                'stun': StatusEffect.CONCUSSED,
                'staggered': StatusEffect.STAGGERED,
                'stagger': StatusEffect.STAGGERED,
                'crippled': StatusEffect.CRIPPLED,
                'cripple': StatusEffect.CRIPPLED,
            }.get(key, None)
            if eff_enum is not None:
                move_status_effects.append((eff_enum, dur, inten))
        except Exception:
            continue
    
    return MoveSpec(
        id=f"{weapon_data['id']}_{move_type}",
        name=f"{weapon_data['name']} ({move_type})",
        move_type=move_type,
        stamina_cost=moveset.get('stamina_cost', 10),
        reach=weapon_data.get('reach', 1),
        windup_time=moveset.get('windup', 1),
        recovery_time=moveset.get('recovery', 1),
        noise_level=weapon_data.get('noise_level', 1),
        damage_base=weapon_data.get('damage', 1) * moveset.get('damage_multiplier', 1.0),
        damage_type=damage_type,
        status_effects=move_status_effects
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

# ---- Ranged helpers ----
def _is_ranged_weapon(weapon_data: Dict[str, Any] | None) -> bool:
    return bool(weapon_data) and weapon_data.get('weapon_class') == 'ranged'

def _consume_ammo_if_needed(weapon_data: Dict[str, Any]) -> tuple[bool, str]:
    """For ranged weapons, consume 1 ammo from clip; if empty, block and return message."""
    if not _is_ranged_weapon(weapon_data):
        return True, ''
    clip = int(weapon_data.get('ammo_in_clip', 0))
    if clip <= 0:
        return False, "Nessun colpo nel caricatore. Usa 'reload'."
    weapon_data['ammo_in_clip'] = clip - 1
    return True, ''

def _reload_weapon(weapon_data: Dict[str, Any]) -> tuple[str, bool]:
    """Perform reload on a ranged weapon using its ammo fields. Returns (message, changed)."""
    if not _is_ranged_weapon(weapon_data):
        return ("Non stai impugnando un'arma da fuoco.", False)
    clip_size = int(weapon_data.get('clip_size', 0))
    in_clip = int(weapon_data.get('ammo_in_clip', 0))
    reserve = int(weapon_data.get('ammo_reserve', 0))
    if clip_size <= 0:
        return ("Questa arma non supporta ricarica.", False)
    if in_clip >= clip_size:
        return ("Il caricatore è già pieno.", False)
    if reserve <= 0:
        return ("Nessuna munizione di riserva.", False)
    needed = clip_size - in_clip
    to_load = min(needed, reserve)
    weapon_data['ammo_in_clip'] = in_clip + to_load
    weapon_data['ammo_reserve'] = reserve - to_load
    return (f"Ricarichi {to_load} colpi ({weapon_data['ammo_in_clip']}/{clip_size} | riserva {weapon_data['ammo_reserve']}).", True)

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
    """Emit structured combat event into state.timeline.

    Ogni evento è un dict:
      { 'type': 'combat', 'event': event_type, 'time': epoch_sec,
        'total_minutes': simulated_minutes, **payload }
    """
    # Recupera stato da payload se presente
    state: GameState | None = payload.pop('_state', None)
    if state is None:
        return
    if not hasattr(state, 'timeline') or state.timeline is None:
        # Inizializza timeline se assente
        state.timeline = []
    try:
        now_sim = _total_minutes(state)
        evt = {
            'type': 'combat',
            'event': event_type,
            'time': time.time(),
            'total_minutes': now_sim,
        }
        evt.update(payload)
        state.timeline.append(evt)
    except Exception:
        # Non deve rompere il flusso di gioco
        return

def _auto_switch_focus_if_needed(state: GameState):
    s = state.combat_session
    if not s:
        return
    focus_id = s.get('focus_enemy_id')
    if not focus_id:
        return
    enemies = s.get('enemies', [])
    for idx, e in enumerate(enemies):
        if e['id'] == focus_id:
            if e['hp'] <= 0:
                # trova prossimo vivo
                for j, other in enumerate(enemies):
                    if other['hp'] > 0:
                        s['focus_enemy_id'] = other['id']
                        _emit_combat_event('focus_auto_switch', {'_state': state, 'enemy_id': other['id'], 'enemy_index': j})
                        return
                # Nessun vivo, rimuovi focus
                s.pop('focus_enemy_id', None)
            return

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

    # Assicura che la definizione base sia registrata per spawn successivi (test multi-spawn)
    if enemy_id not in MOBS:
        # Copia shallow: sufficiente per hp/attack e parametri spawn
        MOBS[enemy_id] = enemy.copy()
    
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
    # Realtime combat extension fields:
    # - next_enemy_attack_total: minuto simulato in cui, se non interrotto, il nemico effettua un attacco
    # - enemy_attack_interval: intervallo base (minuti simulati) tra due attacchi automatici
    # - defensive_qte_window: durata finestra QTE difensivo prima che il colpo vada a segno
    # - incoming_attack: True se un attacco è caricato ed in attesa di risoluzione (difesa o impatto)
    # Parametri difficoltà opzionali
    dmg_mult = float(enemy.get('attack_damage_multiplier', 1.0))
    interval_mult = float(enemy.get('attack_interval_multiplier', 1.0))
    base_interval_raw = max(1, int(enemy.get('attack_interval_minutes', 3)))
    base_interval = max(1, int(base_interval_raw * interval_mult))  # scala intervallo attacchi
    defensive_window = enemy.get('defensive_qte_window', DEFAULT_DEFENSIVE_QTE_WINDOW_MIN)
    now_total = _total_minutes(state)
    enemy_entry = {
        'id': enemy['id'],
        'name': enemy.get('name', enemy['id']),
        'hp': enemy['hp'],
        'max_hp': enemy['hp'],
        'attack': int(enemy.get('attack', 1) * dmg_mult),
        'attack_interval': base_interval,
        'next_attack_total': now_total + base_interval,
        'incoming_attack': False,
        'incoming_attack_damage': 0,
        'incoming_attack_deadline': None,
    }
    session = {
        # Legacy alias (manteniamo per retro compatibilità test esistenti)
        'enemy_id': enemy_entry['id'],
        'enemy_name': enemy_entry['name'],
        'enemy_hp': enemy_entry['hp'],
        'enemy_max_hp': enemy_entry['max_hp'],
        'enemy_attack': enemy_entry['attack'],
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
        # Realtime legacy (riferito al nemico primario) - mantenuto per compatibilità
        'next_enemy_attack_total': enemy_entry['next_attack_total'],
        'enemy_attack_interval': base_interval,
        'defensive_qte_window': defensive_window,
        'incoming_attack': False,
        'incoming_attack_damage': 0,
        # Tracciamento realtime azioni player (per inattività)
        'last_player_action_real': time.time(),  # timestamp reale dell'ultima azione valida del giocatore
    'inactivity_attack_seconds': INACTIVITY_ATTACK_SECONDS,
        # Multi-enemy
        'enemies': [enemy_entry],
    }
    state.combat_session = session
    lines = [
        f"Un {session['enemy_name']} ti si avvicina minaccioso.", 
        f"HP Nemico: {session['enemy_hp']}/{session['enemy_max_hp']} | I tuoi HP: {state.player_hp}/{state.player_max_hp}"
    ]
    
    # Emit combat started event
    _emit_combat_event('combat_started', {
        '_state': state,
        'player_id': player_id,     'enemy_id': enemy_id,
        'enemy_name': enemy.get('name', enemy_id)
    })
    
    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'started'}}

# Helper per creare un enemy_entry riutilizzabile anche da spawn
def _create_enemy_entry(state: GameState, base_def: Dict[str, Any]) -> Dict[str, Any]:
    dmg_mult = float(base_def.get('attack_damage_multiplier', 1.0))
    interval_mult = float(base_def.get('attack_interval_multiplier', 1.0))
    base_interval_raw = max(1, int(base_def.get('attack_interval_minutes', 3)))
    base_interval = max(1, int(base_interval_raw * interval_mult))
    now_total = _total_minutes(state)
    # Offset casuale iniziale per desincronizzare attacchi (0..base_interval-1)
    global _RNG
    rng = _RNG or random
    jitter = 0
    if base_interval > 1:
        jitter = rng.randrange(0, base_interval)
    entry = {
        'id': base_def['id'],
        'name': base_def.get('name', base_def['id']),
        'hp': base_def['hp'],
        'max_hp': base_def['hp'],
        'attack': int(base_def.get('attack', 1) * dmg_mult),
        'attack_interval': base_interval,
        'next_attack_total': now_total + base_interval + jitter,
        'incoming_attack': False,
        'incoming_attack_damage': 0,
        'incoming_attack_deadline': None,
    }
    return entry

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
    """Check for combat end conditions and handle loot drops."""
    s = state.combat_session
    if not s:
        return
    
    # Check for newly defeated enemies and handle loot drops
    _handle_defeated_enemy_loot(state)
    
    # Multi enemy: vittoria se tutti <=0
    all_dead = True
    for e in s.get('enemies', []):
        if e['hp'] > 0:
            all_dead = False
            break
    if all_dead:
        s['phase'] = 'ended'
        s['result'] = 'victory'
        _emit_combat_event('combat_ended', {
            'result': 'victory',
            'player_id': s.get('player_id', 'player'),
            'enemy_id': 'all'
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

def _handle_defeated_enemy_loot(state: GameState):
    """Handle loot drops for recently defeated enemies."""
    s = state.combat_session
    if not s:
        return
    
    # Track which enemies were already processed for loot
    if not hasattr(s, 'loot_processed_enemies'):
        s['loot_processed_enemies'] = set()
    
    enemies = s.get('enemies', [])
    for enemy in enemies:
        enemy_id = enemy['id']
        
        # Skip if already processed or still alive
        if enemy_id in s['loot_processed_enemies'] or enemy['hp'] > 0:
            continue
            
        # Mark as processed
        s['loot_processed_enemies'].add(enemy_id)
        
        # Get enemy definition for loot table
        enemy_base_id = enemy_id.split('_')[0] if '_' in enemy_id else enemy_id
        enemy_def = MOBS.get(enemy_base_id)
        
        if not enemy_def or 'loot' not in enemy_def:
            continue
            
        # Roll for loot drops
        dropped_items = _roll_enemy_loot(enemy_def['loot'])
        
        if dropped_items:
            # Add items to player inventory
            _add_loot_to_inventory(state, dropped_items, enemy['name'])

def _roll_enemy_loot(loot_table: list) -> list:
    """Roll for loot drops based on enemy loot table."""
    dropped_items = []
    rng = _RNG or random
    
    for loot_entry in loot_table:
        item_id = loot_entry.get('item')
        chance = loot_entry.get('chance', 0.0)
        quantity = loot_entry.get('quantity', 1)
        
        if not item_id:
            continue
            
        # Roll for drop
        if rng.random() <= chance:
            dropped_items.append({
                'id': item_id,
                'quantity': quantity
            })
    
    return dropped_items

def _add_item_to_inventory(state: GameState, item_id: str, quantity: int = 1):
    """Helper function to add items to player inventory."""
    try:
        from engine.core.actions import _get_player_inventory, _save_player_inventory
        
        player_inventory = _get_player_inventory(state)
        success = player_inventory.add(item_id, quantity)
        
        if success:
            _save_player_inventory(state, player_inventory)
        
        return success
    except Exception as e:
        print(f"Warning: Failed to add {item_id} to inventory: {e}")
        return False

def _add_loot_to_inventory(state: GameState, dropped_items: list, enemy_name: str):
    """Add dropped loot to player inventory."""
    try:
        from engine.items import get_item_registry
        
        item_registry = get_item_registry()
        loot_messages = []
        
        for item_drop in dropped_items:
            item_id = item_drop['id']
            quantity = item_drop.get('quantity', 1)
            
            # Check if item exists in registry
            item_data = item_registry.get(item_id)
            if not item_data:
                continue
                
            item_name = item_data.get('name', item_id)
            
            # Add to inventory
            success = _add_item_to_inventory(state, item_id, quantity)
            
            if success:
                if quantity > 1:
                    loot_messages.append(f"{item_name} x{quantity}")
                else:
                    loot_messages.append(item_name)
        
        if loot_messages:
            # Store loot message for display
            if not hasattr(state, 'pending_loot_messages'):
                state.pending_loot_messages = []
            
            loot_text = f"Raccogli da {enemy_name}: {', '.join(loot_messages)}"
            state.pending_loot_messages.append(loot_text)
            
    except Exception as e:
        # Don't break combat flow if loot system fails
        print(f"Warning: Loot system error: {e}")
        pass

# Nuovo: trigger QTE offensivo direttamente dopo un attacco player (realtime, niente fase enemy)
def _maybe_trigger_offense_qte(state: GameState):
    s = state.combat_session
    if not s or s['phase'] != 'player':
        return
    if s['qte_chance'] <= 0:
        return
    # Scegli prompt da pool se presente
    chosen_prompt = None
    global _RNG
    rng = _RNG or random
    if s.get('qte_pool'):
        chosen_prompt = rng.choice(s['qte_pool'])
    trigger = rng.random() < s['qte_chance']
    if not trigger:
        return
    deadline = _total_minutes(state) + s.get('qte_window', DEFAULT_OFFENSIVE_QTE_WINDOW_MIN)
    if _COMPLEX_QTE_ENABLED:
        # Genera codice alfanumerico 3-5 per QTE Offensivo
        length = rng.randint(QTE_CODE_LENGTH_MIN, QTE_CODE_LENGTH_MAX)
        alphabet = QTE_CODE_ALPHABET
        code = ''.join(rng.choice(alphabet) for _ in range(length))
        prompt_text = f"QTE Offensivo! Digita: {code}"
        expected = code
        effect = chosen_prompt.get('effect') if chosen_prompt else None
    else:
        if not (chosen_prompt or s.get('qte_prompt')):
            return
        if chosen_prompt:
            prompt_text = chosen_prompt.get('prompt', s.get('qte_prompt',''))
            expected = chosen_prompt.get('expected', s.get('qte_expected',''))
            effect = chosen_prompt.get('effect')
        else:
            prompt_text = s.get('qte_prompt','')
            expected = s.get('qte_expected','')
            effect = None
    s['phase'] = 'qte'
    s['qte'] = {
        'prompt': prompt_text,
        'expected': expected,
        'deadline_total': deadline,
        'effect': effect,
        'type': 'offense'
    }

def resolve_combat_action(state: GameState, registry: ContentRegistry, command: str, arg: str | None = None) -> Dict[str, Any]:
    """Legacy combat action resolution - enhanced con realtime e QTE difensivi/offensivi."""
    if not state.combat_session:
        raise CombatError('Non sei in combattimento.')
    s = state.combat_session
    lines: list[str] = []

    # Non processiamo immediatamente eventi realtime per preservare turn feeling legacy

    # Timeout QTE offensivo (non difensivo: difensivo gestito da realtime landing)
    if s['phase'] == 'qte' and s.get('qte') and s['qte'].get('type','offense'):
        if _total_minutes(state) >= s['qte']['deadline_total']:
            lines.append('Fallisci il tempo di reazione!')
            # In modello realtime non forziamo enemy attack immediato, semplicemente chiudiamo QTE
            s['qte'] = None
            s['phase'] = 'player'
            # Dopo timeout, processa eventuali nuovi eventi
            lines.extend(_process_realtime_events(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
    
    if s['phase'] == 'ended':
        return {'lines': ['Il combattimento è già concluso.'], 'hints': [], 'events_triggered': [], 'changes': {}}

    command = command.lower().strip()

    # Reload for ranged weapons
    if command == 'reload':
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        s['last_player_action_real'] = time.time()
        if not state.player_weapon_id or state.player_weapon_id not in WEAPONS:
            return {'lines': ['Nessuna arma equipaggiata.'], 'hints': [], 'events_triggered': [], 'changes': {}}
        w = WEAPONS[state.player_weapon_id]
        msg, changed = _reload_weapon(w)
        lines.append(msg)
        if changed:
            # Simula costo tempo ricarica: ritarda prossimo attacco nemico principale di reload_time minuti
            rt = int(max(1, round(float(w.get('reload_time', 2)))))
            s['next_enemy_attack_total'] = max(s.get('next_enemy_attack_total', _total_minutes(state)), _total_minutes(state)) + rt
        lines.extend(_process_realtime_events(state))
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
    
    # Status command with enhanced info (multi nemico)
    if command == 'status':
        lines.extend(_process_realtime_events(state))
        _sync_primary_alias(state)
        enemies = s.get('enemies', [])
        status_line = f"Tu {state.player_hp}/{state.player_max_hp} | Fase: {s['phase']}"
        if s.get('incoming_attack') and 'incoming_attack_deadline' in s:
            remaining = s['incoming_attack_deadline'] - _total_minutes(state)
            if remaining < 0:
                remaining = 0
            status_line += f" | ATTACCO IN ARRIVO ({remaining}m)"
        if s.get('new_system_active'):
            resolver = _get_combat_resolver()
            player_id = s.get('player_id', 'player')
            enemy_id = s.get('enemy_id')
            if enemy_id:
                player_stamina = resolver.stamina.get_stamina(player_id)
                player_posture = resolver.posture.get_posture(player_id)
                enemy_stamina = resolver.stamina.get_stamina(enemy_id)
                enemy_posture = resolver.posture.get_posture(enemy_id)
                status_line += f" | Stamina: {player_stamina}/100 | Postura: {player_posture:.0f}/100"
                status_line += f" | Nemico Stamina: {enemy_stamina}/80 | Nemico Postura: {enemy_posture:.0f}/60"
        if s['phase'] == 'qte' and s.get('qte'):
            remaining = max(0, s['qte']['deadline_total'] - _total_minutes(state))
            status_line += f" | QTE: {s['qte']['prompt']} (restano {remaining} minuti)"
        # Show ammo if ranged weapon equipped
        if state.player_weapon_id and state.player_weapon_id in WEAPONS:
            w = WEAPONS[state.player_weapon_id]
            if _is_ranged_weapon(w):
                status_line += f" | Munizioni: {int(w.get('ammo_in_clip',0))}/{int(w.get('clip_size',0))} (riserva {int(w.get('ammo_reserve',0))})"
            elif w.get('weapon_class') == 'throwable':
                status_line += f" | Usi: {int(w.get('uses',1))}"
        lines.append(status_line)
        # Elenco nemici multilinea
        if enemies:
            focus_id = s.get('focus_enemy_id')
            for idx, e in enumerate(enemies):
                flags = []
                if e['hp'] <= 0:
                    flags.append('X')
                if focus_id == e['id'] and e['hp'] > 0:
                    flags.append('F')
                if e.get('incoming_attack'):
                    # calcola minuti rimanenti
                    dl = e.get('incoming_attack_deadline')
                    if dl is not None:
                        rem = max(0, dl - _total_minutes(state))
                        flags.append(f"I:{rem}m")
                    else:
                        flags.append('I')
                flag_str = (' [' + ','.join(flags) + ']') if flags else ''
                lines.append(f"  {idx+1}. {e['name']} {e['hp']}/{e['max_hp']}{flag_str}")
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    # Comando focus: focus <index>
    if command.startswith('focus'):
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        parts = command.split()
        enemies = s.get('enemies', [])
        if len(enemies) == 0:
            raise CombatError('Nessun nemico da focalizzare.')
        target_enemy = None
        idx_used = None
        if len(parts) >= 2 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            if 0 <= idx < len(enemies):
                if enemies[idx]['hp'] > 0:
                    target_enemy = enemies[idx]
                    idx_used = idx
        if target_enemy is None:
            # default: primo vivo
            for i,e in enumerate(enemies):
                if e['hp'] > 0:
                    target_enemy = e
                    idx_used = i
                    break
        if target_enemy is None:
            raise CombatError('Nessun bersaglio valido da focalizzare.')
        s['focus_enemy_id'] = target_enemy['id']
        lines.append(f"Ti concentri su {target_enemy['name']}.")
        _emit_combat_event('focus_set', {'_state': state, 'enemy_id': target_enemy['id'], 'enemy_index': idx_used})
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    # Throw (consume uses, AoE apply)
    if command.startswith('throw'):
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        s['last_player_action_real'] = time.time()
        if not state.player_weapon_id or state.player_weapon_id not in WEAPONS:
            return {'lines': ['Nessuna arma equipaggiata.'], 'hints': [], 'events_triggered': [], 'changes': {}}
        w = WEAPONS[state.player_weapon_id]
        if w.get('weapon_class') != 'throwable':
            return {'lines': ["Questa non è un'arma da lancio."], 'hints': [], 'events_triggered': [], 'changes': {}}
        uses = int(w.get('uses', 0))
        if uses <= 0:
            return {'lines': ["Non ti rimangono usi."], 'hints': [], 'events_triggered': [], 'changes': {}}
        # Identify target index if provided
        enemies = s.get('enemies', [])
        target_enemy = None
        if ' ' in command:
            parts = command.split()
            if len(parts) >= 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                if 0 <= idx < len(enemies):
                    target_enemy = enemies[idx]
        if target_enemy is None:
            # default to first alive
            for e in enemies:
                if e['hp'] > 0:
                    target_enemy = e
                    break
        if target_enemy is None and enemies:
            target_enemy = enemies[0]
        if not target_enemy:
            raise CombatError('Nessun bersaglio disponibile.')
        # Build move from weapon (throw)
        available_moves = _get_available_moves(state)
        chosen_move = None
        for mv in available_moves:
            if mv.move_type == 'throw':
                chosen_move = mv
                break
        if not chosen_move and available_moves:
            chosen_move = available_moves[0]
        if not chosen_move:
            raise CombatError('Nessuna mossa disponibile.')
        # Resolve primary hit
        resolver = _get_combat_resolver()
        player_id = s.get('player_id', 'player')
        ctx = CombatContext(attacker_id=player_id, defender_id=target_enemy['id'], move=chosen_move)
        player_data = _get_player_data(state)
        enemy_data = _get_enemy_data({'hp': target_enemy['hp'], 'attack': target_enemy['attack']})
        result = resolver.resolve_attack(ctx, player_data, enemy_data)
        # Consume one use regardless of hit success
        w['uses'] = max(0, uses - 1)
        if not result.success:
            lines.extend(['Lancio mancato.'])
            lines.extend(_process_realtime_events(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
        total_damage = sum(d.amount for d in result.damage_dealt)
        dmg_int = max(0, int(round(total_damage)))
        target_enemy['hp'] = max(0, target_enemy['hp'] - dmg_int)
        s['enemy_id'] = target_enemy['id']
        s['enemy_name'] = target_enemy['name']
        s['enemy_hp'] = target_enemy['hp']
        s['enemy_max_hp'] = target_enemy['max_hp']
        primary_report = f"Colpisci {target_enemy['name']} per {dmg_int} danni ({target_enemy['hp']}/{target_enemy['max_hp']})."
        # AoE to others
        aoe_factor = float(w.get('aoe_factor', 0.0))
        splash_reports = []
        if aoe_factor > 0:
            others = [e for e in enemies if e is not target_enemy and e['hp'] > 0]
            for other in others:
                ctx2 = CombatContext(attacker_id=player_id, defender_id=other['id'], move=chosen_move)
                enemy2 = _get_enemy_data({'hp': other['hp'], 'attack': other['attack']})
                r2 = resolver.resolve_attack(ctx2, player_data, enemy2)
                if not r2.success:
                    continue
                base2 = sum(d.amount for d in r2.damage_dealt)
                splash = max(0, int(round(base2 * aoe_factor)))
                if splash <= 0:
                    continue
                other['hp'] = max(0, other['hp'] - splash)
                splash_reports.append(f"{other['name']} -{splash} ({other['hp']}/{other['max_hp']})")
        line = primary_report
        if splash_reports:
            line += " Spruzzi colpiscono: " + "; ".join(splash_reports)
            _emit_combat_event('throw_splash', {
                '_state': state,
                'targets': [
                    {
                        'enemy_id': e['id'],
                        'enemy_index': enemies.index(e),
                        'enemy_hp': e['hp']
                    } for e in enemies if e is not target_enemy and e['hp']>0
                ]
            })
        # Show remaining uses
        line += f" | Usi rimasti: {int(w.get('uses',0))}"
        if splash_reports:
            _emit_combat_event('throw_splash', {
                '_state': state,
                'targets': [
                    {
                        'enemy_id': e['id'],
                        'enemy_index': enemies.index(e),
                        'enemy_hp': e['hp']
                    } for e in enemies if e is not target_enemy and e['hp']>0
                ]
            })
        lines.append(line)
        _emit_combat_event('throw', {'_state': state, 'primary': target_enemy['id'], 'uses_left': int(w.get('uses',0))})
        _check_end(state)
        _auto_switch_focus_if_needed(state)
        _sync_primary_alias(state)
        if s['phase'] == 'ended':
            lines.append('Hai vinto.')
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
        # Process tick systems on primary only for simplicity
        tick_damage = resolver.tick_systems(target_enemy['id'])
        if tick_damage:
            tick_total = sum(d.amount for d in tick_damage)
            tick_int = max(0, int(round(tick_total)))
            if tick_int > 0:
                lines.append(f"Effetti stato causano {tick_int} danni aggiuntivi.")
            target_enemy['hp'] = max(0, target_enemy['hp'] - tick_int)
            s['enemy_hp'] = target_enemy['hp']
        _check_end(state)
        _auto_switch_focus_if_needed(state)
        _sync_primary_alias(state)
        if s['phase'] == 'ended':
            lines.append('Hai vinto.')
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
        lines.extend(_process_realtime_events(state))
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    # Special commands for passive mobs
    if command.startswith('hunt') or command.startswith('capture') or command.startswith('negotiate'):
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        
        # Get target enemy
        enemies = s.get('enemies', [])
        target_enemy = None
        if ' ' in command:
            parts = command.split()
            if len(parts) >= 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                if 0 <= idx < len(enemies) and enemies[idx]['hp'] > 0:
                    target_enemy = enemies[idx]
        
        if target_enemy is None:
            # Default to focused enemy or first alive
            focus_id = s.get('focus_enemy_id')
            if focus_id:
                for e in enemies:
                    if e['id'] == focus_id and e['hp'] > 0:
                        target_enemy = e
                        break
            if target_enemy is None:
                for e in enemies:
                    if e['hp'] > 0:
                        target_enemy = e
                        break
        
        if target_enemy is None:
            raise CombatError('Nessun bersaglio valido.')
    
    # Passive mob interactions - hunt, capture, negotiate
    if command.startswith(('hunt', 'capture', 'negotiate')):
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        s['last_player_action_real'] = time.time()
        
        # Get target enemy
        enemies = s.get('enemies', [])
        target_enemy = None
        if ' ' in command:
            parts = command.split()
            if len(parts) >= 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                if 0 <= idx < len(enemies) and enemies[idx]['hp'] > 0:
                    target_enemy = enemies[idx]
        if target_enemy is None:
            # Default to focused or first alive
            if s.get('focus_enemy_id'):
                for e in enemies:
                    if e['id'] == s['focus_enemy_id'] and e['hp'] > 0:
                        target_enemy = e
                        break
            if not target_enemy:
                for e in enemies:
                    if e['hp'] > 0:
                        target_enemy = e
                        break
        if not target_enemy:
            raise CombatError('Nessun bersaglio disponibile.')
        
        # Load mob definition to check AI state
        mob_def = MOBS.get(target_enemy['id'], {})
        ai_state = mob_def.get('ai_state', 'aggressive')
        behavioral_traits = mob_def.get('behavioral_traits', {})
        
        return _handle_passive_interaction(state, registry, command.split()[0], target_enemy, mob_def, behavioral_traits, lines)
    
    # Attack (supporta target: attack 2)
    if command.startswith('attack'):
        # Attacco ad area: "attack all"
        if command.strip() == 'attack all':
            if s['phase'] != 'player':
                # Replica logica penalità usata nell'attacco singolo
                if s['phase'] == 'qte' and s.get('qte') and s['qte'].get('type') == 'defense' and s.get('incoming_attack'):
                    dmg = s.get('incoming_attack_damage') or s.get('enemy_attack',1)
                    state.player_hp -= dmg
                    lines.append(f"Ignori la difesa e vieni colpito per {dmg} danni! (HP: {state.player_hp}/{state.player_max_hp})")
                    attacker_idx = s.get('qte', {}).get('enemy_index')
                    if attacker_idx is not None and attacker_idx < len(s.get('enemies', [])):
                        s['enemies'][attacker_idx]['incoming_attack'] = False
                        s['enemies'][attacker_idx]['incoming_attack_deadline'] = None
                    s['incoming_attack'] = False
                    s['qte'] = None
                    _check_end(state)
                    if s['phase'] != 'ended':
                        s['phase'] = 'player'
                if s['phase'] != 'player':
                    raise CombatError('Non è il tuo turno.')
            # Cooldown check
            cd_total = s.get('attack_all_cooldown_total')
            if cd_total is not None and _total_minutes(state) < cd_total:
                remaining = cd_total - _total_minutes(state)
                lines.append(f"L'attacco ad area non è pronto (restano {remaining}m).")
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            s['last_player_action_real'] = time.time()
            enemies = s.get('enemies', [])
            alive = [e for e in enemies if e['hp'] > 0]
            if not alive:
                raise CombatError('Nessun bersaglio disponibile.')
            if s.get('new_system_active'):
                resolver = _get_combat_resolver()
                player_id = s.get('player_id', 'player')
                # Usa mossa light base
                available_moves = _get_available_moves(state)
                chosen_move = available_moves[0] if available_moves else None
                if not chosen_move:
                    raise CombatError('Nessuna mossa disponibile.')
                # Costo stamina extra (scalare con num nemici) semplice: +5 per nemico oltre il primo
                extra_cost = max(0, (len(alive)-1) * 5)
                chosen_move = MoveSpec(
                    id=chosen_move.id,
                    name=chosen_move.name + ' (AoE)',
                    move_type=chosen_move.move_type,
                    stamina_cost=chosen_move.stamina_cost + extra_cost,
                    reach=chosen_move.reach,
                    windup_time=chosen_move.windup_time,
                    recovery_time=chosen_move.recovery_time,
                    noise_level=chosen_move.noise_level,
                    damage_base=chosen_move.damage_base,
                    damage_type=chosen_move.damage_type,
                )
                # Verifica stamina prima di procedere (manualmente)
                resolver_rng = resolver._rng or random
                if not resolver.stamina.has_stamina_for_move(player_id, chosen_move):
                    lines.append('Non hai abbastanza stamina per un attacco ad area.')
                    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
                total_report = []
                per_target_events = []
                # Scaling danno: base 50% * fattore (0.8 + 0.2 * n/(n+2)) → leggero boost su gruppi grandi
                n_alive = len(alive)
                scaling_factor = 0.5 * (0.8 + 0.2 * (n_alive / (n_alive + 2)))
                for enemy_obj in alive:
                    ctx = CombatContext(attacker_id=player_id, defender_id=enemy_obj['id'], move=chosen_move)
                    player_data = _get_player_data(state)
                    enemy_data = _get_enemy_data({'hp': enemy_obj['hp'], 'attack': enemy_obj['attack']})
                    result = resolver.resolve_attack(ctx, player_data, enemy_data)
                    if not result.success:
                        continue
                    base_damage = sum(d.amount for d in result.damage_dealt)
                    aoe_damage = max(0, int(round(base_damage * scaling_factor)))
                    enemy_obj['hp'] = max(0, enemy_obj['hp'] - aoe_damage)
                    total_report.append(f"{enemy_obj['name']} -{aoe_damage} ({enemy_obj['hp']}/{enemy_obj['max_hp']})")
                    per_target_events.append({
                        'enemy_id': enemy_obj['id'],
                        'enemy_index': enemies.index(enemy_obj),
                        'damage': aoe_damage,
                        'enemy_hp': enemy_obj['hp']
                    })
                if total_report:
                    lines.append("Colpisci tutti i nemici! " + "; ".join(total_report))
                _emit_combat_event('area_attack', {'_state': state, 'targets': per_target_events})
                # Cooldown: reuse attack interval medio (minimo 2) per gating
                base_cd = max(MIN_ATTACK_ALL_COOLDOWN_MINUTES, int(sum(e['attack_interval'] for e in alive)/len(alive)))
                s['attack_all_cooldown_total'] = _total_minutes(state) + base_cd
                _check_end(state)
                _sync_primary_alias(state)
                if s['phase'] == 'ended':
                    lines.append('Hai vinto.')
                    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
                # Process tick systems per nemico colpito (semplificato: stesso resolver.tick per ultimo target)
                # Potremmo iterare ma manteniamo compatibilità e semplicità
                lines.extend(_process_realtime_events(state))
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
        if s['phase'] != 'player':
            # Se QTE difensivo attivo: penalità e poi continuiamo
            if s['phase'] == 'qte' and s.get('qte') and s['qte'].get('type') == 'defense' and s.get('incoming_attack'):
                dmg = s.get('incoming_attack_damage') or s.get('enemy_attack',1)
                state.player_hp -= dmg
                lines.append(f"Ignori la difesa e vieni colpito per {dmg} danni! (HP: {state.player_hp}/{state.player_max_hp})")
                attacker_idx = s.get('qte', {}).get('enemy_index')
                if attacker_idx is not None and attacker_idx < len(s.get('enemies', [])):
                    s['enemies'][attacker_idx]['incoming_attack'] = False
                    s['enemies'][attacker_idx]['incoming_attack_deadline'] = None
                s['incoming_attack'] = False
                s['qte'] = None
                _check_end(state)
                if s['phase'] != 'ended':
                    s['phase'] = 'player'
            # Se ancora non player (es. offense QTE) semplicemente non consentiamo
            if s['phase'] != 'player':
                # Per compat test: annulla QTE offense scaduto implicitamente e continua
                if s.get('qte') and s['qte'].get('type') == 'offense':
                    s['qte'] = None
                    s['phase'] = 'player'
                else:
                    raise CombatError('Non è il tuo turno.')
        # Aggiorna ultimo timestamp azione giocatore
        s['last_player_action_real'] = time.time()
        # Identifica bersaglio
        enemies = s.get('enemies', [])
        target_enemy = None
        if ' ' in command:
            _, tail = command.split(' ', 1)
            tail = tail.strip()
            if tail.isdigit():
                idx = int(tail) - 1
                if 0 <= idx < len(enemies):
                    target_enemy = enemies[idx]
        # Se non specificato, usa focus se valido
        if target_enemy is None and s.get('focus_enemy_id'):
            for e in enemies:
                if e['id'] == s['focus_enemy_id'] and e['hp'] > 0:
                    target_enemy = e
                    break
        if target_enemy is None:
            for e in enemies:
                if e['hp'] > 0:
                    target_enemy = e
                    break
        if target_enemy is None and enemies:
            target_enemy = enemies[0]
        if target_enemy is None:
            raise CombatError('Nessun bersaglio disponibile.')
        # Sincronizza alias legacy al bersaglio scelto
        s['enemy_id'] = target_enemy['id']
        s['enemy_name'] = target_enemy['name']
        s['enemy_hp'] = target_enemy['hp']
        s['enemy_max_hp'] = target_enemy['max_hp']
        s['enemy_attack'] = target_enemy['attack']
        
        # Use new system if available
        if s.get('new_system_active'):
            resolver = _get_combat_resolver()
            player_id = s.get('player_id', 'player')
            enemy_id = target_enemy['id']
            
            # Get available moves and choose based on ranged mode if applicable
            available_moves = _get_available_moves(state)
            chosen_move: MoveSpec | None = None
            weapon_data = WEAPONS.get(state.player_weapon_id)
            # Allow suffix 'aimed' or 'snap': e.g., 'attack aimed' / 'attack snap'
            mode = None
            if ' ' in command:
                try:
                    tail = command.split(' ', 1)[1].strip()
                    # if first token is index (digit), next may be mode; else use tail directly
                    tokens = tail.split()
                    if tokens:
                        if tokens[0].isdigit() and len(tokens) >= 2:
                            mode = tokens[1]
                        elif tokens[0] in ('aimed','snap'):
                            mode = tokens[0]
                except Exception:
                    mode = None
            if _is_ranged_weapon(weapon_data) and mode in ('aimed','snap'):
                # pick moveset of that mode if present, else approximate via damage multiplier
                # Build a temporary move overriding damage_base by multiplier if missing
                # First, find base light move (or any)
                base = available_moves[0] if available_moves else None
                for mv in available_moves:
                    if mv.move_type == mode:
                        base = mv
                        break
                if base and base.move_type != mode:
                    # synthesize a move variant
                    movesets = weapon_data.get('movesets', {})
                    mult = movesets.get(mode, {}).get('damage_multiplier', 1.0)
                    chosen_move = MoveSpec(
                        id=f"{weapon_data['id']}_{mode}",
                        name=f"{weapon_data.get('name','')} ({mode})",
                        move_type=mode,
                        stamina_cost=movesets.get(mode, {}).get('stamina_cost', base.stamina_cost),
                        reach=base.reach,
                        windup_time=movesets.get(mode, {}).get('windup', base.windup_time),
                        recovery_time=movesets.get(mode, {}).get('recovery', base.recovery_time),
                        noise_level=base.noise_level,
                        damage_base=(weapon_data.get('damage', 1) * mult),
                        damage_type=base.damage_type,
                        status_effects=movesets.get(mode, {}).get('status_effects', [])
                    )
            if chosen_move is None:
                chosen_move = available_moves[0] if available_moves else None
            
            if not chosen_move:
                raise CombatError('Nessuna mossa disponibile.')
            
            # For ranged weapons, ensure ammo
            if _is_ranged_weapon(weapon_data):
                ok, msg = _consume_ammo_if_needed(weapon_data)
                if not ok:
                    lines.append(msg)
                    lines.extend(_process_realtime_events(state))
                    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
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
                # Realtime: nessuna fase enemy, processa eventi e resta al giocatore
                lines.extend(_process_realtime_events(state))
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            # Apply damage to legacy HP system (rounded to match display)
            total_damage = sum(d.amount for d in result.damage_dealt)
            damage_int = max(0, int(round(total_damage)))
            target_enemy['hp'] = max(0, target_enemy['hp'] - damage_int)
            s['enemy_hp'] = target_enemy['hp']
            
            # Build description
            # total_damage già calcolato
            quality_text = {
                HitQuality.GRAZE: "di striscio",
                HitQuality.NORMAL: "",
                HitQuality.CRITICAL: "critico"
            }.get(result.hit_quality, "")
            
            damage_text = f"infliggendo {damage_int} danni" if damage_int > 0 else "senza danni"
            # Ammo display suffix if ranged
            ammo_suffix = ''
            if _is_ranged_weapon(weapon_data):
                ammo_suffix = f" | Munizioni: {int(weapon_data.get('ammo_in_clip',0))}/{int(weapon_data.get('clip_size',0))} (riserva {int(weapon_data.get('ammo_reserve',0))})"
            attack_line = f"Colpisci {quality_text} il {s['enemy_name']} {damage_text}. ({s['enemy_hp']}/{s['enemy_max_hp']}){ammo_suffix}"
            lines.append(attack_line)

            # Heavy cleave: optionally hit additional enemies for scaled damage
            cleave_reports = []
            weapon_class = (weapon_data or {}).get('weapon_class') if weapon_data else None
            if weapon_class == 'heavy':
                cleave_targets = int((weapon_data or {}).get('cleave_targets', 0))
                cleave_factor = float((weapon_data or {}).get('cleave_factor', 0.6))
                if cleave_targets > 0 and cleave_factor > 0:
                    others = [e for e in enemies if e is not target_enemy and e['hp'] > 0]
                    for other in others[:cleave_targets]:
                        # Reuse the same move context against other target
                        ctx2 = CombatContext(attacker_id=player_id, defender_id=other['id'], move=chosen_move)
                        e2 = _get_enemy_data({'hp': other['hp'], 'attack': other['attack']})
                        r2 = resolver.resolve_attack(ctx2, player_data, e2)
                        if not r2.success:
                            continue
                        base2 = sum(d.amount for d in r2.damage_dealt)
                        cleave_dmg = max(0, int(round(base2 * cleave_factor)))
                        if cleave_dmg <= 0:
                            continue
                        other['hp'] = max(0, other['hp'] - cleave_dmg)
                        cleave_reports.append(f"{other['name']} -{cleave_dmg} ({other['hp']}/{other['max_hp']})")
                    if cleave_reports:
                        lines.append("Colpo pesante fende altri nemici: " + "; ".join(cleave_reports))
                        _emit_combat_event('heavy_cleave', {
                            '_state': state,
                            'enemy_id': enemy_id,
                            'targets': [
                                {
                                    'enemy_id': x['id'],
                                    'enemy_index': enemies.index(x),
                                    'enemy_hp': x['hp']
                                } for x in enemies if x is not target_enemy and x['hp']>0
                            ]
                        })
            
            # Apply status effects
            for effect in result.status_effects_applied:
                if effect.effect == StatusEffect.STAGGERED:
                    lines.append("Il nemico barcolla!")
            
            _check_end(state)
            _auto_switch_focus_if_needed(state)
            _sync_primary_alias(state)
            _emit_combat_event('player_attack', {'_state': state,'enemy_id': enemy_id,'enemy_index': enemies.index(target_enemy) if target_enemy in enemies else None,'damage': total_damage,'hit_quality': result.hit_quality.name,'enemy_hp': s['enemy_hp']})
            if s['phase'] == 'ended':
                lines.append('Hai vinto.')
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
            
            # Process system ticks
            tick_damage = resolver.tick_systems(enemy_id)
            if tick_damage:
                tick_total = sum(d.amount for d in tick_damage)
                tick_int = max(0, int(round(tick_total)))
                # Display and apply the same integer amount
                if tick_int > 0:
                    lines.append(f"Effetti stato causano {tick_int} danni aggiuntivi.")
                else:
                    lines.append("Effetti stato causano 0 danni aggiuntivi.")
                target_enemy['hp'] = max(0, target_enemy['hp'] - tick_int)
                s['enemy_hp'] = target_enemy['hp']
                _emit_combat_event('status_tick', {
                    '_state': state,
                    'enemy_id': enemy_id,
                    'enemy_index': enemies.index(target_enemy) if target_enemy in enemies else None,
                    'tick_damage': tick_total,
                    'enemy_hp': s['enemy_hp']
                })
                _check_end(state)
                _auto_switch_focus_if_needed(state)
                _auto_switch_focus_if_needed(state)
                _sync_primary_alias(state)
                if s['phase'] == 'ended':
                    lines.append('Hai vinto.')
                    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
            # Trigger QTE offensivo realtime (senza passare da enemy)
            _maybe_trigger_offense_qte(state)
            if s['phase'] == 'qte' and s.get('qte') and s['qte'].get('type') == 'offense':
                lines.append(s['qte']['prompt'])
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            # Altrimenti processa ulteriori eventi realtime
            lines.extend(_process_realtime_events(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    # Spawn nuovi nemici durante il combattimento: "spawn <enemy_id> [count]"
    if command.startswith('spawn'):
        if s['phase'] != 'player':
            return {'lines': ['Non puoi spawnare ora.'], 'hints': [], 'events_triggered': [], 'changes': {}}
        parts = command.split()
        if len(parts) < 2:
            raise CombatError('Uso: spawn <enemy_id> [count]')
        enemy_id = parts[1]
        count = 1
        if len(parts) >= 3 and parts[2].isdigit():
            count = max(1, int(parts[2]))
        base_def = MOBS.get(enemy_id)
        if not base_def:
            raise CombatError(f'Nemico sconosciuto: {enemy_id}')
        # Cloniamo definizione per evitare mutazioni
        added = []
        resolver = _get_combat_resolver()
        ai = _get_tactical_ai()
        for _ in range(count):
            entry = _create_enemy_entry(state, base_def)
            # Gestione id univoco: se esiste già, aggiungi suffisso incrementale
            existing_ids = {e['id'] for e in s.get('enemies', [])}
            if entry['id'] in existing_ids:
                suffix = 2
                base_base = entry['id']
                while f"{base_base}_{suffix}" in existing_ids:
                    suffix += 1
                entry['id'] = f"{base_base}_{suffix}"
                entry['name'] = f"{entry['name']} ({suffix})"
            s['enemies'].append(entry)
            added.append(entry['name'])
            # Inizializza entity nel resolver/AI (se non esiste già)
            if entry['id'] not in resolver._entity_data:
                enemy_data_full = _get_enemy_data({'hp': entry['hp'], 'attack': entry['attack']})
                resolver.initialize_entity(entry['id'], enemy_data_full)
                try:
                    ai_state = AIState(base_def.get('ai_state','aggressive'))
                except ValueError:
                    ai_state = AIState.AGGRESSIVE
                ai.initialize_entity(entry['id'], ai_state, base_def.get('ai_traits', {}))
        # Sincronizza alias se non c'è un nemico vivo precedente (o se prima non c'erano nemici)
        _sync_primary_alias(state)
        lines.append(f"Arrivano nuovi nemici: {', '.join(added)}")
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'spawned': len(added)}}

    if command == 'push':
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        s['last_player_action_real'] = time.time()
        # Associa push al primo vivo
        enemies = s.get('enemies', [])
        target_enemy = None
        for e in enemies:
            if e['hp'] > 0:
                target_enemy = e
                break
        if target_enemy is None and enemies:
            target_enemy = enemies[0]
        s['distance'] += 1
        s['push_decay'] = 1
        lines.append(f"Spingi {target_enemy['name']} e guadagni spazio (distanza {s['distance']}).")
        # Il nemico usa tempo per chiudere la distanza invece di attaccare: ritardiamo il prossimo attacco
        if s['distance'] > 0:
            s['distance'] -= 1
            lines.append(f"Il {s['enemy_name']} avanza per ridurre la distanza.")
            # Ritarda il prossimo attacco di un intervallo parziale
            s['next_enemy_attack_total'] = max(_total_minutes(state) + 1, s['next_enemy_attack_total'])
        # Process realtime events dopo l'azione
        lines.extend(_process_realtime_events(state))
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    if command == 'flee':
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        s['last_player_action_real'] = time.time()
        enemies = s.get('enemies', [])
        base = 0.3
        if s['distance'] > 0:
            base += 0.3
        # Bonus se almeno un nemico è ferito
        if any(e['hp'] <= e['max_hp'] * 0.4 for e in enemies):
            base += 0.2
        rng = _RNG or random
        if rng.random() < base:
            lines.append('Riesci a sganciarti e fuggire.')
            s['phase'] = 'ended'
            s['result'] = 'escaped'
            _emit_combat_event('player_escape', {'_state': state, 'enemy_id': s['enemy_id']})
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'escaped'}}
        else:
            lines.append('Tentativo di fuga fallito!')
            # Penalità: accelera il prossimo attacco del nemico
            s['next_enemy_attack_total'] = _total_minutes(state)
            _emit_combat_event('player_escape_fail', {'_state': state, 'enemy_id': s['enemy_id']})
            lines.extend(_process_realtime_events(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    if command == 'qte':
        if s['phase'] != 'qte' or not s.get('qte'):
            raise CombatError('Nessun QTE attivo.')
        if not arg:
            raise CombatError('Inserisci input QTE.')
        # QTE considerata azione
        s['last_player_action_real'] = time.time()
        expected = s['qte']['expected']
        qte_type = s['qte'].get('type', 'offense')
        if arg.lower() == expected.lower():
            effect = s['qte'].get('effect')
            if qte_type == 'offense':
                if effect == 'bonus_damage':
                    bonus = max(1, _weapon_damage(state))
                    s['enemy_hp'] -= bonus
                    lines.append(f"Colpo mirato! Bonus {bonus} danni. ({s['enemy_hp']}/{s['enemy_max_hp']})")
                    _check_end(state)
                    _emit_combat_event('qte_offense_success', {'_state': state, 'enemy_id': s['enemy_id'], 'bonus': bonus, 'enemy_hp': s['enemy_hp']})
                    if s['phase'] == 'ended':
                        lines.append('Hai vinto.')
                        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'victory'}}
                elif effect == 'reduce_next_damage':
                    s['enemy_attack'] = max(0, s['enemy_attack'] - 1)
                    lines.append('Riduci il danno del prossimo attacco.')
                    _emit_combat_event('qte_offense_success', {'_state': state, 'enemy_id': s['enemy_id'], 'effect': 'reduce_next_damage', 'enemy_attack_new': s['enemy_attack']})
                else:
                    lines.append('Reazione riuscita!')
                    _emit_combat_event('qte_offense_success', {'_state': state, 'enemy_id': s['enemy_id'], 'effect': 'generic'})
                s['phase'] = 'player'
                s['qte'] = None
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            elif qte_type == 'defense':
                if s.get('incoming_attack') or True:  # fallback: consenti comunque la parata per compat
                    lines.append('Parata riuscita! Annulli l\'attacco imminente.')
                    # Identifica attaccante associato
                    attacker_idx = s.get('qte', {}).get('enemy_index')
                    if attacker_idx is not None and attacker_idx < len(s.get('enemies', [])):
                        s['enemies'][attacker_idx]['incoming_attack'] = False
                        s['enemies'][attacker_idx]['incoming_attack_deadline'] = None
                    s['incoming_attack'] = False
                    s['qte'] = None
                    s['next_enemy_attack_total'] = _total_minutes(state) + s['enemy_attack_interval']
                    # Aggiorna anche il timer del nemico specifico (primario) per evitare immediato retrigger
                    if attacker_idx is not None and attacker_idx < len(s.get('enemies', [])):
                        s['enemies'][attacker_idx]['next_attack_total'] = s['next_enemy_attack_total']
                    s['phase'] = 'player'
                    _sync_primary_alias(state)
                    _emit_combat_event('qte_defense_success', {'_state': state, 'enemy_id': s['enemy_id']})
                    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
        else:
            # Failure
            if qte_type == 'offense':
                lines.append('Fallisci la reazione!')
                # Penalità: avvicina il prossimo attacco nemico riducendo il timer
                now_total = _total_minutes(state)
                s['next_enemy_attack_total'] = min(s['next_enemy_attack_total'], now_total + 1)
                s['qte'] = None
                s['phase'] = 'player'
                _emit_combat_event('qte_offense_fail', {'_state': state, 'enemy_id': s['enemy_id']})
                lines.extend(_process_realtime_events(state))
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
            elif qte_type == 'defense':
                lines.append('Fallisci la difesa!')
                if s.get('incoming_attack'):
                    attacker_idx = s.get('qte', {}).get('enemy_index')
                    dmg = s['incoming_attack_damage'] or s['enemy_attack']
                    state.player_hp -= dmg
                    lines.append(f"Un nemico ti colpisce infliggendo {dmg} danni! (HP: {state.player_hp}/{state.player_max_hp})")
                    if attacker_idx is not None and attacker_idx < len(s.get('enemies', [])):
                        s['enemies'][attacker_idx]['incoming_attack'] = False
                        s['enemies'][attacker_idx]['incoming_attack_deadline'] = None
                    s['incoming_attack'] = False
                    s['qte'] = None
                    _check_end(state)
                    if s['phase'] != 'ended':
                        s['next_enemy_attack_total'] = _total_minutes(state) + s['enemy_attack_interval']
                        s['phase'] = 'player'
                    _emit_combat_event('qte_defense_fail', {'_state': state, 'enemy_id': s['enemy_id'], 'damage': dmg, 'player_hp': state.player_hp})
                return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

    raise CombatError(f'Azione sconosciuta in combattimento: {command}')

def spawn_enemy(enemy_id: str) -> Dict[str, Any]:
    if enemy_id not in MOBS:
        raise CombatError(f'Nemico inesistente: {enemy_id}')
    return MOBS[enemy_id]

# --- Public realtime tick ---
def tick_combat(state: GameState) -> list[str]:
    """Processa eventi realtime (attacchi in arrivo / scadenze) senza input giocatore.

    Ritorna eventuali linee prodotte (colpi andati a segno, QTE difensivi apparsi, timeout).
    Non modifica la fase se non per effetto naturale degli eventi.
    """
    if not state.combat_session or state.combat_session.get('phase') == 'ended':
        return []
    lines: list[str] = []
    # Se c'è un QTE offensivo attivo controlla timeout
    s = state.combat_session
    if s['phase'] == 'qte' and s.get('qte') and s['qte'].get('type') == 'offense':
        if _total_minutes(state) >= s['qte']['deadline_total']:
            lines.append('Fallisci il tempo di reazione!')
            s['qte'] = None
            s['phase'] = 'player'
    # Process realtime (difesa / spawn nuovo attacco)
    lines.extend(_process_realtime_events(state))
    return lines

# --- Realtime processing helper ---
def _check_auto_reinforcements(state: GameState) -> List[str]:
    """Controlla se devono arrivare rinforzi automatici durante il combattimento."""
    s = state.combat_session
    if not s or s.get('phase') == 'ended':
        return []
    
    # Evita di spawnare rinforzi troppo spesso
    last_reinforcement = s.get('last_reinforcement_total', 0)
    now_total = _total_minutes(state)
    min_gap = 3  # Minimo 3 minuti simulati tra rinforzi
    
    if now_total - last_reinforcement < min_gap:
        return []
    
    # Calcola probabilità di rinforzi basata su vari fattori
    base_chance = 0.05  # 5% base ogni tick
    
    # Aumenta probabilità se il combattimento dura a lungo
    combat_duration = now_total - s.get('start_total', now_total)
    if combat_duration > 5:
        base_chance += 0.02  # +2% se combattimento > 5 min
    if combat_duration > 10:
        base_chance += 0.03  # +3% se combattimento > 10 min
    
    # Aumenta probabilità se ci sono pochi nemici
    alive_enemies = sum(1 for e in s.get('enemies', []) if e.get('hp', 0) > 0)
    if alive_enemies == 1:
        base_chance += 0.03  # +3% se solo 1 nemico
    elif alive_enemies == 0:
        base_chance = 0  # No rinforzi se non ci sono nemici
    
    # Limita probabilità massima
    base_chance = min(base_chance, 0.15)  # Max 15%
    
    if random.random() > base_chance:
        return []
    
    # Scegli tipo di rinforzo
    try:
        from engine.core.spawn_system import AREA_ENEMY_SPAWNS
        area_id = state.current_micro.replace(" ", "_").lower()
        
        if area_id not in AREA_ENEMY_SPAWNS:
            return []
        
        # Filtra regole con chance di rinforzi > 0
        reinforcement_rules = [rule for rule in AREA_ENEMY_SPAWNS[area_id] 
                             if rule.reinforcement_chance > 0]
        
        if not reinforcement_rules:
            return []
        
        # Scegli una regola a caso
        rule = random.choice(reinforcement_rules)
        
        # Spawna 1-2 rinforzi
        count = random.randint(1, 2)
        
        lines = []
        for _ in range(count):
            enemy_def = spawn_enemy(rule.enemy_id)
            if enemy_def and s.get('enemies') is not None:
                s['enemies'].append(enemy_def)
                lines.append(f"⚡ Rinforzi! Un {enemy_def['name']} si unisce al combattimento!")
        
        # Aggiorna timestamp ultimo rinforzo
        s['last_reinforcement_total'] = now_total
        
        return lines
        
    except Exception as e:
        # Spawn system non disponibile o errore, non bloccare il combattimento
        return []

def _process_realtime_events(state: GameState) -> List[str]:
    s = state.combat_session
    if not s or s.get('phase') == 'ended':
        return []
    out: List[str] = []
    
    # Check for automatic reinforcements
    out.extend(_check_auto_reinforcements(state))
    # Gestione inattività: se trascorsi N secondi reali senza azioni del player, anticipa attacco
    try:
        inactivity_sec = s.get('inactivity_attack_seconds', None)
        last_act = s.get('last_player_action_real')
        if inactivity_sec and last_act:
            now_real = time.time()
            if now_real - last_act >= inactivity_sec:
                # Forza un aggiornamento del clock simulato per riflettere il tempo reale trascorso
                if state.real_start_ts is not None:
                    # recompute_from_real userà time.time(); già now_real
                    state.recompute_from_real(now_real)
                # Anticipa il prossimo attacco se non già in arrivo
                if not s.get('incoming_attack'):
                    # Imposta i prox attacchi dei nemici vivi al valore corrente per QTE immediato
                    now_total_force = _total_minutes(state)
                    for e in s.get('enemies', []):
                        if e.get('hp', 0) > 0 and not e.get('incoming_attack'):
                            e['next_attack_total'] = now_total_force
    except Exception:
        pass
    now_total = _total_minutes(state)
    enemies = s.get('enemies', [])
    # Se c'è un QTE difensivo attivo, controlla landing relativo al nemico indicato
    if s.get('incoming_attack') and s.get('qte') and s['qte'].get('type') == 'defense':
        attacker_idx = s['qte'].get('enemy_index')
        if attacker_idx is not None and attacker_idx < len(enemies):
            enemy_ref = enemies[attacker_idx]
            if enemy_ref.get('incoming_attack') and now_total >= enemy_ref.get('incoming_attack_deadline', 0):
                dmg = enemy_ref.get('incoming_attack_damage') or enemy_ref['attack']
                state.player_hp -= dmg
                out.append(f"{enemy_ref['name']} ti colpisce infliggendo {dmg} danni! (HP: {state.player_hp}/{state.player_max_hp})")
                enemy_ref['incoming_attack'] = False
                enemy_ref['incoming_attack_deadline'] = None
                s['incoming_attack'] = False
                s['qte'] = None
                _check_end(state)
                if s['phase'] != 'ended':
                    s['phase'] = 'player'
                return out
    # Altrimenti valuta se un nuovo nemico deve preparare attacco (il più imminente)
    # Evita di creare nuovi QTE difensivi se ne esiste già uno attivo
    if not (s.get('qte') and s['qte'].get('type') == 'defense'):
        # Trova attacco più vicino
        next_idx = None
        earliest = 10**12
        for idx, e in enumerate(enemies):
            if e['hp'] <= 0:
                continue
            # Non considerare chi ha già un attacco in arrivo
            if e.get('incoming_attack'):
                continue
            nt = e.get('next_attack_total')
            if nt is not None and nt < earliest:
                earliest = nt
                next_idx = idx
        if next_idx is not None and now_total >= earliest and not (s['phase'] == 'qte' and s.get('qte',{}).get('type')=='offense'):
            enemy_ref = enemies[next_idx]
            enemy_ref['incoming_attack'] = True
            enemy_ref['incoming_attack_damage'] = enemy_ref['attack']
            deadline = now_total + s.get('defensive_qte_window', 1)
            enemy_ref['incoming_attack_deadline'] = deadline
            # Pianifica già il prossimo attacco dopo questo (evita retrigger immediato)
            interval = enemy_ref.get('attack_interval', s.get('enemy_attack_interval', 3)) or 3
            enemy_ref['next_attack_total'] = deadline + max(1, int(interval))
            s['phase'] = 'qte'
            rng = _RNG or random
            if _COMPLEX_QTE_ENABLED:
                # Genera codice alfanumerico 3-5 per QTE Difensivo
                length = rng.randint(QTE_CODE_LENGTH_MIN, QTE_CODE_LENGTH_MAX)
                alphabet = QTE_CODE_ALPHABET
                code = ''.join(rng.choice(alphabet) for _ in range(length))
                s['qte'] = {
                    'prompt': f'Difesa! Digita: {code}',
                    'expected': code,
                    'deadline_total': deadline,
                    'effect': None,
                    'type': 'defense',
                    'enemy_index': next_idx,
                }
            else:
                s['qte'] = {
                    'prompt': 'Difesa! Premi D!',
                    'expected': 'd',
                    'deadline_total': deadline,
                    'effect': None,
                    'type': 'defense',
                    'enemy_index': next_idx,
                }
            s['incoming_attack'] = True
            s['incoming_attack_damage'] = enemy_ref['attack']
            out.append(f"{enemy_ref['name']} prepara un attacco!")
            out.append(s['qte']['prompt'])
    return out

__all__ = [
    'start_combat', 'resolve_combat_action', 'resolve_attack', 'CombatError', 'tick_combat',
    'WEAPONS', 'MOBS', 'inject_content', 'spawn_enemy',
    'set_combat_seed', 'set_complex_qte',
    # New system classes and models for direct use
    'CombatContext', 'CombatResult', 'MoveSpec', 'DamageType', 'StatusEffect', 'HitQuality'
]

# --- Test helpers (non production) ---
# Rinominati per non essere raccolti automaticamente da pytest.
def helper_reset_player_phase(state: GameState):  # pragma: no cover - utility
    """Forza la fase del giocatore eliminando qualsiasi QTE / attacco in arrivo.

    Inoltre spinge in avanti il prossimo attacco dei nemici così che un comando
    immediatamente successivo (es. focus) non venga interrotto da un QTE difensivo
    generato istantaneamente perché il clock simulato è già oltre next_attack_total.
    """
    if not state.combat_session:
        return
    s = state.combat_session
    now_total = _total_minutes(state)
    s['qte'] = None
    s['incoming_attack'] = False
    for e in s.get('enemies', []):
        e['incoming_attack'] = False
        e['incoming_attack_deadline'] = None
        # Sposta in avanti il prossimo attacco (fallback 3 minuti se assente l'intervallo)
        interval = e.get('attack_interval') or 3
        e['next_attack_total'] = now_total + max(1, interval)
    s['phase'] = 'player'
    _sync_primary_alias(state)

def helper_force_focus_autoswitch(state: GameState):  # pragma: no cover - utility
    if not state.combat_session:
        return
    _auto_switch_focus_if_needed(state)

__all__.extend(['helper_reset_player_phase', 'helper_force_focus_autoswitch'])

def _handle_passive_interaction(state: GameState, registry: ContentRegistry, action: str, 
                               target_enemy: Dict[str, Any], mob_def: Dict[str, Any], 
                               behavioral_traits: Dict[str, Any], lines: List[str]) -> Dict[str, Any]:
    """Handle special interactions with passive mobs (hunt, capture, negotiate)."""
    s = state.combat_session
    ai_state = mob_def.get('ai_state', 'aggressive')
    
    # Only allow special interactions with passive mobs
    if ai_state not in ['passive', 'surrendered', 'fleeing']:
        if action == 'hunt':
            lines.append(f"Il {target_enemy['name']} è troppo aggressivo per essere cacciato facilmente.")
        elif action == 'capture':
            lines.append(f"Il {target_enemy['name']} si oppone troppo fieramente per essere catturato.")
        elif action == 'negotiate':
            lines.append(f"Il {target_enemy['name']} non sembra interessato a negoziare.")
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
    
    s['last_player_action_real'] = time.time()
    
    if action == 'hunt':
        return _handle_hunt_action(state, target_enemy, mob_def, behavioral_traits, lines)
    elif action == 'capture':
        return _handle_capture_action(state, target_enemy, mob_def, behavioral_traits, lines)
    elif action == 'negotiate':
        return _handle_negotiate_action(state, target_enemy, mob_def, behavioral_traits, lines)
    
    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

def _handle_hunt_action(state: GameState, target_enemy: Dict[str, Any], 
                       mob_def: Dict[str, Any], behavioral_traits: Dict[str, Any], 
                       lines: List[str]) -> Dict[str, Any]:
    """Handle hunting passive animals."""
    s = state.combat_session
    
    # Check if it's an animal
    if not behavioral_traits.get('is_animal', False):
        lines.append(f"Non puoi cacciare {target_enemy['name']} - non è un animale.")
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
    
    # Hunting success based on animal's current health and flee chance
    flee_chance = behavioral_traits.get('flee_chance', 0.3)
    current_hp_ratio = target_enemy['hp'] / target_enemy['max_hp']
    
    # Higher success if animal is wounded
    base_success = 0.7 if current_hp_ratio < 0.5 else 0.4
    
    # Random factor
    global _RNG
    rng = _RNG or random
    success_roll = rng.random()
    
    if success_roll < base_success:
        # Successful hunt
        target_enemy['hp'] = 0
        lines.append(f"Riesci a cacciare {target_enemy['name']} con successo.")
        
        # Enhanced loot for successful hunting
        _handle_passive_mob_loot(state, target_enemy, mob_def, enhanced_loot=True)
        
        # Moral consequences for hunting
        moral_impact = behavioral_traits.get('moral_impact', 'none')
        if moral_impact == 'negative':
            lines.append("Senti un peso sulla coscienza per aver ucciso una creatura innocente.")
        elif moral_impact == 'neutral':
            lines.append("È la legge della sopravvivenza.")
            
        _emit_combat_event('successful_hunt', {
            '_state': state,
            'target_id': target_enemy['id'],
            'moral_impact': moral_impact
        })
    
    elif success_roll < base_success + flee_chance:
        # Animal flees
        lines.append(f"{target_enemy['name']} ti sfugge e scappa via!")
        target_enemy['hp'] = 0  # Remove from combat
        
        _emit_combat_event('prey_escaped', {
            '_state': state,
            'target_id': target_enemy['id']
        })
    
    else:
        # Failed hunt - animal becomes defensive
        lines.append(f"{target_enemy['name']} percepisce il pericolo e assume una posizione difensiva.")
        
        # Change AI state to cautious (defensive but not fleeing)
        if s.get('new_system_active'):
            ai = _get_tactical_ai()
            ai._ai_states[target_enemy['id']] = AIState.CAUTIOUS
    
    _check_end(state)
    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

def _handle_capture_action(state: GameState, target_enemy: Dict[str, Any], 
                          mob_def: Dict[str, Any], behavioral_traits: Dict[str, Any], 
                          lines: List[str]) -> Dict[str, Any]:
    """Handle capturing surrendered humans."""
    s = state.combat_session
    
    ai_state = mob_def.get('ai_state', 'aggressive')
    if ai_state != 'surrendered':
        lines.append(f"{target_enemy['name']} non si è arreso - non puoi catturarlo.")
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
    
    # Capture attempt
    global _RNG
    rng = _RNG or random
    
    # Success factors
    surrender_complete = behavioral_traits.get('surrender_complete', True)
    has_hidden_weapon = behavioral_traits.get('has_hidden_weapon', False)
    
    base_success = 0.8 if surrender_complete else 0.5
    
    if rng.random() < base_success:
        # Successful capture
        target_enemy['hp'] = 0  # Remove from combat
        lines.append(f"Catturi {target_enemy['name']} con successo.")
        
        # Loot from captured person (search them)
        _handle_passive_mob_loot(state, target_enemy, mob_def, captured=True)
        
        # Moral choice outcome
        if behavioral_traits.get('has_family_photo', False):
            lines.append("Frugando tra i suoi effetti personali, trovi una foto di famiglia...")
            lines.append("Ti fa riflettere sulla tua decisione.")
        
        _emit_combat_event('successful_capture', {
            '_state': state,
            'target_id': target_enemy['id'],
            'has_story': behavioral_traits.get('has_personal_story', False)
        })
    
    else:
        if has_hidden_weapon:
            # Hidden weapon revealed - combat continues
            lines.append(f"{target_enemy['name']} estrae un'arma nascosta e ti attacca!")
            
            # Change to aggressive temporarily
            if s.get('new_system_active'):
                ai = _get_tactical_ai()
                ai._ai_states[target_enemy['id']] = AIState.AGGRESSIVE
            
            # Immediate counter-attack
            damage = behavioral_traits.get('hidden_weapon_damage', 5)
            state.player_hp = max(0, state.player_hp - damage)
            lines.append(f"Vieni colpito per {damage} danni! HP: {state.player_hp}/{state.player_max_hp}")
        
        else:
            # Just becomes more defensive
            lines.append(f"{target_enemy['name']} si irrigidisce e oppone resistenza.")
    
    _check_end(state)
    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

def _handle_negotiate_action(state: GameState, target_enemy: Dict[str, Any], 
                           mob_def: Dict[str, Any], behavioral_traits: Dict[str, Any], 
                           lines: List[str]) -> Dict[str, Any]:
    """Handle negotiating with surrendered or wounded humans."""
    s = state.combat_session
    
    ai_state = mob_def.get('ai_state', 'aggressive')
    
    # Only works with surrendered or wounded humans
    if not behavioral_traits.get('can_negotiate', False):
        lines.append(f"{target_enemy['name']} non sembra in grado di negoziare.")
        return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
    
    # Negotiation outcomes based on mob's story and traits
    global _RNG
    rng = _RNG or random
    
    negotiation_outcomes = mob_def.get('negotiation_outcomes', [])
    if not negotiation_outcomes:
        # Default outcomes
        negotiation_outcomes = [
            {"success": True, "message": "Si allontana rapidamente senza fare storie.", "loot": None},
            {"success": False, "message": "Scuote la testa e rimane in posizione difensiva.", "loot": None}
        ]
    
    # Choose random outcome
    outcome = rng.choice(negotiation_outcomes)
    
    if outcome['success']:
        # Successful negotiation - enemy leaves peacefully
        target_enemy['hp'] = 0  # Remove from combat
        lines.append(f"Riesci a negoziare con {target_enemy['name']}.")
        lines.append(outcome['message'])
        
        # Possible reward for peaceful resolution
        if outcome.get('loot'):
            loot_item = outcome['loot']
            _add_item_to_inventory(state, loot_item, 1)
            # Load item name from items.json if possible, otherwise use ID
            item_name = loot_item.replace('_', ' ').title()
            lines.append(f"Ti offre {item_name} come segno di gratitudine.")
        
        # Positive moral impact
        lines.append("Ti senti meglio per aver risolto la situazione pacificamente.")
        
        _emit_combat_event('successful_negotiation', {
            '_state': state,
            'target_id': target_enemy['id'],
            'peaceful_resolution': True
        })
    
    else:
        # Failed negotiation
        lines.append(f"Il tentativo di negoziazione con {target_enemy['name']} fallisce.")
        lines.append(outcome['message'])
        
        # May become more hostile or remain defensive
        if behavioral_traits.get('becomes_hostile_on_failed_negotiation', False):
            if s.get('new_system_active'):
                ai = _get_tactical_ai()
                ai._ai_states[target_enemy['id']] = AIState.AGGRESSIVE
            lines.append(f"{target_enemy['name']} diventa ostile!")
    
    _check_end(state)
    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}

def _handle_passive_mob_loot(state: GameState, enemy: Dict[str, Any], 
                            mob_def: Dict[str, Any], enhanced_loot: bool = False, 
                            captured: bool = False) -> None:
    """Enhanced loot handling for passive mob interactions."""
    # Get loot table
    loot_table = mob_def.get('loot_table', [])
    if not loot_table:
        return
    
    # Enhanced loot gives better chances or additional items
    loot_modifier = 1.5 if enhanced_loot else 1.0
    
    global _RNG
    rng = _RNG or random
    
    for loot_entry in loot_table:
        item_id = loot_entry['item']
        base_chance = loot_entry.get('chance', 1.0)
        quantity = loot_entry.get('quantity', 1)
        
        # Apply modifier
        final_chance = min(1.0, base_chance * loot_modifier)
        
        if rng.random() < final_chance:
            # Special handling for captured humans (they have more items on them)
            if captured and 'captured_bonus' in loot_entry:
                quantity = loot_entry['captured_bonus']
            
            _add_item_to_inventory(state, item_id, quantity)
