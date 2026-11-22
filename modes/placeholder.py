"""
MODES/PLACEHOLDER — "Coming Soon" screens for future game modes.
"""
import pygame
import config
from config import WIDTH, HEIGHT, GROUND_Y, WHITE, MUTED, GOLD, fonts
from ui import draw_text, panel, veil

class PlaceholderMode:
    def __init__(self, manager, mode_index):
        self.manager = manager
        self.mode_index = mode_index
        self.names = ["THE LABYRINTH", "THE STORM"]
        self.descs = ["A puzzle of logic and memory.", "An arcade test of reflexes."]

    def update(self):
        pass # No physics needed

    def draw(self):
        self.manager.world_scenery(config.canvas, self.manager.frame)
        config.canvas.blit(veil(180), (0, 0))
        panel(config.canvas, (250, 150, 600, 350), (15, 25, 40, 240), (130, 162, 190, 100), 26, True)
        
        draw_text(config.canvas, self.names[self.mode_index - 1], fonts.LARGE, GOLD, (WIDTH // 2, 220), center=True)
        draw_text(config.canvas, self.descs[self.mode_index - 1], fonts.BODY, WHITE, (WIDTH // 2, 280), center=True)
        draw_text(config.canvas, "(Coming in the full release)", fonts.SMALL, MUTED, (WIDTH // 2, 320), center=True)

    def handle_click(self, pos):
        # Check if they clicked the "Return to Menu" button area
        if 420 <= pos[0] <= 680 and 400 <= pos[1] <= 446:
            self.manager.change_scene("MENU")

    def handle_key(self, key):
        if key == pygame.K_ESCAPE:
            self.manager.change_scene("MENU")