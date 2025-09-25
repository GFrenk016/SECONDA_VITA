"""Events system for narrative triggers and environmental effects.

Handles on_enter/on_exit room events, conditional triggers, and narrative branching.
Integrates with the existing flag system and game state.
"""
from __future__ import annotations
import json
import random
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .state import GameState
from .registry import ContentRegistry

@dataclass
class EventCondition:
    """Represents a condition that must be met for an event to trigger."""
    type: str
    key: str
    value: Any = None
    negate: bool = False

@dataclass  
class EventEffect:
    """Represents an effect that occurs when an event triggers."""
    type: str
    text: str = ""
    key: str = ""
    value: Any = None

@dataclass
class Event:
    """Represents a game event with conditions and effects."""
    id: str
    type: str
    conditions: List[EventCondition]
    effects: List[EventEffect]
    chance: float = 1.0
    cooldown_minutes: int = 0
    one_time: bool = False

class EventSystem:
    """Manages and processes game events."""
    
    def __init__(self):
        self.events: Dict[str, Event] = {}
        self.room_events: Dict[str, Dict[str, List[str]]] = {}
        self.event_cooldowns: Dict[str, int] = {}  # event_id -> last_triggered_minute
        
    def load_events(self, filepath: str = "assets/events.json"):
        """Load events from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load event definitions
            for event_id, event_data in data.get("events", {}).items():
                conditions = []
                for cond_data in event_data.get("conditions", []):
                    conditions.append(EventCondition(
                        type=cond_data["type"],
                        key=cond_data["key"],
                        value=cond_data.get("value"),
                        negate=cond_data.get("negate", False)
                    ))
                
                effects = []
                for effect_data in event_data.get("effects", []):
                    effects.append(EventEffect(
                        type=effect_data["type"],
                        text=effect_data.get("text", ""),
                        key=effect_data.get("key", ""),
                        value=effect_data.get("value")
                    ))
                
                self.events[event_id] = Event(
                    id=event_id,
                    type=event_data.get("type", "narrative"),
                    conditions=conditions,
                    effects=effects,
                    chance=event_data.get("chance", 1.0),
                    cooldown_minutes=event_data.get("cooldown_minutes", 0),
                    one_time=event_data.get("one_time", False)
                )
            
            # Load room-specific event mappings
            self.room_events = data.get("room_events", {})
            
        except Exception as e:
            print(f"Warning: Failed to load events: {e}")
    
    def check_condition(self, condition: EventCondition, state: GameState, registry: ContentRegistry) -> bool:
        """Check if a condition is met."""
        result = False
        
        if condition.type == "flag":
            result = bool(state.flags.get(condition.key, False))
            if condition.value is not None:
                result = (state.flags.get(condition.key) == condition.value)
        
        elif condition.type == "location":
            result = (state.location_key() == condition.key)
        
        elif condition.type == "location_contains":
            result = condition.key in state.location_key()
        
        elif condition.type == "daytime":
            result = (state.daytime == condition.key)
        
        elif condition.type == "weather":
            result = (state.weather == condition.key)
        
        elif condition.type == "day_count":
            if condition.value is not None:
                result = (state.day_count >= condition.value)
            else:
                result = (state.day_count > 0)
        
        elif condition.type == "time_minutes":
            if condition.value is not None:
                result = (state.time_minutes >= condition.value)
        
        elif condition.type == "visited":
            result = condition.key in state.visited_micro
        
        elif condition.type == "has_item":
            # Check player inventory for item
            result = condition.key in state.inventory
        
        # Apply negation if specified
        if condition.negate:
            result = not result
            
        return result
    
    def apply_effect(self, effect: EventEffect, state: GameState, registry: ContentRegistry) -> List[str]:
        """Apply an event effect and return any messages to display."""
        messages = []
        
        if effect.type == "show_message":
            messages.append(effect.text)
        
        elif effect.type == "set_flag":
            state.flags[effect.key] = effect.value
        
        elif effect.type == "add_item":
            if effect.key not in state.inventory:
                state.inventory.append(effect.key)
                messages.append(f"Hai ottenuto: {effect.key}")
        
        elif effect.type == "remove_item":
            if effect.key in state.inventory:
                state.inventory.remove(effect.key)
                messages.append(f"Hai perso: {effect.key}")
        
        elif effect.type == "timeline_event":
            event_entry = {
                "type": "event",
                "text": effect.text,
                "timestamp": state.time_minutes,
                "day": state.day_count,
                "location": state.location_key()
            }
            state.timeline.append(event_entry)
        
        elif effect.type == "change_weather":
            state.weather = effect.key
            messages.append(f"Il tempo cambia: {effect.key}")
        
        elif effect.type == "advance_time":
            if isinstance(effect.value, int):
                state.manual_offset_minutes += effect.value
                messages.append(f"Il tempo avanza di {effect.value} minuti")
        
        return messages
    
    def can_trigger_event(self, event: Event, state: GameState) -> bool:
        """Check if an event can trigger based on cooldowns and one-time restrictions."""
        # Check if event is one-time and already fired
        if event.one_time and event.id in state.fired_events:
            return False
        
        # Check cooldown
        if event.cooldown_minutes > 0:
            last_triggered = self.event_cooldowns.get(event.id, -1)
            current_total_minutes = state.day_count * 24 * 60 + state.time_minutes
            if last_triggered >= 0 and (current_total_minutes - last_triggered) < event.cooldown_minutes:
                return False
        
        # Check random chance
        if event.chance < 1.0 and random.random() > event.chance:
            return False
        
        return True
    
    def trigger_event(self, event: Event, state: GameState, registry: ContentRegistry) -> List[str]:
        """Trigger an event and return messages to display."""
        messages = []
        
        # Check if event can trigger
        if not self.can_trigger_event(event, state):
            return messages
        
        # Check all conditions
        for condition in event.conditions:
            if not self.check_condition(condition, state, registry):
                return messages
        
        # All conditions met - trigger the event
        for effect in event.effects:
            effect_messages = self.apply_effect(effect, state, registry)
            messages.extend(effect_messages)
        
        # Mark event as fired
        state.fired_events.add(event.id)
        
        # Update cooldown
        if event.cooldown_minutes > 0:
            current_total_minutes = state.day_count * 24 * 60 + state.time_minutes
            self.event_cooldowns[event.id] = current_total_minutes
        
        return messages
    
    def process_room_events(self, location_key: str, trigger_type: str, state: GameState, registry: ContentRegistry) -> List[str]:
        """Process events for a specific room and trigger type (on_enter, on_exit)."""
        messages = []
        
        # Get events for this room and trigger type
        room_events = self.room_events.get(location_key, {})
        event_ids = room_events.get(trigger_type, [])
        
        for event_id in event_ids:
            event = self.events.get(event_id)
            if event:
                event_messages = self.trigger_event(event, state, registry)
                messages.extend(event_messages)
        
        return messages
    
    def process_ambient_events(self, state: GameState, registry: ContentRegistry) -> List[str]:
        """Process ambient events that can trigger based on current conditions."""
        messages = []
        
        # Process all ambient type events
        for event in self.events.values():
            if event.type == "ambient":
                event_messages = self.trigger_event(event, state, registry)
                messages.extend(event_messages)
        
        return messages

# Global event system instance
event_system = EventSystem()

def load_events():
    """Load events from the default events.json file."""
    event_system.load_events()

def process_events(trigger_type: str, location_key: str, state: GameState, registry: ContentRegistry) -> List[str]:
    """Process events for the given trigger type and location."""
    return event_system.process_room_events(location_key, trigger_type, state, registry)

def process_ambient_events(state: GameState, registry: ContentRegistry) -> List[str]:
    """Process ambient events based on current game state."""
    return event_system.process_ambient_events(state, registry)