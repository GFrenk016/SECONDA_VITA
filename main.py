from engine.core import Game
from engine.io import print_banner
from config import SETTINGS

def main():
    print_banner()

game = Game(settings=SETTINGS)
game.bootstrap()
game.loop()

if __name__ == "__main__":
    main()
