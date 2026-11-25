"""
GAME — Orchestrator: text-map levels, 2D clamped camera, autotiled terrain,
prop PNGs, spikes, movers that carry, checkpoints, i-frames.

Physics runs on a fixed 60 Hz accumulator; rendering runs at display rate.
Level reachability auditing lives in validate_levels.py (run it separately).

Progression: every moving platform starts LOCKED. Standing on (or next to) one
and pressing E opens a Python question (scene "QUIZ"); the right answer starts
the platform, a wrong one costs a heart. The level layouts make each mover
mandatory, so the questions gate progress.
"""
import os
import json
import math
import random
import pygame
import config
from config import (WIDTH, HEIGHT, FPS, GROUND_Y, INK, WHITE, MUTED, SUBTLE,
                    GOLD, GOLD_SOFT, MINT, CORAL, BLUE, CRIMSON, MAX_HEARTS,
                    GRAVITY, MAX_FALL_SPEED, MOVE_SPEED, ACCEL_GROUND, ACCEL_AIR,
                    FRICTION_GROUND, FRICTION_AIR, TILE, SKY_ROWS,
                    PHYSICS_DT, MAX_PHYSICS_STEPS,
                    HURT_FRAMES, INVULN_FRAMES, GLIDE_FRAMES,
                    GLIDE_GRAVITY_MUL, GLIDE_FALL_MUL, DROP_THROUGH_FRAMES,
                    KNOCKBACK_X, KNOCKBACK_Y, SAFE_GROUND_EVERY, TRY_AGAIN_FRAMES,
                    fonts)
from data import (LEVEL_LAYOUTS, LEVEL_THEMES, DECORATIONS, DECOR_SIZES,
                  MOVER_ROUTES, MOVER_QUESTIONS, make_question_deck)
from ui import (draw_text, gradient_rect, draw_pill, panel, get_radial_glow,
                get_smooth_heart, veil, Button, clamp, lerp, blend_color, get_text_image,
                wrap_text)
from audio import AudioManager
from entities import Player, Particle, FloatingText, MovingPlatform
from sprites import bank, ROSTER
from character_select import CharacterSelect, draw_fallback_hero

_MENU_CACHE = {}
HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(HERE, "savegame.json")

TITLE_BG_CANDIDATES = (os.path.join("assets", "ui", "title_bg.png"),
                       os.path.join("assets", "title_bg.png"), "title_bg.png")
TILE_SHEET_CANDIDATES = (os.path.join("assets", "tiles", "sakura_tiles.png"),
                         os.path.join("assets", "tiles", "tiles.png"),
                         os.path.join("assets", "sprites", "sakura_tiles.png"),
                         os.path.join("assets", "tileset.png"),
                         "sakura_tiles.png", "tiles.png")
DECOR_SHEET_CANDIDATES = (os.path.join("assets", "props", "decorations.png"),
                          os.path.join("assets", "sprites", "decorations.png"),
                          os.path.join("assets", "props", "props.png"),
                          os.path.join("assets", "props.png"),
                          "decorations.png", "props.png")
PROP_FILE_MAP = {
    "torii": "torii.png", "stone_lantern": "stone_lantern.png",
    "hanging_lantern": "lantern_post.png", "banner": "banner.png",
    "shrine": "shrine.png", "tree": "sakura_tree.png", "bush": "bush_pink.png",
    "crate": "crate.png", "fence": "fence.png", "sign": "signpost.png",
    "rope_bridge": "rope_bridge.png", "waterfall": "waterfall.png",
}
PROP_DIRS = (os.path.join("assets", "props"), os.path.join("assets", "sprites"),
             os.path.join("assets", "props", "props"), "assets", "")
# Flame positions as fractions of the prop SPRITE (measured from the PNGs);
# the procedural fallbacks use the same fractions of their box.
LAMP_SPOTS = {"stone_lantern": [(0.49, 0.44)], "hanging_lantern": [(0.80, 0.53)],
              "shrine": [(0.17, 0.68), (0.83, 0.68)]}
LAMP_POOL = {"stone_lantern", "hanging_lantern"}       # cast a light pool on the ground
WARM, WARM_CORE = (255, 168, 78), (255, 232, 170)
KNOWN_CHARS = set("=|-M^v~KPG ")
JUMP_KEYS = (pygame.K_w, pygame.K_UP, pygame.K_SPACE)
DOWN_KEYS = (pygame.K_s, pygame.K_DOWN)
GATE_KEYS = (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER)
ANSWER_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)
WORLD_SCENES = ("PLAYING", "PAUSED", "SETTINGS", "CONFIRM_MENU", "TRY_AGAIN",
                "LEVEL_CLEAR", "QUIZ")


def _fmt_time(sec):
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _p(*parts):
    return os.path.join(HERE, *parts)


def _alpha_grad(w, h, horizontal, a0, a1, color=(8, 10, 20)):
    key = ("ag", w, h, horizontal, a0, a1, color)
    hit = _MENU_CACHE.get(key)
    if hit is not None:
        return hit
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    n = w if horizontal else h
    for i in range(n):
        a = int(a0 + (a1 - a0) * (i / max(1, n - 1)))
        if horizontal:
            pygame.draw.line(s, (*color, a), (i, 0), (i, h - 1))
        else:
            pygame.draw.line(s, (*color, a), (0, i), (w - 1, i))
    if len(_MENU_CACHE) > 80:
        _MENU_CACHE.clear()
    _MENU_CACHE[key] = s
    return s


def _plain_surface(w, h, color):
    key = ("plain", w, h, tuple(color))
    hit = _MENU_CACHE.get(key)
    if hit is not None:
        return hit
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill(color)
    if len(_MENU_CACHE) > 80:
        _MENU_CACHE.clear()
    _MENU_CACHE[key] = s
    return s


def load_level(layout_text, routes=None):
    """Parse an ASCII layout. Unknown characters are reported, never crash.

    routes: {(row, col_of_leftmost_M): (dx_tiles, dy_tiles)}. A mover listed
    there is question-gated (starts locked); one that is not listed falls back
    to the old always-on sideways patrol.
    """
    routes = routes or {}
    rows = []
    for ln in layout_text.split("\n"):
        s = ln
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        rows.append(s)
    cols = max((len(r) for r in rows), default=0)
    rows = [r.ljust(cols) for r in rows]
    n = len(rows)
    width, height = cols * TILE, (n + SKY_ROWS) * TILE

    platforms, one_way, water = [], [], []
    spike_runs_floor, spike_runs_ceil = [], []
    spikes_floor, spikes_ceil = [], []
    checkpoints, movers, unknown = [], [], []
    start = (TILE, height - TILE)
    goal = None

    for r in range(n):
        c = 0
        while c < cols:
            ch = rows[r][c]
            x, y = c * TILE, (r + SKY_ROWS) * TILE
            if ch in "=|":
                c0 = c
                while c < cols and rows[r][c] in "=|":
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
                route = routes.get((r, c0))
                movers.append(MovingPlatform(x, y, c - c0, route=route,
                                             locked=route is not None))
                continue
            if ch == "^":
                c0 = c
                while c < cols and rows[r][c] == "^":
                    c += 1
                w = (c - c0) * TILE
                platforms.append(pygame.Rect(x, y, w, TILE))
                spike_runs_floor.append((x, y, w))
                spikes_floor.append(pygame.Rect(x + 6, y - 24, w - 12, 24))
                continue
            if ch == "v":
                c0 = c
                while c < cols and rows[r][c] == "v":
                    c += 1
                w = (c - c0) * TILE
                spike_runs_ceil.append((x, y, w))
                spikes_ceil.append(pygame.Rect(x + 6, y, w - 12, 24))
                continue
            if ch == "~":
                c0 = c
                while c < cols and rows[r][c] == "~":
                    c += 1
                water.append(pygame.Rect(x, y, (c - c0) * TILE, TILE))
                continue
            if ch == "K":
                checkpoints.append({"x": x + TILE // 2, "ground_y": y + TILE, "active": False})
            elif ch == "P":
                start = (x + TILE // 2, y + TILE)
            elif ch == "G":
                goal = pygame.Rect(x + 4, y - 10, TILE - 8, TILE + 10)
            elif ch not in KNOWN_CHARS:
                unknown.append((ch, r, c))
            c += 1

    return {"width": width, "height": height, "platforms": platforms, "one_way": one_way,
            "water": water, "spikes_floor": spikes_floor, "spikes_ceil": spikes_ceil,
            "spike_runs_floor": spike_runs_floor, "spike_runs_ceil": spike_runs_ceil,
            "checkpoints": checkpoints, "movers": movers,
            "start": start, "goal": goal, "unknown": unknown}


class Game:
    def __init__(self):
        self.audio = AudioManager()
        self.scene, self.settings_return = "MENU", "MENU"
        self.selected_character = 0
        self.character = ROSTER[0]
        self.settings = {"fullscreen": False, "particles": True}
        self.best_time, self.new_record = None, False
        self._load_save()
        self.stats = self.new_stats()
        self.level_index = 0
        self.theme = LEVEL_THEMES[0]
        self.dt_scale, self.frame, self.scene_fade = 1.0, 0.0, 0.0
        self.accumulator = 0.0
        self.buttons, self.button_cache, self.mouse_pos = [], {}, (0, 0)
        self.particles, self.popups = [], []
        self.player = None
        self.camera_x, self.camera_y = 0.0, 0.0
        self.level_width, self.level_height = WIDTH, HEIGHT
        self.shake = 0.0
        self.slider_drag = None
        self.slider_rects = {}
        self.title_bob = 0.0
        self.pause_index = 0
        self.try_again_timer = 0
        self.clear_timer = 0.0
        self.banner_timer = 0.0
        self.look = 0.0
        self._step_count = 0
        self._scaled_canvas = (None, None)

        self.motes = [(random.randrange(WIDTH), random.randrange(70, GROUND_Y - 30),
                       random.random() * math.tau) for _ in range(38)]
        self.clouds = [(110, 92, 1.0, 0.10), (470, 64, 1.2, 0.07), (840, 128, 0.9, 0.12)]
        self.petals = [{"x": random.randrange(WIDTH), "y": random.randrange(HEIGHT),
                        "ph": random.random() * math.tau, "sp": random.uniform(0.45, 1.1),
                        "sw": random.uniform(10, 28), "sz": random.randint(3, 6)}
                       for _ in range(26)]
        self._title_bg = None
        self._title_bg_missing = False
        self.select = CharacterSelect(self)
        self.tiles = self._load_tile_sheet()
        self.decor_sprites = self._load_decor_sprites()
        self._bg_arts = {}
        self._decor_scaled = {}
        self.level_data = None
        self.sky_surf = None
        self.bg_art = None
        self.bg_par = 0.2
        self.bg_par_y = 0.0
        self.terrain_surf = None
        self.one_way_cap = None
        self.platforms, self.one_way, self.water = [], [], []
        self.spikes_floor, self.spikes_ceiling = [], []
        self.spike_runs_floor, self.spike_runs_ceil = [], []
        self.checkpoints, self.movers = [], []
        self.crate_solids, self.bridge_one_way = [], []
        self.last_checkpoint = None
        self.last_safe = None
        self.goal_rect = None
        self.decor_draw = []
        self.terrain_shadow = None
        self.quiz = None
        self.quiz_deck = []
        self.gate_hint = None
        self.bg_base = self.make_background()
        if self.settings["fullscreen"]:
            self.set_fullscreen(True)

    # ── save file ────────────────────────────────────────────────
    def _load_save(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            idx = int(d.get("character", 0))
            if 0 <= idx < len(ROSTER):
                self.selected_character, self.character = idx, ROSTER[idx]
            self.settings["fullscreen"] = bool(d.get("fullscreen", False))
            self.settings["particles"] = bool(d.get("particles", True))
            self.audio.set_music(float(d.get("music", self.audio.music_volume)))
            self.audio.set_sfx(float(d.get("sfx", self.audio.sfx_volume)))
            bt = d.get("best_time")
            self.best_time = float(bt) if bt else None
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def _save(self):
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump({"character": self.selected_character,
                           "fullscreen": self.settings["fullscreen"],
                           "particles": self.settings["particles"],
                           "music": round(self.audio.music_volume, 3),
                           "sfx": round(self.audio.sfx_volume, 3),
                           "best_time": self.best_time}, f)
        except OSError:
            pass

    # ── assets ───────────────────────────────────────────────────
    def _load_tile_sheet(self):
        for cand in TILE_SHEET_CANDIDATES:
            p = cand if os.path.isabs(cand) else _p(cand)
            if not os.path.isfile(p):
                continue
            try:
                sheet = pygame.image.load(p).convert_alpha()
                w, h = sheet.get_size()
                cw, ch = w // 8, h // 2
                if cw < 1 or ch < 1:
                    raise pygame.error(f"tileset too small: {w}x{h}")
                tiles = []
                for i in range(16):
                    t = sheet.subsurface(pygame.Rect((i % 8) * cw, (i // 8) * ch, cw, ch)).copy()
                    tiles.append(pygame.transform.scale(t, (TILE, TILE)))
                print(f"[game] tileset loaded: {p}")
                return tiles
            except (pygame.error, ValueError, OSError) as e:
                print(f"[game] tileset failed ({p}): {e}")
        print("[game] WARNING tileset not found or unreadable — procedural terrain fallback")
        return None

    @staticmethod
    def _strip_magenta(surf):
        try:
            arr = pygame.PixelArray(surf)
            arr.replace((255, 0, 255, 255), (0, 0, 0, 0), distance=0.18)
            del arr
            return surf
        except Exception:
            pass
        try:
            surf.set_colorkey((255, 0, 255))
        except pygame.error:
            pass
        return surf

    def _load_decor_sprites(self):
        out = {}
        for t, fn in PROP_FILE_MAP.items():
            for sub in PROP_DIRS:
                p = os.path.join(HERE, sub, fn) if sub else os.path.join(HERE, fn)
                if not os.path.isfile(p):
                    continue
                try:
                    out[t] = self._strip_magenta(pygame.image.load(p).convert_alpha())
                except (pygame.error, ValueError, OSError) as e:
                    print(f"[game] decor load failed {p}: {e}")
                break
        missing = [t for t in PROP_FILE_MAP if t not in out]
        if missing:
            for cand in DECOR_SHEET_CANDIDATES:
                p = cand if os.path.isabs(cand) else _p(cand)
                if not os.path.isfile(p):
                    continue
                try:
                    sheet = pygame.image.load(p).convert()
                    sheet.set_colorkey((255, 0, 255))
                    w, h = sheet.get_size()
                    cw, ch = w // 4, h // 3
                    order = ["torii", "stone_lantern", "hanging_lantern", "banner",
                             "shrine", "tree", "bush", "crate",
                             "fence", "sign", "rope_bridge", "waterfall"]
                    for i, nm in enumerate(order):
                        if nm in missing:
                            out[nm] = sheet.subsurface(
                                pygame.Rect((i % 4) * cw, (i // 4) * ch, cw, ch)).copy()
                except (pygame.error, ValueError, OSError) as e:
                    print(f"[game] decor sheet failed ({p}): {e}")
                break
        still = [t for t in PROP_FILE_MAP if t not in out]
        if still:
            print(f"[game] WARNING decor missing (procedural fallback): {still}")
        return out

    def _load_bg_art(self, idx):
        if idx in self._bg_arts:
            return self._bg_arts[idx]
        art = None
        for cand in (os.path.join("assets", "bg", f"level{idx + 1}.png"),
                     os.path.join("assets", "bg", f"bg{idx + 1}.png")):
            p = cand if os.path.isabs(cand) else _p(cand)
            if not os.path.isfile(p):
                continue
            try:
                art = pygame.image.load(p).convert_alpha()
                if art.get_height() < HEIGHT:
                    nw = max(WIDTH, int(round(art.get_width() * (HEIGHT / art.get_height()))))
                    art = pygame.transform.scale(art, (nw, HEIGHT))
                if art.get_width() < WIDTH:
                    nh = max(HEIGHT, int(round(art.get_height() * (WIDTH / art.get_width()))))
                    art = pygame.transform.scale(art, (WIDTH, nh))
                # Darken + cool the painted backdrop so it never competes with
                # the playable terrain (multiply keeps the alpha channel intact).
                tint = LEVEL_THEMES[idx].get("bg_tint", (120, 110, 140))
                art = art.copy()
                art.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            except (pygame.error, ValueError, OSError) as e:
                print(f"[game] WARNING background failed ({p}): {e} — procedural sky")
                art = None
            break
        if art is None:
            print(f"[game] WARNING no background art for level {idx + 1} — procedural sky")
        self._bg_arts[idx] = art
        return art

    def _decor_surf(self, t, pw, ph):
        key = (t, pw, ph)
        hit = self._decor_scaled.get(key)
        if hit is not None:
            return hit
        base = self.decor_sprites.get(t)
        if base is None:
            return None
        bw, bh = base.get_size()
        s = min(pw / max(1, bw), ph / max(1, bh))
        nw, nh = max(1, int(round(bw * s))), max(1, int(round(bh * s)))
        scaled = pygame.transform.scale(base, (nw, nh))
        out = pygame.Surface((pw, ph), pygame.SRCALPHA)
        out.blit(scaled, ((pw - nw) // 2, ph - nh))
        if len(self._decor_scaled) > 120:
            self._decor_scaled.clear()
        self._decor_scaled[key] = out
        return out

    # ── basics ───────────────────────────────────────────────────
    def new_stats(self):
        mh = MAX_HEARTS + self.character.get("traits", {}).get("bonus_hearts", 0)
        return {"lives": mh, "max_lives": mh, "time": 0.0, "hits": 0,
                "answered": 0, "correct": 0}

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
            for base in (HERE, os.getcwd()):
                q = os.path.join(base, cand)
                if os.path.isfile(q):
                    path = q
                    break
            if path:
                break
        if path is None:
            self._title_bg_missing = True
            print("[game] no title background — procedural menu")
            return None
        try:
            img = pygame.image.load(path).convert()
            scale = max(WIDTH / img.get_width(), HEIGHT / img.get_height())
            nw = max(WIDTH, int(round(img.get_width() * scale)))
            nh = max(HEIGHT, int(round(img.get_height() * scale)))
            img = pygame.transform.scale(img, (nw, nh))
            rx, ry = (nw - WIDTH) // 2, (nh - HEIGHT) // 2
            self._title_bg = img.subsurface(pygame.Rect(rx, ry, WIDTH, HEIGHT)).copy()
        except (pygame.error, ValueError, OSError) as e:
            print(f"[game] WARNING title background failed: {e}")
            self._title_bg_missing = True
        return self._title_bg

    def _petal_surf(self, sz, rb):
        key = ("petal", sz, rb)
        s = _MENU_CACHE.get(key)
        if s is None:
            base = pygame.Surface((sz * 3, sz * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(base, (244, 152, 192, 205), base.get_rect())
            s = pygame.transform.rotate(base, rb * 12)
            if len(_MENU_CACHE) > 80:
                _MENU_CACHE.clear()
            _MENU_CACHE[key] = s
        return s

    def _draw_petals(self, surface, cam=0):
        for p in self.petals:
            y = (p["y"] + self.frame * p["sp"]) % (HEIGHT + 40) - 20
            x = (p["x"] + math.sin(self.frame * 0.02 + p["ph"]) * p["sw"] - cam * 0.35) % WIDTH
            surface.blit(self._petal_surf(p["sz"], int(math.sin(self.frame * 0.05 + p["ph"]) * 4)),
                         (int(x), int(y)))

    def _menu_options(self):
        return [("I.  THE ASCENT", "mode_0", True),
                ("II.  THE LABYRINTH  ·  COMING SOON", "mode_1", False),
                ("III.  THE STORM  ·  COMING SOON", "mode_2", False),
                ("SETTINGS", "settings", True),
                ("QUIT", "quit", True)]

    def _register_menu_rect(self, action, rect, enabled):
        entry = self.button_cache.get(action)
        if isinstance(entry, dict):
            entry["rect"], entry["enabled"] = rect, enabled
        else:
            self.button_cache[action] = {"rect": rect, "action": action, "enabled": enabled}

    # ── menu ─────────────────────────────────────────────────────
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
        draw_text(cv, "THE THREE TRIALS", fonts.LARGE, (0, 0, 0), (WIDTH // 2 + 4, title_y + 4),
                  center=True, shadow=True)
        draw_text(cv, "THE THREE TRIALS", fonts.LARGE, WHITE, (WIDTH // 2, title_y), center=True)
        draw_text(cv, "A PYTHON JOURNEY", fonts.SMALL, GOLD_SOFT, (WIDTH // 2, title_y + 46),
                  center=True)
        start_y, gap = 252, 54
        for i, (text, action, enabled) in enumerate(self._menu_options()):
            y = start_y + i * gap
            rect = pygame.Rect(44, y - 21, 340, 42)
            hovered = enabled and rect.collidepoint(self.mouse_pos)
            if hovered:
                draw_pill(cv, rect, (16, 22, 38, 190), (*GOLD, 150), shadow=False)
                pygame.draw.polygon(cv, GOLD, [(rect.x + 10, rect.centery - 6),
                                               (rect.x + 10, rect.centery + 6),
                                               (rect.x + 20, rect.centery)])
                draw_text(cv, text, fonts.FONT, GOLD, (rect.x + 34, rect.centery), valign="middle")
            else:
                color = WHITE if enabled else SUBTLE
                draw_text(cv, text, fonts.FONT, color, (rect.x + 34, rect.centery), valign="middle")
            self._register_menu_rect(action, rect, enabled)
        chip = pygame.Rect(24, HEIGHT - 54, 214, 34)
        draw_pill(cv, chip, (14, 20, 34, 210), (*self.character["accent"], 110), shadow=False)
        if bank.has(self.character["id"]):
            bank.draw(cv, self.character["id"], "idle",
                      int(self.frame * 0.07) % bank.count(self.character["id"], "idle"),
                      48, HEIGHT - 24, 26, facing=1)
        else:
            draw_fallback_hero(cv, self.character, 48, HEIGHT - 24, 26, self.frame)
        draw_text(cv, f"{self.character['name']} · {self.character['short']}", fonts.TINY, WHITE,
                  (66, chip.centery), valign="middle")
        draw_text(cv, "1 PLAY   ·   S SETTINGS   ·   ESC QUIT", fonts.TINY, (214, 224, 238),
                  (WIDTH - 24, HEIGHT - 22), right=True)

    def _draw_menu_procedural(self):
        cv = config.canvas
        self.world_scenery(cv, self.frame)
        pygame.draw.ellipse(cv, (0, 0, 0), (830, GROUND_Y - 5, 40, 10))
        pygame.draw.rect(cv, INK, (838, GROUND_Y - 40, 24, 40), border_radius=4)
        pygame.draw.circle(cv, INK, (850, GROUND_Y - 50), 14)
        pygame.draw.polygon(cv, CRIMSON, [(845, GROUND_Y - 35), (825, GROUND_Y - 30),
                                          (810, GROUND_Y - 38), (815, GROUND_Y - 25)])
        self._draw_petals(cv)
        self.title_bob = math.sin(self.frame * 0.03) * 4
        title_y = 130 + self.title_bob
        draw_text(cv, "THE THREE TRIALS", fonts.LARGE, CRIMSON, (WIDTH // 2, title_y),
                  center=True, shadow=True)
        draw_text(cv, "THE THREE TRIALS", fonts.LARGE, WHITE, (WIDTH // 2 - 2, title_y - 2),
                  center=True)
        draw_text(cv, "A PYTHON JOURNEY", fonts.SMALL, GOLD_SOFT, (WIDTH // 2, title_y + 55),
                  center=True)
        start_y, gap = 280, 55
        for i, (text, action, enabled) in enumerate(self._menu_options()):
            y = start_y + i * gap
            rect = pygame.Rect(WIDTH // 2 - 200, y - 20, 400, 40)
            hovered = enabled and rect.collidepoint(self.mouse_pos)
            if hovered:
                pygame.draw.polygon(cv, GOLD, [(rect.left - 20, rect.centery - 6),
                                               (rect.left - 20, rect.centery + 6),
                                               (rect.left - 8, rect.centery)])
                draw_text(cv, text, fonts.FONT, GOLD, (WIDTH // 2, y), center=True)
            else:
                draw_text(cv, text, fonts.FONT, WHITE if enabled else SUBTLE,
                          (WIDTH // 2, y), center=True)
            self._register_menu_rect(action, rect, enabled)

    def make_background(self):
        bg = pygame.Surface((WIDTH, HEIGHT)).convert()
        th = self.theme
        gradient_rect(bg, (0, 0, WIDTH, HEIGHT), th["sky_top"], th["sky_bottom"])
        rng = random.Random(42 + self.level_index * 19)
        for _ in range(55):
            shade = rng.randint(120, 200)
            pygame.draw.circle(bg, (shade, min(255, shade + 12), min(255, shade + 24)),
                               (rng.randrange(WIDTH), rng.randrange(24, 290)), 1)
        cx, cy = 830, 132
        bg.blit(get_radial_glow(150, th["celestial"], 34, 5), (cx - 150, cy - 150))
        pygame.draw.circle(bg, th["celestial"], (cx, cy), 34)
        pygame.draw.polygon(bg, th["ridge_far"],
                            [(0, 410), (140, 250), (290, 365), (460, 215), (630, 355),
                             (810, 235), (980, 350), (1100, 285), (1100, GROUND_Y), (0, GROUND_Y)])
        pygame.draw.polygon(bg, th["ridge_mid"],
                            [(0, 445), (210, 310), (390, 430), (590, 315), (780, 435),
                             (960, 305), (1100, 390), (1100, GROUND_Y), (0, GROUND_Y)])
        pygame.draw.polygon(bg, th["ridge_near"],
                            [(0, 485), (170, 415), (360, 492), (560, 420), (760, 495),
                             (940, 425), (1100, 475), (1100, GROUND_Y), (0, GROUND_Y)])
        gradient_rect(bg, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y),
                      th["ground_top"], th["ground_bottom"])
        return bg

    def _cloud_surf(self, w, h):
        return _plain_surface(w, h, (255, 255, 255, 18))

    def world_scenery(self, target, frame, cam=0, cam_y=0):
        in_world = self.sky_surf is not None and self.scene in WORLD_SCENES
        if in_world:
            target.blit(self.sky_surf, (0, 0))
            if self.bg_art is not None:
                off = -int(clamp(cam * self.bg_par, 0, max(0, self.bg_art.get_width() - WIDTH)))
                off_y = -int(clamp(cam_y * self.bg_par_y, 0,
                                   max(0, self.bg_art.get_height() - HEIGHT)))
                target.blit(self.bg_art, (off, off_y))
        else:
            target.blit(self.bg_base, (0, 0))
        for cx, cy, scale, speed in self.clouds:
            x = (cx + frame * speed - cam * 0.10) % (WIDTH + 200) - 100
            w, h = max(4, int(96 * scale)), max(4, int(22 * scale))
            target.blit(self._cloud_surf(w, h), (int(x), int(cy - cam_y * 0.05)))
        for x, y, phase in self.motes:
            pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(frame * 0.035 + phase))
            xx = (x + math.sin(frame * 0.015 + phase) * 8 - cam * 0.25) % WIDTH
            yy = y + math.cos(frame * 0.02 + phase) * 5 - cam_y * 0.08
            pygame.draw.circle(target, self.theme["mote"], (int(xx), int(yy)),
                               2 if pulse > 0.75 else 1)
        if in_world:
            # Depth haze: pushes the backdrop back so terrain reads as foreground.
            target.blit(_alpha_grad(WIDTH, HEIGHT, False, 30, 125, self.theme["sky_top"]),
                        (0, 0))

    # ── level lifecycle ──────────────────────────────────────────
    def start_game(self):
        self.character = ROSTER[self.selected_character]
        self._save()
        self.stats = self.new_stats()
        self.level_index = 0
        self.begin_level(0)
        self.change_scene("PLAYING")

    def _build_sky(self):
        th = self.theme
        sky = pygame.Surface((WIDTH, HEIGHT)).convert()
        gradient_rect(sky, (0, 0, WIDTH, HEIGHT), th["sky_top"], th["sky_bottom"])
        rng = random.Random(7 + self.level_index * 31)
        for _ in range(60):
            shade = rng.randint(90, 170)
            pygame.draw.circle(sky, (shade, shade, min(255, shade + 18)),
                               (rng.randrange(WIDTH), rng.randrange(10, 320)), 1)
        if self.bg_art is None:
            # the painted backdrops have their own moon; only draw one here
            cx, cy = 830, 120
            sky.blit(get_radial_glow(170, th["celestial"], 26, 6), (cx - 170, cy - 170))
            pygame.draw.circle(sky, blend_color(th["celestial"], th["sky_top"], 0.25), (cx, cy), 40)
            # No painted backdrop for this level: low, dark ridges for depth.
            pygame.draw.polygon(sky, th["ridge_far"],
                                [(0, 470), (160, 340), (330, 430), (520, 300), (700, 420),
                                 (880, 320), (1100, 410), (1100, HEIGHT), (0, HEIGHT)])
            pygame.draw.polygon(sky, th["ridge_mid"],
                                [(0, 520), (230, 410), (430, 500), (640, 400), (850, 505),
                                 (1000, 420), (1100, 470), (1100, HEIGHT), (0, HEIGHT)])
            pygame.draw.polygon(sky, th["ridge_near"],
                                [(0, 580), (190, 520), (400, 585), (610, 525), (820, 590),
                                 (980, 540), (1100, 575), (1100, HEIGHT), (0, HEIGHT)])
        self.sky_surf = sky

    def _mover_cells(self):
        """Tiles a mover rests on/over at any point of its route: no tufts there."""
        out = set()
        for m in self.movers:
            for (x, y) in ((m.ax, m.ay), m.route_end):
                for cc in range(int(x) // TILE, (int(x) + m.rect.w - 1) // TILE + 1):
                    out.add((cc, (int(y) + 20) // TILE))
        return out

    def _build_terrain(self):
        self.terrain_surf = None
        self.terrain_shadow = None
        self.one_way_cap = None
        if not self.tiles:
            self._build_fallback_terrain()
            self._build_terrain_shadow()
            return
        surf = pygame.Surface((self.level_width, self.level_height), pygame.SRCALPHA)
        cells = set()
        for rct in self.platforms:
            for cc in range(rct.x // TILE, (rct.x + rct.w) // TILE):
                cells.add((cc, rct.y // TILE))
        T_ = self.tiles
        # Sheet: 1 grass-mid 2 grass-left 3 grass-right | 4/15 stone fill
        #        5 stone-left 6 stone-right | 7/8 floating-island caps | 9 grass block
        for (c, r) in cells:
            up = (c, r - 1) in cells
            lf, rt = (c - 1, r) in cells, (c + 1, r) in cells
            if not up:
                # surface row: the only place grass belongs
                gid = 2 if not lf else (3 if not rt else 1)
            else:
                # everything under a surface is plain stone (previously the
                # bottom row used grass-topped tiles, painting a second grass
                # stripe through the middle of the ground)
                gid = 5 if not lf else (6 if not rt else (4 if (c * 7 + r * 13) % 3 else 15))
            surf.blit(T_[gid - 1], (c * TILE, r * TILE))
        no_tuft = self._mover_cells()
        for (c, r) in cells:
            hsh = (c * 31 + r * 17) % 97
            if ((c, r - 1) not in cells and hsh % 4 == 0 and (c, r - 1) not in no_tuft
                    and (c, r) not in no_tuft):
                surf.blit(T_[9 if hsh % 8 else 10], (c * TILE, (r - 1) * TILE))
            if (c, r + 1) not in cells and (c, r - 1) not in cells and (c * 13 + r * 7) % 5 == 0:
                surf.blit(T_[15], (c * TILE, (r + 1) * TILE))
        # One-way ledges: a slim lip cut from the grass tiles (left/mid/right
        # ends) so they read as solid-looking shelves rather than loose grass.
        lip_h = 22
        lips = [pygame.transform.scale(T_[g - 1].subsurface(
                    pygame.Rect(0, 0, TILE, int(TILE * 0.62))), (TILE, lip_h))
                for g in (2, 1, 3)]
        self.one_way_cap = lips[1]
        under = pygame.Surface((TILE, 6), pygame.SRCALPHA)
        under.fill((0, 0, 0, 70))
        for ow in self.one_way:
            c0, c1 = ow.x // TILE, (ow.x + ow.w) // TILE
            for cc in range(c0, c1):
                lip = lips[0] if cc == c0 else (lips[2] if cc == c1 - 1 else lips[1])
                surf.blit(lip, (cc * TILE, ow.y - 4))
                surf.blit(under, (cc * TILE, ow.y - 4 + lip_h))
        for (x, y, w) in self.spike_runs_floor:
            n = max(1, w // TILE)
            for i in range(n):
                gid = 12 if i == 0 else (14 if i == n - 1 else 13)
                surf.blit(pygame.transform.scale(T_[gid - 1], (TILE, 26)), (x + i * TILE, y - 26))
        for (x, y, w) in self.spike_runs_ceil:
            n = max(1, w // TILE)
            for i in range(n):
                gid = 12 if i == 0 else (14 if i == n - 1 else 13)
                sp = pygame.transform.flip(pygame.transform.scale(T_[gid - 1], (TILE, 26)),
                                           False, True)
                surf.blit(sp, (x + i * TILE, y))
        self.terrain_surf = surf
        self._build_terrain_shadow()

    def _build_terrain_shadow(self):
        """Soft dark silhouette drawn offset behind the terrain: separates the
        playable layer from the painted backdrop."""
        self.terrain_shadow = None
        if self.terrain_surf is None:
            return
        try:
            mask = pygame.mask.from_surface(self.terrain_surf, 60)
            self.terrain_shadow = mask.to_surface(setcolor=(4, 4, 10, 120),
                                                  unsetcolor=(0, 0, 0, 0))
        except (pygame.error, TypeError, AttributeError):
            self.terrain_shadow = None

    def _build_fallback_terrain(self):
        """Procedural terrain used when no tileset exists: ground, ledges, spikes."""
        th = self.theme
        surf = pygame.Surface((self.level_width, self.level_height), pygame.SRCALPHA)
        cells = set()
        for rct in self.platforms:
            for cc in range(rct.x // TILE, (rct.x + rct.w) // TILE):
                cells.add((cc, rct.y // TILE))
        for (c, r) in cells:
            depth = 0
            while depth < 6 and (c, r - 1 - depth) in cells:
                depth += 1
            col = blend_color(th["ground_top"], th["ground_bottom"], depth / 6.0)
            x, y = c * TILE, r * TILE
            pygame.draw.rect(surf, col, (x, y, TILE, TILE))
            pygame.draw.rect(surf, blend_color(col, (0, 0, 0), 0.2), (x, y, TILE, TILE), 1)
            if depth == 0:
                pygame.draw.rect(surf, th["accent"], (x, y, TILE, 5))
                pygame.draw.rect(surf, blend_color(th["accent"], WHITE, 0.45), (x, y, TILE, 2))
        wood, wood_d = (176, 138, 100), (96, 66, 42)
        for ow in self.one_way:
            pygame.draw.rect(surf, wood, ow, border_radius=3)
            for px in range(ow.x + 10, ow.right - 4, 20):
                pygame.draw.line(surf, wood_d, (px, ow.y + 3), (px, ow.bottom - 3), 1)
            pygame.draw.rect(surf, th["accent"], (ow.x, ow.y, ow.w, 4), border_radius=2)
            pygame.draw.rect(surf, wood_d, ow, 2, border_radius=3)
        steel, steel_d = (214, 222, 238), (110, 122, 148)
        for (x, y, w) in self.spike_runs_floor:
            n = max(1, w // TILE) * 3
            step = w / n
            for i in range(n):
                a = x + i * step
                pts = [(a + 1, y), (a + step - 1, y), (a + step / 2, y - 24)]
                pygame.draw.polygon(surf, steel, pts)
                pygame.draw.polygon(surf, steel_d, pts, 2)
        for (x, y, w) in self.spike_runs_ceil:
            n = max(1, w // TILE) * 3
            step = w / n
            for i in range(n):
                a = x + i * step
                pts = [(a + 1, y), (a + step - 1, y), (a + step / 2, y + 24)]
                pygame.draw.polygon(surf, steel, pts)
                pygame.draw.polygon(surf, steel_d, pts, 2)
        self.terrain_surf = surf

    def _build_decor(self):
        self.decor_draw, self.crate_solids, self.bridge_one_way = [], [], []
        for dec in DECORATIONS.get(self.level_index, []):
            t = dec["type"]
            wt, ht = DECOR_SIZES.get(t, (1, 1))
            wt, ht = dec.get("width", wt), dec.get("height", ht)
            x = dec["col"] * TILE
            pw, ph = wt * TILE, ht * TILE
            if t == "waterfall":
                y = (dec["row"] + SKY_ROWS) * TILE
            else:
                y = (dec["row"] + SKY_ROWS) * TILE - ph
            if t == "waterfall":
                # Pour all the way down to the first surface under it.
                below = [s.top for s in self.platforms + self.one_way
                         if s.left < x + pw and x < s.right and s.top > y + TILE]
                ph = max(2 * TILE, (min(below) if below else self.level_height) - y)
            if t == "crate":
                self.crate_solids.append(pygame.Rect(x, y, pw, ph))
            elif t == "rope_bridge":
                y = (dec["row"] + SKY_ROWS) * TILE
                self.bridge_one_way.append(pygame.Rect(x, y, pw, 12))
            self.decor_draw.append({"type": t, "x": x, "y": y, "w": pw, "h": ph})

    def begin_level(self, level_index):
        self.level_index = int(clamp(level_index, 0, len(LEVEL_LAYOUTS) - 1))
        self.theme = LEVEL_THEMES[self.level_index]
        self.bg_base = self.make_background()
        d = load_level(LEVEL_LAYOUTS[self.level_index], MOVER_ROUTES.get(self.level_index, {}))
        if d["unknown"]:
            leftover = sorted({ch for ch, _r, _c in d["unknown"]})
            print(f"[game] WARNING level {self.level_index + 1} has unknown tiles {leftover} "
                  f"({len(d['unknown'])} cells ignored) — run validate_levels.py")
        self.level_data = d
        self.level_width, self.level_height = d["width"], d["height"]
        self.platforms = d["platforms"]
        self.one_way = d["one_way"]
        self.water = d["water"]
        self.spikes_floor, self.spikes_ceiling = d["spikes_floor"], d["spikes_ceil"]
        self.spike_runs_floor, self.spike_runs_ceil = d["spike_runs_floor"], d["spike_runs_ceil"]
        self.checkpoints = d["checkpoints"]
        self.movers = d["movers"]
        self.goal_rect = d["goal"]
        self.last_checkpoint = None
        self._build_decor()
        self.one_way += self.bridge_one_way
        self.bg_art = self._load_bg_art(self.level_index)
        self._build_sky()
        if self.bg_art:
            self.bg_par = clamp((self.bg_art.get_width() - WIDTH) / max(1, self.level_width - WIDTH),
                                0.05, 0.5)
            self.bg_par_y = clamp((self.bg_art.get_height() - HEIGHT)
                                  / max(1, self.level_height - HEIGHT), 0.0, 0.35)
        else:
            self.bg_par, self.bg_par_y = 0.2, 0.0
        self._build_terrain()
        self.player = Player(self.character)
        sx, gy = d["start"]
        self.player.x = float(sx - self.player.w // 2)
        self.player.y = float(gy - self.player.h)
        self.player.sync_rect()
        self.last_safe = (self.player.x, self.player.y)
        self.snap_camera()
        self.stats["lives"] = self.stats["max_lives"]
        self.quiz = None
        self.gate_hint = None
        self.quiz_deck = make_question_deck(MOVER_QUESTIONS[self.level_index % len(MOVER_QUESTIONS)])
        self.particles.clear()
        self.popups.clear()
        self.banner_timer = 230.0
        self.look = 0.0
        self.scene_fade = 160.0
        self.accumulator = 0.0
        self.shake = 0.0

    def snap_camera(self):
        self.camera_x = clamp(self.player.rect.centerx - WIDTH // 2, 0,
                              max(0, self.level_width - WIDTH))
        self.camera_y = clamp(self.player.rect.centery - HEIGHT // 2, 0,
                              max(0, self.level_height - HEIGHT))

    def update_camera(self):
        if abs(self.player.vx) > 0.5:
            self.look = lerp(self.look, self.player.facing * 70.0, 0.03)
        tx = clamp(self.player.rect.centerx - WIDTH // 2 + self.look, 0,
                   max(0, self.level_width - WIDTH))
        ty = clamp(self.player.rect.centery - HEIGHT // 2 - 30, 0,
                   max(0, self.level_height - HEIGHT))
        self.camera_x = lerp(self.camera_x, tx, 0.14)
        self.camera_y = lerp(self.camera_y, ty, 0.14)

    # ── damage / respawn ─────────────────────────────────────────
    def _lose_heart(self):
        self.stats["hits"] += 1
        self.stats["lives"] -= 1
        if self.stats["lives"] <= 0:
            self.stats["lives"] = 0
            self.try_again_timer = TRY_AGAIN_FRAMES
            self.change_scene("TRY_AGAIN")
            return False
        return True

    def _spike_hit(self):
        """Spikes: knockback + i-frames, no teleport."""
        p = self.player
        if p.invincible_timer > 0:
            return
        self.audio.play("hurt")
        if not self._lose_heart():
            return
        p.vx = -p.facing * KNOCKBACK_X
        p.vel_y = KNOCKBACK_Y
        p.on_ground = False
        p.on_one_way = False
        p.carried_by = None
        p.gliding = False
        p.jump_cut_ready = False
        p.hurt_timer = float(HURT_FRAMES)
        p.invincible_timer = float(INVULN_FRAMES + p.invuln_bonus)
        self.shake = 10.0
        self.add_popup("SPIKED", p.rect.centerx, p.rect.y - 40, CORAL)

    def _fall_out(self, label):
        """Pits and water always respawn, even during invincibility."""
        p = self.player
        self.audio.play("wrong")
        if not self._lose_heart():
            return
        if self.last_checkpoint:
            gx, gy = self.last_checkpoint["x"], self.last_checkpoint["ground_y"]
        elif self.last_safe:
            p.x, p.y = self.last_safe
            gx = None
        else:
            gx, gy = self.level_data["start"]
        if gx is not None:
            p.x = float(gx - p.w // 2)
            p.y = float(gy - p.h)
        p.vx = p.vel_y = 0.0
        p.carried_by = None
        p.on_ground = False
        p.on_one_way = False
        p.gliding = False
        p.glide_fuel = GLIDE_FRAMES
        p.jump_buffer = 0.0
        p.coyote_timer = 0.0
        p.jump_cut_ready = False
        p.drop_timer = 0
        p.hurt_timer = float(HURT_FRAMES)
        p.invincible_timer = float(INVULN_FRAMES + p.invuln_bonus)
        p.sync_rect()
        p.reset_scarf()
        self.snap_camera()
        self.shake = 8.0
        self.add_popup(label, p.rect.centerx, p.rect.y - 40, CORAL)

    # ── physics (one fixed 60 Hz step) ───────────────────────────
    def _move_x(self, amount, solids, ignore=None):
        """Move horizontally and resolve. Returns True if blocked.
        A grounded player steps up onto a mover's 14 px lip instead of
        bumping into it like a wall."""
        p = self.player
        if not amount:
            return False
        p.x += amount
        p.sync_rect()
        blocked = False
        mover_ids = {id(m.rect) for m in self.movers}
        for s in solids:
            if s is ignore:
                continue
            if p.rect.colliderect(s):
                if (id(s) in mover_ids and p.on_ground
                        and 0 < p.rect.bottom - s.top <= 16):
                    old_y = p.rect.y
                    p.rect.bottom = s.top
                    if not any(p.rect.colliderect(o) for o in self.platforms
                               + self.crate_solids):
                        p.y = float(p.rect.y)
                        continue
                    p.rect.y = old_y
                if amount > 0:
                    p.rect.right = s.left
                else:
                    p.rect.left = s.right
                p.x = float(p.rect.x)
                blocked = True
        return blocked

    def update_player(self):
        p = self.player
        keys = pygame.key.get_pressed()
        p.invincible_timer = max(0.0, p.invincible_timer - 1.0)
        p.hurt_timer = max(0.0, p.hurt_timer - 1.0)
        p.drop_timer = max(0, p.drop_timer - 1)

        move = ((keys[pygame.K_d] or keys[pygame.K_RIGHT])
                - (keys[pygame.K_a] or keys[pygame.K_LEFT]))
        if move:
            p.facing = move
            acc = (ACCEL_GROUND if p.on_ground else ACCEL_AIR) * p.accel_mul
            p.vx = clamp(p.vx + move * acc, -p.max_speed, p.max_speed)
        else:
            p.vx *= FRICTION_GROUND if p.on_ground else FRICTION_AIR
            if abs(p.vx) < 0.08:
                p.vx = 0.0

        static = self.platforms + self.crate_solids
        mover_rects = [m.rect for m in self.movers]
        solids = static + mover_rects

        # Carry only while actually standing on that mover.
        if p.carried_by is not None:
            if not p.on_ground:
                p.carried_by = None
            else:
                dx = p.carried_by.last_dx
                if dx:
                    before = p.x
                    if self._move_x(dx, solids, ignore=p.carried_by.rect):
                        p.x = before          # never pushed into a wall
                        p.sync_rect()
                dy = p.carried_by.last_dy     # lifts and diagonal skiffs
                if dy:
                    p.y += dy
                    p.sync_rect()
                    if dy < 0 and any(p.rect.colliderect(s) for s in static):
                        p.y -= dy             # head would clip a ceiling: let it pass
                        p.sync_rect()

        if self._move_x(p.vx, solids):
            p.vx = 0.0
        p.x = clamp(p.x, 0.0, float(max(0, self.level_width - p.w)))
        p.sync_rect()

        p.walking = abs(p.vx) > 0.35
        if p.walking:
            p.anim += abs(p.vx) / MOVE_SPEED
            if self.settings["particles"] and p.on_ground and self._step_count % 10 == 0:
                self.particles.append(Particle(p.rect.centerx, p.rect.bottom,
                                               (255, 190, 220), dust=True))

        was_ground = p.on_ground
        if p.jump_buffer > 0:
            p.jump_buffer = max(0.0, p.jump_buffer - 1.0)
            if p.on_ground or p.coyote_timer > 0:
                p.execute_jump(self.particles, self.audio)

        prev_bottom = p.rect.bottom
        jump_held = any(keys[k] for k in JUMP_KEYS)
        if not jump_held:
            p.cut_jump()

        p.gliding = (p.can_glide and not p.on_ground and p.vel_y > 1.0
                     and jump_held and p.glide_fuel > 0)
        if p.gliding:
            p.glide_fuel -= 1
        grav = GRAVITY * (GLIDE_GRAVITY_MUL if p.gliding else 1.0)
        max_fall = MAX_FALL_SPEED * (GLIDE_FALL_MUL if p.gliding else 1.0)
        p.vel_y = min(p.vel_y + grav, max_fall)
        p.y += p.vel_y
        p.sync_rect()

        if p.rect.top > self.level_height + 60:
            self._fall_out("FELL")
            return
        for w in self.water:
            if p.rect.colliderect(w):
                self._fall_out("DROWNED")
                return
        for s in self.spikes_floor + self.spikes_ceiling:
            if p.rect.colliderect(s):
                self._spike_hit()
                break

        p.on_ground = False
        p.on_one_way = False
        p.carried_by = None
        landed = False
        land_top = None
        for s in solids:
            if p.rect.colliderect(s):
                if p.vel_y >= 0 and prev_bottom <= s.top + 14:
                    # several candidates (mover resting on a ledge): take the higher
                    if land_top is None or s.top < land_top:
                        land_top = s.top
                elif p.vel_y < 0 and p.rect.top >= s.bottom - 14:
                    p.rect.top = s.bottom
                    p.y = float(p.rect.y)
                    p.vel_y = 0.0
                    p.jump_cut_ready = False
        if land_top is not None:
            p.rect.bottom = land_top
            p.y = float(p.rect.y)
            landed = True
        if not landed and p.drop_timer == 0:
            for ow in self.one_way:
                if p.vel_y >= 0 and prev_bottom <= ow.top + 10 and p.rect.colliderect(ow):
                    p.rect.bottom = ow.top
                    p.y = float(p.rect.y)
                    landed = True
                    p.on_one_way = True
                    break

        if landed:
            for m in self.movers:
                if p.rect.colliderect(m.rect.inflate(0, 6)) and p.rect.bottom <= m.rect.top + 6:
                    p.carried_by = m
                    break
            if not was_ground and p.vel_y > 3.5:
                p.land_squash = 1.0
                self.audio.play("land")
                if self.settings["particles"]:
                    self.particles.append(Particle(p.rect.centerx, p.rect.bottom,
                                                   (255, 200, 226), ring=True))
            p.vel_y = 0.0
            p.on_ground = True
            p.gliding = False
            p.glide_fuel = GLIDE_FRAMES
            p.coyote_timer = float(p.coyote_max)
            p.jump_cut_ready = False
            if p.jump_buffer > 0:
                p.execute_jump(self.particles, self.audio)
        else:
            p.coyote_timer = max(0.0, p.coyote_timer - 1.0)

        p.land_squash = max(0.0, p.land_squash - 0.14)
        p.update_scarf()

        if (p.on_ground and p.carried_by is None and p.invincible_timer <= 0
                and self._step_count % SAFE_GROUND_EVERY == 0):
            probe = p.rect.inflate(10, 8)
            if not any(probe.colliderect(h) for h in
                       self.spikes_floor + self.spikes_ceiling + self.water):
                self.last_safe = (p.x, p.y)

    def update_gameplay(self):
        """Exactly one 60 Hz physics step."""
        self._step_count += 1
        self.stats["time"] += PHYSICS_DT
        self.banner_timer = max(0.0, self.banner_timer - 1.0)
        p = self.player
        for m in self.movers:
            m.update()
            # Never crush: a mover that would push into a player who isn't
            # standing on top of it simply waits (like a safe elevator).
            if (p is not None and p.carried_by is not m and m.rect.colliderect(p.rect)
                    and p.rect.bottom > m.rect.top + 14):
                m.undo()
        self.update_player()
        if self.scene != "PLAYING":
            return
        self.gate_hint = self._find_gate()
        self.update_camera()
        pr = self.player.rect.inflate(-6, -6)
        for cp in self.checkpoints:
            if not cp["active"] and pr.collidepoint(cp["x"], cp["ground_y"] - 26):
                cp["active"] = True
                self.last_checkpoint = cp
                self.add_popup("CHECKPOINT", cp["x"], cp["ground_y"] - 70, MINT)
                self.audio.play("check")
        if self.goal_rect and self.player.rect.colliderect(self.goal_rect):
            self.add_popup("TRIAL COMPLETE", self.player.rect.centerx,
                           self.player.rect.y - 60, MINT)
            self.add_particle_burst(self.goal_rect.centerx, self.goal_rect.centery, GOLD, 45, 5.2)
            self.audio.play("level")
            self.clear_timer = 75.0
            self.scene = "LEVEL_CLEAR"       # short victory beat before the next level
            self.accumulator = 0.0
            return
        self._update_fx()

    # ── question gates ───────────────────────────────────────────
    def _gate_zone(self, m):
        """Standing on a locked mover, or right beside it, offers the question."""
        h = self.player.h if self.player else 52
        return pygame.Rect(m.rect.x - 30, m.rect.y - h - 12, m.rect.w + 60, h + 30)

    def _find_gate(self):
        p = self.player
        if p is None or not p.on_ground:
            return None
        for m in self.movers:
            if m.locked and p.rect.colliderect(self._gate_zone(m)):
                return m
        return None

    def gate_counts(self):
        gated = [m for m in self.movers if not getattr(m, "_legacy", False)]
        return sum(1 for m in gated if not m.locked), len(gated)

    def _next_question(self):
        if not self.quiz_deck:
            self.quiz_deck = make_question_deck(
                MOVER_QUESTIONS[self.level_index % len(MOVER_QUESTIONS)])
        return self.quiz_deck.pop()

    def open_quiz(self, mover):
        # The same question waits on the platform until it is answered, so
        # backing out with ESC can't be used to re-roll an easier one.
        if mover.pending_question is None:
            mover.pending_question = self._next_question()
        self.player.vx = 0.0
        self.quiz = {"mover": mover, "q": mover.pending_question, "sel": 0,
                     "state": "ask", "picked": None}
        self.change_scene("QUIZ")

    def answer_quiz(self, idx):
        qz = self.quiz
        if not qz or qz["state"] != "ask" or not 0 <= idx < len(qz["q"]["options"]):
            return
        qz["picked"] = idx
        qz["mover"].pending_question = None
        self.stats["answered"] += 1
        if idx == qz["q"]["answer"]:
            qz["state"] = "right"
            self.stats["correct"] += 1
            self.audio.play("check")
        else:
            qz["state"] = "wrong"
            self.audio.play("wrong")

    def close_quiz(self):
        qz, self.quiz = self.quiz, None
        self.change_scene("PLAYING")
        if not qz or qz["state"] == "ask":
            return                                   # backed out: no penalty
        m, p = qz["mover"], self.player
        if qz["state"] == "right":
            m.activate()
            self.add_popup("GATE OPEN", m.rect.centerx, m.rect.y - 74, MINT)
            self.add_particle_burst(m.rect.centerx, m.rect.y, self.theme["accent"], 34, 4.2)
            self.audio.play("level")
        else:
            self.audio.play("hurt")
            if self._lose_heart():
                p.hurt_timer = float(HURT_FRAMES)
                self.shake = 7.0
                self.add_popup("WRONG  -1 HEART", p.rect.centerx, p.rect.y - 40, CORAL)

    def _update_fx(self):
        for pt in self.particles:
            pt.update()
        self.particles[:] = [pt for pt in self.particles if pt.life > 0]
        for pp in self.popups:
            pp.update()
        self.popups[:] = [pp for pp in self.popups if pp.life > 0]
        self.shake = max(0.0, self.shake - 1.0)

    def _finish_run(self):
        t = self.stats["time"]
        self.new_record = self.best_time is None or t < self.best_time
        if self.new_record:
            self.best_time = t
        self._save()
        self.change_scene("VICTORY")

    def add_particle_burst(self, x, y, color, count=20, power=4.0):
        if self.settings["particles"]:
            self.particles.extend(Particle(x, y, color, power=power) for _ in range(count))

    def add_popup(self, text, x, y, color=GOLD):
        self.popups.append(FloatingText(text, x, y, color))

    def change_scene(self, scene):
        self.scene, self.scene_fade, self.buttons = scene, 160.0, []
        self.pause_index = 0
        self.accumulator = 0.0
        if self.player:
            self.player.jump_buffer = 0.0
            self.player.cut_jump()
        if scene == "CHARACTER_SELECT":
            self.select.intro = 0.0
            self.select.pulse = 1.0
        self.audio.play("click")

    # ── decor drawing ────────────────────────────────────────────
    def _decor_art(self, world, t, x, y, w, h):
        wood, wood_d = (139, 100, 66), (96, 66, 42)
        stone, stone_d = (150, 132, 168), (108, 92, 128)
        blossom, blossom_d = (255, 176, 214), (232, 120, 176)
        red, red_d = (214, 66, 92), (176, 48, 74)
        if t == "sign":
            pygame.draw.rect(world, wood_d, (x + w // 2 - 3, y + h * 0.3, 6, h * 0.7))
            board = pygame.Rect(x - w * 0.1, y + h * 0.08, w * 1.2, h * 0.34)
            pygame.draw.rect(world, wood, board, border_radius=3)
            pygame.draw.rect(world, wood_d, board, 2, border_radius=3)
        elif t == "fence":
            n = max(2, w // 40)
            for i in range(n + 1):
                px = x + i * (w // n)
                pygame.draw.rect(world, wood, (px - 3, y + h * 0.15, 6, h * 0.85))
            pygame.draw.rect(world, wood, (x, y + h * 0.3, w, 4))
            pygame.draw.rect(world, wood, (x, y + h * 0.62, w, 4))
        elif t == "shrine":
            pygame.draw.rect(world, wood, (x + w * 0.22, y + h * 0.45, w * 0.56, h * 0.55 - 8))
            pygame.draw.rect(world, (255, 214, 150), (x + w * 0.42, y + h * 0.6, w * 0.16, h * 0.4 - 8))
            pygame.draw.polygon(world, (70, 44, 86),
                                [(x, y + h * 0.48), (x + w, y + h * 0.48),
                                 (x + w * 0.82, y + h * 0.2), (x + w * 0.18, y + h * 0.2)])
        elif t == "stone_lantern":
            cx = x + w // 2
            pygame.draw.rect(world, stone, (cx - w * 0.35, y + h - 6, w * 0.7, 6))
            pygame.draw.rect(world, stone, (cx - 3, y + h * 0.55, 6, h * 0.45 - 6))
            pygame.draw.rect(world, (255, 220, 150), (cx - w * 0.18, y + h * 0.26, w * 0.36, h * 0.16))
            pygame.draw.polygon(world, stone_d, [(cx - w * 0.42, y + h * 0.26),
                                                 (cx + w * 0.42, y + h * 0.26), (cx, y + h * 0.06)])
        elif t == "hanging_lantern":
            pygame.draw.rect(world, wood, (x + 4, y + h * 0.3, 6, h * 0.7))
            pygame.draw.rect(world, wood, (x + 4, y + h * 0.3, w - 8, 5))
            pygame.draw.rect(world, (255, 214, 140), (x + w - 19, y + h * 0.45, 14, h * 0.3),
                             border_radius=4)
        elif t == "banner":
            pygame.draw.rect(world, wood_d, (x + w // 2 - 2, y, 4, h))
            pygame.draw.polygon(world, (196, 62, 132),
                                [(x + w // 2 + 2, y + 6), (x + w // 2 + w * 0.8, y + 6),
                                 (x + w // 2 + w * 0.8, y + h * 0.8),
                                 (x + w // 2 + w * 0.4, y + h * 0.92), (x + w // 2 + 2, y + h * 0.8)])
        elif t == "tree":
            cx = x + w // 2
            pygame.draw.line(world, (90, 60, 50), (cx, y + h), (cx - w * 0.06, y + h * 0.45),
                             max(4, w // 14))
            rng = random.Random(int(x))
            for ox, oy, rr in ((-0.28, 0.3, 0.2), (-0.1, 0.16, 0.24), (0.12, 0.22, 0.22),
                               (0.28, 0.34, 0.17), (0.0, 0.34, 0.2)):
                c = blossom if rng.random() < 0.5 else blossom_d
                pygame.draw.circle(world, c, (int(cx + ox * w), int(y + oy * h)),
                                   max(6, int(rr * w)))
        elif t == "bush":
            rng = random.Random(int(x) + 3)
            for ox, rr in ((0.25, 0.28), (0.5, 0.34), (0.75, 0.26)):
                pygame.draw.circle(world, blossom_d if rng.random() < 0.5 else blossom,
                                   (int(x + ox * w), int(y + h - rr * h * 1.2)),
                                   max(5, int(rr * h * 1.6)))
        elif t == "crate":
            pygame.draw.rect(world, wood, (x, y, w, h), border_radius=3)
            pygame.draw.rect(world, wood_d, (x, y, w, h), 2, border_radius=3)
            pygame.draw.line(world, wood_d, (x, y), (x + w, y + h), 2)
        elif t == "rope_bridge":
            pygame.draw.rect(world, wood_d, (x, y - 14, 6, 26))
            pygame.draw.rect(world, wood_d, (x + w - 6, y - 14, 6, 26))
            for i in range(11):
                tt = (i + 0.5) / 11.0
                pygame.draw.rect(world, (176, 138, 100),
                                 (int(x + w * tt), int(y - 2 + math.sin(math.pi * tt) * 4),
                                  max(4, w // 14), 5))
        elif t == "waterfall":
            world.blit(_plain_surface(w, h, (186, 202, 244, 110)), (x, y))
        elif t == "torii":
            pygame.draw.rect(world, red, (x + w * 0.14, y + h * 0.18, w * 0.1, h * 0.82))
            pygame.draw.rect(world, red, (x + w * 0.76, y + h * 0.18, w * 0.1, h * 0.82))
            pygame.draw.polygon(world, red_d, [(x, y + h * 0.16), (x + w, y + h * 0.16),
                                               (x + w * 0.94, y + h * 0.06),
                                               (x + w * 0.06, y + h * 0.06)])
            pygame.draw.rect(world, red, (x + w * 0.12, y + h * 0.34, w * 0.76, h * 0.07))
        else:
            pygame.draw.rect(world, stone, (x, y, w, h), border_radius=4)

    def _sprite_box(self, t, pw, ph):
        """Where _decor_surf puts the scaled sprite inside its box: (ox, oy, w, h)."""
        base = self.decor_sprites.get(t)
        if base is None:
            return 0, 0, pw, ph
        bw, bh = base.get_size()
        s = min(pw / max(1, bw), ph / max(1, bh))
        nw, nh = max(1, int(round(bw * s))), max(1, int(round(bh * s)))
        return (pw - nw) // 2, ph - nh, nw, nh

    def _draw_decor_item(self, world, d, cx, cy):
        x, y = d["x"] - cx, d["y"] - cy
        if d["type"] == "waterfall":
            if not (x + d["w"] < -40 or x > WIDTH + 40 or y + d["h"] < -40 or y > HEIGHT + 40):
                self._draw_waterfall(world, d, int(x), int(y))
            return
        if x + d["w"] < -60 or x > WIDTH + 60 or y + d["h"] < -60 or y > HEIGHT + 60:
            return
        surf = self._decor_surf(d["type"], d["w"], d["h"])
        if surf is not None:
            world.blit(surf, (int(x), int(y)))
        else:
            self._decor_art(world, d["type"], int(x), int(y), d["w"], d["h"])
        if d["type"] in LAMP_SPOTS:
            self._draw_lamp_light(world, d, x, y)

    # ── lamps: warm layered glow, flicker, ground pool, rising embers ──
    def _draw_lamp_light(self, world, d, x, y):
        ox, oy, sw, sh = self._sprite_box(d["type"], d["w"], d["h"])
        seed = d["x"] * 0.37 + d["y"] * 0.11
        f = self.frame
        flick = (0.80 + 0.12 * math.sin(f * 0.19 + seed)
                 + 0.08 * math.sin(f * 0.53 + seed * 2.3))
        q = lambda a: int(a * flick) // 4 * 4          # quantised: keeps glow cache small
        if d["type"] in LAMP_POOL:
            pool = _MENU_CACHE.get(("pool",))
            if pool is None:
                pool = pygame.Surface((96, 22), pygame.SRCALPHA)
                for i in range(6):
                    k = i / 6
                    pygame.draw.ellipse(pool, (*WARM, int(10 + 12 * k)),
                                        (int(48 * k), int(11 * k), int(96 - 96 * k), int(22 - 22 * k)))
                _MENU_CACHE[("pool",)] = pool
            pool = pool.copy()
            pool.set_alpha(int(255 * flick))
            world.blit(pool, (int(x + d["w"] / 2 - 48), int(y + d["h"] - 12)))
        for fx, fy in LAMP_SPOTS[d["type"]]:
            gx = int(x + ox + sw * fx)
            gy = int(y + oy + sh * fy)
            world.blit(get_radial_glow(54, WARM, q(34), 6), (gx - 54, gy - 54))
            world.blit(get_radial_glow(18, WARM_CORE, q(110), 4), (gx - 18, gy - 18))
            # two embers drifting up out of each flame
            for k in range(2):
                life = ((f * 0.55 + seed * 40 + k * 47) % 70) / 70.0
                ex = gx + math.sin(f * 0.045 + seed + k * 2.1) * (3 + 6 * life)
                ey = gy - 6 - life * 46
                a = int(200 * (1.0 - life))
                if a > 8:
                    world.blit(_plain_surface(2, 2, (*WARM_CORE, a // 8 * 8)), (int(ex), int(ey)))

    # ── waterfall: animated sheet that falls to the surface below ──
    def _waterfall_body(self, w, h):
        key = ("wf", w, h, self.level_index)
        hit = self._decor_scaled.get(key)
        if hit is not None:
            return hit
        mote = self.theme["mote"]
        deep = blend_color((44, 78, 150), mote, 0.18)
        light = blend_color((128, 172, 226), mote, 0.22)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for xx in range(w):
            e = min(xx, w - 1 - xx) / max(1.0, w / 2)          # 0 at edges, 1 at centre
            col = blend_color(deep, light, min(1.0, e * 1.4))
            pygame.draw.line(s, (*col, int(105 + 85 * min(1.0, e * 2.5))), (xx, 0), (xx, h - 1))
        # fade in at the lip, darker at the edges
        for yy in range(min(10, h)):
            pygame.draw.line(s, (232, 244, 255, int(200 - yy * 18)), (0, yy), (w - 1, yy))
        pygame.draw.line(s, (*deep, 220), (0, 0), (0, h - 1), 2)
        pygame.draw.line(s, (*deep, 220), (w - 1, 0), (w - 1, h - 1), 2)
        self._decor_scaled[key] = s
        return s

    def _draw_waterfall(self, world, d, x, y):
        w, h, f = d["w"], d["h"], self.frame
        world.blit(self._waterfall_body(w, h), (x, y))
        # falling streaks in lanes, each at its own speed
        for i, lane in enumerate(range(5, w - 4, 7)):
            speed = 5.0 + (i * 37 % 5) * 0.8
            length = 14 + (i * 23 % 4) * 6
            for j in range(h // 70 + 2):
                yy = (f * speed + i * 53 + j * 70) % (h + length) - length
                top, bot = max(0, yy), min(h, yy + length)
                if bot - top > 2:
                    world.blit(_plain_surface(2, int(bot - top), (226, 238, 255, 105)),
                               (x + lane, int(y + top)))

    def _draw_waterfall_foam(self, world, d, cx, cy):
        """Drawn after the terrain so the splash sits on top of the surface."""
        x, y, w, h, f = d["x"] - cx, d["y"] - cy, d["w"], d["h"], self.frame
        bx, by = int(x + w / 2), int(y + h)
        if bx < -80 or bx > WIDTH + 80 or by < -40 or by > HEIGHT + 60:
            return
        world.blit(get_radial_glow(w, (200, 224, 255), 46, 4), (bx - w, by - w + 6))
        foam = pygame.Surface((w + 36, 30), pygame.SRCALPHA)
        n = max(3, w // 10 + 2)
        for k in range(n):
            fx = 18 + k * w / (n - 1)
            r = 6 + 3 * math.sin(f * 0.22 + k * 1.7)
            pygame.draw.circle(foam, (226, 238, 255, 190), (int(fx), 18), max(3, int(r)))
            pygame.draw.circle(foam, (255, 255, 255, 230), (int(fx), 16), max(2, int(r * 0.5)))
        world.blit(foam, (int(x) - 18, by - 22))
        for k in range(7):
            t = ((f * 0.022) + k / 7.0) % 1.0
            sx = bx + (k - 3) * (w / 5) * t * 1.6
            sy = by - 10 - 70 * t * (1 - t) * 1.2
            world.blit(_plain_surface(3, 3, (235, 244, 255, int(220 * (1 - t)) // 8 * 8)),
                       (int(sx), int(sy)))

    def _draw_mover(self, world, m, cx, cy):
        accent = self.theme["accent"]
        w, h = m.rect.w, m.rect.h
        if not getattr(m, "_legacy", False) and m.length > 0:
            # Route preview: dotted path plus a ghost outline of the far stop.
            ax, ay = m.ax + w / 2 - cx, m.ay + h / 2 - cy
            bx, by = m.bx + w / 2 - cx, m.by + h / 2 - cy
            n = max(2, int(m.length // 22))
            dot = (*accent, 70 if m.locked else 40)
            for i in range(1, n):
                k = i / n
                px, py = int(ax + (bx - ax) * k), int(ay + (by - ay) * k)
                if -10 < px < WIDTH + 10 and -10 < py < HEIGHT + 10:
                    world.blit(_plain_surface(4, 4, dot), (px - 2, py - 2))
            if m.locked:
                ghost = pygame.Rect(int(m.bx - cx), int(m.by - cy), w, h)
                pygame.draw.rect(world, blend_color(accent, (20, 20, 30), 0.45), ghost, 1,
                                 border_radius=4)
        rx, ry = int(m.rect.x - cx), int(m.rect.y - cy)
        if rx + w < -20 or rx > WIDTH + 20 or ry + h < -40 or ry > HEIGHT + 20:
            return
        if m.locked:
            pulse = 0.5 + 0.5 * math.sin(self.frame * 0.08 + m.ax * 0.01)
            world.blit(get_radial_glow(30, accent, int(16 + 24 * pulse), 4),
                       (rx + w // 2 - 30, ry + h // 2 - 30))
            pygame.draw.rect(world, (34, 30, 48), (rx - 2, ry - 2, w + 4, h + 6), border_radius=5)
            pygame.draw.rect(world, (78, 70, 102), (rx, ry, w, h), border_radius=4)
            pygame.draw.line(world, blend_color((120, 110, 150), accent, 0.4 * pulse),
                             (rx + 2, ry + 2), (rx + w - 2, ry + 2), 2)
            # rune plate with a "?" in the middle
            mx = rx + w // 2
            pygame.draw.circle(world, (24, 20, 36), (mx, ry + h // 2), 11)
            pygame.draw.circle(world, blend_color(accent, WHITE, 0.2 * pulse), (mx, ry + h // 2), 11, 2)
            draw_text(world, "?", fonts.SMALL, accent, (mx, ry + h // 2), center=True)
        else:
            if m.glow > 0:
                world.blit(get_radial_glow(48, accent, int(70 * m.glow), 4),
                           (rx + w // 2 - 48, ry + h // 2 - 48))
            pygame.draw.rect(world, (96, 66, 48), (rx - 2, ry - 2, w + 4, h + 6), border_radius=5)
            pygame.draw.rect(world, (176, 138, 100), (rx, ry, w, h), border_radius=4)
            pygame.draw.line(world, accent, (rx + 2, ry + 2), (rx + w - 2, ry + 2), 2)
            for gx in range(rx + 14, rx + w - 8, 26):
                pygame.draw.circle(world, blend_color(accent, WHITE, 0.3), (gx, ry + h // 2 + 1), 2)

    def _draw_gate_hint(self, world, m, cx, cy):
        bob = math.sin(self.frame * 0.1) * 3
        label = "E  ·  ANSWER TO START"
        img = get_text_image(label, fonts.TINY, WHITE)
        pill = pygame.Rect(0, 0, img.get_width() + 30, 28)
        pill.midbottom = (int(m.rect.centerx - cx), int(m.rect.y - cy - 66 + bob))
        pill.clamp_ip(pygame.Rect(8, 8, WIDTH - 16, HEIGHT - 16))
        draw_pill(world, pill, (16, 26, 42, 230), (*self.theme["accent"], 160), shadow=False)
        world.blit(img, img.get_rect(center=pill.center))

    # ── quiz panel ───────────────────────────────────────────────
    QUIZ_TOPICS = ("PYTHON BASICS", "CONTROL FLOW", "COLLECTIONS", "FUNCTIONS",
                   "STRINGS · ERRORS · CLASSES")
    _PY_KW = {"def", "return", "if", "else", "elif", "for", "while", "in", "and", "or",
              "not", "try", "except", "finally", "class", "lambda", "True", "False",
              "None", "import", "from", "as", "pass", "break", "continue"}
    _PY_FN = {"print", "len", "int", "str", "float", "range", "list", "set", "dict",
              "type", "tuple", "upper", "split", "append", "get"}

    def _code_tokens(self, line):
        """Tiny Python highlighter: yields (text, colour)."""
        import re
        out = []
        for m in re.finditer(r'(#.*$)|(f?"[^"]*"|f?\'[^\']*\')|(\b\d+(?:\.\d+)?\b)'
                             r'|([A-Za-z_]\w*)|(\s+)|(.)', line):
            com, st, num, word, sp, op = m.groups()
            if com:
                out.append((com, (110, 128, 150)))
            elif st:
                out.append((st, (152, 220, 140)))
            elif num:
                out.append((num, (246, 180, 110)))
            elif word:
                col = ((206, 150, 255) if word in self._PY_KW else
                       (110, 196, 250) if word in self._PY_FN else (226, 232, 242))
                out.append((word, col))
            else:
                out.append((sp or op, (190, 200, 214)))
        return out

    def _draw_code_box(self, cv, rect, lines, accent):
        font = fonts.CODE_FONT
        lh = font.get_linesize() + 3
        pygame.draw.rect(cv, (6, 10, 19), rect, border_radius=12)
        bar = pygame.Rect(rect.x, rect.y, rect.w, 26)
        pygame.draw.rect(cv, (18, 26, 40), bar, border_top_left_radius=12,
                         border_top_right_radius=12)
        for i, c in enumerate(((242, 98, 112), (246, 196, 92), (86, 214, 166))):
            pygame.draw.circle(cv, c, (bar.x + 18 + i * 16, bar.centery), 5)
        draw_text(cv, "gate.py", fonts.TINY, MUTED, (bar.centerx, bar.centery), center=True)
        pygame.draw.rect(cv, blend_color((60, 84, 112), accent, 0.25), rect, 1, border_radius=12)
        gutter = rect.x + 40
        pygame.draw.line(cv, (30, 42, 60), (gutter, bar.bottom + 4), (gutter, rect.bottom - 8), 1)
        y = bar.bottom + 10
        for n, ln in enumerate(lines, 1):
            draw_text(cv, str(n), font, (70, 88, 110), (gutter - 10, y + lh // 2 - 1), right=True)
            x = gutter + 14
            for tok, col in self._code_tokens(ln):
                img = get_text_image(tok, font, col)
                cv.blit(img, (x, y))
                x += img.get_width()
            y += lh

    def _draw_check(self, cv, center, color, ok):
        x, y = center
        pygame.draw.circle(cv, color, center, 11)
        if ok:
            pygame.draw.lines(cv, INK, False, [(x - 5, y), (x - 1, y + 4), (x + 6, y - 4)], 3)
        else:
            pygame.draw.line(cv, INK, (x - 4, y - 4), (x + 4, y + 4), 3)
            pygame.draw.line(cv, INK, (x + 4, y - 4), (x - 4, y + 4), 3)

    def _draw_option_card(self, cv, i, rect, text, state, qz, accent):
        """One answer card. Registers an invisible Button for mouse clicks."""
        key = f"quiz_opt{i}"
        b = self.button_cache.get(key)
        if not isinstance(b, Button):
            b = self.button_cache[key] = Button(key, rect, "", f"quiz_a{i}", accent)
        b.rect, b.action = pygame.Rect(rect), f"quiz_a{i}"
        b.update(self.mouse_pos, self.dt_scale, selected=(state == "ask" and i == qz["sel"]))
        self.buttons.append(b)
        q = qz["q"]
        hot = b.hover if state == "ask" else 0.0
        if state == "ask":
            edge = blend_color((70, 92, 120), accent, hot)
            fill = blend_color((20, 32, 50), blend_color((20, 32, 50), accent, 0.22), hot)
            badge, txt = blend_color((40, 56, 80), accent, hot), WHITE
        elif i == q["answer"]:
            edge, fill, badge, txt = MINT, (18, 52, 50), MINT, WHITE
        elif i == qz["picked"]:
            edge, fill, badge, txt = CORAL, (60, 24, 36), CORAL, WHITE
        else:
            edge, fill, badge, txt = (44, 56, 74), (16, 24, 38), (40, 50, 66), SUBTLE
        r = pygame.Rect(rect).move(0, -int(round(hot * 3)))
        if hot > 0.05:
            cv.blit(get_radial_glow(r.h, accent, int(30 * hot) // 4 * 4, 4),
                    (r.centerx - r.h, r.centery - r.h))
        pygame.draw.rect(cv, (4, 8, 16), r.move(0, 4), border_radius=14)
        pygame.draw.rect(cv, fill, r, border_radius=14)
        pygame.draw.rect(cv, edge, r, 2 if (hot > 0.3 or state != "ask") else 1, border_radius=14)
        bc = (r.x + 26, r.centery)
        if state != "ask" and i in (q["answer"], qz["picked"]):
            self._draw_check(cv, bc, badge, i == q["answer"])
        else:
            pygame.draw.circle(cv, badge, bc, 13)
            draw_text(cv, str(i + 1), fonts.SMALL, WHITE, bc, center=True)
        codey = any(ch in text for ch in "[]{}()'\"=_.") or text.isdigit()
        font = fonts.CODE_FONT if codey else fonts.BODY
        draw_text(cv, text, font, txt, (r.x + 50, r.centery), valign="middle")

    def draw_quiz(self):
        self.draw_game_world()
        qz = self.quiz
        if qz is None:
            return
        cv = config.canvas
        q, state = qz["q"], qz["state"]
        accent = self.theme["accent"]
        border = MINT if state == "right" else (CORAL if state == "wrong" else accent)
        if "t0" not in qz:
            qz["t0"] = self.frame
        e = clamp((self.frame - qz["t0"]) / 14.0, 0.0, 1.0)
        ease = 1.0 - (1.0 - e) ** 3
        cv.blit(veil(int(190 * ease)), (0, 0))

        code = q.get("code", "").split("\n") if q.get("code") else []
        qlines = wrap_text(q["q"], fonts.MED, 640)
        lh = fonts.CODE_FONT.get_linesize() + 3
        code_h = (len(code) * lh + 46) if code else 0
        body_h = 70 + len(qlines) * 32 + (code_h + 18 if code else 6) + 2 * 62 + 14
        why_lines = wrap_text(q["why"], fonts.BODY, 780 - 150)[:2]
        foot_h = (80 + 40 + 22 * len(why_lines)) if state != "ask" else 70
        ph = min(HEIGHT - 30, body_h + foot_h)
        pr = pygame.Rect(0, 0, 780, ph)
        pr.center = (WIDTH // 2, HEIGHT // 2 + int((1.0 - ease) * 40))

        cv.blit(get_radial_glow(340, border, 26, 6), (pr.centerx - 340, pr.centery - 340))
        panel(cv, pr, (12, 20, 34, 248), (*border, 150), 26, True)
        # header strip
        head = pygame.Rect(pr.x, pr.y, pr.w, 46)
        gradient_rect(cv, head, (*accent, 70), (*accent, 0), 26)
        opened, total = self.gate_counts()
        gated = [mm for mm in self.movers if not getattr(mm, "_legacy", False)]
        num = gated.index(qz["mover"]) + 1 if qz["mover"] in gated else opened + 1
        badge = pygame.Rect(pr.x + 22, pr.y + 12, 150, 26)
        draw_pill(cv, badge, (*blend_color(accent, INK, 0.55), 240), (*accent, 200), shadow=False)
        draw_text(cv, f"PYTHON GATE {num}/{total}", fonts.TINY, WHITE, badge.center, center=True)
        topic = self.QUIZ_TOPICS[self.level_index % len(self.QUIZ_TOPICS)]
        draw_text(cv, topic, fonts.TINY, blend_color(accent, WHITE, 0.45),
                  (badge.right + 14, badge.centery), valign="middle")
        for i in range(total):
            c = (pr.right - 30 - (total - 1 - i) * 20, badge.centery)
            if i < opened:
                pygame.draw.circle(cv, MINT, c, 6)
            elif gated[i] is qz["mover"]:
                pygame.draw.circle(cv, accent, c, 6)
                pygame.draw.circle(cv, WHITE, c, 6, 1)
            else:
                pygame.draw.circle(cv, SUBTLE, c, 6, 2)
        # lives
        hx = pr.right - 30 - total * 20 - 18
        for i in range(self.stats["lives"]):
            img = get_smooth_heart(14, CORAL, filled=True)
            cv.blit(img, img.get_rect(center=(hx - i * 18, badge.centery)))

        y = pr.y + 64
        for line in qlines:
            draw_text(cv, line, fonts.MED, WHITE, (WIDTH // 2, y + 12), center=True, shadow=True)
            y += 32
        if code:
            box = pygame.Rect(pr.x + 120, y + 6, pr.w - 240, code_h)
            self._draw_code_box(cv, box, code, accent)
            y = box.bottom + 18
        else:
            y += 10
        bw, bh, gap = 345, 50, 14
        x0 = WIDTH // 2 - bw - gap // 2
        for i, opt in enumerate(q["options"]):
            r = pygame.Rect(x0 + (i % 2) * (bw + gap), y + (i // 2) * (bh + 12), bw, bh)
            self._draw_option_card(cv, i, r, opt, state, qz, accent)
        y += 2 * (bh + 12) + 4

        if state == "ask":
            hints = (("1-4", "ANSWER"), ("ARROWS", "MOVE"), ("ENTER", "PICK"), ("ESC", "BACK"))
            total_w = sum(fonts.TINY.size(k)[0] + fonts.TINY.size(v)[0] + 40 for k, v in hints)
            hx = WIDTH // 2 - total_w // 2
            hy = pr.bottom - 30
            for k, v in hints:
                kw = fonts.TINY.size(k)[0] + 14
                cap = pygame.Rect(hx, hy - 11, kw, 22)
                pygame.draw.rect(cv, (30, 42, 60), cap.move(0, 2), border_radius=6)
                pygame.draw.rect(cv, (48, 64, 88), cap, border_radius=6)
                draw_text(cv, k, fonts.TINY, WHITE, cap.center, center=True)
                draw_text(cv, v, fonts.TINY, MUTED, (cap.right + 6, hy), valign="middle")
                hx = cap.right + 6 + fonts.TINY.size(v)[0] + 20
            draw_text(cv, "Right answer starts the platform  ·  wrong answer costs a heart",
                      fonts.TINY, SUBTLE, (WIDTH // 2, pr.bottom - 54), center=True)
        else:
            right = state == "right"
            col = MINT if right else CORAL
            box = pygame.Rect(pr.x + 40, y + 4, pr.w - 80, 40 + 22 * len(why_lines))
            pygame.draw.rect(cv, (*blend_color(col, (12, 20, 34), 0.82),), box, border_radius=14)
            pygame.draw.rect(cv, col, box, 1, border_radius=14)
            self._draw_check(cv, (box.x + 26, box.y + 20), col, right)
            head = "CORRECT!  THE PLATFORM AWAKENS" if right else "NOT QUITE  ·  YOU LOSE A HEART"
            draw_text(cv, head, fonts.SMALL, col, (box.x + 48, box.y + 20), valign="middle")
            for n, why in enumerate(why_lines):
                draw_text(cv, why, fonts.BODY, (214, 224, 236),
                          (box.x + 48, box.y + 44 + n * 22), valign="middle")
            self.make_button("quiz_continue", (WIDTH // 2 - 120, pr.bottom - 56, 240, 42),
                             "CONTINUE" if right else "GOT IT", "quiz_continue",
                             col, selected=True)

    def get_shadow_surface_y(self):
        cx = self.player.rect.centerx
        best = float(self.level_height)
        candidates = (self.platforms + self.one_way + self.crate_solids
                      + [m.rect for m in self.movers])
        for s in candidates:
            if s.left <= cx <= s.right and s.top >= self.player.rect.bottom - 4 and s.top < best:
                best = float(s.top)
        return best

    def draw_game_world(self):
        cx, cy = int(round(self.camera_x)), int(round(self.camera_y))
        world = config.world
        self.world_scenery(world, self.frame, cx, cy)
        for d in self.decor_draw:
            if d["type"] not in ("crate", "rope_bridge", "waterfall"):
                self._draw_decor_item(world, d, cx, cy)
        for d in self.decor_draw:
            if d["type"] == "waterfall":
                self._draw_decor_item(world, d, cx, cy)
        if self.terrain_shadow is not None:
            world.blit(self.terrain_shadow, (-cx + 5, -cy + 7))
        if self.terrain_surf is not None:
            world.blit(self.terrain_surf, (-cx, -cy))
        else:
            for p in self.platforms:
                rx, ry = p.x - cx, p.y - cy
                if rx + p.w < 0 or rx > WIDTH or ry + p.h < 0 or ry > HEIGHT:
                    continue
                gradient_rect(world, (int(rx), int(ry), p.w, p.h),
                              self.theme["ground_top"], self.theme["ground_bottom"])
                pygame.draw.rect(world, self.theme["accent"], (int(rx), int(ry), p.w, 5))
        for w in self.water:
            rx, ry = w.x - cx, w.y - cy
            if rx + w.w < 0 or rx > WIDTH:
                continue
            world.blit(_plain_surface(w.w, w.h, (86, 140, 205, 150)), (int(rx), int(ry) + 8))
            wave = int(math.sin(self.frame * 0.1 + w.x * 0.05) * 2)
            pygame.draw.line(world, (190, 224, 255), (int(rx), int(ry) + 8 + wave),
                             (int(rx + w.w), int(ry) + 8 + wave), 2)
        for m in self.movers:
            self._draw_mover(world, m, cx, cy)
        for d in self.decor_draw:
            if d["type"] in ("crate", "rope_bridge"):
                self._draw_decor_item(world, d, cx, cy)
            elif d["type"] == "waterfall":
                self._draw_waterfall_foam(world, d, cx, cy)
        for cp in self.checkpoints:
            x, y = int(cp["x"] - cx), int(cp["ground_y"] - cy)
            if x < -40 or x > WIDTH + 40:
                continue
            pygame.draw.line(world, (200, 200, 210), (x, y), (x, y - 46), 4)
            col = MINT if cp["active"] else SUBTLE
            pygame.draw.polygon(world, col, [(x + 2, y - 46),
                                             (x + 26, y - 39 + math.sin(self.frame * 0.1) * 2),
                                             (x + 2, y - 32)])
            if cp["active"]:
                world.blit(get_radial_glow(24, MINT, 40, 4), (x - 12, y - 60))
        if self.goal_rect:
            gx, gy = int(self.goal_rect.x - cx), int(self.goal_rect.y - cy)
            world.blit(get_radial_glow(46, GOLD, 42, 4), (gx - 26, gy - 40))
            pygame.draw.line(world, (214, 208, 226), (gx + 6, gy + self.goal_rect.h),
                             (gx + 6, gy - 46), 4)
            pygame.draw.circle(world, GOLD, (gx + 6, gy - 48), 4)
            wave = math.sin(self.frame * 0.12) * 4
            pygame.draw.polygon(world, CORAL, [(gx + 8, gy - 46), (gx + 46, gy - 36 + wave),
                                               (gx + 8, gy - 26)])
        if self.player:
            self.player.draw(world, self.frame, self.get_shadow_surface_y(), cx, cy)
        if self.gate_hint is not None and self.scene == "PLAYING":
            self._draw_gate_hint(world, self.gate_hint, cx, cy)
        for pt in self.particles:
            pt.draw(world, cx, cy)
        for pp in self.popups:
            pp.draw(world, cx, cy)
        config.canvas.blit(world, (0, 0))
        if self.shake > 0:       # scroll keeps the old pixels at the edges: no dark border
            i = max(1, int(self.shake / 3))
            config.canvas.scroll(random.randint(-i, i), random.randint(-i, i))
        self._draw_petals(config.canvas, cx)
        self.draw_hud()
        self._draw_banner()

    def _draw_banner(self):
        t = self.banner_timer
        if t <= 0:
            return
        a = clamp(min(t / 30.0, (230.0 - t) / 20.0), 0.0, 1.0)
        title = f"TRIAL {self.level_index + 1}  ·  {self.theme['name'].upper()}"
        for color, off in (((6, 10, 18), (2, 2)), (WHITE, (0, 0))):
            img = get_text_image(title, fonts.MED, color).copy()
            img.set_alpha(int(255 * a))
            config.canvas.blit(img, img.get_rect(center=(WIDTH // 2 + off[0], 122 + off[1])))
        sub = "Glowing  ?  platforms are locked: stand on one and press E to answer a Python question"
        for color, off in (((6, 10, 18), (1, 1)), (GOLD_SOFT, (0, 0))):
            img = get_text_image(sub, fonts.BODY, color).copy()
            img.set_alpha(int(235 * a))
            config.canvas.blit(img, img.get_rect(center=(WIDTH // 2 + off[0], 156 + off[1])))

    def draw_hud(self):
        n_hearts = self.stats.get("max_lives", MAX_HEARTS)
        hearts_pill = pygame.Rect(20, 18, 24 + n_hearts * 38, 46)
        draw_pill(config.canvas, hearts_pill)
        low = self.stats["lives"] == 1
        for i in range(n_hearts):
            active = i < self.stats["lives"]
            size = int(24 * ((1.0 + 0.14 * math.sin(self.frame * 0.22))
                             if (active and low) else 1.0))
            img = get_smooth_heart(size, CORAL if active else SUBTLE, filled=active)
            config.canvas.blit(img, img.get_rect(center=(hearts_pill.x + 31 + i * 38,
                                                         hearts_pill.centery)))
        prog = pygame.Rect(WIDTH - 252, 18, 232, 46)
        draw_pill(config.canvas, prog)
        draw_text(config.canvas, f"LEVEL {self.level_index + 1}/{len(LEVEL_LAYOUTS)}",
                  fonts.SMALL, self.theme["accent"], (prog.x + 22, prog.centery), valign="middle")
        draw_text(config.canvas, _fmt_time(self.stats["time"]), fonts.SMALL, WHITE,
                  (prog.right - 22, prog.centery), right=True)
        opened, total = self.gate_counts()
        if total:
            gp = pygame.Rect(WIDTH - 252, 72, 232, 34)
            draw_pill(config.canvas, gp, (16, 26, 42, 210), (*self.theme["accent"], 70), shadow=False)
            draw_text(config.canvas, "PYTHON GATES", fonts.TINY, MUTED,
                      (gp.x + 18, gp.centery), valign="middle")
            for i in range(total):
                c = (gp.right - 22 - (total - 1 - i) * 22, gp.centery)
                if i < opened:
                    pygame.draw.circle(config.canvas, MINT, c, 7)
                else:
                    pygame.draw.circle(config.canvas, SUBTLE, c, 7, 2)
        chip_label = f"{self.character['name']} · {self.character['short']}"
        chip = pygame.Rect(20, HEIGHT - 46, max(196, 84 + fonts.TINY.size(chip_label)[0]), 32)
        draw_pill(config.canvas, chip, (16, 26, 42, 210), (*self.character["accent"], 90),
                  shadow=False)
        if bank.has(self.character["id"]):
            bank.draw(config.canvas, self.character["id"], "idle",
                      int(self.frame * 0.07) % bank.count(self.character["id"], "idle"),
                      44, HEIGHT - 17, 26, facing=1)
        else:
            draw_fallback_hero(config.canvas, self.character, 44, HEIGHT - 17, 26, self.frame)
        draw_text(config.canvas, chip_label, fonts.TINY, WHITE, (64, chip.centery), valign="middle")

    # ── buttons / settings / pause / end ─────────────────────────
    def make_button(self, key, rect, label, action, accent=GOLD, selected=False):
        if key not in self.button_cache or isinstance(self.button_cache[key], dict):
            self.button_cache[key] = Button(key, rect, label, action, accent)
        b = self.button_cache[key]
        b.rect, b.label, b.action, b.accent = pygame.Rect(rect), label, action, accent
        b.update(self.mouse_pos, self.dt_scale, selected=selected)
        b.draw(config.canvas)
        self.buttons.append(b)
        return b

    def draw_slider(self, key, label, value, y):
        x, width = 350, 400
        draw_text(config.canvas, label, fonts.TINY, MUTED, (x, y - 22))
        draw_text(config.canvas, f"{int(round(value * 100))}%", fonts.TINY, GOLD_SOFT,
                  (x + width, y - 16), right=True)
        pygame.draw.rect(config.canvas, (36, 50, 70), (x, y, width, 8), border_radius=4)
        fill = int(width * value)
        if fill:
            pygame.draw.rect(config.canvas, MINT if key == "music" else BLUE,
                             (x, y, fill, 8), border_radius=4)
        pygame.draw.circle(config.canvas, WHITE, (x + fill, y + 4), 9)
        pygame.draw.circle(config.canvas, GOLD if self.slider_drag == key else SUBTLE,
                           (x + fill, y + 4), 9, 2)
        self.slider_rects[key] = pygame.Rect(x - 12, y - 14, width + 24, 34)

    def draw_settings(self):
        if self.settings_return == "MENU":
            bg = self._title_background()
            if bg is not None:
                config.canvas.blit(bg, (0, 0))
            else:
                self.world_scenery(config.canvas, self.frame)
            config.canvas.blit(veil(120), (0, 0))
        else:
            self.draw_game_world()
            config.canvas.blit(veil(150), (0, 0))
        panel(config.canvas, (240, 82, 620, 486), (15, 25, 40, 236), (130, 162, 190, 90), 26, True)
        draw_text(config.canvas, "SETTINGS", fonts.LARGE, WHITE, (WIDTH // 2, 134),
                  center=True, shadow=True)
        self.draw_slider("music", "MUSIC VOLUME", self.audio.music_volume, 236)
        self.draw_slider("sfx", "SOUND EFFECTS", self.audio.sfx_volume, 316)
        self.make_button("settings_fullscreen", (330, 388, 210, 46),
                         "FULLSCREEN: ON" if self.settings["fullscreen"] else "FULLSCREEN: OFF",
                         "fullscreen", BLUE)
        self.make_button("settings_particles", (560, 388, 210, 46),
                         "PARTICLES: ON" if self.settings["particles"] else "PARTICLES: OFF",
                         "particles", MINT)
        self.make_button("settings_back", (420, 476, 260, 46), "BACK", "back", GOLD)

    PAUSE_ACTIONS = ("resume", "restart", "settings", "menu")

    def draw_pause(self):
        self.draw_game_world()
        config.canvas.blit(veil(185), (0, 0))
        panel(config.canvas, (355, 130, 390, 400), (16, 27, 43, 245), (130, 162, 190, 100), 24, True)
        draw_text(config.canvas, "PAUSED", fonts.LARGE, WHITE, (WIDTH // 2, 184),
                  center=True, shadow=True)
        draw_text(config.canvas, f"{self.character['name']} — {self.character['title'].upper()}",
                  fonts.TINY, self.character["accent"], (WIDTH // 2, 216), center=True)
        rows = [("pause_resume", 236, "RESUME", "resume", MINT),
                ("pause_restart", 294, "RESTART", "restart", GOLD),
                ("pause_settings", 352, "SETTINGS", "settings", BLUE),
                ("pause_menu", 410, "MAIN MENU", "menu", CORAL)]
        for i, (key, y, label, action, accent) in enumerate(rows):
            self.make_button(key, (415, y, 270, 46), label, action, accent,
                             selected=(i == self.pause_index))
        draw_text(config.canvas, "ESC/P RESUME   R RESTART   S SETTINGS   M MENU",
                  fonts.TINY, MUTED, (WIDTH // 2, 484), center=True)
        draw_text(config.canvas, "↑ ↓ SELECT   ·   ENTER CONFIRM", fonts.TINY, SUBTLE,
                  (WIDTH // 2, 504), center=True)

    def draw_confirm_menu(self):
        self.draw_game_world()
        config.canvas.blit(veil(200), (0, 0))
        panel(config.canvas, (330, 210, 440, 230), (16, 27, 43, 248), (*CORAL, 120), 24, True)
        draw_text(config.canvas, "ARE YOU SURE?", fonts.MED, WHITE, (WIDTH // 2, 258),
                  center=True, shadow=True)
        draw_text(config.canvas, "Progress in this trial will be lost.", fonts.BODY, MUTED,
                  (WIDTH // 2, 296), center=True)
        self.make_button("confirm_yes", (366, 344, 180, 46), "YES, LEAVE", "menu_confirm", CORAL,
                         selected=(self.pause_index == 0))
        self.make_button("confirm_no", (556, 344, 180, 46), "NO, STAY", "menu_cancel", MINT,
                         selected=(self.pause_index == 1))
        draw_text(config.canvas, "ESC CANCEL   ·   ENTER CONFIRM", fonts.TINY, SUBTLE,
                  (WIDTH // 2, 412), center=True)

    def draw_try_again(self):
        self.draw_game_world()
        config.canvas.blit(veil(190), (0, 0))
        panel(config.canvas, (350, 240, 400, 170), (16, 27, 43, 246), (*CORAL, 130), 24, True)
        draw_text(config.canvas, "TRY AGAIN", fonts.LARGE, CORAL, (WIDTH // 2, 296),
                  center=True, shadow=True)
        draw_text(config.canvas, f"Restarting {self.theme.get('name', 'the trial')}...",
                  fonts.BODY, MUTED, (WIDTH // 2, 348), center=True)

    def draw_end_screen(self, title, subtitle, accent, buttons, info):
        self.world_scenery(config.canvas, self.frame)
        config.canvas.blit(veil(175), (0, 0))
        panel(config.canvas, (290, 118, 520, 420), (16, 27, 43, 242), (*accent, 115), 26, True)
        config.canvas.blit(get_radial_glow(64, accent, 42, 4), (WIDTH // 2 - 64, 120))
        pygame.draw.circle(config.canvas, accent, (WIDTH // 2, 184), 28, 2)
        if bank.has(self.character["id"]):
            bank.draw(config.canvas, self.character["id"], "idle",
                      int(self.frame * 0.07) % bank.count(self.character["id"], "idle"),
                      WIDTH // 2, 208, 50, facing=1)
        else:
            draw_fallback_hero(config.canvas, self.character, WIDTH // 2, 208, 50, self.frame)
        draw_text(config.canvas, title, fonts.LARGE, WHITE, (WIDTH // 2, 248),
                  center=True, shadow=True)
        draw_text(config.canvas, subtitle, fonts.BODY, MUTED, (WIDTH // 2, 286), center=True)
        pill = pygame.Rect(WIDTH // 2 - 200, 318, 400, 44)
        draw_pill(config.canvas, pill, (22, 36, 56, 230), (*accent, 90), shadow=False)
        draw_text(config.canvas, info, fonts.SMALL, WHITE, pill.center, center=True)
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
            self.draw_game_world()
        elif self.scene == "QUIZ":
            self.draw_quiz()
        elif self.scene == "PAUSED":
            self.draw_pause()
        elif self.scene == "CONFIRM_MENU":
            self.draw_confirm_menu()
        elif self.scene == "TRY_AGAIN":
            self.draw_try_again()
        elif self.scene == "LEVEL_CLEAR":
            self.draw_game_world()
            if self.clear_timer < 30:
                config.canvas.blit(veil(int(220 * (1 - self.clear_timer / 30.0))), (0, 0))
        elif self.scene == "VICTORY":
            self.draw_end_screen(
                "YOU WIN!", ("NEW PERSONAL BEST!" if self.new_record
                          else f"Best time {_fmt_time(self.best_time or 0)}"), GOLD,
                [("victory_again", (415, 392, 270, 46), "PLAY AGAIN", "retry", GOLD),
                 ("victory_menu", (415, 450, 270, 44), "MAIN MENU", "menu", BLUE)],
                f"TIME {_fmt_time(self.stats['time'])}  ·  HITS {self.stats['hits']}  ·  "
                f"PYTHON {self.stats['correct']}/{self.stats['answered']}")
        if self.scene_fade > 0:
            config.canvas.blit(veil(int(self.scene_fade)), (0, 0))
            self.scene_fade = max(0.0, self.scene_fade - 14.0 * self.dt_scale)

    # ── input / flow ─────────────────────────────────────────────
    def set_fullscreen(self, enabled):
        self.settings["fullscreen"] = enabled
        try:
            config.screen = (pygame.display.set_mode((0, 0), pygame.FULLSCREEN) if enabled
                             else pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE))
        except pygame.error:
            self.settings["fullscreen"] = False
            config.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self._scaled_canvas = (None, None)

    def handle_button_action(self, action):
        if action in ("play", "retry", "begin_run", "mode_0"):
            if action == "mode_0":
                self.change_scene("CHARACTER_SELECT")
            else:
                self.start_game()
        elif action in ("mode_1", "mode_2"):
            return                                  # COMING SOON — intentionally inert
        elif action == "select_back":
            self.change_scene("MENU")
        elif action == "settings":
            self.settings_return = self.scene
            self.change_scene("SETTINGS")
        elif action == "back":
            self.change_scene(self.settings_return)
        elif action == "fullscreen":
            self.set_fullscreen(not self.settings["fullscreen"])
            self._save()
        elif action == "particles":
            self.settings["particles"] = not self.settings["particles"]
            self._save()
        elif action == "resume":
            self.change_scene("PLAYING")
        elif action == "restart":
            self.begin_level(self.level_index)
            self.change_scene("PLAYING")
        elif action == "menu":
            if self.scene == "PAUSED":
                self.change_scene("CONFIRM_MENU")
            else:
                self.change_scene("MENU")
        elif action == "menu_confirm":
            self.change_scene("MENU")
        elif action == "menu_cancel":
            self.change_scene("PAUSED")
        elif action.startswith("quiz_a"):
            self.answer_quiz(int(action[6:]))
        elif action in ("quiz_continue", "quiz_back"):
            self.close_quiz()
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
                entry = self.button_cache.get(action)
                if isinstance(entry, dict) and entry.get("enabled") and entry["rect"].collidepoint(pos):
                    self.audio.play("click")
                    self.handle_button_action(action)
                    return
            return
        if self.scene == "CHARACTER_SELECT":
            if self.select.handle_click(pos):
                return
        if self.scene == "SETTINGS":
            for key, r in self.slider_rects.items():
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
            elif event.type == pygame.VIDEORESIZE:
                self._scaled_canvas = (None, None)
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = self.convert_mouse(event.pos)
                if self.slider_drag:
                    self.update_slider(self.mouse_pos[0])
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.slider_drag:
                    self._save()
                self.slider_drag = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_pos = self.convert_mouse(event.pos)
                self.handle_mouse_down(self.mouse_pos)
            elif event.type == pygame.KEYUP:
                # Processed in EVERY scene: no stuck jump flag after pause/respawn.
                if event.key in JUMP_KEYS and self.player:
                    self.player.cut_jump()
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

    def _handle_keydown(self, key):
        if key == pygame.K_F11:
            self.set_fullscreen(not self.settings["fullscreen"])
            self._save()
            return
        if self.scene == "MENU":
            if key == pygame.K_s:
                self.settings_return = "MENU"
                self.change_scene("SETTINGS")
            elif key == pygame.K_ESCAPE:
                self.quit()
            elif key in (pygame.K_1, pygame.K_RETURN, pygame.K_SPACE):
                self.handle_button_action("mode_0")
            # 2 and 3 are COMING SOON and deliberately do nothing.
        elif self.scene == "CHARACTER_SELECT":
            self.select.handle_key(key)
        elif self.scene == "SETTINGS":
            if key == pygame.K_ESCAPE:
                self.change_scene(self.settings_return)
        elif self.scene == "PLAYING":
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self.change_scene("PAUSED")
            elif key in GATE_KEYS and self.gate_hint is not None and self.player:
                self.open_quiz(self.gate_hint)
            elif key in JUMP_KEYS and self.player:
                keys = pygame.key.get_pressed()
                if self.player.on_one_way and any(keys[k] for k in DOWN_KEYS):
                    self.player.drop_through()
                else:
                    self.player.request_jump()
        elif self.scene == "QUIZ":
            self._quiz_key(key)
        elif self.scene == "PAUSED":
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self.handle_button_action("resume")
            elif key == pygame.K_r:
                self.handle_button_action("restart")
            elif key == pygame.K_s:
                self.handle_button_action("settings")
            elif key == pygame.K_m:
                self.handle_button_action("menu")
            elif key in (pygame.K_UP, pygame.K_w):
                self.pause_index = (self.pause_index - 1) % 4
                self.audio.play("click")
            elif key == pygame.K_DOWN:
                self.pause_index = (self.pause_index + 1) % 4
                self.audio.play("click")
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.handle_button_action(self.PAUSE_ACTIONS[self.pause_index])
        elif self.scene == "CONFIRM_MENU":
            if key == pygame.K_ESCAPE:
                self.handle_button_action("menu_cancel")
            elif key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                self.pause_index = 1 - self.pause_index
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.handle_button_action("menu_confirm" if self.pause_index == 0
                                          else "menu_cancel")
        elif self.scene == "VICTORY":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_game()
            elif key == pygame.K_ESCAPE:
                self.change_scene("MENU")

    def _quiz_key(self, key):
        qz = self.quiz
        if qz is None:
            self.change_scene("PLAYING")
            return
        if qz["state"] != "ask":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_e,
                       pygame.K_ESCAPE):
                self.close_quiz()
            return
        if key == pygame.K_ESCAPE:
            self.close_quiz()
        elif key in ANSWER_KEYS:
            self.answer_quiz(ANSWER_KEYS.index(key))
        elif key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
            qz["sel"] ^= 1
            self.audio.play("click")
        elif key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            qz["sel"] ^= 2
            self.audio.play("click")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.answer_quiz(qz["sel"])

    def quit(self):
        self._save()
        pygame.quit()
        raise SystemExit

    # ── main loop: fixed physics, free-running render ────────────
    def update_scene(self, raw_ms):
        if self.scene == "PLAYING":
            self.accumulator += min(raw_ms / 1000.0, 0.25)
            steps = 0
            while self.accumulator >= PHYSICS_DT and steps < MAX_PHYSICS_STEPS:
                self.accumulator -= PHYSICS_DT
                steps += 1
                self.update_gameplay()
                if self.scene != "PLAYING":
                    self.accumulator = 0.0
                    break
            if steps >= MAX_PHYSICS_STEPS:
                self.accumulator = 0.0
        elif self.scene == "TRY_AGAIN":
            self.try_again_timer -= self.dt_scale
            if self.try_again_timer <= 0:
                self.begin_level(self.level_index)
                self.change_scene("PLAYING")
        elif self.scene == "LEVEL_CLEAR":
            self._update_fx()
            self.clear_timer -= self.dt_scale
            if self.clear_timer <= 0:
                if self.level_index < len(LEVEL_LAYOUTS) - 1:
                    self.begin_level(self.level_index + 1)
                    self.scene = "PLAYING"
                else:
                    self._finish_run()

    def run(self):
        while True:
            raw_ms = config.clock.tick(FPS)
            self.dt_scale = clamp(raw_ms / (1000.0 / FPS), 0.25, 3.0)
            self.frame += self.dt_scale
            self.mouse_pos = self.convert_mouse(pygame.mouse.get_pos())
            self.handle_events()

            self.update_scene(raw_ms)

            self.draw_scene()

            vp = self.get_viewport_rect()
            if vp.size == (WIDTH, HEIGHT) and vp.topleft == (0, 0):
                config.screen.blit(config.canvas, (0, 0))
            else:
                size, surf = self._scaled_canvas
                if size != vp.size or surf is None:
                    surf = pygame.transform.scale(config.canvas, vp.size)
                    self._scaled_canvas = (vp.size, surf)
                else:
                    pygame.transform.scale(config.canvas, vp.size, surf)
                config.screen.fill((4, 8, 16))
                config.screen.blit(surf, vp.topleft)
            pygame.display.flip()