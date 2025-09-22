"""Minimal hybrid combat system (Phase 1).

Design goals:
- Single enemy at a time (walker style) in the same micro room.
- Blend narrative beats (Telltale style QTE prompts) with lightweight roguelike stats.
- Deterministic & testable: uses GameState.total_minutes concept for QTE deadlines.
- Text-only API returning ActionResult-like dict (lines, changes, etc.).

Flow summary:
start_combat(state, registry, enemy_def) -> initializes state.combat_session
resolve_combat_action(state, registry, command, payload)

Commands:
- 'attack': Player attacks. If enemy survives -> enemy may trigger QTE or attack.
- 'qte <input>': Player answers active QTE prompt.
- 'status': Returns current combat snapshot.
- 'flee': (not yet implemented - future extension)

Enemy definition (dict) minimal keys:
{
  'id': 'walker1',
  'name': 'Walker',
  'hp': 6,
  'attack': 2,
  'qte_chance': 0.5,   # chance after player attack that next phase is a QTE (dodge)
  'qte_prompt': 'Premi A per schivare!',
  'qte_expected': 'a',
  'qte_window_minutes': 2  # simulated minutes allowed (works with manual_offset in tests)
}

Weapon simple stats (looked up by id in WEAPONS registry below) -> {'id','name','damage'}.
If no weapon equipped, base damage = 1.

End states:
- Player hp <= 0: combat_session['phase'] = 'ended' + result 'defeat'
- Enemy hp <= 0: combat_session['phase'] = 'ended' + result 'victory'

This module purposefully avoids randomness inside resolution except QTE triggering, which uses random.random().
Tests can set random.seed for determinism.
"""
from __future__ import annotations
from typing import Dict, Any, List
import random
from .state import GameState
from .registry import ContentRegistry

# Simple in-module weapon definitions (could move to assets later)
WEAPONS: Dict[str, Dict[str, Any]] = {
    'knife': {'id': 'knife', 'name': 'Coltello', 'damage': 3},  # fallback se asset non caricato
}

MOBS: Dict[str, Dict[str, Any]] = {}

def inject_content(weapons: Dict[str, Any], mobs: Dict[str, Any]):
    """Inject loaded JSON weapon/mob definitions (id -> data)."""
    if weapons:
        WEAPONS.update(weapons)
    if mobs:
        MOBS.update(mobs)

class CombatError(Exception):
    pass

def _total_minutes(state: GameState) -> int:
    return state.day_count * 24 * 60 + state.time_minutes

def start_combat(state: GameState, registry: ContentRegistry, enemy: Dict[str, Any]) -> Dict[str, Any]:
    if state.combat_session and state.combat_session.get('phase') != 'ended':
        raise CombatError('Sei già in combattimento.')
    # Pick a first QTE seed list (if any)
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
        'distance': 0,  # 0 = ingaggio, >0 = allontanato (push aumenta)
        'push_decay': 0,  # turni rimanenti prima che il nemico riaccorci
    }
    state.combat_session = session
    lines = [f"Un {session['enemy_name']} ti si avvicina minaccioso.", f"HP Nemico: {session['enemy_hp']}/{session['enemy_max_hp']} | I tuoi HP: {state.player_hp}/{state.player_max_hp}"]
    return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {'combat': 'started'}}

def _weapon_damage(state: GameState) -> int:
    if state.player_weapon_id and state.player_weapon_id in WEAPONS:
        return WEAPONS[state.player_weapon_id]['damage']
    return 1

def _check_end(state: GameState):
    s = state.combat_session
    if not s:
        return
    if s['enemy_hp'] <= 0:
        s['enemy_hp'] = 0
        s['phase'] = 'ended'
        s['result'] = 'victory'
    elif state.player_hp <= 0:
        state.player_hp = 0
        s['phase'] = 'ended'
        s['result'] = 'defeat'

def _maybe_trigger_qte(state: GameState):
    s = state.combat_session
    if not s or s['phase'] != 'enemy':
        return
    if s['qte_chance'] <= 0 or not s['qte_prompt']:
        # fallback: maybe pool based prompts
        pass
    # Use pool if available to vary body part prompts
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
    s = state.combat_session
    if not s or s['phase'] not in ('enemy', 'qte'):
        return []
    # If phase was 'qte' and we reach here means failure due to timeout or wrong input
    dmg = s['enemy_attack']
    state.player_hp -= dmg
    lines = [f"Il {s['enemy_name']} ti colpisce infliggendo {dmg} danni. (HP: {state.player_hp}/{state.player_max_hp})"]
    _check_end(state)
    if s['phase'] != 'ended':
        s['phase'] = 'player'
        s['qte'] = None
    return lines

def resolve_combat_action(state: GameState, registry: ContentRegistry, command: str, arg: str | None = None) -> Dict[str, Any]:
    if not state.combat_session:
        raise CombatError('Non sei in combattimento.')
    s = state.combat_session
    lines: list[str] = []
    # Update potential QTE timeout before action
    if s['phase'] == 'qte' and s.get('qte'):
        if _total_minutes(state) >= s['qte']['deadline_total']:
            # Timeout -> enemy hits
            lines.append('Fallisci il tempo di reazione!')
            lines.extend(_enemy_attack(state))
            return {'lines': lines, 'hints': [], 'events_triggered': [], 'changes': {}}
    if s['phase'] == 'ended':
        return {'lines': ['Il combattimento è già concluso.'], 'hints': [], 'events_triggered': [], 'changes': {}}

    command = command.lower().strip()
    if command == 'status':
        status_line = f"Nemico {s['enemy_name']} HP {s['enemy_hp']}/{s['enemy_max_hp']} | Tu {state.player_hp}/{state.player_max_hp} | Fase: {s['phase']}"
        if s['phase'] == 'qte' and s['qte']:
            remaining = max(0, s['qte']['deadline_total'] - _total_minutes(state))
            status_line += f" | QTE: {s['qte']['prompt']} (restano {remaining} minuti)"
        return {'lines': [status_line], 'hints': [], 'events_triggered': [], 'changes': {}}

    if command == 'attack':
        if s['phase'] != 'player':
            raise CombatError('Non è il tuo turno.')
        dmg = _weapon_damage(state)
        s['enemy_hp'] -= dmg
        lines.append(f"Colpisci il {s['enemy_name']} infliggendo {dmg} danni. ({s['enemy_hp']}/{s['enemy_max_hp']})")
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
        # Otherwise direct enemy attack
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

__all__ = ['start_combat', 'resolve_combat_action', 'CombatError', 'WEAPONS', 'MOBS', 'inject_content', 'spawn_enemy']
