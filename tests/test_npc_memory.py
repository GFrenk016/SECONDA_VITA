"""Tests for NPC RAG memory system."""

import pytest
import tempfile
import shutil
from pathlib import Path
from engine.npc.memory import write_mem, retrieve, clear_memories, get_memory_count


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Create temporary directory for memory files."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Mock the BASE path in the memory module
    import engine.npc.memory as memory_module
    original_base = memory_module.BASE
    memory_module.BASE = temp_dir / "npc_memories"
    
    yield temp_dir
    
    # Cleanup
    memory_module.BASE = original_base
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_memories():
    """Sample memory data for testing."""
    return [
        {
            "type": "episodic",
            "key": "met_frank",
            "value": "First meeting with Frank at the lake at dawn"
        },
        {
            "type": "semantic", 
            "key": "frank_personality",
            "value": "Frank seems cautious but friendly"
        },
        {
            "type": "episodic",
            "key": "found_bandage",
            "value": "Found medical supplies near the old cabin"
        }
    ]


class TestMemoryWrite:
    """Test memory writing functionality."""
    
    def test_write_memories(self, temp_data_dir, sample_memories):
        """Test writing memories to file."""
        npc_id = "vicky"
        
        write_mem(npc_id, sample_memories)
        
        # Check file was created
        memory_file = temp_data_dir / "npc_memories" / f"{npc_id}.jsonl"
        assert memory_file.exists()
        
        # Check content
        lines = memory_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
    
    def test_write_empty_memories(self, temp_data_dir):
        """Test that empty memory list doesn't create file."""
        npc_id = "vicky"
        
        write_mem(npc_id, [])
        
        memory_file = temp_data_dir / "npc_memories" / f"{npc_id}.jsonl"
        assert not memory_file.exists()
    
    def test_append_memories(self, temp_data_dir, sample_memories):
        """Test that memories are appended to existing file."""
        npc_id = "vicky"
        
        # Write first batch
        write_mem(npc_id, sample_memories[:2])
        
        # Write second batch
        write_mem(npc_id, sample_memories[2:])
        
        # Check total count
        assert get_memory_count(npc_id) == 3


class TestMemoryRetrieval:
    """Test memory retrieval functionality."""
    
    def test_retrieve_relevant_memories(self, temp_data_dir, sample_memories):
        """Test retrieving memories relevant to query terms."""
        npc_id = "vicky"
        write_mem(npc_id, sample_memories)
        
        # Search for "frank" related memories
        results = retrieve(npc_id, ["frank"])
        
        assert len(results) == 2  # Should find 2 frank-related memories
        assert any("met_frank" in r.get("key", "") for r in results)
        assert any("frank_personality" in r.get("key", "") for r in results)
    
    def test_retrieve_with_limit(self, temp_data_dir, sample_memories):
        """Test that retrieval respects limit parameter."""
        npc_id = "vicky"
        
        # Add more memories with same keyword
        extended_memories = sample_memories + [
            {"type": "episodic", "key": "frank_said_hello", "value": "Frank greeted me"},
            {"type": "episodic", "key": "frank_left", "value": "Frank departed eastward"}
        ]
        write_mem(npc_id, extended_memories)
        
        # Retrieve with limit
        results = retrieve(npc_id, ["frank"], limit=2)
        
        assert len(results) <= 2
    
    def test_retrieve_no_matches(self, temp_data_dir, sample_memories):
        """Test retrieving with no matching terms."""
        npc_id = "vicky"
        write_mem(npc_id, sample_memories)
        
        results = retrieve(npc_id, ["zombies", "spaceship"])
        
        assert len(results) == 0
    
    def test_retrieve_nonexistent_npc(self, temp_data_dir):
        """Test retrieving for NPC with no memory file."""
        results = retrieve("nonexistent_npc", ["anything"])
        
        assert results == []
    
    def test_retrieve_case_insensitive(self, temp_data_dir, sample_memories):
        """Test that retrieval is case-insensitive."""
        npc_id = "vicky"
        write_mem(npc_id, sample_memories)
        
        results_lower = retrieve(npc_id, ["frank"])
        results_upper = retrieve(npc_id, ["FRANK"])
        results_mixed = retrieve(npc_id, ["Frank"])
        
        assert len(results_lower) == len(results_upper) == len(results_mixed)


class TestMemoryScoring:
    """Test memory relevance scoring."""
    
    def test_multiple_keyword_matches(self, temp_data_dir):
        """Test that memories with multiple keyword matches score higher."""
        npc_id = "vicky"
        memories = [
            {
                "type": "episodic",
                "key": "frank_at_lake",
                "value": "Met Frank at the lake during morning"
            },
            {
                "type": "episodic", 
                "key": "met_someone",
                "value": "Met someone at the market"
            }
        ]
        write_mem(npc_id, memories)
        
        # Search for both "frank" and "lake"
        results = retrieve(npc_id, ["frank", "lake"])
        
        # First result should be the one with both keywords
        assert len(results) >= 1
        assert "frank_at_lake" in results[0].get("key", "")


class TestMemoryUtilities:
    """Test utility functions."""
    
    def test_clear_memories(self, temp_data_dir, sample_memories):
        """Test clearing all memories for an NPC."""
        npc_id = "vicky"
        write_mem(npc_id, sample_memories)
        
        # Verify memories exist
        assert get_memory_count(npc_id) == 3
        
        # Clear memories
        clear_memories(npc_id)
        
        # Verify memories are gone
        assert get_memory_count(npc_id) == 0
    
    def test_get_memory_count_empty(self, temp_data_dir):
        """Test getting memory count for NPC with no memories."""
        count = get_memory_count("empty_npc")
        assert count == 0
    
    def test_get_memory_count_existing(self, temp_data_dir, sample_memories):
        """Test getting memory count for NPC with memories."""
        npc_id = "vicky"
        write_mem(npc_id, sample_memories)
        
        count = get_memory_count(npc_id)
        assert count == 3


class TestMemoryCorruption:
    """Test handling of corrupted memory files."""
    
    def test_retrieve_corrupted_file(self, temp_data_dir):
        """Test that corrupted memory file returns empty list."""
        npc_id = "corrupted"
        
        # Create corrupted memory file
        memory_file = temp_data_dir / "npc_memories"
        memory_file.mkdir(parents=True, exist_ok=True)
        (memory_file / f"{npc_id}.jsonl").write_text("corrupted json content\n{invalid")
        
        results = retrieve(npc_id, ["anything"])
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])