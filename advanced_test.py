#!/usr/bin/env python3
"""
Test interattivo per le nuove armi e sistema combattimento
"""

from game.bootstrap import load_world_and_state
from engine.core.loader.content_loader import load_combat_content
from engine.core.combat import inject_content

def test_weapon_loading():
    """Test del caricamento delle armi"""
    print("=== Test Caricamento Armi ===")
    
    weapons, mobs = load_combat_content()
    inject_content(weapons, mobs)
    
    print(f"Armi caricate: {len(weapons)}")
    for weapon_id, weapon_data in weapons.items():
        print(f"  - {weapon_id}: {weapon_data.get('name', 'No Name')} ({weapon_data.get('weapon_class', 'unknown')})")
        if weapon_data.get('weapon_class') == 'ranged':
            print(f"    Munizioni: {weapon_data.get('ammo_in_clip', 0)}/{weapon_data.get('clip_size', 0)} + {weapon_data.get('ammo_reserve', 0)}")
        elif weapon_data.get('weapon_class') == 'throwable':
            print(f"    Usi: {weapon_data.get('uses', 0)}, AoE: {weapon_data.get('aoe_factor', 0)}")
    
    print(f"\nMob caricati: {len(mobs)}")
    for mob_id, mob_data in mobs.items():
        print(f"  - {mob_id}: {mob_data.get('name', 'No Name')} (HP: {mob_data.get('hp', 0)})")

def test_inventory_system():
    """Test del sistema inventario"""
    print("\n=== Test Sistema Inventario ===")
    
    registry, state = load_world_and_state()
    
    # Inizializza sistemi
    from engine.items import create_default_items, load_items_from_assets
    from engine.loot import create_default_loot_tables, load_loot_tables_from_assets
    from engine.crafting import create_default_recipes, load_recipes_from_assets
    
    create_default_items()
    create_default_loot_tables()
    create_default_recipes()
    
    items_loaded = load_items_from_assets()
    loot_loaded = load_loot_tables_from_assets()
    recipes_loaded = load_recipes_from_assets()
    
    print(f"Oggetti caricati: {items_loaded}")
    print(f"Loot tables caricate: {loot_loaded}")
    print(f"Ricette caricate: {recipes_loaded}")
    
    # Mostra inventario iniziale
    from engine.core.actions import inventory, stats
    
    inv_result = inventory(state, registry)
    print("\nInventario iniziale:")
    for line in inv_result.get("lines", []):
        print(f"  {line}")
    
    stats_result = stats(state, registry)
    print("\nStatistiche:")
    for line in stats_result.get("lines", []):
        print(f"  {line}")

def test_npc_system():
    """Test del sistema NPC"""
    print("\n=== Test Sistema NPC ===")
    
    try:
        from engine.core.loader.world_loader import load_npcs_from_assets
        npcs_loaded = load_npcs_from_assets()
        print(f"NPC caricati: {npcs_loaded}")
    except Exception as e:
        print(f"Errore caricamento NPC: {e}")

if __name__ == "__main__":
    print("Test Approfondito SECONDA VITA Alpha 0.3")
    print("=" * 50)
    
    test_weapon_loading()
    test_inventory_system()
    test_npc_system()
    
    print("\n" + "=" * 50)
    print("Test completati!")