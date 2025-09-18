SETTINGS = {
    "title": "Seconda Vita",
    "version": "0.3",
    "colors": False,
    "prompt": "> ",

    # --- Combat (Telltale-like) ---
    "combat_attack_interval_s": 5.0,  # ogni N secondi il walker parte all'attacco
    "combat_qte_time_s": 3.0,         # tempo per digitare la sequenza di QTE
    "combat_qte_len_min": 3,
    "combat_qte_len_max": 4,
    "combat_qte_charset": "WASD123",  # lettere/numeri semplici
    "combat_bite_damage": 1,

    # --- 0.4 Movement & Sensing ---
    "scan_radius_m": 80.0,
    "scan_energy_cost": 0.6,
    "sprint_speed_mult": 1.5,
    "sprint_energy_mult": 1.5,
    "stealth_speed_mult": 0.5,
    "stealth_energy_mult": 0.8,
    "rest_energy_per_tick": 0.5,
    "hud_enabled": True,

    # --- Movement & Proximity (Seconda Vita) ---
    "step_meters": 10.0,          # metri percorsi con 'go <dir>' se non specifichi metri
    "energy_per_meter": 0.02,     # costo energia per metro (50 m = 1 energia)
    "proximity_radius_m": 40.0,   # raggio per avvisi POI/landmark
}
