"""Facade for world model & loader.

Re-exports dataclasses and utility build/validate functions from the
refactored internal modules to provide a stable import surface.
"""
from .model.base import (
    World,
    MacroRoom,
    MicroRoom,
    Exit,
    ConditionRef,
    InteractableRef,
)
from .loader.world_loader import build_world_from_dict, validate_world

__all__ = [
    "World",
    "MacroRoom",
    "MicroRoom",
    "Exit",
    "ConditionRef",
    "InteractableRef",
    "build_world_from_dict",
    "validate_world",
]
