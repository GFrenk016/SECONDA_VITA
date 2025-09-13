import os

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

def prompt(sign="> "):
    return input(sign)
