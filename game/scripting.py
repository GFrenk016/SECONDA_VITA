from engine.io import say
from engine.commands import cmd_look
from engine.journal import log

def on_bootstrap(ctx):
    say("Il bosco trattiene il fiato. Frank ascolta. Qualcosa lo chiama da nord.")
    log(ctx, "Frank si è risvegliato nella foresta.")
    cmd_look(ctx)

def on_tick(ctx):
    # Evento atmosferico semplice già c'è, qui lasciamo solo un trigger di esempio
    if ctx.state.tick == 3 and not ctx.state.flags.get("vento"):
        say("Un soffio di vento sposta gli aghi: pare un sussurro. Non sei solo.")
        ctx.state.flags["vento"] = True
        log(ctx, "Il vento si è alzato tra i pini.")
