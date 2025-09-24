"""Crafting system for combining materials into items.

Provides recipe management, material verification, and item creation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import json
import os


@dataclass
class CraftingIngredient:
    """Single ingredient in a recipe."""
    item_id: str
    quantity: int
    
    def __str__(self) -> str:
        return f"{self.quantity}x {self.item_id}"


@dataclass
class CraftingResult:
    """Result of a crafting recipe."""
    item_id: str
    quantity: int = 1
    
    def __str__(self) -> str:
        return f"{self.quantity}x {self.item_id}"


@dataclass
class Recipe:
    """Crafting recipe definition."""
    id: str
    name: str
    inputs: List[CraftingIngredient]
    output: CraftingResult
    station: Optional[str] = None  # Required crafting station
    skill_requirement: int = 0
    craft_time: int = 60  # Time in seconds/ticks
    tags: List[str] = field(default_factory=list)
    description: str = ""
    
    def get_total_input_weight(self, item_registry) -> float:
        """Calculate total weight of input materials."""
        from .items import get_item_registry
        
        if item_registry is None:
            item_registry = get_item_registry()
        
        total_weight = 0.0
        for ingredient in self.inputs:
            item = item_registry.get_item(ingredient.item_id)
            if item:
                total_weight += item.weight * ingredient.quantity
        
        return total_weight
    
    def can_craft_with_materials(self, available_materials: Dict[str, int]) -> Tuple[bool, List[str]]:
        """Check if recipe can be crafted with available materials."""
        missing = []
        
        for ingredient in self.inputs:
            available = available_materials.get(ingredient.item_id, 0)
            if available < ingredient.quantity:
                needed = ingredient.quantity - available
                missing.append(f"{needed}x {ingredient.item_id}")
        
        return len(missing) == 0, missing


class CraftingStation:
    """Represents a crafting station in the world."""
    
    def __init__(self, station_id: str, name: str, recipes: List[str] = None):
        self.id = station_id
        self.name = name
        self.available_recipes = recipes or []
        self.is_active = True
    
    def can_craft_recipe(self, recipe: Recipe) -> bool:
        """Check if this station can craft the given recipe."""
        if not self.is_active:
            return False
        
        # If recipe requires a station, check if this is the right one
        if recipe.station and recipe.station != self.id:
            return False
        
        # If station has specific recipes, check if recipe is available
        if self.available_recipes and recipe.id not in self.available_recipes:
            return False
        
        return True


class CraftingRegistry:
    """Registry for managing recipes and crafting stations."""
    
    def __init__(self):
        self.recipes: Dict[str, Recipe] = {}
        self.stations: Dict[str, CraftingStation] = {}
    
    def register_recipe(self, recipe: Recipe):
        """Register a recipe."""
        self.recipes[recipe.id] = recipe
    
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Get a recipe by ID."""
        return self.recipes.get(recipe_id)
    
    def get_all_recipes(self) -> List[Recipe]:
        """Get all registered recipes."""
        return list(self.recipes.values())
    
    def get_recipes_by_station(self, station_id: str) -> List[Recipe]:
        """Get all recipes that can be crafted at a station."""
        return [recipe for recipe in self.recipes.values() 
                if recipe.station is None or recipe.station == station_id]
    
    def get_recipes_by_tag(self, tag: str) -> List[Recipe]:
        """Get all recipes with a specific tag."""
        return [recipe for recipe in self.recipes.values() if tag in recipe.tags]
    
    def register_station(self, station: CraftingStation):
        """Register a crafting station."""
        self.stations[station.id] = station
    
    def get_station(self, station_id: str) -> Optional[CraftingStation]:
        """Get a crafting station by ID."""
        return self.stations.get(station_id)
    
    def find_recipes_by_name(self, name: str, partial=False) -> List[Recipe]:
        """Find recipes by name."""
        if partial:
            name_lower = name.lower()
            return [recipe for recipe in self.recipes.values() 
                   if name_lower in recipe.name.lower()]
        else:
            return [recipe for recipe in self.recipes.values() 
                   if recipe.name.lower() == name.lower()]
    
    def can_craft(self, recipe_id: str, available_materials: Dict[str, int], 
                  station_id: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Check if a recipe can be crafted with available materials and station."""
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return False, ["Recipe not found"]
        
        # Check materials
        can_craft, missing_materials = recipe.can_craft_with_materials(available_materials)
        if not can_craft:
            return False, [f"Missing materials: {', '.join(missing_materials)}"]
        
        # Check station requirement
        if recipe.station:
            if not station_id:
                return False, [f"Requires crafting station: {recipe.station}"]
            
            station = self.get_station(station_id)
            if not station or not station.can_craft_recipe(recipe):
                return False, [f"Cannot craft at this station"]
        
        return True, []
    
    def craft_item(self, recipe_id: str, available_materials: Dict[str, int],
                   station_id: Optional[str] = None) -> Tuple[bool, str, Optional[CraftingResult], Dict[str, int]]:
        """Attempt to craft an item. Returns (success, message, result, consumed_materials)."""
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return False, "Recipe not found", None, {}
        
        # Check if crafting is possible
        can_craft, reasons = self.can_craft(recipe_id, available_materials, station_id)
        if not can_craft:
            return False, "; ".join(reasons), None, {}
        
        # Consume materials
        consumed = {}
        for ingredient in recipe.inputs:
            consumed[ingredient.item_id] = ingredient.quantity
        
        return True, f"Crafted {recipe.output}", recipe.output, consumed
    
    def load_from_file(self, filepath: str) -> int:
        """Load recipes from JSON file. Returns number of recipes loaded."""
        if not os.path.exists(filepath):
            return 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            recipes_data = data.get('recipes', [])
            loaded_count = 0
            
            for recipe_data in recipes_data:
                try:
                    recipe = self._create_recipe_from_data(recipe_data)
                    self.register_recipe(recipe)
                    loaded_count += 1
                except Exception as e:
                    print(f"Warning: Failed to load recipe {recipe_data.get('id', 'unknown')}: {e}")
            
            return loaded_count
            
        except Exception as e:
            print(f"Error loading recipes from {filepath}: {e}")
            return 0
    
    def _create_recipe_from_data(self, data: Dict[str, Any]) -> Recipe:
        """Create Recipe from JSON data."""
        recipe_id = data['id']
        name = data['name']
        
        # Parse inputs
        inputs = []
        inputs_data = data.get('inputs', [])
        for input_data in inputs_data:
            if isinstance(input_data, list) and len(input_data) >= 2:
                # Format: ["item_id", quantity]
                inputs.append(CraftingIngredient(input_data[0], input_data[1]))
            elif isinstance(input_data, dict):
                # Format: {"item": "item_id", "quantity": 2}
                inputs.append(CraftingIngredient(
                    input_data['item'],
                    input_data.get('quantity', 1)
                ))
        
        # Parse output
        output_data = data.get('output', [recipe_id, 1])
        if isinstance(output_data, list) and len(output_data) >= 2:
            output = CraftingResult(output_data[0], output_data[1])
        elif isinstance(output_data, dict):
            output = CraftingResult(
                output_data['item'],
                output_data.get('quantity', 1)
            )
        else:
            output = CraftingResult(recipe_id, 1)
        
        return Recipe(
            id=recipe_id,
            name=name,
            inputs=inputs,
            output=output,
            station=data.get('station'),
            skill_requirement=data.get('skill', 0),
            craft_time=data.get('time', 60),
            tags=data.get('tags', []),
            description=data.get('description', "")
        )
    
    def create_default_recipes(self):
        """Create some default recipes for testing."""
        # Bandage recipe
        bandage_recipe = Recipe(
            id="bandage",
            name="Bandage",
            inputs=[CraftingIngredient("cloth", 2)],
            output=CraftingResult("bandage", 1),
            station="craft_bench",
            craft_time=30,
            tags=["medical", "basic"],
            description="A simple bandage for treating wounds."
        )
        
        # Knife repair recipe
        knife_repair_recipe = Recipe(
            id="knife_repair",
            name="Knife Repair",
            inputs=[
                CraftingIngredient("metal_scrap", 2),
                CraftingIngredient("adhesive", 1)
            ],
            output=CraftingResult("hunting_knife", 1),
            station="craft_bench",
            craft_time=120,
            tags=["repair", "weapon"],
            description="Repair a hunting knife using scrap metal and adhesive."
        )
        
        # Basic energy drink
        energy_drink_recipe = Recipe(
            id="energy_drink",
            name="Energy Drink",
            inputs=[
                CraftingIngredient("canned_beans", 1),
                CraftingIngredient("cloth", 1)  # Filter
            ],
            output=CraftingResult("energy_drink", 1),
            craft_time=60,
            tags=["consumable", "energy"],
            description="A makeshift energy drink."
        )
        
        # Register recipes
        for recipe in [bandage_recipe, knife_repair_recipe, energy_drink_recipe]:
            self.register_recipe(recipe)
        
        # Create default stations
        craft_bench = CraftingStation("craft_bench", "Crafting Bench")
        workbench = CraftingStation("workbench", "Workbench")
        
        for station in [craft_bench, workbench]:
            self.register_station(station)


# Global crafting registry
_crafting_registry = CraftingRegistry()


def get_crafting_registry() -> CraftingRegistry:
    """Get the global crafting registry."""
    return _crafting_registry


def load_recipes_from_assets(assets_dir: str = "assets") -> int:
    """Load recipes from assets/recipes.json."""
    recipes_file = os.path.join(assets_dir, "recipes.json")
    return _crafting_registry.load_from_file(recipes_file)


def create_default_recipes():
    """Create default recipes in the global registry."""
    _crafting_registry.create_default_recipes()


def craft_item(recipe_id: str, available_materials: Dict[str, int], 
               station_id: Optional[str] = None) -> Tuple[bool, str, Optional[CraftingResult], Dict[str, int]]:
    """Convenience function to craft an item."""
    return _crafting_registry.craft_item(recipe_id, available_materials, station_id)