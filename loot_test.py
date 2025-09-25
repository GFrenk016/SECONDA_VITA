#!/usr/bin/env python3
"""
Test del sistema loot e multi-nemico migliorato
"""

from game.bootstrap import load_world_and_state
from engine.core.loader.content_loader import load_combat_content
from engine.core.combat import inject_content, set_combat_seed
from engine.core.actions import spawn, combat_action, look, inventory
from engine.items import create_default_items, load_items_from_assets

def test_loot_system():
    """Test del sistema loot dalle sconfitte nemici"""
    print("🎁 === TEST SISTEMA LOOT ===")
    
    # Setup
    registry, state = load_world_and_state()
    weapons, mobs = load_combat_content()
    inject_content(weapons, mobs)
    
    # Inizializza sistema oggetti
    create_default_items()
    load_items_from_assets()
    
    set_combat_seed(123)  # Per risultati deterministici
    
    print("Inventario iniziale:")
    inv_result = inventory(state, registry)
    for line in inv_result.get("lines", [])[-3:]:  # Solo ultime 3 linee
        print(f"  {line}")
    
    print("\n🗡️ Combattimento con Vagante...")
    spawn_result = spawn(state, registry, "walker_basic")
    print(f"  {spawn_result['lines'][0]}")
    
    # Attacchi fino a sconfiggere il nemico
    attacks = 0
    while state.combat_session and state.combat_session.get('phase') != 'ended':
        attack_result = combat_action(state, registry, "attack", None)
        attacks += 1
        for line in attack_result.get("lines", []):
            if "danni" in line or "vinto" in line or "Raccogli" in line:
                print(f"  Attacco {attacks}: {line}")
        
        if attacks > 20:  # Safety break
            break
    
    print(f"\n📦 Inventario dopo combattimento:")
    inv_result = inventory(state, registry)
    for line in inv_result.get("lines", [])[-5:]:  # Ultime 5 linee
        print(f"  {line}")
    
    print(f"\n🐺 Combattimento con Lupo del Branco...")
    spawn_result = spawn(state, registry, "pack_wolf")
    print(f"  {spawn_result['lines'][0]}")
    
    attacks = 0
    while state.combat_session and state.combat_session.get('phase') != 'ended':
        attack_result = combat_action(state, registry, "attack", None)
        attacks += 1
        for line in attack_result.get("lines", []):
            if "danni" in line or "vinto" in line or "Raccogli" in line:
                print(f"  Attacco {attacks}: {line}")
        
        if attacks > 20:
            break
    
    print(f"\n📦 Inventario finale:")
    inv_result = inventory(state, registry)
    for line in inv_result.get("lines", []):
        print(f"  {line}")

def test_multi_enemy():
    """Test del sistema multi-nemico"""
    print("\n\n⚔️ === TEST MULTI-NEMICO ===")
    
    # Setup
    registry, state = load_world_and_state()
    weapons, mobs = load_combat_content()
    inject_content(weapons, mobs)
    
    create_default_items()
    load_items_from_assets()
    
    set_combat_seed(456)
    
    print("🎯 Spawn multipli...")
    spawn_result = spawn(state, registry, "walker_basic")
    print(f"  {spawn_result['lines'][0]}")
    
    # Spawn secondo nemico durante il combattimento
    spawn_result2 = combat_action(state, registry, "spawn pack_wolf", None)
    for line in spawn_result2.get("lines", []):
        print(f"  {line}")
    
    # Spawn terzo nemico
    spawn_result3 = combat_action(state, registry, "spawn walker_basic 2", None)
    for line in spawn_result3.get("lines", []):
        print(f"  {line}")
    
    # Mostra status
    status_result = combat_action(state, registry, "status", None)
    print(f"\n📊 Status battaglia:")
    for line in status_result.get("lines", []):
        print(f"  {line}")
    
    # Test focus
    print(f"\n🎯 Test sistema focus:")
    focus_result = combat_action(state, registry, "focus", "2")
    for line in focus_result.get("lines", []):
        print(f"  {line}")
    
    # Attacco con focus
    attack_result = combat_action(state, registry, "attack", None)
    for line in attack_result.get("lines", []):
        if "Colpisci" in line:
            print(f"  {line}")
    
    # Test attacco specifico per indice
    attack_result = combat_action(state, registry, "attack", "1")
    for line in attack_result.get("lines", []):
        if "Colpisci" in line:
            print(f"  {line}")
    
    # Test attacco ad area
    print(f"\n💥 Test attacco ad area:")
    area_attack = combat_action(state, registry, "attack all", None)
    for line in area_attack.get("lines", []):
        if "Colpisci" in line or "tutti i nemici" in line:
            print(f"  {line}")

if __name__ == "__main__":
    print("Test Sistemi Avanzati SECONDA VITA Alpha 0.3")
    print("=" * 60)
    
    test_loot_system()
    test_multi_enemy()
    
    print("\n" + "=" * 60)
    print("🎉 Test sistemi completati!")