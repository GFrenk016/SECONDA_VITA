from __future__ import annotations
import random, time
from typing import Optional, Dict, Any
from config import SETTINGS
from engine.io import say
from engine.journal import log
from game.scenes import parse_key, world_display_name
from engine.assets import load_walkers, load_melee_weapons, pick_best_melee_from_inventory

# ----------------- Helpers stato combat -----------------
def in_combat(ctx) -> bool:
    return bool(ctx.state.flags.get("in_combat", False))

def _set_combat(ctx, active: bool):
    ctx.state.flags["in_combat"] = active

def current_enemy(ctx) -> Optional[dict]:
    return ctx.state.flags.get("enemy")

def _rng(ctx) -> random.Random:
    r = getattr(ctx, "_rng", None)
    if r is not None:
        return r
    seed = SETTINGS.get("seed")
    r = random.Random(seed) if seed is not None else random
    ctx._rng = r
    return r

# ----------------- Spawn & lifecycle -----------------
def enter_combat_with_walker(ctx, mob_id: str = "shambler"):
    if in_combat(ctx):
        return
    walkers = load_walkers()
    mob = walkers.get(mob_id, {"id":"shambler","name":"Walker barcollante","health":2,"attack_damage":1})
    _set_combat(ctx, True)
    ctx.state.flags["enemy"] = {
        "kind":"walker",
        "id": mob["id"],
        "name": mob.get("name","Walker"),
        "hp": int(mob.get("health",2)),
        "admg": int(mob.get("attack_damage",1)),
    }
    # TIMER & QTE state
    now = time.monotonic()
    ctx.state.flags["next_attack_at"] = now + float(SETTINGS.get("combat_attack_interval_s", 6.0))
    ctx.state.flags["qte_active"] = False
    ctx.state.flags["qte_seq"] = ""
    ctx.state.flags["qte_deadline"] = 0.0

    say("──────────────── COMBAT ────────────────")
    say(f"Un **{mob.get('name','Walker')}** ti punta. (attack / push / flee)")
    say("Devi agire in fretta.")
    say("───────────────────────────────────────")
    log(ctx, f"Spawn walker: {mob_id} (in_combat=True)")

def combat_tick(ctx):
    """
    Timer a secondi: se scade next_attack_at e non sei in QTE, il walker ti afferra -> parte un QTE.
    Se sei in QTE e scade la deadline -> morso.
    """
    if not in_combat(ctx):
        return

    now = time.monotonic()
    enemy = current_enemy(ctx)
    if not enemy:
        return

    qte_active = bool(ctx.state.flags.get("qte_active", False))

    # Se QTE attivo: controlla deadline
    if qte_active:
        deadline = float(ctx.state.flags.get("qte_deadline", 0.0))
        if now > deadline:
            # Fallito QTE -> morso
            dmg = int(SETTINGS.get("combat_bite_damage", 1))
            p = ctx.state.player
            p.health = max(0, p.health - dmg)
            say(f"Non fai in tempo: il walker ti morde! (Health -{dmg})")
            log(ctx, f"Walker morde (QTE fail, Health -{dmg}).")
            if p.health <= 0:
                say("Cadi a terra. Il mondo sfuma nel buio…")
                exit_combat(ctx, reason="player_down")
                ctx.state.flags["game_over"] = True
                return
            # Nuova finestra prima del prossimo attacco
            ctx.state.flags["qte_active"] = False
            ctx.state.flags["qte_seq"] = ""
            ctx.state.flags["qte_deadline"] = 0.0
            ctx.state.flags["next_attack_at"] = now + float(SETTINGS.get("combat_attack_interval_s", 6.0))
        return

    # Se NON QTE: controlla l'arrivo dell'attacco
    next_at = float(ctx.state.flags.get("next_attack_at", now + 9999))
    if now >= next_at:
        # Inizia la presa -> genera QTE
        seq = _gen_qte_sequence(ctx)
        ctx.state.flags["qte_active"] = True
        ctx.state.flags["qte_seq"] = seq
        ctx.state.flags["qte_deadline"] = now + float(SETTINGS.get("combat_qte_time_s", 3.0))
        say(f"❗ Il walker ti afferra! Liberati digitando:  qte {seq}")
        log(ctx, f"QTE start: '{seq}' (deadline {ctx.state.flags['qte_deadline']:.2f})")

def exit_combat(ctx, *, reason: str = "end"):
    _set_combat(ctx, False)
    ctx.state.flags.pop("enemy", None)
    ctx.state.flags.pop("combat_timer", None)
    ctx.state.flags.pop("stagger", None)
    log(ctx, f"Combat finito ({reason}).")

# ----------------- Durabilità armi -----------------
def _init_weapon_pool_if_needed(ctx):
    if "weapon_dura" not in ctx.state.flags:
        ctx.state.flags["weapon_dura"] = {}  # {weapon_id: remaining_uses_current_piece}

def _consume_durability(ctx, weapon_id: str) -> None:
    if weapon_id in ("fists",):
        return
    melee = load_melee_weapons()
    dur = int(melee[weapon_id].get("durability", 10))
    inv: Dict[str,int] = ctx.state.player.inventory

    _init_weapon_pool_if_needed(ctx)
    pool: Dict[str,int] = ctx.state.flags["weapon_dura"]

    rem = pool.get(weapon_id, dur)
    rem -= 1
    if rem > 0:
        pool[weapon_id] = rem
        return

    # pezzo rotto → consumi 1 unità dall'inventario
    qty = inv.get(weapon_id, 0)
    if qty > 1:
        inv[weapon_id] = qty - 1
        pool[weapon_id] = dur  # nuovo pezzo, reset uso
        say(f"Il tuo {weapon_id} si incrina… lo sostituisci in fretta.")
    else:
        # ultimo pezzo rotto → rimosso
        inv.pop(weapon_id, None)
        pool.pop(weapon_id, None)
        say(f"Il tuo {weapon_id} si spezza—ti restano solo i pugni.")

# ----------------- ATTACK (già passato) -----------------
# incolla qui la tua versione di attack(...) se non è già presente
# (quella che ti ho dato nel messaggio precedente, compatibile con equip, crit, durabilità)

# ----------------- Nuove azioni: PUSH e FLEE e ATTACK -----------------
def push(ctx, *args):
    """
    Spingi via il walker per guadagnare respiro.
    - Consuma poca energia, 70% di 'stagger' (salta il prossimo attacco nemico).
    - Resetta il timer se resti in combat.
    """
    if not in_combat(ctx):
        say("Spingere cosa?")
        return
    p = ctx.state.player
    p.energy = max(0.0, p.energy - 0.2)

    rng = _rng(ctx)
    if rng.random() <= 0.70:
        ctx.state.flags["stagger"] = 1
        say("Lo spingi con forza: il walker barcolla all'indietro.")
        log(ctx, "Walker staggered.")
    else:
        say("Provi a spingerlo ma resta addosso a te.")

    if in_combat(ctx):
        ctx.state.flags["combat_timer"] = 2

def flee(ctx, *args):
    """
    Tentativo di fuga. Se riesce, esci dal combat (60%).
    Se fallisce, il tempo si accorcia.
    """
    if not in_combat(ctx):
        say("Non stai fuggendo da nulla.")
        return
    p = ctx.state.player
    p.energy = max(0.0, p.energy - 0.3)

    rng = _rng(ctx)
    if rng.random() <= 0.60:
        say("Scatti di lato e ti liberi: abbandoni lo scontro.")
        log(ctx, "Frank fugge dal combat.")
        exit_combat(ctx, reason="flee")
    else:
        say("Cerchi una via d'uscita, ma il walker ti sbarra la strada!")
        if in_combat(ctx):
            ctx.state.flags["combat_timer"] = 1  # resta poco respiro

def attack(ctx, *args):
    """
    attack [weapon_id|nome]
      Regole:
        - Se QTE attivo: devi prima liberarti con `qte <seq>`
        - Priorità arma: 1) equip (se posseduta)  2) argomento passato  3) migliore in inventario  4) pugni
        - Coltello = one-shot kill
        - Pugni non possono uccidere (HP nemico clamp ≥ 1)
        - Hit = 0.70 + hit_bonus; se energy < 1.0: −0.15 (clamp 5–95%)
        - Consumo energia = weapon.energy_cost; durabilità consumata ad ogni colpo non a pugni
        - Dopo l’azione, se il fight continua, reset next_attack_at
    """
    # ---- vincoli di stato ----
    if not in_combat(ctx):
        say("Non c'è nulla da colpire.")
        return
    if bool(ctx.state.flags.get("qte_active", False)):
        say("Sei bloccato! Liberati prima: usa 'qte <sequenza>'.")
        return

    enemy = current_enemy(ctx)
    if not enemy or enemy.get("kind") != "walker":
        say("Il bersaglio non è chiaro.")
        return

    # ---- scelta arma ----
    inv = ctx.state.player.inventory
    melee = load_melee_weapons()

    chosen_id = None
    # 1) equip se posseduta
    equipped = getattr(ctx.state.player, "equipped", None)
    if equipped and inv.get(equipped, 0) > 0 and equipped in melee:
        chosen_id = equipped

    # 2) argomento esplicito (id o nome umano)
    if not chosen_id and args:
        token = " ".join(args).lower().strip()
        if token in melee and inv.get(token, 0) > 0:
            chosen_id = token
        else:
            name_to_id = { v.get("name","").lower(): k for k, v in melee.items() }
            wid = name_to_id.get(token)
            if wid and inv.get(wid, 0) > 0:
                chosen_id = wid

    # 3) migliore in inventario  /  4) fallback pugni
    if not chosen_id:
        chosen_id, w = pick_best_melee_from_inventory(inv)
    else:
        w = melee[chosen_id]

    # ---- statistiche arma ----
    dmg         = float(w.get("damage", 1))
    energy_cost = float(w.get("energy_cost", 0.4))
    hit_bonus   = float(w.get("hit_bonus", 0.0))
    crit_chance = float(w.get("crit_chance", 0.0))
    wname       = w.get("name", chosen_id)

    # ---- energia del player ----
    p = ctx.state.player
    p.energy = max(0.0, p.energy - energy_cost)

    # ---- chance di colpire ----
    hit_chance = 0.70 + hit_bonus
    if p.energy < 1.0:
        hit_chance -= 0.15
    hit_chance = max(0.05, min(0.95, hit_chance))

    rng = _rng(ctx)
    roll = rng.random()

    if roll <= hit_chance:
        # ----- colpo a segno -----
        # critico?
        crit = (rng.random() <= crit_chance)

        # regole speciali
        if chosen_id == "knife":
            # one-shot
            enemy["hp"] = 0
            # consumi comunque la durabilità del coltello
            _consume_durability(ctx, chosen_id)
            say("La lama prende l’orbita—un istante, e il walker collassa.")
            log(ctx, "Kill walker (arma=Coltello, one-shot).")
            exit_combat(ctx, reason="walker_killed")
            return
        else:
            dealt = int(max(1, dmg * (2 if crit else 1)))
            if chosen_id == "fists":
                # i pugni non possono uccidere
                enemy["hp"] = max(1, enemy.get("hp", 2) - dealt)
            else:
                enemy["hp"] = max(0, enemy.get("hp", 2) - dealt)
                # durabilità (non sui pugni)
                _consume_durability(ctx, chosen_id)

            if enemy["hp"] <= 0:
                line = "Il colpo spezza tutto: il walker cede e crolla."
                say(line)
                log(ctx, f"Kill walker (arma={wname}, crit={crit})")
                exit_combat(ctx, reason="walker_killed")
                return
            else:
                say(f"Colpisci con {wname}: il walker vacilla (HP {enemy['hp']}).")
                log(ctx, f"Walker ferito (HP={enemy['hp']}, arma={wname}, crit={crit})")

    else:
        # ----- colpo mancato → contrattacco -----
        admg = int(enemy.get("admg", 1))
        p.health = max(0, p.health - admg)
        say(f"Sbagli il colpo—il walker ti graffia! (Health -{admg})")
        log(ctx, f"Frank ferito (graffio, -{admg}).")
        if p.health <= 0:
            say("Cadi a terra. Il mondo sfuma nel buio…")
            exit_combat(ctx, reason="player_down")
            ctx.state.flags["game_over"] = True
            return

    # ---- respiro: resetta il timer di attacco del walker ----
    if in_combat(ctx):
        import time
        interval = float(SETTINGS.get("combat_attack_interval_s", 6.0))
        ctx.state.flags["next_attack_at"] = time.monotonic() + interval

def _rng(ctx) -> random.Random:
    r = getattr(ctx, "_rng", None)
    if r is not None:
        return r
    seed = SETTINGS.get("seed")
    r = random.Random(seed) if seed is not None else random
    ctx._rng = r
    return r

def _gen_qte_sequence(ctx) -> str:
    rng = _rng(ctx)
    charset = str(SETTINGS.get("combat_qte_charset", "WASD123"))
    nmin = int(SETTINGS.get("combat_qte_len_min", 3))
    nmax = int(SETTINGS.get("combat_qte_len_max", 4))
    n = rng.randint(nmin, nmax)
    return "".join(rng.choice(charset) for _ in range(n))

def qte_input(ctx, *args):
    """
    qte <sequenza>  — risponde alla presa. Se corretta, ti liberi e puoi agire (attack/push/flee).
    """
    if not in_combat(ctx):
        say("Non sei in combattimento.")
        return
    if not bool(ctx.state.flags.get("qte_active", False)):
        say("Non sei bloccato: agisci! (attack / push / flee)")
        return
    if not args:
        say("Devi digitare la sequenza: es. 'qte WAS'")
        return

    typed = "".join(args).upper().strip()
    goal = str(ctx.state.flags.get("qte_seq", "")).upper().strip()

    if typed == goal:
        ctx.state.flags["qte_active"] = False
        ctx.state.flags["qte_seq"] = ""
        ctx.state.flags["qte_deadline"] = 0.0
        # finestra prima del prossimo attacco
        ctx.state.flags["next_attack_at"] = time.monotonic() + float(SETTINGS.get("combat_attack_interval_s", 6.0))
        say("Ti divincoli—ti liberi dalla presa! (puoi agire)")
        log(ctx, "QTE success (liberato).")
    else:
        say("Sequenza errata! Riprova in fretta!")

# ----------------- “Idle tick” se perdi tempo in combat -----------------
def combat_idle_tick(ctx):
    """
    Chiamare quando in combat fai un'azione non-risolutiva (inventory, help, stats).
    Decrementa il timer; se scade e non c'è 'stagger', il walker ti colpisce.
    """
    if not in_combat(ctx):
        return

    t = int(ctx.state.flags.get("combat_timer", 2))
    stagger = int(ctx.state.flags.get("stagger", 0))

    if stagger > 0:
        ctx.state.flags["stagger"] = 0
        ctx.state.flags["combat_timer"] = 2
        say("Il walker recupera l'equilibrio…")
        return

    t -= 1
    if t > 0:
        ctx.state.flags["combat_timer"] = t
        say("Il tempo stringe…")
        return

    # timer scaduto → attacco gratuito del walker
    enemy = current_enemy(ctx)
    if enemy:
        dmg = int(enemy.get("admg", 1))
        p = ctx.state.player
        p.health = max(0, p.health - dmg)
        say(f"Esiti un istante: il walker ti addenta! (Health -{dmg})")
        log(ctx, f"Walker colpisce per inattività (Health -{dmg}).")
        if p.health <= 0:
            say("Cadi a terra. Il mondo sfuma nel buio…")
            exit_combat(ctx, reason="player_down")
            ctx.state.flags["game_over"] = True
            return

    if in_combat(ctx):
        ctx.state.flags["combat_timer"] = 2
