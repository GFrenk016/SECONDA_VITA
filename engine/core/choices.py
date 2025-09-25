"""Narrative branching system with flag-based decision making.

Handles player choices and their consequences, managing flags and future narrative permissions.
Provides structured choice functions for key narrative moments.
"""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .state import GameState
from .registry import ContentRegistry

class ChoiceType(Enum):
    """Types of narrative choices."""
    DIALOGUE = "dialogue"
    ACTION = "action"
    MORAL = "moral"
    STRATEGIC = "strategic"

@dataclass
class ChoiceOption:
    """Represents a single choice option."""
    id: str
    text: str
    description: str = ""
    requirements: List[str] = None  # Required flags
    forbidden: List[str] = None     # Forbidden flags (choice unavailable if any present)
    consequences: Dict[str, Any] = None  # Effects of choosing this option
    
    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.forbidden is None:
            self.forbidden = []
        if self.consequences is None:
            self.consequences = {}

@dataclass
class Choice:
    """Represents a complete choice scenario."""
    id: str
    title: str
    description: str
    choice_type: ChoiceType
    options: List[ChoiceOption]
    repeatable: bool = False
    timeout_minutes: Optional[int] = None
    default_option: Optional[str] = None

class ChoiceSystem:
    """Manages narrative choices and their consequences."""
    
    def __init__(self):
        self.active_choice: Optional[Choice] = None
        self.choice_history: List[Dict[str, Any]] = []
        self.registered_choices: Dict[str, Choice] = {}
        
        # Register built-in choices
        self._register_default_choices()
    
    def _register_default_choices(self):
        """Register built-in narrative choices."""
        
        # Choice: Approach to investigating the stone marker
        stone_marker_choice = Choice(
            id="investigate_stone_marker",
            title="Approccio al Cippo",
            description="Come vuoi approcciare l'antico cippo di pietra?",
            choice_type=ChoiceType.ACTION,
            options=[
                ChoiceOption(
                    id="careful_study",
                    text="Studio attento",
                    description="Esamini con cautela ogni simbolo e dettaglio",
                    consequences={
                        "flags": {"careful_investigator": True, "hasty_explorer": False},
                        "skills": {"observation": 1},
                        "memory": "Hai scelto di investigare con pazienza e attenzione"
                    }
                ),
                ChoiceOption(
                    id="bold_touch",
                    text="Tocca i simboli",
                    description="Tocchi direttamente i simboli antichi per sentirne la texture",
                    consequences={
                        "flags": {"bold_explorer": True, "touched_ancient_stone": True},
                        "skills": {"intuition": 1},
                        "memory": "Hai scelto l'approccio diretto, toccando i simboli antichi"
                    }
                ),
                ChoiceOption(
                    id="respectful_distance",
                    text="Osserva a distanza",
                    description="Mantieni una distanza rispettosa dall'antico manufatto",
                    consequences={
                        "flags": {"respectful_explorer": True, "spiritual_awareness": True},
                        "skills": {"wisdom": 1},
                        "memory": "Hai scelto di rispettare l'antichità del cippo"
                    }
                )
            ]
        )
        self.registered_choices["investigate_stone_marker"] = stone_marker_choice
        
        # Choice: First encounter with forest whispers
        whisper_choice = Choice(
            id="respond_to_whisper",
            title="Risposta al Sussurro",
            description="Hai sentito un misterioso sussurro dalle profondità del bosco. Come rispondi?",
            choice_type=ChoiceType.MORAL,
            options=[
                ChoiceOption(
                    id="answer_whisper",
                    text="Rispondi al richiamo",
                    description="Sussurri una risposta verso il buio del bosco",
                    consequences={
                        "flags": {"answered_forest_call": True, "forest_connection": True},
                        "relationship": {"forest_spirit": 1},
                        "memory": "Hai scelto di rispondere al richiamo misterioso del bosco"
                    }
                ),
                ChoiceOption(
                    id="ignore_whisper",
                    text="Ignora il sussurro",
                    description="Fingi di non aver sentito nulla e prosegui",
                    consequences={
                        "flags": {"ignored_forest_call": True, "skeptical_mind": True},
                        "memory": "Hai scelto di ignorare i sussurri del bosco"
                    }
                ),
                ChoiceOption(
                    id="investigate_source",
                    text="Cerca la fonte",
                    description="Ti dirigi cautamente verso l'origine del sussurro",
                    requirements=["bold_explorer"],
                    consequences={
                        "flags": {"investigated_whisper": True, "deeper_mystery": True},
                        "memory": "Hai scelto di investigare attivamente il mistero",
                        "location_hint": "Un sentiero nascosto si rivela"
                    }
                )
            ]
        )
        self.registered_choices["respond_to_whisper"] = whisper_choice
        
        # Choice: NPC interaction approach
        npc_approach_choice = Choice(
            id="npc_interaction_style",
            title="Approccio Sociale",
            description="Come preferisci interagire con gli abitanti del bosco?",
            choice_type=ChoiceType.DIALOGUE,
            options=[
                ChoiceOption(
                    id="friendly_open",
                    text="Amichevole e aperto",
                    description="Mostrati disponibile e cordiale",
                    consequences={
                        "flags": {"friendly_demeanor": True},
                        "relationship_modifier": 1,
                        "memory": "Hai scelto un approccio amichevole e aperto"
                    }
                ),
                ChoiceOption(
                    id="cautious_polite",
                    text="Cauto ma educato",
                    description="Mantieni le distanze ma resta cortese",
                    consequences={
                        "flags": {"cautious_demeanor": True},
                        "memory": "Hai scelto un approccio cauto ma rispettoso"
                    }
                ),
                ChoiceOption(
                    id="direct_business",
                    text="Diretto e pragmatico",
                    description="Vai dritto al punto senza troppi preamboli",
                    consequences={
                        "flags": {"direct_communication": True},
                        "relationship_modifier": -1,
                        "memory": "Hai scelto un approccio diretto e pragmatico"
                    }
                )
            ]
        )
        self.registered_choices["npc_interaction_style"] = npc_approach_choice
    
    def can_choose_option(self, option: ChoiceOption, state: GameState) -> bool:
        """Check if a choice option is available to the player."""
        # Check requirements
        for req_flag in option.requirements:
            if not state.flags.get(req_flag, False):
                return False
        
        # Check forbidden flags
        for forbidden_flag in option.forbidden:
            if state.flags.get(forbidden_flag, False):
                return False
        
        return True
    
    def present_choice(self, choice_id: str, state: GameState) -> Dict[str, Any]:
        """Present a choice to the player."""
        choice = self.registered_choices.get(choice_id)
        if not choice:
            return {"error": f"Choice '{choice_id}' not found"}
        
        # Check if choice was already made and is not repeatable
        if not choice.repeatable:
            for past_choice in self.choice_history:
                if past_choice.get("choice_id") == choice_id:
                    return {"error": "This choice has already been made"}
        
        # Filter available options
        available_options = []
        for option in choice.options:
            if self.can_choose_option(option, state):
                available_options.append({
                    "id": option.id,
                    "text": option.text,
                    "description": option.description
                })
        
        if not available_options:
            return {"error": "No options available for this choice"}
        
        self.active_choice = choice
        
        return {
            "choice_id": choice_id,
            "title": choice.title,
            "description": choice.description,
            "type": choice.choice_type.value,
            "options": available_options
        }
    
    def make_choice(self, option_id: str, state: GameState, registry: ContentRegistry) -> Dict[str, Any]:
        """Execute a player's choice and apply consequences."""
        if not self.active_choice:
            return {"error": "No active choice to resolve"}
        
        # Find the selected option
        selected_option = None
        for option in self.active_choice.options:
            if option.id == option_id:
                selected_option = option
                break
        
        if not selected_option:
            return {"error": f"Option '{option_id}' not found"}
        
        if not self.can_choose_option(selected_option, state):
            return {"error": "This option is not available"}
        
        # Apply consequences
        messages = []
        changes = {}
        
        consequences = selected_option.consequences
        
        # Apply flag changes
        if "flags" in consequences:
            for flag, value in consequences["flags"].items():
                state.flags[flag] = value
                changes[f"flag_{flag}"] = value
        
        # Apply relationship changes
        if "relationship" in consequences:
            for npc_id, change in consequences["relationship"].items():
                current = state.relationships.get(npc_id, 0)
                state.relationships[npc_id] = current + change
                changes[f"relationship_{npc_id}"] = change
        
        # Apply relationship modifier (global modifier for future interactions)
        if "relationship_modifier" in consequences:
            state.flags["relationship_modifier"] = state.flags.get("relationship_modifier", 0) + consequences["relationship_modifier"]
        
        # Add memory
        if "memory" in consequences:
            memory_entry = {
                "type": "choice",
                "choice_id": self.active_choice.id,
                "option_id": option_id,
                "text": consequences["memory"],
                "timestamp": state.time_minutes,
                "day": state.day_count,
                "location": state.location_key()
            }
            state.timeline.append(memory_entry)
            
            # Also add to protagonist memory fragments if system exists
            if not hasattr(state, 'memory_fragments'):
                state.memory_fragments = []
            state.memory_fragments.append(memory_entry)
        
        # Add to choice history
        choice_record = {
            "choice_id": self.active_choice.id,
            "option_id": option_id,
            "timestamp": state.time_minutes,
            "day": state.day_count,
            "location": state.location_key(),
            "consequences": consequences
        }
        self.choice_history.append(choice_record)
        
        result_message = f"Hai scelto: {selected_option.text}"
        if selected_option.description:
            result_message += f" - {selected_option.description}"
        messages.append(result_message)
        
        # Clear active choice
        self.active_choice = None
        
        return {
            "lines": messages,
            "hints": [],
            "events_triggered": [f"choice_{self.active_choice.id if self.active_choice else 'unknown'}"],
            "changes": changes
        }
    
    def get_choice_history(self, state: GameState) -> List[Dict[str, Any]]:
        """Get the player's choice history."""
        return self.choice_history.copy()
    
    def trigger_choice_by_flag(self, flag_name: str, state: GameState) -> Optional[str]:
        """Check if any choices should be triggered by a flag being set."""
        # Simple mapping of flags to choices - could be expanded
        flag_to_choice = {
            "inspected_cippo": "investigate_stone_marker",
            "heard_whisper": "respond_to_whisper"
        }
        
        return flag_to_choice.get(flag_name)

# Global choice system instance
choice_system = ChoiceSystem()

def present_choice(choice_id: str, state: GameState) -> Dict[str, Any]:
    """Present a choice to the player."""
    return choice_system.present_choice(choice_id, state)

def make_choice(option_id: str, state: GameState, registry: ContentRegistry) -> Dict[str, Any]:
    """Execute a player's choice."""
    return choice_system.make_choice(option_id, state, registry)

def get_choice_history(state: GameState) -> List[Dict[str, Any]]:
    """Get player choice history."""
    return choice_system.get_choice_history(state)

def check_choice_triggers(state: GameState) -> Optional[str]:
    """Check if any choices should be automatically triggered."""
    # Check recent flags for choice triggers
    for flag_name in state.flags:
        if state.flags[flag_name]:  # Flag is set
            choice_id = choice_system.trigger_choice_by_flag(flag_name, state)
            if choice_id:
                return choice_id
    return None