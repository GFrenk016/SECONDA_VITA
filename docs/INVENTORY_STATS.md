# Inventory & Stats System Documentation

This document describes the inventory, stats, and item systems in Seconda Vita.

## Commands

### Inventory Management

- `inventory` or `inv` - Display current inventory with weight and categorized items
- `use <item>` - Use a consumable item (e.g., `use medkit`)
- `equip <item>` - Equip an item to appropriate slot (e.g., `equip hunting knife`)
- `unequip <slot|item>` - Unequip by slot name or item name (e.g., `unequip main_hand`)
- `drop <item> [quantity]` - Drop items from inventory (e.g., `drop cloth 2`)
- `examine <item>` - View detailed information about an item

### Character Stats

- `stats` - Display player statistics, resistances, and active effects

## Item System

### Item Types

- **Consumable**: Items that are used up when consumed (medkits, food, potions)
- **Weapon**: Equipable items for combat (knives, swords)
- **Armor**: Equipable protective gear (jackets, boots, helmets)
- **Material**: Crafting materials (cloth, metal scrap, adhesive)
- **Quest**: Special story items

### Equipment Slots

- `main_hand` - Primary weapon or tool
- `off_hand` - Secondary weapon or shield
- `head` - Helmets, hats
- `body` - Jackets, shirts, armor
- `legs` - Pants, leg armor
- `feet` - Boots, shoes
- `accessory1` / `accessory2` - Jewelry, charms

### Item Effects

Items can have various effects when used or equipped:

- `heal: <amount>` - Restore health points
- `restore: {energy: <amount>}` - Restore energy
- `buff: {stat: <stat_name>, amount: <value>, duration_ticks: <duration>}` - Temporary stat boost
- `damage_over_time: {type: <damage_type>, amount: <damage>, duration: <ticks>}` - DoT effects
- `resist: {type: <damage_type>, amount: <resistance>, duration: <ticks>}` - Damage resistance

## Statistics System

### Base Stats

- **Health** (0-100): Current/maximum health points
- **Energy** (0-100): Current/maximum energy for actions
- **Morale** (0-100): Mental state affecting various actions

### Attributes

- **Strength**: Affects carry capacity and melee damage
- **Agility**: Affects evasion chance and movement
- **Intellect**: Affects crafting and problem solving
- **Perception**: Affects vision range and detection
- **Charisma**: Affects NPC interactions
- **Luck**: Affects critical hits and loot drops

### Derived Stats

- **Carry Capacity**: `10 + (Strength × 2)` kg maximum weight
- **Critical Chance**: `(Luck × 2)%` base chance (max 50%)
- **Evasion**: `(Agility × 1.5)%` chance to avoid damage (max 30%)
- **Vision Range**: `2 + (Perception × 0.2)` cells

### Resistances

- **Bleed Resistance**: Reduces bleeding damage
- **Poison Resistance**: Reduces poison damage
- **Fire Resistance**: Reduces fire damage
- **Cold Resistance**: Reduces cold damage

## Asset Files

### items.json Format

```json
{
  "items": [
    {
      "id": "medkit",
      "name": "Medkit",
      "type": "consumable",
      "weight": 0.4,
      "stack_max": 3,
      "effects": [{"heal": 35}],
      "value": 15,
      "description": "A medical kit that quickly restores health."
    }
  ]
}
```

### loot_tables.json Format

```json
{
  "tables": {
    "overworld_common": {
      "name": "Overworld Common Loot",
      "max_rolls": 2,
      "entries": [
        {
          "item": "canned_beans",
          "chance": 0.35,
          "min": 1,
          "max": 2,
          "rarity": "common"
        }
      ],
      "tags": ["outdoor", "common"]
    }
  }
}
```

### recipes.json Format

```json
{
  "recipes": [
    {
      "id": "bandage",
      "name": "Bandage",
      "station": "craft_bench",
      "inputs": [["cloth", 2]],
      "output": ["bandage", 3],
      "time": 30,
      "tags": ["medical", "basic"],
      "description": "Craft bandages from cloth."
    }
  ]
}
```

## Examples

### Creating New Items

Add to `assets/items.json`:

```json
{
  "id": "energy_bar",
  "name": "Energy Bar",
  "type": "consumable",
  "weight": 0.2,
  "stack_max": 8,
  "effects": [
    {"restore": {"energy": 25}},
    {"buff": {"stat": "strength", "amount": 1, "duration_ticks": 60}}
  ],
  "value": 8,
  "tags": ["food", "energy"],
  "description": "A nutritious energy bar that provides stamina and temporary strength."
}
```

### Creating Equipment

```json
{
  "id": "combat_helmet",
  "name": "Combat Helmet",
  "type": "armor",
  "weight": 1.8,
  "stack_max": 1,
  "equip_slot": "head",
  "durability": 150,
  "value": 60,
  "effects": [
    {"buff": {"stat": "perception", "amount": 2, "duration_ticks": 0}},
    {"resist": {"type": "bleed", "amount": 20, "duration_ticks": 0}}
  ],
  "tags": ["armor", "military"],
  "description": "A military-grade helmet offering excellent head protection."
}
```

### Creating Loot Tables

```json
{
  "military_cache": {
    "name": "Military Supply Cache",
    "max_rolls": 3,
    "guaranteed_rolls": 1,
    "entries": [
      {"item": "combat_helmet", "chance": 0.15, "min": 1, "max": 1, "rarity": "rare"},
      {"item": "medkit", "chance": 0.40, "min": 1, "max": 2, "rarity": "common"},
      {"item": "energy_bar", "chance": 0.60, "min": 2, "max": 4, "rarity": "common"}
    ],
    "tags": ["military", "rare", "valuable"]
  }
}
```

### Creating Recipes

```json
{
  "id": "first_aid_kit",
  "name": "First Aid Kit",
  "station": "craft_bench",
  "inputs": [
    ["bandage", 3],
    ["adhesive", 1],
    ["cloth", 2]
  ],
  "output": ["medkit", 1],
  "time": 120,
  "tags": ["medical", "advanced"],
  "description": "Assemble a proper medical kit from basic supplies."
}
```

## Best Practices

### Item Design

1. **Weight Balance**: Keep items realistic - heavy items should provide significant benefits
2. **Stack Limits**: Common materials should stack high (10-20), weapons/armor shouldn't stack
3. **Value Scaling**: Rare items should have proportionally higher values
4. **Effect Duration**: Permanent equipment bonuses use `duration_ticks: 0`

### Loot Table Design

1. **Rarity Distribution**: 60% common, 25% uncommon, 10% rare, 4% epic, 1% legendary
2. **Contextual Loot**: Forest areas drop natural materials, urban areas drop manufactured goods
3. **Guaranteed vs Random**: Important locations should have at least 1 guaranteed roll

### Recipe Balance

1. **Input Cost**: Total input value should be less than output value
2. **Time Investment**: Rare items should take longer to craft
3. **Station Requirements**: Advanced items need proper crafting stations

## Integration Notes

The inventory system integrates with:

- **Combat System**: Weapons provide damage bonuses, armor provides protection
- **World System**: Containers and resource nodes in world files
- **Save System**: All inventory/stats data is saved automatically
- **Command System**: All commands follow the existing ActionResult pattern

## Migration from Legacy

The system maintains compatibility with the legacy `inventory: List[str]` field in GameState for backward compatibility with old save files.