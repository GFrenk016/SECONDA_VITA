"""Save/Load system for Seconda Vita.

Handles complete GameState serialization with versioning support.
Maintains compatibility with existing save formats while adding new features.
"""
from __future__ import annotations
import json
import os
import time
from datetime import datetime
from dataclasses import asdict
from typing import Dict, List, Any, Optional
from pathlib import Path

from .state import GameState

# Save format version - increment when making breaking changes
SAVE_VERSION = 1
SAVES_DIR = Path("data/saves")

class SaveError(Exception):
    """Exception raised for save/load operations."""
    pass

def ensure_saves_dir():
    """Ensure the saves directory exists."""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)

def serialize_game_state(state: GameState) -> Dict[str, Any]:
    """Convert GameState to serializable dictionary."""
    # Convert dataclass to dict
    data = asdict(state)
    
    # Add metadata
    data["_save_metadata"] = {
        "version": SAVE_VERSION,
        "timestamp": time.time(),
        "date_saved": datetime.now().isoformat(),
        "game_version": state.version
    }
    
    # Convert sets to lists for JSON serialization
    if "visited_micro" in data:
        data["visited_micro"] = list(data["visited_micro"])
    if "fired_events" in data:
        data["fired_events"] = list(data["fired_events"])
    
    # Handle nested dict with sets in micro_last_visible
    if "micro_last_visible" in data:
        data["micro_last_visible"] = {
            k: list(v) for k, v in data["micro_last_visible"].items()
        }
    
    return data

def deserialize_game_state(data: Dict[str, Any]) -> GameState:
    """Convert dictionary back to GameState."""
    # Extract and validate metadata
    metadata = data.pop("_save_metadata", {})
    save_version = metadata.get("version", 0)
    
    if save_version > SAVE_VERSION:
        raise SaveError(f"Save file version {save_version} is newer than supported version {SAVE_VERSION}")
    
    # Convert lists back to sets
    if "visited_micro" in data:
        data["visited_micro"] = set(data["visited_micro"])
    if "fired_events" in data:
        data["fired_events"] = set(data["fired_events"])
    
    # Handle nested dict with sets in micro_last_visible
    if "micro_last_visible" in data:
        data["micro_last_visible"] = {
            k: set(v) for k, v in data["micro_last_visible"].items()
        }
    
    # Create GameState instance
    return GameState(**data)

def save_game(state: GameState, slot_name: str = "quicksave") -> str:
    """Save game state to a named slot.
    
    Args:
        state: GameState to save
        slot_name: Name of the save slot (default: "quicksave")
    
    Returns:
        Path to the save file
        
    Raises:
        SaveError: If save operation fails
    """
    ensure_saves_dir()
    
    try:
        # Serialize the state
        save_data = serialize_game_state(state)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{slot_name}_{timestamp}.json"
        filepath = SAVES_DIR / filename
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
        
    except Exception as e:
        raise SaveError(f"Failed to save game: {e}")

def load_game(slot_name: str = None, filepath: str = None) -> GameState:
    """Load game state from a save file.
    
    Args:
        slot_name: Name of save slot to load latest from
        filepath: Specific file path to load from
    
    Returns:
        Loaded GameState
        
    Raises:
        SaveError: If load operation fails
    """
    ensure_saves_dir()
    
    try:
        if filepath:
            # Load from specific file
            load_path = Path(filepath)
        elif slot_name:
            # Find latest save for slot
            pattern = f"{slot_name}_*.json"
            saves = list(SAVES_DIR.glob(pattern))
            if not saves:
                raise SaveError(f"No saves found for slot '{slot_name}'")
            # Sort by modification time, newest first
            saves.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            load_path = saves[0]
        else:
            raise SaveError("Must specify either slot_name or filepath")
        
        if not load_path.exists():
            raise SaveError(f"Save file not found: {load_path}")
        
        # Load and deserialize
        with open(load_path, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
        
        return deserialize_game_state(save_data)
        
    except Exception as e:
        raise SaveError(f"Failed to load game: {e}")

def list_saves() -> List[Dict[str, Any]]:
    """List all available save files with metadata.
    
    Returns:
        List of save file info dictionaries
    """
    ensure_saves_dir()
    
    saves = []
    for save_file in SAVES_DIR.glob("*.json"):
        try:
            with open(save_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get("_save_metadata", {})
            saves.append({
                "filename": save_file.name,
                "filepath": str(save_file),
                "slot_name": save_file.stem.split("_")[0],
                "timestamp": metadata.get("timestamp", save_file.stat().st_mtime),  
                "date_saved": metadata.get("date_saved", "Unknown"),
                "version": metadata.get("version", 0),
                "game_version": metadata.get("game_version", 0),
                "location": f"{data.get('current_macro', 'Unknown')}:{data.get('current_micro', 'Unknown')}",
                "day_count": data.get("day_count", 0),
                "time_minutes": data.get("time_minutes", 0)
            })
        except Exception:
            # Skip corrupted save files
            continue
    
    # Sort by timestamp, newest first
    saves.sort(key=lambda x: x["timestamp"], reverse=True)
    return saves

def delete_save(slot_name: str = None, filepath: str = None) -> bool:
    """Delete a save file.
    
    Args:
        slot_name: Delete all saves for this slot
        filepath: Delete specific save file
    
    Returns:
        True if deletion successful
        
    Raises:
        SaveError: If deletion fails
    """
    ensure_saves_dir()
    
    try:
        if filepath:
            Path(filepath).unlink()
            return True
        elif slot_name:
            pattern = f"{slot_name}_*.json"
            saves = list(SAVES_DIR.glob(pattern))
            for save_file in saves:
                save_file.unlink()
            return len(saves) > 0
        else:
            raise SaveError("Must specify either slot_name or filepath")
            
    except Exception as e:
        raise SaveError(f"Failed to delete save: {e}")