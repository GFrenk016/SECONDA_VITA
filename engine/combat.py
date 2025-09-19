# combat.py — Strict Timer Mode
# Una sola pipeline nemica: TIMER -> QTE -> BITE (niente morsi "da idle").
# Push (stagger) salta il prossimo attacco e riprogramma. Flee, Attack, QTE coerenti.
# Idle non fa danno: accorcia 'next_attack_at' così da generare QTE al prossimo tick.

from __future__ import annotations
import time
import random
from typing import Optional, Dict, Any

from config import SETTINGS
from engine.io import say
from engine.journal import log
from engine.assets import (
    load_walkers,
    load_melee_weapons,
    pick_best_melee_from_inventory,
)

# ============================================================================
# Stato & Helpers
# ============================================================================

def in_combat(ctx) -> bool:
    return bool(ctx.state.flags.get("in_combat", False))

def _set_combat(ctx, active: bool):
    ctx.state.flags["in_combat"] = active

def current_enemies(ctx) -> list:
    return ctx.state.flags.get("enemies", [])

def _rng(ctx) -> random.Random:
    r = getattr(ctx, "_rng", None)
    if r is not None:
        return r
    seed = SETTINGS.get("seed")
    r = random.Random(seed) if seed is not None else random
    ctx._rng = r
    return r

def _reset_next_attack(ctx, *, now: float | None = None, extra: float = 0.0) -> None:
    """Riparte sempre da zero: sovrascrive il vecchio timer."""
    if now is None:
        now = time.monotonic()
    base = float(SETTINGS.get("combat_attack_interval_s", 6.0))
    ctx.state.flags["next_attack_at"] = now + base + float(extra)

def _gen_qte_sequence(ctx) -> str:
    rng = _rng(ctx)
    charset = str(SETTINGS.get("combat_qte_charset", "WASD123"))
    nmin = int(SETTINGS.get("combat_qte_len_min", 3))
    nmax = int(SETTINGS.get("combat_qte_len_max", 4))
    n = rng.randint(nmin, nmax)
    return "".join(rng.choice(charset) for _ in range(n))

def _ensure_fists(melee: Dict[str, Any]) -> None:
    if "fists" not in melee:
        melee["fists"] = {
            "name": "Pugni",
            "damage": 1,
            "energy_cost": 0.3,
            "hit_bonus": -0.10,
            "crit_chance": 0.0,
            "durability": 999999,
        }

def _debug(ctx, msg: str):
    if SETTINGS.get("debug_combat"):
        say(f"[COMBAT-DBG] {msg}")

# ============================================================================
# Lifecycle
# ============================================================================

def enter_combat_with_walker(ctx, mob_ids=None):
    """
    Avvia un combattimento con una lista di mob_id (o uno solo).
    """
    if in_combat(ctx):
        return
    walkers = load_walkers()
    mob_ids_local = mob_ids
    if mob_ids_local is None:
        mob_ids_local = ["shambler"]
    elif isinstance(mob_ids_local, str):
        mob_ids_local = [mob_ids_local]
    enemies = []
    for mob_id in mob_ids_local:
        mob = walkers.get(mob_id, {
            "id": "shambler",
            "name": "Walker barcollante",
            "health": 2,
            "attack_damage": 1
        })
        enemies.append({
            "kind": "walker",
            "id": mob.get("id", "shambler"),
            "name": mob.get("name", "Walker"),
            "hp": int(mob.get("health", 2)),
            "admg": int(mob.get("attack_damage", 1)),
        })
    # log dopo la definizione di mob_ids_local
        mob = walkers.get(mob_id, {
            "id": "shambler",
            "name": "Walker barcollante",
            "health": 2,
            "attack_damage": 1
        })
        enemies.append({
            "kind": "walker",
            "id": mob.get("id", "shambler"),
            "name": mob.get("name", "Walker"),
            "hp": int(mob.get("health", 2)),
            "admg": int(mob.get("attack_damage", 1)),
        })
    _set_combat(ctx, True)
    ctx.state.flags.update({
        "enemies": enemies,
        "qte_active": False,
        "qte_seq": "",
        "qte_deadline": 0.0,
        "stagger": 0,
        "combat_timer": 2,
    })
    now = time.monotonic()
    _reset_next_attack(ctx, now=now)
    say("──────────────── COMBAT ────────────────")
    _print_enemies(ctx)
    say("(attack [n] / push [n] / flee)")
    say("Devi agire in fretta.")
    say("───────────────────────────────────────")
    log(ctx, f"Spawn walkers: {','.join(mob_ids_local)} (in_combat=True)")
    _debug(ctx, f"enter: next_at={ctx.state.flags['next_attack_at']:.2f}")
def _print_enemies(ctx):
    enemies = current_enemies(ctx)
    if not enemies:
        say("Nessun nemico rimasto.")
        return
    for i, e in enumerate(enemies):
        say(f"[{i+1}] {e['name']} (HP {e['hp']})")

def exit_combat(ctx, *, reason: str = "end"):
    _set_combat(ctx, False)
    for k in ("enemies","combat_timer","stagger","qte_active","qte_seq","qte_deadline","next_attack_at"):
        ctx.state.flags.pop(k, None)
    log(ctx, f"Combat finito ({reason}).")

# ============================================================================
# Durabilità
# ============================================================================

def _init_weapon_pool_if_needed(ctx):
    if "weapon_dura" not in ctx.state.flags:
        ctx.state.flags["weapon_dura"] = {}

def _consume_durability(ctx, weapon_id: str) -> None:
    if weapon_id in ("fists",):
        return
    melee = load_melee_weapons()
    _ensure_fists(melee)
    inv: Dict[str,int] = ctx.state.player.inventory
    dur = int(melee.get(weapon_id, {}).get("durability", 10))
    _init_weapon_pool_if_needed(ctx)
    pool: Dict[str,int] = ctx.state.flags["weapon_dura"]
    rem = pool.get(weapon_id, dur) - 1
    if rem > 0:
        pool[weapon_id] = rem
        return
    qty = inv.get(weapon_id, 0)
    if qty > 1:
        inv[weapon_id] = qty - 1
        pool[weapon_id] = dur
        say(f"Il tuo {weapon_id} si incrina… lo sostituisci in fretta.")
    else:
        inv.pop(weapon_id, None)
        pool.pop(weapon_id, None)
        say(f"Il tuo {weapon_id} si spezza—ti restano solo i pugni.")

# ============================================================================
# Loop: TIMER -> (stagger?) -> QTE -> BITE
# ============================================================================

def combat_tick(ctx):
    if not in_combat(ctx):
        return
    now = time.monotonic()
    enemies = current_enemies(ctx)
    if not enemies:
        exit_combat(ctx, reason="all_enemies_dead")
        return
    # Per semplicità, solo il primo nemico vivo attacca/QTE (estendibile)
    enemy = enemies[0]
    if ctx.state.flags.get("qte_active", False):
        deadline = float(ctx.state.flags.get("qte_deadline", 0.0))
        if now > deadline:
            dmg = int(SETTINGS.get("combat_bite_damage", 1))
            p = ctx.state.player
            p.health = max(0, p.health - dmg)
            say(f"Non fai in tempo: {enemy['name']} ti morde! (Health -{dmg})")
            log(ctx, f"{enemy['name']} morde (QTE fail, Health -{dmg}).")
            _debug(ctx, "QTE fail -> bite; reset timer")
            if p.health <= 0:
                say("Cadi a terra. Il mondo sfuma nel buio…")
                exit_combat(ctx, reason="player_down")
                ctx.state.flags["game_over"] = True
                return
            ctx.state.flags.update({
                "qte_active": False,
                "qte_seq": "",
                "qte_deadline": 0.0,
            })
            _reset_next_attack(ctx, now=now)
            _print_enemies(ctx)
        return
    next_at = float(ctx.state.flags.get("next_attack_at", now + 9999))
    if now >= next_at:
        if int(ctx.state.flags.get("stagger", 0)) > 0:
            ctx.state.flags["stagger"] = 0
            _reset_next_attack(ctx, now=now)
            say(f"{enemy['name']} barcolla e perde il tempo per afferrarti.")
            log(ctx, f"Attacco nemico saltato grazie allo stagger.")
            _debug(ctx, "stagger consumed -> reset timer")
            _print_enemies(ctx)
            return
        seq = _gen_qte_sequence(ctx)
        ctx.state.flags["qte_active"] = True
        ctx.state.flags["qte_seq"] = seq
        ctx.state.flags["qte_deadline"] = now + float(SETTINGS.get("combat_qte_time_s", 3.0))
        say(f"❗ {enemy['name']} ti afferra! Liberati digitando:  qte {seq}")
        log(ctx, f"QTE start: '{seq}' (deadline {ctx.state.flags['qte_deadline']:.2f})")
        _debug(ctx, f"QTE start; deadline={ctx.state.flags['qte_deadline']:.2f}")
        _print_enemies(ctx)

# ============================================================================
# Azioni
# ============================================================================

def attack(ctx, *args):
    if not in_combat(ctx):
        say("Non c'è nulla da colpire.")
        return
    if ctx.state.flags.get("qte_active", False):
        say("Sei bloccato! Liberati prima.")
        return
    enemies = current_enemies(ctx)
    if not enemies:
        say("Non ci sono nemici.")
        return
    # Scegli bersaglio: attack [n] oppure default primo
    idx = 0
    if args and args[0].isdigit():
        idx = int(args[0]) - 1
    if idx < 0 or idx >= len(enemies):
        say(f"Bersaglio non valido. Scegli tra 1 e {len(enemies)}.")
        _print_enemies(ctx)
        return
    enemy = enemies[idx]

    inv = ctx.state.player.inventory
    melee = load_melee_weapons()
    _ensure_fists(melee)

    # Selezione arma (come prima)
    chosen_id = None
    equipped = getattr(ctx.state.player, "equipped", None)
    if equipped and inv.get(equipped, 0) > 0 and equipped in melee:
        chosen_id = equipped

    if not chosen_id and len(args) > 1:
        token = " ".join(args[1:]).lower().strip()
        if token in melee and inv.get(token, 0) > 0:
            chosen_id = token
        else:
            name_to_id = {v.get("name","").lower(): k for k,v in melee.items()}
            wid = name_to_id.get(token)
            if wid and inv.get(wid, 0) > 0:
                chosen_id = wid

    if not chosen_id:
        best = pick_best_melee_from_inventory(inv) if callable(pick_best_melee_from_inventory) else None
        if best and isinstance(best, (tuple, list)) and len(best) == 2 and best[0]:
            chosen_id, w = best
        else:
            chosen_id, w = "fists", melee["fists"]
    else:
        w = melee.get(chosen_id, melee["fists"])

    # Statistiche arma
    dmg         = float(w.get("damage", 1))
    energy_cost = float(w.get("energy_cost", 0.4))
    hit_bonus   = float(w.get("hit_bonus", 0.0))
    crit_chance = float(w.get("crit_chance", 0.0))
    wname       = w.get("name", chosen_id)
    import random as _rnd
    kill_msg_raw = w.get("kill_msg", "Il colpo spezza tutto: il walker cede e crolla.")
    hit_msg_raw  = w.get("hit_msg", f"Colpisci con {wname}: il walker vacilla (HP {{hp}}).")
    kill_msg = _rnd.choice(kill_msg_raw) if isinstance(kill_msg_raw, list) else kill_msg_raw
    hit_msg  = _rnd.choice(hit_msg_raw) if isinstance(hit_msg_raw, list) else hit_msg_raw

    # Energia
    p = ctx.state.player
    p.energy = max(0.0, p.energy - energy_cost)

    # Chance di colpire
    hit_chance = 0.70 + hit_bonus
    if p.energy < 1.0:
        hit_chance -= 0.15
    hit_chance = max(0.05, min(0.95, hit_chance))

    rng = _rng(ctx)
    roll = rng.random()

    if roll <= hit_chance:
        crit = (rng.random() <= crit_chance)
        if chosen_id == "knife":
            enemy["hp"] = 0
            _consume_durability(ctx, chosen_id)
            say(w.get("kill_msg", "La lama prende l’orbita—un istante, e il walker collassa."))
            log(ctx, f"Kill walker (arma={wname}, one-shot).")
        else:
            dealt = int(max(1, dmg * (2 if crit else 1)))
            if chosen_id == "fists":
                enemy["hp"] = max(1, enemy.get("hp", 2) - dealt)
            else:
                enemy["hp"] = max(0, enemy.get("hp", 2) - dealt)
                _consume_durability(ctx, chosen_id)

            if enemy["hp"] <= 0:
                say(kill_msg)
                log(ctx, f"Kill walker (arma={wname}, crit={crit})")
        # Rimuovi nemico se morto
        if enemy["hp"] <= 0:
            enemies.pop(idx)
            _print_enemies(ctx)
            if not enemies:
                exit_combat(ctx, reason="all_enemies_dead")
                return
        else:
            say(hit_msg.replace("{hp}", str(enemy["hp"])))
            log(ctx, f"Walker ferito (HP={enemy['hp']}, arma={wname}, crit={crit})")
            _print_enemies(ctx)
    else:
        admg = int(enemy.get("admg", 1))
        p.health = max(0, p.health - admg)
        say(f"Sbagli il colpo—{enemy['name']} ti graffia! (Health -{admg})")
        log(ctx, f"Frank ferito (graffio, -{admg}).")
        if p.health <= 0:
            say("Cadi a terra. Il mondo sfuma nel buio…")
            exit_combat(ctx, reason="player_down")
            ctx.state.flags["game_over"] = True
            return

    # Respiro: reset timer
    if in_combat(ctx):
        _reset_next_attack(ctx)
        _debug(ctx, "attack -> reset timer")

def push(ctx, *args):
    if not in_combat(ctx):
        say("Spingere cosa?")
        return

    enemies = current_enemies(ctx)
    if not enemies:
        say("Non ci sono nemici.")
        return
    idx = 0
    if args and args[0].isdigit():
        idx = int(args[0]) - 1
    if idx < 0 or idx >= len(enemies):
        say(f"Bersaglio non valido. Scegli tra 1 e {len(enemies)}.")
        _print_enemies(ctx)
        return
    enemy = enemies[idx]

    p = ctx.state.player
    p.energy = max(0.0, p.energy - 0.2)

    rng = _rng(ctx)
    if rng.random() <= 0.70:
        ctx.state.flags["stagger"] = 1
        _reset_next_attack(ctx, now=time.monotonic(), extra=SETTINGS.get("stagger_delay_s", 0))
        say(f"Lo spingi con forza: {enemy['name']} barcolla all'indietro.")
        log(ctx, f"{enemy['name']} staggered.")
    else:
        say(f"Provi a spingere {enemy['name']} ma resta addosso a te.")
        _reset_next_attack(ctx)

    if in_combat(ctx):
        ctx.state.flags["combat_timer"] = 2
        _debug(ctx, "push -> reset timer (+stagger se riuscito)")
    _print_enemies(ctx)

def flee(ctx, *args):
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
            now = time.monotonic()
            next_at = ctx.state.flags.get("next_attack_at", now)
            if next_at - now > 2.0:
                ctx.state.flags["next_attack_at"] = next_at - 2.0
            else:
                ctx.state.flags["next_attack_at"] = now + 0.5
            ctx.state.flags["combat_timer"] = 1
            _debug(ctx, f"flee fail -> next_at={ctx.state.flags['next_attack_at']:.2f}")

def qte_input(ctx, *args):
    if not in_combat(ctx):
        say("Non sei in combattimento.")
        return
    if not ctx.state.flags.get("qte_active", False):
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
        _reset_next_attack(ctx)
        say("Ti divincoli—ti liberi dalla presa! (puoi agire)")
        log(ctx, "QTE success (liberato).")
        _debug(ctx, "qte success -> reset timer")
        _print_enemies(ctx)
    else:
        say("Sequenza errata! Riprova in fretta!")
        _print_enemies(ctx)

# ============================================================================
# Idle: NIENTE DANNI. Accorcia solo il timer per forzare l'attacco/QTE.
# ============================================================================

def combat_idle_tick(ctx):
    if not in_combat(ctx):
        return

    t = int(ctx.state.flags.get("combat_timer", 2))
    stagger = int(ctx.state.flags.get("stagger", 0))

    if stagger > 0:
        ctx.state.flags["stagger"] = 0
        ctx.state.flags["combat_timer"] = 2
        say("Il walker recupera l'equilibrio…")
        _debug(ctx, "idle while stagger -> consume stagger, reset idle counter")
        return

    now = time.monotonic()
    next_at = float(ctx.state.flags.get("next_attack_at", now))
    if next_at - now > 1.5:
        new_next = next_at - 1.5
    else:
        new_next = max(now, next_at)
    ctx.state.flags["next_attack_at"] = new_next

    t = max(0, t - 1)
    ctx.state.flags["combat_timer"] = (2 if t == 0 else t)
    say("Il tempo stringe…")
    _debug(ctx, f"idle -> next_at={new_next:.2f}, idle_cnt={ctx.state.flags['combat_timer']}")
