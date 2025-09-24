"""Tests for NPC system functionality."""

import pytest
from game.bootstrap import load_world_and_state
from engine.core.actions import talk, say
from engine.core.npc.models import NPC, NPCState, NPCRelation
from engine.core.npc.loader import load_npcs_from_assets, _load_npc_from_dict
from engine.core.npc.registry import NPCRegistry
from engine.core.npc.dialogue import AIDialogueEngine


@pytest.fixture
def game_setup():
    """Set up game with NPCs loaded."""
    registry, state = load_world_and_state()
    return registry, state


@pytest.fixture
def sample_npc_data():
    """Sample NPC data for testing."""
    return {
        "id": "test_npc",
        "name": "Test NPC",
        "description": "A test character",
        "current_macro": "fronte_bosco",
        "current_micro": "limite_sentiero",
        "personality": {"traits": ["friendly"]},
        "background": "Test background",
        "relationship": "stranger",
        "current_state": "neutral"
    }


class TestNPCLoader:
    """Test NPC loading functionality."""
    
    def test_load_npcs_from_assets(self):
        """Test loading NPCs from asset files."""
        npcs = load_npcs_from_assets()
        assert len(npcs) >= 2  # We have forest_guardian and wandering_merchant
        assert "forest_guardian" in npcs
        assert "wandering_merchant" in npcs
        
        guardian = npcs["forest_guardian"]
        assert guardian.name == "Guardiano del Bosco"
        assert guardian.current_macro == "fronte_bosco"
        assert guardian.current_micro == "limite_sentiero"
    
    def test_load_npc_from_dict(self, sample_npc_data):
        """Test creating NPC from dictionary."""
        npc = _load_npc_from_dict(sample_npc_data)
        assert npc.id == "test_npc"
        assert npc.name == "Test NPC"
        assert npc.relationship == NPCRelation.STRANGER
        assert npc.current_state == NPCState.NEUTRAL


class TestNPCRegistry:
    """Test NPC registry functionality."""
    
    def test_register_npc(self, sample_npc_data):
        """Test registering an NPC."""
        registry = NPCRegistry()
        npc = _load_npc_from_dict(sample_npc_data)
        
        registry.register_npc(npc)
        assert npc.id in registry.npcs
        assert len(registry.get_npcs_at_location("fronte_bosco", "limite_sentiero")) == 1
    
    def test_get_talkable_npcs(self, sample_npc_data):
        """Test getting talkable NPCs."""
        registry = NPCRegistry()
        npc = _load_npc_from_dict(sample_npc_data)
        registry.register_npc(npc)
        
        # Normal NPC should be talkable
        talkable = registry.get_talkable_npcs("fronte_bosco", "limite_sentiero")
        assert len(talkable) == 1
        
        # Sleeping NPC should not be talkable
        npc.current_state = NPCState.SLEEPING
        talkable = registry.get_talkable_npcs("fronte_bosco", "limite_sentiero")
        assert len(talkable) == 0
    
    def test_move_npc(self, sample_npc_data):
        """Test moving an NPC."""
        registry = NPCRegistry()
        npc = _load_npc_from_dict(sample_npc_data)
        registry.register_npc(npc)
        
        # Move NPC
        registry.move_npc("test_npc", "fronte_bosco", "radura_muschiosa")
        
        # Check old location is empty
        old_npcs = registry.get_npcs_at_location("fronte_bosco", "limite_sentiero")
        assert len(old_npcs) == 0
        
        # Check new location has NPC
        new_npcs = registry.get_npcs_at_location("fronte_bosco", "radura_muschiosa")
        assert len(new_npcs) == 1
        assert new_npcs[0].id == "test_npc"


class TestDialogueEngine:
    """Test AI dialogue engine."""
    
    def test_generate_response(self, sample_npc_data):
        """Test dialogue response generation."""
        engine = AIDialogueEngine()
        npc = _load_npc_from_dict(sample_npc_data)
        
        from engine.core.npc.models import DialogueContext
        context = DialogueContext(
            npc_id=npc.id,
            player_name="Player",
            current_location="fronte_bosco:limite_sentiero",
            game_time="360",
            weather="sereno",
            recent_events=[],
            relationship_status=npc.relationship,
            npc_mood=npc.mood,
            conversation_history=[]
        )
        
        # Test greeting
        response = engine.generate_response(npc, "ciao", context)
        assert len(response) > 0
        assert isinstance(response, str)
        
        # Test goodbye
        response = engine.generate_response(npc, "arrivederci", context)
        assert len(response) > 0
    
    def test_conversation_flow(self, sample_npc_data):
        """Test full conversation flow."""
        engine = AIDialogueEngine()
        npc = _load_npc_from_dict(sample_npc_data)
        
        from engine.core.npc.models import DialogueContext
        context = DialogueContext(
            npc_id=npc.id,
            player_name="Player", 
            current_location="fronte_bosco:limite_sentiero",
            game_time="360",
            weather="sereno",
            recent_events=[],
            relationship_status=npc.relationship,
            npc_mood=npc.mood,
            conversation_history=[]
        )
        
        # Start conversation
        result = engine.start_conversation(npc, context)
        assert "lines" in result
        assert len(result["lines"]) > 0
        assert result["conversation_active"] == True
        
        # Continue conversation
        result = engine.process_dialogue_turn(npc, "Come stai?", context)
        assert "lines" in result
        assert len(result["lines"]) > 0
        
        # End conversation
        result = engine.process_dialogue_turn(npc, "arrivederci", context)
        assert "lines" in result
        assert result["conversation_active"] == False


class TestNPCActions:
    """Test NPC-related game actions."""
    
    def test_talk_action_list_npcs(self, game_setup):
        """Test talk action listing NPCs."""
        registry, state = game_setup
        
        result = talk(state, registry)
        assert "lines" in result
        assert any("Persone presenti:" in line for line in result["lines"])
        assert any("Guardiano del Bosco" in line for line in result["lines"])
    
    def test_talk_action_specific_npc(self, game_setup):
        """Test talking to specific NPC."""
        registry, state = game_setup
        
        result = talk(state, registry, "Guardiano del Bosco")
        assert "lines" in result
        assert len(result["lines"]) > 0
        assert any("Guardiano del Bosco:" in line for line in result["lines"])
        
        # Check conversation state is set
        assert hasattr(state, "active_conversation")
        assert state.active_conversation is not None
        assert state.active_conversation["npc_id"] == "forest_guardian"
    
    def test_say_action(self, game_setup):
        """Test say action during conversation."""
        registry, state = game_setup
        
        # Start conversation first
        talk(state, registry, "Guardiano del Bosco")
        
        # Test saying something
        result = say(state, registry, "Ciao, come stai?")
        assert "lines" in result
        assert len(result["lines"]) > 0
        assert any("Guardiano del Bosco:" in line for line in result["lines"])
    
    def test_say_without_conversation(self, game_setup):
        """Test say action without active conversation."""
        registry, state = game_setup
        
        result = say(state, registry, "Ciao")
        assert "lines" in result
        assert any("Non stai parlando" in line for line in result["lines"])
    
    def test_talk_invalid_npc(self, game_setup):
        """Test talking to non-existent NPC."""
        registry, state = game_setup
        
        result = talk(state, registry, "NonExistentNPC")
        assert "lines" in result
        assert any("Non riesco a trovare" in line for line in result["lines"])
    
    def test_conversation_ending(self, game_setup):
        """Test conversation ending."""
        registry, state = game_setup
        
        # Start conversation
        talk(state, registry, "Guardiano del Bosco")
        assert state.active_conversation is not None
        
        # End conversation
        result = say(state, registry, "arrivederci")
        
        # Check conversation ended
        assert state.active_conversation is None
        assert any("Guardiano del Bosco:" in line for line in result["lines"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])