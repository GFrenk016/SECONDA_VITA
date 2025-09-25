"""Simple integration test for NPC AI adapter system."""

import pytest
import tempfile
import shutil
from pathlib import Path
from engine.core.actions import process_npc_turn
from engine.core.npc.models import NPC, NPCState, NPCRelation
from engine.npc.memory import write_mem, retrieve


@pytest.fixture
def temp_memory_dir(monkeypatch):
    """Setup temporary directory for memory persistence."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Mock the memory module BASE path
    import engine.npc.memory as memory_module
    original_base = memory_module.BASE
    memory_module.BASE = temp_dir / "npc_memories"
    
    yield temp_dir
    
    # Cleanup
    memory_module.BASE = original_base
    shutil.rmtree(temp_dir)


class TestNPCIntegrationSimple:
    """Simple integration tests that work with fallback behavior."""
    
    def test_process_npc_turn_fallback(self, temp_memory_dir):
        """Test that process_npc_turn returns proper fallback when no LLM backend."""
        # Create test objects
        npc = NPC(
            id="vicky",
            name="Vicky",
            description="A wary survivor",
            current_macro="forest",
            current_micro="clearing", 
            home_location="clearing",
            personality={"traits": ["wary", "protective"]},
            background="Survivor from the early days",
            goals=["Stay safe", "Help trusted allies"],
            relationship=NPCRelation.STRANGER,
            current_state=NPCState.NEUTRAL,
            mood=0.0
        )
        npc.relationships = {}
        
        class MockPlayer:
            def __init__(self):
                self.id = "player"
                self.name = "Frank"
                self.current_micro = "clearing"
        
        class MockWorld:
            def __init__(self):
                self.llm_backend = None  # No backend - will trigger fallback
        
        player = MockPlayer()
        world = MockWorld()
        scene_context = {
            "place": "forest clearing",
            "weather": "sunny",
            "player_input": "Hello there!",
            "time": "morning"
        }
        
        # Execute NPC turn
        result = process_npc_turn(npc, player, world, scene_context)
        
        # Verify fallback response structure
        assert isinstance(result, dict)
        assert "npc_id" in result
        assert "mood" in result
        assert "intent" in result
        assert "say" in result
        assert result["npc_id"] == "vicky"
        assert result["mood"] == "neutral"
        assert result["intent"] == "evade"
        assert result["say"] == "..."
        assert "error" in result
    
    def test_memory_system_integration(self, temp_memory_dir):
        """Test that the memory system works correctly."""
        npc_id = "vicky"
        
        # Write some memories
        memories = [
            {
                "type": "episodic",
                "key": "met_frank",
                "value": "First meeting with Frank at the lake"
            },
            {
                "type": "semantic",
                "key": "frank_helpful",
                "value": "Frank seems to be helpful and trustworthy"
            }
        ]
        write_mem(npc_id, memories)
        
        # Retrieve memories
        results = retrieve(npc_id, ["frank"])
        
        # Verify retrieval works
        assert len(results) == 2
        assert any("met_frank" in r.get("key", "") for r in results)
        assert any("frank_helpful" in r.get("key", "") for r in results)
    
    def test_whitelist_loading(self):
        """Test that intent and action whitelists are loaded."""
        from engine.npc.llm_adapter import INTENTS, ACTIONS
        
        # Check that whitelists contain expected values
        assert "greet" in INTENTS
        assert "warn_player" in INTENTS
        assert "evade" in INTENTS
        
        assert "none" in ACTIONS
        assert "move_away" in ACTIONS
        assert "stay_in_cover" in ACTIONS
    
    def test_schema_validation(self):
        """Test that schema validation works."""
        from engine.npc.validator import validate_schema
        
        valid_payload = {
            "npc_id": "test",
            "mood": "neutral",
            "intent": "greet",
            "say": "Hello!",
            "memory_write": [],
            "relationship_delta": 0,
            "confidence": 0.8,
            "stop_speaking_after": 1
        }
        
        # Should not raise exception
        assert validate_schema(valid_payload) is True
        
        # Invalid payload should raise exception
        invalid_payload = {
            "npc_id": "test",
            "mood": "invalid_mood",  # Invalid enum value
            "intent": "greet",
            "say": "Hello!"
        }
        
        with pytest.raises(Exception):  # jsonschema.ValidationError
            validate_schema(invalid_payload)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])