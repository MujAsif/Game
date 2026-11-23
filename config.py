"""
CONFIG — Game constants, physics tuning, color palette, and global pygame objects.
Physics runs at a fixed PHYSICS_HZ; rendering runs at FPS.
"""

# ── Display ──────────────────────────────────────────────────────
WIDTH, HEIGHT = 1100, 650
FPS = 60
GROUND_Y = 544

# ── Tilemap ──────────────────────────────────────────────────────
TILE = 40
SKY_ROWS = 5          # extra empty sky rows added above every level

# ── Fixed-step physics ───────────────────────────────────────────
PHYSICS_HZ = 60
PHYSICS_DT = 1.0 / PHYSICS_HZ
MAX_PHYSICS_STEPS = 5     # catch-up cap; prevents a spiral of death

# ── Platformer physics (per 60 Hz step) ──────────────────────────
GRAVITY = 0.78
MAX_FALL_SPEED = 16.5
JUMP_SPEED = -14.8        # max jump ≈ 140px (3.5 tiles)
MOVE_SPEED = 5.2
ACCEL_GROUND = 0.90
ACCEL_AIR = 0.60
FRICTION_GROUND = 0.75
FRICTION_AIR = 0.92

# ── Feel / timing frames (all at 60 Hz) ──────────────────────────
COYOTE_FRAMES = 7
JUMP_BUFFER_FRAMES = 7
JUMP_CUT_THRESHOLD = -5.5
JUMP_CUT_FACTOR = 0.56
HURT_FRAMES = 16
INVULN_FRAMES = 60
GLIDE_FRAMES = 90         # FEN's glide budget per airtime
GLIDE_GRAVITY_MUL = 0.42
GLIDE_FALL_MUL = 0.5
DROP_THROUGH_FRAMES = 12
KNOCKBACK_X = 4.2
KNOCKBACK_Y = -6.0
SAFE_GROUND_EVERY = 12    # steps between last-safe-ground snapshots
TRY_AGAIN_FRAMES = 90

# ── Gameplay ─────────────────────────────────────────────────────
MAX_HEARTS = 5

# ── Player body / sprite ─────────────────────────────────────────
PLAYER_W, PLAYER_H = 30, 52
PLAYER_SPRITE_H = 54      # drawn at rect.bottom+2 → sprite top == rect.top
SPRITE_SOURCE_FACING = 1

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
screen = None
canvas = None
world = None
clock = None