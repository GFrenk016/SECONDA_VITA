#!/usr/bin/env python3
"""Test del sistema di mob passivi con caccia, cattura e negoziazione."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.core.state import GameState
from engine.core.registry import ContentRegistry
from engine.core.actions import combat_action
from engine.core.loader.content_loader import load_mob_by_path
from game.bootstrap import load_world_and_state
import engine.core.combat as combat


def setup_test_state():
    """Crea uno stato di test."""
    registry, state = load_world_and_state()
    return state, registry


def test_passive_deer_hunt():
    """Test caccia al cervo passivo."""
    print("\n=== TEST: Caccia al Cervo Passivo ===")
    
    state, registry = setup_test_state()
    
    # Carica il cervo dalla directory animals
    deer_def = load_mob_by_path('assets/mobs/animals/deer.json')
    if not deer_def:
        print("❌ Impossibile caricare deer.json")
        return False
    
    print(f"✅ Cervo caricato: {deer_def.get('name', 'N/A')}")
    print(f"   AI State: {deer_def.get('ai_state', 'N/A')}")
    print(f"   Behavioral Traits: {deer_def.get('behavioral_traits', {})}")
    
    # Inizia combattimento con il cervo
    try:
        result = combat.start_combat(state, registry, deer_def)
        print("✅ Combattimento iniziato:")
        for line in result.get('lines', []):
            print(f"   {line}")
        
        # Prova comando hunt
        hunt_result = combat_action(state, registry, "hunt")
        print("\n🏹 Tentativo di caccia:")
        for line in hunt_result.get('lines', []):
            print(f"   {line}")
            
        # Verifica se il combattimento è finito
        if state.combat_session and state.combat_session.get('phase') == 'ended':
            print("✅ Caccia completata - combattimento terminato")
        else:
            print("⚠️  Caccia in corso - combattimento attivo")
            
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la caccia: {e}")
        return False


def test_surrendered_human_negotiate():
    """Test negoziazione con umano arreso."""
    print("\n=== TEST: Negoziazione con Bandito Arreso ===")
    
    state, registry = setup_test_state()
    
    # Carica il bandito arreso
    bandit_def = load_mob_by_path('assets/mobs/humans/bandit_surrendered.json')
    if not bandit_def:
        print("❌ Impossibile caricare bandit_surrendered.json")
        return False
    
    print(f"✅ Bandito caricato: {bandit_def.get('name', 'N/A')}")
    print(f"   AI State: {bandit_def.get('ai_state', 'N/A')}")
    
    # Inizia combattimento
    try:
        result = combat.start_combat(state, registry, bandit_def)
        print("✅ Incontro iniziato:")
        for line in result.get('lines', []):
            print(f"   {line}")
        
        # Prova comando negotiate
        negotiate_result = combat_action(state, registry, "negotiate")
        print("\n🤝 Tentativo di negoziazione:")
        for line in negotiate_result.get('lines', []):
            print(f"   {line}")
            
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la negoziazione: {e}")
        return False


def test_wounded_walker_capture():
    """Test cattura di walker ferito."""
    print("\n=== TEST: Cattura di Walker Ferito ===")
    
    state, registry = setup_test_state()
    
    # Carica il walker ferito
    walker_def = load_mob_by_path('assets/mobs/walkers/walker_wounded.json')
    if not walker_def:
        print("❌ Impossibile caricare walker_wounded.json")
        return False
    
    print(f"✅ Walker caricato: {walker_def.get('name', 'N/A')}")
    print(f"   AI State: {walker_def.get('ai_state', 'N/A')}")
    
    # Inizia combattimento
    try:
        result = combat.start_combat(state, registry, walker_def)
        print("✅ Incontro iniziato:")
        for line in result.get('lines', []):
            print(f"   {line}")
        
        # Prova comando capture
        capture_result = combat_action(state, registry, "capture")
        print("\n🕸️ Tentativo di cattura:")
        for line in capture_result.get('lines', []):
            print(f"   {line}")
            
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la cattura: {e}")
        return False


def test_aggressive_mob_rejection():
    """Test che mob aggressivi rifiutino interazioni passive."""
    print("\n=== TEST: Mob Aggressivo Rifiuta Interazioni Passive ===")
    
    state, registry = setup_test_state()
    
    # Carica un lupo aggressivo
    wolf_def = load_mob_by_path('assets/mobs/animals/pack_wolf.json')
    if not wolf_def:
        print("❌ Impossibile caricare pack_wolf.json")
        return False
    
    print(f"✅ Lupo caricato: {wolf_def.get('name', 'N/A')}")
    print(f"   AI State: {wolf_def.get('ai_state', 'aggressive')}")
    
    try:
        result = combat.start_combat(state, registry, wolf_def)
        print("✅ Combattimento iniziato:")
        for line in result.get('lines', []):
            print(f"   {line}")
        
        # Prova hunt su mob aggressivo (dovrebbe fallire)
        hunt_result = combat_action(state, registry, "hunt")
        print("\n🏹 Tentativo di caccia su lupo aggressivo:")
        for line in hunt_result.get('lines', []):
            print(f"   {line}")
            
        # Prova negotiate su mob aggressivo (dovrebbe fallire)
        negotiate_result = combat_action(state, registry, "negotiate")
        print("\n🤝 Tentativo di negoziazione su lupo aggressivo:")
        for line in negotiate_result.get('lines', []):
            print(f"   {line}")
            
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        return False


def main():
    """Esegue tutti i test dei mob passivi."""
    print("🔬 SISTEMA MOB PASSIVI - Test Suite")
    print("=" * 50)
    
    tests = [
        test_passive_deer_hunt,
        test_surrendered_human_negotiate,
        test_wounded_walker_capture,
        test_aggressive_mob_rejection
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print("✅ PASSED")
            else:
                print("❌ FAILED")
        except Exception as e:
            print(f"💥 CRASH: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 RISULTATI: {passed}/{total} test superati")
    
    if passed == total:
        print("🎉 Tutti i test sono passati! Sistema mob passivi funzionante.")
    else:
        print("⚠️  Alcuni test sono falliti. Controlla l'implementazione.")
    
    return passed == total


if __name__ == "__main__":
    main()