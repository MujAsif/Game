"""
MAIN — Entry point. Initializes pygame, creates fonts and surfaces, then runs the game.
Run this file:  python main.py
"""

import pygame
import config
from game import Game


def pick_font(size, bold=False, mono=False):
    """Find the best available system font for the given style."""
    names = (("consolas", "jetbrainsmono", "firacode", "dejavusansmono", "couriernew") if mono
             else ("segoeui", "sfprodisplay", "inter", "ubuntu", "dejavusans", "arial"))
    for n in names:
        path = pygame.font.match_font(n, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)


def main():
    pygame.init()
    pygame.display.set_caption("RISE TO THE FLAG — Premium Edition")

    # Create display and draw surfaces
    config.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT), pygame.RESIZABLE)
    config.canvas = pygame.Surface((config.WIDTH, config.HEIGHT)).convert()
    config.world  = pygame.Surface((config.WIDTH, config.HEIGHT)).convert()
    config.clock  = pygame.time.Clock()

    # Build the font set
    config.fonts.FONT      = pick_font(19)
    config.fonts.SMALL     = pick_font(14, bold=True)
    config.fonts.TINY      = pick_font(11, bold=True)
    config.fonts.BODY      = pick_font(16)
    config.fonts.CODE_FONT = pick_font(16, bold=True, mono=True)
    config.fonts.MED       = pick_font(22, bold=True)
    config.fonts.LARGE     = pick_font(40, bold=True)

    try:
        Game().run()
    except SystemExit:
        pass
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()