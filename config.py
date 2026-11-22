"""
CONFIG — Game constants, physics tuning, color palette, and global pygame objects.
Edit tuning values here. Global surfaces (screen, canvas, world) and fonts are
initialized by main.py.
"""

# ── Display ──────────────────────────────────────────────────────
WIDTH, HEIGHT = 1100, 650
FPS = 60
GROUND_Y = 544

# ── Platformer physics ───────────────────────────────────────────
GRAVITY = 0.78
MAX_FALL_SPEED = 16.5
JUMP_SPEED = -14.8        # max jump ≈ 140px
MOVE_SPEED = 5.2
ACCEL_GROUND = 0.90
ACCEL_AIR = 0.60
FRICTION_GROUND = 0.75
FRICTION_AIR = 0.92

# ── Staircase design ─────────────────────────────────────────────
# Solved pillars descend to these step heights, forming a climbable staircase.
STEP_HEIGHTS = (60, 100, 140, 180, 220)
PILLAR_BLOCK = 120        # extra wall height on unsolved pillars (unjumpable)
PILLAR_W = 120

# ── Gameplay ─────────────────────────────────────────────────────
MAX_HEARTS = 5
QUESTIONS_PER_REGION = 5

# ── Sprites ──────────────────────────────────────────────────────
SPRITE_DIR = "assets/sprites"
SPRITE_CACHE_DIR = "assets/sprites/_cache"
PLAYER_SPRITE_H = 78      # on-screen height of the hero in gameplay
SPRITE_SOURCE_FACING = 1  # direction the sheet art faces: 1 = right, -1 = left

# ── Minimalist color palette ─────────────────────────────────────
INK = (12, 19, 31)
PANEL_BG = (17, 27, 43, 224)
PANEL_BORDER = (130, 158, 184, 72)
WHITE = (245, 248, 252)
MUTED = (156, 174, 194)
SUBTLE = (92, 110, 130)
GOLD = (246, 196, 92)
GOLD_SOFT = (255, 228, 168)
MINT = (86, 214, 166)
CORAL = (242, 98, 112)
BLUE = (104, 176, 242)
CRIMSON = (220, 60, 80)


# ── Globals (initialized by main.py) ─────────────────────────────
class Fonts:
    """Namespace for all game fonts. Attributes are set after pygame.init()."""
    pass


fonts = Fonts()
screen = None   # pygame display
canvas = None   # off-screen draw buffer
world = None    # game world buffer
clock = None    # frame timer