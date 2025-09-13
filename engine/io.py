import os

try:
    import colorama
    colorama.just_fix_windows_console()
    HAS_COLOR = True
except Exception:
    HAS_COLOR = False

def supports_color():
    return HAS_COLOR

def c(text, code=""):
    if not HAS_COLOR or not code:
        return text
    return f"\033[{code}m{text}\033[0m"

def print_banner():
    banner_path = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.txt")
    try:
        with open(os.path.abspath(banner_path), "r", encoding="utf-8") as f:
            print(f.read())
    except FileNotFoundError:
        print("SECONDA VITA")

def say(text):
    print(text)

def prompt(sign="> "):
    return input(sign)
