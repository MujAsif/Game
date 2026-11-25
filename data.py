"""
DATA — Level maps, mover routes, themes, decoration placement and the
Python question bank that unlocks the moving platforms.

Maps are tile runs (row, col, length, char) stamped onto a blank grid, then
newline-joined into the ASCII map game.load_level() parses. _build() raises on
out-of-bounds runs; _check_shape() raises if a map is malformed.

    python data.py            # print all five maps (with mover routes)
    python validate_levels.py # reachability + "movers are mandatory" audit

PROGRESSION — QUESTION GATES
  Every level is split into tiers that can ONLY be joined by a moving platform.
  Each mover starts LOCKED (parked, not moving). Stand on it and press E to
  answer a Python question; a right answer starts it, a wrong one costs a
  heart and you can try again with a new question.
  validate_levels.py fails a level if its goal is reachable without riding
  every gate (checked against the best jumper, the fastest runner and BASIL's
  glide), so the gates cannot be skipped.

LAYOUT RULES
  * Row 30 = ground surface, row 31 = ground fill.
  * 'P'/'K' sit ONE ROW ABOVE their surface. 'G' one row above its platform.
  * Never use '|' (load_level strips it). Use '='.
  * One-way '-' top = row*40+28.  Mover 'M' top = row*40+26, i.e. a mover on
    row r-1 rests exactly on a surface whose top is row r.
  * A mover's route (dx, dy) in tiles lives in MOVER_ROUTES, keyed by the
    (row, col) of its LEFTMOST 'M'. It ping-pongs start <-> start+route.
  * Park a mover ON its ledge (or beside it at the same height), never above a
    platform the player must jump from: a parked mover is solid and would
    block the jump.
  * Keep a mover's whole travel corridor (plus 52 px of head-room above it)
    free of solids.
  * Consecutive climb platforms must NOT overlap in x (2-tile offset), so you
    jump up-and-over rather than into an underside. Rise <= 2 rows (80 px).

TILE LEGEND
    =  solid   -  one-way   M  mover (gated)   ^  floor spikes
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
# 1 gate: a lift on the east wall.
_L1 = [
    (30, 0, 14, "="), (30, 14, 2, "^"), (30, 16, 20, "="),
    (31, 0, 36, "="),
    (29, 2, 1, "P"),
    # Tier 1: climb east
    (28, 6, 5, "-"),
    (26, 13, 5, "-"),
    (24, 20, 5, "-"),
    (23, 27, 9, "="),  (22, 28, 1, "K"),       # east ledge + checkpoint
    (22, 32, 4, "M"),                          # GATE 1: lift, 9 rows up
    # Tier 2: sweep west, then back east to the goal
    (14, 22, 10, "="),
    (12, 15, 5, "-"),
    (10, 8, 5, "-"),
    (8, 1, 5, "-"),
    (6, 8, 5, "-"),
    (5, 15, 8, "="),   (4, 20, 1, "G"),        # goal slab
]

# ── LEVEL 2 — THE EMBER CANOPY ───────────────────────────────────
# 2 gates: a diagonal skiff over the canopy, then an east-wall lift.
_L2 = [
    (30, 0, 10, "="), (30, 10, 2, "^"), (30, 12, 10, "="),
    (30, 22, 2, "^"), (30, 24, 12, "="),
    (31, 0, 36, "="),
    (29, 33, 1, "P"),
    # Tier 1: climb west
    (28, 26, 5, "-"),
    (26, 19, 5, "-"),
    (24, 12, 5, "-"),
    (23, 2, 8, "="),   (22, 3, 1, "K"),        # west ledge + checkpoint
    (22, 6, 4, "M"),                           # GATE 1: diagonal up-east
    # Tier 2: east ledge
    (17, 26, 10, "="), (16, 27, 1, "K"),
    (16, 32, 4, "M"),                          # GATE 2: lift, 8 rows up
    # Tier 3: sweep west to the summit
    (9, 22, 10, "="),
    (7, 15, 5, "-"),
    (5, 8, 5, "-"),
    (3, 1, 5, "-"),
    (2, 8, 8, "="),    (1, 13, 1, "G"),        # goal slab
]

# ── LEVEL 3 — THE VERDANT HOLLOW ─────────────────────────────────
# 2 gates: a diagonal skiff west, then a lift beside the high ledge.
_L3 = [
    (30, 0, 10, "="), (30, 10, 2, "^"), (30, 12, 8, "="),
    (30, 20, 2, "^"), (30, 22, 14, "="),
    (31, 0, 36, "="),
    (29, 2, 1, "P"),
    # Tier 1: climb east
    (28, 8, 5, "-"),
    (26, 15, 5, "-"),
    (24, 22, 5, "-"),
    (23, 29, 7, "="),  (22, 34, 1, "K"),       # east ledge + checkpoint
    (22, 29, 4, "M"),                          # GATE 1: diagonal up-west
    # Tier 2: hollow ledge, climb west then east
    (14, 12, 6, "="),  (13, 13, 1, "K"),
    (12, 5, 5, "-"),
    (10, 12, 5, "-"),
    (9, 19, 7, "="),   (8, 20, 1, "K"),
    (8, 26, 3, "M"),                           # GATE 2: lift, 6 rows up
    # Tier 3: summit
    (3, 29, 7, "="),   (2, 34, 1, "G"),        # goal slab
]

# ── LEVEL 4 — THE FROSTBOUND RIDGE ───────────────────────────────
# 2 gates: a long ferry west across the ridge, then a tall west-wall lift.
_L4 = [
    (30, 0, 12, "="), (30, 12, 3, "^"), (30, 15, 9, "="),
    (30, 24, 3, "^"), (30, 27, 9, "="),
    (31, 0, 36, "="),
    (29, 2, 1, "P"),
    # Tier 1: climb east
    (28, 9, 5, "-"),
    (26, 15, 5, "-"),
    (24, 22, 5, "-"),
    (23, 28, 8, "="),  (22, 34, 1, "K"),       # east ledge + checkpoint
    (22, 28, 4, "M"),                          # GATE 1: ferry, 19 tiles west
    # Tier 2: west ledge
    (23, 0, 9, "="),   (22, 5, 1, "K"),
    (22, 0, 3, "M"),                           # GATE 2: lift, 12 rows up
    # Tier 3: climb east to the summit (icicles under the goal slab)
    (11, 3, 6, "="),   (10, 4, 1, "K"),
    (9, 11, 5, "-"),
    (7, 18, 5, "-"),
    (5, 25, 5, "-"),
    (4, 31, 5, "="),   (3, 34, 1, "G"),        # goal slab
    (5, 31, 5, "v"),                           # icicles: don't walk under it
]

# ── LEVEL 5 — THE MOONLIT CASCADES ───────────────────────────────
# 3 gates: diagonal skiff, high ferry, final lift.
_L5 = [
    (30, 0, 9, "="), (30, 9, 3, "~"), (30, 12, 13, "="),
    (30, 25, 3, "^"), (30, 28, 8, "="),
    (31, 0, 9, "="), (31, 9, 3, "~"), (31, 12, 24, "="),
    (29, 2, 1, "P"),
    # Tier 1: climb east over the water and spikes
    (28, 6, 5, "-"),
    (26, 13, 5, "-"),
    (24, 20, 5, "-"),
    (23, 27, 9, "="),  (22, 34, 1, "K"),       # east ledge + checkpoint
    (22, 27, 3, "M"),                          # GATE 1: diagonal up-west
    # Tier 2: falls ledge, climb west then to the high ledge
    (15, 10, 6, "="),  (14, 11, 1, "K"),
    (13, 3, 5, "-"),
    (11, 9, 4, "-"),
    (10, 14, 5, "="),
    (9, 19, 3, "M"),                           # GATE 2: ferry, 9 tiles east
    # Tier 3: east ledge, final lift to the summit
    (10, 31, 5, "="),  (9, 31, 1, "K"),
    (9, 33, 3, "M"),                           # GATE 3: lift, 6 rows up
    (4, 24, 9, "="),   (3, 25, 1, "G"),        # goal slab
]

LEVEL_LAYOUTS = _check_shape([_build(s) for s in (_L1, _L2, _L3, _L4, _L5)])

# ── Mover routes: {level_index: {(row, col of leftmost M): (dx, dy) tiles}} ──
MOVER_ROUTES = {
    0: {(22, 32): (0, -9)},
    1: {(22, 6): (16, -6), (16, 32): (0, -8)},
    2: {(22, 29): (-11, -9), (8, 26): (0, -6)},
    3: {(22, 28): (-19, 0), (22, 0): (0, -12)},
    4: {(22, 27): (-11, -8), (9, 19): (9, 0), (9, 33): (0, -6)},
}

# ── Per-level color themes (kept dark so the foreground reads clearly) ──
LEVEL_THEMES = [
    {"name": "The Sakura Sanctum",
     "sky_top": (9, 5, 20), "sky_bottom": (66, 26, 56), "celestial": (226, 150, 188),
     "ridge_far": (50, 28, 66), "ridge_mid": (38, 22, 54), "ridge_near": (26, 16, 40),
     "ground_top": (92, 62, 116), "ground_bottom": (30, 20, 48),
     "accent": (255, 138, 186), "mote": (220, 160, 200),
     "bg_tint": (142, 120, 156)},
    {"name": "The Ember Canopy",
     "sky_top": (7, 5, 20), "sky_bottom": (56, 26, 60), "celestial": (232, 160, 198),
     "ridge_far": (44, 28, 66), "ridge_mid": (34, 22, 54), "ridge_near": (24, 16, 42),
     "ground_top": (80, 54, 112), "ground_bottom": (26, 18, 46),
     "accent": (196, 132, 255), "mote": (200, 168, 240),
     "bg_tint": (134, 116, 160)},
    {"name": "The Verdant Hollow",
     "sky_top": (12, 5, 20), "sky_bottom": (70, 26, 46), "celestial": (232, 140, 160),
     "ridge_far": (54, 26, 56), "ridge_mid": (42, 20, 46), "ridge_near": (30, 14, 36),
     "ground_top": (98, 54, 106), "ground_bottom": (32, 18, 44),
     "accent": (255, 110, 140), "mote": (230, 160, 176),
     "bg_tint": (146, 116, 146)},
    {"name": "The Frostbound Ridge",
     "sky_top": (5, 10, 24), "sky_bottom": (24, 42, 64), "celestial": (190, 218, 242),
     "ridge_far": (20, 34, 56), "ridge_mid": (22, 42, 64), "ridge_near": (14, 30, 48),
     "ground_top": (76, 118, 146), "ground_bottom": (20, 38, 62),
     "accent": (124, 208, 252), "mote": (190, 220, 240),
     "bg_tint": (124, 138, 166)},
    {"name": "The Moonlit Cascades",
     "sky_top": (5, 12, 22), "sky_bottom": (22, 44, 48), "celestial": (228, 212, 168),
     "ridge_far": (18, 34, 44), "ridge_mid": (16, 40, 42), "ridge_near": (12, 30, 34),
     "ground_top": (48, 86, 74), "ground_bottom": (18, 33, 38),
     "accent": (98, 220, 170), "mote": (180, 228, 204),
     "bg_tint": (120, 142, 146)},
]

# ── Decoration footprint in TILES (width, height) ────────────────
DECOR_SIZES = {
    "torii": (4, 3), "stone_lantern": (1, 2), "hanging_lantern": (1, 2),
    "banner": (1, 2), "shrine": (4, 3), "tree": (4, 4), "bush": (1, 1),
    "crate": (1, 1), "fence": (1, 1), "sign": (1, 1),
    "rope_bridge": (4, 1), "waterfall": (2, 4),
}

# ── Decoration placement ('row' = the surface row the prop stands on) ──
DECORATIONS = {
    0: [
        {"type": "sign", "row": 30, "col": 4},
        {"type": "fence", "row": 30, "col": 17, "width": 3},
        {"type": "tree", "row": 30, "col": 22, "width": 4},
        {"type": "shrine", "row": 30, "col": 29, "width": 4},
        {"type": "stone_lantern", "row": 23, "col": 30},
        {"type": "bush", "row": 23, "col": 27},
        {"type": "stone_lantern", "row": 14, "col": 23},
        {"type": "bush", "row": 14, "col": 26, "width": 2},
        {"type": "banner", "row": 5, "col": 15},
        {"type": "torii", "row": 5, "col": 16, "width": 4},
        {"type": "stone_lantern", "row": 5, "col": 22},
    ],
    1: [
        {"type": "sign", "row": 30, "col": 31},
        {"type": "fence", "row": 30, "col": 26, "width": 3},
        {"type": "tree", "row": 30, "col": 15, "width": 4},
        {"type": "shrine", "row": 30, "col": 3, "width": 4},
        {"type": "stone_lantern", "row": 23, "col": 2},
        {"type": "bush", "row": 23, "col": 4},
        {"type": "stone_lantern", "row": 17, "col": 29},
        {"type": "bush", "row": 17, "col": 30, "width": 2},
        {"type": "stone_lantern", "row": 9, "col": 23},
        {"type": "banner", "row": 9, "col": 27},
        {"type": "waterfall", "row": 18, "col": 28, "width": 2},
        {"type": "banner", "row": 2, "col": 8},
        {"type": "torii", "row": 2, "col": 9, "width": 4},
    ],
    2: [
        {"type": "sign", "row": 30, "col": 4},
        {"type": "fence", "row": 30, "col": 14, "width": 3},
        {"type": "stone_lantern", "row": 30, "col": 23},
        {"type": "shrine", "row": 30, "col": 26, "width": 4},
        {"type": "bush", "row": 23, "col": 33},
        {"type": "waterfall", "row": 24, "col": 32, "width": 2},
        {"type": "stone_lantern", "row": 14, "col": 16},
        {"type": "hanging_lantern", "row": 9, "col": 22},
        {"type": "bush", "row": 9, "col": 24},
        {"type": "banner", "row": 3, "col": 29},
        {"type": "torii", "row": 3, "col": 30, "width": 4},
    ],
    3: [
        {"type": "sign", "row": 30, "col": 4},
        {"type": "tree", "row": 30, "col": 16, "width": 4},
        {"type": "fence", "row": 30, "col": 29, "width": 3},
        {"type": "stone_lantern", "row": 30, "col": 34},
        {"type": "bush", "row": 23, "col": 32},
        {"type": "stone_lantern", "row": 23, "col": 3},
        {"type": "bush", "row": 23, "col": 7},
        {"type": "hanging_lantern", "row": 11, "col": 7},
        {"type": "stone_lantern", "row": 11, "col": 3},
        {"type": "banner", "row": 4, "col": 31},
        {"type": "torii", "row": 4, "col": 32, "width": 3},
    ],
    4: [
        {"type": "sign", "row": 30, "col": 4},
        {"type": "tree", "row": 30, "col": 15, "width": 4},
        {"type": "stone_lantern", "row": 30, "col": 33},
        {"type": "waterfall", "row": 16, "col": 12, "width": 2, "height": 4},
        {"type": "bush", "row": 23, "col": 31},
        {"type": "stone_lantern", "row": 15, "col": 14},
        {"type": "hanging_lantern", "row": 10, "col": 17},
        {"type": "banner", "row": 4, "col": 28},
        {"type": "torii", "row": 4, "col": 29, "width": 3},
    ],
}

# ════════════════════════════════════════════════════════════════
# MOVER GATE QUESTIONS — one bank per level, getting harder each level.
#   q       question text
#   code    optional snippet shown in a monospace box ("\n" for new lines)
#   options exactly four short answers
#   answer  index of the correct option
#   why     one-line explanation shown after answering
# ════════════════════════════════════════════════════════════════
MOVER_QUESTIONS = [
    # Level 1 — Python basics
    [
        {"q": "What does this print?", "code": "x = 5\nx += 2\nprint(x)",
         "options": ["7", "52", "5", "Error"], "answer": 0,
         "why": "x += 2 adds 2 to x, so x becomes 7."},
        {"q": "What does this print?", "code": 'print("Hi" * 3)',
         "options": ["HiHiHi", "Hi 3", "Hi*3", "Error"], "answer": 0,
         "why": "Multiplying a string repeats it."},
        {"q": "Which symbol starts a comment in Python?",
         "options": ["#", "//", "--", "/*"], "answer": 0,
         "why": "Everything after # on a line is ignored."},
        {"q": "What is the result?", "code": 'len("python")',
         "options": ["6", "5", "7", "\"python\""], "answer": 0,
         "why": "len() counts the 6 characters."},
        {"q": "What is the result?", "code": "10 // 3",
         "options": ["3", "3.33", "1", "30"], "answer": 0,
         "why": "// is floor division: it drops the remainder."},
        {"q": "What is the result?", "code": "2 ** 3",
         "options": ["8", "6", "9", "23"], "answer": 0,
         "why": "** is the power operator: 2 * 2 * 2."},
        {"q": "What is the result?", "code": 'int("7") + 3',
         "options": ["10", "73", "\"73\"", "Error"], "answer": 0,
         "why": "int() turns the text \"7\" into the number 7."},
        {"q": "Which type is 3.0?", "code": "type(3.0)",
         "options": ["float", "int", "str", "double"], "answer": 0,
         "why": "Numbers with a decimal point are floats."},
    ],
    # Level 2 — Control flow
    [
        {"q": "What is the LAST number printed?",
         "code": "for i in range(3):\n    print(i)",
         "options": ["2", "3", "0", "1"], "answer": 0,
         "why": "range(3) gives 0, 1, 2 and stops before 3."},
        {"q": "Which keyword exits a loop immediately?",
         "options": ["break", "continue", "pass", "exit"], "answer": 0,
         "why": "break leaves the nearest loop."},
        {"q": "Which keyword skips to the next loop pass?",
         "options": ["continue", "break", "skip", "next"], "answer": 0,
         "why": "continue jumps straight to the next iteration."},
        {"q": "What does this print?",
         "code": 'x = 5\nif x > 3:\n    print("A")\nelse:\n    print("B")',
         "options": ["A", "B", "AB", "Nothing"], "answer": 0,
         "why": "5 > 3 is True, so the if-branch runs."},
        {"q": "How many times does the loop body run?",
         "code": "n = 0\nwhile n < 3:\n    n += 1",
         "options": ["3", "2", "4", "Forever"], "answer": 0,
         "why": "n goes 0 -> 1 -> 2 -> 3, then n < 3 is False."},
        {"q": "What is the result?", "code": "list(range(2, 8, 2))",
         "options": ["[2, 4, 6]", "[2, 4, 6, 8]", "[2, 8]", "[4, 6, 8]"], "answer": 0,
         "why": "Start 2, step 2, stop before 8."},
        {"q": "What is the result?", "code": "True and False",
         "options": ["False", "True", "None", "Error"], "answer": 0,
         "why": "and is True only if both sides are True."},
        {"q": "Which keyword adds another condition to an if?",
         "options": ["elif", "else if", "elseif", "orif"], "answer": 0,
         "why": "Python spells 'else if' as elif."},
    ],
    # Level 3 — Collections
    [
        {"q": "Which type stores key-value pairs?",
         "options": ["dict", "list", "tuple", "set"], "answer": 0,
         "why": "A dict maps keys to values."},
        {"q": "What is the result?", "code": "nums = [1, 2, 3]\nnums.append(4)\nlen(nums)",
         "options": ["4", "3", "5", "Error"], "answer": 0,
         "why": "append() adds one item to the end."},
        {"q": "What is the result?", "code": "[10, 20, 30][-1]",
         "options": ["30", "10", "-1", "Error"], "answer": 0,
         "why": "Index -1 is the last item."},
        {"q": "What is the result?", "code": "[1, 2, 3, 4][1:3]",
         "options": ["[2, 3]", "[1, 2, 3]", "[2, 3, 4]", "[1, 2]"], "answer": 0,
         "why": "Slices start at 1 and stop before 3."},
        {"q": "What is the result?", "code": "set([1, 1, 2])",
         "options": ["{1, 2}", "{1, 1, 2}", "[1, 2]", "Error"], "answer": 0,
         "why": "A set keeps only unique values."},
        {"q": "What is the result?", "code": 'd = {"a": 1}\nd.get("b", 0)',
         "options": ["0", "None", "1", "KeyError"], "answer": 0,
         "why": "get() returns the default when the key is missing."},
        {"q": "What makes a tuple different from a list?",
         "options": ["It can't be changed", "It's always sorted",
                     "It holds one type", "It has no index"], "answer": 0,
         "why": "Tuples are immutable."},
        {"q": "Which brackets create a list?",
         "options": ["[ ]", "{ }", "( )", "< >"], "answer": 0,
         "why": "Square brackets define a list."},
    ],
    # Level 4 — Functions
    [
        {"q": "Which keyword defines a function?",
         "options": ["def", "func", "function", "define"], "answer": 0,
         "why": "def starts a function definition."},
        {"q": "What does f(4) return?", "code": "def f(x):\n    return x * 2",
         "options": ["8", "4", "6", "None"], "answer": 0,
         "why": "f doubles its argument."},
        {"q": "What does g(3) return?", "code": "def g(a, b=2):\n    return a + b",
         "options": ["5", "3", "Error", "None"], "answer": 0,
         "why": "b falls back to its default value 2."},
        {"q": "What does h() return?", "code": "def h():\n    x = 1",
         "options": ["None", "1", "0", "Error"], "answer": 0,
         "why": "A function with no return gives back None."},
        {"q": "What is the result?", "code": "add = lambda a, b: a + b\nadd(2, 5)",
         "options": ["7", "25", "Error", "None"], "answer": 0,
         "why": "lambda makes a small anonymous function."},
        {"q": "What does *args collect?",
         "options": ["Extra positional args", "Keyword args",
                     "Only the first arg", "Global variables"], "answer": 0,
         "why": "*args packs extra positional arguments into a tuple."},
        {"q": "A variable created inside a function is...",
         "options": ["Local to it", "Global", "Shared by all", "Constant"], "answer": 0,
         "why": "Names assigned in a function live in its local scope."},
        {"q": "What is the result?", "code": "def sq(n):\n    return n * n\nsq(sq(2))",
         "options": ["16", "8", "4", "64"], "answer": 0,
         "why": "sq(2) is 4, and sq(4) is 16."},
    ],
    # Level 5 — Strings, errors and classes
    [
        {"q": "What is the result?", "code": '"code".upper()',
         "options": ['"CODE"', '"Code"', '"code"', "Error"], "answer": 0,
         "why": "upper() returns an all-caps copy."},
        {"q": "What is the result?", "code": '"a,b,c".split(",")',
         "options": ["['a', 'b', 'c']", "'abc'", "['a,b,c']", "('a', 'b', 'c')"],
         "answer": 0, "why": "split() breaks a string into a list."},
        {"q": "What is the result?", "code": 'f"{2 + 3}"',
         "options": ['"5"', '"2 + 3"', "5", "Error"], "answer": 0,
         "why": "f-strings evaluate what's inside { }."},
        {"q": "Which error does this raise?", "code": 'int("abc")',
         "options": ["ValueError", "TypeError", "NameError", "KeyError"], "answer": 0,
         "why": "\"abc\" isn't a valid number, so int() raises ValueError."},
        {"q": "Which error does this raise?", "code": "1 / 0",
         "options": ["ZeroDivisionError", "ValueError", "MathError", "None"], "answer": 0,
         "why": "Dividing by zero raises ZeroDivisionError."},
        {"q": "Which block catches an error?",
         "code": "try:\n    risky()\n???:\n    print('oops')",
         "options": ["except", "catch", "error", "finally"], "answer": 0,
         "why": "Python uses try / except."},
        {"q": "What does __init__ do in a class?",
         "options": ["Sets up a new object", "Deletes the object",
                     "Prints the object", "Imports the class"], "answer": 0,
         "why": "__init__ runs when an object is created."},
        {"q": "What is the result?", "code": '"python"[0]',
         "options": ['"p"', '"y"', '"python"', "Error"], "answer": 0,
         "why": "Strings are indexed from 0."},
    ],
]


def make_question_deck(pool):
    """Shuffle a pool's questions and options. Keeps 'code' when present."""
    deck = []
    for item in random.sample(pool, len(pool)):
        opts = item["options"][:]
        correct = opts[item["answer"]]
        random.shuffle(opts)
        q = {"q": item["q"], "options": opts,
             "answer": opts.index(correct), "why": item["why"]}
        if item.get("code"):
            q["code"] = item["code"]
        deck.append(q)
    return deck


# ════════════════════════════════════════════════════════════════
# Legacy banks for the (unbuilt) Modes II/III.
# ════════════════════════════════════════════════════════════════
LEVEL1_TOPIC = "Python Basics"
LEVEL1_QUESTIONS = MOVER_QUESTIONS[0]
LEVEL2_TOPIC = "Control Flow"
LEVEL2_QUESTIONS = MOVER_QUESTIONS[1]
LEVEL3_TOPIC = "Collections"
LEVEL3_QUESTIONS = MOVER_QUESTIONS[2]


if __name__ == "__main__":
    for i, m in enumerate(LEVEL_LAYOUTS):
        print(f"\n=== LEVEL {i+1} — {LEVEL_THEMES[i]['name']} ===")
        for (r, c), (dx, dy) in MOVER_ROUTES.get(i, {}).items():
            print(f"  gate at row {r} col {c}: moves {dx:+d} cols, {dy:+d} rows")
        print("     0    5    10   15   20   25   30   35")
        for r, line in enumerate(m.split("\n")):
            print(f"{r:3d} |{line}|")
