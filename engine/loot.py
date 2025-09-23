"""Loot table system for generating random items from containers, zones, and mobs.

Provides weighted random item generation with rarity tiers and level scaling.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import random
import json
import os


@dataclass
class LootEntry:
    """Single entry in a loot table."""
    item: str
    chance: float  # 0.0 to 1.0
    min_quantity: int = 1
    max_quantity: int = 1
    rarity: str = "common"  # common, uncommon, rare, epic, legendary
    level_requirement: int = 0
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def roll_quantity(self, rng: random.Random = None) -> int:
        """Roll for quantity within min/max range."""
        if rng is None:
            rng = random
        return rng.randint(self.min_quantity, self.max_quantity)


@dataclass
class LootTable:
    """Collection of loot entries with metadata."""
    id: str
    name: str
    entries: List[LootEntry] = field(default_factory=list)
    max_rolls: int = 1
    guaranteed_rolls: int = 0
    level_scaling: bool = False
    tags: List[str] = field(default_factory=list)
    
    def add_entry(self, entry: LootEntry):
        """Add a loot entry to this table."""
        self.entries.append(entry)
    
    def roll_loot(self, player_level: int = 1, luck_modifier: float = 0.0, 
                  rng: random.Random = None, conditions: Dict[str, Any] = None) -> List[Tuple[str, int]]:
        """Roll for loot from this table. Returns list of (item_id, quantity) tuples."""
        if rng is None:
            rng = random
        
        if conditions is None:
            conditions = {}
        
        results = []
        
        # Calculate number of rolls
        total_rolls = self.guaranteed_rolls
        for _ in range(self.max_rolls - self.guaranteed_rolls):
            if rng.random() < 0.5 + (luck_modifier * 0.1):  # Luck increases roll chance
                total_rolls += 1
        
        # Perform rolls
        for _ in range(total_rolls):
            eligible_entries = self._get_eligible_entries(player_level, conditions)
            if not eligible_entries:
                continue
            
            # Apply luck modifier to rare items
            for entry in eligible_entries:
                if entry.rarity in ['rare', 'epic', 'legendary']:
                    entry.chance += luck_modifier * 0.05  # Small luck boost to rare items
            
            # Roll for item
            total_weight = sum(entry.chance for entry in eligible_entries)
            if total_weight <= 0:
                continue
            
            roll = rng.random() * total_weight
            current_weight = 0.0
            
            for entry in eligible_entries:
                current_weight += entry.chance
                if roll <= current_weight:
                    quantity = entry.roll_quantity(rng)
                    results.append((entry.item, quantity))
                    break
        
        return results
    
    def _get_eligible_entries(self, player_level: int, conditions: Dict[str, Any]) -> List[LootEntry]:
        """Get entries that meet level and condition requirements."""
        eligible = []
        
        for entry in self.entries:
            # Check level requirement
            if entry.level_requirement > player_level:
                continue
            
            # Check conditions
            if not self._check_conditions(entry.conditions, conditions):
                continue
            
            eligible.append(entry)
        
        return eligible
    
    def _check_conditions(self, entry_conditions: Dict[str, Any], actual_conditions: Dict[str, Any]) -> bool:
        """Check if entry conditions are met."""
        for key, required_value in entry_conditions.items():
            actual_value = actual_conditions.get(key)
            
            if isinstance(required_value, dict):
                # Handle complex conditions like {"min": 5, "max": 10}
                if "min" in required_value and actual_value < required_value["min"]:
                    return False
                if "max" in required_value and actual_value > required_value["max"]:
                    return False
            elif actual_value != required_value:
                return False
        
        return True


class LootRegistry:
    """Registry for managing loot tables."""
    
    def __init__(self):
        self.tables: Dict[str, LootTable] = {}
        self.rng_seed: Optional[int] = None
        self._rng: Optional[random.Random] = None
    
    def set_seed(self, seed: int):
        """Set random seed for deterministic loot generation."""
        self.rng_seed = seed
        self._rng = random.Random(seed)
    
    def get_rng(self) -> random.Random:
        """Get random number generator (seeded if seed was set)."""
        if self._rng is None:
            if self.rng_seed is not None:
                self._rng = random.Random(self.rng_seed)
            else:
                self._rng = random.Random()
        return self._rng
    
    def register_table(self, table: LootTable):
        """Register a loot table."""
        self.tables[table.id] = table
    
    def get_table(self, table_id: str) -> Optional[LootTable]:
        """Get a loot table by ID."""
        return self.tables.get(table_id)
    
    def roll_loot(self, table_id: str, player_level: int = 1, luck_modifier: float = 0.0,
                  conditions: Dict[str, Any] = None) -> List[Tuple[str, int]]:
        """Roll loot from a table."""
        table = self.get_table(table_id)
        if not table:
            return []
        
        return table.roll_loot(player_level, luck_modifier, self.get_rng(), conditions)
    
    def get_tables_by_tag(self, tag: str) -> List[LootTable]:
        """Get all tables with a specific tag."""
        return [table for table in self.tables.values() if tag in table.tags]
    
    def load_from_file(self, filepath: str) -> int:
        """Load loot tables from JSON file. Returns number of tables loaded."""
        if not os.path.exists(filepath):
            return 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            tables_data = data.get('tables', {})
            loaded_count = 0
            
            for table_id, table_data in tables_data.items():
                try:
                    table = self._create_table_from_data(table_id, table_data)
                    self.register_table(table)
                    loaded_count += 1
                except Exception as e:
                    print(f"Warning: Failed to load loot table {table_id}: {e}")
            
            return loaded_count
            
        except Exception as e:
            print(f"Error loading loot tables from {filepath}: {e}")
            return 0
    
    def _create_table_from_data(self, table_id: str, data: Any) -> LootTable:
        """Create LootTable from JSON data."""
        if isinstance(data, list):
            # Simple format - just list of entries
            entries_data = data
            table_name = table_id.replace('_', ' ').title()
            max_rolls = 1
            tags = []
        else:
            # Complex format - table with metadata
            entries_data = data.get('entries', data.get('items', []))
            table_name = data.get('name', table_id.replace('_', ' ').title())
            max_rolls = data.get('max_rolls', 1)
            tags = data.get('tags', [])
        
        table = LootTable(
            id=table_id,
            name=table_name,
            max_rolls=max_rolls,
            tags=tags
        )
        
        # Parse entries
        for entry_data in entries_data:
            entry = LootEntry(
                item=entry_data['item'],
                chance=entry_data.get('chance', 0.5),
                min_quantity=entry_data.get('min', entry_data.get('min_quantity', 1)),
                max_quantity=entry_data.get('max', entry_data.get('max_quantity', 1)),
                rarity=entry_data.get('rarity', 'common'),
                level_requirement=entry_data.get('level', entry_data.get('level_requirement', 0)),
                conditions=entry_data.get('conditions', {})
            )
            table.add_entry(entry)
        
        return table
    
    def create_default_tables(self):
        """Create some default loot tables for testing."""
        # Overworld common loot
        overworld_table = LootTable(
            id="overworld_common",
            name="Overworld Common Loot",
            max_rolls=2,
            tags=["outdoor", "common"]
        )
        
        overworld_table.add_entry(LootEntry("canned_beans", 0.35, 1, 2, "common"))
        overworld_table.add_entry(LootEntry("cloth", 0.25, 1, 3, "common"))
        overworld_table.add_entry(LootEntry("metal_scrap", 0.15, 1, 1, "uncommon"))
        overworld_table.add_entry(LootEntry("medkit", 0.05, 1, 1, "rare"))
        
        # House drawer loot
        house_drawer_table = LootTable(
            id="house_drawer",
            name="House Drawer",
            max_rolls=1,
            guaranteed_rolls=0,
            tags=["indoor", "container"]
        )
        
        house_drawer_table.add_entry(LootEntry("medkit", 0.10, 1, 1, "uncommon"))
        house_drawer_table.add_entry(LootEntry("adhesive", 0.20, 1, 2, "common"))
        house_drawer_table.add_entry(LootEntry("cloth", 0.30, 1, 2, "common"))
        
        # Rare container loot
        rare_container_table = LootTable(
            id="rare_container",
            name="Rare Container",
            max_rolls=3,
            guaranteed_rolls=1,
            tags=["special", "rare"]
        )
        
        rare_container_table.add_entry(LootEntry("hunting_knife", 0.15, 1, 1, "rare"))
        rare_container_table.add_entry(LootEntry("medkit", 0.40, 1, 3, "uncommon"))
        rare_container_table.add_entry(LootEntry("adhesive", 0.25, 2, 4, "common"))
        rare_container_table.add_entry(LootEntry("metal_scrap", 0.30, 1, 3, "common"))
        
        # Register tables
        for table in [overworld_table, house_drawer_table, rare_container_table]:
            self.register_table(table)


# Global loot registry
_loot_registry = LootRegistry()


def get_loot_registry() -> LootRegistry:
    """Get the global loot registry."""
    return _loot_registry


def load_loot_tables_from_assets(assets_dir: str = "assets") -> int:
    """Load loot tables from assets/loot_tables.json."""
    loot_file = os.path.join(assets_dir, "loot_tables.json")
    return _loot_registry.load_from_file(loot_file)


def create_default_loot_tables():
    """Create default loot tables in the global registry."""
    _loot_registry.create_default_tables()


def roll_loot_for_zone(zone_id: str, player_level: int = 1, luck: float = 0.0) -> List[Tuple[str, int]]:
    """Convenience function to roll loot for a zone."""
    return _loot_registry.roll_loot(zone_id, player_level, luck)


def roll_loot_for_container(container_type: str, player_level: int = 1, luck: float = 0.0) -> List[Tuple[str, int]]:
    """Convenience function to roll loot for a container."""
    return _loot_registry.roll_loot(container_type, player_level, luck)