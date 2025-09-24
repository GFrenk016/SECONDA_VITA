"""Item definitions and registry system.

Defines item types, categories, and provides a registry for loading and managing items.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import json
import os


@dataclass
class Item:
    """Base item definition."""
    id: str
    name: str
    type: str  # consumable, weapon, armor, material, quest
    weight: float
    stack_max: int = 1
    effects: List[Dict[str, Any]] = field(default_factory=list)
    equip_slot: Optional[str] = None  # main_hand, off_hand, head, body, legs, feet, accessory
    durability: Optional[int] = None
    value: int = 0
    tags: List[str] = field(default_factory=list)
    description: str = ""
    
    def has_tag(self, tag: str) -> bool:
        """Check if item has a specific tag."""
        return tag in self.tags
    
    def is_equipable(self) -> bool:
        """Check if item can be equipped."""
        return self.equip_slot is not None
    
    def is_consumable(self) -> bool:
        """Check if item is consumable."""
        return self.type == 'consumable'
    
    def is_weapon(self) -> bool:
        """Check if item is a weapon."""
        return self.type == 'weapon'
    
    def is_armor(self) -> bool:
        """Check if item is armor."""
        return self.type == 'armor'
    
    def is_material(self) -> bool:
        """Check if item is a crafting material."""
        return self.type == 'material'
    
    def is_quest_item(self) -> bool:
        """Check if item is a quest item."""
        return self.type == 'quest'
    
    def get_heal_amount(self) -> int:
        """Get healing amount from effects."""
        for effect in self.effects:
            if 'heal' in effect:
                return effect['heal']
        return 0
    
    def get_energy_restore(self) -> int:
        """Get energy restoration amount from effects."""
        for effect in self.effects:
            if 'restore' in effect and 'energy' in effect['restore']:
                return effect['restore']['energy']
        return 0
    
    def get_buffs(self) -> List[Dict[str, Any]]:
        """Get buff effects from this item."""
        buffs = []
        for effect in self.effects:
            if 'buff' in effect:
                buffs.append(effect['buff'])
        return buffs


class ItemRegistry:
    """Registry for managing item definitions."""
    
    def __init__(self):
        self.items: Dict[str, Item] = {}
    
    def register_item(self, item: Item):
        """Register a new item."""
        self.items[item.id] = item
    
    def get_item(self, item_id: str) -> Optional[Item]:
        """Get item by ID."""
        return self.items.get(item_id)
    
    def get_all_items(self) -> List[Item]:
        """Get all registered items."""
        return list(self.items.values())
    
    def get_items_by_type(self, item_type: str) -> List[Item]:
        """Get all items of a specific type."""
        return [item for item in self.items.values() if item.type == item_type]
    
    def get_items_by_tag(self, tag: str) -> List[Item]:
        """Get all items with a specific tag."""
        return [item for item in self.items.values() if item.has_tag(tag)]
    
    def find_items_by_name(self, name: str, partial=False) -> List[Item]:
        """Find items by name (exact or partial match)."""
        if partial:
            name_lower = name.lower()
            return [item for item in self.items.values() 
                   if name_lower in item.name.lower()]
        else:
            return [item for item in self.items.values() 
                   if item.name.lower() == name.lower()]
    
    def load_from_file(self, filepath: str) -> int:
        """Load items from JSON file. Returns number of items loaded."""
        if not os.path.exists(filepath):
            return 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            items_data = data.get('items', [])
            loaded_count = 0
            
            for item_data in items_data:
                try:
                    item = self._create_item_from_data(item_data)
                    self.register_item(item)
                    loaded_count += 1
                except Exception as e:
                    print(f"Warning: Failed to load item {item_data.get('id', 'unknown')}: {e}")
            
            return loaded_count
            
        except Exception as e:
            print(f"Error loading items from {filepath}: {e}")
            return 0
    
    def _create_item_from_data(self, data: Dict[str, Any]) -> Item:
        """Create Item instance from JSON data."""
        # Required fields
        item_id = data['id']
        name = data['name']
        item_type = data['type']
        weight = float(data['weight'])
        
        # Optional fields with defaults
        stack_max = data.get('stack_max', 1)
        effects = data.get('effects', [])
        equip_slot = data.get('equip_slot')
        durability = data.get('durability')
        value = data.get('value', 0)
        tags = data.get('tags', [])
        description = data.get('description', "")
        
        return Item(
            id=item_id,
            name=name,
            type=item_type,
            weight=weight,
            stack_max=stack_max,
            effects=effects,
            equip_slot=equip_slot,
            durability=durability,
            value=value,
            tags=tags,
            description=description
        )
    
    def create_default_items(self):
        """Create some default items for testing."""
        # Consumables
        medkit = Item(
            id="medkit",
            name="Medkit",
            type="consumable",
            weight=0.4,
            stack_max=3,
            effects=[{"heal": 35}],
            value=15,
            description="A medical kit that restores health."
        )
        
        beans = Item(
            id="canned_beans",
            name="Canned Beans",
            type="consumable", 
            weight=0.5,
            stack_max=5,
            effects=[{"restore": {"energy": 20}}],
            value=5,
            description="Nutritious canned beans that restore energy."
        )
        
        # Weapon
        knife = Item(
            id="hunting_knife",
            name="Hunting Knife",
            type="weapon",
            weight=0.8,
            stack_max=1,
            equip_slot="main_hand",
            durability=100,
            value=25,
            effects=[{"buff": {"stat": "crit_chance", "amount": 5, "duration_ticks": 0}}],
            tags=["weapon", "melee"],
            description="A sharp hunting knife, good for close combat."
        )
        
        # Materials
        cloth = Item(
            id="cloth",
            name="Cloth",
            type="material",
            weight=0.1,
            stack_max=10,
            value=2,
            tags=["crafting"],
            description="Simple cloth fabric, useful for crafting."
        )
        
        metal_scrap = Item(
            id="metal_scrap",
            name="Metal Scrap",
            type="material",
            weight=0.3,
            stack_max=5,
            value=8,
            tags=["crafting", "metal"],
            description="Pieces of scrap metal that can be repurposed."
        )
        
        adhesive = Item(
            id="adhesive",
            name="Adhesive",
            type="material",
            weight=0.2,
            stack_max=3,
            value=12,
            tags=["crafting"],
            description="Strong adhesive for repairs and crafting."
        )
        
        # Register all default items
        for item in [medkit, beans, knife, cloth, metal_scrap, adhesive]:
            self.register_item(item)


# Global registry instance
_item_registry = ItemRegistry()

def get_item_registry() -> ItemRegistry:
    """Get the global item registry."""
    return _item_registry

def load_items_from_assets(assets_dir: str = "assets") -> int:
    """Load items from assets/items.json file."""
    items_file = os.path.join(assets_dir, "items.json")
    return _item_registry.load_from_file(items_file)

def create_default_items():
    """Create default items in the global registry."""
    _item_registry.create_default_items()