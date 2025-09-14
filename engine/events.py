import random
from engine.io import say
from engine.journal import log
from engine.combat import try_spawn_walker

def atmospheric_tick(ctx):
    """Eventi atmosferici semplici e leggeri."""
    r = random.random()
    if ctx.state.tick % 7 == 0 and r < 0.5 and not ctx.state.flags.get("vento2"):
        say("Le fronde si piegano tutte insieme: il bosco ascolta.")
        ctx.state.flags["vento2"] = True
        log(ctx, "Il vento ha cambiato verso.")

def encounter_tick(ctx):
    """Possibili incontri ostili (walker)."""
    try_spawn_walker(ctx, chance=0.20)

def run_events(ctx):
    """Chiamato ogni tick dal Director."""
    atmospheric_tick(ctx)
    encounter_tick(ctx)
