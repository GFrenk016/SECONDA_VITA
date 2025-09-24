"""AI Dialogue Engine for NPCs.

This module handles dialogue generation using AI (initially mock, later Ollama integration).
"""

from __future__ import annotations
import random
from typing import Dict, List, Any, Optional
from .models import NPC, DialogueContext, NPCRelation, NPCState


class AIDialogueEngine:
    """AI-powered dialogue generation for NPCs."""
    
    def __init__(self):
        self.ollama_available = False  # Will be set to True when Ollama is integrated
        self._fallback_responses = self._init_fallback_responses()
    
    def _init_fallback_responses(self) -> Dict[str, List[str]]:
        """Initialize fallback responses for when AI is not available."""
        return {
            'greeting': [
                "Ciao, straniero. Cosa ti porta qui?",
                "Salve! Non ti ho mai visto da queste parti.",
                "Benvenuto. Posso aiutarti con qualcosa?",
            ],
            'friendly_greeting': [
                "È bello rivederti! Come stai?",
                "Ciao amico! Che cosa ti porta qui oggi?",
                "Salve! Sempre un piacere vederti.",
            ],
            'hostile_greeting': [
                "Tu di nuovo... Cosa vuoi?",
                "Non ho tempo per te.",
                "Faresti meglio a non disturbarmi.",
            ],
            'goodbye': [
                "Arrivederci, che la fortuna ti accompagni.",
                "Buona giornata!",
                "Ci vediamo presto.",
            ],
            'unknown_topic': [
                "Non so nulla a riguardo.",
                "Mi dispiace, non posso aiutarti con questo.",
                "Non è qualcosa di cui mi occupo.",
            ],
            'busy': [
                "Scusa, sono molto occupato ora.",
                "Torna più tardi, per favore.",
                "Non posso parlare adesso.",
            ],
            'afraid': [
                "Non... non posso parlare ora.",
                "Vai via, per favore!",
                "Ho paura... lasciami in pace.",
            ]
        }
    
    def generate_response(self, npc: NPC, player_input: str, context: DialogueContext) -> str:
        """Generate NPC response to player input."""
        if self.ollama_available:
            return self._generate_ai_response(npc, player_input, context)
        else:
            return self._generate_fallback_response(npc, player_input, context)
    
    def _generate_ai_response(self, npc: NPC, player_input: str, context: DialogueContext) -> str:
        """Generate response using Ollama AI (future implementation)."""
        # TODO: Implement Ollama integration
        # For now, return fallback
        return self._generate_fallback_response(npc, player_input, context)
    
    def _generate_fallback_response(self, npc: NPC, player_input: str, context: DialogueContext) -> str:
        """Generate fallback response based on NPC state and simple rules."""
        player_input_lower = player_input.lower()
        
        # Handle special states
        if npc.current_state == NPCState.BUSY:
            return random.choice(self._fallback_responses['busy'])
        elif npc.current_state == NPCState.AFRAID:
            return random.choice(self._fallback_responses['afraid'])
        elif npc.current_state == NPCState.SLEEPING:
            return f"{npc.name} sta dormendo e non risponde."
        
        # Handle greetings
        if any(word in player_input_lower for word in ['ciao', 'salve', 'saluti', 'buongiorno', 'buonasera']):
            if npc.relationship == NPCRelation.FRIEND or npc.relationship == NPCRelation.ALLY:
                return random.choice(self._fallback_responses['friendly_greeting'])
            elif npc.relationship == NPCRelation.ENEMY or npc.current_state == NPCState.HOSTILE:
                return random.choice(self._fallback_responses['hostile_greeting'])
            else:
                return random.choice(self._fallback_responses['greeting'])
        
        # Handle goodbyes
        if any(word in player_input_lower for word in ['arrivederci', 'addio', 'ciao', 'bye']):
            return random.choice(self._fallback_responses['goodbye'])
        
        # Handle topic-specific responses
        response = self._handle_topic_response(npc, player_input_lower, context)
        if response:
            return response
        
        # Default response
        return random.choice(self._fallback_responses['unknown_topic'])
    
    def _handle_topic_response(self, npc: NPC, player_input: str, context: DialogueContext) -> Optional[str]:
        """Handle responses to specific topics."""
        # Check NPC's conversation topics
        for topic in npc.conversation_topics:
            if topic.lower() in player_input:
                # Generate topic-specific response
                return self._generate_topic_response(npc, topic, context)
        
        # Check special knowledge
        for knowledge_key in npc.special_knowledge:
            if knowledge_key.lower() in player_input:
                knowledge = npc.special_knowledge[knowledge_key]
                if isinstance(knowledge, str):
                    return knowledge
                elif isinstance(knowledge, list):
                    return random.choice(knowledge)
        
        return None
    
    def _generate_topic_response(self, npc: NPC, topic: str, context: DialogueContext) -> str:
        """Generate response about a specific topic."""
        # Simple topic responses based on NPC personality
        if npc.mood > 0.5:
            return f"Ah, {topic}! Mi fa sempre piacere parlarne."
        elif npc.mood < -0.5:
            return f"{topic}... non è il mio argomento preferito."
        else:
            return f"Cosa vuoi sapere su {topic}?"
    
    def start_conversation(self, npc: NPC, context: DialogueContext) -> Dict[str, Any]:
        """Start a conversation with an NPC."""
        # Update last interaction time
        npc.last_interaction = context.game_time if isinstance(context.game_time, int) else 0
        
        # Generate initial greeting
        greeting = self._generate_fallback_response(npc, "ciao", context)
        
        # Add memory of interaction
        if hasattr(npc, 'add_memory'):
            npc.add_memory(
                event="conversation_started",
                timestamp=npc.last_interaction,
                context={
                    'location': context.current_location,
                    'weather': context.weather,
                    'player_initiated': True
                },
                importance=3
            )
        
        return {
            'lines': [f"{npc.name}: {greeting}"],
            'npc_id': npc.id,
            'conversation_active': True,
            'hints': [f"Puoi parlare con {npc.name} digitando quello che vuoi dire."]
        }
    
    def end_conversation(self, npc: NPC, context: DialogueContext) -> Dict[str, Any]:
        """End a conversation with an NPC."""
        goodbye = self._generate_fallback_response(npc, "arrivederci", context)
        
        # Add memory of conversation end
        if hasattr(npc, 'add_memory'):
            npc.add_memory(
                event="conversation_ended",
                timestamp=context.game_time if isinstance(context.game_time, int) else 0,
                context={'location': context.current_location},
                importance=2
            )
        
        return {
            'lines': [f"{npc.name}: {goodbye}"],
            'conversation_active': False,
            'hints': []
        }
    
    def process_dialogue_turn(self, npc: NPC, player_input: str, context: DialogueContext) -> Dict[str, Any]:
        """Process a dialogue turn between player and NPC."""
        response = self.generate_response(npc, player_input, context)
        
        # Add to conversation history
        context.conversation_history.append({
            'player': player_input,
            'npc': response
        })
        
        # Keep only recent conversation history
        if len(context.conversation_history) > 10:
            context.conversation_history = context.conversation_history[-10:]
        
        # Check if conversation should end
        should_end = any(word in player_input.lower() for word in ['arrivederci', 'addio', 'bye', 'fine'])
        
        return {
            'lines': [f"{npc.name}: {response}"],
            'conversation_active': not should_end,
            'hints': [] if should_end else [f"Continua a parlare con {npc.name} o scrivi 'arrivederci' per terminare."]
        }