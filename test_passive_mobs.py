#!/usr/bin/env python3
"""
Test per il sistema di mob passivi di SECONDA VITA Alpha 0.3
Verifica l'organizzazione delle cartelle e la funzionalità delle interazioni passive.
"""

import json
import os
from pathlib import Path
from engine.core.state import GameState
from engine.core.registry import ContentRegistry
from engine.core.combat import start_combat, resolve_combat_action, CombatError
from game.bootstrap import setup_game


def test_mob_folder_organization():
    """Test dell'organizzazione delle cartelle mob."""
    print("🗂️ Test organizzazione cartelle mob...")
    
    base_path = Path("assets/mobs")
    
    # Verifica esistenza cartelle
    categories = ["walkers", "animals", "humans"]
    for category in categories:
        folder_path = base_path / category
        if folder_path.exists():
            print(f"  ✅ Cartella {category}/ esiste")
            
            # Lista file nella cartella
            mob_files = list(folder_path.glob("*.json"))
            if mob_files:
                print(f"     📄 Mob trovati: {[f.stem for f in mob_files]}")
            else:
                print(f"     ⚠️ Nessun mob trovato in {category}/")
        else:
            print(f"  ❌ Cartella {category}/ mancante")
    
    print()


def test_passive_mob_loading():
    """Test caricamento definizioni mob passivi."""
    print("📦 Test caricamento mob passivi...")
    
    # Test alcuni mob specifici
    test_mobs = [
        ("animals/deer.json", "cervo"),
        ("animals/rabbit.json", "coniglio"),
        ("animals/wild_boar.json", "cinghiale selvatico"),
        ("humans/survivor_injured.json", "sopravvissuto ferito"),
        ("humans/bandit_surrendered.json", "bandito arreso"),
        ("walkers/walker_wounded.json", "walker ferito")
    ]
    
    for mob_file, mob_name in test_mobs:
        mob_path = Path("assets/mobs") / mob_file
        if mob_path.exists():
            try:
                with open(mob_path) as f:
                    mob_data = json.load(f)
                
                # Verifica campi chiave
                required_fields = ["id", "name", "hp", "ai_state", "behavioral_traits"]
                missing_fields = [field for field in required_fields if field not in mob_data]
                
                if not missing_fields:
                    ai_state = mob_data.get("ai_state")
                    traits = mob_data.get("behavioral_traits", {})
                    
                    print(f"  ✅ {mob_name}: AI={ai_state}, traits={len(traits)}")
                    
                    # Mostra tratti interessanti
                    interesting_traits = []
                    if traits.get("flees_when_hurt"):
                        interesting_traits.append("fugge se ferito")
                    if traits.get("is_animal"):
                        interesting_traits.append("animale")
                    if traits.get("can_negotiate"):
                        interesting_traits.append("negoziabile")
                    if traits.get("has_hidden_weapon"):
                        interesting_traits.append("arma nascosta")
                    
                    if interesting_traits:
                        print(f"     🔍 Tratti: {', '.join(interesting_traits)}")
                
                else:
                    print(f"  ❌ {mob_name}: campi mancanti {missing_fields}")
                    
            except json.JSONDecodeError as e:
                print(f"  ❌ {mob_name}: errore JSON - {e}")
        else:
            print(f"  ⚠️ {mob_name}: file non trovato")
    
    print()


def test_passive_combat_interactions():
    """Test delle interazioni di combattimento con mob passivi."""
    print("⚔️ Test interazioni combattimento passivo...")
    
    try:
        # Setup game
        state, registry = setup_game()
        
        # Test con un cervo (animale passivo)
        deer_path = Path("assets/mobs/animals/deer.json")
        if not deer_path.exists():
            print("  ⚠️ File cervo non trovato, salto test")
            return
        
        with open(deer_path) as f:
            deer_data = json.load(f)
        
        print(f"  🦌 Inizio combattimento con {deer_data['name']}")
        
        # Inizia combattimento
        result = start_combat(state, registry, deer_data)
        print(f"     Combat iniziato: {result['lines'][0]}")
        
        # Test comando hunt
        print(f"  🏹 Tentativo di caccia...")
        try:
            hunt_result = resolve_combat_action(state, registry, "hunt")
            for line in hunt_result['lines']:
                print(f"     {line}")
        except CombatError as e:
            print(f"     ❌ Errore hunt: {e}")
        
        print()
        
        # Test con un sopravvissuto arreso
        survivor_path = Path("assets/mobs/humans/survivor_injured.json")
        if survivor_path.exists():
            with open(survivor_path) as f:
                survivor_data = json.load(f)
            
            # Reset state per nuovo combattimento
            state.combat_session = None
            
            print(f"  🧑‍⚕️ Inizio combattimento con {survivor_data['name']}")
            start_combat(state, registry, survivor_data)
            
            # Test comando negotiate
            print(f"  💬 Tentativo di negoziazione...")
            try:
                negotiate_result = resolve_combat_action(state, registry, "negotiate")
                for line in negotiate_result['lines']:
                    print(f"     {line}")
            except CombatError as e:
                print(f"     ❌ Errore negotiate: {e}")
        
        print()
            
    except Exception as e:
        print(f"  ❌ Errore durante test combattimento: {e}")
        import traceback
        traceback.print_exc()


def test_loot_system_integration():
    """Test integrazione sistema loot con mob passivi."""
    print("💰 Test integrazione sistema loot...")
    
    try:
        # Verifica che i nuovi oggetti siano stati aggiunti
        items_path = Path("assets/items.json")
        if not items_path.exists():
            print("  ❌ File items.json non trovato")
            return
        
        with open(items_path) as f:
            items_data = json.load(f)
        
        # Cerca nuovi oggetti loot
        new_items = ["carne_cruda", "pelle", "corna", "pelliccia_piccola", "foto_famiglia", "medicine_scadute"]
        found_items = []
        
        for item in items_data["items"]:
            if item["id"] in new_items:
                found_items.append(item["id"])
        
        if found_items:
            print(f"  ✅ Nuovi oggetti loot trovati: {found_items}")
        else:
            print(f"  ⚠️ Nessun nuovo oggetto loot trovato")
        
        # Verifica tabelle loot nei mob
        deer_path = Path("assets/mobs/animals/deer.json")
        if deer_path.exists():
            with open(deer_path) as f:
                deer_data = json.load(f)
            
            loot_table = deer_data.get("loot_table", [])
            if loot_table:
                loot_items = [entry["item"] for entry in loot_table]
                print(f"  🦌 Loot cervo: {loot_items}")
            else:
                print(f"  ⚠️ Cervo senza tabella loot")
        
        print()
        
    except Exception as e:
        print(f"  ❌ Errore test loot: {e}")


def run_full_test():
    """Esegue tutti i test per il sistema mob passivi."""
    print("🧪 TEST SISTEMA MOB PASSIVI - SECONDA VITA Alpha 0.3")
    print("=" * 60)
    print()
    
    test_mob_folder_organization()
    test_passive_mob_loading()
    test_passive_combat_interactions()
    test_loot_system_integration()
    
    print("✨ Test completati!")


if __name__ == "__main__":
    run_full_test()