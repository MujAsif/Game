"""
DATA — Level definitions, themes, and question banks (for other modes).
"""
import random

# ── Question Banks (Kept for Labyrinth/Storm modes if needed later) ────────
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

# ── Platformer Levels ──────────────────────────────────────────────────
LEVELS = [
    # LEVEL 1: TWILIGHT SAKURA SHRINE
    {
        "name": "THE SAKURA SANCTUM",
        "topic": "Twilight",
        "width": 3260,
        "start_x": 100,
        "flag_x": 3120,
        "platforms": [
            {"x": 0, "y": 470, "w": 320, "h": 230},
            {"x": 320, "y": 530, "w": 180, "h": 170},
            {"x": 560, "y": 430, "w": 120, "h": 26},
            {"x": 760, "y": 470, "w": 160, "h": 230},
            {"x": 1000, "y": 400, "w": 140, "h": 300},
            {"x": 1220, "y": 330, "w": 110, "h": 26},
            {"x": 1400, "y": 300, "w": 160, "h": 400},
            {"x": 1650, "y": 380, "w": 110, "h": 26},
            {"x": 1830, "y": 450, "w": 150, "h": 250},
            {"x": 2050, "y": 360, "w": 110, "h": 26},
            {"x": 2230, "y": 300, "w": 150, "h": 400},
            {"x": 2450, "y": 470, "w": 160, "h": 230},
            {"x": 2680, "y": 430, "w": 220, "h": 270},
            {"x": 2980, "y": 380, "w": 280, "h": 320},
        ],
        "props": [
            {"type": "sakura_tree", "x": 90, "y": 470, "scale": 1.35},
            {"type": "bush_pink", "x": 185, "y": 470},
            {"type": "signpost", "x": 262, "y": 470},
            {"type": "torii", "x": 410, "y": 530},
            {"type": "lantern_post", "x": 800, "y": 470},
            {"type": "rope_bridge", "x": 920, "y": 468, "x2": 1000, "y2": 398},
            {"type": "stone_lantern", "x": 1035, "y": 400},
            {"type": "sakura_tree", "x": 1105, "y": 400, "scale": 0.6},
            {"type": "stone_lantern", "x": 1420, "y": 300},
            {"type": "torii", "x": 1480, "y": 300, "scale": 1.1},
            {"type": "lantern_post", "x": 1540, "y": 300},
            {"type": "banner", "x": 1875, "y": 450},
            {"type": "bush_pink", "x": 1945, "y": 450},
            {"type": "banner", "x": 2270, "y": 300},
            {"type": "bush_pink", "x": 2345, "y": 300},
            {"type": "waterfall", "x": 2642, "y": 470},
            {"type": "lantern_post", "x": 2712, "y": 430},
            {"type": "shrine", "x": 2790, "y": 430},
            {"type": "crate", "x": 2862, "y": 430},
            {"type": "crate", "x": 2862, "y": 400},
            {"type": "rope_bridge", "x": 2900, "y": 428, "x2": 2980, "y2": 378},
            {"type": "stone_lantern", "x": 3010, "y": 380},
            {"type": "banner", "x": 3052, "y": 380},
            {"type": "fence", "x": 3170, "y": 380},
            {"type": "lantern_post", "x": 3228, "y": 380},
        ],
        "coins": [
            [585, 392], [620, 382], [655, 392],
            [1245, 292], [1275, 282], [1305, 292],
            [1675, 342], [1705, 332], [1735, 342],
            [2075, 322], [2105, 312], [2135, 322],
            [2320, 262], [2352, 262],
            [2405, 352], [2432, 372], [2459, 392],
            [2925, 402], [2950, 386], [2975, 372],
        ],
    },
    # LEVEL 2: DESERT DUNES
    {
        "name": "THE EMBER CANOPY",
        "topic": "Desert",
        "width": 2800,
        "start_x": 100,
        "flag_x": 2600,
        "platforms": [
            {"x": 0, "y": 520, "w": 500, "h": 130}, {"x": 600, "y": 520, "w": 400, "h": 130},
            {"x": 1100, "y": 520, "w": 300, "h": 130}, {"x": 1500, "y": 520, "w": 500, "h": 130},
            {"x": 2100, "y": 520, "w": 700, "h": 130}, {"x": 520, "y": 450, "w": 60, "h": 20},
            {"x": 1020, "y": 400, "w": 60, "h": 20}, {"x": 1420, "y": 350, "w": 60, "h": 20},
            {"x": 2020, "y": 420, "w": 60, "h": 20}, {"x": 700, "y": 300, "w": 150, "h": 20},
            {"x": 1200, "y": 250, "w": 120, "h": 20}, {"x": 1700, "y": 280, "w": 100, "h": 20},
        ],
        "props": [
            {"type": "cactus", "x": 200, "y": 520}, {"type": "crate", "x": 300, "y": 520},
            {"type": "crate", "x": 300, "y": 480}, {"type": "tree_acacia", "x": 800, "y": 520},
            {"type": "skull", "x": 1250, "y": 520}, {"type": "cactus", "x": 1600, "y": 520},
            {"type": "tree_acacia", "x": 2300, "y": 520}, {"type": "signpost", "x": 2500, "y": 520},
        ],
    },
    # LEVEL 3: JUNGLE RUINS
    {
        "name": "THE VERDANT HOLLOW",
        "topic": "Jungle",
        "width": 3000,
        "start_x": 100,
        "flag_x": 2800,
        "platforms": [
            {"x": 0, "y": 540, "w": 600, "h": 110}, {"x": 700, "y": 540, "w": 400, "h": 110},
            {"x": 1200, "y": 540, "w": 300, "h": 110}, {"x": 1600, "y": 540, "w": 500, "h": 110},
            {"x": 2200, "y": 540, "w": 800, "h": 110}, {"x": 620, "y": 480, "w": 60, "h": 20},
            {"x": 1120, "y": 420, "w": 60, "h": 20}, {"x": 1520, "y": 380, "w": 60, "h": 20},
            {"x": 2120, "y": 450, "w": 60, "h": 20}, {"x": 800, "y": 350, "w": 150, "h": 20},
            {"x": 1300, "y": 300, "w": 120, "h": 20}, {"x": 1800, "y": 250, "w": 100, "h": 20},
            {"x": 2400, "y": 320, "w": 100, "h": 20},
        ],
        "props": [
            {"type": "tree_leafy", "x": 200, "y": 540}, {"type": "tree_leafy", "x": 400, "y": 540},
            {"type": "plant_tall", "x": 900, "y": 540}, {"type": "tree_leafy", "x": 1400, "y": 540},
            {"type": "ruin_column", "x": 1700, "y": 540}, {"type": "tree_leafy", "x": 2500, "y": 540},
            {"type": "signpost", "x": 2700, "y": 540},
        ],
    },
]

# ── Per-region color themes ────────────────────────────────────────────────
LEVEL_THEMES = [
    # 1. Twilight Sakura
    {
        "style": "sakura",
        "sky_top": (18, 12, 40), "sky_bottom": (226, 92, 132),
        "celestial": (255, 158, 196),
        "ridge_far": (96, 52, 118), "ridge_mid": (70, 40, 96), "ridge_near": (46, 28, 72),
        "ground_top": (74, 52, 98), "ground_bottom": (26, 18, 42),
        "accent": (255, 138, 186), "mote": (255, 190, 220),
        "prop_colors": {"wood": (122, 80, 68), "leaf": (240, 120, 175),
                        "stone": (148, 128, 168), "grass": (226, 92, 164),
                        "blossom": (255, 176, 214)},
    },
    # 2. Desert
    {
        "sky_top": (135, 206, 235), "sky_bottom": (255, 228, 181), "celestial": (255, 255, 200),
        "ridge_far": (210, 180, 140), "ridge_mid": (190, 150, 100), "ridge_near": (160, 120, 80),
        "ground_top": (210, 160, 90), "ground_bottom": (139, 69, 19),
        "accent": (248, 164, 108), "mote": (255, 214, 164),
        "prop_colors": {"sand": (230, 200, 150), "cactus": (60, 140, 60), "wood": (139, 69, 19), "bone": (240, 240, 220), "leaf": (40, 100, 40)},
    },
    # 3. Jungle
    {
        "sky_top": (15, 28, 46), "sky_bottom": (56, 98, 102), "celestial": (252, 232, 186),
        "ridge_far": (37, 63, 82), "ridge_mid": (31, 74, 76), "ridge_near": (23, 55, 60),
        "ground_top": (48, 86, 74), "ground_bottom": (18, 33, 38),
        "accent": (98, 220, 170), "mote": (210, 245, 224),
        "prop_colors": {"grass": (60, 140, 60), "leaf": (40, 100, 40), "wood": (100, 70, 50), "stone": (120, 120, 120)},
    },
]


def make_question_deck(pool):
    """Shuffle a pool's questions."""
    deck = []
    for item in random.sample(pool, len(pool)):
        opts = item["options"][:]
        correct = opts[item["answer"]]
        random.shuffle(opts)
        deck.append({"q": item["q"], "options": opts, "answer": opts.index(correct), "why": item["why"]})
    return deck