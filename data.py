"""
DATA — Level maps, themes, decoration placement, and (unused by Mode I) quiz banks.

Maps are tile runs (row, col, length, char) stamped onto a blank grid, then
newline-joined into the ASCII map game.load_level() parses. _build() raises on
out-of-bounds runs; _check_shape() raises if a map is malformed.

    python data.py            # print all five maps
    python validate_levels.py # reachability audit

LAYOUT RULES
  * Row 30 = ground surface, row 31 = ground fill.
  * 'P'/'K' sit ONE ROW ABOVE their surface. 'G' one row above its platform.
  * Never use '|' (load_level strips it). Use '='.
  * One-way '-' top = row*40+28.  Mover 'M' top = row*40+26.
  * Keep >= 60px between a mover's underside and any surface the player
    can stand on below it (else the mover hits the player's head).
  * Top-of-climb steps must rise <= 112px (one-way->solid is 28px extra).

CRITICAL RULE (the bug this file fixes):
  Consecutive platforms in the climb must NOT overlap in x. If the next slab
  is directly overhead, the player jumps into its underside and is trapped.
  Offset each platform sideways (2-tile gap) so you jump up-and-over onto it.
  A non-overlapping pair 2 rows apart = 80px rise + 80px gap, well inside the
  112px step / 130px gap safe limits.

TILE LEGEND
    =  solid   -  one-way   M  mover   ^  floor spikes
    v  ceiling spikes       ~  water   K  checkpoint
    P  spawn   G  goal      (space) empty
"""
import random

LEVEL_COLS = 36
LEVEL_ROWS = 32


def _build(spec):
    grid = [[" "] * LEVEL_COLS for _ in range(LEVEL_ROWS)]
    for row, col, length, ch in spec:
        if not (0 <= row < LEVEL_ROWS and 0 <= col and col + length <= LEVEL_COLS):
            raise ValueError(
                f"tile run out of bounds: row={row} col={col} len={length} char={ch!r}")
        if length < 1 or len(ch) != 1:
            raise ValueError(f"bad tile run: {(row, col, length, ch)!r}")
        for i in range(length):
            grid[row][col + i] = ch
    return "\n".join("".join(r) for r in grid)


def _check_shape(maps):
    for i, m in enumerate(maps):
        rows = m.split("\n")
        if len(rows) != LEVEL_ROWS:
            raise ValueError(f"level {i+1}: {len(rows)} rows, expected {LEVEL_ROWS}")
        bad = [(r, len(s)) for r, s in enumerate(rows) if len(s) != LEVEL_COLS]
        if bad:
            raise ValueError(f"level {i+1} ragged rows (row,width): {bad}")
    return maps


# ── LEVEL 1 — THE SAKURA SANCTUM ─────────────────────────────────
# Zig-zag climb. Every consecutive pair is offset 2 tiles (no ceiling trap).
_L1 = [
    (30, 0, 14, "="), (30, 14, 2, "^"), (30, 16, 20, "="),
    (31, 0, 36, "="),
    (29, 2, 1, "P"),
    (28, 6, 6, "-"),
    (26, 14, 6, "-"),
    (24, 22, 6, "-"),
    (23, 30, 5, "="),  (22, 32, 1, "K"),      # checkpoint 1
    (21, 22, 6, "-"),
    (19, 14, 6, "-"),
    (17, 22, 5, "M"),                          # optional shortcut: ow19 -> M -> ow15
    (17, 6, 6, "-"),
    (15, 14, 6, "-"),
    (13, 22, 6, "-"),
    (12, 30, 5, "="),  (11, 32, 1, "K"),      # checkpoint 2
    (10, 22, 6, "-"),
    (8, 14, 6, "-"),
    (6, 6, 6, "-"),
    (4, 14, 6, "-"),
    (3, 22, 12, "="),  (2, 32, 1, "G"),       # goal
]

# ── LEVEL 2 — THE EMBER CANOPY (mirrored) ────────────────────────
_L2 = [
    (30, 0, 13, "="), (30, 13, 2, "^"), (30, 15, 4, "="),
    (30, 19, 2, "^"), (30, 21, 15, "="),
    (31, 0, 36, "="),
    (29, 33, 1, "P"),
    (28, 24, 6, "-"),
    (26, 16, 6, "-"),
    (24, 8, 6, "-"),
    (23, 1, 5, "="),   (22, 3, 1, "K"),       # checkpoint 1
    (21, 8, 6, "-"),
    (19, 16, 6, "-"),
    (17, 9, 5, "M"),                           # optional shortcut: ow19 -> M -> ow15
    (17, 24, 6, "-"),
    (15, 16, 6, "-"),
    (13, 8, 6, "-"),
    (12, 1, 5, "="),   (11, 3, 1, "K"),       # checkpoint 2
    (10, 8, 6, "-"),
    (8, 16, 6, "-"),
    (6, 24, 6, "-"),
    (4, 16, 6, "-"),
    (3, 2, 12, "="),   (2, 3, 1, "G"),        # goal
]

# ── LEVEL 3 — THE VERDANT HOLLOW ─────────────────────────────────
_L3 = [
    (0, 10, 11, "v"),                          # ceiling spikes: >=8 rows above any platform
    (30, 0, 20, "="), (30, 20, 2, "^"), (30, 22, 14, "="),
    (31, 0, 36, "="),
    (29, 3, 1, "P"),
    (28, 8, 6, "-"),
    (26, 16, 6, "-"),
    (24, 24, 6, "-"),
    (22, 16, 6, "-"),
    (20, 8, 6, "-"),
    (19, 0, 6, "="),   (18, 3, 1, "K"),       # checkpoint 1 (left wall slab)
    (17, 8, 6, "-"),
    (15, 16, 6, "-"),
    (13, 24, 6, "-"),
    (12, 32, 4, "="),  (11, 33, 1, "K"),      # checkpoint 2
    (10, 24, 6, "-"),
    (8, 16, 6, "-"),
    (6, 24, 6, "-"),
    (5, 32, 4, "="),   (4, 34, 1, "G"),       # goal
]

# ── LEVEL 4 — THE FROSTBOUND RIDGE ───────────────────────────────
_L4 = [
    (30, 0, 12, "="), (30, 12, 3, "^"), (30, 15, 21, "="),
    (31, 0, 36, "="),
    (29, 17, 1, "P"),
    (27, 14, 6, "-"),
    (25, 6, 6, "-"),
    (23, 14, 6, "="),
    (22, 17, 1, "K"),
    (20, 22, 6, "-"),
    (18, 19, 5, "M"),
    (17, 12, 6, "-"),
    (15, 4, 8, "="),
    (14, 6, 1, "K"),
    (12, 14, 6, "-"),
    (10, 22, 6, "-"),
    (8, 14, 6, "-"),
    (6, 4, 8, "="),
    (4, 14, 8, "="),
    (3, 20, 1, "G"),
]

# ── LEVEL 5 — THE MOONLIT CASCADES ───────────────────────────────
_L5 = [
    (30, 0, 10, "="), (30, 10, 3, "~"), (30, 13, 12, "="),
    (30, 25, 3, "^"), (30, 28, 8, "="),
    (31, 0, 10, "="), (31, 10, 3, "~"), (31, 13, 23, "="),
    (29, 3, 1, "P"),
    (27, 6, 6, "-"),
    (25, 14, 6, "-"),
    (23, 22, 6, "="),
    (22, 25, 1, "K"),
    (20, 14, 6, "-"),
    (18, 16, 5, "M"),
    (17, 6, 6, "-"),
    (15, 14, 8, "="),
    (14, 16, 1, "K"),
    (12, 24, 6, "-"),
    (10, 16, 6, "-"),
    (8, 8, 6, "-"),
    (6, 16, 8, "="),
    (4, 26, 8, "="),
    (3, 32, 1, "G"),
]

LEVEL_LAYOUTS = _check_shape([_build(s) for s in (_L1, _L2, _L3, _L4, _L5)])

# ── Per-level color themes ───────────────────────────────────────
LEVEL_THEMES = [
    {"name": "The Sakura Sanctum",
     "sky_top": (24, 12, 46), "sky_bottom": (232, 96, 140), "celestial": (255, 158, 196),
     "ridge_far": (104, 58, 126), "ridge_mid": (76, 44, 102), "ridge_near": (50, 30, 78),
     "ground_top": (92, 62, 116), "ground_bottom": (30, 20, 48),
     "accent": (255, 138, 186), "mote": (255, 190, 220)},
    {"name": "The Ember Canopy",
     "sky_top": (16, 10, 40), "sky_bottom": (186, 84, 152), "celestial": (255, 170, 205),
     "ridge_far": (88, 52, 122), "ridge_mid": (64, 40, 98), "ridge_near": (42, 26, 72),
     "ground_top": (80, 54, 112), "ground_bottom": (26, 18, 46),
     "accent": (196, 132, 255), "mote": (230, 190, 255)},
    {"name": "The Verdant Hollow",
     "sky_top": (30, 10, 42), "sky_bottom": (240, 90, 122), "celestial": (255, 150, 172),
     "ridge_far": (112, 50, 112), "ridge_mid": (84, 38, 90), "ridge_near": (56, 26, 66),
     "ground_top": (98, 54, 106), "ground_bottom": (32, 18, 44),
     "accent": (255, 110, 140), "mote": (255, 180, 192)},
    {"name": "The Frostbound Ridge",
     "sky_top": (13, 24, 48), "sky_bottom": (58, 96, 134), "celestial": (214, 238, 255),
     "ridge_far": (38, 62, 98), "ridge_mid": (42, 82, 118), "ridge_near": (26, 54, 86),
     "ground_top": (76, 118, 146), "ground_bottom": (20, 38, 62),
     "accent": (124, 208, 252), "mote": (220, 242, 255)},
    {"name": "The Moonlit Cascades",
     "sky_top": (15, 28, 46), "sky_bottom": (56, 98, 102), "celestial": (252, 232, 186),
     "ridge_far": (37, 63, 82), "ridge_mid": (31, 74, 76), "ridge_near": (23, 55, 60),
     "ground_top": (48, 86, 74), "ground_bottom": (18, 33, 38),
     "accent": (98, 220, 170), "mote": (210, 245, 224)},
]

# ── Decoration footprint in TILES (width, height) ────────────────
DECOR_SIZES = {
    "torii": (4, 3), "stone_lantern": (1, 2), "hanging_lantern": (1, 2),
    "banner": (1, 2), "shrine": (4, 3), "tree": (4, 4), "bush": (1, 1),
    "crate": (1, 1), "fence": (1, 1), "sign": (1, 1),
    "rope_bridge": (4, 1), "waterfall": (2, 4),
}

# ── Decoration placement (re-anchored onto the new surfaces) ─────
DECORATIONS = {
    0: [
        {"type": "sign", "row": 30, "col": 5},
        {"type": "fence", "row": 30, "col": 17, "width": 3},
        {"type": "tree", "row": 30, "col": 22, "width": 4},
        {"type": "shrine", "row": 30, "col": 30, "width": 4},
        {"type": "bush", "row": 23, "col": 30, "width": 2},
        {"type": "stone_lantern", "row": 12, "col": 30},
        {"type": "stone_lantern", "row": 3, "col": 23},
        {"type": "banner", "row": 3, "col": 24},
        {"type": "torii", "row": 3, "col": 26, "width": 4},
    ],
    1: [
        {"type": "sign", "row": 30, "col": 30},
        {"type": "fence", "row": 30, "col": 16, "width": 3},
        {"type": "tree", "row": 30, "col": 8, "width": 4},
        {"type": "shrine", "row": 30, "col": 2, "width": 4},
        {"type": "stone_lantern", "row": 30, "col": 24},
        {"type": "bush", "row": 23, "col": 1, "width": 2},
        {"type": "stone_lantern", "row": 12, "col": 5},
        {"type": "stone_lantern", "row": 3, "col": 12},
        {"type": "banner", "row": 3, "col": 11},
        {"type": "torii", "row": 3, "col": 6, "width": 4},
    ],
    2: [
        {"type": "sign", "row": 30, "col": 6},
        {"type": "fence", "row": 30, "col": 11, "width": 3},
        {"type": "stone_lantern", "row": 30, "col": 25},
        {"type": "shrine", "row": 30, "col": 28, "width": 4},
        {"type": "bush", "row": 30, "col": 34},
        {"type": "stone_lantern", "row": 19, "col": 1},
        {"type": "bush", "row": 19, "col": 5},
        {"type": "bush", "row": 12, "col": 35},
        {"type": "banner", "row": 5, "col": 32},
        {"type": "stone_lantern", "row": 5, "col": 35},
    ],
    3: [
        {"type": "sign", "row": 30, "col": 20},
        {"type": "fence", "row": 30, "col": 24, "width": 3},
        {"type": "hanging_lantern", "row": 15, "col": 8},
        {"type": "bush", "row": 23, "col": 18, "width": 2},
        {"type": "banner", "row": 6, "col": 10},
        {"type": "waterfall", "row": 10, "col": 30, "width": 2, "height": 4},
        {"type": "stone_lantern", "row": 30, "col": 33},
        {"type": "crate", "row": 30, "col": 28, "solid": True},
        {"type": "torii", "row": 4, "col": 14, "width": 4},
    ],
    4: [
        {"type": "sign", "row": 30, "col": 5},
        {"type": "crate", "row": 30, "col": 20, "solid": True},
        {"type": "tree", "row": 30, "col": 21, "width": 4},
        {"type": "rope_bridge", "row": 21, "col": 19, "width": 4},
        {"type": "waterfall", "row": 26, "col": 30, "width": 2, "height": 4},
        {"type": "stone_lantern", "row": 15, "col": 18},
        {"type": "hanging_lantern", "row": 6, "col": 20},
        {"type": "banner", "row": 23, "col": 23},
        {"type": "torii", "row": 4, "col": 26, "width": 4},
    ],
}

# ════════════════════════════════════════════════════════════════
# QUIZ BANKS — NOT USED BY MODE I. Reserved for Modes II/III.
# ════════════════════════════════════════════════════════════════
LEVEL1_TOPIC = "Python Basics"
LEVEL1_QUESTIONS = [
    {"q": "Which function prints text?",
     "options": ["print()", "echo()", "console.log()", "display()"],
     "answer": 0, "why": "print() outputs to console."},
    {"q": "What does len([4, 8]) return?",
     "options": ["2", "3", "4", "15"],
     "answer": 0, "why": "len() counts items."},
]
LEVEL2_TOPIC = "Control Flow"
LEVEL2_QUESTIONS = [
    {"q": "Which keyword runs a block if true?",
     "options": ["if", "for", "def", "import"],
     "answer": 0, "why": "if checks a condition."},
    {"q": "Which loop iterates over elements?",
     "options": ["if", "for", "def", "try"],
     "answer": 1, "why": "for loops iterate."},
]
LEVEL3_TOPIC = "Collections"
LEVEL3_QUESTIONS = [
    {"q": "Which stores key-value pairs?",
     "options": ["list", "tuple", "dict", "set"],
     "answer": 2, "why": "dict maps keys to values."},
    {"q": "Which brackets create a list?",
     "options": ["{}", "[]", "()", "<>"],
     "answer": 1, "why": "[] defines lists."},
]


def make_question_deck(pool):
    """Shuffle a pool's questions and options. Modes II/III only."""
    deck = []
    for item in random.sample(pool, len(pool)):
        opts = item["options"][:]
        correct = opts[item["answer"]]
        random.shuffle(opts)
        deck.append({"q": item["q"], "options": opts,
                     "answer": opts.index(correct), "why": item["why"]})
    return deck


if __name__ == "__main__":
    for i, m in enumerate(LEVEL_LAYOUTS):
        print(f"\n=== LEVEL {i+1} — {LEVEL_THEMES[i]['name']} ===")
        print("     0    5    10   15   20   25   30   35")
        for r, line in enumerate(m.split("\n")):
            print(f"{r:3d} |{line}|")