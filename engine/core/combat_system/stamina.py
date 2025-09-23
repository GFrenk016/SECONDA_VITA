"""Stamina system for combat moves and penalties."""
from __future__ import annotations
from typing import Dict, Optional
from .models import MoveSpec


class StaminaSystem:
    """Manages stamina for combat entities."""
    
    def __init__(self):
        self._stamina: Dict[str, int] = {}
        self._max_stamina: Dict[str, int] = {}
    
    def initialize_entity(self, entity_id: str, max_stamina: int = 100):
        """Initialize stamina for an entity."""
        self._stamina[entity_id] = max_stamina
        self._max_stamina[entity_id] = max_stamina
    
    def get_stamina(self, entity_id: str) -> int:
        """Get current stamina for entity."""
        return self._stamina.get(entity_id, 0)
    
    def get_max_stamina(self, entity_id: str) -> int:
        """Get max stamina for entity."""
        return self._max_stamina.get(entity_id, 100)
    
    def has_stamina_for_move(self, entity_id: str, move: MoveSpec) -> bool:
        """Check if entity has enough stamina for a move."""
        current = self.get_stamina(entity_id)
        return current >= move.stamina_cost
    
    def consume_stamina(self, entity_id: str, amount: int) -> bool:
        """Consume stamina. Returns True if successful."""
        current = self.get_stamina(entity_id)
        if current >= amount:
            self._stamina[entity_id] = current - amount
            return True
        return False
    
    def restore_stamina(self, entity_id: str, amount: int):
        """Restore stamina up to maximum."""
        current = self.get_stamina(entity_id)
        max_stamina = self.get_max_stamina(entity_id)
        self._stamina[entity_id] = min(max_stamina, current + amount)
    
    def is_out_of_stamina(self, entity_id: str) -> bool:
        """Check if entity is out of stamina."""
        return self.get_stamina(entity_id) <= 0
    
    def get_stamina_penalty(self, entity_id: str) -> float:
        """Get hit penalty multiplier based on stamina level."""
        current = self.get_stamina(entity_id)
        max_stamina = self.get_max_stamina(entity_id)
        
        if max_stamina == 0:
            return 1.0
            
        stamina_ratio = current / max_stamina
        
        # Penalties kick in when stamina drops below 30%
        if stamina_ratio > 0.3:
            return 1.0
        elif stamina_ratio > 0.1:
            return 0.8  # 20% penalty
        else:
            return 0.5  # 50% penalty when nearly exhausted
    
    def can_use_heavy_moves(self, entity_id: str) -> bool:
        """Check if entity has enough stamina for heavy moves."""
        return not self.is_out_of_stamina(entity_id)
    
    def tick_regeneration(self, entity_id: str, regen_amount: int = 5):
        """Regenerate stamina each turn."""
        self.restore_stamina(entity_id, regen_amount)