from typing import List
from engine.io import say

JOURNAL_KEY = "journal"

def log(ctx, text: str):
    """Aggiunge una riga al diario (flags['journal'])."""
    lst: List[str] = ctx.state.flags.get(JOURNAL_KEY, [])
    lst.append(text)
    ctx.state.flags[JOURNAL_KEY] = lst

def print_journal(ctx, limit: int | None = None):
    lst: List[str] = ctx.state.flags.get(JOURNAL_KEY, [])
    if not lst:
        say("Journal is empty.")
        return
    rows = lst if limit is None else lst[-limit:]
    say("Journal:")
    for i, line in enumerate(rows, 1):
        say(f" {i}. {line}")
