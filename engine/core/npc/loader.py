"""NPC loader - reads NPC definitions from JSON files.

Follows the same pattern as existing content loaders (weapons, mobs, etc.).
Scans assets/npcs/*.json and returns a dictionary of NPC objects.
"""

from __future__ import annotations
import json
import os
from typing import Dict, Any
from .models import NPC, NPCState, NPCRelation

# Follow existing pattern from content_loader.py
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'assets')
NPCS_DIR = os.path.join(ASSETS_DIR, 'npcs')


def _load_npc_from_dict(data: Dict[str, Any]) -> NPC:
    """Convert JSON dict to NPC object."""
    # Handle enums safely
    relationship = NPCRelation.STRANGER
    if 'relationship' in data:
        try:
            relationship = NPCRelation(data['relationship'])
        except ValueError:
            relationship = NPCRelation.STRANGER
    
    current_state = NPCState.NEUTRAL
    if 'current_state' in data:
        try:
            current_state = NPCState(data['current_state'])
        except ValueError:
            current_state = NPCState.NEUTRAL
    
    return NPC(
        id=data['id'],
        name=data['name'],
        description=data.get('description', ''),
        current_macro=data.get('current_macro', ''),
        current_micro=data.get('current_micro', ''),
        home_location=data.get('home_location', data.get('current_micro', '')),
        personality=data.get('personality', {}),
        background=data.get('background', ''),
        goals=data.get('goals', []),
        relationship=relationship,
        current_state=current_state,
        mood=float(data.get('mood', 0.0)),
        conversation_topics=data.get('conversation_topics', []),
        special_knowledge=data.get('special_knowledge', {}),
        daily_schedule=data.get('daily_schedule', {}),
        movement_pattern=data.get('movement_pattern', []),
        flags_set=data.get('flags_set', []),
        flags_required=data.get('flags_required', []),
        quest_giver=data.get('quest_giver', False),
        merchant=data.get('merchant', False),
        created_at=data.get('created_at', 0),
        last_interaction=data.get('last_interaction', 0)
    )


def _load_npcs_dir(path: str) -> Dict[str, NPC]:
    """Load all NPCs from a directory."""
    npcs: Dict[str, NPC] = {}
    if not os.path.isdir(path):
        return npcs
    
    for fname in os.listdir(path):
        if not fname.endswith('.json'):
            continue
        
        full_path = os.path.join(path, fname)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle single NPC or array of NPCs
            if isinstance(data, list):
                for npc_data in data:
                    if 'id' in npc_data:
                        npc = _load_npc_from_dict(npc_data)
                        npcs[npc.id] = npc
            elif isinstance(data, dict):
                if 'id' in data:
                    # Single NPC in file
                    npc = _load_npc_from_dict(data)
                    npcs[npc.id] = npc
                elif 'npcs' in data:
                    # NPCs in array under 'npcs' key
                    for npc_data in data['npcs']:
                        if 'id' in npc_data:
                            npc = _load_npc_from_dict(npc_data)
                            npcs[npc.id] = npc
        except Exception as e:
            # Skip malformed files but could log warning
            print(f"Warning: Failed to load NPC file {fname}: {e}")
            continue
    
    return npcs


def load_npcs_from_assets() -> Dict[str, NPC]:
    """Load all NPCs from assets/npcs/ directory."""
    return _load_npcs_dir(NPCS_DIR)


def validate_npc_references(npcs: Dict[str, NPC]) -> List[str]:
    """Validate NPC definitions and return list of issues."""
    issues = []
    
    for npc_id, npc in npcs.items():
        # Check required fields
        if not npc.name:
            issues.append(f"NPC {npc_id} has no name")
        
        if not npc.current_macro or not npc.current_micro:
            issues.append(f"NPC {npc_id} has invalid location")
        
        # Validate mood range
        if not (-1.0 <= npc.mood <= 1.0):
            issues.append(f"NPC {npc_id} has mood outside valid range (-1.0 to 1.0)")
    
    return issues