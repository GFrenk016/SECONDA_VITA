"""JSON schema definition for NPC AI responses.

Defines the strict structure that NPC AI must follow to ensure
consistent and validatable outputs.
"""

NPC_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["npc_id", "mood", "intent", "say"],
    "properties": {
        "npc_id": {"type": "string", "minLength": 1},
        "mood": {"type": "string", "enum": ["calm", "wary", "angry", "sad", "neutral", "hopeful"]},
        "intent": {"type": "string"},  # validated against intents.json
        "action": {"type": ["string", "null"]},  # validated against actions.json and state
        "say": {"type": "string", "minLength": 1, "maxLength": 160},
        "memory_write": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "key", "value"],
                "properties": {
                    "type": {"type": "string", "enum": ["episodic", "semantic"]},
                    "key": {"type": "string"},
                    "value": {"type": "string", "maxLength": 240}
                }
            }
        },
        "relationship_delta": {"type": "integer", "minimum": -2, "maximum": 2, "default": 0},
        "directives": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "stop_speaking_after": {"type": "integer", "minimum": 0, "maximum": 2, "default": 1}
    },
    "additionalProperties": False
}