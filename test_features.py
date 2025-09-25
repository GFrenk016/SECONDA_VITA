#!/usr/bin/env python3
"""
Test script per esplorare le nuove funzionalità di SECONDA VITA Alpha 0.3
"""

import sys
import subprocess
import time

def send_commands_to_game(commands):
    """Invia una serie di comandi al gioco e cattura l'output"""
    try:
        # Avvia il processo del gioco
        process = subprocess.Popen(
            ['python', 'run.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Invia i comandi
        command_str = '\n'.join(commands) + '\n'
        stdout, stderr = process.communicate(input=command_str, timeout=10)
        
        return stdout, stderr, process.returncode
        
    except subprocess.TimeoutExpired:
        process.kill()
        return "TIMEOUT", "", -1
    except Exception as e:
        return f"ERROR: {e}", "", -1

def test_basic_commands():
    """Test dei comandi base"""
    print("=== Test Comandi Base ===")
    commands = [
        "1",  # Inizia partita
        "look",
        "status", 
        "inventory",
        "stats",
        "where",
        "quit"
    ]
    
    stdout, stderr, code = send_commands_to_game(commands)
    print(f"Exit code: {code}")
    print("Output:")
    print(stdout[-1000:])  # Ultimi 1000 caratteri per evitare spam

def test_combat_system():
    """Test del nuovo sistema di combattimento"""
    print("\n=== Test Sistema Combattimento ===")
    commands = [
        "1",  # Inizia partita
        "spawn walker_basic",
        "status",
        "attack",
        "qte t",  # Prova un QTE
        "status",
        "flee",
        "quit"
    ]
    
    stdout, stderr, code = send_commands_to_game(commands)
    print(f"Exit code: {code}")
    print("Output:")
    print(stdout[-1000:])

def test_weapons():
    """Test delle nuove armi"""
    print("\n=== Test Armi ===")
    # Qui dovremmo testare il caricamento e uso delle armi
    # Ma prima dobbiamo vedere come equipaggiare armi nel gioco
    pass

if __name__ == "__main__":
    print("Testing SECONDA VITA Alpha 0.3 Features")
    print("=" * 50)
    
    test_basic_commands()
    test_combat_system()
    
    print("\nTest completati!")