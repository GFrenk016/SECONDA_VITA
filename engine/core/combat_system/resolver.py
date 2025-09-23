"""Core combat resolution system."""
from __future__ import annotations
import random
from typing import Dict, Any, Optional, List
from .models import (
    CombatContext, CombatResult, MoveSpec, DamageInstance, DamageType, 
    HitQuality, StatusEffectInstance, StatusEffect
)
from .stamina import StaminaSystem
from .posture import PostureSystem
from .effects import StatusEffectSystem


class CombatResolver:
    """Core combat resolution coordinator.

    Aggiunto supporto a RNG iniettabile per determinismo test:
    - self._rng: se impostato viene usato al posto del modulo random globale
    - metodo set_rng(r) per iniezione
    """
    
    def __init__(self):
        self.stamina = StaminaSystem()
        self.posture = PostureSystem()
        self.effects = StatusEffectSystem()
        self._entity_data: Dict[str, Dict[str, Any]] = {}
        self._resistance_data: Dict[str, Dict[DamageType, float]] = {}
        self._rng: Optional[random.Random] = None

    def set_rng(self, rng: random.Random):
        self._rng = rng
        
    def initialize_entity(self, entity_id: str, entity_data: Dict[str, Any]):
        """Initialize an entity for combat."""
        self._entity_data[entity_id] = entity_data.copy()
        
        # Initialize subsystems
        max_stamina = entity_data.get('max_stamina', 100)
        self.stamina.initialize_entity(entity_id, max_stamina)
        
        max_posture = entity_data.get('max_posture', 100.0)
        stagger_threshold = entity_data.get('stagger_threshold', 0.3)
        self.posture.initialize_entity(entity_id, max_posture, stagger_threshold)
        
        # Load resistances/vulnerabilities
        resistances = entity_data.get('resistances', {})
        self._resistance_data[entity_id] = {}
        for damage_type in DamageType:
            # Default resistance is 1.0 (no modification)
            self._resistance_data[entity_id][damage_type] = resistances.get(damage_type.value, 1.0)
    
    def resolve_attack(self, ctx: CombatContext, attacker_data: Dict[str, Any], defender_data: Dict[str, Any]) -> CombatResult:
        """Main combat resolution function - maintains public API."""
        result = CombatResult(success=False)
        
        # Check if attacker has enough stamina
        if not self.stamina.has_stamina_for_move(ctx.attacker_id, ctx.move):
            result.description.append(f"Attaccante senza stamina per {ctx.move.name}")
            result.events.append({
                'type': 'stamina_insufficient',
                'attacker': ctx.attacker_id,
                'move': ctx.move.id,
                'stamina_needed': ctx.move.stamina_cost,
                'stamina_available': self.stamina.get_stamina(ctx.attacker_id)
            })
            return result
        
        # Consume stamina
        self.stamina.consume_stamina(ctx.attacker_id, ctx.move.stamina_cost)
        result.stamina_consumed = ctx.move.stamina_cost
        
        # Calculate hit quality
        hit_quality = self._calculate_hit_quality(ctx)
        result.hit_quality = hit_quality
        
        # Check if attack hits based on quality
        hit_chance = self._get_hit_chance(hit_quality, ctx)
        rng = self._rng or random
        if rng.random() > hit_chance:
            result.description.append(f"Attacco mancato - {hit_quality.value}")
            result.events.append({
                'type': 'attack_missed',
                'attacker': ctx.attacker_id,
                'defender': ctx.defender_id,
                'move': ctx.move.id,
                'hit_quality': hit_quality.value
            })
            return result
        
        result.success = True
        
        # Calculate damage
        damage = self._calculate_damage(ctx, hit_quality)
        if damage.amount > 0:
            result.damage_dealt.append(damage)
        
        # Calculate posture damage
        posture_damage = self._calculate_posture_damage(ctx, hit_quality)
        if posture_damage > 0:
            result.posture_damage = posture_damage
            staggered, stagger_effect = self.posture.damage_posture(ctx.defender_id, posture_damage)
            if staggered and stagger_effect:
                result.status_effects_applied.append(stagger_effect)
                self.effects.apply_effect(ctx.defender_id, stagger_effect)
        
        # Apply move-specific status effects
        for effect_spec in ctx.move.status_effects:
            effect_type, duration, intensity = effect_spec
            status_effect = StatusEffectInstance(
                effect=effect_type,
                duration=duration,
                intensity=intensity,
                source=ctx.move.id
            )
            result.status_effects_applied.append(status_effect)
            self.effects.apply_effect(ctx.defender_id, status_effect)
        
        # Build description
        damage_text = f"{damage.amount:.1f}" if damage.amount > 0 else "nessun"
        result.description.append(f"Colpo {hit_quality.value}: {damage_text} danni {damage.damage_type.value}")
        
        # Log event for telemetry
        result.events.append({
            'type': 'attack_resolved',
            'attacker': ctx.attacker_id,
            'defender': ctx.defender_id,
            'move': ctx.move.id,
            'hit_quality': hit_quality.value,
            'damage': damage.amount,
            'damage_type': damage.damage_type.value,
            'posture_damage': posture_damage,
            'stamina_consumed': ctx.move.stamina_cost
        })
        
        return result
    
    def _calculate_hit_quality(self, ctx: CombatContext) -> HitQuality:
        """Calculate hit quality based on weapon handling + posture gap + situation."""
        base_score = 0.5  # Base 50% chance for normal hit
        
        # Weapon handling (from attacker data)
        attacker_data = self._entity_data.get(ctx.attacker_id, {})
        weapon_handling = attacker_data.get('weapon_handling', 0.5)
        base_score += (weapon_handling - 0.5) * 0.3  # ±15% based on skill
        
        # Posture gap
        posture_gap = self.posture.get_posture_gap(ctx.attacker_id, ctx.defender_id)
        base_score += posture_gap * 0.2  # Up to ±20% based on posture difference
        
        # Situational modifiers
        for modifier, value in ctx.situational_modifiers.items():
            if modifier == 'flanking':
                base_score += 0.15  # 15% bonus for flanking
            elif modifier == 'cover':
                base_score -= 0.1  # 10% penalty for cover
            elif modifier == 'darkness':
                base_score -= 0.05  # 5% penalty for darkness
            elif modifier == 'rain':
                base_score -= 0.05  # 5% penalty for rain
        
        # Stamina penalties
        stamina_penalty = self.stamina.get_stamina_penalty(ctx.attacker_id)
        base_score *= stamina_penalty
        
        # Status effect penalties
        accuracy_penalty = self.effects.get_accuracy_penalty(ctx.attacker_id)
        base_score *= accuracy_penalty
        
        # Determine quality based on final score
        if base_score >= 0.85:
            return HitQuality.CRITICAL
        elif base_score <= 0.25:
            return HitQuality.GRAZE
        else:
            return HitQuality.NORMAL
    
    def _get_hit_chance(self, quality: HitQuality, ctx: CombatContext) -> float:
        """Get actual hit chance based on quality."""
        base_chances = {
            HitQuality.GRAZE: 0.4,
            HitQuality.NORMAL: 0.7,
            HitQuality.CRITICAL: 0.9
        }
        return base_chances[quality]
    
    def _calculate_damage(self, ctx: CombatContext, quality: HitQuality) -> DamageInstance:
        """Calculate damage amount with resistances."""
        base_damage = ctx.move.damage_base
        
        # Quality modifiers
        quality_multipliers = {
            HitQuality.GRAZE: 0.5,
            HitQuality.NORMAL: 1.0,
            HitQuality.CRITICAL: 1.8
        }
        damage = base_damage * quality_multipliers[quality]
        
        # Apply defender resistances
        defender_resistances = self._resistance_data.get(ctx.defender_id, {})
        resistance = defender_resistances.get(ctx.move.damage_type, 1.0)
        damage *= resistance
        
        return DamageInstance(
            amount=damage,
            damage_type=ctx.move.damage_type,
            source=ctx.move.id,
            hit_quality=quality
        )
    
    def _calculate_posture_damage(self, ctx: CombatContext, quality: HitQuality) -> float:
        """Calculate posture damage based on move and hit quality."""
        base_posture_damage = ctx.move.damage_base * 0.8  # Posture damage is related to move damage
        
        quality_multipliers = {
            HitQuality.GRAZE: 0.3,
            HitQuality.NORMAL: 1.0,
            HitQuality.CRITICAL: 1.5
        }
        
        return base_posture_damage * quality_multipliers[quality]
    
    def tick_systems(self, entity_id: str) -> List[DamageInstance]:
        """Tick all systems for an entity (called each turn)."""
        damage_instances = []
        
        # Tick status effects
        effect_damage = self.effects.tick_effects(entity_id)
        damage_instances.extend(effect_damage)
        
        # Regenerate stamina and posture
        self.stamina.tick_regeneration(entity_id)
        self.posture.tick_regeneration(entity_id)
        
        return damage_instances