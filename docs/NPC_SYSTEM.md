# NPC System Documentation

The NPC (Non-Player Character) system adds intelligent dialogue and character interaction to Seconda Vita.

## Features

- **Dynamic NPC Loading**: NPCs are loaded from JSON files in `assets/npcs/`
- **AI Dialogue Engine**: Supports both Ollama AI integration and fallback responses
- **Persistent State**: NPC relationships, mood, and memories are maintained
- **Contextual Conversations**: NPCs respond based on personality, mood, and special knowledge
- **Schedule System**: NPCs have daily schedules and can move between locations

## Commands

- `talk` - List NPCs in current location
- `talk <npc_name>` - Start conversation with specific NPC
- `say <message>` - Continue active conversation

## NPC Definition Format

NPCs are defined in JSON files under `assets/npcs/`. Here's the structure:

```json
{
  "id": "unique_npc_id",
  "name": "Display Name",
  "description": "Physical description",
  "current_macro": "macro_room_id",
  "current_micro": "micro_room_id",
  "home_location": "home_micro_room_id",
  "personality": {
    "traits": ["trait1", "trait2"],
    "speech_patterns": ["pattern1", "pattern2"],
    "quirks": ["quirk1", "quirk2"]
  },
  "background": "Character background story",
  "goals": ["goal1", "goal2"],
  "relationship": "stranger|acquaintance|friend|ally|enemy",
  "current_state": "neutral|friendly|hostile|afraid|busy|sleeping",
  "mood": 0.0,
  "conversation_topics": ["topic1", "topic2"],
  "special_knowledge": {
    "keyword": "response when keyword mentioned"
  },
  "daily_schedule": {
    "06:00": "activity",
    "12:00": "another_activity"
  },
  "flags_set": ["flag1", "flag2"],
  "quest_giver": false,
  "merchant": false
}
```

## Core Classes

### NPC
Main NPC data class containing all character information, relationships, and state.

### NPCRegistry  
Manages all NPCs at runtime, handles location indexing and state updates.

### AIDialogueEngine
Handles dialogue generation using either Ollama AI or contextual fallback responses.

### DialogueContext
Contains conversation context including location, time, weather, and history.

## AI Integration

The system supports Ollama for advanced AI dialogue:

1. **Ollama Available**: Uses AI to generate contextual, personality-driven responses
2. **Ollama Unavailable**: Falls back to rule-based responses using special knowledge

### Ollama Setup
To enable AI dialogue:
1. Install Ollama: https://ollama.ai/
2. Run `ollama serve` 
3. Pull a model: `ollama pull llama3.2:3b`
4. NPCs will automatically use AI for responses

## Memory System

NPCs maintain memories of interactions:
- **Event-based**: Records significant events
- **Emotional Impact**: Tracks positive/negative experiences  
- **Importance Levels**: 1-10 scale affects memory retention
- **Automatic Cleanup**: Keeps only most important/recent memories

## Relationship System

NPC relationships evolve through interactions:
- **Stranger** → **Acquaintance** → **Friend** → **Ally**
- **Enemy** relationships affect dialogue tone
- Mood changes based on relationship improvements

## Testing

Run NPC system tests:
```bash
python -m pytest tests/test_npc_system.py -v
```

## Examples

### Basic Interaction
```
> talk
Persone presenti:
- Guardiano del Bosco
Usa 'talk <nome>' per iniziare una conversazione.

> talk Guardiano del Bosco
Guardiano del Bosco: Salve! Non ti ho mai visto da queste parti.

> say Conosci dei segreti del bosco?
Guardiano del Bosco: Il bosco nasconde molti segreti. Solo chi rispetta la natura può scoprirli davvero.

> say arrivederci
Guardiano del Bosco: Buona giornata!
```

### Adding New NPCs

1. Create JSON file in `assets/npcs/`
2. Define character with required fields  
3. Add special knowledge for contextual responses
4. Test with `talk` command

The NPC system integrates seamlessly with the existing game state, events, and save/load functionality.