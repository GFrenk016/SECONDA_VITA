"""Test the quest engine FSM (Finite State Machine)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.quest.model import Quest, Step, Condition, Reward
from engine.quest.fsm import can_start, can_advance, advance, fail_if_needed, start_quest

class MockGameState:
    """Mock GameState for testing."""
    def __init__(self):
        self.flags = {}
        self.player_inventory = {}
        self.inventory = {}
        self.world_id = "house"
        self.current_macro = "kitchen"
        self.current_micro = "bench"
        self.player_stats = {}
        self.relationships = {}
        self.time_minutes = 0
        self.weather = "sereno"

def test_quest_start():
    """Test quest starting logic."""
    gs = MockGameState()
    
    # Create quest with prerequisites
    quest = Quest(
        id="test_quest",
        title="Test Quest",
        prerequisites=[
            Condition(op="flag_is", args={"key": "can_start", "value": True})
        ]
    )
    
    # Cannot start without prerequisites
    assert can_start(quest, gs) == False
    
    # Can start with prerequisites met
    gs.flags["can_start"] = True
    assert can_start(quest, gs) == True
    
    # Successfully start quest
    assert start_quest(quest, gs) == True
    assert quest.state == "IN_PROGRESS"
    
    # Cannot start already started quest
    assert start_quest(quest, gs) == False

def test_step_advancement():
    """Test step advancement logic."""
    gs = MockGameState()
    
    # Create quest with two steps
    step1 = Step(
        id="step1",
        title="First Step",
        description="Do something",
        complete_conditions=[
            Condition(op="flag_is", args={"key": "step1_done", "value": True})
        ],
        on_complete_flags={"step1_completed": True}
    )
    
    step2 = Step(
        id="step2", 
        title="Second Step",
        description="Do something else",
        complete_conditions=[
            Condition(op="flag_is", args={"key": "step2_done", "value": True})
        ]
    )
    
    quest = Quest(
        id="multi_step_quest",
        title="Multi-Step Quest",
        state="IN_PROGRESS",
        steps=[step1, step2],
        rewards_on_complete=Reward(stats={"morale": 10})
    )
    
    # Cannot advance without step completion
    assert can_advance(quest, gs) == False
    
    # Complete first step
    gs.flags["step1_done"] = True
    assert can_advance(quest, gs) == True
    
    # Advance to next step
    advance(quest, gs)
    assert quest.current_step_index == 1
    assert gs.flags.get("step1_completed") == True
    
    # Complete second step
    gs.flags["step2_done"] = True
    assert can_advance(quest, gs) == True
    
    # Advance completes quest
    initial_morale = gs.player_stats.get("morale", 0) if gs.player_stats else gs.flags.get("morale", 0)
    advance(quest, gs)
    assert quest.state == "COMPLETED"
    
    # Check reward was applied
    final_morale = gs.player_stats.get("morale", 0) if gs.player_stats else gs.flags.get("morale", 0)
    assert final_morale == initial_morale + 10

def test_blocked_step():
    """Test step blocking by enter conditions."""
    gs = MockGameState()
    
    step1 = Step(
        id="step1",
        title="First Step", 
        description="Easy step",
        complete_conditions=[
            Condition(op="flag_is", args={"key": "step1_done", "value": True})
        ]
    )
    
    step2 = Step(
        id="step2",
        title="Blocked Step",
        description="Needs prerequisites",
        enter_conditions=[
            Condition(op="flag_is", args={"key": "can_enter_step2", "value": True})
        ],
        complete_conditions=[
            Condition(op="flag_is", args={"key": "step2_done", "value": True})
        ]
    )
    
    quest = Quest(
        id="blocking_quest",
        title="Blocking Quest",
        state="IN_PROGRESS", 
        steps=[step1, step2]
    )
    
    # Complete first step but second step blocked
    gs.flags["step1_done"] = True
    advance(quest, gs)
    
    assert quest.state == "BLOCKED"
    assert quest.current_step_index == 1
    
    # Unblock by meeting enter conditions
    from engine.quest.fsm import unblock_if_possible
    gs.flags["can_enter_step2"] = True
    assert unblock_if_possible(quest, gs) == True
    assert quest.state == "IN_PROGRESS"

def test_quest_failure():
    """Test quest failure conditions."""
    gs = MockGameState()
    
    quest = Quest(
        id="failing_quest",
        title="Failing Quest",
        state="IN_PROGRESS",
        fail_conditions=[
            Condition(op="flag_is", args={"key": "quest_failed", "value": True})
        ],
        rewards_on_fail=Reward(stats={"morale": -5})
    )
    
    # Quest not failed initially
    assert fail_if_needed(quest, gs) == False
    assert quest.state == "IN_PROGRESS"
    
    # Trigger failure condition
    gs.player_stats = None  # Force fallback to flags
    initial_morale = gs.flags.get("morale", 0)
    gs.flags["quest_failed"] = True
    assert fail_if_needed(quest, gs) == True
    assert quest.state == "FAILED"
    
    # Check failure reward applied
    final_morale = gs.flags.get("morale", 0)
    assert final_morale == initial_morale - 5

def test_step_enter_flags():
    """Test step on_enter flags are applied."""
    gs = MockGameState()
    
    step1 = Step(
        id="step1",
        title="First Step",
        description="Sets flags on enter",
        enter_conditions=[],
        on_enter_flags={"entered_step1": True, "tutorial_shown": True},
        complete_conditions=[
            Condition(op="flag_is", args={"key": "step1_done", "value": True})
        ]
    )
    
    quest = Quest(
        id="flag_test_quest",
        title="Flag Test Quest", 
        steps=[step1]
    )
    
    # Start quest
    start_quest(quest, gs)
    
    # Check enter flags were applied
    assert gs.flags.get("entered_step1") == True
    assert gs.flags.get("tutorial_shown") == True

def test_reward_application():
    """Test different types of rewards are applied correctly."""
    gs = MockGameState()
    gs.player_inventory = {}
    gs.player_stats = {"health": 50}
    gs.relationships = {"npc1": 10}
    
    rewards = Reward(
        items=[{"id": "bandage", "qty": 2}],
        stats={"health": 25, "morale": 10},
        relation={"npc1": 5, "npc2.trust": 3},
        flags={"reward_received": True}
    )
    
    from engine.quest.fsm import _apply_rewards
    _apply_rewards(rewards, gs)
    
    # Check items added
    assert gs.player_inventory.get("bandage") == 2
    
    # Check stats updated
    assert gs.player_stats.get("health") == 75
    assert gs.player_stats.get("morale") == 10
    
    # Check relationships updated
    assert gs.relationships.get("npc1") == 15
    assert gs.relationships.get("npc2.trust") == 3
    
    # Check flags set
    assert gs.flags.get("reward_received") == True

if __name__ == "__main__":
    test_quest_start()
    test_step_advancement()
    test_blocked_step()
    test_quest_failure()
    test_step_enter_flags()
    test_reward_application()
    print("All FSM tests passed!")