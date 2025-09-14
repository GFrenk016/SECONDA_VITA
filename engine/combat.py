import random
from engine.io import say
from engine.journal import log

ENEMIES_KEY = "enemies"  # flags['enemies'] = dict[location_key -> int]

def enemies_here(ctx) -> int:
    loc = ctx.state.location_key
    enemies = ctx.state.flags.get(ENEMIES_KEY, {})
    return int(enemies.get(loc, 0))

def set_enemies_here(ctx, count: int):
    loc = ctx.state.location_key
    enemies = ctx.state.flags.get(ENEMIES_KEY, {})
    if count <= 0:
        enemies.pop(loc, None)
    else:
        enemies[loc] = count
    ctx.state.flags[ENEMIES_KEY] = enemies

def try_spawn_walker(ctx, chance: float = 0.25):
    """Tenta di spawnare 1 walker nella location corrente, se non ce ne sono."""
    if enemies_here(ctx) > 0:
        return
    if random.random() < chance:
        set_enemies_here(ctx, 1)
        say("Tra gli alberi si trascina un vagante. Il suo respiro è un fruscio.")
        log(ctx, "Un walker è comparso qui.")

def attack(ctx, *args):
    """Comando 'attack' (ENG). Usa il coltello se presente, altrimenti pugni."""
    n = enemies_here(ctx)
    if n <= 0:
        say("Non c'è nessuno da colpire.")
        return

    p = ctx.state.player
    weapon = "coltello" if p.inventory.get("coltello", 0) > 0 else None

    # Costi ed esiti base
    p.energy = max(0, min(100, p.energy - 5))  # affaticamento
    if weapon:
        hit_chance = 0.75
        dmg_kill = True
        fail_hp_loss = 5
        text_hit = "Il coltello entra morbido sotto l’osso. Il vagante crolla."
        text_miss = "La lama graffia soltanto. Il vagante ti urta con violenza."
    else:
        hit_chance = 0.35
        dmg_kill = True
        fail_hp_loss = 12
        text_hit = "Colpisci alla tempia con il pugno chiuso: il collo cede di lato."
        text_miss = "Sbagli il tempo. Il vagante ti graffia, brucia."

    import random as _r
    if _r.random() < hit_chance:
        # ucciso
        set_enemies_here(ctx, n - (1 if dmg_kill else 0))
        say(text_hit)
        log(ctx, "Frank ha eliminato un vagante.")
        p.morale = max(0, min(100, p.morale + 2))
    else:
        # subisci danno
        p.health = max(0, min(100, p.health - fail_hp_loss))
        say(text_miss + f" (-{fail_hp_loss} HP)")
        log(ctx, f"Frank è stato ferito in combattimento (-{fail_hp_loss} HP).")
        if p.health == 0:
            say("Il mondo si stringe. Freddo. Buio.")
            log(ctx, "Frank è collassato.")
            # segnala al core che è game over
            ctx.state.flags["game_over"] = True
