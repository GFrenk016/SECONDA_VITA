"""NPC registry for runtime NPC management."""

from __future__ import annotations
from typing import Dict, List, Optional
from .models import NPC, NPCState, NPCRelation


class NPCRegistry:
    """Registry for managing NPCs at runtime."""
    
    def __init__(self):
        self.npcs: Dict[str, NPC] = {}
        self.location_index: Dict[str, List[str]] = {}  # location -> list of npc_ids
    
    def register_npc(self, npc: NPC):
        """Register an NPC in the system."""
        self.npcs[npc.id] = npc
        self._update_location_index(npc)
    
    def register_npcs(self, npcs: Dict[str, NPC]):
        """Register multiple NPCs."""
        for npc in npcs.values():
            self.register_npc(npc)
    
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """Get NPC by ID."""
        return self.npcs.get(npc_id)
    
    def get_npcs_at_location(self, macro_id: str, micro_id: str) -> List[NPC]:
        """Get all NPCs at a specific location."""
        location_key = f"{macro_id}:{micro_id}"
        npc_ids = self.location_index.get(location_key, [])
        return [self.npcs[npc_id] for npc_id in npc_ids if npc_id in self.npcs]
    
    def move_npc(self, npc_id: str, new_macro: str, new_micro: str):
        """Move an NPC to a new location."""
        npc = self.npcs.get(npc_id)
        if not npc:
            return
        
        # Remove from old location index
        old_location = f"{npc.current_macro}:{npc.current_micro}"
        if old_location in self.location_index:
            self.location_index[old_location] = [
                id_ for id_ in self.location_index[old_location] if id_ != npc_id
            ]
        
        # Update NPC location
        npc.current_macro = new_macro
        npc.current_micro = new_micro
        
        # Update location index
        self._update_location_index(npc)
    
    def _update_location_index(self, npc: NPC):
        """Update the location index for an NPC."""
        location_key = f"{npc.current_macro}:{npc.current_micro}"
        if location_key not in self.location_index:
            self.location_index[location_key] = []
        
        if npc.id not in self.location_index[location_key]:
            self.location_index[location_key].append(npc.id)
    
    def update_npc_states(self, current_time_minutes: int):
        """Update NPC states based on schedules and time."""
        for npc in self.npcs.values():
            self._update_npc_schedule(npc, current_time_minutes)
    
    def _update_npc_schedule(self, npc: NPC, current_time_minutes: int):
        """Update NPC based on their daily schedule."""
        if not npc.daily_schedule:
            return
        
        # Convert current time to hour format for schedule lookup
        hour = (current_time_minutes // 60) % 24
        hour_key = f"{hour:02d}:00"
        
        # Check for exact hour matches or ranges
        activity = npc.daily_schedule.get(hour_key)
        if activity:
            if activity == "sleep":
                npc.current_state = NPCState.SLEEPING
            elif activity == "work":
                npc.current_state = NPCState.BUSY
            else:
                npc.current_state = NPCState.NEUTRAL
    
    def get_talkable_npcs(self, macro_id: str, micro_id: str) -> List[NPC]:
        """Get NPCs that can be talked to at a location."""
        npcs = self.get_npcs_at_location(macro_id, micro_id)
        return [npc for npc in npcs if npc.current_state not in [NPCState.SLEEPING, NPCState.HOSTILE]]
    
    def save_state(self) -> Dict[str, any]:
        """Save NPC registry state for persistence."""
        return {
            'npcs': {
                npc_id: {
                    'current_macro': npc.current_macro,
                    'current_micro': npc.current_micro,
                    'relationship': npc.relationship.value,
                    'current_state': npc.current_state.value,
                    'mood': npc.mood,
                    'memories': [
                        {
                            'event': mem.event,
                            'timestamp_minutes': mem.timestamp_minutes,
                            'context': mem.context,
                            'importance': mem.importance,
                            'emotional_impact': mem.emotional_impact
                        }
                        for mem in npc.memories
                    ],
                    'last_interaction': npc.last_interaction
                }
                for npc_id, npc in self.npcs.items()
            }
        }
    
    def load_state(self, state_data: Dict[str, any]):
        """Load NPC registry state from persistence."""
        if 'npcs' not in state_data:
            return
        
        for npc_id, npc_state in state_data['npcs'].items():
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            
            # Update location
            if 'current_macro' in npc_state and 'current_micro' in npc_state:
                self.move_npc(npc_id, npc_state['current_macro'], npc_state['current_micro'])
            
            # Update relationship and state
            if 'relationship' in npc_state:
                try:
                    npc.relationship = NPCRelation(npc_state['relationship'])
                except ValueError:
                    pass
            
            if 'current_state' in npc_state:
                try:
                    npc.current_state = NPCState(npc_state['current_state'])
                except ValueError:
                    pass
            
            # Update mood and interaction time
            if 'mood' in npc_state:
                npc.mood = float(npc_state['mood'])
            
            if 'last_interaction' in npc_state:
                npc.last_interaction = int(npc_state['last_interaction'])
            
            # Load memories would require more complex deserialization
            # For now, skip to keep changes minimal