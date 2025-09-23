"""Tactical AI system for combat entities."""
from __future__ import annotations
import random
from typing import Dict, Any, List, Optional
from .models import AIState, MoveSpec, StatusEffect
from .stamina import StaminaSystem
from .posture import PostureSystem
from .effects import StatusEffectSystem


class TacticalAI:
    """AI system that chooses moves based on tactical situation."""
    
    def __init__(self, stamina: StaminaSystem, posture: PostureSystem, effects: StatusEffectSystem):
        self.stamina = stamina
        self.posture = posture
        self.effects = effects
        self._ai_states: Dict[str, AIState] = {}
        self._ai_traits: Dict[str, Dict[str, Any]] = {}
    
    def initialize_entity(self, entity_id: str, ai_state: AIState = AIState.AGGRESSIVE, traits: Optional[Dict[str, Any]] = None):
        """Initialize AI for an entity."""
        self._ai_states[entity_id] = ai_state
        self._ai_traits[entity_id] = traits or {}
    
    def choose_move(self, entity_id: str, available_moves: List[MoveSpec], targets: List[str], 
                   situation: Dict[str, Any]) -> Optional[MoveSpec]:
        """Choose the best move for the AI entity."""
        if not available_moves:
            return None
        
        ai_state = self._ai_states.get(entity_id, AIState.AGGRESSIVE)
        traits = self._ai_traits.get(entity_id, {})
        
        # Filter moves by stamina availability
        viable_moves = [
            move for move in available_moves 
            if self.stamina.has_stamina_for_move(entity_id, move)
        ]
        
        if not viable_moves:
            # No stamina for any moves, choose lowest cost move anyway (will fail but be handled)
            return min(available_moves, key=lambda m: m.stamina_cost)
        
        # Choose move based on AI state and situation
        if ai_state == AIState.AGGRESSIVE:
            return self._choose_aggressive_move(entity_id, viable_moves, targets, situation, traits)
        elif ai_state == AIState.CAUTIOUS:
            return self._choose_cautious_move(entity_id, viable_moves, targets, situation, traits)
        elif ai_state == AIState.PACK:
            return self._choose_pack_move(entity_id, viable_moves, targets, situation, traits)
        
        # Fallback: random choice
        return random.choice(viable_moves)
    
    def _choose_aggressive_move(self, entity_id: str, moves: List[MoveSpec], targets: List[str], 
                               situation: Dict[str, Any], traits: Dict[str, Any]) -> MoveSpec:
        """Choose move for aggressive AI."""
        # Prefer high damage moves
        heavy_moves = [m for m in moves if m.move_type in ['heavy', 'thrust']]
        if heavy_moves and self.stamina.get_stamina(entity_id) > 50:  # Only use heavy moves with good stamina
            return max(heavy_moves, key=lambda m: m.damage_base)
        
        # Otherwise prefer any damaging move
        damaging_moves = [m for m in moves if m.damage_base > 0]
        if damaging_moves:
            return max(damaging_moves, key=lambda m: m.damage_base)
        
        return random.choice(moves)
    
    def _choose_cautious_move(self, entity_id: str, moves: List[MoveSpec], targets: List[str], 
                             situation: Dict[str, Any], traits: Dict[str, Any]) -> MoveSpec:
        """Choose move for cautious AI."""
        # Check our health/posture situation
        my_posture_ratio = self.posture.get_posture_ratio(entity_id)
        my_stamina_ratio = self.stamina.get_stamina(entity_id) / self.stamina.get_max_stamina(entity_id)
        
        # If low on resources, prefer defensive moves
        if my_posture_ratio < 0.4 or my_stamina_ratio < 0.3:
            defensive_moves = [m for m in moves if m.move_type in ['parry', 'light']]
            if defensive_moves:
                return min(defensive_moves, key=lambda m: m.stamina_cost)  # Lowest cost defensive move
        
        # If we have an advantage, be more aggressive
        if targets:
            target_id = targets[0]  # Focus on first target
            target_posture_ratio = self.posture.get_posture_ratio(target_id)
            
            if target_posture_ratio < 0.3:  # Target is vulnerable
                heavy_moves = [m for m in moves if m.move_type in ['heavy', 'thrust']]
                if heavy_moves:
                    return max(heavy_moves, key=lambda m: m.damage_base)
        
        # Default: balanced approach
        balanced_moves = [m for m in moves if m.move_type in ['light', 'thrust']]
        if balanced_moves:
            return random.choice(balanced_moves)
        
        return random.choice(moves)
    
    def _choose_pack_move(self, entity_id: str, moves: List[MoveSpec], targets: List[str], 
                         situation: Dict[str, Any], traits: Dict[str, Any]) -> MoveSpec:
        """Choose move for pack AI."""
        pack_size = situation.get('allied_count', 1)
        
        # Pack tactics: coordinate attacks
        if pack_size > 1:
            # If allies are present, focus on the most vulnerable target
            if targets:
                target_scores = []
                for target_id in targets:
                    target_posture = self.posture.get_posture_ratio(target_id)
                    target_effects = len(self.effects.get_effects(target_id))
                    # Lower posture and more effects = higher priority target
                    score = (1.0 - target_posture) + (target_effects * 0.1)
                    target_scores.append((target_id, score))
                
                # Target the most vulnerable
                best_target = max(target_scores, key=lambda x: x[1])[0]
                
                # Choose high damage moves for coordinated assault
                heavy_moves = [m for m in moves if m.move_type in ['heavy', 'thrust']]
                if heavy_moves and self.stamina.get_stamina(entity_id) > 30:
                    return max(heavy_moves, key=lambda m: m.damage_base)
        
        # Pack hunter trait: apply status effects to weaken prey
        if traits.get('pack_hunter', False):
            status_moves = [m for m in moves if m.status_effects]
            if status_moves and random.random() < 0.4:  # 40% chance to use status move
                return random.choice(status_moves)
        
        # Default pack behavior: aggressive but coordinated
        return self._choose_aggressive_move(entity_id, moves, targets, situation, traits)
    
    def should_retreat(self, entity_id: str, situation: Dict[str, Any]) -> bool:
        """Determine if AI should attempt to retreat."""
        ai_state = self._ai_states.get(entity_id, AIState.AGGRESSIVE)
        traits = self._ai_traits.get(entity_id, {})
        
        # Never retreat if aggressive and not heavily damaged
        if ai_state == AIState.AGGRESSIVE:
            my_posture_ratio = self.posture.get_posture_ratio(entity_id)
            return my_posture_ratio < 0.15  # Only retreat if almost broken
        
        # Cautious AI retreats more readily
        if ai_state == AIState.CAUTIOUS:
            my_posture_ratio = self.posture.get_posture_ratio(entity_id)
            my_stamina_ratio = self.stamina.get_stamina(entity_id) / self.stamina.get_max_stamina(entity_id)
            
            # Retreat if low on resources or heavily outnumbered
            if my_posture_ratio < 0.3 or my_stamina_ratio < 0.2:
                return True
            
            enemy_count = situation.get('enemy_count', 1)
            if enemy_count > 2:  # Outnumbered
                return True
        
        # Pack AI retreats if pack is broken
        if ai_state == AIState.PACK:
            allied_count = situation.get('allied_count', 1)
            if allied_count == 1:  # Pack is gone, retreat
                return True
        
        return False
    
    def update_ai_state(self, entity_id: str, situation: Dict[str, Any]):
        """Update AI state based on combat situation."""
        current_state = self._ai_states.get(entity_id, AIState.AGGRESSIVE)
        traits = self._ai_traits.get(entity_id, {})
        
        # Dynamic state changes based on situation
        my_posture_ratio = self.posture.get_posture_ratio(entity_id)
        
        # Switch to cautious if badly hurt (unless always aggressive)
        if my_posture_ratio < 0.3 and current_state != AIState.AGGRESSIVE:
            if not traits.get('always_aggressive', False):
                self._ai_states[entity_id] = AIState.CAUTIOUS
        
        # Pack hunters become aggressive when pack is strong
        if traits.get('pack_hunter', False):
            allied_count = situation.get('allied_count', 1)
            if allied_count > 2:
                self._ai_states[entity_id] = AIState.PACK
            elif allied_count == 1:
                self._ai_states[entity_id] = AIState.CAUTIOUS
    
    def get_target_priority(self, entity_id: str, targets: List[str]) -> List[str]:
        """Sort targets by priority for AI."""
        if not targets:
            return []
        
        target_scores = []
        for target_id in targets:
            score = 0.0
            
            # Lower posture = higher priority
            posture_ratio = self.posture.get_posture_ratio(target_id)
            score += (1.0 - posture_ratio) * 10
            
            # More status effects = higher priority (easier target)
            effect_count = len(self.effects.get_effects(target_id))
            score += effect_count * 2
            
            # Staggered targets are high priority
            if self.effects.has_effect(target_id, StatusEffect.STAGGERED):
                score += 5
            
            target_scores.append((target_id, score))
        
        # Sort by score (highest first)
        target_scores.sort(key=lambda x: x[1], reverse=True)
        return [target_id for target_id, _ in target_scores]