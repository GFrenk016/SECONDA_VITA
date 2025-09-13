from engine.io import say
from engine.commands import cmd_look

def on_bootstrap(ctx):
    # Narrativa in ITA
    say("Il bosco trattiene il fiato. Frank ascolta. Qualcosa lo chiama da nord.")
    cmd_look(ctx)  # mostra la location iniziale

def on_tick(ctx):
    # Piccolo evento atmosferico dopo 3 comandi
    if ctx.state.tick == 3 and not ctx.state.flags.get("vento"):
        say("Un soffio di vento sposta gli aghi: pare un sussurro. Non sei solo.")
        ctx.state.flags["vento"] = True
