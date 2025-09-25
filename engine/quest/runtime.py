"""Quest runtime management system.

This module manages the active quest log and handles quest progression ticks.
"""

from typing import Dict, List, Optional
from .model import Quest
from .fsm import start_quest, advance, fail_if_needed, unblock_if_possible

class QuestLog:
    """Manages the player's active quest log and progression."""
    
    def __init__(self, gs):
        """Initialize quest log with game state reference.
        
        Args:
            gs: GameState object
        """
        self.gs = gs
        self.quests: Dict[str, Quest] = {}
        self.tracked_quest_id: Optional[str] = None  # Quest being actively tracked
    
    def register(self, quest: Quest) -> None:
        """Register a quest in the log.
        
        Args:
            quest: Quest to register
        """
        self.quests[quest.id] = quest
    
    def start(self, quest_id: str) -> bool:
        """Start a quest by ID.
        
        Args:
            quest_id: ID of quest to start
            
        Returns:
            True if quest was started successfully
        """
        quest = self.quests.get(quest_id)
        if not quest:
            return False
        
        return start_quest(quest, self.gs)
    
    def abandon(self, quest_id: str) -> bool:
        """Abandon a quest (only side quests can be abandoned).
        
        Args:
            quest_id: ID of quest to abandon
            
        Returns:
            True if quest was abandoned successfully
        """
        quest = self.quests.get(quest_id)
        if not quest:
            return False
        
        if quest.priority == "main":
            return False  # Cannot abandon main quests
        
        if quest.state in ["COMPLETED", "FAILED", "ABANDONED"]:
            return False
        
        quest.state = "ABANDONED"
        return True
    
    def track(self, quest_id: str) -> bool:
        """Set a quest as actively tracked.
        
        Args:
            quest_id: ID of quest to track
            
        Returns:
            True if quest is now being tracked
        """
        quest = self.quests.get(quest_id)
        if not quest:
            return False
        
        if quest.state not in ["IN_PROGRESS", "BLOCKED"]:
            return False
        
        self.tracked_quest_id = quest_id
        return True
    
    def untrack(self) -> None:
        """Stop tracking the current quest."""
        self.tracked_quest_id = None
    
    def get_tracked_quest(self) -> Optional[Quest]:
        """Get the currently tracked quest.
        
        Returns:
            Currently tracked quest or None
        """
        if self.tracked_quest_id:
            return self.quests.get(self.tracked_quest_id)
        return None
    
    def tick(self) -> List[str]:
        """Process quest progression tick.
        
        Called regularly to check for quest advancement and failures.
        
        Returns:
            List of progression messages for display
        """
        messages = []
        
        for quest in self.quests.values():
            # Skip inactive quests
            if quest.state in ["NOT_STARTED", "COMPLETED", "FAILED", "ABANDONED"]:
                continue
            
            # Check for quest failure first
            if fail_if_needed(quest, self.gs):
                messages.append(f"*** Quest FALLITA: {quest.title} ***")
                continue
            
            # Try to unblock blocked quests
            if quest.state == "BLOCKED":
                if unblock_if_possible(quest, self.gs):
                    current_step = quest.get_current_step()
                    if current_step:
                        messages.append(f">> {quest.title}: {current_step.title}")
                continue
            
            # Check for step advancement
            if quest.state == "IN_PROGRESS":
                old_step_index = quest.current_step_index
                advance(quest, self.gs)
                
                if quest.state == "COMPLETED":
                    messages.append(f"*** Quest COMPLETATA: {quest.title} ***")
                elif quest.current_step_index > old_step_index:
                    # Advanced to next step
                    current_step = quest.get_current_step()
                    if current_step:
                        messages.append(f">> {quest.title}: {current_step.title}")
                elif quest.state == "BLOCKED":
                    messages.append(f">> {quest.title}: Bloccata - requisiti non soddisfatti")
        
        return messages
    
    def active(self) -> List[Quest]:
        """Get all active quests (in progress or blocked).
        
        Returns:
            List of active quests
        """
        return [q for q in self.quests.values() if q.state in ["IN_PROGRESS", "BLOCKED"]]
    
    def by_priority(self, priority: str) -> List[Quest]:
        """Get quests by priority level.
        
        Args:
            priority: "main" or "side"
            
        Returns:
            List of quests with specified priority
        """
        return [q for q in self.quests.values() if q.priority == priority]
    
    def completed(self) -> List[Quest]:
        """Get all completed quests.
        
        Returns:
            List of completed quests
        """
        return [q for q in self.quests.values() if q.state == "COMPLETED"]
    
    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get quest by ID.
        
        Args:
            quest_id: Quest ID to look up
            
        Returns:
            Quest object or None if not found
        """
        return self.quests.get(quest_id)
    
    def get_journal_entries(self) -> List[str]:
        """Get formatted journal entries for display.
        
        Returns:
            List of formatted journal lines
        """
        lines = []
        active_quests = self.active()
        
        if not active_quests:
            lines.append("Nessuna missione attiva.")
            return lines
        
        lines.append("=== Diario delle Missioni ===")
        
        # Show main quests first
        main_quests = [q for q in active_quests if q.priority == "main"]
        side_quests = [q for q in active_quests if q.priority == "side"]
        
        if main_quests:
            lines.append("\n-- Missioni Principali --")
            for quest in main_quests:
                self._add_quest_entry(quest, lines)
        
        if side_quests:
            lines.append("\n-- Missioni Secondarie --")
            for quest in side_quests:
                self._add_quest_entry(quest, lines)
        
        return lines
    
    def _add_quest_entry(self, quest: Quest, lines: List[str]) -> None:
        """Add a quest entry to journal lines.
        
        Args:
            quest: Quest to add
            lines: List of lines to append to
        """
        status_marker = "★" if quest.id == self.tracked_quest_id else " "
        lines.append(f"\n{status_marker} {quest.title}")
        
        if quest.act:
            lines.append(f"   Atto: {quest.act}")
        
        current_step = quest.get_current_step()
        if current_step:
            if quest.state == "BLOCKED":
                lines.append(f"   [BLOCCATA] {current_step.title}")
            else:
                lines.append(f"   Obiettivo: {current_step.description}")
        
        # Show progress
        progress = f"   Progresso: {quest.current_step_index + 1}/{len(quest.steps)}"
        lines.append(progress)