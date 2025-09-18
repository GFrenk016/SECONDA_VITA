from engine.io import say
from engine.combat import try_spawn_walker_from_noise

def on_noise(ctx, score: int):
    if score >= 2:
        say("Un fruscio distante risponde al tuo passo affrettato…")
    try_spawn_walker_from_noise(ctx, score)

def on_exposure(ctx, ticks: int):
    # futuro: aumentare leggermente il rischio se si riposa a lungo
    pass
