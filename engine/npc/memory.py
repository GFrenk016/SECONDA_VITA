"""RAG memory system for NPCs.

Implements simple file-based memory storage and retrieval
with keyword matching for RAG functionality.
"""
from pathlib import Path
import json
import time

# Base directory for NPC memory files
BASE = Path("data/npc_memories")

def write_mem(npc_id, items):
    """Write memory items to NPC's memory file.
    
    Args:
        npc_id: NPC identifier
        items: List of memory items to write
    """
    if not items:
        return
    
    BASE.mkdir(parents=True, exist_ok=True)
    fp = BASE / f"{npc_id}.jsonl"
    
    with fp.open("a", encoding="utf-8") as f:
        for item in items:
            # Add timestamp if not present
            if "timestamp" not in item:
                item["timestamp"] = int(time.time())
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def retrieve(npc_id, query_terms, limit=5):
    """Retrieve relevant memories for an NPC.
    
    Args:
        npc_id: NPC identifier
        query_terms: List of terms to search for
        limit: Maximum number of memories to return
        
    Returns:
        List of relevant memory objects, scored by relevance
    """
    fp = BASE / f"{npc_id}.jsonl"
    if not fp.exists():
        return []
    
    # Simple keyword-based scoring
    scored = []
    try:
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            text = f'{obj.get("key", "")} {obj.get("value", "")}'.lower()
            score = sum(text.count(q.lower()) for q in (query_terms or []))
            scored.append((score, obj))
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Handle corrupted memory file gracefully
        return []
    
    # Sort by relevance score and return top results
    scored.sort(reverse=True, key=lambda x: x[0])
    return [obj for score, obj in scored[:limit] if score > 0]

def clear_memories(npc_id):
    """Clear all memories for an NPC (for testing/debugging)."""
    fp = BASE / f"{npc_id}.jsonl"
    if fp.exists():
        fp.unlink()

def get_memory_count(npc_id):
    """Get the number of memories stored for an NPC."""
    fp = BASE / f"{npc_id}.jsonl"
    if not fp.exists():
        return 0
    
    try:
        return len(fp.read_text(encoding="utf-8").splitlines())
    except UnicodeDecodeError:
        return 0