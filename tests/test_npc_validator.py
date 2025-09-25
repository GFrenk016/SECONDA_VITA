"""Tests for NPC AI response validation system."""

import pytest
import json
from engine.npc.validator import validate_schema, validate_semantics, load_whitelist
from engine.npc.schema import NPC_RESPONSE_SCHEMA


@pytest.fixture
def sample_payload():
    """Valid NPC response payload for testing."""
    return {
        "npc_id": "test_npc",
        "mood": "neutral",
        "intent": "greet",
        "action": None,
        "say": "Hello there!",
        "memory_write": [
            {
                "type": "episodic",
                "key": "met_player",
                "value": "First meeting with player at forest entrance"
            }
        ],
        "relationship_delta": 1,
        "directives": [],
        "confidence": 0.8,
        "stop_speaking_after": 1
    }


@pytest.fixture
def mock_objects():
    """Mock NPC, player, and world objects."""
    class MockNPC:
        def __init__(self):
            self.id = "test_npc"
            self.name = "Test NPC"
            self.current_micro = "forest_entrance"
            self.inventory = ["bandage", "stick"]
    
    class MockPlayer:
        def __init__(self):
            self.id = "player"
            self.name = "Player"
            self.current_micro = "forest_entrance"
    
    class MockWorld:
        pass
    
    return MockNPC(), MockPlayer(), MockWorld()


class TestSchemaValidation:
    """Test JSON schema validation."""
    
    def test_valid_schema(self, sample_payload):
        """Test that valid payload passes schema validation."""
        assert validate_schema(sample_payload) is True
    
    def test_missing_required_field(self, sample_payload):
        """Test that missing required fields fail validation."""
        del sample_payload["npc_id"]
        
        with pytest.raises(Exception):  # jsonschema.ValidationError
            validate_schema(sample_payload)
    
    def test_invalid_mood_enum(self, sample_payload):
        """Test that invalid mood values fail validation."""
        sample_payload["mood"] = "invalid_mood"
        
        with pytest.raises(Exception):  # jsonschema.ValidationError
            validate_schema(sample_payload)
    
    def test_say_too_long(self, sample_payload):
        """Test that 'say' field longer than 160 chars fails."""
        sample_payload["say"] = "x" * 161
        
        with pytest.raises(Exception):  # jsonschema.ValidationError
            validate_schema(sample_payload)
    
    def test_invalid_memory_structure(self, sample_payload):
        """Test that invalid memory structure fails validation."""
        sample_payload["memory_write"] = [
            {"invalid": "structure"}
        ]
        
        with pytest.raises(Exception):  # jsonschema.ValidationError
            validate_schema(sample_payload)
    
    def test_relationship_delta_out_of_range(self, sample_payload):
        """Test that relationship_delta outside -2,+2 range fails."""
        sample_payload["relationship_delta"] = 5
        
        with pytest.raises(Exception):  # jsonschema.ValidationError
            validate_schema(sample_payload)


class TestSemanticValidation:
    """Test semantic validation against game state."""
    
    def test_valid_semantics(self, sample_payload, mock_objects):
        """Test that valid semantics pass validation."""
        npc, player, world = mock_objects
        intents = {"greet", "warn_player"}
        actions = {"none", "give_bandage_to_frank"}
        
        is_valid, error = validate_semantics(sample_payload, world, npc, player, intents, actions)
        assert is_valid is True
        assert error is None
    
    def test_intent_not_allowed(self, sample_payload, mock_objects):
        """Test that disallowed intent fails validation."""
        npc, player, world = mock_objects
        sample_payload["intent"] = "mind_read"
        intents = {"greet", "warn_player"}
        actions = {"none"}
        
        is_valid, error = validate_semantics(sample_payload, world, npc, player, intents, actions)
        assert is_valid is False
        assert error == "intent_not_allowed"
    
    def test_action_not_allowed(self, sample_payload, mock_objects):
        """Test that disallowed action fails validation."""
        npc, player, world = mock_objects
        sample_payload["action"] = "forbidden_action"
        intents = {"greet"}
        actions = {"none", "give_bandage_to_frank"}
        
        is_valid, error = validate_semantics(sample_payload, world, npc, player, intents, actions)
        assert is_valid is False
        assert error == "action_not_allowed"
    
    def test_action_missing_item(self, sample_payload, mock_objects):
        """Test that action requiring unavailable item fails."""
        npc, player, world = mock_objects
        npc.inventory = ["stick"]  # No bandage
        sample_payload["action"] = "give_bandage_to_frank"
        intents = {"greet"}
        actions = {"none", "give_bandage_to_frank"}
        
        is_valid, error = validate_semantics(sample_payload, world, npc, player, intents, actions)
        assert is_valid is False
        assert error == "action_missing_item"
    
    def test_action_too_far(self, sample_payload, mock_objects):
        """Test that melee action when too far fails."""
        npc, player, world = mock_objects
        player.current_micro = "different_location"
        sample_payload["intent"] = "threaten"  # Valid intent
        sample_payload["action"] = "attack_melee"
        intents = {"threaten"}
        actions = {"attack_melee"}
        
        is_valid, error = validate_semantics(sample_payload, world, npc, player, intents, actions)
        assert is_valid is False
        assert error == "action_too_far"


class TestWhitelistLoading:
    """Test whitelist loading functionality."""
    
    def test_load_valid_whitelist(self, tmp_path):
        """Test loading valid whitelist file."""
        whitelist_file = tmp_path / "test_intents.json"
        whitelist_data = ["greet", "warn", "threaten"]
        
        with whitelist_file.open("w") as f:
            json.dump(whitelist_data, f)
        
        result = load_whitelist(str(whitelist_file))
        assert result == {"greet", "warn", "threaten"}
    
    def test_load_missing_whitelist(self):
        """Test loading missing whitelist file returns empty set."""
        result = load_whitelist("nonexistent_file.json")
        assert result == set()
    
    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns empty set."""
        whitelist_file = tmp_path / "invalid.json"
        whitelist_file.write_text("invalid json content")
        
        result = load_whitelist(str(whitelist_file))
        assert result == set()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])