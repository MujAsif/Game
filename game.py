"""
GAME — Main orchestrator class.
Handles scene flow, platformer mechanics, camera scrolling, pit deaths, and aesthetic UI.
Stage 1 uses the procedural sakura twilight theme (sakura.py) when available.
"""
import os
import pygame
import math
import random
import config
from config import (WIDTH, HEIGHT, FPS, GROUND_Y, INK, WHITE, MUTED, SUBTLE,
                    GOLD, GOLD_SOFT, MINT, CORAL, BLUE, CRIMSON, MAX_HEARTS,
                    GRAVITY, MAX_FALL_SPEED, MOVE_SPEED, ACCEL_GROUND, ACCEL_AIR,
                    FRICTION_GROUND, FRICTION_AIR, fonts)
from data import LEVELS, LEVEL_THEMES
from ui import (draw_text, wrap_text, gradient_rect, draw_pill, panel,
                get_radial_glow, get_smooth_heart, get_smooth_star, veil, Button,
                clamp, blend_color, lerp)
from audio import AudioManager
from entities import Player, Particle, FloatingText
from sprites import bank, ROSTER
from character_select import CharacterSelect
import sakura

_MENU_CACHE = {}
TITLE_BG_CANDIDATES = (
    os.path.join("assets", "ui", "title_bg.png"),
    os.path.join("assets", "title_bg.png"),
    "title_bg.png",
)


def _alpha_grad(w, h, horizontal, a0, a1, color=(8, 10, 20)):
    key = ("ag", w, h, horizontal, a0, a1, color)
    hit = _MENU_CACHE.get(key)
    if hit is not None: return hit
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    n = w if horizontal else h
    for i in range(n):
        t = i / max(1, n - 1)
        a = int(a0 + (a1 - a0) * t)
        if horizontal: pygame.draw.line(s, (*color, a), (i, 0), (i, h - 1))
        else: pygame.draw.line(s, (*color, a), (0, i), (w - 1, i))
    if len(_MENU_CACHE) > 60: _MENU_CACHE.clear()
    _MENU_CACHE[key] = s
    return s


class Game:
    def __init__(self):
        self.audio = AudioManager()
        self.scene, self.settings_return = "MENU", "MENU"
        self.selected_character = 0
        self.character = ROSTER[0]
        self.stats = self.new_stats()
        self.level_index, self.unlocked_levels = 0, 1
        self.theme = LEVEL_THEMES[0]
        self.dt_scale, self.frame, self.scene_fade = 1.0, 0.0, 0.0
        self.buttons, self.button_cache, self.mouse_pos = [], {}, (0, 0)
        self.particles, self.popups = [], []
        self.player, self.platforms = None, []
        self.coins = []
        self.game_mode = 0
        self.mode_names = ["THE ASCENT", "THE LABYRINTH", "THE STORM"]
        self.mode_descriptions = ["A platformer of wit and agility.", "A puzzle of logic and memory.", "An arcade test of reflexes."]
        # Platformer specific
        self.camera_x = 0.0
        self.level_width = WIDTH
        self.flag_rect = None
        self.start_pos = (100, GROUND_Y - 54)
        self.shake = 0.0
        self.score_display = 0.0
        self.settings = {"fullscreen": False, "particles": True}
        self.slider_drag = None
        self.menu_hover_index = -1
        self.title_bob = 0.0
        self.motes = [(random.randrange(WIDTH), random.randrange(70, GROUND_Y - 30), random.random() * math.tau, random.uniform(0.5, 1.2)) for _ in range(38)]
        self.clouds = [(110, 92, 1.0, 0.10), (470, 64, 1.2, 0.07), (840, 128, 0.9, 0.12)]
        self.bg_base = self.make_background()
        self.petals = [{"x": random.randrange(WIDTH), "y": random.randrange(HEIGHT), "ph": random.random() * math.tau, "sp": random.uniform(0.45, 1.1), "sw": random.uniform(10, 28), "sz": random.randint(3, 6)} for _ in range(26)]
        self._title_bg = None
        self._title_bg_missing = False
        self.select = CharacterSelect(self)

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
        return (int(clamp((position[0] - vp.x) * WIDTH / vp.w, 0, WIDTH - 1)), int(clamp((position[1] - vp.y) * HEIGHT / vp.h, 0, HEIGHT - 1)))

    def _title_background(self):
        if self._title_bg is not None: return self._title_bg
        if self._title_bg_missing: return None
        here = os.path.dirname(os.path.abspath(__file__))
        path = None
        for cand in TITLE_BG_CANDIDATES:
            for base in (here, os.getcwd()):
                p = os.path.join(base, cand)
                if os.path.isfile(p):
                    path = p
                    break
            if path: break
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
            return None
        return self._title_bg

    def _draw_petals(self, surface):
        for p in self.petals:
            y = (p["y"] + self.frame * p["sp"]) % (HEIGHT + 40) - 20
            x = (p["x"] + math.sin(self.frame * 0.02 + p["ph"]) * p["sw"]) % WIDTH
            rot = math.sin(self.frame * 0.05 + p["ph"])
            sz, rb = p["sz"], int(rot * 4)
            key = ("petal", sz, rb)
            s = _MENU_CACHE.get(key)
            if s is None:
                base = pygame.Surface((sz * 3, sz * 2), pygame.SRCALPHA)
                pygame.draw.ellipse(base, (244, 152, 192, 205), base.get_rect())
                s = pygame.transform.rotate(base, rb * 12)
                if len(_MENU_CACHE) > 60: _MENU_CACHE.clear()
                _MENU_CACHE[key] = s
            surface.blit(s, (int(x), int(y)))

    def _menu_options(self):
        return [("I. THE ASCENT", "mode_0"), ("II. THE LABYRINTH", "mode_1"), ("III. THE STORM", "mode_2"), ("SETTINGS", "settings"), ("QUIT", "quit")]

    def _register_menu_rect(self, action, rect):
        if action not in self.button_cache: self.button_cache[action] = {"rect": rect, "action": action}
        else: self.button_cache[action]["rect"] = rect

    def draw_menu(self):
        bg = self._title_background()
        if bg is not None: self._draw_menu_image(bg)
        else: self._draw_menu_procedural()

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
            hover = rect.collidepoint(self.mouse_pos)
            if hover:
                self.menu_hover_index = i
                draw_pill(cv, rect, (16, 22, 38, 190), (*GOLD, 150), shadow=False)
                tri = [(rect.x + 10, rect.centery - 6), (rect.x + 10, rect.centery + 6), (rect.x + 20, rect.centery)]
                pygame.draw.polygon(cv, GOLD, tri)
                draw_text(cv, text, fonts.FONT, GOLD, (rect.x + 34, rect.centery), valign="middle")
            else:
                draw_text(cv, text, fonts.FONT, WHITE if i < 3 else MUTED, (rect.x + 34, rect.centery), valign="middle")
            self._register_menu_rect(action, rect)
        chip = pygame.Rect(24, HEIGHT - 54, 214, 34)
        draw_pill(cv, chip, (14, 20, 34, 210), (*self.character["accent"], 110), shadow=False)
        if bank.has(self.character["id"]):
            n = bank.count(self.character["id"], "idle")
            bank.draw(cv, self.character["id"], "idle", int(self.frame * 0.07) % n, 48, HEIGHT - 24, 26, facing=1)
        draw_text(cv, f"{self.character['name']} · {self.character['short']}", fonts.TINY, WHITE, (66, chip.centery), valign="middle")
        draw_text(cv, "1–3 MODES   ·   S SETTINGS   ·   ESC QUIT", fonts.TINY, (214, 224, 238), (WIDTH - 24, HEIGHT - 22), right=True)

    def _draw_menu_procedural(self):
        self.world_scenery(config.canvas, self.frame)
        self.draw_menu_silhouette(config.canvas, 850, GROUND_Y)
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
            hover = rect.collidepoint(self.mouse_pos)
            if hover:
                self.menu_hover_index = i
                tri = [(rect.left - 20, rect.centery - 6), (rect.left - 20, rect.centery + 6), (rect.left - 8, rect.centery)]
                pygame.draw.polygon(config.canvas, GOLD, tri)
                draw_text(config.canvas, text, fonts.FONT, GOLD, (WIDTH // 2, y), center=True)
            else:
                draw_text(config.canvas, text, fonts.FONT, WHITE if i < 3 else MUTED, (WIDTH // 2, y), center=True)
            self._register_menu_rect(action, rect)

    def draw_menu_silhouette(self, surface, x, y):
        pygame.draw.ellipse(surface, (0, 0, 0, 100), (x - 20, y - 5, 40, 10))
        pygame.draw.rect(surface, INK, (x - 12, y - 40, 24, 40), border_radius=4)
        pygame.draw.circle(surface, INK, (x, y - 50), 14)
        scarf_pts = [(x - 5, y - 35), (x - 25, y - 30), (x - 40, y - 38), (x - 35, y - 25)]
        pygame.draw.polygon(surface, CRIMSON, scarf_pts)

    def make_background(self):
        if self.theme.get("style") == "sakura":
            return sakura.make_background(self.theme)
        bg = pygame.Surface((WIDTH, HEIGHT)).convert()
        theme = self.theme
        gradient_rect(bg, (0, 0, WIDTH, HEIGHT), theme["sky_top"], theme["sky_bottom"])
        rng = random.Random(42 + self.level_index * 19)
        for _ in range(55):
            shade = rng.randint(120, 200)
            pygame.draw.circle(bg, (shade, min(255, shade + 12), min(255, shade + 24)), (rng.randrange(WIDTH), rng.randrange(24, 290)), 1)
        cx, cy = 830, 132
        sky_at = lambda yy: blend_color(theme["sky_top"], theme["sky_bottom"], clamp(yy / HEIGHT, 0.0, 1.0))
        bg.blit(get_radial_glow(150, theme["celestial"], 34, 5), (cx - 150, cy - 150))
        pygame.draw.circle(bg, theme["celestial"], (cx, cy), 34)
        d, ox, oy = 64, cx + 12 - 32, cy - 8 - 32
        cut = pygame.Surface((d, d), pygame.SRCALPHA)
        for yy in range(d):
            c = sky_at(oy + yy)
            pygame.draw.line(cut, (*c, 255), (0, yy), (d - 1, yy))
        mask = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (d // 2, d // 2), d // 2)
        cut.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        bg.blit(cut, (ox, oy))
        pygame.draw.polygon(bg, theme["ridge_far"], [(0, 410), (140, 250), (290, 365), (460, 215), (630, 355), (810, 235), (980, 350), (1100, 285), (1100, GROUND_Y), (0, GROUND_Y)])
        pygame.draw.polygon(bg, theme["ridge_mid"], [(0, 445), (210, 310), (390, 430), (590, 315), (780, 435), (960, 305), (1100, 390), (1100, GROUND_Y), (0, GROUND_Y)])
        pygame.draw.polygon(bg, theme["ridge_near"], [(0, 485), (170, 415), (360, 492), (560, 420), (760, 495), (940, 425), (1100, 475), (1100, GROUND_Y), (0, GROUND_Y)])
        for x in range(30, WIDTH, 95):
            h, w = 34 + ((x * 13) % 26), 16 + ((x * 7) % 8)
            pygame.draw.polygon(bg, theme["ridge_near"], [(x - w, GROUND_Y), (x, GROUND_Y - h), (x + w, GROUND_Y)])
        gradient_rect(bg, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y), theme["ground_top"], theme["ground_bottom"])
        pygame.draw.line(bg, blend_color(theme["ground_top"], WHITE, 0.22), (0, GROUND_Y), (WIDTH, GROUND_Y), 2)
        return bg

    def world_scenery(self, target, frame, cam_x=0.0):
        target.blit(self.bg_base, (0, 0))
        if self.theme.get("style") == "sakura":
            sakura.draw_sky_fx(target, frame, cam_x)
            sakura.draw_petals(target, frame, cam_x, front=False)
            return
        for cx, cy, scale, speed in self.clouds:
            x = (cx + frame * speed) % (WIDTH + 200) - 100
            w, h = int(96 * scale), int(22 * scale)
            cloud = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(cloud, (255, 255, 255, 18), cloud.get_rect(), border_radius=h // 2)
            target.blit(cloud, (int(x), int(cy)))
        for x, y, phase, _ in self.motes:
            pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(frame * 0.035 + phase))
            xx = (x + math.sin(frame * 0.015 + phase) * 8) % WIDTH
            yy = y + math.cos(frame * 0.02 + phase) * 5
            pygame.draw.circle(target, self.theme["mote"], (int(xx), int(yy)), 2 if pulse > 0.75 else 1)

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
        self.level_index = int(clamp(level_index, 0, len(LEVELS) - 1))
        level = LEVELS[self.level_index]
        self.theme = LEVEL_THEMES[self.level_index]
        self.bg_base = self.make_background()
        self.player = Player(self.character)
        # FIX: Dynamically find the platform height at the start position
        start_y = GROUND_Y
        for p in level["platforms"]:
            if p["x"] <= level["start_x"] <= p["x"] + p["w"]:
                start_y = p["y"]
                break
        self.player.x = float(level["start_x"])
        self.player.y = float(start_y - self.player.h - 10)  # Spawn 10px above the platform
        self.player.sync_rect()
        self.start_pos = (level["start_x"], start_y - self.player.h - 10)
        self.level_width = level["width"]
        self.platforms = [pygame.Rect(p["x"], p["y"], p["w"], p["h"]) for p in level["platforms"]]
        flag_x = level["flag_x"]
        flag_y = GROUND_Y
        for p in self.platforms:
            if p.left <= flag_x <= p.right:
                flag_y = p.top
                break
        self.flag_rect = pygame.Rect(flag_x - 10, flag_y - 80, 20, 80)
        self.coins = [{"x": c[0], "y": c[1], "taken": False} for c in level.get("coins", [])]
        self.camera_x = 0.0
        self.particles.clear()
        self.popups.clear()
        self.score_display = float(self.stats["score"])
        self.scene_fade = 160.0

    def update_camera(self):
        target_x = self.player.rect.centerx - WIDTH // 2
        self.camera_x = clamp(self.camera_x + (target_x - self.camera_x) * 0.1 * self.dt_scale, 0, max(0, self.level_width - WIDTH))

    def update_player(self):
        player = self.player
        keys = pygame.key.get_pressed()
        move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        if move:
            player.facing = move
            player.vx = clamp(player.vx + move * (ACCEL_GROUND if player.on_ground else ACCEL_AIR) * player.accel_mul * self.dt_scale, -player.max_speed, player.max_speed)
        else:
            player.vx *= (FRICTION_GROUND if player.on_ground else FRICTION_AIR) ** self.dt_scale
            if abs(player.vx) < 0.08: player.vx = 0.0
        player.walking = abs(player.vx) > 0.35
        if player.walking:
            player.anim += self.dt_scale * (abs(player.vx) / MOVE_SPEED)
            if self.settings["particles"] and player.on_ground and int(self.frame) % 12 == 0:
                self.particles.append(Particle(player.rect.centerx, player.rect.bottom, (190, 212, 222), dust=True))
        solids = self.platforms
        player.x += player.vx * self.dt_scale
        player.sync_rect()
        for s in solids:
            if player.rect.colliderect(s):
                if player.vx > 0: player.rect.right = s.left
                elif player.vx < 0: player.rect.left = s.right
                player.x = float(player.rect.x)
                player.vx = 0.0
        was_ground = player.on_ground
        player.coyote_timer = 7.0 if was_ground else max(0.0, player.coyote_timer - self.dt_scale)
        if player.jump_buffer > 0:
            player.jump_buffer = max(0.0, player.jump_buffer - self.dt_scale)
            if player.on_ground or player.coyote_timer > 0:
                player.execute_jump(self.particles, self.audio)
                was_ground = False
        prev_bottom = player.rect.bottom
        jump_held = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]
        player.gliding = (player.can_glide and not player.on_ground and player.vel_y > 1.0 and jump_held)
        grav = GRAVITY * (0.42 if player.gliding else 1.0)
        max_fall = MAX_FALL_SPEED * (0.5 if player.gliding else 1.0)
        player.vel_y = min(player.vel_y + grav * self.dt_scale, max_fall)
        player.y += player.vel_y * self.dt_scale
        player.sync_rect()
        player.on_ground = False
        landed = False
        # Pit Death Check
        if player.rect.top > HEIGHT + 100:
            self.stats["lives"] -= 1
            if self.stats["lives"] <= 0:
                self.change_scene("GAME_OVER")
                return
            else:
                player.x, player.y = float(self.start_pos[0]), float(self.start_pos[1])
                player.vx = player.vel_y = 0.0
                player.sync_rect()
                self.add_popup("RESPAWNED", player.rect.centerx, player.rect.y - 40, CORAL)
                self.audio.play("wrong")
                return
        for s in solids:
            if player.rect.colliderect(s):
                if player.vel_y >= 0 and prev_bottom <= s.top + 12:
                    player.rect.bottom = s.top
                    player.y = float(player.rect.y)
                    landed = True
                    break
                elif player.vel_y < 0 and player.rect.top >= s.bottom - 12:
                    player.rect.top = s.bottom
                    player.y = float(player.rect.y)
                    player.vel_y = 0.0
        if landed:
            if not was_ground and player.vel_y > 3.5:
                player.land_squash = 1.0
                self.audio.play("land")
                if self.settings["particles"]:
                    self.particles.append(Particle(player.rect.centerx, player.rect.bottom, (200, 224, 232), ring=True))
            player.vel_y = 0.0
            player.on_ground = True
            player.gliding = False
            if player.jump_buffer > 0: player.execute_jump(self.particles, self.audio)
        player.land_squash = max(0.0, player.land_squash - 0.14 * self.dt_scale)
        player.hurt_timer = max(0.0, player.hurt_timer - self.dt_scale)
        player.update_scarf(self.dt_scale)

    def update_gameplay(self):
        self.update_player()
        self.update_camera()
        self.collect_coins()
        if self.player and self.player.rect.colliderect(self.flag_rect):
            self.stats["score"] += 500
            self.unlocked_levels = max(self.unlocked_levels, min(len(LEVELS), self.level_index + 2))
            self.add_popup("SUMMIT REACHED", WIDTH // 2, 210, MINT)
            self.add_particle_burst(self.flag_rect.centerx, self.flag_rect.y + 20, GOLD, 45, 5.2)
            self.audio.play("level")
            self.change_scene("LEVEL_COMPLETE")
        for pt in self.particles[:]:
            pt.update(self.dt_scale)
            if pt.life <= 0: self.particles.remove(pt)
        for pp in self.popups[:]:
            pp.update(self.dt_scale)
            if pp.life <= 0: self.popups.remove(pp)

    def collect_coins(self):
        if not self.coins:
            return
        pr = self.player.rect
        for c in self.coins:
            if not c["taken"] and abs(pr.centerx - c["x"]) < 30 and abs(pr.centery - c["y"]) < 36:
                c["taken"] = True
                self.stats["score"] += 50
                self.add_popup("+50", c["x"], c["y"] - 18, GOLD)
                self.add_particle_burst(c["x"], c["y"], GOLD, 10, 3.0)
                self.audio.play("click")

    def draw_coins(self, surface):
        if not self.coins:
            return
        for i, c in enumerate(self.coins):
            if not c["taken"]:
                sakura.draw_coin(surface, c["x"] - self.camera_x, c["y"], self.frame, i)

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

    def get_shadow_surface_y(self):
        cx = self.player.rect.centerx
        best = float(HEIGHT)
        for s in self.platforms:
            if s.left <= cx <= s.right and s.top >= self.player.rect.bottom - 4 and s.top < best:
                best = float(s.top)
        return best

    def draw_prop(self, surface, prop, cam_x):
        if self.theme.get("style") == "sakura":
            sakura.draw_prop(surface, prop, cam_x, self.frame)
            return
        px, py = int(prop["x"] - cam_x), int(prop["y"])
        if px < -100 or px > WIDTH + 100: return
        ptype = prop["type"]
        colors = self.theme.get("prop_colors", {})
        if ptype == "tree_pine":
            pygame.draw.rect(surface, colors.get("wood", (139, 69, 19)), (px - 5, py - 40, 10, 40))
            pygame.draw.polygon(surface, colors.get("leaf", (40, 100, 40)), [(px - 20, py - 30), (px + 20, py - 30), (px, py - 80)])
            pygame.draw.polygon(surface, colors.get("leaf", (40, 100, 40)), [(px - 25, py - 50), (px + 25, py - 50), (px, py - 100)])
            if self.level_index == 0: pygame.draw.polygon(surface, colors.get("snow", (240, 248, 255)), [(px - 15, py - 60), (px + 15, py - 60), (px, py - 80)])
        elif ptype == "snowman":
            pygame.draw.circle(surface, colors.get("snow", (240, 248, 255)), (px, py - 20), 15)
            pygame.draw.circle(surface, colors.get("snow", (240, 248, 255)), (px, py - 45), 10)
            pygame.draw.circle(surface, (0, 0, 0), (px - 3, py - 48), 2)
            pygame.draw.polygon(surface, (255, 100, 0), [(px, py - 45), (px + 10, py - 43), (px, py - 41)])
        elif ptype == "ice_block":
            r = pygame.Rect(px - 15, py - 30, 30, 30)
            pygame.draw.rect(surface, colors.get("ice", (180, 220, 255)), r, border_radius=5)
            pygame.draw.line(surface, (255, 255, 255), (r.left + 5, r.top + 5), (r.right - 5, r.bottom - 5), 2)
        elif ptype == "igloo":
            pygame.draw.arc(surface, colors.get("snow", (240, 248, 255)), (px - 40, py - 40, 80, 80), 0, math.pi, 40)
            pygame.draw.rect(surface, (100, 150, 200), (px - 10, py - 15, 20, 15))
        elif ptype == "cactus":
            pygame.draw.rect(surface, colors.get("cactus", (60, 140, 60)), (px - 5, py - 40, 10, 40), border_radius=5)
            pygame.draw.rect(surface, colors.get("cactus", (60, 140, 60)), (px - 15, py - 30, 10, 20), border_radius=5)
            pygame.draw.rect(surface, colors.get("cactus", (60, 140, 60)), (px + 5, py - 20, 10, 20), border_radius=5)
        elif ptype == "crate":
            r = pygame.Rect(px - 15, py - 30, 30, 30)
            pygame.draw.rect(surface, colors.get("wood", (139, 69, 19)), r, border_radius=3)
            pygame.draw.line(surface, (80, 50, 30), (r.left, r.top), (r.right, r.bottom), 2)
            pygame.draw.line(surface, (80, 50, 30), (r.right, r.top), (r.left, r.bottom), 2)
        elif ptype == "tree_acacia":
            pygame.draw.rect(surface, colors.get("wood", (139, 69, 19)), (px - 3, py - 50, 6, 50))
            pygame.draw.ellipse(surface, colors.get("leaf", (40, 100, 40)), (px - 30, py - 70, 60, 30))
            pygame.draw.ellipse(surface, colors.get("leaf", (40, 100, 40)), (px - 20, py - 85, 40, 20))
        elif ptype == "skull":
            pygame.draw.ellipse(surface, colors.get("bone", (240, 240, 220)), (px - 15, py - 20, 30, 20))
            pygame.draw.circle(surface, (0, 0, 0), (px - 5, py - 10), 3)
            pygame.draw.circle(surface, (0, 0, 0), (px + 5, py - 10), 3)
        elif ptype == "signpost":
            pygame.draw.rect(surface, colors.get("wood", (139, 69, 19)), (px - 2, py - 40, 4, 40))
            pygame.draw.rect(surface, colors.get("wood", (139, 69, 19)), (px - 15, py - 40, 30, 15), border_radius=2)
        elif ptype == "tree_leafy":
            pygame.draw.rect(surface, colors.get("wood", (100, 70, 50)), (px - 5, py - 60, 10, 60))
            pygame.draw.circle(surface, colors.get("leaf", (40, 100, 40)), (px, py - 70), 25)
            pygame.draw.circle(surface, colors.get("leaf", (40, 100, 40)), (px - 15, py - 60), 20)
            pygame.draw.circle(surface, colors.get("leaf", (40, 100, 40)), (px + 15, py - 60), 20)
        elif ptype == "plant_tall":
            pygame.draw.line(surface, colors.get("grass", (60, 140, 60)), (px, py), (px - 10, py - 30), 3)
            pygame.draw.line(surface, colors.get("grass", (60, 140, 60)), (px, py), (px + 10, py - 30), 3)
            pygame.draw.line(surface, colors.get("grass", (60, 140, 60)), (px, py), (px, py - 40), 3)
        elif ptype == "ruin_column":
            pygame.draw.rect(surface, colors.get("stone", (120, 120, 120)), (px - 10, py - 60, 20, 60))
            pygame.draw.rect(surface, colors.get("stone", (120, 120, 120)), (px - 15, py - 70, 30, 10))

    def draw_platform(self, surface, rect, cam_x):
        if self.theme.get("style") == "sakura":
            sakura.draw_platform(surface, rect, cam_x, self.frame)
            return
        rx, ry = int(rect.x - cam_x), int(rect.y)
        if rx + rect.w < 0 or rx > WIDTH: return
        body = self.theme["ground_top"]
        edge_col = blend_color(body, WHITE, 0.3)
        if self.level_index == 0: edge_col = (240, 248, 255)
        if self.level_index == 1: edge_col = (230, 200, 150)
        if self.level_index == 2: edge_col = (60, 140, 60)
        pygame.draw.rect(surface, body, (rx, ry, rect.w, rect.h))
        pygame.draw.rect(surface, edge_col, (rx, ry, rect.w, 6))
        rng = random.Random(rx * 100 + ry)
        for _ in range(int(rect.w * rect.h / 800)):
            dx, dy = rng.randint(5, rect.w - 5), rng.randint(10, rect.h - 5)
            col = blend_color(body, INK, 0.2)
            pygame.draw.circle(surface, col, (rx + dx, ry + dy), 2)

    def draw_flag(self, surface, cam_x):
        fx, fy = int(self.flag_rect.centerx - cam_x), int(self.flag_rect.bottom)
        if fx < -50 or fx > WIDTH + 50: return
        pygame.draw.line(surface, (200, 200, 200), (fx, fy), (fx, fy - 80), 4)
        wave = math.sin(self.frame * 0.1) * 5
        points = [(fx, fy - 80), (fx + 40, fy - 70 + wave), (fx, fy - 60)]
        pygame.draw.polygon(surface, CORAL, points)
        pygame.draw.rect(surface, (100, 100, 100), (fx - 10, fy - 5, 20, 5))

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
        score_pill = pygame.Rect(hearts_pill.right + 12, 18, 192, 46)
        draw_pill(config.canvas, score_pill)
        star = get_smooth_star(22, GOLD)
        config.canvas.blit(star, star.get_rect(center=(score_pill.x + 28, score_pill.centery)))
        self.score_display = lerp(self.score_display, self.stats["score"], 0.16)
        draw_text(config.canvas, "SCORE", fonts.TINY, MUTED, (score_pill.x + 48, score_pill.y + 8))
        draw_text(config.canvas, f"{int(round(self.score_display)):,}", fonts.FONT, WHITE, (score_pill.x + 48, score_pill.y + 22))
        prog = pygame.Rect(WIDTH - 292, 18, 272, 46)
        draw_pill(config.canvas, prog)
        draw_text(config.canvas, f"LEVEL {self.level_index + 1}", fonts.SMALL, self.theme["accent"], (prog.x + 22, prog.centery), valign="middle")
        chip = pygame.Rect(20, HEIGHT - 46, 196, 32)
        draw_pill(config.canvas, chip, (16, 26, 42, 210), (*self.character["accent"], 90), shadow=False)
        if bank.has(self.character["id"]):
            n = bank.count(self.character["id"], "idle")
            bank.draw(config.canvas, self.character["id"], "idle", int(self.frame * 0.07) % n, 44, HEIGHT - 17, 26, facing=1)
        draw_text(config.canvas, f"{self.character['name']} · {self.character['short']}", fonts.TINY, WHITE, (64, chip.centery), valign="middle")

    def draw_game_world(self):
        self.world_scenery(config.world, self.frame, self.camera_x)
        level_data = LEVELS[self.level_index]
        for prop in level_data["props"]:
            self.draw_prop(config.world, prop, self.camera_x)
        for p in self.platforms:
            self.draw_platform(config.world, p, self.camera_x)
        self.draw_flag(config.world, self.camera_x)
        self.draw_coins(config.world)
        if self.theme.get("style") == "sakura":
            sakura.draw_mist(config.world, self.frame, self.camera_x)
        temp_x = self.player.x
        self.player.x -= self.camera_x
        self.player.sync_rect()
        self.player.draw(config.world, self.frame, self.get_shadow_surface_y())
        self.player.x = temp_x
        self.player.sync_rect()
        for pt in self.particles: pt.draw(config.world)
        for pp in self.popups: pp.draw(config.world)
        if self.theme.get("style") == "sakura":
            sakura.draw_petals(config.world, self.frame, self.camera_x, front=True)
        offset = (0, 0)
        if self.shake > 0:
            i = max(1, int(self.shake / 3))
            offset = (random.randint(-i, i), random.randint(-i, i))
            self.shake = max(0.0, self.shake - self.dt_scale)
        config.canvas.fill(INK)
        config.canvas.blit(config.world, offset)
        self.draw_hud()

    def draw_placeholder_game(self):
        self.world_scenery(config.canvas, self.frame)
        config.canvas.blit(veil(180), (0, 0))
        panel(config.canvas, (250, 150, 600, 350), (15, 25, 40, 240), (130, 162, 190, 100), 26, True)
        mode_name = self.mode_names[self.game_mode]
        mode_desc = self.mode_descriptions[self.game_mode]
        draw_text(config.canvas, mode_name, fonts.LARGE, GOLD, (WIDTH // 2, 220), center=True)
        draw_text(config.canvas, mode_desc, fonts.BODY, WHITE, (WIDTH // 2, 280), center=True)
        draw_text(config.canvas, "(Coming in the full release)", fonts.SMALL, MUTED, (WIDTH // 2, 320), center=True)
        if bank.has(self.character["id"]):
            n = bank.count(self.character["id"], "idle")
            bank.draw(config.canvas, self.character["id"], "idle", int(self.frame * 0.07) % n, 330, 440, 118, facing=1)
        draw_text(config.canvas, f"{self.character['name']} AWAITS", fonts.TINY, self.character["accent"], (330, 458), center=True)
        self.make_button("placeholder_back", (420, 400, 260, 46), "RETURN TO MENU", "menu", GOLD)

    def make_button(self, key, rect, label, action, accent=GOLD):
        if key not in self.button_cache: self.button_cache[key] = Button(key, rect, label, action, accent)
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
        if fill: pygame.draw.rect(config.canvas, MINT if key == "music" else BLUE, (x, y, fill, 8), border_radius=4)
        pygame.draw.circle(config.canvas, WHITE, (x + fill, y + 4), 9)
        pygame.draw.circle(config.canvas, GOLD if self.slider_drag == key else SUBTLE, (x + fill, y + 4), 9, 2)
        self.slider_rects = getattr(self, "slider_rects", {})
        self.slider_rects[key] = pygame.Rect(x - 12, y - 14, width + 24, 34)

    def draw_settings(self):
        self.world_scenery(config.canvas, self.frame)
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
        self.make_button("pause_settings", (415, 352, 270, 46), "SETTINGS", "pause_settings", BLUE)
        self.make_button("pause_menu", (415, 410, 270, 46), "MAIN MENU", "menu", CORAL)

    def draw_end_screen(self, title, subtitle, accent, buttons):
        self.world_scenery(config.canvas, self.frame)
        config.canvas.blit(veil(175), (0, 0))
        panel(config.canvas, (290, 118, 520, 420), (16, 27, 43, 242), (*accent, 115), 26, True)
        config.canvas.blit(get_radial_glow(64, accent, 42, 4), (WIDTH // 2 - 64, 120))
        pygame.draw.circle(config.canvas, accent, (WIDTH // 2, 184), 28, 2)
        if bank.has(self.character["id"]):
            n = bank.count(self.character["id"], "idle")
            bank.draw(config.canvas, self.character["id"], "idle", int(self.frame * 0.07) % n, WIDTH // 2, 208, 50, facing=1)
        draw_text(config.canvas, title, fonts.LARGE, WHITE, (WIDTH // 2, 248), center=True, shadow=True)
        draw_text(config.canvas, subtitle, fonts.BODY, MUTED, (WIDTH // 2, 286), center=True)
        pill = pygame.Rect(WIDTH // 2 - 170, 318, 340, 44)
        draw_pill(config.canvas, pill, (22, 36, 56, 230), (*accent, 90), shadow=False)
        draw_text(config.canvas, f"SCORE: {self.stats['score']:,}    ·    BEST STREAK: x{self.stats['best_combo']}", fonts.SMALL, WHITE, pill.center, center=True)
        for b in buttons: self.make_button(*b)

    def draw_scene(self):
        self.buttons = []
        if self.scene == "MENU": self.draw_menu()
        elif self.scene == "CHARACTER_SELECT": self.select.draw()
        elif self.scene == "SETTINGS": self.draw_settings()
        elif self.scene == "PLAYING":
            if self.game_mode == 0: self.draw_game_world()
            else: self.draw_placeholder_game()
        elif self.scene == "PLACEHOLDER_GAME": self.draw_placeholder_game()
        elif self.scene == "PAUSED": self.draw_pause()
        elif self.scene == "GAME_OVER":
            self.draw_end_screen("OUT OF HEARTS", "Every climb teaches the path to the top.", CORAL, [("game_retry", (415, 392, 270, 46), "TRY AGAIN", "retry", GOLD), ("game_menu", (415, 450, 270, 44), "MAIN MENU", "menu", BLUE)])
        elif self.scene == "LEVEL_COMPLETE":
            final = self.level_index == len(LEVELS) - 1
            self.draw_end_screen("SUMMIT CONQUERED" if final else "LEVEL CLEARED", "All three regions mastered." if final else f"{LEVELS[self.level_index]['name'].title()} complete.", self.theme["accent"], [("complete_continue", (415, 392, 270, 46), "FINISH ADVENTURE" if final else "NEXT LEVEL", "victory" if final else "next_level", GOLD)])
        elif self.scene == "VICTORY":
            self.draw_end_screen("YOU WIN!", "You are a true Python trailblazer.", GOLD, [("victory_again", (415, 392, 270, 46), "PLAY AGAIN", "retry", GOLD), ("victory_menu", (415, 450, 270, 44), "MAIN MENU", "menu", BLUE)])
        if self.scene_fade > 0:
            v = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            v.fill((3, 9, 18, int(self.scene_fade)))
            config.canvas.blit(v, (0, 0))
            self.scene_fade = max(0.0, self.scene_fade - 14.0 * self.dt_scale)

    def set_fullscreen(self, enabled):
        self.settings["fullscreen"] = enabled
        try: config.screen = (pygame.display.set_mode((0, 0), pygame.FULLSCREEN) if enabled else pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE))
        except pygame.error:
            self.settings["fullscreen"] = False
            config.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

    def handle_button_action(self, action):
        if action in ("play", "retry", "begin_run"): self.start_game(0)
        elif action == "mode_0": self.change_scene("CHARACTER_SELECT")
        elif action.startswith("mode_"): self.start_game(int(action.split("_")[1]))
        elif action == "select_back": self.change_scene("MENU")
        elif action == "settings":
            self.settings_return = self.scene
            self.change_scene("SETTINGS")
        elif action == "back": self.change_scene(self.settings_return)
        elif action == "fullscreen": self.set_fullscreen(not self.settings["fullscreen"])
        elif action == "particles": self.settings["particles"] = not self.settings["particles"]
        elif action == "resume": self.change_scene("PLAYING")
        elif action == "restart":
            self.stats["lives"] = self.stats.get("max_lives", MAX_HEARTS)
            self.stats["combo"] = 0
            self.begin_level(self.level_index)
            self.change_scene("PLAYING")
        elif action == "menu": self.change_scene("MENU")
        elif action == "next_level":
            if self.level_index < len(LEVELS) - 1:
                self.unlocked_levels = max(self.unlocked_levels, self.level_index + 2)
                self.begin_level(self.level_index + 1)
                self.change_scene("PLAYING")
            else: self.change_scene("VICTORY")
        elif action == "victory": self.change_scene("VICTORY")
        elif action == "quit": self.quit()

    def update_slider(self, mouse_x):
        value = clamp((mouse_x - 350) / 400, 0.0, 1.0)
        if self.slider_drag == "music": self.audio.set_music(value)
        elif self.slider_drag == "sfx": self.audio.set_sfx(value)

    def handle_mouse_down(self, pos):
        if self.scene == "MENU":
            for action in ("mode_0", "mode_1", "mode_2", "settings", "quit"):
                rect = self.button_cache.get(action, {}).get("rect")
                if rect and rect.collidepoint(pos):
                    self.audio.play("click")
                    self.handle_button_action(action)
                    return
        if self.scene == "CHARACTER_SELECT":
            if self.select.handle_click(pos): return
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
            if event.type == pygame.QUIT: self.quit()
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = self.convert_mouse(event.pos)
                if self.slider_drag: self.update_slider(self.mouse_pos[0])
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.slider_drag = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_pos = self.convert_mouse(event.pos)
                self.handle_mouse_down(self.mouse_pos)
            elif event.type == pygame.KEYUP:
                if self.scene == "PLAYING" and self.game_mode == 0 and self.player:
                    if event.key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE): self.player.cut_jump()
            elif event.type == pygame.KEYDOWN:
                if self.scene == "MENU":
                    if event.key == pygame.K_s:
                        self.settings_return = "MENU"
                        self.change_scene("SETTINGS")
                    elif event.key == pygame.K_ESCAPE: self.quit()
                    elif event.key == pygame.K_1: self.handle_button_action("mode_0")
                    elif event.key == pygame.K_2: self.handle_button_action("mode_1")
                    elif event.key == pygame.K_3: self.handle_button_action("mode_2")
                elif self.scene == "CHARACTER_SELECT": self.select.handle_key(event.key)
                elif self.scene == "SETTINGS" and event.key == pygame.K_ESCAPE: self.change_scene(self.settings_return)
                elif self.scene == "PLAYING" and self.game_mode == 0:
                    if event.key in (pygame.K_ESCAPE, pygame.K_p): self.change_scene("PAUSED")
                    if event.key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE): self.player.request_jump()
                elif self.scene in ("PAUSED", "PLACEHOLDER_GAME") and event.key == pygame.K_ESCAPE: self.change_scene("MENU")
                elif self.scene in ("LEVEL_COMPLETE", "GAME_OVER", "VICTORY"):
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.scene == "LEVEL_COMPLETE": self.handle_button_action("next_level" if self.level_index < len(LEVELS) - 1 else "victory")
                        else: self.start_game(0)
                    elif event.key == pygame.K_ESCAPE: self.change_scene("MENU")

    def quit(self):
        pygame.quit()
        raise SystemExit

    def run(self):
        while True:
            self.dt_scale = clamp(config.clock.tick(FPS) / (1000.0 / FPS), 0.35, 2.5)
            self.frame += self.dt_scale
            self.mouse_pos = self.convert_mouse(pygame.mouse.get_pos())
            self.handle_events()
            if self.scene == "PLAYING" and self.game_mode == 0: self.update_gameplay()
            self.draw_scene()
            vp = self.get_viewport_rect()
            if vp.size == (WIDTH, HEIGHT) and vp.topleft == (0, 0): config.screen.blit(config.canvas, (0, 0))
            else:
                config.screen.fill((4, 8, 16))
                config.screen.blit(pygame.transform.smoothscale(config.canvas, vp.size), vp.topleft)
            pygame.display.flip()


SceneManager = Game