"""Player statistics system with base stats, derived stats, and temporary effects.

Manages health, energy, morale, attributes, resistances and buff/debuff effects.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import time


@dataclass
class StatModifier:
    """Temporary stat modifier with duration."""
    stat: str
    amount: float
    duration_ticks: int
    applied_tick: int
    source: str = "unknown"
    
    def is_expired(self, current_tick: int) -> bool:
        """Check if modifier has expired."""
        if self.duration_ticks <= 0:  # Permanent modifier
            return False
        return current_tick >= self.applied_tick + self.duration_ticks
    
    def is_permanent(self) -> bool:
        """Check if modifier is permanent."""
        return self.duration_ticks <= 0


@dataclass
class PlayerStats:
    """Player statistics container."""
    # Base stats (0-100 where applicable)
    health: int = 100
    max_health: int = 100
    energy: int = 100
    max_energy: int = 100
    morale: int = 75
    max_morale: int = 100
    
    # Attributes (base values, can be modified by equipment)
    strength: int = 10
    agility: int = 10
    intellect: int = 10
    perception: int = 10
    charisma: int = 10
    luck: int = 10
    
    # Resistances (0-100, percentage resistance)
    bleed_resistance: int = 0
    poison_resistance: int = 0
    fire_resistance: int = 0
    cold_resistance: int = 0
    
    # Active modifiers
    modifiers: List[StatModifier] = field(default_factory=list)
    
    # Tracking
    current_tick: int = 0
    
    def clamp_stats(self):
        """Ensure all stats are within valid ranges."""
        self.health = max(0, min(self.health, self.max_health))
        self.energy = max(0, min(self.energy, self.max_energy))
        self.morale = max(0, min(self.morale, self.max_morale))
        
        # Clamp resistances to 0-100
        self.bleed_resistance = max(0, min(self.bleed_resistance, 100))
        self.poison_resistance = max(0, min(self.poison_resistance, 100))
        self.fire_resistance = max(0, min(self.fire_resistance, 100))
        self.cold_resistance = max(0, min(self.cold_resistance, 100))
        
        # Attributes can go negative but have reasonable limits
        for attr in ['strength', 'agility', 'intellect', 'perception', 'charisma', 'luck']:
            current_value = getattr(self, attr)
            setattr(self, attr, max(1, min(current_value, 50)))  # 1-50 range
    
    def get_modified_stat(self, stat_name: str) -> float:
        """Get stat value including all active modifiers."""
        base_value = getattr(self, stat_name, 0)
        total_modifier = 0.0
        
        for modifier in self.modifiers:
            if modifier.stat == stat_name and not modifier.is_expired(self.current_tick):
                total_modifier += modifier.amount
        
        return float(base_value) + total_modifier
    
    def get_carry_capacity(self) -> float:
        """Calculate carrying capacity based on strength."""
        base_strength = self.get_modified_stat('strength')
        return 10.0 + (base_strength * 2.0)  # Base 10kg + 2kg per strength
    
    def get_crit_chance(self, weapon_bonus: float = 0.0) -> float:
        """Calculate critical hit chance based on luck and weapon."""
        base_luck = self.get_modified_stat('luck')
        return min(0.5, (base_luck * 0.02) + weapon_bonus)  # 2% per luck point, max 50%
    
    def get_evasion(self) -> float:
        """Calculate evasion chance based on agility."""
        base_agility = self.get_modified_stat('agility')
        return min(0.3, base_agility * 0.015)  # 1.5% per agility point, max 30%
    
    def get_vision_range(self) -> int:
        """Calculate vision range based on perception."""
        base_perception = self.get_modified_stat('perception')
        return max(1, int(2 + (base_perception * 0.2)))  # Base 2 + 0.2 per perception
    
    def get_effective_resistance(self, damage_type: str) -> float:
        """Get effective resistance for a damage type."""
        resistance_map = {
            'bleed': 'bleed_resistance',
            'poison': 'poison_resistance', 
            'fire': 'fire_resistance',
            'cold': 'cold_resistance'
        }
        
        resistance_stat = resistance_map.get(damage_type)
        if not resistance_stat:
            return 0.0
        
        return self.get_modified_stat(resistance_stat) / 100.0  # Convert to 0-1 range
    
    def add_modifier(self, stat: str, amount: float, duration_ticks: int, source: str = "unknown"):
        """Add a temporary stat modifier."""
        modifier = StatModifier(
            stat=stat,
            amount=amount,
            duration_ticks=duration_ticks,
            applied_tick=self.current_tick,
            source=source
        )
        self.modifiers.append(modifier)
    
    def remove_modifiers_by_source(self, source: str):
        """Remove all modifiers from a specific source."""
        self.modifiers = [m for m in self.modifiers if m.source != source]
    
    def tick_modifiers(self):
        """Process one tick of all modifiers, removing expired ones."""
        self.current_tick += 1
        
        # Remove expired modifiers
        self.modifiers = [m for m in self.modifiers if not m.is_expired(self.current_tick)]
        
        # Clamp all stats after modifier changes
        self.clamp_stats()
    
    def get_active_buffs(self) -> List[Dict[str, Any]]:
        """Get list of active buff information."""
        buffs = []
        for modifier in self.modifiers:
            if not modifier.is_expired(self.current_tick):
                remaining_ticks = 0
                if modifier.duration_ticks > 0:
                    remaining_ticks = max(0, modifier.applied_tick + modifier.duration_ticks - self.current_tick)
                
                buffs.append({
                    'stat': modifier.stat,
                    'amount': modifier.amount,
                    'remaining_ticks': remaining_ticks,
                    'is_permanent': modifier.is_permanent(),
                    'source': modifier.source
                })
        
        return buffs
    
    def heal(self, amount: int) -> int:
        """Heal for amount, returns actual healing done."""
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        self.clamp_stats()
        return self.health - old_health
    
    def take_damage(self, amount: int, damage_type: str = "physical") -> int:
        """Take damage with resistance calculation. Returns actual damage taken."""
        resistance = self.get_effective_resistance(damage_type)
        actual_damage = int(amount * (1.0 - resistance))
        
        old_health = self.health
        self.health = max(0, self.health - actual_damage)
        self.clamp_stats()
        return old_health - self.health
    
    def restore_energy(self, amount: int) -> int:
        """Restore energy, returns actual restoration."""
        old_energy = self.energy
        self.energy = min(self.max_energy, self.energy + amount)
        self.clamp_stats()
        return self.energy - old_energy
    
    def consume_energy(self, amount: int) -> bool:
        """Consume energy, returns True if successful."""
        if self.energy >= amount:
            self.energy = max(0, self.energy - amount)
            self.clamp_stats()
            return True
        return False
    
    def adjust_morale(self, amount: int) -> int:
        """Adjust morale, returns actual change."""
        old_morale = self.morale
        self.morale = max(0, min(self.max_morale, self.morale + amount))
        self.clamp_stats()
        return self.morale - old_morale
    
    def get_health_percentage(self) -> float:
        """Get health as percentage."""
        return (self.health / self.max_health) * 100.0 if self.max_health > 0 else 0.0
    
    def get_energy_percentage(self) -> float:
        """Get energy as percentage."""
        return (self.energy / self.max_energy) * 100.0 if self.max_energy > 0 else 0.0
    
    def get_morale_percentage(self) -> float:
        """Get morale as percentage."""
        return (self.morale / self.max_morale) * 100.0 if self.max_morale > 0 else 0.0
    
    def is_alive(self) -> bool:
        """Check if player is alive."""
        return self.health > 0
    
    def is_exhausted(self) -> bool:
        """Check if player is out of energy."""
        return self.energy <= 0
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of current status."""
        return {
            'health': f"{self.health}/{self.max_health} ({self.get_health_percentage():.1f}%)",
            'energy': f"{self.energy}/{self.max_energy} ({self.get_energy_percentage():.1f}%)",
            'morale': f"{self.morale}/{self.max_morale} ({self.get_morale_percentage():.1f}%)",
            'carry_capacity': f"{self.get_carry_capacity():.1f}kg",
            'crit_chance': f"{self.get_crit_chance() * 100:.1f}%",
            'evasion': f"{self.get_evasion() * 100:.1f}%",
            'vision_range': self.get_vision_range(),
            'active_buffs': len(self.get_active_buffs())
        }


def create_default_stats() -> PlayerStats:
    """Create default player stats."""
    return PlayerStats()


def apply_item_effects(stats: PlayerStats, effects: List[Dict[str, Any]]) -> List[str]:
    """Apply item effects to player stats. Returns list of effect messages."""
    messages = []
    
    for effect in effects:
        if 'heal' in effect:
            amount = effect['heal']
            actual = stats.heal(amount)
            if actual > 0:
                messages.append(f"Restored {actual} health.")
        
        elif 'restore' in effect:
            restore_data = effect['restore']
            if 'energy' in restore_data:
                amount = restore_data['energy']
                actual = stats.restore_energy(amount)
                if actual > 0:
                    messages.append(f"Restored {actual} energy.")
        
        elif 'buff' in effect:
            buff_data = effect['buff']
            stat = buff_data.get('stat')
            amount = buff_data.get('amount', 0)
            duration = buff_data.get('duration_ticks', 300)  # Default 5 minutes
            
            if stat and amount != 0:
                stats.add_modifier(stat, amount, duration, "item_effect")
                if duration > 0:
                    messages.append(f"Gained {amount:+.1f} {stat} for {duration} ticks.")
                else:
                    messages.append(f"Gained permanent {amount:+.1f} {stat}.")
        
        elif 'damage_over_time' in effect or 'dot' in effect:
            dot_data = effect.get('damage_over_time', effect.get('dot', {}))
            damage_type = dot_data.get('type', 'poison')
            amount = dot_data.get('amount', 1)
            duration = dot_data.get('duration', 60)
            
            # Apply negative health modifier for DoT effect
            stats.add_modifier('health', -amount, duration, f"dot_{damage_type}")
            messages.append(f"Suffering {amount} {damage_type} damage over {duration} ticks.")
        
        elif 'resist' in effect:
            resist_data = effect['resist']
            resist_type = resist_data.get('type')
            amount = resist_data.get('amount', 0)
            duration = resist_data.get('duration', 300)
            
            if resist_type and amount > 0:
                resist_stat = f"{resist_type}_resistance"
                stats.add_modifier(resist_stat, amount, duration, "item_effect")
                messages.append(f"Gained {amount} {resist_type} resistance for {duration} ticks.")
    
    return messages