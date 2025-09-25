"""Ambient events system for environmental storytelling and atmosphere.

Handles time-based events, environmental changes, and atmospheric effects
that enhance immersion and narrative depth.
"""
from __future__ import annotations
import json
import random
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .state import GameState
from .registry import ContentRegistry

@dataclass
class AmbientEvent:
    """Represents an ambient event with conditions and effects."""
    id: str
    name: str
    description: str
    messages: List[str]
    conditions: List[Dict[str, Any]]
    frequency: int  # Minutes between possible triggers
    chance: float  # 0.0 to 1.0
    effects: List[Dict[str, Any]] = None
    conditional_messages: Dict[str, List[str]] = None
    last_triggered: int = -1000  # Last trigger time in total minutes
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = []
        if self.conditional_messages is None:
            self.conditional_messages = {}

@dataclass
class TimeEvent:
    """Represents a time-specific event."""
    id: str
    name: str
    description: str
    trigger_time: Optional[str] = None  # "HH:MM" format
    frequency: Optional[int] = None  # Minutes interval
    conditions: List[Dict[str, Any]] = None
    messages: List[str] = None
    effects: List[Dict[str, Any]] = None
    last_triggered_day: int = -1
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = []
        if self.messages is None:
            self.messages = []
        if self.effects is None:
            self.effects = []

class AmbientEventSystem:
    """Manages ambient events and environmental storytelling."""
    
    def __init__(self):
        self.ambient_events: Dict[str, AmbientEvent] = {}
        self.time_events: Dict[str, TimeEvent] = {}
        self.last_ambient_check: int = 0
        
    def load_ambient_events(self, filepath: str = "assets/ambient_events.json"):
        """Load ambient events from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load ambient events
            for event_data in data.get("ambient_events", []):
                event = AmbientEvent(
                    id=event_data["id"],
                    name=event_data["name"],
                    description=event_data["description"],
                    messages=event_data["messages"],
                    conditions=event_data["conditions"],
                    frequency=event_data["frequency"],
                    chance=event_data["chance"],
                    effects=event_data.get("effects", []),
                    conditional_messages=event_data.get("conditional_messages", {})
                )
                self.ambient_events[event.id] = event
            
            # Load time events
            for event_data in data.get("time_events", []):
                event = TimeEvent(
                    id=event_data["id"],
                    name=event_data["name"],
                    description=event_data["description"],
                    trigger_time=event_data.get("trigger_time"),
                    frequency=event_data.get("frequency"),
                    conditions=event_data.get("conditions", []),
                    messages=event_data.get("messages", []),
                    effects=event_data.get("effects", [])
                )
                self.time_events[event.id] = event
                
        except Exception as e:
            print(f"Warning: Failed to load ambient events: {e}")
    
    def check_event_condition(self, condition: Dict[str, Any], state: GameState) -> bool:
        """Check if an ambient event condition is met."""
        cond_type = condition["type"]
        key = condition["key"]
        value = condition.get("value")
        negate = condition.get("negate", False)
        
        result = False
        
        if cond_type == "location":
            result = (state.location_key() == key)
        elif cond_type == "location_contains":
            result = key in state.location_key()
        elif cond_type == "daytime":
            result = (state.daytime == key)
        elif cond_type == "weather":
            result = (state.weather == key)
        elif cond_type == "flag":
            result = bool(state.flags.get(key, False))
        elif cond_type == "day_count":
            if value is not None:
                result = (state.day_count >= value)
            else:
                result = (state.day_count > 0)
        elif cond_type == "time_range":
            # Format: "HH:MM-HH:MM"
            start_time, end_time = key.split("-")
            current_minutes = state.time_minutes
            start_minutes = self._time_to_minutes(start_time)
            end_minutes = self._time_to_minutes(end_time)
            
            if start_minutes <= end_minutes:
                result = start_minutes <= current_minutes <= end_minutes
            else:  # Spans midnight
                result = current_minutes >= start_minutes or current_minutes <= end_minutes
        
        return result if not negate else not result
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM to minutes since midnight."""
        hours, minutes = map(int, time_str.split(":"))
        return hours * 60 + minutes
    
    def can_trigger_ambient_event(self, event: AmbientEvent, state: GameState) -> bool:
        """Check if an ambient event can trigger."""
        current_total_minutes = state.day_count * 24 * 60 + state.time_minutes
        
        # Check frequency cooldown
        if current_total_minutes - event.last_triggered < event.frequency:
            return False
        
        # Check random chance
        if random.random() > event.chance:
            return False
        
        # Check all conditions
        for condition in event.conditions:
            if not self.check_event_condition(condition, state):
                return False
        
        return True
    
    def get_ambient_message(self, event: AmbientEvent, state: GameState) -> str:
        """Get an appropriate message for an ambient event."""
        # Check for conditional messages based on flags
        for flag, messages in event.conditional_messages.items():
            if state.flags.get(flag, False):
                return random.choice(messages)
        
        # Use default messages
        return random.choice(event.messages)
    
    def trigger_ambient_event(self, event: AmbientEvent, state: GameState) -> List[str]:
        """Trigger an ambient event and return messages."""
        messages = []
        
        # Get event message
        message = self.get_ambient_message(event, state)
        messages.append(message)
        
        # Apply effects
        for effect in event.effects:
            effect_messages = self.apply_ambient_effect(effect, state)
            messages.extend(effect_messages)
        
        # Update last triggered time
        current_total_minutes = state.day_count * 24 * 60 + state.time_minutes
        event.last_triggered = current_total_minutes
        
        return messages
    
    def apply_ambient_effect(self, effect: Dict[str, Any], state: GameState) -> List[str]:
        """Apply an ambient event effect."""
        messages = []
        effect_type = effect["type"]
        
        if effect_type == "set_flag":
            state.flags[effect["key"]] = effect["value"]
        
        elif effect_type == "weather_hint":
            # Set a flag indicating weather might change
            state.flags[f"weather_hint_{effect['target']}"] = True
        
        elif effect_type == "trigger_memory_check":
            # This would trigger the memory system
            state.flags["memory_check_pending"] = True
        
        elif effect_type == "show_message":
            messages.append(effect["text"])
        
        elif effect_type == "check_ambient_events":
            # This creates a recursive check - be careful with this
            pass
        
        return messages
    
    def check_time_events(self, state: GameState) -> List[str]:
        """Check and trigger time-based events."""
        messages = []
        
        for event in self.time_events.values():
            should_trigger = False
            
            if event.trigger_time:
                # Specific time trigger (e.g., "06:00")
                trigger_minutes = self._time_to_minutes(event.trigger_time)
                if (state.time_minutes == trigger_minutes and 
                    event.last_triggered_day != state.day_count):
                    should_trigger = True
                    event.last_triggered_day = state.day_count
            
            elif event.frequency:
                # Frequency-based trigger
                current_total_minutes = state.day_count * 24 * 60 + state.time_minutes
                if current_total_minutes % event.frequency == 0:
                    should_trigger = True
            
            if should_trigger:
                # Check conditions
                conditions_met = True
                for condition in event.conditions:
                    if not self.check_event_condition(condition, state):
                        conditions_met = False
                        break
                
                if conditions_met:
                    # Trigger the event
                    if event.messages:
                        messages.extend(event.messages)
                    
                    # Apply effects
                    for effect in event.effects:
                        effect_messages = self.apply_ambient_effect(effect, state)
                        messages.extend(effect_messages)
        
        return messages
    
    def check_ambient_events(self, state: GameState) -> List[str]:
        """Check all ambient events and return triggered messages."""
        messages = []
        current_total_minutes = state.day_count * 24 * 60 + state.time_minutes
        
        # Rate limiting - don't check too frequently
        if current_total_minutes - self.last_ambient_check < 5:  # Check at most every 5 game minutes
            return messages
        
        self.last_ambient_check = current_total_minutes
        
        # Check ambient events
        for event in self.ambient_events.values():
            if self.can_trigger_ambient_event(event, state):
                event_messages = self.trigger_ambient_event(event, state)
                messages.extend(event_messages)
                # Only trigger one ambient event per check to avoid spam
                break
        
        # Check time events
        time_messages = self.check_time_events(state)
        messages.extend(time_messages)
        
        return messages

# Global ambient event system
ambient_system = AmbientEventSystem()

def load_ambient_events():
    """Load ambient events from the default file."""
    ambient_system.load_ambient_events()

def check_ambient_events(state: GameState) -> List[str]:
    """Check for ambient events to trigger."""
    return ambient_system.check_ambient_events(state)