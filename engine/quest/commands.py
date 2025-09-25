"""Quest system command handlers for integration with the game.

This module provides command handlers that can be integrated with the existing
game command system to provide quest functionality.
"""

from typing import Dict, List, Any
from .runtime import QuestLog
from .loader import load_main_story
from .generator import generate_side_quests

def quest_list_command(quest_log: QuestLog, priority: str = None) -> Dict[str, Any]:
    """Handle 'quests' command to list active quests.
    
    Args:
        quest_log: QuestLog instance
        priority: Optional filter by priority ("main" or "side")
        
    Returns:
        Command result dictionary
    """
    lines = []
    
    if priority:
        quests = quest_log.by_priority(priority)
        lines.append(f"=== Missioni {priority.title()} ===")
    else:
        quests = quest_log.active()
        lines.append("=== Missioni Attive ===")
    
    if not quests:
        lines.append("Nessuna missione attiva.")
        return {"lines": lines, "hints": [], "events_triggered": []}
    
    for quest in quests:
        status_marker = "★" if quest.id == quest_log.tracked_quest_id else " "
        status_text = ""
        
        if quest.state == "BLOCKED":
            status_text = " [BLOCCATA]"
        
        lines.append(f"{status_marker} {quest.title}{status_text}")
        
        if quest.act:
            lines.append(f"   Atto: {quest.act}")
        
        current_step = quest.get_current_step()
        if current_step:
            progress = f"{quest.current_step_index + 1}/{len(quest.steps)}"
            lines.append(f"   Progresso: {progress} - {current_step.title}")
    
    return {"lines": lines, "hints": [], "events_triggered": []}

def quest_detail_command(quest_log: QuestLog, quest_id: str) -> Dict[str, Any]:
    """Handle 'quest <id>' command to show quest details.
    
    Args:
        quest_log: QuestLog instance
        quest_id: ID of quest to show details for
        
    Returns:
        Command result dictionary
    """
    quest = quest_log.get_quest(quest_id)
    if not quest:
        return {
            "lines": [f"Missione '{quest_id}' non trovata."],
            "hints": [],
            "events_triggered": []
        }
    
    lines = [f"=== {quest.title} ==="]
    
    if quest.act:
        lines.append(f"Atto: {quest.act}")
    
    lines.append(f"Tipo: {quest.priority.title()}")
    lines.append(f"Stato: {quest.state}")
    
    if quest.state in ["IN_PROGRESS", "BLOCKED"]:
        current_step = quest.get_current_step()
        if current_step:
            lines.append(f"\nObiettivo Attuale:")
            lines.append(f"  {current_step.title}")
            lines.append(f"  {current_step.description}")
            
            if quest.state == "BLOCKED":
                lines.append("  [Requisiti non soddisfatti]")
    
    # Show all steps with status
    lines.append(f"\nPassi della Missione:")
    for i, step in enumerate(quest.steps):
        if i < quest.current_step_index:
            status = "✓"
        elif i == quest.current_step_index:
            status = "→" if quest.state == "IN_PROGRESS" else "⚠"
        else:
            status = " "
        
        lines.append(f"  {status} {step.title}")
    
    return {"lines": lines, "hints": [], "events_triggered": []}

def quest_track_command(quest_log: QuestLog, quest_id: str) -> Dict[str, Any]:
    """Handle 'track <id>' command to track a quest.
    
    Args:
        quest_log: QuestLog instance
        quest_id: ID of quest to track
        
    Returns:
        Command result dictionary
    """
    if quest_log.track(quest_id):
        quest = quest_log.get_quest(quest_id)
        return {
            "lines": [f"Ora stai seguendo: {quest.title}"],
            "hints": [],
            "events_triggered": []
        }
    else:
        return {
            "lines": [f"Impossibile seguire la missione '{quest_id}'."],
            "hints": [],
            "events_triggered": []
        }

def quest_abandon_command(quest_log: QuestLog, quest_id: str) -> Dict[str, Any]:
    """Handle 'abandon <id>' command to abandon a side quest.
    
    Args:
        quest_log: QuestLog instance
        quest_id: ID of quest to abandon
        
    Returns:
        Command result dictionary
    """
    quest = quest_log.get_quest(quest_id)
    if not quest:
        return {
            "lines": [f"Missione '{quest_id}' non trovata."],
            "hints": [],
            "events_triggered": []
        }
    
    if quest.priority == "main":
        return {
            "lines": ["Non puoi abbandonare una missione principale."],
            "hints": [],
            "events_triggered": []
        }
    
    if quest_log.abandon(quest_id):
        return {
            "lines": [f"Hai abbandonato: {quest.title}"],
            "hints": [],
            "events_triggered": []
        }
    else:
        return {
            "lines": [f"Impossibile abbandonare la missione '{quest_id}'."],
            "hints": [],
            "events_triggered": []
        }

def journal_command(quest_log: QuestLog, gs) -> Dict[str, Any]:
    """Handle 'journal' command to show journal entries.
    
    Args:
        quest_log: QuestLog instance
        gs: GameState object
        
    Returns:
        Command result dictionary
    """
    lines = quest_log.get_journal_entries()
    
    # Add recent journal entries if available
    if hasattr(gs, 'journal_history') and gs.journal_history:
        from .journal import get_recent_entries
        recent = get_recent_entries(gs, limit=5)
        
        if recent:
            lines.append("\n=== Voci Recenti ===")
            for entry in recent:
                timestamp = entry.get("timestamp", 0)
                hours = (timestamp // 60) % 24
                minutes = timestamp % 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                weather = entry.get("weather", "")
                location = entry.get("location", "")
                text = entry.get("text", "")
                
                lines.append(f"[{time_str} | {weather} | {location}]")
                lines.append(f"  {text}")
    
    return {"lines": lines, "hints": [], "events_triggered": []}

def quest_tick_command(quest_log: QuestLog) -> List[str]:
    """Process quest progression tick and return messages.
    
    Args:
        quest_log: QuestLog instance
        
    Returns:
        List of progression messages
    """
    return quest_log.tick()

def load_main_story_command(story_file: str, quest_log: QuestLog) -> Dict[str, Any]:
    """Load main story quests from file.
    
    Args:
        story_file: Path to main story JSON file
        quest_log: QuestLog instance to load quests into
        
    Returns:
        Command result dictionary
    """
    try:
        quests = load_main_story(story_file)
        
        for quest in quests:
            quest_log.register(quest)
        
        return {
            "lines": [f"Caricate {len(quests)} missioni principali da {story_file}"],
            "hints": [],
            "events_triggered": []
        }
    except Exception as e:
        return {
            "lines": [f"Errore nel caricamento delle missioni: {str(e)}"],
            "hints": [],
            "events_triggered": []
        }

def generate_side_quests_command(
    templates_file: str, 
    quest_log: QuestLog, 
    gs, 
    max_quests: int = 3
) -> Dict[str, Any]:
    """Generate side quests from templates.
    
    Args:
        templates_file: Path to quest templates JSON file
        quest_log: QuestLog instance
        gs: GameState object
        max_quests: Maximum number of quests to generate
        
    Returns:
        Command result dictionary
    """
    try:
        quests = generate_side_quests(templates_file, gs, max_quests)
        
        for quest in quests:
            quest_log.register(quest)
        
        return {
            "lines": [f"Generate {len(quests)} missioni secondarie"],
            "hints": [],
            "events_triggered": []
        }
    except Exception as e:
        return {
            "lines": [f"Errore nella generazione delle missioni: {str(e)}"],
            "hints": [],
            "events_triggered": []
        }

# Command integration example for existing game system
QUEST_COMMANDS = {
    "quests": {
        "usage": "quests [main|side]",
        "desc": "Mostra le missioni attive. Opzionalmente filtra per tipo.",
        "examples": ["quests", "quests main", "quests side"]
    },
    "quest": {
        "usage": "quest <id>",
        "desc": "Mostra i dettagli di una missione specifica.",
        "examples": ["quest Q1_FIND_BANDAGE", "quest side_fetch_rain_1234"]
    },
    "track": {
        "usage": "track <id>",
        "desc": "Inizia a seguire una missione (mostrerà suggerimenti durante il gioco).",
        "examples": ["track Q1_FIND_BANDAGE"]
    },
    "abandon": {
        "usage": "abandon <id>",
        "desc": "Abbandona una missione secondaria (non funziona per missioni principali).",
        "examples": ["abandon side_fetch_rain_1234"]
    },
    "journal": {
        "usage": "journal",
        "desc": "Mostra il diario delle missioni con le voci recenti.",
        "examples": ["journal"]
    }
}