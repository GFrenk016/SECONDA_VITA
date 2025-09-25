"""Test the branched journal system."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.quest.journal import emit, create_journal_node_key, get_recent_entries
from engine.quest.model import Quest

class MockGameState:
    """Mock GameState for testing."""
    def __init__(self):
        self.flags = {"morale": 50}
        self.time_minutes = 10 * 60  # 10:00
        self.weather = "sereno"
        self.daytime = "giorno"
        self.current_macro = "kitchen"
        self.current_micro = "bench"
        self.day_count = 1
        self.journal_history = []

def test_basic_journal_emission():
    """Test basic journal entry emission."""
    gs = MockGameState()
    
    quest = Quest(
        id="test_quest",
        title="Test Quest",
        journal_nodes={
            "q.test_quest.step1.default": "Basic journal entry for step 1."
        }
    )
    
    text = emit(quest, "q.test_quest.step1.default", {}, gs)
    assert text == "Basic journal entry for step 1."
    
    # Check that entry was added to journal history
    assert len(gs.journal_history) == 1
    entry = gs.journal_history[0]
    assert entry["quest_id"] == "test_quest"
    assert entry["node_key"] == "q.test_quest.step1.default"
    assert entry["text"] == "Basic journal entry for step 1."

def test_weather_variants():
    """Test weather-based journal variants."""
    gs = MockGameState()
    
    quest = Quest(
        id="weather_quest",
        title="Weather Quest",
        journal_nodes={
            "q.weather_quest.step1.default": "A normal day.",
            "q.weather_quest.step1.pioggia": "The rain falls heavily.",
            "q.weather_quest.step1.rain": "Rain variant (generic)."
        }
    )
    
    # Test clear weather - should use default
    gs.weather = "sereno"
    text = emit(quest, "q.weather_quest.step1.default", {}, gs)
    assert text == "A normal day."
    
    # Test rain - should use specific rain variant
    gs.weather = "pioggia"
    text = emit(quest, "q.weather_quest.step1.default", {}, gs)
    assert text == "The rain falls heavily."
    
    # Test storm - should use generic rain variant
    gs.weather = "storm"
    quest.journal_nodes.pop("q.weather_quest.step1.pioggia")  # Remove specific variant
    text = emit(quest, "q.weather_quest.step1.default", {}, gs)
    assert text == "Rain variant (generic)."

def test_time_variants():
    """Test time-based journal variants."""
    gs = MockGameState()
    
    quest = Quest(
        id="time_quest",
        title="Time Quest",
        journal_nodes={
            "q.time_quest.step1.default": "During the day.",
            "q.time_quest.step1.notte": "In the darkness of night.",
            "q.time_quest.step1.night": "Night variant (generic)."
        }
    )
    
    # Test day - should use default
    gs.daytime = "giorno"
    text = emit(quest, "q.time_quest.step1.default", {}, gs)
    assert text == "During the day."
    
    # Test night - should use specific night variant
    gs.daytime = "notte"
    text = emit(quest, "q.time_quest.step1.default", {}, gs)
    assert text == "In the darkness of night."

def test_mood_variants():
    """Test mood/stat-based journal variants."""
    gs = MockGameState()
    
    quest = Quest(
        id="mood_quest",
        title="Mood Quest",
        journal_nodes={
            "q.mood_quest.step1.default": "Feeling normal.",
            "q.mood_quest.step1.desperate": "Hope is fading away.",
            "q.mood_quest.step1.hopeful": "There's light at the end of the tunnel."
        }
    )
    
    # Test normal morale
    gs.flags["morale"] = 50
    text = emit(quest, "q.mood_quest.step1.default", {}, gs)
    assert text == "Feeling normal."
    
    # Test low morale
    gs.flags["morale"] = 20
    text = emit(quest, "q.mood_quest.step1.default", {}, gs)
    assert text == "Hope is fading away."
    
    # Test high morale
    gs.flags["morale"] = 80
    text = emit(quest, "q.mood_quest.step1.default", {}, gs)
    assert text == "There's light at the end of the tunnel."

def test_placeholder_replacement():
    """Test placeholder replacement in journal text."""
    gs = MockGameState()
    gs.time_minutes = 14 * 60 + 30  # 14:30 
    gs.weather = "pioggia"
    gs.current_micro = "kitchen"
    gs.day_count = 3
    gs.flags["morale"] = 75
    
    quest = Quest(
        id="placeholder_quest",
        title="Placeholder Quest",
        journal_nodes={
            "q.placeholder_quest.step1.default": "It's {time} on day {day}. The {weather} makes everything difficult in the {location}. Morale: {morale}."
        }
    )
    
    text = emit(quest, "q.placeholder_quest.step1.default", {}, gs)
    expected = "It's 20:30 on day 3. The pioggia makes everything difficult in the kitchen. Morale: 75."
    assert text == expected

def test_context_placeholders():
    """Test context-specific placeholder replacement."""
    gs = MockGameState()
    
    quest = Quest(
        id="context_quest",
        title="Context Quest",
        journal_nodes={
            "q.context_quest.step1.default": "Hello {npc_name}, you have {item_count} items."
        }
    )
    
    context = {
        "npc_name": "Marcus",
        "item_count": 5
    }
    
    text = emit(quest, "q.context_quest.step1.default", context, gs)
    assert text == "Hello Marcus, you have 5 items."

def test_npc_placeholders():
    """Test NPC name placeholder replacement."""
    gs = MockGameState()
    
    quest = Quest(
        id="npc_quest",
        title="NPC Quest",
        journal_nodes={
            "q.npc_quest.step1.default": "I need to find {npc:clementine} and talk to {npc:marcus}."
        }
    )
    
    text = emit(quest, "q.npc_quest.step1.default", {}, gs)
    assert text == "I need to find Clementine and talk to Marcus."

def test_missing_journal_entry():
    """Test handling of missing journal entries."""
    gs = MockGameState()
    
    quest = Quest(
        id="empty_quest",
        title="Empty Quest",
        journal_nodes={}
    )
    
    text = emit(quest, "q.empty_quest.missing.key", {}, gs)
    assert text == "[Missing journal entry: q.empty_quest.missing.key]"

def test_variant_priority():
    """Test that more specific variants take priority."""
    gs = MockGameState()
    gs.weather = "pioggia"
    gs.daytime = "notte"
    gs.current_micro = "basement"
    gs.flags["morale"] = 20
    
    quest = Quest(
        id="priority_quest",
        title="Priority Quest",
        journal_nodes={
            "q.priority_quest.step1.default": "Default text.",
            "q.priority_quest.step1.pioggia": "Rain text.",
            "q.priority_quest.step1.notte": "Night text.",
            "q.priority_quest.step1.basement": "Location text.",
            "q.priority_quest.step1.desperate": "Mood text."
        }
    )
    
    # Weather should have highest priority
    text = emit(quest, "q.priority_quest.step1.default", {}, gs)
    assert text == "Rain text."

def test_create_journal_node_key():
    """Test journal node key creation utility."""
    key = create_journal_node_key("test_quest", "step1", "default")
    assert key == "q.test_quest.step1.default"
    
    key = create_journal_node_key("another_quest", "step2", "rain")
    assert key == "q.another_quest.step2.rain"

def test_get_recent_entries():
    """Test getting recent journal entries."""
    gs = MockGameState()
    
    # Add some entries to history
    gs.journal_history = [
        {"text": "Entry 1", "timestamp": 100},
        {"text": "Entry 2", "timestamp": 200},
        {"text": "Entry 3", "timestamp": 300},
        {"text": "Entry 4", "timestamp": 400},
        {"text": "Entry 5", "timestamp": 500}
    ]
    
    # Get last 3 entries
    recent = get_recent_entries(gs, limit=3)
    assert len(recent) == 3
    assert recent[0]["text"] == "Entry 3"
    assert recent[1]["text"] == "Entry 4"
    assert recent[2]["text"] == "Entry 5"
    
    # Get more entries than available
    recent = get_recent_entries(gs, limit=10)
    assert len(recent) == 5

def test_journal_history_tracking():
    """Test that journal history is properly tracked."""
    gs = MockGameState()
    gs.time_minutes = 12 * 60
    gs.weather = "pioggia"
    gs.current_macro = "forest"
    gs.current_micro = "clearing"
    
    quest = Quest(
        id="history_quest",
        title="History Quest",
        journal_nodes={
            "q.history_quest.step1.default": "First entry.",
            "q.history_quest.step2.default": "Second entry."
        }
    )
    
    # Emit first entry
    emit(quest, "q.history_quest.step1.default", {}, gs)
    
    # Emit second entry
    emit(quest, "q.history_quest.step2.default", {}, gs)
    
    # Check history
    assert len(gs.journal_history) == 2
    
    entry1 = gs.journal_history[0]
    assert entry1["quest_id"] == "history_quest"
    assert entry1["node_key"] == "q.history_quest.step1.default"
    assert entry1["text"] == "First entry."
    assert entry1["timestamp"] == 12 * 60
    assert entry1["weather"] == "pioggia"
    assert entry1["location"] == "forest/clearing"
    
    entry2 = gs.journal_history[1]
    assert entry2["quest_id"] == "history_quest"
    assert entry2["node_key"] == "q.history_quest.step2.default"
    assert entry2["text"] == "Second entry."

if __name__ == "__main__":
    test_basic_journal_emission()
    test_weather_variants()
    test_time_variants()
    test_mood_variants()
    test_placeholder_replacement()
    test_context_placeholders()
    test_npc_placeholders()
    test_missing_journal_entry()
    test_variant_priority()
    test_create_journal_node_key()
    test_get_recent_entries()
    test_journal_history_tracking()
    print("All journal tests passed!")