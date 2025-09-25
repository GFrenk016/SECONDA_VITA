#!/usr/bin/env python3
"""
DEMO COMPLETO - SECONDA VITA Alpha 0.3
Dimostrazione avanzata di tutte le funzionalità implementate nel progetto.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.core.loader.content_loader import load_combat_content, load_mob_by_path
from game.bootstrap import load_world_and_state
from engine.core.actions import *
from engine.core.combat import inject_content
import engine.core.combat as combat


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"🎮 {title}")
    print('='*60)


def print_section(title: str):
    """Print a section header."""
    print(f"\n🔹 {title}")
    print('-'*40)


def demo_world_exploration():
    """Demo del sistema di esplorazione del mondo."""
    print_header("SISTEMA DI ESPLORAZIONE MONDO")
    
    # Initialize game
    registry, state = load_world_and_state()
    
    print_section("Informazioni Iniziali")
    result = look(state, registry)
    for line in result['lines']:
        print(f"  {line}")
    
    print_section("Sistema Temporale Dinamico")
    result = status(state, registry)
    for line in result['lines']:
        print(f"  {line}")
    
    # Time progression
    print_section("Avanzamento Temporale")
    print("  ⏰ Facciamo passare 45 minuti...")
    wait_result = wait(state, registry, 45)
    for line in wait_result['lines']:
        print(f"  {line}")
    
    # Look again to see changes
    print_section("Ambiente Dopo il Tempo")
    result = look(state, registry)
    for line in result['lines']:
        print(f"  {line}")


def demo_weapon_system():
    """Demo del sistema di armi avanzato."""
    print_header("SISTEMA ARMAMENTI (70+ ARMI)")
    
    # Load weapons
    weapons, mobs = load_combat_content()
    
    print_section("Categorie di Armi Caricate")
    weapon_categories = {}
    for weapon_id, weapon_data in weapons.items():
        category = weapon_data.get('weapon_class', 'unknown')
        if category not in weapon_categories:
            weapon_categories[category] = []
        weapon_categories[category].append(weapon_data.get('name', weapon_id))
    
    for category, weapon_list in weapon_categories.items():
        print(f"  📂 {category.upper()}: {len(weapon_list)} armi")
        for weapon in weapon_list[:3]:  # Show first 3
            print(f"    • {weapon}")
        if len(weapon_list) > 3:
            print(f"    ... e altre {len(weapon_list)-3} armi")
    
    print_section("Esempi di Armi Dettagliate")
    
    # Show detailed weapon examples
    example_weapons = ['knife', 'assault_rifle', 'molotov', 'sledgehammer']
    for weapon_id in example_weapons:
        if weapon_id in weapons:
            weapon = weapons[weapon_id]
            print(f"  🔫 {weapon.get('name', weapon_id)}")
            print(f"     Tipo: {weapon.get('weapon_class', 'N/A')}")
            print(f"     Danno: {weapon.get('damage', 0)}")
            if 'movesets' in weapon:
                moves = list(weapon['movesets'].keys())
                print(f"     Mosse: {', '.join(moves)}")
            print()


def demo_passive_mobs_system():
    """Demo del sistema di mob passivi."""
    print_header("SISTEMA MOB PASSIVI & INTERAZIONI")
    
    registry, state = load_world_and_state()
    
    print_section("Struttura Organizzata dei Mob")
    
    mob_categories = {
        'animals': 'Animali Selvatici',
        'humans': 'Umani Sopravvissuti/Banditi', 
        'walkers': 'Zombie e Vaganti'
    }
    
    for category, description in mob_categories.items():
        print(f"  📁 {category}/: {description}")
        
        # List mobs in category
        import os
        mob_path = f"assets/mobs/{category}"
        if os.path.exists(mob_path):
            mob_files = [f for f in os.listdir(mob_path) if f.endswith('.json')]
            for mob_file in mob_files:
                mob_data = load_mob_by_path(f"assets/mobs/{category}/{mob_file}")
                if mob_data:
                    ai_state = mob_data.get('ai_state', 'unknown')
                    print(f"    • {mob_data.get('name', 'N/A')} (AI: {ai_state})")
        print()
    
    print_section("Demo Interazioni Passive")
    
    # Demo hunting
    print("  🏹 CACCIA - Animali Passivi")
    deer_data = load_mob_by_path('assets/mobs/animals/deer.json')
    if deer_data:
        print(f"    Target: {deer_data.get('name', 'N/A')}")
        print(f"    Comportamenti: {deer_data.get('behavioral_traits', {})}")
        print(f"    Comandi: hunt (caccia con probabilità fuga)")
    
    print("\n  🤝 NEGOZIAZIONE - Umani Arresi")
    bandit_data = load_mob_by_path('assets/mobs/humans/bandit_surrendered.json')
    if bandit_data:
        print(f"    Target: {bandit_data.get('name', 'N/A')}")
        print(f"    Stato AI: {bandit_data.get('ai_state', 'N/A')}")
        print(f"    Comandi: negotiate (risoluzione pacifica)")
    
    print("\n  🕸️ CATTURA - Mob Feriti")
    walker_data = load_mob_by_path('assets/mobs/walkers/walker_wounded.json')
    if walker_data:
        print(f"    Target: {walker_data.get('name', 'N/A')}")
        print(f"    Stato: {walker_data.get('ai_state', 'N/A')}")
        print(f"    Comandi: capture (cattura con loot bonus)")


def demo_combat_system():
    """Demo del sistema di combattimento avanzato."""
    print_header("SISTEMA COMBATTIMENTO AVANZATO")
    
    registry, state = load_world_and_state()
    
    print_section("Caratteristiche Combat System")
    print("""  🎯 REALTIME IBRIDO:
    • Timer nemici automatici con QTE difensivi
    • Stamina e Postura (Poise) per profondità tattica
    • Tipi di danno con resistenze/vulnerabilità
    • Effetti di stato con durata e tick
    • Sistema qualità colpi (graze/normal/critical)
    
  ⚔️ MOSSE SPECIALIZZATE:
    • Light/Heavy/Thrust per ogni arma
    • Reach, windup, recovery, noise per bilanciamento
    • AI tattica con stati (aggressive/cautious/pack/passive)
    
  🎮 QTE AVANZATI:
    • QTE complessi alfanumerici (3-5 caratteri)
    • QTE mirati: braccia, gambe, testa, busto
    • Effetti: riduzione danno, bonus, stagger, push
    
  🏹 SUPPORTO MULTI-ARMA:
    • Melee: combos e cleave
    • Ranged: aimed/snap, munizioni, reload
    • Throwable: AoE, usi limitati
    • Heavy: penetrazione multipla""")
    
    print_section("Stati AI Implementati")
    ai_states = {
        'aggressive': 'Attacco diretto, priorità danni alti',
        'cautious': 'Difensivo, sfrutta vulnerabilità nemiche', 
        'pack': 'Cooperazione di gruppo, focus coordinato',
        'passive': 'Non aggressivo, solo difesa se attaccato',
        'surrendered': 'Arreso, può essere catturato o negoziato',
        'fleeing': 'In fuga, priorità evasione e mobilità'
    }
    
    for state_name, description in ai_states.items():
        print(f"    • {state_name}: {description}")


def demo_loot_crafting_system():
    """Demo del sistema loot e crafting."""
    print_header("SISTEMA LOOT & INVENTARIO")
    
    registry, state = load_world_and_state()
    
    print_section("Sistema Inventario Avanzato")
    result = inventory(state, registry)
    for line in result['lines']:
        print(f"  {line}")
    
    print_section("Nuovi Oggetti Loot")
    new_items = [
        ("carne_cruda", "Cibo da animali cacciati"),
        ("pelle", "Materiale per crafting armature"),
        ("corna", "Materiale per armi"),
        ("medicine_scadute", "Consumabile rischioso"),
        ("foto_famiglia", "Oggetto narrativo con impatto morale"),
        ("mappa_tesoro", "Quest item da negoziazioni")
    ]
    
    for item_id, description in new_items:
        print(f"    • {item_id}: {description}")
    
    print_section("Meccaniche Loot Avanzate")
    print("""    🎲 SISTEMA PROBABILISTICO:
    • Drop rates configurabili per mob
    • Bonus loot per interazioni speciali (caccia, cattura)
    • Loot differenziato per tipo di mob
    
    🎒 GESTIONE PESO E STACK:
    • Limiti di stack per oggetti
    • Sistema peso realistico
    • Equipaggiamento con slot dedicati""")


def demo_npc_system():
    """Demo del sistema NPC avanzato."""
    print_header("SISTEMA NPC & DIALOGHI")
    
    print_section("NPC Implementati")
    npc_info = [
        ("Forest Guardian", "Guardiano del bosco con conoscenze mistiche"),
        ("Wandering Merchant", "Mercante itinerante con oggetti rari")
    ]
    
    for npc_name, description in npc_info:
        print(f"    • {npc_name}: {description}")
    
    print_section("Caratteristiche Sistema NPC")
    print("""    🤖 AI CONVERSAZIONALE:
    • Integrazione Ollama opzionale per dialoghi dinamici
    • Fallback a risposte predefinite se AI non disponibile
    • Sistema memoria conversazioni
    
    📅 SCHEDULE & MOOD:
    • Stati temporali (busy/sleeping/available)
    • Mood tracking per personalità
    • Posizioni dinamiche nel mondo
    
    💬 COMANDI DIALOGO:
    • talk <npc>: inizia conversazione
    • say <messaggio>: comunicazione libera""")


def demo_technical_architecture():
    """Demo dell'architettura tecnica."""
    print_header("ARCHITETTURA TECNICA")
    
    print_section("Struttura Modulare")
    print("""    📁 ORGANIZZAZIONE CODICE:
    engine/
    ├── core/
    │   ├── combat_system/     # Sistema combattimento modulare
    │   ├── loader/           # Caricamento assets dinamico  
    │   ├── npc/             # Sistema NPC e dialoghi
    │   └── model/           # Modelli dati core
    ├── inventory.py         # Gestione inventario
    ├── stats.py            # Sistema statistiche
    └── crafting.py         # Sistema crafting (base)
    
    assets/
    ├── weapons/            # 70+ armi organizzate
    ├── mobs/              # Mob categorizzati
    │   ├── animals/       # Animali selvatici
    │   ├── humans/        # Umani sopravvissuti  
    │   └── walkers/       # Zombie e vaganti
    ├── npcs/              # Definizioni NPC
    └── world/             # Struttura mondo""")
    
    print_section("Sistema di Test Completo")
    print("""    🧪 TESTING AVANZATO:
    • 15+ file di test specializzati
    • Test combat realtime e QTE
    • Test sistema mob passivi  
    • Test integrazione NPC
    • Test narrative systems
    • Test multi-enemy e advanced tactics""")
    
    print_section("Configurazione Flessibile")
    print("""    ⚙️ CONFIG CENTRALIZZATA:
    • config.py per parametri game
    • Variabili d'ambiente per override
    • Time scale configurabile
    • QTE complexity settings
    • Combat timing parameters""")


def run_complete_demo():
    """Esegue la demo completa di SECONDA VITA Alpha 0.3."""
    print("🚀 SECONDA VITA Alpha 0.3 - ANALISI COMPLETA E PROFONDA")
    print("=" * 80)
    
    try:
        demo_world_exploration()
        demo_weapon_system()
        demo_passive_mobs_system()
        demo_combat_system()
        demo_loot_crafting_system()
        demo_npc_system()
        demo_technical_architecture()
        
        print_header("RIASSUNTO FINALE")
        print("""
🎯 SECONDA VITA Alpha 0.3 - FUNZIONALITÀ COMPLETE:

✅ MONDO & ESPLORAZIONE:
   • Clock realtime con sistema meteo dinamico
   • 6+ aree esplorabili con descrizioni immersive
   • Memoria visite e varianti temporali

✅ COMBATTIMENTO (70+ ARMI):
   • Sistema ibrido realtime con QTE avanzati
   • 4 categorie armi: melee, ranged, throwable, heavy
   • AI tattica con 6 stati comportamentali
   • Stamina, postura, effetti di stato

✅ MOB PASSIVI & INTERAZIONI:
   • Struttura organizzata: animals/humans/walkers
   • Comandi speciali: hunt, capture, negotiate
   • Meccaniche morali e conseguenze etiche
   • Loot differenziato per tipo interazione

✅ INVENTARIO & LOOT:
   • Sistema peso e stack realistici
   • 30+ oggetti con drop probabilistici
   • Equipaggiamento multi-slot
   • Materiali crafting e consumabili

✅ NPC & DIALOGHI:
   • AI conversazionale con Ollama
   • Sistema memoria e mood tracking
   • Schedule temporali dinamici
   • 2 NPC implementati con personalità uniche

✅ ARCHITETTURA ROBUSTA:
   • Codice modulare e estensibile
   • Assets data-driven configurabili
   • 15+ test suite automatizzati
   • Config centralizzata e flessibile

🏆 RISULTATO: Motore narrativo completo pronto per espansioni narrative profonde!
        """)
        
    except Exception as e:
        print(f"\n❌ Errore durante la demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_complete_demo()