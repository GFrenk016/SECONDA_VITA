"""Test the quest loader system."""

import sys
import os
import tempfile
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.quest.loader import load_main_story, validate_story_structure
from engine.quest.model import Quest, Step, Condition, Reward

def test_load_main_story():
    """Test loading main story from JSON file."""
    # Create a temporary story file
    story_data = {
        "acts": [
            {
                "id": "ACT_I",
                "title": "First Act",
                "quests": [
                    {
                        "id": "Q1_TEST",
                        "title": "Test Quest",
                        "priority": "main",
                        "steps": [
                            {
                                "id": "s1",
                                "title": "First Step",
                                "description": "Do something",
                                "complete_conditions": [
                                    {
                                        "op": "flag_is",
                                        "args": {"key": "test_flag", "value": True}
                                    }
                                ],
                                "on_complete_flags": {"step1_done": True}
                            }
                        ],
                        "rewards_on_complete": {
                            "stats": {"morale": 10},
                            "items": [{"id": "reward_item", "qty": 1}]
                        },
                        "journal_nodes": {
                            "q.Q1_TEST.s1.start": "Test journal entry"
                        }
                    }
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(story_data, f)
        temp_file = f.name
    
    try:
        # Load the story
        quests = load_main_story(temp_file)
        
        # Verify quest was loaded correctly
        assert len(quests) == 1
        quest = quests[0]
        
        assert quest.id == "Q1_TEST"
        assert quest.title == "Test Quest"
        assert quest.act == "ACT_I"
        assert quest.priority == "main"
        
        # Check steps
        assert len(quest.steps) == 1
        step = quest.steps[0]
        assert step.id == "s1"
        assert step.title == "First Step"
        assert len(step.complete_conditions) == 1
        
        condition = step.complete_conditions[0]
        assert condition.op == "flag_is"
        assert condition.args["key"] == "test_flag"
        assert condition.args["value"] == True
        
        # Check rewards
        assert quest.rewards_on_complete.stats["morale"] == 10
        assert quest.rewards_on_complete.items[0]["id"] == "reward_item"
        
        # Check journal nodes
        assert "q.Q1_TEST.s1.start" in quest.journal_nodes
        
    finally:
        os.unlink(temp_file)

def test_legacy_condition_conversion():
    """Test conversion of legacy condition format."""
    story_data = {
        "acts": [
            {
                "id": "ACT_LEGACY",
                "title": "Legacy Act",
                "quests": [
                    {
                        "id": "LEGACY_QUEST",
                        "title": "Legacy Quest",
                        "steps": [
                            {
                                "id": "legacy_step",
                                "title": "Legacy Step",
                                "description": "Test legacy conditions",
                                "complete_conditions": [
                                    {
                                        "type": "flag",
                                        "flag": "old_flag",
                                        "value": True
                                    },
                                    {
                                        "type": "item_count",
                                        "item": "old_item",
                                        "quantity": 2
                                    },
                                    {
                                        "type": "location",
                                        "location": "old_location"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(story_data, f)
        temp_file = f.name
    
    try:
        quests = load_main_story(temp_file)
        assert len(quests) == 1
        
        step = quests[0].steps[0]
        conditions = step.complete_conditions
        assert len(conditions) == 3
        
        # Check flag condition conversion
        flag_condition = conditions[0]
        assert flag_condition.op == "flag_is"
        assert flag_condition.args["key"] == "old_flag"
        assert flag_condition.args["value"] == True
        
        # Check item condition conversion
        item_condition = conditions[1]  
        assert item_condition.op == "has_item"
        assert item_condition.args["id"] == "old_item"
        assert item_condition.args["qty"] == 2
        
        # Check location condition conversion
        location_condition = conditions[2]
        assert location_condition.op == "in_location"
        assert location_condition.args["micro"] == "old_location"
        
    finally:
        os.unlink(temp_file)

def test_validation():
    """Test story structure validation."""
    # Valid structure
    valid_story = {
        "acts": [
            {
                "id": "ACT_1",
                "title": "Act 1",
                "quests": [
                    {
                        "id": "Q1",
                        "title": "Quest 1",
                        "steps": []
                    }
                ]
            }
        ]
    }
    
    errors = validate_story_structure(valid_story)
    assert len(errors) == 0
    
    # Invalid structure - missing acts
    invalid_story1 = {"not_acts": []}
    errors = validate_story_structure(invalid_story1)
    assert len(errors) > 0
    assert "Missing 'acts' key" in errors[0]
    
    # Invalid structure - acts not a list
    invalid_story2 = {"acts": "not a list"}
    errors = validate_story_structure(invalid_story2)
    assert len(errors) > 0
    assert "'acts' must be a list" in errors[0]
    
    # Invalid structure - missing act fields
    invalid_story3 = {
        "acts": [
            {
                "title": "Act without ID"
            }
        ]
    }
    errors = validate_story_structure(invalid_story3)
    assert len(errors) > 0
    assert any("missing 'id' field" in error for error in errors)

def test_missing_file():
    """Test handling of missing story file."""
    try:
        load_main_story("nonexistent_file.json")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass  # Expected

def test_invalid_json():
    """Test handling of invalid JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("invalid json {")
        temp_file = f.name
    
    try:
        load_main_story(temp_file)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid JSON" in str(e)
    finally:
        os.unlink(temp_file)

def test_multiple_acts_and_quests():
    """Test loading multiple acts with multiple quests."""
    story_data = {
        "acts": [
            {
                "id": "ACT_I",
                "title": "First Act",
                "quests": [
                    {"id": "Q1", "title": "Quest 1", "steps": []},
                    {"id": "Q2", "title": "Quest 2", "steps": []}
                ]
            },
            {
                "id": "ACT_II", 
                "title": "Second Act",
                "quests": [
                    {"id": "Q3", "title": "Quest 3", "steps": []}
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(story_data, f)
        temp_file = f.name
    
    try:
        quests = load_main_story(temp_file)
        assert len(quests) == 3
        
        # Check quest act assignments
        acts = [q.act for q in quests]
        assert "ACT_I" in acts
        assert "ACT_II" in acts
        assert acts.count("ACT_I") == 2
        assert acts.count("ACT_II") == 1
        
    finally:
        os.unlink(temp_file)

if __name__ == "__main__":
    test_load_main_story()
    test_legacy_condition_conversion()
    test_validation()
    test_missing_file()
    test_invalid_json()
    test_multiple_acts_and_quests()
    print("All loader tests passed!")