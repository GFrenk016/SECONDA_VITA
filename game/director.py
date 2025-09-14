from engine.events import run_events

def run_director(ctx):
    """
    Punto centrale per orchestrare cosa succede a ogni tick,
    prima/dopo i moduli futuri (scelte, relazioni, ecc.).
    """
    # In futuro: ordine, priorità, gating su flags/stats
    run_events(ctx)
