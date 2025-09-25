#!/usr/bin/env python3
"""
Demonstration of the new Quest Engine for SECONDA VITA.

This demo shows how the quest engine works with:
- Loading main story quests from JSON
- Generating procedural side quests
- Processing quest progression
- Branched journal entries
- Command system integration
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from engine.core.state import GameState
from engine.quest import initialize_quest_engine, commands

def create_demo_game_state():
    """Create a demo game state for testing."""
    gs = GameState(
        world_id="house",
        current_macro="kitchen", 
        current_micro="bench"
    )
    
    # Set up demo conditions
    gs.time_minutes = 19 * 60 + 30  # 19:30 (night time)
    gs.weather = "pioggia"
    gs.daytime = "notte"
    gs.day_count = 2
    
    # Set up stats and inventory
    gs.flags = {
        "morale": 40,  # Low morale for desperate journal variants
        "tutorial_complete": True
    }
    gs.player_inventory = {
        "cloth": 2
    }
    gs.relationships = {
        "clementine": 50
    }
    
    return gs

def demo_main_story_loading():
    """Demonstrate loading main story quests."""
    print("=== DEMO: Main Story Loading ===")
    
    gs = create_demo_game_state()
    quest_engine = initialize_quest_engine(gs)
    
    # The main story should be loaded automatically
    main_quests = quest_engine.quest_log.by_priority("main")
    print(f"Loaded {len(main_quests)} main story quests:")
    
    for quest in main_quests:
        print(f"  - {quest.title} (Act: {quest.act})")
        print(f"    Steps: {len(quest.steps)}")
        if quest.journal_nodes:
            print(f"    Journal variants: {len(quest.journal_nodes)}")
    
    print()

def demo_quest_commands():
    """Demonstrate quest command system."""
    print("=== DEMO: Quest Commands ===")
    
    gs = create_demo_game_state()
    quest_engine = initialize_quest_engine(gs)
    
    # Start the main quest
    quest_engine.start_quest("Q1_FIND_BANDAGE")
    
    # Demonstrate quest listing
    result = commands.quest_list_command(quest_engine.quest_log)
    print("Command: quests")
    for line in result["lines"]:
        print(f"  {line}")
    print()
    
    # Demonstrate quest details
    result = commands.quest_detail_command(quest_engine.quest_log, "Q1_FIND_BANDAGE")
    print("Command: quest Q1_FIND_BANDAGE")
    for line in result["lines"]:
        print(f"  {line}")
    print()
    
    # Track the quest
    result = commands.quest_track_command(quest_engine.quest_log, "Q1_FIND_BANDAGE")
    print("Command: track Q1_FIND_BANDAGE")
    for line in result["lines"]:
        print(f"  {line}")
    print()

def demo_side_quest_generation():
    """Demonstrate procedural side quest generation."""
    print("=== DEMO: Side Quest Generation ===")
    
    gs = create_demo_game_state()
    quest_engine = initialize_quest_engine(gs)
    
    # Generate side quests - should get rain quest due to weather
    count = quest_engine.generate_side_quests(max_quests=2)
    print(f"Generated {count} side quests based on current conditions:")
    print(f"  Weather: {gs.weather}")
    print(f"  Time: {gs.daytime}")
    print(f"  Morale: {gs.flags['morale']}")
    print()
    
    # List all quests
    result = commands.quest_list_command(quest_engine.quest_log)
    for line in result["lines"]:
        print(f"  {line}")
    print()

def demo_quest_progression():
    """Demonstrate quest progression and journal entries."""
    print("=== DEMO: Quest Progression & Journal ===")
    
    gs = create_demo_game_state()
    quest_engine = initialize_quest_engine(gs)
    
    # Start main quest
    quest_engine.start_quest("Q1_FIND_BANDAGE")
    
    print("Initial quest state:")
    quest = quest_engine.quest_log.get_quest("Q1_FIND_BANDAGE")
    current_step = quest.get_current_step()
    print(f"  Current step: {current_step.title}")
    print(f"  Description: {current_step.description}")
    print()
    
    # Simulate being in kitchen (complete first step)
    print("Player moves to kitchen...")
    gs.current_macro = "kitchen"
    
    # Process quest tick
    messages = quest_engine.tick()
    for message in messages:
        print(f"  {message}")
    print()
    
    # Add bandage to inventory (complete second step)
    print("Player crafts a bandage...")
    gs.player_inventory["bandage"] = 1
    
    # Process quest tick again
    messages = quest_engine.tick()
    for message in messages:
        print(f"  {message}")
    print()
    
    # Show journal with branched entries
    result = commands.journal_command(quest_engine.quest_log, gs)
    print("Command: journal")
    for line in result["lines"]:
        print(f"  {line}")
    print()

def demo_quest_hints():
    """Demonstrate quest hint system."""
    print("=== DEMO: Quest Hints ===")
    
    gs = create_demo_game_state()
    quest_engine = initialize_quest_engine(gs)
    
    # Start and track main quest
    quest_engine.start_quest("Q1_FIND_BANDAGE")
    quest_engine.quest_log.track("Q1_FIND_BANDAGE")
    
    # Get hints for tracked quest
    hints = quest_engine.get_quest_hints()
    print("Hints for tracked quest:")
    for hint in hints:
        print(f"  💡 {hint}")
    print()
    
    # Simulate moving to kitchen
    gs.current_macro = "kitchen"
    quest_engine.tick()  # Advance to next step
    
    # Get new hints
    hints = quest_engine.get_quest_hints()
    print("Hints after progression:")
    for hint in hints:
        print(f"  💡 {hint}")
    print()

def demo_journal_variants():
    """Demonstrate contextual journal variants."""
    print("=== DEMO: Journal Variants ===")
    
    gs = create_demo_game_state()
    quest_engine = initialize_quest_engine(gs)
    
    # Start quest
    quest_engine.start_quest("Q1_FIND_BANDAGE")
    quest = quest_engine.quest_log.get_quest("Q1_FIND_BANDAGE")
    
    from engine.quest.journal import emit
    
    # Test different weather conditions
    print("Journal entry variants:")
    
    # Clear weather
    gs.weather = "sereno"
    text = emit(quest, "q.Q1_FIND_BANDAGE.s0.default", {}, gs)
    print(f"  Clear weather: {text}")
    
    # Rain
    gs.weather = "pioggia"
    text = emit(quest, "q.Q1_FIND_BANDAGE.s0.default", {}, gs)
    print(f"  Rain: {text}")
    
    # Night vs day for step completion
    gs.daytime = "giorno"
    text = emit(quest, "q.Q1_FIND_BANDAGE.s1.default", {}, gs)
    print(f"  Day completion: {text}")
    
    gs.daytime = "notte"
    text = emit(quest, "q.Q1_FIND_BANDAGE.s1.default", {}, gs)
    print(f"  Night completion: {text}")
    
    print()

def main():
    """Run all demos."""
    print("🎮 SECONDA VITA - Quest Engine Demo")
    print("=" * 50)
    print()
    
    try:
        demo_main_story_loading()
        demo_quest_commands()
        demo_side_quest_generation()
        demo_quest_progression()
        demo_quest_hints()
        demo_journal_variants()
        
        print("✅ All demos completed successfully!")
        print()
        print("The Quest Engine provides:")
        print("  ✓ Comprehensive FSM with 7 states")
        print("  ✓ Declarative condition DSL")
        print("  ✓ Branched journal system")
        print("  ✓ Main story loading from JSON")
        print("  ✓ Procedural side quest generation")
        print("  ✓ Full command system integration")
        print("  ✓ Hint and tracking system")
        print("  ✓ Persistence ready")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()