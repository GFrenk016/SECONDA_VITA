"""Quest engine data models for SECONDA VITA.

This module defines the core data structures for the quest system including
Quest, Step, Condition, and Reward dataclasses.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal

# Quest states for the FSM
QuestState = Literal["NOT_STARTED", "AVAILABLE", "IN_PROGRESS", "BLOCKED", "COMPLETED", "FAILED", "ABANDONED"]

@dataclass
class Condition:
    """A declarative condition for the DSL system.
    
    Examples:
        {"op": "has_item", "args": {"id": "bandage", "qty": 1}}
        {"op": "flag_is", "args": {"key": "promise_pinky", "value": True}}
    """
    op: str
    args: Dict[str, Any]

@dataclass
class Step:
    """A single step within a quest."""
    id: str
    title: str
    description: str
    enter_conditions: List[Condition] = field(default_factory=list)  # conditions to unlock step
    complete_conditions: List[Condition] = field(default_factory=list)  # conditions to complete step
    on_enter_flags: Dict[str, Any] = field(default_factory=dict)  # flags to set when entering step
    on_complete_flags: Dict[str, Any] = field(default_factory=dict)  # flags to set when completing step

@dataclass 
class Reward:
    """Rewards that can be granted upon quest/step completion."""
    items: List[Dict[str, Any]] = field(default_factory=list)  # [{"id": "medkit", "qty": 1}]
    stats: Dict[str, int] = field(default_factory=dict)  # {"morale": +10}
    relation: Dict[str, int] = field(default_factory=dict)  # {"clementine.affinity": +5}
    flags: Dict[str, Any] = field(default_factory=dict)  # general flags to set

@dataclass
class Quest:
    """A quest with multiple steps and complex state management."""
    id: str
    title: str
    act: Optional[str] = None  # for main story organization
    priority: Literal["main", "side"] = "main"
    state: QuestState = "NOT_STARTED"
    steps: List[Step] = field(default_factory=list)
    current_step_index: int = 0
    prerequisites: List[Condition] = field(default_factory=list)  # conditions to start quest
    fail_conditions: List[Condition] = field(default_factory=list)  # conditions that cause failure
    rewards_on_complete: Reward = field(default_factory=Reward)
    rewards_on_fail: Reward = field(default_factory=Reward)
    journal_nodes: Dict[str, str] = field(default_factory=dict)  # node_id -> text for branched journal
    
    def get_current_step(self) -> Optional[Step]:
        """Get the currently active step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None