from engine.io import say

def on_bootstrap(ctx):
    # Messaggio iniziale + prima descrizione location
    say("A chill runs through the trees. The world waits.")
    from engine.commands import cmd_look
    cmd_look(ctx)
def on_tick(ctx):
    # Esempio di evento passivo: dopo 10 tick setta un flag
    if ctx.state.tick == 10 and not ctx.state.flags.get("heard_bird"):
        say("Far away, a lone bird cries. You are not alone.")
        ctx.state.flags["heard_bird"] = True