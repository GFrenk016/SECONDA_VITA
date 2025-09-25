#!/usr/bin/env python3
"""Demonstration of the NPC AI Adapter system.

This script shows how the new NPC AI adapter enforces JSON schema,
validates against game state, and persists memories.
"""

import json
import tempfile
from pathlib import Path
from engine.core.npc.models import NPC, NPCState, NPCRelation
from engine.core.actions import process_npc_turn
from engine.npc.memory import write_mem, retrieve, clear_memories
from engine.npc.validator import validate_schema, validate_semantics, load_whitelist


def demo_schema_validation():
    """Demonstrate JSON schema validation."""
    print("=== Schema Validation Demo ===")
    
    # Valid payload
    valid_payload = {
        "npc_id": "vicky",
        "mood": "wary",
        "intent": "greet",
        "action": None,
        "say": "Hello, stranger. I haven't seen you around here before.",
        "memory_write": [
            {
                "type": "episodic",
                "key": "first_meeting",
                "value": "Met a stranger at the forest clearing"
            }
        ],
        "relationship_delta": 0,
        "confidence": 0.7,
        "stop_speaking_after": 1
    }
    
    try:
        validate_schema(valid_payload)
        print("✅ Valid payload passed schema validation")
    except Exception as e:
        print(f"❌ Unexpected validation failure: {e}")
    
    # Invalid payload - bad mood enum
    invalid_payload = valid_payload.copy()
    invalid_payload["mood"] = "extremely_angry"  # Not in enum
    
    try:
        validate_schema(invalid_payload)
        print("❌ Invalid payload should have failed validation")
    except Exception:
        print("✅ Invalid payload correctly rejected by schema validation")
    
    print()


def demo_memory_system():
    """Demonstrate RAG memory system."""
    print("=== Memory System Demo ===")
    
    # Setup temporary memory directory
    temp_dir = Path(tempfile.mkdtemp())
    import engine.npc.memory as memory_module
    original_base = memory_module.BASE
    memory_module.BASE = temp_dir / "npc_memories"
    
    try:
        npc_id = "vicky"
        
        # Clear any existing memories
        clear_memories(npc_id)
        
        # Write some memories
        memories = [
            {
                "type": "episodic",
                "key": "met_frank_lake",
                "value": "Met Frank by the lake at dawn, he seemed tired"
            },
            {
                "type": "semantic",
                "key": "frank_trustworthy",
                "value": "Frank helped me find medical supplies when I was hurt"
            },
            {
                "type": "episodic",
                "key": "weather_observation",
                "value": "It was foggy this morning, visibility was poor"
            }
        ]
        
        write_mem(npc_id, memories)
        print(f"✅ Wrote {len(memories)} memories to file")
        
        # Retrieve memories about Frank
        frank_memories = retrieve(npc_id, ["frank"])
        print(f"✅ Retrieved {len(frank_memories)} memories about Frank:")
        for mem in frank_memories:
            print(f"   - {mem['key']}: {mem['value']}")
        
        # Retrieve memories about weather
        weather_memories = retrieve(npc_id, ["weather", "fog"])
        print(f"✅ Retrieved {len(weather_memories)} memories about weather:")
        for mem in weather_memories:
            print(f"   - {mem['key']}: {mem['value']}")
            
    finally:
        # Cleanup
        memory_module.BASE = original_base
        import shutil
        shutil.rmtree(temp_dir)
    
    print()


def demo_semantic_validation():
    """Demonstrate semantic validation against game state."""
    print("=== Semantic Validation Demo ===")
    
    # Load whitelists
    from engine.npc.llm_adapter import INTENTS, ACTIONS
    print(f"✅ Loaded {len(INTENTS)} allowed intents: {list(INTENTS)}")
    print(f"✅ Loaded {len(ACTIONS)} allowed actions: {list(ACTIONS)}")
    
    # Mock objects for validation
    class MockNPC:
        def __init__(self):
            self.id = "vicky"
            self.current_micro = "forest_clearing"
            self.inventory = ["bandage", "water"]
    
    class MockPlayer:
        def __init__(self):
            self.current_micro = "forest_clearing"
    
    npc = MockNPC()
    player = MockPlayer()
    world = None
    
    # Test valid intent/action combo
    valid_payload = {
        "intent": "greet",
        "action": "give_bandage_to_frank"
    }
    
    is_valid, error = validate_semantics(valid_payload, world, npc, player, INTENTS, ACTIONS)
    if is_valid:
        print("✅ Valid intent/action combination accepted")
    else:
        print(f"❌ Valid combination rejected: {error}")
    
    # Test invalid intent
    invalid_payload = {
        "intent": "cast_spell",  # Not in whitelist
        "action": None
    }
    
    is_valid, error = validate_semantics(invalid_payload, world, npc, player, INTENTS, ACTIONS)
    if not is_valid and error == "intent_not_allowed":
        print("✅ Invalid intent correctly rejected")
    else:
        print(f"❌ Invalid intent should have been rejected: {error}")
    
    print()


def demo_full_integration():
    """Demonstrate the full NPC turn process."""
    print("=== Full Integration Demo ===")
    
    # Create NPC
    npc = NPC(
        id="vicky",
        name="Vicky",
        description="A wary survivor who's learned to be cautious",
        current_macro="forest",
        current_micro="clearing",
        home_location="clearing",
        personality={"traits": ["wary", "protective", "pragmatic"]},
        background="Survived the early chaos by staying hidden and helping select allies",
        goals=["Stay safe", "Protect trusted friends", "Gather useful information"],
        relationship=NPCRelation.STRANGER,
        current_state=NPCState.NEUTRAL,
        mood=0.0
    )
    npc.relationships = {}
    
    # Create mock player and world
    class MockPlayer:
        def __init__(self):
            self.id = "player"
            self.name = "Frank"
            self.current_micro = "clearing"
    
    class MockWorld:
        def __init__(self):
            self.llm_backend = None  # Will trigger fallback
    
    player = MockPlayer()
    world = MockWorld()
    
    # Scene context
    scene_context = {
        "place": "forest clearing",
        "weather": "overcast",
        "player_input": "Hello, I'm looking for shelter",
        "time": "afternoon",
        "recent_events": ["player approached from east"]
    }
    
    print(f"🎬 Scene: {scene_context['place']}, {scene_context['weather']}, {scene_context['time']}")
    print(f"🗣️  Player: \"{scene_context['player_input']}\"")
    
    # Process NPC turn
    result = process_npc_turn(npc, player, world, scene_context)
    
    print(f"🤖 NPC Response Structure:")
    print(f"   - ID: {result.get('npc_id')}")
    print(f"   - Mood: {result.get('mood')}")
    print(f"   - Intent: {result.get('intent')}")
    print(f"   - Action: {result.get('action', 'None')}")
    print(f"   - Say: \"{result.get('say')}\"")
    
    if "error" in result:
        print(f"   - ⚠️  Fallback triggered due to: {result['error']}")
        print("   - 💡 In production, this would use a real LLM backend")
    else:
        print("   - ✅ Successful LLM response processing")
    
    print()


def main():
    """Run all demonstrations."""
    print("🧠 NPC AI Adapter System Demonstration")
    print("=" * 50)
    print()
    
    demo_schema_validation()
    demo_memory_system()
    demo_semantic_validation()
    demo_full_integration()
    
    print("🎉 Demo completed successfully!")
    print("\nKey Features Demonstrated:")
    print("✅ Strict JSON schema validation prevents malformed responses")
    print("✅ Semantic validation ensures actions are valid for game state")
    print("✅ RAG memory system persists and retrieves relevant context")  
    print("✅ Graceful fallback when LLM backend is unavailable")
    print("✅ Integration with existing GameState and NPC models")


if __name__ == "__main__":
    main()