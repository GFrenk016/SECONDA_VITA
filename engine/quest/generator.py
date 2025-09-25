"""Procedural side quest generator from templates.

This module generates side quests from templates based on current game conditions,
using weighted random selection for variety while maintaining determinism.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from .model import Quest, Step, Condition, Reward
from .dsl import check

def generate_side_quests(
    templates_file: str, 
    gs, 
    max_quests: int = 3,
    rng_seed: Optional[int] = None
) -> List[Quest]:
    """Generate side quests from templates based on current conditions.
    
    Args:
        templates_file: Path to quest templates JSON file
        gs: GameState object for condition checking
        max_quests: Maximum number of side quests to generate
        rng_seed: Optional seed for deterministic generation
        
    Returns:
        List of generated Quest objects
    """
    templates = _load_templates(templates_file)
    if not templates:
        return []
    
    # Set up deterministic RNG
    rng = random.Random()
    if rng_seed is not None:
        rng.seed(rng_seed)
    elif hasattr(gs, 'rng_seed'):
        rng.seed(gs.rng_seed)
    
    # Filter templates by conditions
    eligible_templates = []
    for template in templates:
        if _check_template_conditions(template, gs):
            # Calculate weight based on current conditions
            weight = _calculate_template_weight(template, gs)
            if weight > 0:
                eligible_templates.append((template, weight))
    
    if not eligible_templates:
        return []
    
    # Select templates using weighted random selection
    generated_quests = []
    templates_to_use = min(max_quests, len(eligible_templates))
    
    for _ in range(templates_to_use):
        if not eligible_templates:
            break
        
        # Weighted selection
        total_weight = sum(weight for _, weight in eligible_templates)
        if total_weight <= 0:
            break
        
        selection = rng.uniform(0, total_weight)
        current_weight = 0
        
        selected_template = None
        selected_index = -1
        
        for i, (template, weight) in enumerate(eligible_templates):
            current_weight += weight
            if current_weight >= selection:
                selected_template = template
                selected_index = i
                break
        
        if selected_template:
            # Generate quest from template
            quest = _generate_quest_from_template(selected_template, gs, rng)
            if quest:
                generated_quests.append(quest)
            
            # Remove selected template to avoid duplicates
            eligible_templates.pop(selected_index)
    
    return generated_quests

def _load_templates(templates_file: str) -> List[Dict[str, Any]]:
    """Load quest templates from JSON file.
    
    Args:
        templates_file: Path to templates file
        
    Returns:
        List of template dictionaries
    """
    templates_path = Path(templates_file)
    if not templates_path.exists():
        return []
    
    try:
        with open(templates_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('templates', [])
    except (json.JSONDecodeError, IOError):
        return []

def _check_template_conditions(template: Dict[str, Any], gs) -> bool:
    """Check if template conditions are met.
    
    Args:
        template: Template dictionary
        gs: GameState object
        
    Returns:
        True if template can be used
    """
    when_conditions = template.get('when', {})
    if not when_conditions:
        return True
    
    # Convert when conditions to Condition objects and check
    for op, args in when_conditions.items():
        condition = Condition(op=op, args=args)
        if not check(condition, gs):
            return False
    
    return True

def _calculate_template_weight(template: Dict[str, Any], gs) -> float:
    """Calculate template weight based on current conditions.
    
    Args:
        template: Template dictionary
        gs: GameState object
        
    Returns:
        Weight for this template (higher = more likely)
    """
    base_weight = template.get('base_weight', 1.0)
    weights = template.get('weights', {})
    
    # Apply conditional weights
    current_weight = base_weight
    
    # Time-based weights
    daytime = getattr(gs, 'daytime', 'giorno')
    if daytime in weights:
        current_weight *= weights[daytime]
    
    # Weather-based weights
    weather = getattr(gs, 'weather', 'sereno')
    if weather in weights:
        current_weight *= weights[weather]
    
    # Location-based weights
    if hasattr(gs, 'current_macro'):
        location_key = f"location_{gs.current_macro}"
        if location_key in weights:
            current_weight *= weights[location_key]
    
    # Stat-based weights
    if hasattr(gs, 'flags'):
        morale = gs.flags.get('morale', 50)
        if morale < 30 and 'low_morale' in weights:
            current_weight *= weights['low_morale']
        elif morale > 70 and 'high_morale' in weights:
            current_weight *= weights['high_morale']
    
    return max(0, current_weight)

def _generate_quest_from_template(
    template: Dict[str, Any], 
    gs, 
    rng: random.Random
) -> Optional[Quest]:
    """Generate a quest from a template.
    
    Args:
        template: Template dictionary
        gs: GameState object
        rng: Random number generator
        
    Returns:
        Generated Quest object or None if generation failed
    """
    template_id = template.get('id', 'unknown_template')
    title = template.get('title', 'Generated Quest')
    
    # Generate unique quest ID
    quest_id = f"side_{template_id}_{rng.randint(1000, 9999)}"
    
    # Generate steps from goals
    steps = []
    goals = template.get('goals', [])
    
    for i, goal in enumerate(goals):
        step = _generate_step_from_goal(goal, i, gs, rng)
        if step:
            steps.append(step)
    
    if not steps:
        return None
    
    # Parse rewards
    rewards_data = template.get('rewards', {})
    rewards = Reward(
        items=rewards_data.get('items', []),
        stats=rewards_data.get('stats', {}),
        relation=rewards_data.get('relation', {}),
        flags=rewards_data.get('flags', {})
    )
    
    # Generate journal nodes
    journal_nodes = _generate_journal_nodes(template, quest_id, gs)
    
    return Quest(
        id=quest_id,
        title=title,
        priority="side",
        steps=steps,
        rewards_on_complete=rewards,
        journal_nodes=journal_nodes
    )

def _generate_step_from_goal(
    goal: Dict[str, Any], 
    step_index: int, 
    gs, 
    rng: random.Random
) -> Optional[Step]:
    """Generate a quest step from a goal specification.
    
    Args:
        goal: Goal dictionary
        step_index: Index of this step in the quest
        gs: GameState object
        rng: Random number generator
        
    Returns:
        Generated Step object or None if generation failed
    """
    goal_type = goal.get('type')
    
    if goal_type == 'collect':
        return _generate_collect_step(goal, step_index, gs, rng)
    elif goal_type == 'escort':
        return _generate_escort_step(goal, step_index, gs, rng)
    elif goal_type == 'reach':
        return _generate_reach_step(goal, step_index, gs, rng)
    elif goal_type == 'survive':
        return _generate_survive_step(goal, step_index, gs, rng)
    
    return None

def _generate_collect_step(
    goal: Dict[str, Any], 
    step_index: int, 
    gs, 
    rng: random.Random
) -> Step:
    """Generate a collection step."""
    item_id = goal.get('item', 'unknown_item')
    quantity = goal.get('qty', 1)
    area = goal.get('area', {})
    
    step_id = f"collect_{step_index}"
    title = f"Raccogli {item_id}"
    description = f"Trova {quantity}x {item_id}"
    
    if area:
        world = area.get('world')
        macro = area.get('macro')
        if world and macro:
            description += f" nell'area {macro}"
    
    # Completion condition: have the required items
    complete_conditions = [
        Condition(op='has_item', args={'id': item_id, 'qty': quantity})
    ]
    
    return Step(
        id=step_id,
        title=title,
        description=description,
        complete_conditions=complete_conditions
    )

def _generate_escort_step(
    goal: Dict[str, Any], 
    step_index: int, 
    gs, 
    rng: random.Random
) -> Step:
    """Generate an escort step."""
    npc_id = goal.get('npc', 'unknown_npc')
    destination = goal.get('to', {})
    
    step_id = f"escort_{step_index}"
    title = f"Scorta {npc_id}"
    description = f"Accompagna {npc_id} al sicuro"
    
    if destination:
        dest_name = destination.get('world', 'destinazione')
        description += f" verso {dest_name}"
    
    # Completion condition: reach destination with NPC
    complete_conditions = [
        Condition(op='flag_is', args={'key': f'escort_{npc_id}_complete', 'value': True})
    ]
    
    return Step(
        id=step_id,
        title=title,
        description=description,
        complete_conditions=complete_conditions
    )

def _generate_reach_step(
    goal: Dict[str, Any], 
    step_index: int, 
    gs, 
    rng: random.Random
) -> Step:
    """Generate a reach location step."""
    location = goal.get('location', {})
    
    step_id = f"reach_{step_index}"
    title = "Raggiungi il luogo"
    description = "Raggiungi la destinazione indicata"
    
    # Completion condition: be at the location
    complete_conditions = [
        Condition(op='in_location', args=location)
    ]
    
    return Step(
        id=step_id,
        title=title,
        description=description,
        complete_conditions=complete_conditions
    )

def _generate_survive_step(
    goal: Dict[str, Any], 
    step_index: int, 
    gs, 
    rng: random.Random
) -> Step:
    """Generate a survival step."""
    duration = goal.get('duration', 60)  # minutes
    
    step_id = f"survive_{step_index}"
    title = "Sopravvivi"
    description = f"Sopravvivi per {duration} minuti"
    
    # Completion condition: time-based flag
    complete_conditions = [
        Condition(op='flag_is', args={'key': f'survived_{duration}min', 'value': True})
    ]
    
    return Step(
        id=step_id,
        title=title,
        description=description,
        complete_conditions=complete_conditions
    )

def _generate_journal_nodes(
    template: Dict[str, Any], 
    quest_id: str, 
    gs
) -> Dict[str, str]:
    """Generate journal nodes for a quest from template.
    
    Args:
        template: Template dictionary
        quest_id: Generated quest ID
        gs: GameState object
        
    Returns:
        Dictionary of journal node keys to text
    """
    nodes = {}
    template_id = template.get('id', 'unknown')
    
    # Base journal entries
    nodes[f'q.{quest_id}.start.default'] = f"Una nuova opportunità si presenta: {template.get('title', 'Unknown Quest')}"
    nodes[f'q.{quest_id}.complete.default'] = "L'obiettivo è stato raggiunto. È tempo di andare avanti."
    
    # Weather variants
    current_weather = getattr(gs, 'weather', 'sereno')
    if current_weather == 'pioggia':
        nodes[f'q.{quest_id}.start.rain'] = f"La pioggia batte forte mentre considero questa nuova sfida: {template.get('title', 'Unknown Quest')}"
    
    # Time variants
    current_time = getattr(gs, 'daytime', 'giorno')
    if current_time == 'notte':
        nodes[f'q.{quest_id}.start.night'] = f"L'oscurità avvolge tutto, ma la necessità è chiara: {template.get('title', 'Unknown Quest')}"
    
    return nodes