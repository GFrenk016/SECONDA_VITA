#!/usr/bin/env python3
"""
Test interattivo del sistema di combattimento avanzato
"""

import subprocess
import sys

def test_combat_scenario():
    """Test di uno scenario di combattimento completo"""
    
    commands = [
        "1",  # Inizia partita
        "look",  # Osserva l'ambiente
        "inventory",  # Controlla inventario
        "stats",  # Controlla statistiche
        "spawn walker_basic",  # Genera un nemico
        "status",  # Controlla stato combattimento
        "attack",  # Attacca
        "status",  # Controlla dopo attacco
        "attack",  # Attacca di nuovo
        "attack",  # Continua ad attaccare
        "attack",  # Continua
        "status",  # Controlla se nemico è morto
        "inventory",  # Verifica se ci sono cambiamenti
        "quit"  # Esci
    ]
    
    print("=== Test Scenario Combattimento Completo ===")
    print("Comandi da eseguire:")
    for i, cmd in enumerate(commands, 1):
        print(f"{i:2}. {cmd}")
    
    print(f"\nEseguendo {len(commands)} comandi...")
    
    try:
        # Crea il processo
        process = subprocess.Popen(
            ['python', 'run.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Invia tutti i comandi
        input_str = '\n'.join(commands) + '\n'
        stdout, _ = process.communicate(input=input_str, timeout=15)
        
        # Analizza l'output
        lines = stdout.split('\n')
        combat_lines = []
        inventory_lines = []
        status_lines = []
        
        for line in lines:
            if any(word in line.lower() for word in ['attacca', 'colpisce', 'danni', 'hp', 'nemico']):
                combat_lines.append(line)
            elif 'inventario' in line.lower() or 'peso:' in line.lower():
                inventory_lines.append(line)
            elif any(word in line.lower() for word in ['orario:', 'fase:', 'meteo:']):
                status_lines.append(line)
        
        print("\n=== RISULTATI COMBATTIMENTO ===")
        for line in combat_lines[-10:]:  # Ultimi 10 eventi di combattimento
            if line.strip():
                print(f"  {line}")
        
        print("\n=== STATO FINALE ===")
        for line in status_lines[-3:]:  # Ultimi 3 status
            if line.strip():
                print(f"  {line}")
        
        return process.returncode == 0
        
    except subprocess.TimeoutExpired:
        process.kill()
        print("TIMEOUT: Il combattimento ha richiesto troppo tempo")
        return False
    except Exception as e:
        print(f"ERRORE: {e}")
        return False

def test_weapon_switching():
    """Test del cambio armi durante combattimento"""
    
    commands = [
        "1",  # Inizia partita  
        "inventory",  # Vedi armi disponibili
        # Potremmo equipaggiare diverse armi se il sistema lo supporta
        "spawn walker_basic",
        "attack",
        "quit"
    ]
    
    print("\n=== Test Cambio Armi ===")
    # Per ora testiamo solo l'arma base, in futuro si potrebbe estendere
    
if __name__ == "__main__":
    print("Test Sistema Combattimento Avanzato")
    print("=" * 50)
    
    success = test_combat_scenario()
    if success:
        print("\n✅ Test combattimento completato con successo!")
    else:
        print("\n❌ Test combattimento fallito!")
        
    test_weapon_switching()
    
    print("\n" + "=" * 50)
    print("Analisi completa!")