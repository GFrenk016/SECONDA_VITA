"""Main NPC AI adapter with structured output and validation.

Orchestrates LLM calls, validation, and memory updates for NPCs.
"""
import json
import logging
from pathlib import Path
from .validator import validate_schema, validate_semantics, load_whitelist
from .memory import retrieve, write_mem

# Load whitelists (will be loaded from assets)
_ASSETS_BASE = Path(__file__).resolve().parents[2] / "assets" / "npc"
INTENTS = load_whitelist(_ASSETS_BASE / "intents.json")
ACTIONS = load_whitelist(_ASSETS_BASE / "actions.json")

SYSTEM_PROMPT = """You are {name}, an NPC in a text-adventure engine.
Personality: {persona}. Goals: {goals}. Taboo: {taboo}.
World rules: Only output STRICT JSON matching the provided schema.
Steps:
1) Decide an intent from the allowed list.
2) Optional action from the allowed list.
3) Generate a SHORT 'say' line (max 160 chars).
4) Optionally write memories (episodic/semantic).
5) Adjust relationship (-2..+2).
6) Output JSON ONLY. No extra text.

Allowed intents: {intents}
Allowed actions: {actions}
"""

def build_user_prompt(context, retrieved_mem):
    """Build user prompt with context and relevant memories."""
    return {
        "context": context,
        "memories": retrieved_mem,
        "schema_hint": "Use the exact keys as schema: npc_id,mood,intent,action,say,memory_write,relationship_delta,directives,confidence,stop_speaking_after"
    }

def npc_turn(llm_call, npc, player, world, scene_context):
    """Execute an NPC turn with structured AI response.
    
    Args:
        llm_call: Function to call LLM (system, user) -> str
        npc: NPC object
        player: Player state
        world: World state
        scene_context: Current scene context dict
        
    Returns:
        Dict with NPC response or error fallback
    """
    try:
        # Retrieve relevant memories
        query_terms = [
            getattr(player, 'name', 'player'),
            scene_context.get("place", ""),
            scene_context.get("weather", ""),
        ]
        mem = retrieve(npc.id, query_terms)
        
        # Build prompts
        sys = SYSTEM_PROMPT.format(
            name=npc.name,
            persona=getattr(npc, 'persona', getattr(npc, 'personality', {})),
            goals=getattr(npc, 'goals', []),
            taboo=getattr(npc, 'taboo', "Nothing specific"),
            intents=list(INTENTS),
            actions=list(ACTIONS)
        )
        usr = build_user_prompt(scene_context, mem)
        
        # Call LLM
        raw = llm_call(system=sys, user=json.dumps(usr, ensure_ascii=False))
        
        # Extract JSON from response (handle extra text)
        json_start = raw.find("{")
        json_end = raw.rfind("}")
        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON found in response")
        
        payload = json.loads(raw[json_start:json_end+1])
        
        # Validate schema
        validate_schema(payload)
        
        # Validate semantics
        ok, err = validate_semantics(payload, world, npc, player, INTENTS, ACTIONS)
        if not ok:
            logging.warning(f"NPC {npc.id} semantic validation failed: {err}")
            return {
                "say": "...",
                "error": err,
                "npc_id": npc.id,
                "mood": "neutral",
                "intent": "evade"
            }
        
        # Apply effects
        memory_items = payload.get("memory_write", [])
        if memory_items:
            write_mem(npc.id, memory_items)
        
        # Update relationship
        relationship_delta = payload.get("relationship_delta", 0)
        if relationship_delta != 0 and hasattr(npc, 'relationships'):
            player_id = getattr(player, 'id', 'player')
            if not hasattr(npc, 'relationships'):
                npc.relationships = {}
            current_rel = npc.relationships.get(player_id, 0)
            npc.relationships[player_id] = max(-10, min(10, current_rel + relationship_delta))
        
        return payload
        
    except (json.JSONDecodeError, ValueError, Exception) as e:
        logging.error(f"NPC {npc.id} AI call failed: {e}")
        # Graceful fallback
        return {
            "say": "...",
            "error": str(e),
            "npc_id": getattr(npc, 'id', 'unknown'),
            "mood": "neutral", 
            "intent": "evade"
        }