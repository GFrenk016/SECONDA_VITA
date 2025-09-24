"""NPC data models and enums."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class NPCState(Enum):
    """NPC behavioral states."""
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    HOSTILE = "hostile"
    AFRAID = "afraid"
    BUSY = "busy"
    SLEEPING = "sleeping"


class NPCRelation(Enum):
    """Player-NPC relationship types."""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    ALLY = "ally"
    ENEMY = "enemy"
    LOVER = "lover"
    FAMILY = "family"


@dataclass
class NPCMemory:
    """Individual memory entry for an NPC."""
    event: str
    timestamp_minutes: int  # When the event occurred (in game minutes)
    context: Dict[str, Any]  # Additional context (location, mood, etc.)
    importance: int  # 1-10, affects how long it's remembered
    emotional_impact: float  # -1.0 to 1.0, negative to positive


@dataclass
class DialogueContext:
    """Context for dialogue generation."""
    npc_id: str
    player_name: str
    current_location: str
    game_time: str
    weather: str
    recent_events: List[str]
    relationship_status: NPCRelation
    npc_mood: float  # -1.0 to 1.0
    conversation_history: List[Dict[str, str]]  # Recent dialogue turns


@dataclass
class NPC:
    """Non-Player Character definition."""
    id: str
    name: str
    description: str
    
    # Location and positioning
    current_macro: str
    current_micro: str
    home_location: str  # Where they return when not busy
    
    # Core personality and background
    personality: Dict[str, Any]  # Traits, quirks, speech patterns
    background: str  # Personal history and context
    goals: List[str]  # Current objectives/motivations
    
    # Relationship and state
    relationship: NPCRelation = NPCRelation.STRANGER
    current_state: NPCState = NPCState.NEUTRAL
    mood: float = 0.0  # -1.0 (very negative) to 1.0 (very positive)
    
    # Memory and dialogue
    memories: List[NPCMemory] = field(default_factory=list)
    conversation_topics: List[str] = field(default_factory=list)
    special_knowledge: Dict[str, Any] = field(default_factory=dict)
    
    # Schedule and behavior
    daily_schedule: Dict[str, str] = field(default_factory=dict)  # time -> activity
    movement_pattern: List[str] = field(default_factory=list)  # Locations they visit
    
    # Game integration
    flags_set: List[str] = field(default_factory=list)  # Game flags this NPC can set
    flags_required: List[str] = field(default_factory=list)  # Flags required for interaction
    quest_giver: bool = False
    merchant: bool = False
    
    # Meta
    created_at: int = 0  # Game minutes when created
    last_interaction: int = 0  # Last time player talked to them
    
    def add_memory(self, event: str, timestamp: int, context: Dict[str, Any] = None, 
                   importance: int = 5, emotional_impact: float = 0.0):
        """Add a new memory for this NPC."""
        memory = NPCMemory(
            event=event,
            timestamp_minutes=timestamp,
            context=context or {},
            importance=importance,
            emotional_impact=emotional_impact
        )
        self.memories.append(memory)
        
        # Keep only the most important/recent memories (max 20)
        if len(self.memories) > 20:
            self.memories.sort(key=lambda m: (m.importance, m.timestamp_minutes), reverse=True)
            self.memories = self.memories[:20]
    
    def get_recent_memories(self, limit: int = 5) -> List[NPCMemory]:
        """Get the most recent memories."""
        return sorted(self.memories, key=lambda m: m.timestamp_minutes, reverse=True)[:limit]
    
    def adjust_mood(self, change: float):
        """Adjust NPC mood within bounds."""
        self.mood = max(-1.0, min(1.0, self.mood + change))
    
    def set_relationship(self, new_relationship: NPCRelation):
        """Change relationship status with appropriate mood adjustment."""
        if new_relationship != self.relationship:
            # Positive relationships improve mood slightly
            if new_relationship in [NPCRelation.FRIEND, NPCRelation.ALLY, NPCRelation.LOVER]:
                self.adjust_mood(0.1)
            elif new_relationship in [NPCRelation.ENEMY]:
                self.adjust_mood(-0.2)
            
            self.relationship = new_relationship