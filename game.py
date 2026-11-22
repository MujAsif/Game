"""
GAME — Main orchestrator: text-map levels, 2D clamped camera, one-way platforms,
moving platforms that carry the player, enemy AI, checkpoints, hazards with
invincibility frames, decorations (colorkey sprites, culled, nearest-neighbour),
and the full scene flow.
"""
import os
import pygame
import math
import random
import config
from config import (WIDTH, HEIGHT, FPS, GROUND_Y, INK, WHITE, MUTED, SUBTLE,
                    GOLD, GOLD_SOFT, MINT, CORAL, BLUE, CRIMSON, MAX_HEARTS,
                    GRAVITY, MAX_FALL_SPEED, MOVE_SPEED, ACCEL_GROUND, ACCEL_AIR,
                    FRICTION_GROUND, FRICTION_AIR, TILE, SKY_ROWS, fonts)
from data import LEVEL_LAYOUTS, LEVEL_THEMES, DECORATIONS, DECOR_SIZES
from ui import (draw_text, wrap_text, gradient_rect, draw_pill, panel,
                get_radial_glow, get_smooth_heart, get_smooth_star, veil, Button,
                clamp, blend_color, lerp)
from audio import AudioManager
from entities import Player, Particle, FloatingText, Enemy, MovingPlatform
from sprites import bank, ROSTER
from character_select import CharacterSelect

_MENU_CACHE = {}
TITLE_BG_CANDIDATES = (
    os.path.join("assets", "ui", "title_bg.png"),
    os.path.join("assets", "title_bg.png"),
    "title_bg.png",
)
DECOR_SHEET_CANDIDATES = (
    os.path.join("assets", "props", "decorations.png"),
    os.path.join("assets", "sprites", "decorations.png"),
    "decorations.png",
)


def _alpha_grad(w, h, horizontal, a0, a1, color=(8, 10, 20)):
    key = ("ag", w, h, horizontal, a0, a1, color)
    hit = _MENU_CACHE.get(key)
    if hit is not None:
        return hit
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    n = w if horizontal else h
    for i in range(n):
        t = i / max(1, n - 1)
        a = int(a0 + (a1 - a0) * t)
        if horizontal:
            pygame.draw.line(s, (*color, a), (i, 0), (i, h - 1))
        else:
            pygame.draw.line(s, (*color, a), (0, i), (w - 1, i))
    if len(_MENU_CACHE) > 60:
        _MENU_CACHE.clear()
    _MENU_CACHE[key] = s
    return s


# ─────────────────────────── level parsing ───────────────────────────
def load_level(layout_text):
    """Parse one text map. Returns a dict of everything the game needs."""
    raw = [ln for ln in layout_text.split("\n")]
    rows = []
    for ln in raw:
        s = ln
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        rows.append(s)
    cols = max((len(r) for r in rows), default=0)
    rows = [r.ljust(cols) for r in rows]
    n_rows = len(rows)
    width, height = cols * TILE, (n_rows + SKY_ROWS) * TILE

    platforms, one_way, water = [], [], []
    spikes_floor, spikes_ceil = [], []
    coins, checkpoints = [], []
    enemies, flyers, movers = [], [], []
    crates, bridges = [], []
    solid_cells = set()
    start = (TILE, height - TILE)
    goal = None

    r = 0
    while r < n_rows:
        c = 0
        while c < cols:
            ch = rows[r][c]
            x, y = c * TILE, (r + SKY_ROWS) * TILE
            if ch in "=|":
                c0 = c
                while c < cols and rows[r][c] in "=|":
                    solid_cells.add((c, r))
                    c += 1
                platforms.append(pygame.Rect(x, y, (c - c0) * TILE, TILE))
                continue
            if ch == "-":
                c0 = c
                while c < cols and rows[r][c] == "-":
                    c += 1
                one_way.append(pygame.Rect(x, y + TILE - 12, (c - c0) * TILE, 12))
                continue
            if ch == "M":
                c0 = c
                while c < cols and rows[r][c] == "M":
                    c += 1
                movers.append(MovingPlatform(x, y, c - c0))
                continue
            if ch == "^":
                c0 = c
                while c < cols and rows[r][c] == "^":
                    solid_cells.add((c, r))
                    c += 1
                platforms.append(pygame.Rect(x, y, (c - c0) * TILE, TILE))
                spikes_floor.append(pygame.Rect(x + 8, y + 8, (c - c0) * TILE - 16, TILE - 8))
                continue
            if ch == "v":
                c0 = c
                while c < cols and rows[r][c] == "v":
                    c += 1
                spikes_ceil.append(pygame.Rect(x + 8, y, (c - c0) * TILE - 16, 22))
                continue
            if ch == "~":
                c0 = c
                while c < cols and rows[r][c] == "~":
                    c += 1
                water.append(pygame.Rect(x, y, (c - c0) * TILE, TILE))
                continue
            if ch == "c":
                coins.append({"x": x + TILE // 2, "y": y + TILE // 2, "taken": False})
            elif ch == "E":
                enemies.append(Enemy(x, y, "walk"))
            elif ch == "F":
                flyers.append(Enemy(x, y, "fly"))
            elif ch == "K":
                checkpoints.append({"x": x + TILE // 2, "ground_y": y + TILE, "active": False})
            elif ch == "P":
                start = (x + TILE // 2, y + TILE)
            elif ch == "G":
                goal = pygame.Rect(x + 4, y - 8, TILE - 8, TILE + 8)
            c += 1
        r += 1

    return {"width": width, "height": height, "platforms": platforms, "one_way": one_way,
            "water": water, "spikes_floor": spikes_floor, "spikes_ceil": spikes_ceil,
            "coins": coins, "checkpoints": checkpoints, "enemies": enemies,
            "flyers": flyers, "movers": movers, "solid_cells": solid_cells,
            "start": start, "goal": goal}


class Game:
    def __init__(self):
        self.audio = AudioManager()
        self.scene, self.settings_return = "MENU", "MENU"
        self.selected_character = 0
        self.character = ROSTER[0]
        self.stats = self.new_stats()
        self.level_index = 0
        self.theme = LEVEL_THEMES[0]
        self.dt_scale, self.frame, self.scene_fade = 1.0, 0.0, 0.0
        self.buttons, self.button_cache, self.mouse_pos = [], {}, (0, 0)
        self.particles, self.popups = [], []
        self.player = None
        self.game_mode = 0
        self.mode_names = ["THE ASCENT", "THE LABYRINTH", "THE STORM"]
        self.mode_descriptions = ["A platformer of wit and agility.", "A puzzle of logic and memory.", "An arcade test of reflexes."]
        self.camera_x, self.camera_y = 0.0, 0.0
        self.level_width, self.level_height = WIDTH, HEIGHT
        self.shake = 0.0
        self.score_display = 0.0
        self.score_at_level_start = 0
        self.settings = {"fullscreen": False, "particles": True}
        self.slider_drag = None
        self.menu_hover_index = -1
        self.title_bob = 0.0
        self._jump_held = False
        self.motes = [(random.randrange(WIDTH), random.randrange(70, GROUND_Y - 30), random.random() * math.tau) for _ in range(38)]
        self.clouds = [(110, 92, 1.0, 0.10), (470, 64, 1.2, 0.07), (840, 128, 0.9, 0.12)]
        self.bg_base = self.make_background()
        self.petals = [{"x": random.randrange(WIDTH), "y": random.randrange(HEIGHT), "ph": random.random() * math.tau,
                        "sp": random.uniform(0.45, 1.1), "sw": random.uniform(10, 28), "sz": random.randint(3, 6)} for _ in range(26)]
        self._title_bg = None
        self._title_bg_missing = False
        self.select = CharacterSelect(self)
        # level state
        self.level_data = None
        self.platforms, self.one_way, self.water = [], [], []
        self.spikes_floor, self.spikes_ceiling = [], []
        self.coins, self.checkpoints = [], []
        self.enemies, self.flyers, self.movers = [], [], []
        self.crate_solids, self.bridge_one_way = [], []
        self.solid_cells = set()
        self.last_checkpoint = None
        self.goal_rect = None
        self.coin_count = 0
        self.decor_draw = []
        self.decor_sprites = self._load_decor_sprites()

    # ── decorations ──────────────────────────────────────────────
    def _load_decor_sprites(self):
        sheet = None
        for cand in DECOR_SHEET_CANDIDATES:
            p = cand if os.path.isabs(cand) else os.path.join(os.path.dirname(os.path.abspath(__file__)), cand)
            if os.path.isfile(p):
                try:
                    sheet = pygame.image.load(p).convert()
                    sheet.set_colorkey((255, 0, 255))
                except pygame.error:
                    sheet = None
                break
        if sheet is None:
            return {}
        names = ["torii", "stone_lantern", "hanging_lantern", "banner",
                 "shrine", "tree", "bush", "crate",
                 "fence", "sign", "rope_bridge", "waterfall"]
        w, h = sheet.get_size()
        cw, ch = w // 4, h // 3
        out = {}
        for i, name in enumerate(names):
            out[name] = sheet.subsurface(pygame.Rect((i % 4) * cw, (i // 4) * ch, cw, ch)).copy()
        return out

    def _build_decor(self):
        """Pre-scale every decoration once (nearest-neighbour) + collision extras."""
        self.decor_draw, self.crate_solids, self.bridge_one_way = [], [], []
        for dec in DECORATIONS.get(self.level_index, []):
            t = dec["type"]
            wt, ht = DECOR_SIZES.get(t, (1, 1))
            wt, ht = dec.get("width", wt), dec.get("height", ht)
            x = dec["col"] * TILE
            if t == "waterfall":
                y = (dec["row"] + SKY_ROWS) * TILE
            elif t == "crate":
                y = (dec["row"] + SKY_ROWS) * TILE - ht * TILE
            else:
                y = (dec["row"] + SKY_ROWS) * TILE - ht * TILE
            pw, ph = wt * TILE, ht * TILE
            surf = None
            base = self.decor_sprites.get(t)
            if base is not None:
                surf = pygame.transform.scale(base, (pw, ph))   # nearest-neighbour
            if t == "crate":
                self.crate_solids.append(pygame.Rect(x, y, pw, ph))
            elif t == "rope_bridge":
                self.bridge_one_way.append(pygame.Rect(x, (dec["row"] + SKY_ROWS) * TILE, pw, 12))
            self.decor_draw.append({"type": t, "x": x, "y": y, "w": pw, "h": ph, "surf": surf})

    # ── basics ───────────────────────────────────────────────────
    def new_stats(self):
        mh = MAX_HEARTS + self.character.get("traits", {}).get("bonus_hearts", 0)
        return {"lives": mh, "max_lives": mh, "score": 0, "combo": 0, "best_combo": 0}

    def get_viewport_rect(self):
        dw, dh = config.screen.get_size()
        scale = min(dw / WIDTH, dh / HEIGHT)
        vw, vh = int(round(WIDTH * scale)), int(round(HEIGHT * scale))
        return pygame.Rect((dw - vw) // 2, (dh - vh) // 2, max(1, vw), max(1, vh))

    def convert_mouse(self, position):
        vp = self.get_viewport_rect()
        return (int(clamp((position[0] - vp.x) * WIDTH / vp.w, 0, WIDTH - 1)),
                int(clamp((position[1] - vp.y) * HEIGHT / vp.h, 0, HEIGHT - 1)))

    def _title_background(self):
        if self._title_bg is not None:
            return self._title_bg
        if self._title_bg_missing:
            return None
        path = None
        for cand in TITLE_BG_CANDIDATES:
            for base in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
                p = os.path.join(base, cand)
                if os.path.isfile(p):
                    path = p
                    break
            if path:
                break
        if path is None:
            self._title_bg_missing = True
            return None
        try:
            img = pygame.image.load(path).convert()
            scale = max(WIDTH / img.get_width(), HEIGHT / img.get_height())
            nw, nh = max(WIDTH, int(round(img.get_width() * scale))), max(HEIGHT, int(round(img.get_height() * scale)))
            img = pygame.transform.smoothscale(img, (nw, nh))
            rx, ry = (nw - WIDTH) // 2, (nh - HEIGHT) // 2
            self._title_bg = img.subsurface(pygame.Rect(rx, ry, WIDTH, HEIGHT)).copy()
        except pygame.error:
            self._title_bg_missing = True
        return self._title_bg

    def _petal_surf(self, sz, rb):
        key = ("petal", sz, rb)
        s = _MENU_CACHE.get(key)
        if s is None:
            base = pygame.Surface((sz * 3, sz * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(base, (244, 152, 192, 205), base.get_rect())
            s = pygame.transform.rotate(base, rb * 12)
            if len(_MENU_CACHE) > 60:
                _MENU_CACHE.clear()
            _MENU_CACHE[key] = s
        return s

    def _draw_petals(self, surface, cam=0):
        for p in self.petals:
            y = (p["y"] + self.frame * p["sp"]) % (HEIGHT + 40) - 20
            x = (p["x"] + math.sin(self.frame * 0.02 + p["ph"]) * p["sw"] - cam * 0.35) % WIDTH
            surface.blit(self._petal_surf(p["sz"], int(math.sin(self.frame * 0.05 + p["ph"]) * 4)), (int(x), int(y)))

    def _menu_options(self):
        return [("I. THE ASCENT", "mode_0"), ("II. THE LABYRINTH", "mode_1"), ("III. THE STORM", "mode_2"),
                ("SETTINGS", "settings"), ("QUIT", "quit")]

    def _register_menu_rect(self, action, rect):
        if action not in self.button_cache:
            self.button_cache[action] = {"rect": rect, "action": action}
        else:
            self.button_cache[action]["rect"] = rect

    # ── menu / settings / pause / end ────────────────────────────
    def draw_menu(self):
        bg = self._title_background()
        if bg is not None:
            self._draw_menu_image(bg)
        else:
            self._draw_menu_procedural()

    def _draw_menu_image(self, bg):
        cv = config.canvas
        cv.blit(bg, (0, 0))
        cv.blit(_alpha_grad(WIDTH, 190, False, 150, 0), (0, 0))
        cv.blit(_alpha_grad(410, HEIGHT, True, 150, 0), (0, 0))
        cv.blit(_alpha_grad(WIDTH, 130, False, 0, 150), (0, HEIGHT - 130))
        self._draw_petals(cv)
        self.title_bob = math.sin(self.frame * 0.03) * 3
        title_y = 84 + self.title_bob
        draw_text(cv, "THE THREE TRIALS", fonts.LARGE, (0, 0, 0, 190), (WIDTH // 2 + 4, title_y + 4), center=True)
        draw_text(cv, "THE THREE TRIALS", fonts.LARGE, WHITE, (WIDTH // 2, title_y), center=True)
        draw_text(cv, "A PYTHON JOURNEY", fonts.SMALL, GOLD_SOFT, (WIDTH // 2, title_y + 46), center=True)
        start_y, gap = 252, 54
        self.menu_hover_index = -1
        for i, (text, action) in enumerate(self._menu_options()):
            y = start_y + i * gap
            rect = pygame.Rect(44, y - 21, 256, 42)
            if rect.collidepoint(self.mouse_pos):
                self.menu_hover_index = i
                draw_pill(cv, rect, (16, 22, 38, 190), (*GOLD, 150), shadow=False)
                pygame.draw.polygon(cv, GOLD, [(rect.x + 10, rect.centery - 6), (rect.x + 10, rect.centery + 6), (rect.x + 20, rect.centery)])
                draw_text(cv, text, fonts.FONT, GOLD, (rect.x + 34, rect.centery), valign="middle")
            else:
                draw_text(cv, text, fonts.FONT, WHITE if i < 3 else MUTED, (rect.x + 34, rect.centery), valign="middle")
            self._register_menu_rect(action, rect)
        chip = pygame.Rect(24, HEIGHT - 54, 214, 34)
        draw_pill(cv, chip, (14, 20, 34, 210), (*self.character["accent"], 110), shadow=False)
        if bank.has(self.character["id"]):
            bank.draw(cv, self.character["id"], "idle", int(self.frame * 0.07) % bank.count(self.character["id"], "idle"), 48, HEIGHT - 24, 26, facing=1)
        draw_text(cv, f"{self.character['name']} · {self.character['short']}", fonts.TINY, WHITE, (66, chip.centery), valign="middle")
        draw_text(cv, "1–3 MODES   ·   S SETTINGS   ·   ESC QUIT", fonts.TINY, (214, 224, 238), (WIDTH - 24, HEIGHT - 22), right=True)

    def _draw_menu_procedural(self):
        self.world_scenery(config.canvas, self.frame)
        pygame.draw.ellipse(config.canvas, (0, 0, 0, 100), (830, GROUND_Y - 5, 40, 10))
        pygame.draw.rect(config.canvas, INK, (838, GROUND_Y - 40, 24, 40), border_radius=4)
        pygame.draw.circle(config.canvas, INK, (850, GROUND_Y - 50), 14)
        pygame.draw.polygon(config.canvas, CRIMSON, [(845, GROUND_Y - 35), (825, GROUND_Y - 30), (810, GROUND_Y - 38), (815, GROUND_Y - 25)])
        self._draw_petals(config.canvas)
        self.title_bob = math.sin(self.frame * 0.03) * 4
        title_y = 130 + self.title_bob
        draw_text(config.canvas, "THE THREE TRIALS", fonts.LARGE, (0, 0, 0, 180), (WIDTH // 2 + 5, title_y + 5), center=True)
        draw_text(config.canvas, "THE THREE TRIALS", fonts.LARGE, CRIMSON, (WIDTH // 2, title_y), center=True)
        draw_text(config.canvas, "THE THREE TRIALS", fonts.LARGE, WHITE, (WIDTH // 2 - 2, title_y - 2), center=True)
        draw_text(config.canvas, "A PYTHON JOURNEY", fonts.SMALL, GOLD_SOFT, (WIDTH // 2, title_y + 55), center=True)
        start_y, gap = 280, 55
        self.menu_hover_index = -1
        for i, (text, action) in enumerate(self._menu_options()):
            y = start_y + i * gap
            rect = pygame.Rect(WIDTH // 2 - 150, y - 20, 300, 40)
            if rect.collidepoint(self.mouse_pos):
                self.menu_hover_index = i
                pygame.draw.polygon(config.canvas, GOLD, [(rect.left - 20, rect.centery - 6), (rect.left - 20, rect.centery + 6), (rect.left - 8, rect.centery)])
                draw_text(config.canvas, text, fonts.FONT, GOLD, (WIDTH // 2, y), center=True)
            else:
                draw_text(config.canvas, text, fonts.FONT, WHITE if i < 3 else MUTED, (WIDTH // 2, y), center=True)
            self._register_menu_rect(action, rect)

    def make_background(self):
        bg = pygame.Surface((WIDTH, HEIGHT)).convert()
        th = self.theme
        gradient_rect(bg, (0, 0, WIDTH, HEIGHT), th["sky_top"], th["sky_bottom"])
        rng = random.Random(42 + self.level_index * 19)
        for _ in range(55):
            shade = rng.randint(120, 200)
            pygame.draw.circle(bg, (shade, min(255, shade + 12), min(255, shade + 24)), (rng.randrange(WIDTH), rng.randrange(24, 290)), 1)
        cx, cy = 830, 132
        bg.blit(get_radial_glow(150, th["celestial"], 34, 5), (cx - 150, cy - 150))
        pygame.draw.circle(bg, th["celestial"], (cx, cy), 34)
        pygame.draw.polygon(bg, th["ridge_far"], [(0, 410), (140, 250), (290, 365), (460, 215), (630, 355), (810, 235), (980, 350), (1100, 285), (1100, GROUND_Y), (0, GROUND_Y)])
        pygame.draw.polygon(bg, th["ridge_mid"], [(0, 445), (210, 310), (390, 430), (590, 315), (780, 435), (960, 305), (1100, 390), (1100, GROUND_Y), (0, GROUND_Y)])
        pygame.draw.polygon(bg, th["ridge_near"], [(0, 485), (170, 415), (360, 492), (560, 420), (760, 495), (940, 425), (1100, 475), (1100, GROUND_Y), (0, GROUND_Y)])
        gradient_rect(bg, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y), th["ground_top"], th["ground_bottom"])
        return bg

    def world_scenery(self, target, frame, cam=0):
        target.blit(self.bg_base, (0, 0))
        for cx, cy, scale, speed in self.clouds:
            x = (cx + frame * speed - cam * 0.10) % (WIDTH + 200) - 100
            w, h = int(96 * scale), int(22 * scale)
            cloud = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(cloud, (255, 255, 255, 18), cloud.get_rect(), border_radius=h // 2)
            target.blit(cloud, (int(x), int(cy)))
        for x, y, phase in self.motes:
            pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(frame * 0.035 + phase))
            xx = (x + math.sin(frame * 0.015 + phase) * 8 - cam * 0.25) % WIDTH
            yy = y + math.cos(frame * 0.02 + phase) * 5
            pygame.draw.circle(target, self.theme["mote"], (int(xx), int(yy)), 2 if pulse > 0.75 else 1)

    # ── level lifecycle ──────────────────────────────────────────
    def start_game(self, mode=0):
        self.game_mode = mode
        self.character = ROSTER[self.selected_character]
        self.stats = self.new_stats()
        self.level_index = 0
        if mode == 0:
            self.begin_level(0)
            self.change_scene("PLAYING")
        else:
            self.change_scene("PLACEHOLDER_GAME")

    def begin_level(self, level_index):
        """Full reset of everything per-level: hearts, coins, checkpoint,
        enemies, movers, camera. Fresh entity objects each time."""
        self.level_index = int(clamp(level_index, 0, len(LEVEL_LAYOUTS) - 1))
        self.theme = LEVEL_THEMES[self.level_index]
        self.bg_base = self.make_background()
        d = load_level(LEVEL_LAYOUTS[self.level_index])
        self.level_data = d
        self.level_width, self.level_height = d["width"], d["height"]
        self.platforms = d["platforms"]
        self.one_way = d["one_way"] + []
        self.water = d["water"]
        self.spikes_floor = d["spikes_floor"]
        self.spikes_ceiling = d["spikes_ceil"]
        self.coins = d["coins"]
        self.checkpoints = d["checkpoints"]
        self.enemies = d["enemies"]
        self.flyers = d["flyers"]
        self.movers = d["movers"]
        self.solid_cells = d["solid_cells"]
        self.goal_rect = d["goal"]
        self.last_checkpoint = None
        self.coin_count = 0
        self._build_decor()
        self.one_way += self.bridge_one_way
        self.player = Player(self.character)
        sx, gy = d["start"]
        self.player.x = float(sx - self.player.w // 2)
        self.player.y = float(gy - self.player.h)
        self.player.sync_rect()
        self.camera_x = clamp(self.player.rect.centerx - WIDTH // 2, 0, max(0, self.level_width - WIDTH))
        self.camera_y = clamp(self.player.rect.centery - HEIGHT // 2, 0, max(0, self.level_height - HEIGHT))
        self.stats["lives"] = self.stats["max_lives"]       # hearts reset per level
        self.score_at_level_start = self.stats["score"]
        self.particles.clear()
        self.popups.clear()
        self.score_display = float(self.stats["score"])
        self.scene_fade = 160.0

    # ── camera ───────────────────────────────────────────────────
    def update_camera(self):
        tx = clamp(self.player.rect.centerx - WIDTH // 2, 0, max(0, self.level_width - WIDTH))
        ty = clamp(self.player.rect.centery - HEIGHT // 2 - 30, 0, max(0, self.level_height - HEIGHT))
        t = clamp(0.14 * self.dt_scale, 0.0, 1.0)
        self.camera_x += (tx - self.camera_x) * t
        self.camera_y += (ty - self.camera_y) * t

    # ── hazards / respawn ────────────────────────────────────────
    def _hurt(self, label):
        p = self.player
        if p.invincible_timer > 0:
            return
        self.stats["lives"] -= 1
        if self.stats["lives"] <= 0:
            self.stats["score"] = self.score_at_level_start   # clean level restart
            self.begin_level(self.level_index)
            return
        if self.last_checkpoint:
            gx, gy = self.last_checkpoint["x"], self.last_checkpoint["ground_y"]
        else:
            gx, gy = self.level_data["start"]
        p.x = float(gx - p.w // 2)
        p.y = float(gy - p.h)
        p.vx = p.vel_y = 0.0
        p.carried_by = None
        p.hurt_timer = 16.0
        p.invincible_timer = 60.0     # ~1s invincibility
        p.sync_rect()
        self.camera_x = clamp(p.rect.centerx - WIDTH // 2, 0, max(0, self.level_width - WIDTH))
        self.camera_y = clamp(p.rect.centery - HEIGHT // 2, 0, max(0, self.level_height - HEIGHT))
        self.add_popup(label, p.rect.centerx, p.rect.y - 40, CORAL)
        self.audio.play("wrong")

    # ── player ───────────────────────────────────────────────────
    def update_player(self):
        p = self.player
        p.invincible_timer = max(0.0, p.invincible_timer - self.dt_scale)
        keys = pygame.key.get_pressed()
        move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        if move:
            p.facing = move
            p.vx = clamp(p.vx + move * (ACCEL_GROUND if p.on_ground else ACCEL_AIR) * p.accel_mul * self.dt_scale, -p.max_speed, p.max_speed)
        else:
            p.vx *= (FRICTION_GROUND if p.on_ground else FRICTION_AIR) ** self.dt_scale
            if abs(p.vx) < 0.08:
                p.vx = 0.0
        # carried by moving platform (with crush test against static solids)
        if p.carried_by is not None:
            dx = p.carried_by.last_dx
            if dx:
                test = p.rect.move(int(dx), 0)
                if not any(test.colliderect(s) for s in self.platforms) and not any(test.colliderect(c) for c in self.crate_solids):
                    p.x += dx
        p.walking = abs(p.vx) > 0.35
        if p.walking:
            p.anim += self.dt_scale * (abs(p.vx) / MOVE_SPEED)
            if self.settings["particles"] and p.on_ground and int(self.frame) % 10 == 0:
                self.particles.append(Particle(p.rect.centerx, p.rect.bottom, (255, 190, 220), dust=True))
        static = self.platforms + self.crate_solids
        solids = static + [m.rect for m in self.movers]
        # X axis
        p.x += p.vx * self.dt_scale
        p.sync_rect()
        for s in solids:
            if p.rect.colliderect(s):
                if p.vx > 0:
                    p.rect.right = s.left
                elif p.vx < 0:
                    p.rect.left = s.right
                p.x = float(p.rect.x)
                p.vx = 0.0
        # jump (coyote + buffer)
        was_ground = p.on_ground
        p.coyote_timer = 7.0 if was_ground else max(0.0, p.coyote_timer - self.dt_scale)
        if p.jump_buffer > 0:
            p.jump_buffer = max(0.0, p.jump_buffer - self.dt_scale)
            if p.on_ground or p.coyote_timer > 0:
                p.execute_jump(self.particles, self.audio)
                was_ground = False
        # Y axis
        prev_bottom = p.rect.bottom
        jump_held = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]
        p.gliding = (p.can_glide and not p.on_ground and p.vel_y > 1.0 and jump_held)
        grav = GRAVITY * (0.42 if p.gliding else 1.0)
        max_fall = MAX_FALL_SPEED * (0.5 if p.gliding else 1.0)
        p.vel_y = min(p.vel_y + grav * self.dt_scale, max_fall)
        p.y += p.vel_y * self.dt_scale
        p.sync_rect()
        p.on_ground = False
        landed = False
        # hazards
        if p.rect.top > self.level_height + 60:
            self._hurt("FELL")
            return
        for w in self.water:
            if p.rect.colliderect(w):
                self._hurt("DROWNED")
                return
        for s in self.spikes_floor:
            if p.rect.colliderect(s):
                self._hurt("SPIKED")
                return
        for s in self.spikes_ceiling:
            if p.rect.colliderect(s):
                self._hurt("SPIKED")
                return
        for e in self.enemies + self.flyers:
            if p.rect.colliderect(e.rect):
                self._hurt("HIT")
                return
        # solid landing / ceiling
        for s in solids:
            if p.rect.colliderect(s):
                if p.vel_y >= 0 and prev_bottom <= s.top + 14:
                    p.rect.bottom = s.top
                    p.y = float(p.rect.y)
                    landed = True
                    break
                elif p.vel_y < 0 and p.rect.top >= s.bottom - 14:
                    p.rect.top = s.bottom
                    p.y = float(p.rect.y)
                    p.vel_y = 0.0
        # one-way platforms (jump up through, land on top)
        if not landed:
            for ow in self.one_way:
                if p.vel_y >= 0 and prev_bottom <= ow.top + 10 and p.rect.colliderect(ow):
                    p.rect.bottom = ow.top
                    p.y = float(p.rect.y)
                    landed = True
                    break
        if landed:
            p.carried_by = None
            for m in self.movers:
                if p.rect.colliderect(m.rect.inflate(0, 6)):
                    p.carried_by = m
                    break
            if not was_ground and p.vel_y > 3.5:
                p.land_squash = 1.0
                self.audio.play("land")
                if self.settings["particles"]:
                    self.particles.append(Particle(p.rect.centerx, p.rect.bottom, (255, 200, 226), ring=True))
            p.vel_y = 0.0
            p.on_ground = True
            p.gliding = False
            if p.jump_buffer > 0:
                p.execute_jump(self.particles, self.audio)
        if not p.on_ground:
            p.carried_by = p.carried_by if landed else p.carried_by
        p.land_squash = max(0.0, p.land_squash - 0.14 * self.dt_scale)
        p.hurt_timer = max(0.0, p.hurt_timer - self.dt_scale)
        p.update_scarf(self.dt_scale)

    # ── gameplay update ──────────────────────────────────────────
    def update_gameplay(self):
        for m in self.movers:
            m.update(self.dt_scale)
        for e in self.enemies:
            e.update(self.dt_scale, self)
        for e in self.flyers:
            e.update(self.dt_scale, self)
        self.update_player()
        if self.scene != "PLAYING":
            return
        self.update_camera()
        pr = self.player.rect.inflate(-6, -6)
        for c in self.coins:
            if not c["taken"] and pr.collidepoint(int(c["x"]), int(c["y"])):
                c["taken"] = True
                self.coin_count += 1
                self.stats["score"] += 50
                self.add_popup("+50", c["x"], c["y"] - 12, GOLD)
                self.add_particle_burst(c["x"], c["y"], GOLD, 10, 3.0)
                self.audio.play("coin")
        for cp in self.checkpoints:
            if not cp["active"] and pr.collidepoint(cp["x"], cp["ground_y"] - 26):
                cp["active"] = True
                self.last_checkpoint = cp
                self.add_popup("CHECKPOINT", cp["x"], cp["ground_y"] - 70, MINT)
                self.audio.play("click")
        if self.goal_rect and self.player.rect.colliderect(self.goal_rect):
            self.stats["score"] += 500
            self.add_popup("TRIAL COMPLETE", WIDTH // 2, 210, MINT)
            self.add_particle_burst(self.goal_rect.centerx, self.goal_rect.centery, GOLD, 45, 5.2)
            self.audio.play("level")
            if self.level_index < len(LEVEL_LAYOUTS) - 1:
                self.begin_level(self.level_index + 1)
            else:
                self.change_scene("VICTORY")
            return
        for pt in self.particles[:]:
            pt.update(self.dt_scale)
            if pt.life <= 0:
                self.particles.remove(pt)
        for pp in self.popups[:]:
            pp.update(self.dt_scale)
            if pp.life <= 0:
                self.popups.remove(pp)

    def add_particle_burst(self, x, y, color, count=20, power=4.0):
        if self.settings["particles"]:
            self.particles.extend(Particle(x, y, color, power=power) for _ in range(count))

    def add_popup(self, text, x, y, color=GOLD):
        self.popups.append(FloatingText(text, x, y, color))

    def change_scene(self, scene):
        self.scene, self.scene_fade, self.buttons = scene, 160.0, []
        if scene == "CHARACTER_SELECT":
            self.select.intro = 0.0
            self.select.pulse = 1.0
        self.audio.play("click")

    # ── world drawing ────────────────────────────────────────────
    def _draw_decor_item(self, surface, d, cx, cy):
        x, y = d["x"] - cx, d["y"] - cy
        if x + d["w"] < -8 or x > WIDTH + 8 or y + d["h"] < -8 or y > HEIGHT + 8:
            return
        if d["surf"] is not None:
            surface.blit(d["surf"], (int(x), int(y)))
            return
        # procedural fallbacks keep the level playable without the sheet
        t = d["type"]
        if t == "crate":
            pygame.draw.rect(surface, (122, 80, 68), (int(x), int(y), d["w"], d["h"]), border_radius=3)
            pygame.draw.rect(surface, (80, 50, 40), (int(x), int(y), d["w"], d["h"]), 2, border_radius=3)
        elif t == "rope_bridge":
            pygame.draw.rect(surface, (150, 108, 82), (int(x), int(y), d["w"], 6))
        elif t == "waterfall":
            wf = pygame.Surface((d["w"], d["h"]), pygame.SRCALPHA)
            wf.fill((186, 202, 244, 96))
            surface.blit(wf, (int(x), int(y)))
        elif t == "torii":
            pygame.draw.rect(surface, (206, 62, 92), (int(x), int(y), d["w"], d["h"]), 4)
        else:
            pygame.draw.rect(surface, (90, 70, 110), (int(x), int(y), d["w"], d["h"]))

    def draw_game_world(self):
        cx, cy = int(round(self.camera_x)), int(round(self.camera_y))
        self.world_scenery(config.world, self.frame, cx)
        world = config.world
        # decorations behind everything (culled)
        for d in self.decor_draw:
            if d["type"] not in ("crate", "rope_bridge"):
                self._draw_decor_item(world, d, cx, cy)
        # solids
        for p in self.platforms:
            rx, ry = p.x - cx, p.y - cy
            if rx + p.w < 0 or rx > WIDTH or ry + p.h < 0 or ry > HEIGHT:
                continue
            gradient_rect(world, (int(rx), int(ry), p.w, p.h), self.theme["ground_top"], self.theme["ground_bottom"])
            pygame.draw.rect(world, self.theme["accent"], (int(rx), int(ry), p.w, 5))
        for c in self.crate_solids:
            self._draw_decor_item(world, {"type": "crate", "x": c.x, "y": c.y, "w": c.w, "h": c.h, "surf": None}, cx, cy)
        for ow in self.one_way:
            rx, ry = ow.x - cx, ow.y - cy
            if rx + ow.w < 0 or rx > WIDTH:
                continue
            pygame.draw.rect(world, self.theme["accent"], (int(rx), int(ry), ow.w, ow.h), border_radius=3)
        for m in self.movers:
            rx, ry = m.rect.x - cx, m.rect.y - cy
            pygame.draw.rect(world, (176, 138, 100), (int(rx), int(ry), m.rect.w, m.rect.h), border_radius=4)
            pygame.draw.rect(world, blend_color((176, 138, 100), WHITE, 0.3), (int(rx), int(ry), m.rect.w, 3), border_radius=2)
        # hazards
        for s in self.spikes_floor:
            rx, ry = s.x - cx, s.y - cy
            if rx + s.w < 0 or rx > WIDTH:
                continue
            n = max(1, s.w // 20)
            step = s.w / n
            for i in range(n):
                pygame.draw.polygon(world, (226, 224, 236),
                                    [(int(rx + i * step) + 2, int(ry + s.h)), (int(rx + i * step + step) - 2, int(ry + s.h)), (int(rx + i * step + step / 2), int(ry))])
        for s in self.spikes_ceiling:
            rx, ry = s.x - cx, s.y - cy
            if rx + s.w < 0 or rx > WIDTH:
                continue
            n = max(1, s.w // 20)
            step = s.w / n
            for i in range(n):
                pygame.draw.polygon(world, (226, 224, 236),
                                    [(int(rx + i * step) + 2, int(ry)), (int(rx + i * step + step) - 2, int(ry)), (int(rx + i * step + step / 2), int(ry + s.h))])
        for w in self.water:
            rx, ry = w.x - cx, w.y - cy
            if rx + w.w < 0 or rx > WIDTH:
                continue
            ws = pygame.Surface((w.w, w.h), pygame.SRCALPHA)
            ws.fill((96, 150, 210, 150))
            wave = int(math.sin(self.frame * 0.1 + w.x * 0.05) * 2)
            world.blit(ws, (int(rx), int(ry) + 6 + wave))
        # bridges / crates in front of terrain but behind player
        for d in self.decor_draw:
            if d["type"] in ("crate", "rope_bridge"):
                self._draw_decor_item(world, d, cx, cy)
        # enemies
        for e in self.enemies + self.flyers:
            rx, ry = e.rect.x - cx, e.rect.y - cy
            if rx + e.rect.w < 0 or rx > WIDTH:
                continue
            col = (214, 84, 96) if e.kind == "walk" else (168, 124, 244)
            pygame.draw.rect(world, col, (int(rx), int(ry), e.rect.w, e.rect.h), border_radius=6)
            pygame.draw.circle(world, WHITE, (int(rx + e.rect.w // 2 + e.vx * 3), int(ry + 10)), 3)
        # coins
        for i, c in enumerate(self.coins):
            if c["taken"]:
                continue
            x, y = int(c["x"] - cx), int(c["y"] - cy + math.sin(self.frame * 0.06 + i) * 3)
            if x < -20 or x > WIDTH + 20 or y < -20 or y > HEIGHT + 20:
                continue
            spin = abs(math.cos(self.frame * 0.11 + i * 0.7))
            w = max(2, int(8 * spin))
            world.blit(get_radial_glow(15, GOLD, 34, 4), (x - 15, y - 15))
            pygame.draw.ellipse(world, GOLD, (x - w, y - 9, w * 2, 18))
            pygame.draw.ellipse(world, (146, 92, 22), (x - w, y - 9, w * 2, 18), 2)
        # checkpoints
        for cp in self.checkpoints:
            x, y = int(cp["x"] - cx), int(cp["ground_y"] - cy)
            if x < -40 or x > WIDTH + 40:
                continue
            pygame.draw.line(world, (200, 200, 210), (x, y), (x, y - 46), 4)
            col = MINT if cp["active"] else SUBTLE
            pygame.draw.polygon(world, col, [(x + 2, y - 46), (x + 26, y - 39), (x + 2, y - 32)])
            if cp["active"]:
                world.blit(get_radial_glow(24, MINT, 40, 4), (x - 24, y - 60))
        # goal
        if self.goal_rect:
            gx, gy = int(self.goal_rect.x - cx), int(self.goal_rect.y - cy)
            world.blit(get_radial_glow(46, GOLD, 42, 4), (gx - 26, gy - 40))
            pygame.draw.line(world, (214, 208, 226), (gx + 6, gy + self.goal_rect.h), (gx + 6, gy - 46), 4)
            wave = math.sin(self.frame * 0.12) * 4
            pygame.draw.polygon(world, CORAL, [(gx + 8, gy - 46), (gx + 46, gy - 36 + wave), (gx + 8, gy - 26)])
        # player
        temp_x, temp_y = self.player.x, self.player.y
        self.player.x -= cx
        self.player.y -= cy
        self.player.sync_rect()
        sy = self.get_shadow_surface_y() - cy
        self.player.draw(world, self.frame, sy)
        self.player.x, self.player.y = temp_x, temp_y
        self.player.sync_rect()
        for pt in self.particles:
            pt.draw(world)
        for pp in self.popups:
            pp.draw(world)
        offset = (0, 0)
        if self.shake > 0:
            i = max(1, int(self.shake / 3))
            offset = (random.randint(-i, i), random.randint(-i, i))
            self.shake = max(0.0, self.shake - self.dt_scale)
        config.canvas.fill(INK)
        config.canvas.blit(world, offset)
        self._draw_petals(config.canvas, cx)
        self.draw_hud()

    def get_shadow_surface_y(self):
        cx = self.player.rect.centerx
        best = float(self.level_height)
        for s in self.platforms:
            if s.left <= cx <= s.right and s.top >= self.player.rect.bottom - 4 and s.top < best:
                best = float(s.top)
        return best

    def draw_hud(self):
        n_hearts = self.stats.get("max_lives", MAX_HEARTS)
        hearts_pill = pygame.Rect(20, 18, 24 + n_hearts * 38, 46)
        draw_pill(config.canvas, hearts_pill)
        low = self.stats["lives"] == 1
        for i in range(n_hearts):
            active = i < self.stats["lives"]
            size = int(24 * ((1.0 + 0.14 * math.sin(self.frame * 0.22)) if (active and low) else 1.0))
            img = get_smooth_heart(size, CORAL if active else SUBTLE, filled=active)
            config.canvas.blit(img, img.get_rect(center=(hearts_pill.x + 31 + i * 38, hearts_pill.centery)))
        score_pill = pygame.Rect(hearts_pill.right + 12, 18, 176, 46)
        draw_pill(config.canvas, score_pill)
        star = get_smooth_star(22, GOLD)
        config.canvas.blit(star, star.get_rect(center=(score_pill.x + 26, score_pill.centery)))
        self.score_display = lerp(self.score_display, self.stats["score"], 0.16)
        draw_text(config.canvas, "SCORE", fonts.TINY, MUTED, (score_pill.x + 44, score_pill.y + 8))
        draw_text(config.canvas, f"{int(round(self.score_display)):,}", fonts.FONT, WHITE, (score_pill.x + 44, score_pill.y + 22))
        coin_pill = pygame.Rect(score_pill.right + 12, 18, 118, 46)
        draw_pill(config.canvas, coin_pill)
        spin = max(3, int(8 * abs(math.cos(self.frame * 0.11))))
        pygame.draw.ellipse(config.canvas, GOLD, (coin_pill.x + 16, coin_pill.centery - 10, spin * 2, 20))
        draw_text(config.canvas, "COINS", fonts.TINY, MUTED, (coin_pill.x + 44, coin_pill.y + 8))
        draw_text(config.canvas, f"{self.coin_count}/{len(self.coins)}", fonts.FONT, WHITE, (coin_pill.x + 44, coin_pill.y + 22))
        prog = pygame.Rect(WIDTH - 252, 18, 232, 46)
        draw_pill(config.canvas, prog)
        draw_text(config.canvas, f"LEVEL {self.level_index + 1}/5", fonts.SMALL, self.theme["accent"], (prog.x + 22, prog.centery), valign="middle")
        chip = pygame.Rect(20, HEIGHT - 46, 196, 32)
        draw_pill(config.canvas, chip, (16, 26, 42, 210), (*self.character["accent"], 90), shadow=False)
        if bank.has(self.character["id"]):
            bank.draw(config.canvas, self.character["id"], "idle", int(self.frame * 0.07) % bank.count(self.character["id"], "idle"), 44, HEIGHT - 17, 26, facing=1)
        draw_text(config.canvas, f"{self.character['name']} · {self.character['short']}", fonts.TINY, WHITE, (64, chip.centery), valign="middle")

    def draw_placeholder_game(self):
        self.world_scenery(config.canvas, self.frame)
        config.canvas.blit(veil(180), (0, 0))
        panel(config.canvas, (250, 150, 600, 350), (15, 25, 40, 240), (130, 162, 190, 100), 26, True)
        draw_text(config.canvas, self.mode_names[self.game_mode], fonts.LARGE, GOLD, (WIDTH // 2, 220), center=True)
        draw_text(config.canvas, self.mode_descriptions[self.game_mode], fonts.BODY, WHITE, (WIDTH // 2, 280), center=True)
        draw_text(config.canvas, "(Coming in the full release)", fonts.SMALL, MUTED, (WIDTH // 2, 320), center=True)
        self.make_button("placeholder_back", (420, 400, 260, 46), "RETURN TO MENU", "menu", GOLD)

    def make_button(self, key, rect, label, action, accent=GOLD):
        if key not in self.button_cache:
            self.button_cache[key] = Button(key, rect, label, action, accent)
        b = self.button_cache[key]
        b.rect, b.label, b.action, b.accent = pygame.Rect(rect), label, action, accent
        b.update(self.mouse_pos, self.dt_scale)
        b.draw(config.canvas)
        self.buttons.append(b)

    def draw_slider(self, key, label, value, y):
        x, width = 350, 400
        draw_text(config.canvas, label, fonts.TINY, MUTED, (x, y - 22))
        draw_text(config.canvas, f"{int(round(value * 100))}%", fonts.TINY, GOLD_SOFT, (x + width, y - 16), right=True)
        pygame.draw.rect(config.canvas, (36, 50, 70), (x, y, width, 8), border_radius=4)
        fill = int(width * value)
        if fill:
            pygame.draw.rect(config.canvas, MINT if key == "music" else BLUE, (x, y, fill, 8), border_radius=4)
        pygame.draw.circle(config.canvas, WHITE, (x + fill, y + 4), 9)
        pygame.draw.circle(config.canvas, GOLD if self.slider_drag == key else SUBTLE, (x + fill, y + 4), 9, 2)
        self.slider_rects = getattr(self, "slider_rects", {})
        self.slider_rects[key] = pygame.Rect(x - 12, y - 14, width + 24, 34)

    def draw_settings(self):
        # FIX: keep the start-screen look when opened from the menu
        if self.settings_return == "MENU":
            bg = self._title_background()
            if bg is not None:
                config.canvas.blit(bg, (0, 0))
                config.canvas.blit(veil(120), (0, 0))
            else:
                self.world_scenery(config.canvas, self.frame)
                config.canvas.blit(veil(120), (0, 0))
        else:
            self.draw_game_world()
            config.canvas.blit(veil(150), (0, 0))
        panel(config.canvas, (240, 82, 620, 486), (15, 25, 40, 236), (130, 162, 190, 90), 26, True)
        draw_text(config.canvas, "SETTINGS", fonts.LARGE, WHITE, (WIDTH // 2, 134), center=True, shadow=True)
        self.draw_slider("music", "MUSIC VOLUME", self.audio.music_volume, 236)
        self.draw_slider("sfx", "SOUND EFFECTS", self.audio.sfx_volume, 316)
        self.make_button("settings_fullscreen", (330, 388, 210, 46), "FULLSCREEN: ON" if self.settings["fullscreen"] else "FULLSCREEN: OFF", "fullscreen", BLUE)
        self.make_button("settings_particles", (560, 388, 210, 46), "PARTICLES: ON" if self.settings["particles"] else "PARTICLES: OFF", "particles", MINT)
        self.make_button("settings_back", (420, 476, 260, 46), "BACK", "back", GOLD)

    def draw_pause(self):
        self.draw_game_world()
        config.canvas.blit(veil(185), (0, 0))
        panel(config.canvas, (355, 130, 390, 390), (16, 27, 43, 245), (130, 162, 190, 100), 24, True)
        draw_text(config.canvas, "PAUSED", fonts.LARGE, WHITE, (WIDTH // 2, 184), center=True, shadow=True)
        draw_text(config.canvas, f"{self.character['name']} — {self.character['title'].upper()}", fonts.TINY, self.character["accent"], (WIDTH // 2, 216), center=True)
        self.make_button("pause_resume", (415, 236, 270, 46), "RESUME", "resume", MINT)
        self.make_button("pause_restart", (415, 294, 270, 46), "RESTART", "restart", GOLD)
        self.make_button("pause_menu", (415, 410, 270, 46), "MAIN MENU", "menu", CORAL)

    def draw_end_screen(self, title, subtitle, accent, buttons):
        self.world_scenery(config.canvas, self.frame)
        config.canvas.blit(veil(175), (0, 0))
        panel(config.canvas, (290, 118, 520, 420), (16, 27, 43, 242), (*accent, 115), 26, True)
        config.canvas.blit(get_radial_glow(64, accent, 42, 4), (WIDTH // 2 - 64, 120))
        pygame.draw.circle(config.canvas, accent, (WIDTH // 2, 184), 28, 2)
        if bank.has(self.character["id"]):
            bank.draw(config.canvas, self.character["id"], "idle", int(self.frame * 0.07) % bank.count(self.character["id"], "idle"), WIDTH // 2, 208, 50, facing=1)
        draw_text(config.canvas, title, fonts.LARGE, WHITE, (WIDTH // 2, 248), center=True, shadow=True)
        draw_text(config.canvas, subtitle, fonts.BODY, MUTED, (WIDTH // 2, 286), center=True)
        pill = pygame.Rect(WIDTH // 2 - 170, 318, 340, 44)
        draw_pill(config.canvas, pill, (22, 36, 56, 230), (*accent, 90), shadow=False)
        draw_text(config.canvas, f"SCORE: {self.stats['score']:,}    ·    COINS: {self.coin_count}", fonts.SMALL, WHITE, pill.center, center=True)
        for b in buttons:
            self.make_button(*b)

    def draw_scene(self):
        self.buttons = []
        if self.scene == "MENU":
            self.draw_menu()
        elif self.scene == "CHARACTER_SELECT":
            self.select.draw()
        elif self.scene == "SETTINGS":
            self.draw_settings()
        elif self.scene == "PLAYING":
            if self.game_mode == 0:
                self.draw_game_world()
            else:
                self.draw_placeholder_game()
        elif self.scene == "PLACEHOLDER_GAME":
            self.draw_placeholder_game()
        elif self.scene == "PAUSED":
            self.draw_pause()
        elif self.scene == "VICTORY":
            self.draw_end_screen("YOU WIN!", "All five trials mastered — a true Python trailblazer.", GOLD,
                                 [("victory_again", (415, 392, 270, 46), "PLAY AGAIN", "retry", GOLD),
                                  ("victory_menu", (415, 450, 270, 44), "MAIN MENU", "menu", BLUE)])
        if self.scene_fade > 0:
            v = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            v.fill((3, 9, 18, int(self.scene_fade)))
            config.canvas.blit(v, (0, 0))
            self.scene_fade = max(0.0, self.scene_fade - 14.0 * self.dt_scale)

    # ── input / flow ─────────────────────────────────────────────
    def set_fullscreen(self, enabled):
        self.settings["fullscreen"] = enabled
        try:
            config.screen = (pygame.display.set_mode((0, 0), pygame.FULLSCREEN) if enabled else pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE))
        except pygame.error:
            self.settings["fullscreen"] = False
            config.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

    def handle_button_action(self, action):
        if action in ("play", "retry", "begin_run"):
            self.start_game(0)
        elif action == "mode_0":
            self.change_scene("CHARACTER_SELECT")
        elif action.startswith("mode_"):
            self.start_game(int(action.split("_")[1]))
        elif action == "select_back":
            self.change_scene("MENU")
        elif action == "settings":
            self.settings_return = self.scene
            self.change_scene("SETTINGS")
        elif action == "back":
            self.change_scene(self.settings_return)
        elif action == "fullscreen":
            self.set_fullscreen(not self.settings["fullscreen"])
        elif action == "particles":
            self.settings["particles"] = not self.settings["particles"]
        elif action == "resume":
            self.change_scene("PLAYING")
        elif action == "restart":
            self.stats["score"] = self.score_at_level_start
            self.begin_level(self.level_index)
            self.change_scene("PLAYING")
        elif action == "menu":
            self.change_scene("MENU")
        elif action == "victory":
            self.change_scene("VICTORY")
        elif action == "quit":
            self.quit()

    def update_slider(self, mouse_x):
        value = clamp((mouse_x - 350) / 400, 0.0, 1.0)
        if self.slider_drag == "music":
            self.audio.set_music(value)
        elif self.slider_drag == "sfx":
            self.audio.set_sfx(value)

    def handle_mouse_down(self, pos):
        if self.scene == "MENU":
            for action in ("mode_0", "mode_1", "mode_2", "settings", "quit"):
                rect = self.button_cache.get(action, {}).get("rect")
                if rect and rect.collidepoint(pos):
                    self.audio.play("click")
                    self.handle_button_action(action)
                    return
        if self.scene == "CHARACTER_SELECT":
            if self.select.handle_click(pos):
                return
        if self.scene == "SETTINGS":
            for key, r in getattr(self, "slider_rects", {}).items():
                if r.collidepoint(pos):
                    self.slider_drag = key
                    self.update_slider(pos[0])
                    return
        for b in reversed(self.buttons):
            if b.rect.collidepoint(pos):
                b.press = 1.0
                self.handle_button_action(b.action)
                return

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = self.convert_mouse(event.pos)
                if self.slider_drag:
                    self.update_slider(self.mouse_pos[0])
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.slider_drag = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_pos = self.convert_mouse(event.pos)
                self.handle_mouse_down(self.mouse_pos)
            elif event.type == pygame.KEYUP:
                if self.scene == "PLAYING" and self.game_mode == 0 and self.player:
                    if event.key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE):
                        self.player.cut_jump()
                        self._jump_held = False
            elif event.type == pygame.KEYDOWN:
                if self.scene == "MENU":
                    if event.key == pygame.K_s:
                        self.settings_return = "MENU"
                        self.change_scene("SETTINGS")
                    elif event.key == pygame.K_ESCAPE:
                        self.quit()
                    elif event.key == pygame.K_1:
                        self.handle_button_action("mode_0")
                    elif event.key == pygame.K_2:
                        self.handle_button_action("mode_1")
                    elif event.key == pygame.K_3:
                        self.handle_button_action("mode_2")
                elif self.scene == "CHARACTER_SELECT":
                    self.select.handle_key(event.key)
                elif self.scene == "SETTINGS" and event.key == pygame.K_ESCAPE:
                    self.change_scene(self.settings_return)
                elif self.scene == "PLAYING" and self.game_mode == 0:
                    if event.key in (pygame.K_ESCAPE, pygame.K_p):
                        self.change_scene("PAUSED")
                    # FIX: ignore key-repeat so one press = one jump
                    if event.key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE):
                        if not self._jump_held:
                            self._jump_held = True
                            self.player.request_jump()
                elif self.scene == "PAUSED" and event.key == pygame.K_ESCAPE:
                    self.change_scene("MENU")
                elif self.scene == "VICTORY":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_game(0)
                    elif event.key == pygame.K_ESCAPE:
                        self.change_scene("MENU")

    def quit(self):
        pygame.quit()
        raise SystemExit

    def run(self):
        while True:
            # FIX: clamp dt to 2.0 so max fall step (33px) < player height (52px)
            self.dt_scale = clamp(config.clock.tick(FPS) / (1000.0 / FPS), 0.35, 2.0)
            self.frame += self.dt_scale
            self.mouse_pos = self.convert_mouse(pygame.mouse.get_pos())
            self.handle_events()
            if self.scene == "PLAYING" and self.game_mode == 0:
                self.update_gameplay()
            self.draw_scene()
            vp = self.get_viewport_rect()
            if vp.size == (WIDTH, HEIGHT) and vp.topleft == (0, 0):
                config.screen.blit(config.canvas, (0, 0))
            else:
                config.screen.fill((4, 8, 16))
                config.screen.blit(pygame.transform.smoothscale(config.canvas, vp.size), vp.topleft)
            pygame.display.flip()


SceneManager = Game