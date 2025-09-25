"""Finite State Machine for quest progression.

This module handles quest state transitions and step advancement logic.
States: NOT_STARTED, AVAILABLE, IN_PROGRESS, BLOCKED, COMPLETED, FAILED, ABANDONED
"""

from .model import Quest
from .dsl import check_all, check

def can_start(quest: Quest, gs) -> bool:
    """Check if a quest can be started.
    
    Args:
        quest: Quest to check
        gs: GameState object
        
    Returns:
        True if quest can be started
    """
    if quest.state != "NOT_STARTED":
        return False
    
    # Check prerequisites
    return check_all(quest.prerequisites, gs)

def can_advance(quest: Quest, gs) -> bool:
    """Check if the current step can be advanced.
    
    Args:
        quest: Quest to check
        gs: GameState object
        
    Returns:
        True if current step is complete and quest can advance
    """
    if quest.state != "IN_PROGRESS":
        return False
    
    current_step = quest.get_current_step()
    if not current_step:
        return False
    
    # Check if current step's completion conditions are met
    return check_all(current_step.complete_conditions, gs)

def advance(quest: Quest, gs) -> None:
    """Advance quest to next step or complete it.
    
    Args:
        quest: Quest to advance
        gs: GameState object
    """
    if not can_advance(quest, gs):
        return
    
    current_step = quest.get_current_step()
    if current_step:
        # Apply on_complete flags for current step
        for flag_key, flag_value in current_step.on_complete_flags.items():
            gs.flags[flag_key] = flag_value
    
    # Move to next step
    quest.current_step_index += 1
    
    if quest.current_step_index >= len(quest.steps):
        # Quest completed
        quest.state = "COMPLETED"
        _apply_rewards(quest.rewards_on_complete, gs)
    else:
        # Check if next step can be entered
        next_step = quest.get_current_step()
        if next_step:
            if check_all(next_step.enter_conditions, gs):
                # Apply on_enter flags for next step
                for flag_key, flag_value in next_step.on_enter_flags.items():
                    gs.flags[flag_key] = flag_value
            else:
                # Step blocked by enter conditions
                quest.state = "BLOCKED"

def fail_if_needed(quest: Quest, gs) -> bool:
    """Check if quest should fail and transition to FAILED state.
    
    Args:
        quest: Quest to check
        gs: GameState object
        
    Returns:
        True if quest was failed, False otherwise
    """
    if quest.state in ["COMPLETED", "FAILED", "ABANDONED"]:
        return False
    
    # Check fail conditions
    for condition in quest.fail_conditions:
        if check(condition, gs):
            quest.state = "FAILED"
            _apply_rewards(quest.rewards_on_fail, gs)
            return True
    
    return False

def start_quest(quest: Quest, gs) -> bool:
    """Start a quest if conditions are met.
    
    Args:
        quest: Quest to start
        gs: GameState object
        
    Returns:
        True if quest was started successfully
    """
    if not can_start(quest, gs):
        return False
        
    quest.state = "IN_PROGRESS"
    quest.current_step_index = 0
    
    # Check if first step can be entered immediately
    first_step = quest.get_current_step()
    if first_step:
        if check_all(first_step.enter_conditions, gs):
            # Apply on_enter flags for first step
            for flag_key, flag_value in first_step.on_enter_flags.items():
                gs.flags[flag_key] = flag_value
        else:
            # First step blocked
            quest.state = "BLOCKED"
    
    return True

def unblock_if_possible(quest: Quest, gs) -> bool:
    """Try to unblock a blocked quest.
    
    Args:
        quest: Quest to unblock
        gs: GameState object
        
    Returns:
        True if quest was unblocked
    """
    if quest.state != "BLOCKED":
        return False
    
    current_step = quest.get_current_step()
    if not current_step:
        return False
    
    # Check if step can now be entered
    if check_all(current_step.enter_conditions, gs):
        quest.state = "IN_PROGRESS"
        # Apply on_enter flags for current step
        for flag_key, flag_value in current_step.on_enter_flags.items():
            gs.flags[flag_key] = flag_value
        return True
    
    return False

def _apply_rewards(reward, gs) -> None:
    """Apply rewards to game state.
    
    Args:
        reward: Reward object to apply
        gs: GameState object
    """
    # Apply item rewards
    for item_reward in reward.items:
        item_id = item_reward.get("id")
        qty = item_reward.get("qty", 1)
        
        if hasattr(gs, 'player_inventory') and gs.player_inventory is not None:
            current = gs.player_inventory.get(item_id, 0)
            gs.player_inventory[item_id] = current + qty
        elif hasattr(gs, 'inventory'):
            if isinstance(gs.inventory, dict):
                current = gs.inventory.get(item_id, 0)
                gs.inventory[item_id] = current + qty
    
    # Apply stat rewards
    for stat_name, stat_bonus in reward.stats.items():
        if hasattr(gs, 'player_stats') and gs.player_stats is not None:
            current = gs.player_stats.get(stat_name, 0)
            gs.player_stats[stat_name] = current + stat_bonus
        else:
            # Fallback to flags
            current = gs.flags.get(stat_name, 0)
            gs.flags[stat_name] = current + stat_bonus
    
    # Apply relationship rewards
    for relation_key, relation_bonus in reward.relation.items():
        if hasattr(gs, 'relationships') and gs.relationships is not None:
            current = gs.relationships.get(relation_key, 0)
            gs.relationships[relation_key] = current + relation_bonus
    
    # Apply flag rewards
    for flag_key, flag_value in reward.flags.items():
        gs.flags[flag_key] = flag_value