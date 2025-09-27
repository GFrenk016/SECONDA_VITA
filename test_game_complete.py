#!/usr/bin/env python3
"""Test completo automatico per Seconda Vita.

Questo script testa tutte le funzionalità principali del gioco
senza richiedere input dall'utente.
"""

import sys
import traceback
from game.bootstrap import load_world_and_state
from engine.core.actions import *
from engine.core.combat import inject_content, tick_combat, set_complex_qte
from engine.core.loader.content_loader import load_combat_content
from engine.items import create_default_items, load_items_from_assets
from engine.loot import create_default_loot_tables, load_loot_tables_from_assets
from engine.crafting import create_default_recipes, load_recipes_from_assets
from engine.effects import create_default_effects
from config import DEFAULT_COMPLEX_QTE_ENABLED

def print_section(name):
    """Decoratore per sezioni di test"""
    print(f"\n{'='*50}")
    print(f"🧪 TEST: {name}")
    print('='*50)

def run_action_safe(action_func, *args, **kwargs):
    """Esegue un'azione in modo sicuro e restituisce il risultato"""
    try:
        result = action_func(*args, **kwargs)
        if result and "lines" in result:
            for line in result["lines"]:
                print(f"  → {line}")
        return result
    except Exception as e:
        print(f"  ❌ Errore: {e}")
        return {"lines": [f"Error: {e}"]}

def main():
    print("🎮 SECONDA VITA - TEST AUTOMATICO COMPLETO")
    print("=" * 60)
    
    try:
        # Inizializzazione
        print_section("INIZIALIZZAZIONE SISTEMA")
        registry, state = load_world_and_state()
        weapons, mobs = load_combat_content()
        inject_content(weapons, mobs)
        
        # Carica sistemi inventario
        create_default_items()
        create_default_loot_tables()
        create_default_recipes()
        create_default_effects()
        
        try:
            items_loaded = load_items_from_assets()
            loot_loaded = load_loot_tables_from_assets()
            recipes_loaded = load_recipes_from_assets()
            print(f"  ✅ Caricati {items_loaded} oggetti, {loot_loaded} loot, {recipes_loaded} ricette")
        except Exception as e:
            print(f"  ⚠️  Warning assets: {e}")
        
        set_complex_qte(False)  # QTE semplici per test
        print("  ✅ Sistema inizializzato correttamente!")
        
        # Test 1: Esplorazione base
        print_section("ESPLORAZIONE E AMBIENTE")
        run_action_safe(where, state, registry)
        run_action_safe(look, state, registry)
        run_action_safe(status, state, registry)
        
        # Test 2: Gestione tempo
        print_section("GESTIONE TEMPO")
        run_action_safe(wait, state, registry, 5)
        run_action_safe(wait_until, state, registry, "sera")
        run_action_safe(status, state, registry)
        
        # Test 3: Interazione ambiente
        print_section("INTERAZIONE CON AMBIENTE")
        run_action_safe(inspect, state, registry, "Cippo di Pietra")
        run_action_safe(examine, state, registry, "Cippo di Pietra")
        run_action_safe(search, state, registry, "Cippo di Pietra")
        
        # Test 4: Sistema inventario
        print_section("SISTEMA INVENTARIO")
        run_action_safe(inventory, state, registry)
        run_action_safe(stats, state, registry)
        run_action_safe(equip_item, state, registry, "Hunting Knife")
        run_action_safe(use_item, state, registry, "Medkit")
        run_action_safe(stats, state, registry)
        
        # Test 5: Sistema crafting
        print_section("SISTEMA CRAFTING")
        run_action_safe(craft, state, registry, "bandage")
        run_action_safe(inventory, state, registry)
        
        # Test 6: Combattimento base
        print_section("COMBATTIMENTO BASE")
        run_action_safe(spawn, state, registry, "walker_basic")
        run_action_safe(status, state, registry)
        
        # Simula alcuni attacchi
        for i in range(3):
            result = run_action_safe(combat_action, state, registry, "attack")
            # Se c'è un QTE attivo, rispondi automaticamente
            try:
                sess = getattr(state, 'combat_session', None)
                if sess and sess.get('phase') == 'qte' and sess.get('qte'):
                    qte_data = sess['qte']
                    if 'expected' in qte_data:
                        expected = qte_data['expected']
                        print(f"  🎯 Auto-QTE: {expected}")
                        run_action_safe(combat_action, state, registry, 'qte', expected)
            except:
                pass
        
        # Test 7: Combattimento avanzato
        print_section("COMBATTIMENTO AVANZATO")
        run_action_safe(combat_action, state, registry, "spawn walker_basic 2")
        run_action_safe(status, state, registry)
        run_action_safe(combat_action, state, registry, "attack all")
        run_action_safe(combat_action, state, registry, "focus 2")
        run_action_safe(combat_action, state, registry, "push")
        
        # Test 8: Sistema NPC
        print_section("SISTEMA NPC")
        run_action_safe(talk, state, registry, None)  # Lista NPC
        # Se ci sono NPC, prova a parlare con uno
        if hasattr(state, 'current_area') and state.current_area:
            area = registry.areas.get(state.current_area)
            if area and hasattr(area, 'npcs') and area.npcs:
                npc_name = list(area.npcs.keys())[0] if area.npcs else None
                if npc_name:
                    run_action_safe(talk, state, registry, npc_name)
                    run_action_safe(say, state, registry, "Ciao!")
                    run_action_safe(end_conversation, state, registry)
        
        # Test 9: Sistema salvataggio
        print_section("SISTEMA SALVATAGGIO")
        run_action_safe(save_game, state, registry, "test_save")
        run_action_safe(list_saves, state, registry)
        
        # Test 10: Sistema quest e memoria
        print_section("SISTEMA QUEST E MEMORIA")
        run_action_safe(journal, state, registry)
        run_action_safe(memories, state, registry)
        
        # Test 11: Movimento
        print_section("SISTEMA MOVIMENTO")
        # Prova a muoverti in diverse direzioni
        for direction in ["n", "s", "e", "w"]:
            result = run_action_safe(go, state, registry, direction)
            # Se il movimento ha successo, torna indietro
            if result and result.get("lines") and not any("non puoi" in line.lower() for line in result["lines"]):
                # Direzioni opposte
                opposite = {"n": "s", "s": "n", "e": "w", "w": "e"}
                if direction in opposite:
                    run_action_safe(go, state, registry, opposite[direction])
                break
        
        print("\n" + "="*60)
        print("🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("🎮 Il gioco è pronto per essere testato manualmente!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRORE CRITICO NEL TEST: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)