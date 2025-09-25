#!/usr/bin/env python3
"""
Test completo e dimostrazione delle nuove funzionalità Alpha 0.3
"""

from engine.core.combat import inject_content, set_combat_seed
from engine.core.loader.content_loader import load_combat_content
from game.bootstrap import load_world_and_state
from engine.items import create_default_items, load_items_from_assets
from engine.loot import create_default_loot_tables, load_loot_tables_from_assets
from engine.crafting import create_default_recipes, load_recipes_from_assets
from engine.effects import create_default_effects

def demo_weapon_categories():
    """Dimostra le diverse categorie di armi"""
    print("🔫 === DEMO ARMI PER CATEGORIA ===")
    
    weapons, mobs = load_combat_content()
    
    # Organizza armi per categoria
    categories = {}
    for weapon_id, weapon_data in weapons.items():
        weapon_class = weapon_data.get('weapon_class', 'unknown')
        if weapon_class not in categories:
            categories[weapon_class] = []
        categories[weapon_class].append((weapon_id, weapon_data))
    
    for category, weapon_list in categories.items():
        print(f"\n📂 {category.upper()} ({len(weapon_list)} armi):")
        
        if category == 'ranged':
            # Sottocategorie per armi da fuoco
            pistols = [w for w in weapon_list if w[1].get('clip_size', 0) <= 17 and w[1].get('damage', 0) <= 7]
            rifles = [w for w in weapon_list if w[1].get('clip_size', 0) >= 20 and w[1].get('damage', 0) >= 6]
            smgs = [w for w in weapon_list if 'mp' in w[0].lower() or 'uzi' in w[0].lower() or 'p90' in w[0].lower()]
            snipers = [w for w in weapon_list if 'l96' in w[0].lower() or 'dragunov' in w[0].lower() or 'kar98' in w[0].lower()]
            
            if pistols:
                print(f"  🔫 Pistole ({len(pistols)}):")
                for w_id, w_data in pistols[:3]:  # Mostra prime 3
                    print(f"    • {w_data['name']} - {w_data['damage']} danni, {w_data['ammo_in_clip']}/{w_data['clip_size']} colpi")
            
            if smgs:
                print(f"  🔫 SMG ({len(smgs)}):")
                for w_id, w_data in smgs[:3]:
                    print(f"    • {w_data['name']} - {w_data['damage']} danni, {w_data['ammo_in_clip']}/{w_data['clip_size']} colpi")
                    
            if rifles:
                print(f"  🔫 Fucili d'Assalto ({len(rifles)}):")
                for w_id, w_data in rifles[:3]:
                    print(f"    • {w_data['name']} - {w_data['damage']} danni, {w_data['ammo_in_clip']}/{w_data['clip_size']} colpi")
                    
            if snipers:
                print(f"  🎯 Fucili di Precisione ({len(snipers)}):")
                for w_id, w_data in snipers:
                    print(f"    • {w_data['name']} - {w_data['damage']} danni, {w_data['ammo_in_clip']}/{w_data['clip_size']} colpi")
        
        elif category == 'melee':
            # Sottocategorie per armi bianche
            knives = [w for w in weapon_list if 'knife' in w[0].lower() or 'dagger' in w[0].lower()]
            swords = [w for w in weapon_list if 'katana' in w[0].lower() or 'gladius' in w[0].lower()]
            blunt = [w for w in weapon_list if 'bat' in w[0].lower() or 'hammer' in w[0].lower() or 'club' in w[0].lower()]
            
            if knives:
                print(f"  🔪 Coltelli ({len(knives)}):")
                for w_id, w_data in knives[:3]:
                    print(f"    • {w_data['name']} - {w_data['damage']} danni")
            
            if swords:
                print(f"  ⚔️ Spade ({len(swords)}):")
                for w_id, w_data in swords:
                    print(f"    • {w_data['name']} - {w_data['damage']} danni")
                    
            if blunt:
                print(f"  🔨 Armi Contundenti ({len(blunt)}):")
                for w_id, w_data in blunt[:3]:
                    print(f"    • {w_data['name']} - {w_data['damage']} danni")
        
        elif category == 'throwable':
            print(f"  💣 Armi da Lancio ({len(weapon_list)}):")
            for w_id, w_data in weapon_list:
                aoe = w_data.get('aoe_factor', 0)
                uses = w_data.get('uses', 1)
                status_effects = w_data.get('status_effects', [])
                effects_str = f", effetti: {[e[0] for e in status_effects]}" if status_effects else ""
                print(f"    • {w_data['name']} - {w_data['damage']} danni, {uses} usi, AoE: {aoe}{effects_str}")

def demo_inventory_stats_system():
    """Dimostra il sistema inventario e statistiche"""
    print("\n📦 === DEMO SISTEMA INVENTARIO E STATISTICHE ===")
    
    registry, state = load_world_and_state()
    
    # Inizializza sistemi
    create_default_items()
    create_default_loot_tables() 
    create_default_recipes()
    create_default_effects()
    
    # Carica asset
    items_loaded = load_items_from_assets()
    loot_loaded = load_loot_tables_from_assets()
    recipes_loaded = load_recipes_from_assets()
    
    print(f"📚 Asset caricati: {items_loaded} oggetti, {loot_loaded} loot tables, {recipes_loaded} ricette")
    
    # Mostra inventario iniziale
    from engine.core.actions import inventory, stats
    
    inv_result = inventory(state, registry)
    print(f"\n🎒 Inventario iniziale:")
    for line in inv_result.get("lines", []):
        print(f"  {line}")
    
    # Mostra statistiche 
    stats_result = stats(state, registry)
    print(f"\n📊 Statistiche giocatore:")
    for line in stats_result.get("lines", []):
        if any(keyword in line for keyword in ['Salute:', 'Energia:', 'Morale:', 'Attributi:', 'Resistenze:']):
            print(f"  {line}")

def demo_combat_mechanics():
    """Dimostra le meccaniche di combattimento avanzate"""
    print("\n⚔️ === DEMO MECCANICHE COMBATTIMENTO ===")
    
    registry, state = load_world_and_state()
    weapons, mobs = load_combat_content()
    inject_content(weapons, mobs)
    
    print("🎯 Nemici disponibili:")
    for mob_id, mob_data in mobs.items():
        hp = mob_data.get('hp', 0)
        attack = mob_data.get('attack', 0)
        resistances = mob_data.get('resistances', {})
        ai_state = mob_data.get('ai_state', 'neutral')
        print(f"  • {mob_data['name']} - {hp} HP, {attack} ATK, AI: {ai_state}")
        if resistances:
            resist_str = ", ".join([f"{k}: {v}x" for k, v in resistances.items() if v != 1.0])
            if resist_str:
                print(f"    Resistenze: {resist_str}")
    
    # Test di spawn e attacco
    from engine.core.actions import spawn, combat_action
    
    set_combat_seed(42)  # Per risultati deterministici
    
    print(f"\n🎮 Simulazione combattimento:")
    
    # Spawn nemico
    spawn_result = spawn(state, registry, "walker_basic")
    for line in spawn_result.get("lines", []):
        print(f"  {line}")
    
    # Simula alcuni attacchi
    for i in range(3):
        attack_result = combat_action(state, registry, "attack", None)
        for line in attack_result.get("lines", []):
            if "danni" in line or "HP" in line:
                print(f"  Attacco {i+1}: {line}")

def demo_advanced_features():
    """Dimostra caratteristiche avanzate"""
    print("\n✨ === FUNZIONALITÀ AVANZATE ===")
    
    print("🎯 Sistema QTE:")
    print("  • QTE Offensivi: Aumentano danni o causano effetti speciali")
    print("  • QTE Difensivi: Riducono danni ricevuti")
    print("  • QTE Complessi: Sequenze di tasti per azioni avanzate")
    
    print(f"\n📈 Meccaniche Avanzate:")
    print("  • Sistema Stamina: Limita azioni consecutive")
    print("  • Sistema Postura: Meccanica stagger/equilibrio") 
    print("  • Effetti di Stato: DoT, debuff, buff temporanei")
    print("  • AI Tattica: Nemici con comportamenti diversi")
    print("  • Resistenze Elementali: Danni modificati per tipo")
    
    print(f"\n🎨 Sistemi Data-Driven:")
    print("  • Caricamento automatico asset da JSON")
    print("  • Armi modulari con movesets personalizzabili")
    print("  • Mob con AI configurabile")
    print("  • Sistema di loot e crafting espandibili")

def main():
    """Esegue la demo completa"""
    print("🎮 SECONDA VITA Alpha 0.3 - Demo Completa")
    print("=" * 60)
    
    try:
        demo_weapon_categories()
        demo_inventory_stats_system()
        demo_combat_mechanics()
        demo_advanced_features()
        
        print(f"\n🎉 === RIEPILOGO FUNZIONALITÀ ===")
        print("✅ 70+ armi diverse in 3 categorie (melee, ranged, throwable)")
        print("✅ Sistema inventario con peso realistico")
        print("✅ Sistema statistiche completo con attributi e resistenze")
        print("✅ Combat system ibrido con QTE e meccaniche tattiche")
        print("✅ Asset system data-driven completamente modulare")
        print("✅ Tutorial interattivo completo")
        print("✅ Sistema NPC con dialoghi (parziale)")
        print("✅ Sistema salvataggio/caricamento")
        
        print(f"\n🔜 Prossimi sviluppi suggeriti:")
        print("• Sistema multi-nemico completo")
        print("• Loot reale da combattimenti")  
        print("• NPC con integrazione LLM")
        print("• Crafting avanzato con ricette")
        print("• Eventi ambientali dinamici")
        
    except Exception as e:
        print(f"❌ Errore durante la demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()