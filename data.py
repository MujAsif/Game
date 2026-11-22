"""
DATA — Five text-map levels, per-level themes, decoration tables,
and question banks (for other modes).
Maps: one char = one tile (TILE=40). Row 0 = first line of the string.
5 sky rows are added above row 0 by the loader.
"""
import random

LEVEL1_TOPIC = "Python Basics"
LEVEL1_QUESTIONS = [
    {"q": "Which function prints text?", "options": ["print()", "echo()", "console.log()", "display()"], "answer": 0, "why": "print() outputs to console."},
    {"q": "What does len([4, 8]) return?", "options": ["2", "3", "4", "15"], "answer": 0, "why": "len() counts items."},
]
LEVEL2_TOPIC = "Control Flow"
LEVEL2_QUESTIONS = [
    {"q": "Which keyword runs a block if true?", "options": ["if", "for", "def", "import"], "answer": 0, "why": "if checks condition."},
    {"q": "Which loop iterates over elements?", "options": ["if", "for", "def", "try"], "answer": 1, "why": "for loops iterate."},
]
LEVEL3_TOPIC = "Collections"
LEVEL3_QUESTIONS = [
    {"q": "Which stores key-value pairs?", "options": ["list", "tuple", "dict", "set"], "answer": 2, "why": "dict maps keys to values."},
    {"q": "Which brackets create a list?", "options": ["{}", "[]", "()", "<>"], "answer": 1, "why": "[] defines lists."},
]

LEVEL_LAYOUTS = [
    # ── LEVEL 1 ──────────────────────────────────────────────────
    """|                                    |
|                                    |
|                                 G  |
|                             =======|
|                        c    ||||||||
|                      -----         |
|                                    |
|             MMMMM                  |
|   K                                |
|========                            |
||||||||                            |
||||||   ----                       |
||||                                |
|              -----                 |
|                                    |
|                      -----         |
|                                    |
|                               c    |
|                             =======|
|                             ||||||||
|                             ||||||||
|                      ======        |
|                      ||||||        |
|                                    |
|               -----                |
|                                    |
|                                    |
|        -----                       |
|                                    |
|  P                     E           |
|==============^^^^^^================|
||||||||||||||||||||||||||||||||||||||""",
    # ── LEVEL 2 ──────────────────────────────────────────────────
    """|                                    |
|                                    |
|                              G     |
|                           =======  |
|                           |||||||  |
|                    -----           |
|                F                   |
|              c                     |
|            -----                   |
|                                    |
|                                    |
|   c     ---                        |
|=======                             |
|||||||                             |
||||                                |
||||                                |
|||                                 |
|                                    |
|                -----               |
|                                    |
|                         K   ^^^    |
|                        ============|
|                 MMM      ||||||||||  |
|                          ||||||||||  |
|           -----          ||||||||||  |
|                          ||||||||||  |
|                          ||||||||||  |
|                  -----             |
|  c c c                             |
|       ^^^                   E   P  |
|==========~~~~~~~~~~~~~~~~==========|
||||||||||~~~~~~~~~~~~~~~~||||||||||""",
    # ── LEVEL 3 ──────────────────────────────────────────────────
    """|                                    |
|||||||||||||||||||||||            G |
|||||||||||||||||||||||          ====|
|       vvvvvvvvvvvvvv           ||||  |
|                        =======     |
|  K                                 |
|======         -----                 |
||||||          MMM                   |
||||                                |
|          -----                      |
|                                    |
|                                    |
|                   -----             |
|                                    |
|    F                                |
|                          -----      |
|                                    |
|                                    |
|                                 ===|
|                                 |||
|                                 |||
|                          ======    |
|                                    |
|                     E              |
|                   =====            |
|                                    |
|          c                          |
|        ----- ---                   |
|                                    |
|   P                    ^^^^        |
|============~~~~~~~~~~==============|
||||||||||||~~~~~~~~~~||||||||||||||""",
    # ── LEVEL 4 ──────────────────────────────────────────────────
    """|                                    |
|        G                           |
|      =====                         |
|      |||||                         |
|               -----                 |
|                         K          |
|                       =====        |
|                       |||||        |
|                                    |
|                 -----               |
||||||||||                  ||||||||||
||||||||||                  ||||||||||
|||||||||||-----             ||||||||||
||||||||||                  ||||||||||
||||||||||                  ||||||||||
||||||||||         =========||||||||||
||||||||||                  ||||||||||
||||||||||                  ||||||||||
||||||||||       MMM        ||||||||||
||||||||||                  ||||||||||
||||||||||   c              ||||||||||
|||||||||| -----            ||||||||||
||||||||||                  ||||||||||
||||||||||                  ||||||||||
||||||||||          -----   ||||||||||
||||||||||                  ||||||||||
||||||||||                  ||||||||||
|||||||||| -----            ||||||||||
||||||||||                  ||||||||||
||||||||||   P   ^^^   E    ||||||||||
||||||||||==================||||||||||
||||||||||||||||||||||||||||||||||||||""",
    # ── LEVEL 5 ──────────────────────────────────────────────────
    """|                                    |
|     G                              |
|   =====                            |
|   |||||     -----   -----          |
|         MMM                        |
|                               K    |
|                             =====  |
|                             |||||  |
|                                    |
|                ----- ----          |
|                                    |
|                                    |
|        -----                       |
|              F                      |
|    K                                |
|======                               |
||||||                               |
||||||            ^^^                 |
||||||  -----    =====              |
|                                    |
|                                    |
|                         -----      |
|                                    |
|                                    |
|                                ====|
|                    F           ||||
|                                ||||
|                          ----- ||||
|                                ||||
|  P             E               ||||
|=========^^^^============~~~~~~~||||
|||||||||||||||||||||||||~~~~~~~||||""",
]

LEVEL_THEMES = [
    {"sky_top": (24, 12, 46), "sky_bottom": (232, 96, 140), "celestial": (255, 158, 196),
     "ridge_far": (104, 58, 126), "ridge_mid": (76, 44, 102), "ridge_near": (50, 30, 78),
     "ground_top": (92, 62, 116), "ground_bottom": (30, 20, 48),
     "accent": (255, 138, 186), "mote": (255, 190, 220)},
    {"sky_top": (16, 10, 40), "sky_bottom": (186, 84, 152), "celestial": (255, 170, 205),
     "ridge_far": (88, 52, 122), "ridge_mid": (64, 40, 98), "ridge_near": (42, 26, 72),
     "ground_top": (80, 54, 112), "ground_bottom": (26, 18, 46),
     "accent": (196, 132, 255), "mote": (230, 190, 255)},
    {"sky_top": (30, 10, 42), "sky_bottom": (240, 90, 122), "celestial": (255, 150, 172),
     "ridge_far": (112, 50, 112), "ridge_mid": (84, 38, 90), "ridge_near": (56, 26, 66),
     "ground_top": (98, 54, 106), "ground_bottom": (32, 18, 44),
     "accent": (255, 110, 140), "mote": (255, 180, 192)},
    {"sky_top": (13, 24, 48), "sky_bottom": (58, 96, 134), "celestial": (214, 238, 255),
     "ridge_far": (38, 62, 98), "ridge_mid": (42, 82, 118), "ridge_near": (26, 54, 86),
     "ground_top": (76, 118, 146), "ground_bottom": (20, 38, 62),
     "accent": (124, 208, 252), "mote": (220, 242, 255)},
    {"sky_top": (15, 28, 46), "sky_bottom": (56, 98, 102), "celestial": (252, 232, 186),
     "ridge_far": (37, 63, 82), "ridge_mid": (31, 74, 76), "ridge_near": (23, 55, 60),
     "ground_top": (48, 86, 74), "ground_bottom": (18, 33, 38),
     "accent": (98, 220, 170), "mote": (210, 245, 224)},
]

# Decoration tables. "row" = the row whose TOP edge the object's bottom sits on
# (waterfall uses "row" as its TOP row instead). Cols = first column covered.
DECORATIONS = {
    0: [
        {"type": "sign", "row": 30, "col": 5},
        {"type": "fence", "row": 30, "col": 10, "width": 3},
        {"type": "stone_lantern", "row": 9, "col": 6},
        {"type": "bush", "row": 21, "col": 25, "width": 2},
        {"type": "banner", "row": 18, "col": 34},
        {"type": "torii", "row": 3, "col": 31, "width": 4},
        {"type": "tree", "row": 30, "col": 22, "width": 4},
        {"type": "shrine", "row": 30, "col": 30, "width": 4},
    ],
    1: [
        {"type": "sign", "row": 30, "col": 31},
        {"type": "fence", "row": 30, "col": 26, "width": 3},
        {"type": "stone_lantern", "row": 30, "col": 0},
        {"type": "stone_lantern", "row": 21, "col": 27},
        {"type": "crate", "row": 21, "col": 33},
        {"type": "bush", "row": 8, "col": 14, "width": 2},
        {"type": "banner", "row": 3, "col": 33},
        {"type": "torii", "row": 3, "col": 28, "width": 4},
        {"type": "waterfall", "row": 22, "col": 24, "width": 2, "height": 4},
    ],
    2: [
        {"type": "sign", "row": 30, "col": 6},
        {"type": "fence", "row": 30, "col": 8, "width": 3},
        {"type": "shrine", "row": 30, "col": 29, "width": 4},
        {"type": "bush", "row": 30, "col": 34},
        {"type": "hanging_lantern", "row": 4, "col": 25},
        {"type": "banner", "row": 18, "col": 35},
        {"type": "stone_lantern", "row": 6, "col": 4},
        {"type": "torii", "row": 2, "col": 32, "width": 4},
    ],
    3: [
        {"type": "sign", "row": 30, "col": 10},
        {"type": "fence", "row": 30, "col": 24, "width": 3},
        {"type": "hanging_lantern", "row": 27, "col": 10},
        {"type": "bush", "row": 21, "col": 13, "width": 2},
        {"type": "banner", "row": 15, "col": 26},
        {"type": "waterfall", "row": 10, "col": 25, "width": 2, "height": 4},
        {"type": "stone_lantern", "row": 6, "col": 27},
        {"type": "torii", "row": 2, "col": 6, "width": 4},
    ],
    4: [
        {"type": "sign", "row": 30, "col": 5},
        {"type": "crate", "row": 30, "col": 19},
        {"type": "crate", "row": 29, "col": 19},
        {"type": "tree", "row": 30, "col": 20, "width": 4},
        {"type": "rope_bridge", "row": 18, "col": 13, "width": 4},
        {"type": "waterfall", "row": 26, "col": 30, "width": 2, "height": 4},
        {"type": "stone_lantern", "row": 15, "col": 1},
        {"type": "hanging_lantern", "row": 9, "col": 16},
        {"type": "banner", "row": 6, "col": 33},
        {"type": "torii", "row": 2, "col": 3, "width": 4},
    ],
}

DECOR_SIZES = {   # (width tiles, height tiles)
    "torii": (4, 4), "shrine": (4, 3), "tree": (4, 4), "waterfall": (2, 4),
    "hanging_lantern": (2, 3), "banner": (1, 3), "bush": (2, 1), "fence": (3, 1),
    "rope_bridge": (4, 1), "stone_lantern": (1, 2), "sign": (1, 2), "crate": (1, 1),
}


def make_question_deck(pool):
    """Shuffle a pool's questions."""
    deck = []
    for item in random.sample(pool, len(pool)):
        opts = item["options"][:]
        correct = opts[item["answer"]]
        random.shuffle(opts)
        deck.append({"q": item["q"], "options": opts, "answer": opts.index(correct), "why": item["why"]})
    return deck