"""Posture (Poise) system for stagger mechanics."""
from __future__ import annotations
from typing import Dict, Tuple
from .models import StatusEffect, StatusEffectInstance


class PostureSystem:
    """Manages posture/poise for entities - when broken, entity staggers."""
    
    def __init__(self):
        self._posture: Dict[str, float] = {}
        self._max_posture: Dict[str, float] = {}
        self._stagger_threshold: Dict[str, float] = {}
    
    def initialize_entity(self, entity_id: str, max_posture: float = 100.0, stagger_threshold: float = 0.3):
        """Initialize posture for an entity."""
        self._posture[entity_id] = max_posture
        self._max_posture[entity_id] = max_posture
        self._stagger_threshold[entity_id] = stagger_threshold
    
    def get_posture(self, entity_id: str) -> float:
        """Get current posture for entity."""
        return self._posture.get(entity_id, 100.0)
    
    def get_max_posture(self, entity_id: str) -> float:
        """Get max posture for entity."""
        return self._max_posture.get(entity_id, 100.0)
    
    def get_posture_ratio(self, entity_id: str) -> float:
        """Get posture as ratio of maximum (0.0 to 1.0)."""
        current = self.get_posture(entity_id)
        max_posture = self.get_max_posture(entity_id)
        return current / max_posture if max_posture > 0 else 0.0
    
    def damage_posture(self, entity_id: str, damage: float) -> Tuple[bool, StatusEffectInstance | None]:
        """Damage posture. Returns (staggered, stagger_effect)."""
        current = self.get_posture(entity_id)
        new_posture = max(0.0, current - damage)
        self._posture[entity_id] = new_posture
        
        # Check if posture broken (staggered)
        threshold = self._stagger_threshold[entity_id] * self.get_max_posture(entity_id)
        if new_posture <= threshold and current > threshold:
            # Just broke posture - apply stagger
            stagger_effect = StatusEffectInstance(
                effect=StatusEffect.STAGGERED,
                duration=2,  # 2 turns staggered
                intensity=1.0,
                source="posture_break"
            )
            return True, stagger_effect
        
        return False, None
    
    def restore_posture(self, entity_id: str, amount: float):
        """Restore posture up to maximum."""
        current = self.get_posture(entity_id)
        max_posture = self.get_max_posture(entity_id)
        self._posture[entity_id] = min(max_posture, current + amount)
    
    def get_posture_gap(self, attacker_id: str, defender_id: str) -> float:
        """Get posture gap between attacker and defender for hit quality calculation."""
        attacker_posture = self.get_posture_ratio(attacker_id)
        defender_posture = self.get_posture_ratio(defender_id)
        
        # Higher gap = better chance for attacker
        return attacker_posture - defender_posture
    
    def is_staggered(self, entity_id: str) -> bool:
        """Check if entity is currently staggered (below threshold)."""
        current = self.get_posture(entity_id)
        threshold = self._stagger_threshold[entity_id] * self.get_max_posture(entity_id)
        return current <= threshold
    
    def tick_regeneration(self, entity_id: str, regen_amount: float = 10.0):
        """Regenerate posture each turn."""
        self.restore_posture(entity_id, regen_amount)