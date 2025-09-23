"""Inventory and equipment management system.

Provides API for carrying, stacking, equipping, and managing items with weight limits.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from .items import Item, ItemRegistry


@dataclass
class ItemStack:
    """Represents a stack of identical items."""
    item_id: str
    quantity: int = 1
    
    def can_stack_with(self, other_item_id: str, max_stack: int) -> bool:
        """Check if this stack can accept more of the given item."""
        return self.item_id == other_item_id and self.quantity < max_stack


@dataclass 
class Equipment:
    """Player equipment slots."""
    main_hand: Optional[str] = None
    off_hand: Optional[str] = None
    head: Optional[str] = None
    body: Optional[str] = None
    legs: Optional[str] = None
    feet: Optional[str] = None
    accessory1: Optional[str] = None
    accessory2: Optional[str] = None
    
    def get_all_equipped(self) -> List[str]:
        """Get list of all equipped item IDs."""
        equipped = []
        for slot_value in [self.main_hand, self.off_hand, self.head, self.body, 
                          self.legs, self.feet, self.accessory1, self.accessory2]:
            if slot_value:
                equipped.append(slot_value)
        return equipped
    
    def get_slot_for_item(self, item: Item) -> Optional[str]:
        """Get the equipment slot name for an item, if it has one."""
        if not item.equip_slot:
            return None
        
        # Map item equip_slot to actual equipment attribute
        slot_mapping = {
            'main_hand': 'main_hand',
            'off_hand': 'off_hand', 
            'head': 'head',
            'body': 'body',
            'legs': 'legs',
            'feet': 'feet',
            'accessory1': 'accessory1',
            'accessory2': 'accessory2',
            'accessory': 'accessory1'  # Default to first accessory slot
        }
        return slot_mapping.get(item.equip_slot)
    
    def is_slot_occupied(self, slot: str) -> bool:
        """Check if an equipment slot is occupied."""
        return getattr(self, slot, None) is not None
    
    def equip_item(self, slot: str, item_id: str) -> Optional[str]:
        """Equip item to slot, returning previously equipped item if any."""
        old_item = getattr(self, slot, None)
        setattr(self, slot, item_id)
        return old_item
    
    def unequip_slot(self, slot: str) -> Optional[str]:
        """Unequip item from slot, returning the item ID if any."""
        old_item = getattr(self, slot, None)
        setattr(self, slot, None)
        return old_item


class Inventory:
    """Player inventory management with stacking and weight limits."""
    
    def __init__(self, item_registry: ItemRegistry):
        self.item_registry = item_registry
        self.stacks: List[ItemStack] = []
        self.equipment = Equipment()
    
    def get_total_weight(self) -> float:
        """Calculate total weight of carried items."""
        total = 0.0
        
        # Add inventory weight
        for stack in self.stacks:
            item = self.item_registry.get_item(stack.item_id)
            if item:
                total += item.weight * stack.quantity
        
        # Add equipped items weight
        for item_id in self.equipment.get_all_equipped():
            item = self.item_registry.get_item(item_id)
            if item:
                total += item.weight
        
        return total
    
    def can_carry(self, additional_weight: float, carry_capacity: float) -> bool:
        """Check if can carry additional weight."""
        return self.get_total_weight() + additional_weight <= carry_capacity
    
    def find_stack(self, item_id: str) -> Optional[ItemStack]:
        """Find existing stack for item."""
        for stack in self.stacks:
            if stack.item_id == item_id:
                return stack
        return None
    
    def get_item_quantity(self, item_id: str) -> int:
        """Get total quantity of item in inventory (excluding equipped)."""
        stack = self.find_stack(item_id)
        return stack.quantity if stack else 0
    
    def add(self, item_id: str, quantity: int = 1) -> bool:
        """Add items to inventory. Returns True if successful."""
        item = self.item_registry.get_item(item_id)
        if not item:
            return False
        
        remaining = quantity
        
        # Try to add to existing stacks first
        for stack in self.stacks:
            if stack.can_stack_with(item_id, item.stack_max):
                can_add = min(remaining, item.stack_max - stack.quantity)
                stack.quantity += can_add
                remaining -= can_add
                if remaining <= 0:
                    return True
        
        # Create new stacks for remaining items
        while remaining > 0:
            new_stack_size = min(remaining, item.stack_max)
            self.stacks.append(ItemStack(item_id, new_stack_size))
            remaining -= new_stack_size
        
        return True
    
    def remove(self, item_id: str, quantity: int = 1) -> bool:
        """Remove items from inventory. Returns True if successful."""
        if self.get_item_quantity(item_id) < quantity:
            return False
        
        remaining = quantity
        stacks_to_remove = []
        
        for i, stack in enumerate(self.stacks):
            if stack.item_id == item_id and remaining > 0:
                can_remove = min(remaining, stack.quantity)
                stack.quantity -= can_remove
                remaining -= can_remove
                
                if stack.quantity <= 0:
                    stacks_to_remove.append(i)
        
        # Remove empty stacks
        for i in reversed(stacks_to_remove):
            del self.stacks[i]
        
        return remaining == 0
    
    def list_items(self) -> List[Tuple[str, int, bool]]:
        """List all items as (item_id, quantity, is_equipped)."""
        items = []
        
        # Add inventory items
        for stack in self.stacks:
            items.append((stack.item_id, stack.quantity, False))
        
        # Add equipped items
        for item_id in self.equipment.get_all_equipped():
            items.append((item_id, 1, True))
        
        return items
    
    def can_equip(self, item_id: str) -> Tuple[bool, str]:
        """Check if item can be equipped. Returns (can_equip, reason)."""
        item = self.item_registry.get_item(item_id)
        if not item:
            return False, "Item not found"
        
        if not item.equip_slot:
            return False, "Item cannot be equipped"
        
        if self.get_item_quantity(item_id) <= 0:
            return False, "Item not in inventory"
        
        slot = self.equipment.get_slot_for_item(item)
        if not slot:
            return False, "No valid equipment slot"
        
        # Special handling for accessories - try both slots
        if item.equip_slot == 'accessory':
            if not self.equipment.is_slot_occupied('accessory1'):
                return True, ""
            elif not self.equipment.is_slot_occupied('accessory2'):
                return True, ""
            else:
                return False, "All accessory slots occupied"
        
        return True, ""
    
    def equip(self, item_id: str) -> Tuple[bool, str, Optional[str]]:
        """Equip item. Returns (success, message, unequipped_item_id)."""
        can_equip, reason = self.can_equip(item_id)
        if not can_equip:
            return False, reason, None
        
        item = self.item_registry.get_item(item_id)
        slot = self.equipment.get_slot_for_item(item)
        
        # Special handling for accessories
        if item.equip_slot == 'accessory':
            if not self.equipment.is_slot_occupied('accessory1'):
                slot = 'accessory1'
            else:
                slot = 'accessory2'
        
        # Remove from inventory
        if not self.remove(item_id, 1):
            return False, "Failed to remove from inventory", None
        
        # Equip and handle previously equipped item
        old_item_id = self.equipment.equip_item(slot, item_id)
        if old_item_id:
            self.add(old_item_id, 1)  # Put old item back in inventory
        
        return True, f"Equipped {item.name}", old_item_id
    
    def unequip(self, slot_or_item: str) -> Tuple[bool, str, Optional[str]]:
        """Unequip by slot name or item ID. Returns (success, message, unequipped_item_id)."""
        item_id = None
        slot = None
        
        # Check if it's a slot name
        if hasattr(self.equipment, slot_or_item):
            slot = slot_or_item
            item_id = getattr(self.equipment, slot)
        else:
            # Try to find by item ID
            for slot_name in ['main_hand', 'off_hand', 'head', 'body', 'legs', 'feet', 'accessory1', 'accessory2']:
                if getattr(self.equipment, slot_name) == slot_or_item:
                    slot = slot_name
                    item_id = slot_or_item
                    break
        
        if not item_id or not slot:
            return False, "Item not equipped", None
        
        # Unequip and add to inventory
        self.equipment.unequip_slot(slot)
        self.add(item_id, 1)
        
        item = self.item_registry.get_item(item_id)
        item_name = item.name if item else item_id
        
        return True, f"Unequipped {item_name}", item_id
    
    def use_item(self, item_id: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Use an item, consuming it if it's consumable. Returns (success, message, effects)."""
        item = self.item_registry.get_item(item_id)
        if not item:
            return False, "Item not found", []
        
        if self.get_item_quantity(item_id) <= 0:
            return False, "Item not in inventory", []
        
        if item.type == 'consumable':
            # Consume the item
            if not self.remove(item_id, 1):
                return False, "Failed to consume item", []
            
            return True, f"Used {item.name}", item.effects
        else:
            return False, "Item cannot be used directly", []
    
    def drop_item(self, item_id: str, quantity: int = 1) -> Tuple[bool, str]:
        """Drop item from inventory. Returns (success, message)."""
        if self.get_item_quantity(item_id) < quantity:
            return False, "Not enough items to drop"
        
        if not self.remove(item_id, quantity):
            return False, "Failed to remove items"
        
        item = self.item_registry.get_item(item_id)
        item_name = item.name if item else item_id
        
        return True, f"Dropped {quantity}x {item_name}"