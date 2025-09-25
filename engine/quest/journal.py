"""Branched journal system for contextual quest narratives.

This module handles the emission of journal entries with context-sensitive variants
based on weather, time, location, and other game state factors.
"""

import re
from typing import Dict, Any
from .model import Quest

def emit(quest: Quest, node_key: str, ctx: Dict[str, Any], gs) -> str:
    """Emit a journal entry with contextual variants.
    
    Args:
        quest: Quest object containing journal nodes
        node_key: Key for the journal node (e.g., "q.find_bandage.s0.start")
        ctx: Additional context for placeholder substitution
        gs: GameState object for accessing current conditions
        
    Returns:
        Formatted journal text with placeholders replaced
    """
    # Try to find the most specific variant first
    text = _get_best_variant(quest, node_key, gs)
    
    if not text:
        return f"[Missing journal entry: {node_key}]"
    
    # Replace placeholders with context
    text = _replace_placeholders(text, ctx, gs)
    
    # Add to player's journal history if available
    if hasattr(gs, 'journal_history'):
        entry = {
            'quest_id': quest.id,
            'node_key': node_key,
            'text': text,
            'timestamp': getattr(gs, 'time_minutes', 0),
            'weather': getattr(gs, 'weather', 'sereno'),
            'location': f"{getattr(gs, 'current_macro', '')}/{getattr(gs, 'current_micro', '')}"
        }
        gs.journal_history.append(entry)
    
    return text

def _get_best_variant(quest: Quest, base_key: str, gs) -> str:
    """Find the best journal variant based on current conditions.
    
    Args:
        quest: Quest containing journal nodes
        base_key: Base key to find variants for
        gs: GameState for condition checking
        
    Returns:
        Best matching journal text or empty string if not found
    """
def _get_best_variant(quest: Quest, base_key: str, gs) -> str:
    """Find the best journal variant based on current conditions.
    
    Args:
        quest: Quest containing journal nodes
        base_key: Base key to find variants for (should end with .default)
        gs: GameState for condition checking
        
    Returns:
        Best matching journal text or empty string if not found
    """
    # Remove .default suffix to get the base pattern
    if base_key.endswith('.default'):
        key_base = base_key[:-8]  # Remove '.default'
    else:
        key_base = base_key
    
    # Check for weather-specific variants first
    weather = getattr(gs, 'weather', 'sereno')
    weather_key = f"{key_base}.{weather}"
    if weather_key in quest.journal_nodes:
        return quest.journal_nodes[weather_key]
    
    # Check for rain variant (common case)
    if weather in ['pioggia', 'storm']:
        rain_key = f"{key_base}.rain"
        if rain_key in quest.journal_nodes:
            return quest.journal_nodes[rain_key]
    
    # Check for time-specific variants
    daytime = getattr(gs, 'daytime', 'giorno')
    time_key = f"{key_base}.{daytime}"
    if time_key in quest.journal_nodes:
        return quest.journal_nodes[time_key]
    
    # Check for night variant (common case)
    if daytime == 'notte':
        night_key = f"{key_base}.night"
        if night_key in quest.journal_nodes:
            return quest.journal_nodes[night_key]
    
    # Check for location-specific variants
    if hasattr(gs, 'current_micro'):
        location_key = f"{key_base}.{gs.current_micro}"
        if location_key in quest.journal_nodes:
            return quest.journal_nodes[location_key]
    
    # Check for mood/stat variants
    morale = gs.flags.get('morale', 50) if hasattr(gs, 'flags') else 50
    if morale < 30:
        low_morale_key = f"{key_base}.desperate"
        if low_morale_key in quest.journal_nodes:
            return quest.journal_nodes[low_morale_key]
    elif morale > 70:
        high_morale_key = f"{key_base}.hopeful"
        if high_morale_key in quest.journal_nodes:
            return quest.journal_nodes[high_morale_key]
    
    # Fall back to base key
    return quest.journal_nodes.get(base_key, "")

def _replace_placeholders(text: str, ctx: Dict[str, Any], gs) -> str:
    """Replace placeholders in journal text with actual values.
    
    Args:
        text: Text containing placeholders
        ctx: Context dictionary for placeholder values
        gs: GameState for accessing game data
        
    Returns:
        Text with placeholders replaced
    """
    # Replace context-specific placeholders
    for key, value in ctx.items():
        placeholder = f"{{{key}}}"
        text = text.replace(placeholder, str(value))
    
    # Replace game state placeholders
    placeholders = {
        '{time}': _format_time(getattr(gs, 'time_minutes', 0)),
        '{weather}': getattr(gs, 'weather', 'sereno'),
        '{location}': getattr(gs, 'current_micro', 'unknown'),
        '{day}': str(getattr(gs, 'day_count', 0)),
        '{morale}': str(gs.flags.get('morale', 50)) if hasattr(gs, 'flags') else '50'
    }
    
    for placeholder, value in placeholders.items():
        text = text.replace(placeholder, value)
    
    # Replace NPC name placeholders (pattern: {npc:id})
    npc_pattern = r'\{npc:(\w+)\}'
    def replace_npc(match):
        npc_id = match.group(1)
        # Default NPC names - in a full implementation this would come from NPC registry
        npc_names = {
            'clementine': 'Clementine',
            'marcus': 'Marcus',
            'sarah': 'Sarah'
        }
        return npc_names.get(npc_id, npc_id.title())
    
    text = re.sub(npc_pattern, replace_npc, text)
    
    return text

def _format_time(minutes: int) -> str:
    """Format game minutes into readable time string.
    
    Args:
        minutes: Minutes since game start
        
    Returns:
        Formatted time string (HH:MM)
    """
    # Add 6-hour offset (game starts at 06:00)
    total_minutes = (minutes + 6 * 60) % (24 * 60)
    hours = total_minutes // 60
    mins = total_minutes % 60
    return f"{hours:02d}:{mins:02d}"

def create_journal_node_key(quest_id: str, step_id: str, variant: str = "default") -> str:
    """Create a standardized journal node key.
    
    Args:
        quest_id: Quest identifier
        step_id: Step identifier  
        variant: Variant identifier (default, rain, night, etc.)
        
    Returns:
        Formatted node key
    """
    return f"q.{quest_id}.{step_id}.{variant}"

def get_recent_entries(gs, limit: int = 10) -> list:
    """Get recent journal entries from game state.
    
    Args:
        gs: GameState object
        limit: Maximum number of entries to return
        
    Returns:
        List of recent journal entries
    """
    if not hasattr(gs, 'journal_history'):
        return []
    
    # Return most recent entries
    return gs.journal_history[-limit:]