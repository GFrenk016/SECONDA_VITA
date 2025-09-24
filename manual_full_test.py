"""Manual full smoke test for Seconda Vita.

This script exercises the main gameplay loops without interactive input:
- Exploration (look/where/status, wait, wait until)
- Inventory and items (inventory, examine, equip/unequip, use, drop)
- Combat (engage/spawn, attack, QTE offense/defense success & failure, push, flee)
- Multi-enemy (spawn extra, attack all, focus)

Run:
    python manual_full_test.py

Outputs narrative lines to stdout, grouped by sections.
"""
from __future__ import annotations
import time

from game.bootstrap import load_world_and_state
from engine.core.loader.content_loader import load_combat_content
from engine.core.combat import inject_content, set_complex_qte, set_combat_seed, tick_combat
from engine.core import actions


def print_block(title: str, result: dict | None):
    print("\n====", title, "====")
    if not result:
        return
    for line in result.get("lines", []):
        print(line)


def ensure_realtime_tick(state):
    """Advance realtime mapping once to initialize state time fields."""
    state.recompute_from_real(time.time())


def clear_qte_if_active(state, registry):
    """If a QTE is active, auto-resolve it with the expected input to restore player phase."""
    sess = state.combat_session or {}
    if sess.get("phase") == "qte" and sess.get("qte"):
        expected = sess["qte"].get("expected")
        if expected:
            return actions.combat_action(state, registry, "qte", expected)
    return None


def main():
    registry, state = load_world_and_state()
    ensure_realtime_tick(state)

    # --- Exploration basics ---
    print_block("where", actions.where(state, registry))
    print_block("look", actions.look(state, registry))
    print_block("status", actions.status(state, registry))
    print_block("wait 5", actions.wait(state, registry, 5))
    print_block("look (after wait)", actions.look(state, registry))
    print_block("wait until notte", actions.wait_until(state, registry, "notte"))
    print_block("look (notte)", actions.look(state, registry))

    # --- Inventory & Items ---
    # Initialize content registries (items, loot, recipes, effects)
    try:
        from engine.items import create_default_items, load_items_from_assets
        from engine.loot import create_default_loot_tables, load_loot_tables_from_assets
        from engine.crafting import create_default_recipes, load_recipes_from_assets
        from engine.effects import create_default_effects
        create_default_items(); create_default_loot_tables(); create_default_recipes(); create_default_effects()
        try:
            load_items_from_assets(); load_loot_tables_from_assets(); load_recipes_from_assets()
        except Exception:
            pass
    except Exception:
        pass
    print_block("inventory", actions.inventory(state, registry))
    # Try equipping the hunting knife if present
    print_block("equip hunting knife", actions.equip_item(state, registry, "hunting knife"))
    print_block("inventory (after equip)", actions.inventory(state, registry))
    print_block("unequip main_hand", actions.unequip_item(state, registry, "main_hand"))
    print_block("use medkit", actions.use_item(state, registry, "medkit"))
    print_block("drop cloth 1", actions.drop_item(state, registry, "cloth", 1))
    print_block("inventory (final)", actions.inventory(state, registry))

    # --- Combat setup ---
    weapons, mobs = load_combat_content()
    inject_content(weapons, mobs)
    set_complex_qte(False)  # simpler single-char QTE for demo
    set_combat_seed(42)

    # Engage a walker
    print_block("spawn walker_basic", actions.spawn(state, registry, "walker_basic"))
    print_block("status (combat)", actions.combat_action(state, registry, "status"))

    # Attack until an OFFENSIVE QTE appears, then succeed
    for i in range(10):
        res = actions.combat_action(state, registry, "attack")
        print_block(f"attack #{i+1}", res)
        sess = state.combat_session or {}
        if sess.get("phase") == "qte" and sess.get("qte", {}).get("type") == "offense":
            expected = sess["qte"]["expected"]
            print_block("qte offense (success)", actions.combat_action(state, registry, "qte", expected))
            break

    # Force a DEFENSIVE QTE by fast-forwarding simulated minutes to next attack
    sess = state.combat_session or {}
    if sess and sess.get("enemies"):
        enemy0 = sess["enemies"][0]
        target_total = enemy0.get("next_attack_total", 0)
        # Advance manual offset to reach the attack time, then tick
        current_total = state.day_count * 24 * 60 + state.time_minutes
        if target_total > current_total:
            state.manual_offset_minutes += (target_total - current_total)
            # Recompute to apply offset
            state.recompute_from_real(time.time())
        # Trigger QTE
        _ = tick_combat(state)
        print_block("status (defense QTE should appear)", actions.combat_action(state, registry, "status"))
        sess = state.combat_session or {}
        if sess.get("phase") == "qte" and sess.get("qte", {}).get("type") == "defense":
            expected = sess["qte"]["expected"]
            print_block("qte defense (success)", actions.combat_action(state, registry, "qte", expected))

    # Trigger another defense QTE and fail intentionally
    sess = state.combat_session or {}
    if sess and sess.get("enemies") and sess.get("phase") != "ended":
        # Try to ensure a defense QTE appears (loop a few times if needed)
        for _ in range(3):
            sess = state.combat_session or {}
            if not (sess and sess.get("enemies")):
                break
            enemy0 = sess["enemies"][0]
            target_total = enemy0.get("next_attack_total", 0)
            current_total = state.day_count * 24 * 60 + state.time_minutes
            if target_total > current_total:
                state.manual_offset_minutes += (target_total - current_total)
                state.recompute_from_real(time.time())
            _ = tick_combat(state)
            sess = state.combat_session or {}
            if sess.get("phase") == "qte" and sess.get("qte", {}).get("type") == "defense":
                break
        # Wrong input on purpose if QTE active
        sess = state.combat_session or {}
        if sess.get("phase") == "qte" and sess.get("qte", {}).get("type") == "defense":
            print_block("qte defense (fail)", actions.combat_action(state, registry, "qte", "z"))

    # Multi-spawn two more enemies
    print_block("spawn walker_basic 2", actions.combat_action(state, registry, "spawn walker_basic 2"))
    print_block("status (multi)", actions.combat_action(state, registry, "status"))

    # Attack all (may be gated by cooldown)
    print_block("attack all", actions.combat_action(state, registry, "attack all"))
    # Set focus to 2 if exists
    print_block("focus 2", actions.combat_action(state, registry, "focus 2"))
    print_block("attack (focused)", actions.combat_action(state, registry, "attack"))

    # Push and attempt to flee a few times
    # Ensure it's player's turn (auto-resolve any QTE)
    res_clear = clear_qte_if_active(state, registry)
    if res_clear:
        print_block("qte auto-resolve before push", res_clear)
    print_block("push", actions.combat_action(state, registry, "push"))
    for i in range(5):
        # Ensure player's turn each attempt
        res_clear = clear_qte_if_active(state, registry)
        if res_clear:
            print_block("qte auto-resolve before flee", res_clear)
        res = actions.combat_action(state, registry, "flee")
        print_block(f"flee attempt #{i+1}", res)
        if (state.combat_session or {}).get("phase") == "ended":
            break

    print("\n==== DONE (manual full smoke test) ====\n")


if __name__ == "__main__":
    main()
