"""Core combat data models and enums."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class DamageType(Enum):
    """Types of damage with different resistances/vulnerabilities."""
    BLUNT = "blunt"
    SLASH = "slash"
    PIERCE = "pierce"
    BLEED = "bleed"
    BURN = "burn"
    SHOCK = "shock"


class StatusEffect(Enum):
    """Status effects that can be applied to entities."""
    BLEED = "bleed"
    BURN = "burn"
    CONCUSSED = "concussed"
    STAGGERED = "staggered"
    CRIPPLED = "crippled"


class HitQuality(Enum):
    """Quality of hits based on weapon handling + posture gap + situation."""
    GRAZE = "graze"
    NORMAL = "normal"
    CRITICAL = "critical"


class AIState(Enum):
    """AI behavioral states."""
    AGGRESSIVE = "aggressive"
    CAUTIOUS = "cautious"
    PACK = "pack"


@dataclass
class StatusEffectInstance:
    """Instance of a status effect with duration and parameters."""
    effect: StatusEffect
    duration: int  # remaining ticks
    intensity: float = 1.0
    source: Optional[str] = None  # what caused it
    
    def tick(self) -> bool:
        """Process one tick. Returns True if effect should be removed."""
        self.duration -= 1
        return self.duration <= 0


@dataclass
class DamageInstance:
    """Damage to be applied with type and amount."""
    amount: float
    damage_type: DamageType
    source: Optional[str] = None
    hit_quality: HitQuality = HitQuality.NORMAL


@dataclass
class MoveSpec:
    """Specification for a combat move."""
    id: str
    name: str
    move_type: str  # light/heavy/thrust/aimed/parry/bash
    stamina_cost: int
    reach: int = 1
    windup_time: int = 1  # turns to prepare
    recovery_time: int = 1  # turns to recover
    noise_level: int = 1
    damage_base: float = 1.0
    damage_type: DamageType = DamageType.BLUNT
    status_effects: List[tuple[StatusEffect, int, float]] = field(default_factory=list)  # effect, duration, intensity


@dataclass
class CombatContext:
    """Context for a combat resolution."""
    attacker_id: str
    defender_id: str
    move: MoveSpec
    situational_modifiers: Dict[str, float] = field(default_factory=dict)  # flanking, cover, darkness, etc.
    

@dataclass
class CombatResult:
    """Result of a combat action."""
    success: bool
    damage_dealt: List[DamageInstance] = field(default_factory=list)
    status_effects_applied: List[StatusEffectInstance] = field(default_factory=list)
    stamina_consumed: int = 0
    posture_damage: float = 0.0
    hit_quality: HitQuality = HitQuality.NORMAL
    description: List[str] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)  # for telemetry