"""NPC response validation system.

Validates both JSON schema compliance and semantic correctness
of NPC AI responses against game state and whitelists.
"""
import json
import jsonschema
from pathlib import Path
from .schema import NPC_RESPONSE_SCHEMA

def load_whitelist(path):
    """Load intent/action whitelist from JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def validate_schema(payload: dict):
    """Validate payload against NPC response schema."""
    jsonschema.validate(payload, NPC_RESPONSE_SCHEMA)
    return True

def validate_semantics(payload, world, npc, player, intents_wh, actions_wh):
    """Validate semantic correctness of NPC response against game state.
    
    Args:
        payload: The NPC response dictionary
        world: World state
        npc: NPC object
        player: Player state  
        intents_wh: Set of allowed intents
        actions_wh: Set of allowed actions
        
    Returns:
        tuple: (is_valid: bool, error_reason: str or None)
    """
    # Check intent whitelist
    if payload["intent"] not in intents_wh:
        return False, "intent_not_allowed"
    
    # Check action whitelist and game state constraints
    action = payload.get("action")
    if action and action not in actions_wh:
        return False, "action_not_allowed"
    
    # Basic game state validation examples
    if action:
        # Example: bandage action requires bandage in inventory
        if action == "give_bandage_to_frank":
            # Check if NPC has bandage (simplified check)
            if not hasattr(npc, 'inventory') or 'bandage' not in getattr(npc, 'inventory', []):
                return False, "action_missing_item"
        
        # Example: melee attack requires proximity
        if action == "attack_melee":
            # Check distance (simplified - would need proper distance calculation)
            if hasattr(npc, 'current_micro') and hasattr(player, 'current_micro'):
                if npc.current_micro != getattr(player, 'current_micro', None):
                    return False, "action_too_far"
        
        # Example: cooldown check (simplified)
        if action in ["attack_melee", "attack_ranged"]:
            # Would check actual cooldown system here
            pass
    
    return True, None