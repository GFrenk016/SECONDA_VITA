"""Sistema di spawn dinamico per oggetti e nemici in Seconda Vita.

Questo modulo gestisce lo spawn casuale di oggetti e nemici nelle aree del gioco,
inclusi rinforzi automatici durante il combattimento.
"""

import random
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from engine.core.state import GameState
from engine.core.registry import Registry
from engine.core.combat import add_enemy_to_session
from engine.items import get_item_registry

@dataclass
class SpawnRule:
    """Regola per lo spawn di oggetti o nemici"""
    item_id: str
    probability: float  # 0.0-1.0
    min_quantity: int = 1
    max_quantity: int = 1
    conditions: Dict[str, Any] = None  # Condizioni per lo spawn (tempo, area, ecc.)

@dataclass 
class EnemySpawnRule:
    """Regola per lo spawn di nemici"""
    enemy_id: str
    probability: float  # 0.0-1.0
    min_count: int = 1
    max_count: int = 3
    reinforcement_chance: float = 0.0  # Probabilità di rinforzi automatici
    conditions: Dict[str, Any] = None

# Configurazione spawn oggetti per area
AREA_ITEM_SPAWNS = {
    "limite_del_sentiero": [
        SpawnRule("Stone", 0.3, 1, 2),
        SpawnRule("Cloth", 0.2, 1, 1),
        SpawnRule("Stick", 0.4, 1, 3),
        SpawnRule("Medkit", 0.1, 1, 1),
    ],
    "radura_muschiosa": [
        SpawnRule("Medicinal Herb", 0.4, 1, 2),
        SpawnRule("Cloth", 0.3, 1, 2),
        SpawnRule("Fresh Water", 0.2, 1, 1),
        SpawnRule("Bandage", 0.1, 1, 1),
    ],
    "quercia_cava": [
        SpawnRule("Hunting Knife", 0.1, 1, 1),
        SpawnRule("Rope", 0.2, 1, 1),
        SpawnRule("Canned Beans", 0.3, 1, 2),
        SpawnRule("Stone", 0.4, 1, 3),
    ],
    "ruscello_sommerso": [
        SpawnRule("Fresh Water", 0.6, 1, 2),
        SpawnRule("Fish", 0.3, 1, 1), 
        SpawnRule("Cloth", 0.2, 1, 1),
        SpawnRule("Stick", 0.3, 1, 2),
    ],
    "soglia_radicata": [
        SpawnRule("Medicinal Herb", 0.5, 1, 3),
        SpawnRule("Rope", 0.2, 1, 1),
        SpawnRule("Bandage", 0.2, 1, 1),
        SpawnRule("Stone", 0.3, 1, 2),
    ],
    # Area di test con tutto
    "test_arena": [
        SpawnRule("Hunting Knife", 0.3, 1, 1),
        SpawnRule("Medkit", 0.4, 1, 2),
        SpawnRule("Canned Beans", 0.5, 1, 3),
        SpawnRule("Cloth", 0.6, 1, 4),
        SpawnRule("Stone", 0.7, 1, 5),
        SpawnRule("Rope", 0.3, 1, 2),
        SpawnRule("Bandage", 0.4, 1, 2),
        SpawnRule("Fresh Water", 0.5, 1, 2),
        SpawnRule("Medicinal Herb", 0.4, 1, 3),
    ]
}

# Configurazione spawn nemici per area
AREA_ENEMY_SPAWNS = {
    "limite_del_sentiero": [
        EnemySpawnRule("walker_basic", 0.2, 1, 2, 0.1),
        EnemySpawnRule("rabbit", 0.4, 1, 3, 0.0),
    ],
    "radura_muschiosa": [
        EnemySpawnRule("walker_basic", 0.3, 1, 2, 0.15),
        EnemySpawnRule("walker_runner", 0.1, 1, 1, 0.2),
        EnemySpawnRule("rabbit", 0.3, 1, 2, 0.0),
    ],
    "quercia_cava": [
        EnemySpawnRule("walker_basic", 0.25, 1, 2, 0.2),
        EnemySpawnRule("walker_tough", 0.1, 1, 1, 0.25),
    ],
    "ruscello_sommerso": [
        EnemySpawnRule("walker_basic", 0.15, 1, 1, 0.1),
        EnemySpawnRule("rabbit", 0.5, 1, 4, 0.0),
    ],
    "soglia_radicata": [
        EnemySpawnRule("walker_basic", 0.3, 1, 3, 0.2),
        EnemySpawnRule("walker_runner", 0.15, 1, 2, 0.3),
        EnemySpawnRule("walker_tough", 0.05, 1, 1, 0.4),
    ],
    # Area di test con spawn intensi
    "test_arena": [
        EnemySpawnRule("walker_basic", 0.4, 1, 3, 0.3),
        EnemySpawnRule("walker_runner", 0.3, 1, 2, 0.4),
        EnemySpawnRule("walker_tough", 0.2, 1, 1, 0.5),
        EnemySpawnRule("rabbit", 0.3, 1, 2, 0.0),
    ]
}

def spawn_random_items(state: GameState, registry: Registry, area_id: str) -> List[str]:
    """Spawna oggetti casuali nell'area corrente.
    
    Returns:
        Lista di messaggi sui oggetti spawnati
    """
    messages = []
    
    if area_id not in AREA_ITEM_SPAWNS:
        return messages
    
    spawn_rules = AREA_ITEM_SPAWNS[area_id]
    item_registry = get_item_registry()
    
    for rule in spawn_rules:
        if random.random() <= rule.probability:
            # Controlla condizioni se presenti
            if rule.conditions:
                if not _check_conditions(state, rule.conditions):
                    continue
            
            # Determina quantità
            quantity = random.randint(rule.min_quantity, rule.max_quantity)
            
            # Verifica che l'oggetto esista
            if rule.item_id in item_registry:
                # Aggiungi all'inventario del giocatore
                if hasattr(state, 'inventory') and state.inventory:
                    if rule.item_id in state.inventory:
                        state.inventory[rule.item_id] += quantity
                    else:
                        state.inventory[rule.item_id] = quantity
                    
                    item_name = item_registry[rule.item_id]["name"]
                    if quantity == 1:
                        messages.append(f"🎁 Hai trovato: {item_name}")
                    else:
                        messages.append(f"🎁 Hai trovato: {item_name} x{quantity}")
    
    return messages

def spawn_random_enemies(state: GameState, registry: Registry, area_id: str) -> List[str]:
    """Spawna nemici casuali nell'area corrente.
    
    Returns:
        Lista di messaggi sui nemici spawnati
    """
    messages = []
    
    if area_id not in AREA_ENEMY_SPAWNS:
        return messages
    
    spawn_rules = AREA_ENEMY_SPAWNS[area_id]
    
    for rule in spawn_rules:
        if random.random() <= rule.probability:
            # Controlla condizioni se presenti
            if rule.conditions:
                if not _check_conditions(state, rule.conditions):
                    continue
            
            # Determina numero di nemici
            count = random.randint(rule.min_count, rule.max_count)
            
            # Spawna nemici
            from engine.core.actions import spawn, combat_action
            
            try:
                # Se non siamo in combattimento, inizia con il primo nemico
                if not state.combat_session or state.combat_session.get('phase') == 'ended':
                    result = spawn(state, registry, rule.enemy_id)
                    if result and result.get("lines"):
                        messages.extend(result["lines"])
                    
                    # Aggiungi i restanti se count > 1
                    if count > 1:
                        combat_result = combat_action(state, registry, f"spawn {rule.enemy_id} {count-1}")
                        if combat_result and combat_result.get("lines"):
                            messages.extend(combat_result["lines"])
                else:
                    # Siamo già in combattimento, aggiungi tutti
                    combat_result = combat_action(state, registry, f"spawn {rule.enemy_id} {count}")
                    if combat_result and combat_result.get("lines"):
                        messages.extend(combat_result["lines"])
                
                # Gestisci rinforzi automatici
                if rule.reinforcement_chance > 0 and random.random() <= rule.reinforcement_chance:
                    reinforcements = random.randint(1, 2)
                    combat_result = combat_action(state, registry, f"spawn {rule.enemy_id} {reinforcements}")
                    if combat_result and combat_result.get("lines"):
                        messages.append(f"⚡ Arrivano rinforzi!")
                        messages.extend(combat_result["lines"])
                        
            except Exception as e:
                messages.append(f"Errore spawn nemico {rule.enemy_id}: {e}")
    
    return messages

def trigger_area_spawns(state: GameState, registry: Registry, area_id: str, spawn_items: bool = True, spawn_enemies: bool = True) -> List[str]:
    """Triggera tutti gli spawn per un'area.
    
    Args:
        state: Stato del gioco
        registry: Registro del gioco  
        area_id: ID dell'area
        spawn_items: Se spawnare oggetti
        spawn_enemies: Se spawnare nemici
        
    Returns:
        Lista di messaggi combinati
    """
    messages = []
    
    if spawn_items:
        item_messages = spawn_random_items(state, registry, area_id)
        messages.extend(item_messages)
    
    if spawn_enemies:
        enemy_messages = spawn_random_enemies(state, registry, area_id)
        messages.extend(enemy_messages)
    
    return messages

def _check_conditions(state: GameState, conditions: Dict[str, Any]) -> bool:
    """Controlla se le condizioni per lo spawn sono soddisfatte."""
    
    # Controlla ora del giorno
    if "time_phase" in conditions:
        required_phase = conditions["time_phase"]
        if hasattr(state, 'time_phase') and state.time_phase != required_phase:
            return False
    
    # Controlla meteo
    if "weather" in conditions:
        required_weather = conditions["weather"]
        if hasattr(state, 'weather') and state.weather != required_weather:
            return False
    
    # Controlla se in combattimento
    if "in_combat" in conditions:
        required_combat = conditions["in_combat"]
        in_combat = bool(state.combat_session and state.combat_session.get('phase') != 'ended')
        if in_combat != required_combat:
            return False
    
    return True

def get_spawn_info(area_id: str) -> Dict[str, List]:
    """Ottieni informazioni sui possibili spawn di un'area."""
    return {
        "items": AREA_ITEM_SPAWNS.get(area_id, []),
        "enemies": AREA_ENEMY_SPAWNS.get(area_id, [])
    }