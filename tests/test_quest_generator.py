"""Test the procedural quest generator system."""

import sys
import os
import tempfile
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.quest.generator import generate_side_quests
from engine.quest.model import Quest

class MockGameState:
    """Mock GameState for testing."""
    def __init__(self):
        self.flags = {}
        self.player_inventory = {}
        self.world_id = "overworld"
        self.current_macro = "yard"
        self.current_micro = "bench"
        self.player_stats = {}
        self.relationships = {}
        self.time_minutes = 12 * 60  # 12:00
        self.weather = "pioggia"
        self.daytime = "giorno"
        self.rng_seed = 42

def test_generate_side_quests_deterministic():
    """Test that side quest generation is deterministic with same seed."""
    gs = MockGameState()
    
    templates_data = {
        "templates": [
            {
                "id": "TEST_RAIN_QUEST",
                "title": "Rainy Day Task",
                "base_weight": 1.0,
                "when": {
                    "weather_in": {"any": ["pioggia", "storm"]}
                },
                "goals": [
                    {
                        "type": "collect",
                        "item": "water",
                        "qty": 3
                    }
                ],
                "rewards": {
                    "items": [{"id": "clean_water", "qty": 1}],
                    "stats": {"morale": 5}
                },
                "weights": {
                    "pioggia": 2.0,
                    "giorno": 1.5
                }
            },
            {
                "id": "TEST_CLEAR_QUEST",
                "title": "Sunny Day Task",
                "base_weight": 1.0,
                "when": {
                    "weather_in": {"any": ["sereno", "nuvoloso"]}
                },
                "goals": [
                    {
                        "type": "collect",
                        "item": "herbs",
                        "qty": 2
                    }
                ],
                "rewards": {
                    "stats": {"morale": 3}
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(templates_data, f)
        temp_file = f.name
    
    try:
        # Generate quests with same seed multiple times
        quests1 = generate_side_quests(temp_file, gs, max_quests=2, rng_seed=42)
        quests2 = generate_side_quests(temp_file, gs, max_quests=2, rng_seed=42)
        
        # Should get same results
        assert len(quests1) == len(quests2)
        
        for q1, q2 in zip(quests1, quests2):
            # Quest IDs will be different due to random component, but titles should match
            assert q1.title == q2.title
            assert q1.priority == q2.priority
            assert len(q1.steps) == len(q2.steps)
            
    finally:
        os.unlink(temp_file)

def test_weather_condition_filtering():
    """Test that templates are filtered by weather conditions."""
    gs = MockGameState()
    
    templates_data = {
        "templates": [
            {
                "id": "RAIN_ONLY",
                "title": "Rain Quest",
                "when": {
                    "weather_in": {"any": ["pioggia"]}
                },
                "goals": [{"type": "collect", "item": "water", "qty": 1}],
                "rewards": {"stats": {"morale": 1}}
            },
            {
                "id": "CLEAR_ONLY",
                "title": "Clear Quest", 
                "when": {
                    "weather_in": {"any": ["sereno"]}
                },
                "goals": [{"type": "collect", "item": "herbs", "qty": 1}],
                "rewards": {"stats": {"morale": 1}}
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(templates_data, f)
        temp_file = f.name
    
    try:
        # With rainy weather, should only get rain quest
        gs.weather = "pioggia"
        quests = generate_side_quests(temp_file, gs, max_quests=5, rng_seed=42)
        
        rain_quest_found = any("Rain Quest" in q.title for q in quests)
        clear_quest_found = any("Clear Quest" in q.title for q in quests)
        
        assert rain_quest_found
        assert not clear_quest_found
        
        # With clear weather, should only get clear quest
        gs.weather = "sereno"
        quests = generate_side_quests(temp_file, gs, max_quests=5, rng_seed=42)
        
        rain_quest_found = any("Rain Quest" in q.title for q in quests)
        clear_quest_found = any("Clear Quest" in q.title for q in quests)
        
        assert not rain_quest_found
        assert clear_quest_found
        
    finally:
        os.unlink(temp_file)

def test_time_condition_filtering():
    """Test that templates are filtered by time conditions."""
    gs = MockGameState()
    
    templates_data = {
        "templates": [
            {
                "id": "DAY_QUEST",
                "title": "Day Quest",
                "when": {
                    "time_between": {"start": "06:00", "end": "18:00"}
                },
                "goals": [{"type": "collect", "item": "flowers", "qty": 1}],
                "rewards": {"stats": {"morale": 1}}
            },
            {
                "id": "NIGHT_QUEST",
                "title": "Night Quest",
                "when": {
                    "time_between": {"start": "20:00", "end": "06:00"}
                },
                "goals": [{"type": "collect", "item": "nocturnal_herbs", "qty": 1}],
                "rewards": {"stats": {"morale": 1}}
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(templates_data, f)
        temp_file = f.name
    
    try:
        # During day (12:00)
        gs.time_minutes = 12 * 60
        quests = generate_side_quests(temp_file, gs, max_quests=5, rng_seed=42)
        
        day_quest_found = any("Day Quest" in q.title for q in quests)
        night_quest_found = any("Night Quest" in q.title for q in quests)
        
        assert day_quest_found
        assert not night_quest_found
        
        # During night (23:00)
        gs.time_minutes = 23 * 60
        quests = generate_side_quests(temp_file, gs, max_quests=5, rng_seed=42)
        
        day_quest_found = any("Day Quest" in q.title for q in quests)
        night_quest_found = any("Night Quest" in q.title for q in quests)
        
        assert not day_quest_found
        assert night_quest_found
        
    finally:
        os.unlink(temp_file)

def test_weight_calculation():
    """Test that template weights affect selection probability."""
    gs = MockGameState()
    gs.weather = "pioggia"
    gs.daytime = "notte"
    
    templates_data = {
        "templates": [
            {
                "id": "HIGH_WEIGHT",
                "title": "High Weight Quest",
                "base_weight": 1.0,
                "when": {},  # Always eligible
                "goals": [{"type": "collect", "item": "item1", "qty": 1}],
                "rewards": {"stats": {"morale": 1}},
                "weights": {
                    "pioggia": 10.0,  # Very high weight for rain
                    "notte": 5.0      # High weight for night
                }
            },
            {
                "id": "LOW_WEIGHT",
                "title": "Low Weight Quest",
                "base_weight": 1.0,
                "when": {},  # Always eligible
                "goals": [{"type": "collect", "item": "item2", "qty": 1}],
                "rewards": {"stats": {"morale": 1}},
                "weights": {
                    "pioggia": 0.1,   # Very low weight for rain
                    "notte": 0.1      # Low weight for night
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(templates_data, f)
        temp_file = f.name
    
    try:
        # Generate many quests and count which template is selected more often
        high_weight_count = 0
        low_weight_count = 0
        
        for seed in range(100):
            quests = generate_side_quests(temp_file, gs, max_quests=1, rng_seed=seed)
            if quests:
                if "High Weight" in quests[0].title:
                    high_weight_count += 1
                elif "Low Weight" in quests[0].title:
                    low_weight_count += 1
        
        # High weight quest should be selected much more often
        assert high_weight_count > low_weight_count * 2
        
    finally:
        os.unlink(temp_file)

def test_different_goal_types():
    """Test generation of different goal types."""
    gs = MockGameState()
    
    templates_data = {
        "templates": [
            {
                "id": "COLLECT_QUEST",
                "title": "Collect Quest",
                "goals": [
                    {
                        "type": "collect",
                        "item": "wood",
                        "qty": 5,
                        "area": {"world": "forest", "macro": "clearing"}
                    }
                ],
                "rewards": {"stats": {"morale": 1}}
            },
            {
                "id": "ESCORT_QUEST",
                "title": "Escort Quest",
                "goals": [
                    {
                        "type": "escort",
                        "npc": "survivor",
                        "to": {"world": "camp"}
                    }
                ],
                "rewards": {"stats": {"morale": 2}}
            },
            {
                "id": "REACH_QUEST",
                "title": "Reach Quest",
                "goals": [
                    {
                        "type": "reach",
                        "location": {"world": "ruins", "macro": "tower"}
                    }
                ],
                "rewards": {"stats": {"morale": 1}}
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(templates_data, f)
        temp_file = f.name
    
    try:
        quests = generate_side_quests(temp_file, gs, max_quests=3, rng_seed=42)
        
        # Should generate different types of quests
        titles = [q.title for q in quests]
        assert len(set(titles)) > 1  # At least 2 different quest types
        
        # Check that steps were generated with correct conditions
        for quest in quests:
            assert len(quest.steps) >= 1
            for step in quest.steps:
                assert len(step.complete_conditions) >= 1
                
    finally:
        os.unlink(temp_file)

def test_empty_templates():
    """Test handling of empty templates file."""
    gs = MockGameState()
    
    empty_templates = {"templates": []}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(empty_templates, f)
        temp_file = f.name
    
    try:
        quests = generate_side_quests(temp_file, gs, max_quests=5, rng_seed=42)
        assert len(quests) == 0
        
    finally:
        os.unlink(temp_file)

def test_missing_templates_file():
    """Test handling of missing templates file."""
    gs = MockGameState()
    
    quests = generate_side_quests("nonexistent_file.json", gs, max_quests=5, rng_seed=42)
    assert len(quests) == 0

if __name__ == "__main__":
    test_generate_side_quests_deterministic()
    test_weather_condition_filtering()
    test_time_condition_filtering()
    test_weight_calculation()
    test_different_goal_types()
    test_empty_templates()
    test_missing_templates_file()
    print("All generator tests passed!")