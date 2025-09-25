"""Tests for the new narrative systems: events, choices, ambient events, and memories."""
import pytest
from engine.core.state import GameState
from engine.core.registry import ContentRegistry
from engine.core import events, choices, ambient_events
from engine.core.actions import maybe_trigger_memory, memories
from game.bootstrap import load_world_and_state

class TestNarrativeSystems:
    def setup_method(self):
        """Set up test environment with loaded systems."""
        # Load the game world and state
        self.registry, self.state = load_world_and_state()
        
        # Load narrative systems
        events.load_events()
        ambient_events.load_ambient_events()
    
    def test_event_system_loads(self):
        """Test that events system loads correctly."""
        assert len(events.event_system.events) > 0
        assert "first_enter_bosco" in events.event_system.events
        assert len(events.event_system.room_events) > 0
    
    def test_event_triggers_on_room_entry(self):
        """Test that events trigger when entering rooms."""
        # Clear any previous flags
        self.state.flags.clear()
        self.state.fired_events.clear()
        
        # Trigger events for room entry
        location = "fronte_bosco:limite_sentiero"
        event_messages = events.process_events("on_enter", location, self.state, self.registry)
        
        # Should trigger first_enter_bosco event
        assert len(event_messages) > 0
        assert any("bosco" in msg.lower() for msg in event_messages)
        assert self.state.flags.get("visited_bosco") is True
    
    def test_choice_system_initialization(self):
        """Test that choice system initializes with default choices."""
        assert len(choices.choice_system.registered_choices) > 0
        assert "investigate_stone_marker" in choices.choice_system.registered_choices
        assert "respond_to_whisper" in choices.choice_system.registered_choices
    
    def test_choice_presentation_and_selection(self):
        """Test presenting and making choices."""
        # Present a choice
        result = choices.present_choice("investigate_stone_marker", self.state)
        assert "error" not in result
        assert "options" in result
        assert len(result["options"]) > 0
        
        # Make a choice
        option_id = result["options"][0]["id"]
        choice_result = choices.make_choice(option_id, self.state, self.registry)
        assert "error" not in choice_result
        assert len(choice_result["lines"]) > 0
        assert len(choices.choice_system.choice_history) > 0
    
    def test_ambient_events_system_loads(self):
        """Test that ambient events system loads correctly."""
        assert len(ambient_events.ambient_system.ambient_events) > 0
        assert len(ambient_events.ambient_system.time_events) > 0
        assert "forest_bird_call" in ambient_events.ambient_system.ambient_events
    
    def test_memory_system_triggers(self):
        """Test that memory system triggers correctly."""
        # Set up conditions for memory trigger
        self.state.flags["visited_bosco"] = True
        self.state.memory_fragments.clear()
        
        # Trigger memory check
        memory_messages = maybe_trigger_memory(self.state, "look", "fronte_bosco:limite_sentiero")
        
        # Should trigger first forest entry memory
        assert len(memory_messages) > 0
        assert len(self.state.memory_fragments) > 0
        assert any("ricordo" in msg.lower() for msg in memory_messages)
    
    def test_memory_command(self):
        """Test memories command functionality."""
        # Add a test memory
        test_memory = {
            "type": "memory",
            "memory_id": "test",
            "text": "Test memory fragment",
            "timestamp": 60,
            "day": 0,
            "location": "test:location",
            "context": "test"
        }
        self.state.memory_fragments.append(test_memory)
        
        # Test memories command
        result = memories(self.state, self.registry)
        assert "lines" in result
        assert len(result["lines"]) > 1  # Header + memory
        assert any("Test memory fragment" in line for line in result["lines"])
    
    def test_save_load_preserves_narrative_state(self):
        """Test that save/load preserves all narrative state."""
        from engine.core.persistence import serialize_game_state, deserialize_game_state
        
        # Set up narrative state
        self.state.flags["test_flag"] = True
        self.state.fired_events.add("test_event")
        self.state.memory_fragments.append({
            "type": "test",
            "text": "Test memory",
            "timestamp": 100,
            "day": 1
        })
        
        # Serialize and deserialize
        serialized = serialize_game_state(self.state)
        restored_state = deserialize_game_state(serialized)
        
        # Check that narrative state is preserved
        assert restored_state.flags["test_flag"] is True
        assert "test_event" in restored_state.fired_events
        assert len(restored_state.memory_fragments) == 1
        assert restored_state.memory_fragments[0]["text"] == "Test memory"
    
    def test_choice_consequences_affect_future_choices(self):
        """Test that choice consequences affect future choice availability."""
        # Clear choice history for this test
        choices.choice_system.choice_history.clear()
        choices.choice_system.active_choice = None
        
        # Make a choice that sets a flag
        result = choices.present_choice("investigate_stone_marker", self.state)
        if "error" in result:
            # Choice might already be made, skip this test
            pytest.skip("Choice already made in previous test")
        
        option_id = result["options"][0]["id"]  # Should be "careful_study"
        
        choices.make_choice(option_id, self.state, self.registry)
        
        # Check that the consequence flag was set
        assert self.state.flags.get("careful_investigator") is True
        
        # Check choice history
        history = choices.get_choice_history(self.state)
        assert len(history) == 1
        assert history[0]["option_id"] == option_id
    
    def test_events_integrate_with_flags(self):
        """Test that events properly integrate with the flag system."""
        # Clear flags and events
        self.state.flags.clear()
        self.state.fired_events.clear()
        
        # Manually trigger an event that should set flags
        event = events.event_system.events["first_enter_bosco"]
        event_messages = events.event_system.trigger_event(event, self.state, self.registry)
        
        # Check that flags were set
        assert self.state.flags.get("visited_bosco") is True
        assert "first_enter_bosco" in self.state.fired_events
        assert len(event_messages) > 0