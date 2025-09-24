"""NPC system - Non-Player Characters with AI dialogue."""

from .models import NPC, NPCState, NPCRelation, NPCMemory, DialogueContext
from .loader import load_npcs_from_assets
from .dialogue import AIDialogueEngine
from .registry import NPCRegistry

__all__ = [
    'NPC', 'NPCState', 'NPCRelation', 'NPCMemory', 'DialogueContext',
    'load_npcs_from_assets', 'AIDialogueEngine', 'NPCRegistry'
]