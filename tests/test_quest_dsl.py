"""Test the quest engine DSL condition system."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.quest.dsl import check, check_all
from engine.quest.model import Condition

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

def test_has_item_condition():
    """Test has_item condition with new inventory system."""
    gs = MockGameState()
    gs.player_inventory = {"bandage": 2, "cloth": 1}
    
    # Test positive case
    condition = Condition(op="has_item", args={"id": "bandage", "qty": 1})
    assert check(condition, gs) == True
    
    # Test exact match
    condition = Condition(op="has_item", args={"id": "bandage", "qty": 2})
    assert check(condition, gs) == True
    
    # Test insufficient quantity
    condition = Condition(op="has_item", args={"id": "bandage", "qty": 3})
    assert check(condition, gs) == False
    
    # Test missing item
    condition = Condition(op="has_item", args={"id": "missing", "qty": 1})
    assert check(condition, gs) == False

def test_has_item_legacy_inventory():
    """Test has_item condition with legacy inventory system."""
    gs = MockGameState()
    gs.player_inventory = None
    gs.inventory = {"bandage": 2, "cloth": 1}
    
    condition = Condition(op="has_item", args={"id": "bandage", "qty": 1})
    assert check(condition, gs) == True

def test_flag_is_condition():
    """Test flag_is condition."""
    gs = MockGameState()
    gs.flags = {"tutorial_complete": True, "level": 5, "active_quest": False}
    
    # Test boolean flag
    condition = Condition(op="flag_is", args={"key": "tutorial_complete", "value": True})
    assert check(condition, gs) == True
    
    condition = Condition(op="flag_is", args={"key": "tutorial_complete", "value": False})
    assert check(condition, gs) == False
    
    # Test numeric flag
    condition = Condition(op="flag_is", args={"key": "level", "value": 5})
    assert check(condition, gs) == True
    
    # Test missing flag defaults to False
    condition = Condition(op="flag_is", args={"key": "missing_flag", "value": False})
    assert check(condition, gs) == True

def test_in_location_condition():
    """Test in_location condition."""
    gs = MockGameState()
    gs.world_id = "house"
    gs.current_macro = "kitchen"  
    gs.current_micro = "bench"
    
    # Test world only
    condition = Condition(op="in_location", args={"world": "house"})
    assert check(condition, gs) == True
    
    condition = Condition(op="in_location", args={"world": "forest"})
    assert check(condition, gs) == False
    
    # Test world + macro
    condition = Condition(op="in_location", args={"world": "house", "macro": "kitchen"})
    assert check(condition, gs) == True
    
    condition = Condition(op="in_location", args={"world": "house", "macro": "bedroom"})
    assert check(condition, gs) == False
    
    # Test full hierarchy
    condition = Condition(op="in_location", args={"world": "house", "macro": "kitchen", "micro": "bench"})
    assert check(condition, gs) == True

def test_stat_gte_condition():
    """Test stat_gte condition."""
    gs = MockGameState()
    gs.player_stats = {"morale": 75, "health": 50}
    
    # Test with new stats system
    condition = Condition(op="stat_gte", args={"name": "morale", "value": 50})
    assert check(condition, gs) == True
    
    condition = Condition(op="stat_gte", args={"name": "morale", "value": 80})
    assert check(condition, gs) == False
    
    # Test fallback to flags
    gs.player_stats = None
    gs.flags = {"morale": 60}
    condition = Condition(op="stat_gte", args={"name": "morale", "value": 50})
    assert check(condition, gs) == True

def test_relation_gte_condition():
    """Test relation_gte condition."""
    gs = MockGameState()
    gs.relationships = {"clementine": 75, "clementine.trust": 80}
    
    # Test default affinity field
    condition = Condition(op="relation_gte", args={"npc": "clementine", "value": 70})
    assert check(condition, gs) == True
    
    # Test specific field
    condition = Condition(op="relation_gte", args={"npc": "clementine", "field": "trust", "value": 75})
    assert check(condition, gs) == True
    
    # Test insufficient relationship
    condition = Condition(op="relation_gte", args={"npc": "clementine", "value": 80})
    assert check(condition, gs) == False

def test_time_between_condition():
    """Test time_between condition."""
    gs = MockGameState()
    
    # Test normal time range (09:00 - 17:00)
    gs.time_minutes = 10 * 60  # 10:00 
    condition = Condition(op="time_between", args={"start": "09:00", "end": "17:00"})
    assert check(condition, gs) == True
    
    gs.time_minutes = 8 * 60  # 08:00
    assert check(condition, gs) == False
    
    # Test overnight range (22:00 - 06:00)
    gs.time_minutes = 23 * 60  # 23:00
    condition = Condition(op="time_between", args={"start": "22:00", "end": "06:00"})
    assert check(condition, gs) == True
    
    gs.time_minutes = 2 * 60  # 02:00
    assert check(condition, gs) == True
    
    gs.time_minutes = 12 * 60  # 12:00
    assert check(condition, gs) == False

def test_weather_in_condition():
    """Test weather_in condition."""
    gs = MockGameState()
    
    # Test single weather
    gs.weather = "pioggia"
    condition = Condition(op="weather_in", args={"any": ["pioggia"]})
    assert check(condition, gs) == True
    
    # Test multiple weather options
    condition = Condition(op="weather_in", args={"any": ["pioggia", "storm", "nebbia"]})
    assert check(condition, gs) == True
    
    gs.weather = "sereno"
    assert check(condition, gs) == False

def test_check_all():
    """Test check_all function with multiple conditions."""
    gs = MockGameState()
    gs.flags = {"quest_active": True}
    gs.player_inventory = {"bandage": 1}
    gs.weather = "pioggia"
    
    conditions = [
        Condition(op="flag_is", args={"key": "quest_active", "value": True}),
        Condition(op="has_item", args={"id": "bandage", "qty": 1}),
        Condition(op="weather_in", args={"any": ["pioggia", "storm"]})
    ]
    
    # All conditions met
    assert check_all(conditions, gs) == True
    
    # One condition fails
    gs.flags["quest_active"] = False
    assert check_all(conditions, gs) == False

def test_unknown_condition():
    """Test handling of unknown condition types."""
    gs = MockGameState()
    
    condition = Condition(op="unknown_op", args={})
    assert check(condition, gs) == False

if __name__ == "__main__":
    test_has_item_condition()
    test_has_item_legacy_inventory()
    test_flag_is_condition()
    test_in_location_condition()
    test_stat_gte_condition()
    test_relation_gte_condition()
    test_time_between_condition()
    test_weather_in_condition()
    test_check_all()
    test_unknown_condition()
    print("All DSL tests passed!")