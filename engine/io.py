import os

# --- compat stub: ora la prossimità è gestita in engine/commands._proximity_lines ---
def render_proximity_block(state) -> str:
    return ""

def print_banner():
    banner_path = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.txt")
    banner_path = os.path.abspath(banner_path)
    try:
        with open(banner_path, "r", encoding="utf-8") as f:
            print(f.read())
    except FileNotFoundError:
        print("SECONDA VITA — MINI")

def say(text: str):
    print(text)

def prompt_line(ctx):
    """
    Mostra il prompt e legge una riga dall’utente.
    Ritorna None se EOF (Ctrl+Z/Ctrl+D).
    """
    prompt = getattr(ctx, "prompt", "> ") if hasattr(ctx, "prompt") else "> "
    try:
        return input(prompt)
    except EOFError:
        return None

def prompt(sign="> "):
    return input(sign)
