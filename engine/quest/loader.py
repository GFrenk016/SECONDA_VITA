"""Main story quest loader from structured JSON files.

This module loads main story quests from JSON configuration files,
converting them into Quest objects for the quest system.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from .model import Quest, Step, Condition, Reward

def load_main_story(story_file_path: str) -> List[Quest]:
    """Load main story quests from JSON file.
    
    Args:
        story_file_path: Path to the main story JSON file
        
    Returns:
        List of Quest objects loaded from the file
        
    Raises:
        FileNotFoundError: If story file doesn't exist
        ValueError: If JSON format is invalid
    """
    story_path = Path(story_file_path)
    if not story_path.exists():
        raise FileNotFoundError(f"Story file not found: {story_file_path}")
    
    try:
        with open(story_path, 'r', encoding='utf-8') as f:
            story_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in story file: {e}")
    
    quests = []
    acts = story_data.get('acts', [])
    
    for act in acts:
        act_id = act.get('id', 'unknown_act')
        act_title = act.get('title', 'Unknown Act')
        act_quests = act.get('quests', [])
        
        for quest_data in act_quests:
            quest = _parse_quest(quest_data, act_id)
            quests.append(quest)
    
    return quests

def _parse_quest(quest_data: Dict[str, Any], act_id: str) -> Quest:
    """Parse a single quest from JSON data.
    
    Args:
        quest_data: Quest data dictionary
        act_id: Act identifier this quest belongs to
        
    Returns:
        Parsed Quest object
    """
    quest_id = quest_data.get('id', 'unknown_quest')
    title = quest_data.get('title', 'Unknown Quest')
    priority = quest_data.get('priority', 'main')
    
    # Parse steps
    steps = []
    step_data_list = quest_data.get('steps', [])
    for step_data in step_data_list:
        step = _parse_step(step_data)
        steps.append(step)
    
    # Parse prerequisites
    prerequisites = []
    prereq_data = quest_data.get('prerequisites', [])
    for condition_data in prereq_data:
        condition = _parse_condition(condition_data)
        prerequisites.append(condition)
    
    # Parse fail conditions
    fail_conditions = []
    fail_data = quest_data.get('fail_conditions', [])
    for condition_data in fail_data:
        condition = _parse_condition(condition_data)
        fail_conditions.append(condition)
    
    # Parse rewards
    rewards_on_complete = _parse_reward(quest_data.get('rewards_on_complete', {}))
    rewards_on_fail = _parse_reward(quest_data.get('rewards_on_fail', {}))
    
    # Parse journal nodes
    journal_nodes = quest_data.get('journal_nodes', {})
    
    return Quest(
        id=quest_id,
        title=title,
        act=act_id,
        priority=priority,
        steps=steps,
        prerequisites=prerequisites,
        fail_conditions=fail_conditions,
        rewards_on_complete=rewards_on_complete,
        rewards_on_fail=rewards_on_fail,
        journal_nodes=journal_nodes
    )

def _parse_step(step_data: Dict[str, Any]) -> Step:
    """Parse a quest step from JSON data.
    
    Args:
        step_data: Step data dictionary
        
    Returns:
        Parsed Step object
    """
    step_id = step_data.get('id', 'unknown_step')
    title = step_data.get('title', 'Unknown Step')
    description = step_data.get('description', '')
    
    # Parse enter conditions
    enter_conditions = []
    enter_data = step_data.get('enter_conditions', [])
    for condition_data in enter_data:
        condition = _parse_condition(condition_data)
        enter_conditions.append(condition)
    
    # Parse complete conditions
    complete_conditions = []
    complete_data = step_data.get('complete_conditions', [])
    for condition_data in complete_data:
        condition = _parse_condition(condition_data)
        complete_conditions.append(condition)
    
    # Parse flags
    on_enter_flags = step_data.get('on_enter_flags', {})
    on_complete_flags = step_data.get('on_complete_flags', {})
    
    return Step(
        id=step_id,
        title=title,
        description=description,
        enter_conditions=enter_conditions,
        complete_conditions=complete_conditions,
        on_enter_flags=on_enter_flags,
        on_complete_flags=on_complete_flags
    )

def _parse_condition(condition_data: Dict[str, Any]) -> Condition:
    """Parse a condition from JSON data.
    
    Args:
        condition_data: Condition data dictionary
        
    Returns:
        Parsed Condition object
    """
    # Support both new format and legacy format
    if 'op' in condition_data:
        # New format: {"op": "has_item", "args": {"id": "bandage", "qty": 1}}
        return Condition(
            op=condition_data['op'],
            args=condition_data.get('args', {})
        )
    else:
        # Legacy format conversion
        condition_type = condition_data.get('type')
        
        if condition_type == 'flag':
            return Condition(
                op='flag_is',
                args={
                    'key': condition_data.get('flag'),
                    'value': condition_data.get('value', True)
                }
            )
        elif condition_type == 'item_count':
            return Condition(
                op='has_item',
                args={
                    'id': condition_data.get('item'),
                    'qty': condition_data.get('quantity', 1)
                }
            )
        elif condition_type == 'location':
            return Condition(
                op='in_location',
                args={'micro': condition_data.get('location')}
            )
        else:
            # Unknown legacy type, create as generic condition
            return Condition(
                op=condition_type or 'unknown',
                args=condition_data
            )

def _parse_reward(reward_data: Dict[str, Any]) -> Reward:
    """Parse a reward from JSON data.
    
    Args:
        reward_data: Reward data dictionary
        
    Returns:
        Parsed Reward object
    """
    items = reward_data.get('items', [])
    stats = reward_data.get('stats', {})
    relation = reward_data.get('relation', {})
    flags = reward_data.get('flags', {})
    
    return Reward(
        items=items,
        stats=stats,
        relation=relation,
        flags=flags
    )

def validate_story_structure(story_data: Dict[str, Any]) -> List[str]:
    """Validate the structure of a story JSON file.
    
    Args:
        story_data: Parsed story JSON data
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if 'acts' not in story_data:
        errors.append("Missing 'acts' key in story data")
        return errors
    
    acts = story_data['acts']
    if not isinstance(acts, list):
        errors.append("'acts' must be a list")
        return errors
    
    for i, act in enumerate(acts):
        if not isinstance(act, dict):
            errors.append(f"Act {i} must be a dictionary")
            continue
        
        if 'id' not in act:
            errors.append(f"Act {i} missing 'id' field")
        
        if 'quests' not in act:
            errors.append(f"Act {i} missing 'quests' field")
        elif not isinstance(act['quests'], list):
            errors.append(f"Act {i} 'quests' must be a list")
        else:
            for j, quest in enumerate(act['quests']):
                if not isinstance(quest, dict):
                    errors.append(f"Act {i} quest {j} must be a dictionary")
                    continue
                
                if 'id' not in quest:
                    errors.append(f"Act {i} quest {j} missing 'id' field")
                
                if 'title' not in quest:
                    errors.append(f"Act {i} quest {j} missing 'title' field")
                
                if 'steps' in quest and not isinstance(quest['steps'], list):
                    errors.append(f"Act {i} quest {j} 'steps' must be a list")
    
    return errors