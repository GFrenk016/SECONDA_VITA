"""Status effects system with duration and tick management."""
from __future__ import annotations
from typing import Dict, List, Optional
from .models import StatusEffect, StatusEffectInstance, DamageInstance, DamageType


class StatusEffectSystem:
    """Manages status effects on entities with duration and tick processing."""
    
    def __init__(self):
        self._effects: Dict[str, List[StatusEffectInstance]] = {}
    
    def apply_effect(self, entity_id: str, effect: StatusEffectInstance):
        """Apply a status effect to an entity."""
        if entity_id not in self._effects:
            self._effects[entity_id] = []
        
        # Check if effect already exists - either stack or refresh
        existing = self._find_existing_effect(entity_id, effect.effect)
        if existing:
            # Refresh duration if new one is longer, or stack intensity
            if effect.duration > existing.duration:
                existing.duration = effect.duration
            existing.intensity = min(3.0, existing.intensity + effect.intensity * 0.5)  # Cap at 3x intensity
        else:
            self._effects[entity_id].append(effect)
    
    def _find_existing_effect(self, entity_id: str, effect_type: StatusEffect) -> Optional[StatusEffectInstance]:
        """Find existing effect of given type on entity."""
        if entity_id not in self._effects:
            return None
        
        for effect in self._effects[entity_id]:
            if effect.effect == effect_type:
                return effect
        return None
    
    def has_effect(self, entity_id: str, effect_type: StatusEffect) -> bool:
        """Check if entity has a specific status effect."""
        return self._find_existing_effect(entity_id, effect_type) is not None
    
    def get_effects(self, entity_id: str) -> List[StatusEffectInstance]:
        """Get all active effects on an entity."""
        return self._effects.get(entity_id, []).copy()
    
    def tick_effects(self, entity_id: str) -> List[DamageInstance]:
        """Process one tick of all effects on entity. Returns damage to apply."""
        if entity_id not in self._effects:
            return []
        
        damage_instances = []
        remaining_effects = []
        
        for effect in self._effects[entity_id]:
            # Process effect for this tick
            damage = self._process_effect_tick(effect)
            if damage:
                damage_instances.extend(damage)
            
            # Check if effect should continue
            if not effect.tick():
                remaining_effects.append(effect)
        
        # Update effects list
        self._effects[entity_id] = remaining_effects
        if not remaining_effects:
            del self._effects[entity_id]
        
        return damage_instances
    
    def _process_effect_tick(self, effect: StatusEffectInstance) -> List[DamageInstance]:
        """Process one tick of a specific effect."""
        damage = []
        
        if effect.effect == StatusEffect.BLEED:
            # Bleed does damage over time
            bleed_damage = 1.0 * effect.intensity
            damage.append(DamageInstance(
                amount=bleed_damage,
                damage_type=DamageType.BLEED,
                source=f"bleed_tick"
            ))
        
        elif effect.effect == StatusEffect.BURN:
            # Burn does fire damage over time
            burn_damage = 1.5 * effect.intensity
            damage.append(DamageInstance(
                amount=burn_damage,
                damage_type=DamageType.BURN,
                source=f"burn_tick"
            ))
        
        # Other effects (concussed, staggered, crippled) don't deal direct damage
        # but affect other systems
        
        return damage
    
    def remove_effect(self, entity_id: str, effect_type: StatusEffect):
        """Remove a specific effect type from entity."""
        if entity_id not in self._effects:
            return
        
        self._effects[entity_id] = [
            effect for effect in self._effects[entity_id] 
            if effect.effect != effect_type
        ]
        
        if not self._effects[entity_id]:
            del self._effects[entity_id]
    
    def clear_effects(self, entity_id: str):
        """Clear all effects from an entity."""
        if entity_id in self._effects:
            del self._effects[entity_id]
    
    def get_movement_penalty(self, entity_id: str) -> float:
        """Get movement penalty from status effects."""
        penalty = 1.0
        
        if self.has_effect(entity_id, StatusEffect.CRIPPLED):
            penalty *= 0.5  # 50% movement speed
        
        if self.has_effect(entity_id, StatusEffect.STAGGERED):
            penalty *= 0.7  # 30% movement penalty
        
        return penalty
    
    def get_accuracy_penalty(self, entity_id: str) -> float:
        """Get accuracy penalty from status effects."""
        penalty = 1.0
        
        if self.has_effect(entity_id, StatusEffect.CONCUSSED):
            concussed = self._find_existing_effect(entity_id, StatusEffect.CONCUSSED)
            if concussed:
                penalty *= (1.0 - 0.2 * concussed.intensity)  # Up to 60% accuracy loss
        
        if self.has_effect(entity_id, StatusEffect.STAGGERED):
            penalty *= 0.8  # 20% accuracy penalty
        
        return penalty