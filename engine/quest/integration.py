"""Integration layer between new quest engine and existing game systems.

This module provides a bridge between the new quest engine and the existing
game systems, allowing for gradual migration.
"""

from typing import Optional
from ..core.state import GameState
from .runtime import QuestLog
from .loader import load_main_story
from .generator import generate_side_quests

class QuestEngineIntegration:
    """Integration layer for the new quest engine."""
    
    def __init__(self, gs: GameState):
        """Initialize the quest engine integration.
        
        Args:
            gs: GameState object
        """
        self.gs = gs
        self.quest_log = QuestLog(gs)
        
        # Initialize journal history if not present
        if not hasattr(gs, 'journal_history'):
            gs.journal_history = []
        
        # Initialize relationships if not present
        if not hasattr(gs, 'relationships') or gs.relationships is None:
            gs.relationships = {}
    
    def load_main_story(self, story_file: str = "game/story/main_story.json") -> bool:
        """Load main story quests.
        
        Args:
            story_file: Path to main story file
            
        Returns:
            True if loaded successfully
        """
        try:
            quests = load_main_story(story_file)
            for quest in quests:
                self.quest_log.register(quest)
            return True
        except Exception as e:
            print(f"Error loading main story: {e}")
            return False
    
    def generate_side_quests(
        self, 
        templates_file: str = "assets/quest_templates.json",
        max_quests: int = 3
    ) -> int:
        """Generate side quests from templates.
        
        Args:
            templates_file: Path to templates file
            max_quests: Maximum number of quests to generate
            
        Returns:
            Number of quests generated
        """
        try:
            # Use a seed based on game state for determinism
            seed = self.gs.day_count * 1000 + self.gs.time_minutes
            quests = generate_side_quests(templates_file, self.gs, max_quests, seed)
            
            for quest in quests:
                self.quest_log.register(quest)
                
            return len(quests)
        except Exception as e:
            print(f"Error generating side quests: {e}")
            return 0
    
    def tick(self) -> list:
        """Process quest tick and return progression messages.
        
        Returns:
            List of progression messages
        """
        return self.quest_log.tick()
    
    def start_quest(self, quest_id: str) -> bool:
        """Start a quest by ID.
        
        Args:
            quest_id: ID of quest to start
            
        Returns:
            True if started successfully
        """
        return self.quest_log.start(quest_id)
    
    def get_active_quests(self) -> list:
        """Get list of active quests.
        
        Returns:
            List of active Quest objects
        """
        return self.quest_log.active()
    
    def get_tracked_quest(self):
        """Get currently tracked quest.
        
        Returns:
            Currently tracked Quest object or None
        """
        return self.quest_log.get_tracked_quest()
    
    def get_quest_hints(self) -> list:
        """Get hints for the currently tracked quest.
        
        Returns:
            List of hint strings
        """
        tracked = self.get_tracked_quest()
        if not tracked or tracked.state != "IN_PROGRESS":
            return []
        
        current_step = tracked.get_current_step()
        if not current_step:
            return []
        
        hints = []
        
        # Add step description as primary hint
        hints.append(f"Obiettivo: {current_step.description}")
        
        # Add location hints if step has location requirements
        for condition in current_step.complete_conditions:
            if condition.op == "in_location":
                args = condition.args
                if "micro" in args:
                    hints.append(f"Vai a: {args['micro']}")
                elif "macro" in args:
                    hints.append(f"Raggiungi l'area: {args['macro']}")
            elif condition.op == "has_item":
                args = condition.args
                item_id = args.get("id", "unknown")
                qty = args.get("qty", 1)
                hints.append(f"Raccogli: {qty}x {item_id}")
        
        return hints
    
    def update_legacy_quest_manager(self, legacy_manager):
        """Update legacy quest manager with new system progress.
        
        This method can be used during transition to keep the old system
        in sync with the new one.
        
        Args:
            legacy_manager: The legacy QuestManager instance
        """
        # Example integration - set flags based on new quest progress
        for quest in self.quest_log.quests.values():
            if quest.state == "COMPLETED":
                # Set legacy completion flag
                flag_name = f"quest_{quest.id}_completed"
                self.gs.flags[flag_name] = True
            elif quest.state == "IN_PROGRESS":
                # Set legacy active flag
                flag_name = f"quest_{quest.id}_active"
                self.gs.flags[flag_name] = True

def migrate_from_legacy(gs: GameState, legacy_manager) -> QuestEngineIntegration:
    """Migrate from legacy quest system to new quest engine.
    
    Args:
        gs: GameState object
        legacy_manager: Legacy QuestManager instance
        
    Returns:
        New QuestEngineIntegration instance
    """
    integration = QuestEngineIntegration(gs)
    
    # Migrate quest states from flags
    for flag_name, flag_value in gs.flags.items():
        if flag_name.startswith("quest_") and flag_name.endswith("_completed") and flag_value:
            quest_id = flag_name[6:-10]  # Remove "quest_" and "_completed"
            quest = integration.quest_log.get_quest(quest_id)
            if quest:
                quest.state = "COMPLETED"
        elif flag_name.startswith("quest_") and flag_name.endswith("_active") and flag_value:
            quest_id = flag_name[6:-7]  # Remove "quest_" and "_active"
            quest = integration.quest_log.get_quest(quest_id)
            if quest:
                quest.state = "IN_PROGRESS"
    
    return integration

# Global integration instance - to be initialized when game starts
quest_engine: Optional[QuestEngineIntegration] = None

def initialize_quest_engine(gs: GameState) -> QuestEngineIntegration:
    """Initialize the global quest engine integration.
    
    Args:
        gs: GameState object
        
    Returns:
        QuestEngineIntegration instance
    """
    global quest_engine
    quest_engine = QuestEngineIntegration(gs)
    
    # Load main story by default
    quest_engine.load_main_story()
    
    return quest_engine

def get_quest_engine() -> Optional[QuestEngineIntegration]:
    """Get the global quest engine integration instance.
    
    Returns:
        QuestEngineIntegration instance or None if not initialized
    """
    return quest_engine