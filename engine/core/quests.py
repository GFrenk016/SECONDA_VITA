"""Quest system for micro-quests and story progression.

This module handles quest progression, step tracking, and rewards.
"""

from __future__ import annotations
from dataclasses import dataclass, field 
from typing import Dict, List, Any, Optional
from enum import Enum
from .state import GameState
from .registry import ContentRegistry


class QuestStatus(Enum):
    """Quest status values."""
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QuestStep:
    """A single step in a quest."""
    id: str
    name: str
    description: str
    day_description: str = ""  # Description variant for day time
    night_description: str = ""  # Description variant for night time
    completion_conditions: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[Dict[str, Any]] = field(default_factory=list)
    auto_complete: bool = False  # Auto-complete when conditions are met
    
    def get_description(self, is_night: bool = False) -> str:
        """Get appropriate description based on time of day."""
        if is_night and self.night_description:
            return self.night_description
        elif not is_night and self.day_description:
            return self.day_description
        return self.description


@dataclass
class Quest:
    """A quest with multiple steps."""
    id: str
    name: str
    description: str 
    steps: List[QuestStep] = field(default_factory=list)
    status: QuestStatus = QuestStatus.NOT_STARTED
    current_step: int = 0
    started_at: int = 0  # Game minutes when started
    completed_at: int = 0  # Game minutes when completed
    
    def get_current_step(self) -> Optional[QuestStep]:
        """Get the currently active step."""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
    
    def is_step_complete(self, step_index: int, state: GameState) -> bool:
        """Check if a specific step is complete."""
        if step_index >= len(self.steps):
            return False
        
        step = self.steps[step_index]
        for condition in step.completion_conditions:
            if not self._check_condition(condition, state):
                return False
        return True
    
    def _check_condition(self, condition: Dict[str, Any], state: GameState) -> bool:
        """Check if a condition is met."""
        cond_type = condition.get("type")
        
        if cond_type == "flag":
            flag_name = condition.get("flag")
            expected = condition.get("value", True)
            return state.flags.get(flag_name, False) == expected
        
        elif cond_type == "item_count":
            # For simplified quest, check flags instead of complex inventory
            item_id = condition.get("item")
            if item_id == "cloth":
                # Check if player has cloth via flag or simple inventory access
                return state.flags.get("has_cloth_for_quest", False)
            elif item_id == "bandage":
                return state.flags.get("crafted_first_bandage", False)
            return False
        
        elif cond_type == "location":
            expected_location = condition.get("location")
            return state.location_key() == expected_location
        
        elif cond_type == "npc_relationship":
            # Would need NPC registry to check this
            return True  # Placeholder
            
        return False


class QuestManager:
    """Manages all quests in the game."""
    
    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self._initialize_default_quests()
    
    def _initialize_default_quests(self):
        """Initialize the default micro-quest."""
        # Create "Il coltello e la pioggia" micro-quest
        knife_rain_quest = Quest(
            id="knife_and_rain",
            name="Il coltello e la pioggia",
            description="Una breve avventura che ti porterà a creare un bendaggio, affrontare un vagante e potenzialmente aiutare un NPC in difficoltà."
        )
        
        # Step 1: Find rags
        step1 = QuestStep(
            id="find_rags",
            name="Trova Stracci",
            description="Cerca degli stracci che possano essere utili per creare un bendaggio.",
            day_description="La luce del giorno potrebbe aiutarti a individuare stracci tra la vegetazione.",
            night_description="Nell'oscurità, dovrai cercare con più attenzione tra gli oggetti abbandonati.",
            completion_conditions=[
                {"type": "flag", "flag": "has_cloth_for_quest", "value": True}
            ],
            auto_complete=True
        )
        
        # Step 2: Craft bandage
        step2 = QuestStep(
            id="craft_bandage", 
            name="Crea Bendaggio",
            description="Usa gli stracci per creare un bendaggio che potrebbe tornare utile.",
            day_description="Con la luce diurna, lavorare con precisione è più facile.",
            night_description="Anche al buio, le tue mani esperte riescono a intrecciare i tessuti.",
            completion_conditions=[
                {"type": "flag", "flag": "crafted_first_bandage", "value": True}
            ],
            rewards=[
                {"type": "flag", "flag": "crafted_first_bandage", "value": True}
            ],
            auto_complete=True
        )
        
        # Step 3: Encounter wanderer
        step3 = QuestStep(
            id="fight_wanderer",
            name="Scontro con il Vagante", 
            description="Un vagante ferito appare sul tuo cammino. Devi decidere come gestire la situazione.",
            day_description="La luce del giorno rivela le ferite del vagante e la sua disperazione.",
            night_description="Nel buio, solo i gemiti del vagante rivelano la sua presenza e il suo dolore.",
            completion_conditions=[
                {"type": "flag", "flag": "encountered_wounded_wanderer", "value": True}
            ],
            auto_complete=False
        )
        
        # Step 4: NPC dialogue and choice
        step4 = QuestStep(
            id="npc_help_choice",
            name="Scelta dell'Aiuto",
            description="Dopo lo scontro, un NPC ti chiede aiuto. La tua scelta durante il QTE determinerà l'esito.",
            day_description="La luce del giorno illumina lo sguardo speranzoso dell'NPC che cerca il tuo aiuto.",
            night_description="Nell'oscurità, solo la voce tremula dell'NPC tradisce la sua vulnerabilità.",
            completion_conditions=[
                {"type": "flag", "flag": "knife_rain_quest_completed", "value": True}
            ],
            rewards=[
                {"type": "morale", "amount": 10},
                {"type": "flag", "flag": "completed_first_microquest", "value": True}
            ],
            auto_complete=True
        )
        
        knife_rain_quest.steps = [step1, step2, step3, step4]
        self.quests["knife_and_rain"] = knife_rain_quest
    
    def start_quest(self, quest_id: str, state: GameState) -> bool:
        """Start a quest if not already started."""
        if quest_id not in self.quests:
            return False
        
        quest = self.quests[quest_id]
        if quest.status != QuestStatus.NOT_STARTED:
            return False
        
        quest.status = QuestStatus.ACTIVE
        quest.started_at = state.day_count * 24 * 60 + state.time_minutes
        quest.current_step = 0
        
        # Set quest flag
        state.flags[f"quest_{quest_id}_active"] = True
        
        return True
    
    def update_quest_progress(self, state: GameState) -> List[str]:
        """Update all active quests and return progression messages."""
        messages = []
        
        for quest in self.quests.values():
            if quest.status != QuestStatus.ACTIVE:
                continue
            
            # Check current step completion
            current_step = quest.get_current_step()
            if current_step and quest.is_step_complete(quest.current_step, state):
                
                # Apply step rewards
                self._apply_step_rewards(current_step, state)
                
                # Move to next step
                quest.current_step += 1
                
                if quest.current_step >= len(quest.steps):
                    # Quest completed
                    quest.status = QuestStatus.COMPLETED
                    quest.completed_at = state.day_count * 24 * 60 + state.time_minutes
                    state.flags[f"quest_{quest.id}_completed"] = True
                    state.flags[f"quest_{quest.id}_active"] = False
                    messages.append(f"*** Quest Completata: {quest.name} ***")
                else:
                    # Next step
                    next_step = quest.get_current_step()
                    if next_step:
                        is_night = state.daytime == "notte"
                        step_desc = next_step.get_description(is_night)
                        messages.append(f">> {next_step.name}: {step_desc}")
        
        return messages
    
    def _apply_step_rewards(self, step: QuestStep, state: GameState):
        """Apply rewards from a completed step."""
        for reward in step.rewards:
            reward_type = reward.get("type")
            
            if reward_type == "flag": 
                flag_name = reward.get("flag")
                flag_value = reward.get("value", True)
                state.flags[flag_name] = flag_value
            
            elif reward_type == "morale":
                amount = reward.get("amount", 0)
                current_morale = state.flags.get("morale", 50)
                state.flags["morale"] = min(100, current_morale + amount)
            
            elif reward_type == "item":
                item_id = reward.get("item")
                quantity = reward.get("quantity", 1)
                current = state.inventory.get(item_id, 0)
                state.inventory[item_id] = current + quantity
    
    def get_active_quests(self) -> List[Quest]:
        """Get all currently active quests."""
        return [q for q in self.quests.values() if q.status == QuestStatus.ACTIVE]
    
    def get_quest_journal(self, state: GameState) -> List[str]:
        """Get formatted quest journal entries."""
        lines = []
        active_quests = self.get_active_quests()
        
        if not active_quests:
            lines.append("Nessuna missione attiva.")
            return lines
        
        lines.append("=== Diario delle Missioni ===")
        
        for quest in active_quests:
            lines.append(f"\n{quest.name}")
            lines.append("-" * len(quest.name))
            
            current_step = quest.get_current_step()
            if current_step:
                is_night = state.daytime == "notte"
                step_desc = current_step.get_description(is_night)
                lines.append(f"Obiettivo attuale: {step_desc}")
            
            # Show progress
            progress = f"Passo {quest.current_step + 1} di {len(quest.steps)}"
            lines.append(f"Progresso: {progress}")
        
        return lines


# Global quest manager instance
quest_manager = QuestManager()