"""Declarative condition evaluation DSL for quest system.

This module provides a unified condition checking system that supports:
- has_item: Check inventory for items
- flag_is: Check game flags
- in_location: Check player location
- stat_gte: Check player stats
- relation_gte: Check NPC relationships
- time_between: Check time ranges
- weather_in: Check weather conditions
"""

from typing import List
from .model import Condition

def check(condition: Condition, gs) -> bool:
    """Check if a single condition is met.
    
    Args:
        condition: The condition to evaluate
        gs: GameState object with current game state
        
    Returns:
        True if condition is satisfied, False otherwise
    """
    op = condition.op
    args = condition.args
    
    if op == "has_item":
        item_id = args.get("id")
        required_qty = args.get("qty", 1)
        
        # Check new inventory system first
        if hasattr(gs, 'player_inventory') and gs.player_inventory:
            current_qty = gs.player_inventory.get(item_id, 0)
            return current_qty >= required_qty
        
        # Fallback to legacy inventory  
        if hasattr(gs, 'inventory'):
            if isinstance(gs.inventory, dict):
                return gs.inventory.get(item_id, 0) >= required_qty
            elif isinstance(gs.inventory, list):
                return gs.inventory.count(item_id) >= required_qty
        
        return False
    
    elif op == "flag_is":
        key = args.get("key")
        expected_value = args.get("value", True)
        actual_value = gs.flags.get(key, False)
        return actual_value == expected_value
    
    elif op == "in_location":
        # Support hierarchical location checking
        world = args.get("world")
        macro = args.get("macro")  
        micro = args.get("micro")
        
        if world and hasattr(gs, 'world_id') and gs.world_id != world:
            return False
        
        if macro and hasattr(gs, 'current_macro') and gs.current_macro != macro:
            return False
            
        if micro and hasattr(gs, 'current_micro') and gs.current_micro != micro:
            return False
            
        return True
    
    elif op == "stat_gte":
        stat_name = args.get("name")
        min_value = args.get("value", 0)
        
        # Check new stats system first
        if hasattr(gs, 'player_stats') and gs.player_stats:
            current_value = gs.player_stats.get(stat_name, 0)
            return current_value >= min_value
        
        # Fallback to flags-based stats
        current_value = gs.flags.get(stat_name, 0)
        return current_value >= min_value
    
    elif op == "relation_gte":
        npc = args.get("npc")
        field = args.get("field", "affinity")  # default relationship field
        min_value = args.get("value", 0)
        
        # Check relationships system
        if hasattr(gs, 'relationships') and gs.relationships:
            relation_key = f"{npc}.{field}" if field != "affinity" else npc
            current_value = gs.relationships.get(relation_key, 0)
            return current_value >= min_value
        
        return False
    
    elif op == "time_between":
        start_time = args.get("start")  # format: "HH:MM"
        end_time = args.get("end")      # format: "HH:MM"
        
        if not hasattr(gs, 'time_minutes'):
            return False
        
        # Convert time strings to minutes from midnight
        def time_to_minutes(time_str: str) -> int:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        
        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)
        current_minutes = gs.time_minutes % (24 * 60)  # current time in day
        
        if start_minutes <= end_minutes:
            # Normal range (e.g., 09:00 to 17:00)
            return start_minutes <= current_minutes <= end_minutes
        else:
            # Overnight range (e.g., 22:00 to 06:00)
            return current_minutes >= start_minutes or current_minutes <= end_minutes
    
    elif op == "weather_in":
        allowed_weather = args.get("any", [])
        if not isinstance(allowed_weather, list):
            allowed_weather = [allowed_weather]
        
        current_weather = getattr(gs, 'weather', 'sereno')
        return current_weather in allowed_weather
    
    # Unknown condition type
    return False

def check_all(conditions: List[Condition], gs) -> bool:
    """Check if all conditions in a list are met.
    
    Args:
        conditions: List of conditions to evaluate
        gs: GameState object
        
    Returns:
        True if all conditions are satisfied, False otherwise
    """
    return all(check(condition, gs) for condition in conditions)