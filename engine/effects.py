"""Effects system for managing temporary effects like buffs, debuffs, and status conditions.

This module provides a unified system for applying and managing temporary effects
on players and other entities in the game.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class EffectType(Enum):
    """Types of effects that can be applied."""
    HEAL = "heal"
    RESTORE_ENERGY = "restore_energy"
    BUFF_STAT = "buff_stat"
    DAMAGE_OVER_TIME = "damage_over_time"
    STATUS_CONDITION = "status_condition"
    RESISTANCE = "resistance"


@dataclass
class Effect:
    """Base effect definition."""
    id: str
    name: str
    effect_type: EffectType
    duration_ticks: int
    intensity: float = 1.0
    target_stat: Optional[str] = None
    description: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ActiveEffect:
    """An active effect instance on a target."""
    effect: Effect
    remaining_ticks: int
    applied_tick: int
    source: str
    target_id: str
    stacks: int = 1
    
    def is_expired(self, current_tick: int) -> bool:
        """Check if effect has expired."""
        if self.effect.duration_ticks <= 0:  # Permanent effect
            return False
        return self.remaining_ticks <= 0
    
    def tick(self) -> bool:
        """Process one tick of this effect. Returns True if still active."""
        if self.effect.duration_ticks > 0:
            self.remaining_ticks -= 1
        return not self.is_expired(0)  # Check if expired after tick


class EffectManager:
    """Manages all active effects on entities."""
    
    def __init__(self):
        self.active_effects: Dict[str, List[ActiveEffect]] = {}
        self.effect_definitions: Dict[str, Effect] = {}
        self.current_tick: int = 0
        self.tick_callbacks: List[Callable[[str, List[ActiveEffect]], None]] = []
    
    def register_effect(self, effect: Effect):
        """Register an effect definition."""
        self.effect_definitions[effect.id] = effect
    
    def add_tick_callback(self, callback: Callable[[str, List[ActiveEffect]], None]):
        """Add a callback that gets called during tick processing."""
        self.tick_callbacks.append(callback)
    
    def apply_effect(self, target_id: str, effect_id: str, source: str = "unknown", 
                    duration_override: Optional[int] = None, intensity_override: Optional[float] = None) -> bool:
        """Apply an effect to a target."""
        effect_def = self.effect_definitions.get(effect_id)
        if not effect_def:
            return False
        
        if target_id not in self.active_effects:
            self.active_effects[target_id] = []
        
        # Check for existing effect and handle stacking
        existing = self._find_active_effect(target_id, effect_id)
        
        duration = duration_override if duration_override is not None else effect_def.duration_ticks
        intensity = intensity_override if intensity_override is not None else effect_def.intensity
        
        if existing:
            # Refresh duration and increase stacks for stackable effects
            existing.remaining_ticks = duration
            if "stackable" in effect_def.tags:
                existing.stacks += 1
        else:
            # Create new active effect
            active_effect = ActiveEffect(
                effect=effect_def,
                remaining_ticks=duration,
                applied_tick=self.current_tick,
                source=source,
                target_id=target_id
            )
            
            # Override intensity if specified
            if intensity_override is not None:
                # Create a copy of the effect with modified intensity
                modified_effect = Effect(
                    id=effect_def.id,
                    name=effect_def.name,
                    effect_type=effect_def.effect_type,
                    duration_ticks=effect_def.duration_ticks,
                    intensity=intensity,
                    target_stat=effect_def.target_stat,
                    description=effect_def.description,
                    tags=effect_def.tags.copy()
                )
                active_effect.effect = modified_effect
            
            self.active_effects[target_id].append(active_effect)
        
        return True
    
    def remove_effect(self, target_id: str, effect_id: str) -> bool:
        """Remove a specific effect from a target."""
        if target_id not in self.active_effects:
            return False
        
        effects = self.active_effects[target_id]
        original_count = len(effects)
        
        self.active_effects[target_id] = [e for e in effects if e.effect.id != effect_id]
        
        return len(self.active_effects[target_id]) < original_count
    
    def remove_effects_by_source(self, target_id: str, source: str) -> int:
        """Remove all effects from a specific source. Returns number removed."""
        if target_id not in self.active_effects:
            return 0
        
        effects = self.active_effects[target_id]
        original_count = len(effects)
        
        self.active_effects[target_id] = [e for e in effects if e.source != source]
        
        return original_count - len(self.active_effects[target_id])
    
    def get_active_effects(self, target_id: str) -> List[ActiveEffect]:
        """Get all active effects on a target."""
        return self.active_effects.get(target_id, []).copy()
    
    def has_effect(self, target_id: str, effect_id: str) -> bool:
        """Check if target has a specific effect active."""
        return self._find_active_effect(target_id, effect_id) is not None
    
    def get_effect_value(self, target_id: str, effect_id: str) -> float:
        """Get the current value/intensity of an effect."""
        active_effect = self._find_active_effect(target_id, effect_id)
        if active_effect:
            return active_effect.effect.intensity * active_effect.stacks
        return 0.0
    
    def tick_effects(self, target_id: Optional[str] = None) -> Dict[str, List[str]]:
        """Process one tick of effects. Returns messages by target."""
        self.current_tick += 1
        messages = {}
        
        targets = [target_id] if target_id else list(self.active_effects.keys())
        
        for tid in targets:
            if tid not in self.active_effects:
                continue
            
            target_messages = []
            active_effects = self.active_effects[tid]
            remaining_effects = []
            
            for effect in active_effects:
                # Process effect tick
                if effect.tick():
                    remaining_effects.append(effect)
                    
                    # Generate tick messages for certain effect types
                    tick_msg = self._process_effect_tick(effect)
                    if tick_msg:
                        target_messages.append(tick_msg)
                else:
                    # Effect expired
                    expire_msg = self._get_expiry_message(effect)
                    if expire_msg:
                        target_messages.append(expire_msg)
            
            self.active_effects[tid] = remaining_effects
            
            if target_messages:
                messages[tid] = target_messages
            
            # Call registered callbacks
            for callback in self.tick_callbacks:
                callback(tid, remaining_effects)
        
        return messages
    
    def _find_active_effect(self, target_id: str, effect_id: str) -> Optional[ActiveEffect]:
        """Find an active effect by ID."""
        if target_id not in self.active_effects:
            return None
        
        for effect in self.active_effects[target_id]:
            if effect.effect.id == effect_id:
                return effect
        
        return None
    
    def _process_effect_tick(self, effect: ActiveEffect) -> Optional[str]:
        """Process one tick of an effect and return a message if applicable."""
        if effect.effect.effect_type == EffectType.DAMAGE_OVER_TIME:
            damage = effect.effect.intensity * effect.stacks
            return f"Taking {damage:.1f} {effect.effect.name} damage."
        
        return None
    
    def _get_expiry_message(self, effect: ActiveEffect) -> Optional[str]:
        """Get message when an effect expires."""
        if effect.effect.effect_type == EffectType.BUFF_STAT:
            return f"{effect.effect.name} has worn off."
        elif effect.effect.effect_type == EffectType.STATUS_CONDITION:
            return f"No longer {effect.effect.name.lower()}."
        
        return None
    
    def get_stat_modifiers(self, target_id: str) -> Dict[str, float]:
        """Get all stat modifiers currently active on a target."""
        modifiers = {}
        
        if target_id not in self.active_effects:
            return modifiers
        
        for effect in self.active_effects[target_id]:
            if effect.effect.effect_type == EffectType.BUFF_STAT and effect.effect.target_stat:
                stat = effect.effect.target_stat
                value = effect.effect.intensity * effect.stacks
                
                if stat in modifiers:
                    modifiers[stat] += value
                else:
                    modifiers[stat] = value
        
        return modifiers
    
    def get_resistances(self, target_id: str) -> Dict[str, float]:
        """Get all resistance modifiers currently active on a target."""
        resistances = {}
        
        if target_id not in self.active_effects:
            return resistances
        
        for effect in self.active_effects[target_id]:
            if effect.effect.effect_type == EffectType.RESISTANCE and effect.effect.target_stat:
                resistance_type = effect.effect.target_stat
                value = effect.effect.intensity * effect.stacks
                
                if resistance_type in resistances:
                    resistances[resistance_type] += value
                else:
                    resistances[resistance_type] = value
        
        return resistances


# Global effect manager instance
_effect_manager = EffectManager()


def get_effect_manager() -> EffectManager:
    """Get the global effect manager."""
    return _effect_manager


def create_default_effects():
    """Create and register default effect definitions."""
    effects = [
        Effect(
            id="healing_over_time",
            name="Regeneration",
            effect_type=EffectType.HEAL,
            duration_ticks=300,  # 5 minutes
            intensity=2.0,
            description="Slowly restores health over time."
        ),
        Effect(
            id="strength_boost",
            name="Strength Boost",
            effect_type=EffectType.BUFF_STAT,
            duration_ticks=600,  # 10 minutes
            intensity=5.0,
            target_stat="strength",
            description="Temporarily increases strength."
        ),
        Effect(
            id="poison",
            name="Poisoned",
            effect_type=EffectType.DAMAGE_OVER_TIME,
            duration_ticks=180,  # 3 minutes
            intensity=1.5,
            description="Suffering from poison damage.",
            tags=["debuff", "stackable"]
        ),
        Effect(
            id="fire_resistance",
            name="Fire Ward",
            effect_type=EffectType.RESISTANCE,
            duration_ticks=480,  # 8 minutes
            intensity=25.0,
            target_stat="fire",
            description="Increased resistance to fire damage."
        ),
        Effect(
            id="exhaustion",
            name="Exhausted",
            effect_type=EffectType.STATUS_CONDITION,
            duration_ticks=240,  # 4 minutes
            intensity=1.0,
            description="Reduced combat effectiveness due to exhaustion.",
            tags=["debuff"]
        )
    ]
    
    for effect in effects:
        _effect_manager.register_effect(effect)