"""AI Dialogue Engine for NPCs.

This module handles dialogue generation using AI (initially mock, later Ollama integration).
"""

from __future__ import annotations
import random
import json
from typing import Dict, List, Any, Optional
from .models import NPC, DialogueContext, NPCRelation, NPCState
from config import (
    get_ollama_enabled,
    get_ollama_base_url,
    get_ollama_model,
    get_ollama_timeout,
    get_ollama_temperature,
    get_ollama_max_tokens,
)


class OllamaClient:
    """Simple Ollama HTTP client for AI dialogue generation."""
    
    def __init__(self, base_url: str, timeout: float):
        self.base_url = base_url
        self.timeout = timeout
        self.available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if Ollama is running and available."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=min(2, self.timeout))
            self.available = response.status_code == 200
        except Exception:
            self.available = False
    
    def generate_response(self, prompt: str, model: str, temperature: float, max_tokens: int) -> Optional[str]:
        """Generate response using Ollama."""
        if not self.available:
            return None
        
        try:
            import requests
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": float(temperature),
                    "max_tokens": int(max_tokens),
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
        except Exception as e:
            print(f"Ollama error: {e}")
        
        return None


class AIDialogueEngine:
    """AI-powered dialogue generation for NPCs."""
    
    def __init__(self):
        # Read config
        self._enabled = get_ollama_enabled()
        self._base_url = get_ollama_base_url()
        self._model = get_ollama_model()
        self._timeout = get_ollama_timeout()
        self._temperature = get_ollama_temperature()
        self._max_tokens = get_ollama_max_tokens()

        # Initialize client if enabled
        self.ollama_client = None
        self.ollama_available = False
        if self._enabled:
            try:
                self.ollama_client = OllamaClient(self._base_url, self._timeout)
                self.ollama_available = self.ollama_client.available
            except Exception:
                self.ollama_available = False
        self._fallback_responses = self._init_fallback_responses()
        
        # Log lightweight, avoid noisy tests
        if self.ollama_available:
            print("-- Ollama AI disponibile per dialoghi --")
        elif self._enabled:
            print("-- Ollama abilitato ma non raggiungibile, uso fallback --")
    
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
            ai_response = self._generate_ai_response(npc, player_input, context)
            if ai_response:
                return ai_response
        
        # Fallback to predefined responses
        return self._generate_fallback_response(npc, player_input, context)
    
    def _generate_ai_response(self, npc: NPC, player_input: str, context: DialogueContext) -> Optional[str]:
        """Generate response using Ollama AI."""
        # Build comprehensive prompt for AI
        prompt = self._build_ai_prompt(npc, player_input, context)
        
        try:
            response = self.ollama_client.generate_response(
                prompt,
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            if response and len(response.strip()) > 0:
                # Clean up and validate response
                response = response.strip()
                # Remove quotes if AI wrapped response in quotes
                if response.startswith('"') and response.endswith('"'):
                    response = response[1:-1]
                return response
        except Exception as e:
            print(f"AI generation error: {e}")
        
        return None
    
    def _build_ai_prompt(self, npc: NPC, player_input: str, context: DialogueContext) -> str:
        """Build comprehensive prompt for AI dialogue generation."""
        
        # Character context
        personality_traits = ", ".join(npc.personality.get("traits", []))
        speech_patterns = ", ".join(npc.personality.get("speech_patterns", []))
        
        # Relationship context
        relationship_context = {
            NPCRelation.STRANGER: "Non conosci questo personaggio",
            NPCRelation.ACQUAINTANCE: "Hai già incontrato questo personaggio",
            NPCRelation.FRIEND: "Siete amici",
            NPCRelation.ALLY: "Siete alleati",
            NPCRelation.ENEMY: "Siete nemici",
        }.get(npc.relationship, "Relazione neutra")
        
        # Mood context
        mood_desc = "neutrale"
        if npc.mood > 0.3:
            mood_desc = "positivo e amichevole"
        elif npc.mood < -0.3:
            mood_desc = "negativo e scontroso"
        
        # Recent conversation
        recent_history = ""
        if context.conversation_history:
            recent_turns = context.conversation_history[-3:]  # Last 3 turns
            history_lines = []
            for turn in recent_turns:
                history_lines.append(f"Giocatore: {turn['player']}")
                history_lines.append(f"{npc.name}: {turn['npc']}")
            recent_history = "\n".join(history_lines)
        
        prompt = f"""Sei {npc.name}, un personaggio in un gioco di ruolo testuale ambientato in un bosco misterioso.

CONTESTO PERSONAGGIO:
- Nome: {npc.name}
- Descrizione: {npc.description}
- Background: {npc.background}
- Personalità: {personality_traits}
- Modi di parlare: {speech_patterns}
- Umore attuale: {mood_desc}
- Relazione con il giocatore: {relationship_context}

SITUAZIONE ATTUALE:
- Luogo: {context.current_location}
- Ora del giorno: {context.game_time}
- Meteo: {context.weather}

CONVERSAZIONE RECENTE:
{recent_history}

CONOSCENZE SPECIALI:
{json.dumps(npc.special_knowledge, indent=2, ensure_ascii=False) if npc.special_knowledge else "Nessuna conoscenza speciale"}

Il giocatore ti dice: "{player_input}"

Rispondi come {npc.name} mantenendo il personaggio coerente. Rispondi in italiano, in modo naturale e conciso (massimo 2-3 frasi). Non usare asterischi o azioni tra parentesi, solo il dialogo diretto."""

        return prompt
    
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
        # Check special knowledge first (more specific)
        for knowledge_key in npc.special_knowledge:
            if knowledge_key.lower() in player_input:
                knowledge = npc.special_knowledge[knowledge_key]
                if isinstance(knowledge, str):
                    return knowledge
                elif isinstance(knowledge, list):
                    return random.choice(knowledge)
        
        # Check NPC's conversation topics
        for topic in npc.conversation_topics:
            if topic.lower() in player_input:
                # Generate topic-specific response
                return self._generate_topic_response(npc, topic, context)
        
        # Handle common questions based on NPC type
        if any(word in player_input for word in ['chi sei', 'chi', 'nome']):
            return f"Sono {npc.name}. {npc.description}"
        
        if any(word in player_input for word in ['cosa fai', 'lavoro', 'occupazione']):
            if npc.merchant:
                return "Sono un mercante. Vendo oggetti utili ai viaggiatori."
            elif npc.quest_giver:
                return "Aiuto i viaggiatori che attraversano questi luoghi. Potresti essermi utile."
            else:
                return "Mi occupo di diverse cose qui nel bosco."
        
        if any(word in player_input for word in ['tempo', 'quanto tempo', 'da quanto']):
            return "Vivo qui da molto tempo ormai. Ho visto molte cose."
        
        if any(word in player_input for word in ['aiuto', 'aiutare', 'bisogno']):
            if npc.relationship in [NPCRelation.FRIEND, NPCRelation.ALLY]:
                return "Naturalmente, sarò felice di aiutarti come posso."
            elif npc.relationship == NPCRelation.ENEMY:
                return "Non penso proprio di volerti aiutare."
            else:
                return "Dipende da cosa ti serve. Dimmi di più."
        
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
        # Update last interaction time (store as integer minutes when possible)
        try:
            npc.last_interaction = int(context.game_time)
        except Exception:
            npc.last_interaction = 0
        
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
                timestamp=int(context.game_time) if isinstance(context.game_time, (int, str)) and str(context.game_time).isdigit() else 0,
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
        
        # Keep only recent conversation history (8 turns as per requirements)
        if len(context.conversation_history) > 8:
            context.conversation_history = context.conversation_history[-8:]
        
        # Process keyword-based trust/affinity changes
        self._process_keyword_affinity(npc, player_input)
        
        # Check if conversation should end
        should_end = any(word in player_input.lower() for word in ['arrivederci', 'addio', 'bye', 'fine', 'end'])
        
        return {
            'lines': [f"{npc.name}: {response}"],
            'conversation_active': not should_end,
            'hints': [] if should_end else [f"Continua a parlare con {npc.name} o scrivi 'end' per terminare."]
        }
    
    def _process_keyword_affinity(self, npc: NPC, player_input: str):
        """Process keyword-based trust and affinity changes."""
        input_lower = player_input.lower()
        
        # Kindness keywords - increase mood and trust
        kindness_words = ['grazie', 'prego', 'scusa', 'mi dispiace', 'gentile', 'cortese', 'aiuto', 'posso aiutare']
        if any(word in input_lower for word in kindness_words):
            npc.adjust_mood(0.05)
            if hasattr(npc, 'trust'):
                npc.trust = min(1.0, getattr(npc, 'trust', 0.0) + 0.1)
        
        # Threat keywords - decrease mood and trust
        threat_words = ['minaccia', 'uccidere', 'ammazzare', 'morte', 'nemico', 'guerra', 'attacco']
        if any(word in input_lower for word in threat_words):
            npc.adjust_mood(-0.15)
            if hasattr(npc, 'trust'):
                npc.trust = max(-1.0, getattr(npc, 'trust', 0.0) - 0.2)
        
        # Care keywords - increase mood moderately
        care_words = ['cura', 'preoccupo', 'bene', 'salute', 'stai bene', 'tutto ok', 'va tutto bene']
        if any(word in input_lower for word in care_words):
            npc.adjust_mood(0.08)
            if hasattr(npc, 'trust'):
                npc.trust = min(1.0, getattr(npc, 'trust', 0.0) + 0.05)
    
    def get_npc_profile(self, npc: NPC, context: DialogueContext) -> Dict[str, Any]:
        """Get detailed NPC profile information."""
        # Relationship status description
        relationship_desc = {
            NPCRelation.STRANGER: "Non vi conoscete",
            NPCRelation.ACQUAINTANCE: "Vi siete già incontrati",
            NPCRelation.FRIEND: "Siete amici",
            NPCRelation.ALLY: "Siete alleati",
            NPCRelation.ENEMY: "Siete nemici",
            NPCRelation.LOVER: "Avete una relazione romantica",
            NPCRelation.FAMILY: "Siete parenti"
        }.get(npc.relationship, "Relazione sconosciuta")
        
        # Mood description
        if npc.mood > 0.5:
            mood_desc = "molto positivo"
        elif npc.mood > 0.2:
            mood_desc = "positivo"
        elif npc.mood > -0.2:
            mood_desc = "neutrale"
        elif npc.mood > -0.5:
            mood_desc = "negativo"
        else:
            mood_desc = "molto negativo"
        
        # Trust level if available
        trust_desc = ""
        if hasattr(npc, 'trust'):
            trust_val = getattr(npc, 'trust', 0.0)
            if trust_val > 0.5:
                trust_desc = " - Ti considera fidato"
            elif trust_val < -0.5:
                trust_desc = " - Non si fida di te"
        
        lines = [
            f"=== Profilo di {npc.name} ===",
            f"Descrizione: {npc.description}",
            f"Stato attuale: {npc.current_state.value}",
            f"Umore: {mood_desc}{trust_desc}",
            f"Relazione: {relationship_desc}",
            f"Interazioni precedenti: {len(npc.memories)}"
        ]
        
        if npc.conversation_topics:
            lines.append(f"Argomenti di interesse: {', '.join(npc.conversation_topics)}")
        
        if npc.special_knowledge:
            lines.append(f"Conoscenze speciali: {len(npc.special_knowledge)} argomenti")
        
        return {
            'lines': lines,
            'conversation_active': True,
            'hints': ["Continua la conversazione o chiedi informazioni specifiche."]
        }