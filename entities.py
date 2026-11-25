"""
ENTITIES — Player, Particle, FloatingText, MovingPlatform.
All physics is per fixed 60 Hz step (no dt scaling).
Draw methods take a camera offset and never mutate world positions.
"""
import pygame
import math
import random
import config
from config import (GROUND_Y, MOVE_SPEED, JUMP_SPEED, TILE, WHITE, GOLD,
                    PLAYER_W, PLAYER_H, COYOTE_FRAMES, JUMP_BUFFER_FRAMES,
                    JUMP_CUT_THRESHOLD, JUMP_CUT_FACTOR, GLIDE_FRAMES,
                    DROP_THROUGH_FRAMES)
from ui import clamp, lerp, blend_color, get_text_image
from sprites import bank, ROSTER

_RING_CACHE = {}
_SHADOW_CACHE = {}
_MOVER_RANGE = 3 * TILE


def _ring_surface(radius, color, alpha):
    key = (radius, tuple(color[:3]), alpha // 16)
    hit = _RING_CACHE.get(key)
    if hit is not None:
        return hit
    rs = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
    pygame.draw.ellipse(rs, (*color[:3], alpha),
                        (2, max(2, radius // 2), radius * 2, max(4, radius)), 2)
    if len(_RING_CACHE) > 200:
        _RING_CACHE.clear()
    _RING_CACHE[key] = rs
    return rs


def _shadow_surface(w, h, alpha):
    key = (w, h, alpha // 10)
    hit = _SHADOW_CACHE.get(key)
    if hit is not None:
        return hit
    ss = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(ss, (6, 12, 22, alpha), ss.get_rect())
    if len(_SHADOW_CACHE) > 120:
        _SHADOW_CACHE.clear()
    _SHADOW_CACHE[key] = ss
    return ss


class Particle:
    """Dust puff, sparkle, or expanding ring."""

    def __init__(self, x, y, color, power=3.6, dust=False, ring=False):
        self.x, self.y, self.color, self.ring = float(x), float(y), color, ring
        if ring:
            self.vx = self.vy = self.gravity = 0.0
            self.life = self.max_life = 18.0
            self.size = 5.0
        else:
            self.vx = random.uniform(-1.5, 1.5) if dust else random.uniform(-power, power)
            self.vy = random.uniform(-1.4, -0.2) if dust else random.uniform(-power * 1.45, -0.4)
            self.gravity = 0.03 if dust else 0.14
            self.life = float(random.randint(18, 28) if dust else random.randint(24, 44))
            self.max_life = self.life
            self.size = random.uniform(1.6, 3.2) if dust else random.uniform(2.0, 4.4)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= 0.985
        if self.ring:
            self.size += 1.5
        self.life -= 1.0

    def draw(self, surface, cam_x=0, cam_y=0):
        ratio = clamp(self.life / max(1.0, self.max_life), 0.0, 1.0)
        sx, sy = self.x - cam_x, self.y - cam_y
        if self.ring:
            r = max(2, int(self.size))
            surface.blit(_ring_surface(r, self.color, int(140 * ratio)),
                         (int(sx - r - 2), int(sy - r)))
            return
        radius = max(1, int(self.size * ratio + 0.5))
        color = tuple(int(c * (0.48 + 0.52 * ratio)) for c in self.color[:3])
        pygame.draw.circle(surface, color, (int(sx), int(sy)), radius)


class FloatingText:
    """Feedback popup that floats up and fades. Glyphs cached once."""

    def __init__(self, text, x, y, color=GOLD):
        self.text, self.x, self.y, self.color = text, float(x), float(y), color
        self.life = 64.0
        # copies: set_alpha must not leak into the shared text cache
        self._img = get_text_image(text, config.fonts.SMALL, color).copy()
        self._shade = get_text_image(text, config.fonts.SMALL, (6, 11, 20)).copy()

    def update(self):
        self.y -= 0.68
        self.life -= 1.0

    def draw(self, surface, cam_x=0, cam_y=0):
        alpha = int(255 * clamp(self.life / 22.0, 0.0, 1.0))
        r = self._img.get_rect(center=(int(self.x - cam_x), int(self.y - cam_y)))
        self._shade.set_alpha(alpha)
        self._img.set_alpha(alpha)
        surface.blit(self._shade, r.move(1, 2))
        surface.blit(self._img, r)


class MovingPlatform:
    """Question-gated mover.

    Starts LOCKED and parked at its start point. Once activate() is called
    (right answer) it ping-pongs between start and start + route, pausing at
    each end so the player can board. Routes may be horizontal, vertical or
    diagonal. last_dx / last_dy are exact integer deltas for carrying.
    Without a route it falls back to the old ±3-tile sideways patrol.
    """

    SPEED = 2.0            # px per 60 Hz step along the route
    DWELL = 50             # frames parked at each end once active

    def __init__(self, x, y, tiles, route=None, locked=True):
        self.rect = pygame.Rect(int(x), int(y) + TILE - 14, int(tiles * TILE), 14)
        self.ax, self.ay = float(self.rect.x), float(self.rect.y)
        if route is None:
            route, locked = (0, 0), False
            self._legacy = True
        else:
            self._legacy = False
        self.bx = self.ax + route[0] * TILE
        self.by = self.ay + route[1] * TILE
        self.length = math.hypot(self.bx - self.ax, self.by - self.ay)
        self.fx, self.fy = self.ax, self.ay
        self.t = 0.0                  # distance travelled from A toward B
        self.dir = 1
        self.wait = 0
        self.locked = locked
        self.pending_question = None  # question shown but not yet answered
        self.glow = 0.0               # flash after unlocking
        self.last_dx = self.last_dy = 0
        self.vx = 1.4                 # legacy patrol speed
        self._saved = (self.fx, self.fy, 0.0, 1, 0, self.vx, self.rect.x, self.rect.y)

    @property
    def route_end(self):
        return (self.bx, self.by)

    def activate(self):
        self.locked = False
        self.wait = 20
        self.glow = 1.0

    def undo(self):
        """Cancel this step's move (something is in the way): the mover waits."""
        (self.fx, self.fy, self.t, self.dir, self.wait, self.vx,
         self.rect.x, self.rect.y) = self._saved
        self.last_dx = self.last_dy = 0

    def update(self):
        prev_x, prev_y = self.rect.x, self.rect.y
        self._saved = (self.fx, self.fy, self.t, self.dir, self.wait, self.vx, prev_x, prev_y)
        self.glow = max(0.0, self.glow - 0.02)
        if self._legacy:
            nx = self.fx + self.vx
            if nx < self.ax - _MOVER_RANGE:
                nx, self.vx = self.ax - _MOVER_RANGE, abs(self.vx)
            elif nx > self.ax + _MOVER_RANGE:
                nx, self.vx = self.ax + _MOVER_RANGE, -abs(self.vx)
            self.fx = nx
        elif not self.locked and self.length > 0:
            if self.wait > 0:
                self.wait -= 1
            else:
                self.t += self.dir * self.SPEED
                if self.t >= self.length:
                    self.t, self.dir, self.wait = self.length, -1, self.DWELL
                elif self.t <= 0:
                    self.t, self.dir, self.wait = 0.0, 1, self.DWELL
                k = self.t / self.length
                # ease in/out so riders aren't jolted at the ends
                k = k * k * (3 - 2 * k)
                self.fx = self.ax + (self.bx - self.ax) * k
                self.fy = self.ay + (self.by - self.ay) * k
        self.rect.x = int(round(self.fx))
        self.rect.y = int(round(self.fy))
        self.last_dx = self.rect.x - prev_x
        self.last_dy = self.rect.y - prev_y


class Player:
    """Climber hero: sprite-bank animation with procedural fallback."""

    def __init__(self, character=None):
        self.character = character or ROSTER[0]
        self.cid = self.character["id"]
        traits = self.character.get("traits", {})

        # Every perk advertised in ROSTER is read here.
        self.speed_mul = traits.get("speed_mul", 1.0)
        self.accel_mul = traits.get("accel_mul", 1.0)
        self.jump_mul = traits.get("jump_mul", 1.0)
        self.invuln_bonus = traits.get("invuln_bonus", 0)
        self.coyote_max = COYOTE_FRAMES + traits.get("coyote_bonus", 0)
        self.buffer_max = JUMP_BUFFER_FRAMES + traits.get("buffer_bonus", 0)
        self.can_glide = bool(traits.get("glide", False))

        self.max_speed = MOVE_SPEED * self.speed_mul
        self.jump_speed = JUMP_SPEED * self.jump_mul

        self.w, self.h = PLAYER_W, PLAYER_H
        self.x, self.y = 64.0, float(GROUND_Y - self.h)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        self.vx = self.vel_y = 0.0
        self.on_ground = True
        self.on_one_way = False
        self.facing = 1
        self.walking = False
        self.gliding = False
        self.glide_fuel = GLIDE_FRAMES
        self.drop_timer = 0
        self.air_phase = 0
        self.anim = 0.0
        self.land_squash = 0.0
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.hurt_timer = 0.0
        self.invincible_timer = 0.0
        self.jump_cut_ready = False
        self.carried_by = None
        self.scarf_points = [(self.x + 16, self.y + 22) for _ in range(4)]
        self.state_timers = {"idle": 0.0, "walk": 0.0, "run": 0.0, "air": 0.0, "crouch": 0.0}
        self.anim_state_name = "idle"

    def reset_scarf(self):
        """Snap the scarf to the body after any teleport (respawn, checkpoint)."""
        self.scarf_points = [(self.x + 16, self.y + 22) for _ in range(4)]

    def sync_rect(self):
        self.rect.topleft = (int(round(self.x)), int(round(self.y)))

    def request_jump(self):
        self.jump_buffer = float(self.buffer_max)

    def drop_through(self):
        self.drop_timer = DROP_THROUGH_FRAMES
        self.on_ground = False
        self.on_one_way = False
        self.carried_by = None
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.y += 2.0
        self.sync_rect()

    def execute_jump(self, particles, audio):
        self.vel_y = self.jump_speed
        self.on_ground = False
        self.on_one_way = False
        self.gliding = False
        self.air_phase = 0
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.carried_by = None
        self.jump_cut_ready = True
        particles.append(Particle(self.rect.centerx, self.rect.bottom, (205, 232, 235), ring=True))
        for _ in range(9):
            particles.append(Particle(self.rect.centerx, self.rect.bottom, (200, 226, 230), dust=True))
        audio.play("jump")

    def cut_jump(self):
        if self.jump_cut_ready and self.vel_y < JUMP_CUT_THRESHOLD:
            self.vel_y *= JUMP_CUT_FACTOR
        self.jump_cut_ready = False

    def anim_state(self):
        if not self.on_ground:
            return "air"
        if self.land_squash > 0.45:
            return "crouch"
        if abs(self.vx) > 0.72 * self.max_speed:
            return "run"
        if self.walking:
            return "walk"
        return "idle"

    def update_scarf(self):
        self.scarf_points[0] = (self.x + self.w * 0.5 - self.facing * 3, self.y + 22)
        for i in range(1, len(self.scarf_points)):
            px, py = self.scarf_points[i - 1]
            cx, cy = self.scarf_points[i]
            tx = px - self.facing * 5.2 - self.vx * 0.35
            ty = py + 1.2 - self.vel_y * 0.12 + math.sin(self.anim * 0.35 + i * 1.1) * 1.1
            self.scarf_points[i] = (lerp(cx, tx, 0.36), lerp(cy, ty, 0.36))
        state = self.anim_state()
        self.anim_state_name = state
        rate = {"idle": 0.075, "walk": 0.15, "run": 0.22, "air": 0.1, "crouch": 0.18}[state]
        if state == "walk":
            rate *= clamp(abs(self.vx) / self.max_speed, 0.4, 1.2)
        self.state_timers[state] += rate

    def draw(self, surface, frame, shadow_surface_y, cam_x=0, cam_y=0):
        rect = self.rect.move(-int(cam_x), -int(cam_y))
        cx = rect.centerx
        d = max(0.0, (shadow_surface_y - cam_y) - rect.bottom)
        sc = clamp(1.0 - d / 220.0, 0.35, 1.0)
        sw, sh = max(12, int(30 * sc)), max(4, int(7 * sc))
        surface.blit(_shadow_surface(sw, sh, int(130 * sc)),
                     (cx - sw // 2, int(shadow_surface_y - cam_y) - sh // 2))
        hurt = self.hurt_timer > 0 and int(frame / 4) % 2 == 0
        if self.invincible_timer > 0 and int(frame / 3) % 2 == 0:
            return
        if bank.has(self.cid):
            state = self.anim_state_name
            n = bank.count(self.cid, state)
            if state == "air":
                if self.vel_y < -3.0:
                    self.air_phase = 0
                elif self.vel_y > 3.0:
                    self.air_phase = 2
                elif abs(self.vel_y) <= 1.5:
                    self.air_phase = 1
                idx = {0: 0, 1: n // 2, 2: n - 1}[self.air_phase]
            elif state == "crouch":
                idx = min(int(self.state_timers[state]), n - 1)
            else:
                idx = int(self.state_timers[state]) % n
            height = config.PLAYER_SPRITE_H * (1.0 - 0.10 * self.land_squash)
            bank.draw(surface, self.cid, state, idx, cx, rect.bottom + 2,
                      height, facing=self.facing, tint=hurt)
            return
        self._draw_procedural(surface, frame, rect, cx, hurt, cam_x, cam_y)

    def _draw_procedural(self, surface, frame, rect, cx, hurt, cam_x, cam_y):
        airborne = not self.on_ground
        speed_ratio = clamp(abs(self.vx) / MOVE_SPEED, 0.0, 1.0)
        bob = (math.sin(frame * 0.10) if (self.on_ground and not self.walking)
               else abs(math.sin(self.anim * 0.42)) * -1.8 * speed_ratio)
        y = int(round(rect.y + bob + self.land_squash * 2.5))
        col = self.character["colors"]
        style = self.character.get("style", "scarf")
        skin = (255, 165, 165) if hurt else (236, 194, 162)
        hair = col["hair"]
        jacket = (210, 88, 98) if hurt else col["jacket"]
        jacket_shade = blend_color(jacket, (0, 0, 0), 0.28)
        pants, boots, scarf = col["pants"], (72, 54, 48), col["scarf"]
        pts = [(int(px - cam_x), int(py - cam_y)) for px, py in self.scarf_points]
        pygame.draw.lines(surface, scarf, False, pts, 5)
        pygame.draw.circle(surface, scarf, pts[-1], 2)
        stride = (math.sin(self.anim * 0.42) * 7.5 * speed_ratio if not airborne
                  else (-4.0 if self.vel_y < 0 else 4.0))
        hip_y = y + 36
        for side, swing in ((-1, stride), (1, -stride)):
            hip_x = cx + side * 4
            foot_x = hip_x + int(round(swing))
            foot_y = y + 51 - (int(abs(swing) * 0.25) if not airborne else 0)
            knee = ((hip_x + foot_x) // 2 + self.facing * 2, (hip_y + foot_y) // 2)
            pygame.draw.line(surface, pants, (hip_x, hip_y), knee, 5)
            pygame.draw.line(surface, pants, knee, (foot_x, foot_y), 5)
            pygame.draw.rect(surface, boots, (foot_x - 4 + self.facing, foot_y - 2, 9, 5),
                             border_radius=2)
        arm_swing = -stride * 0.85
        shoulder_y = y + 23
        bh = (cx - self.facing * 3 - int(round(arm_swing)), y + 34)
        pygame.draw.line(surface, jacket_shade, (cx - self.facing * 4, shoulder_y), bh, 4)
        pygame.draw.circle(surface, skin, bh, 3)
        torso = pygame.Rect(cx - 9, y + 20, 18, 18)
        pygame.draw.rect(surface, jacket, torso, border_radius=6)
        pygame.draw.line(surface, blend_color(jacket, WHITE, 0.3),
                         (torso.left + 1, torso.top + 2), (torso.left + 1, torso.bottom - 2), 1)
        pygame.draw.rect(surface, scarf, (cx - 7, y + 19, 14, 4), border_radius=2)
        fh = (cx + self.facing * 3 + int(round(arm_swing)), y + 34)
        pygame.draw.line(surface, jacket, (cx + self.facing * 4, shoulder_y), fh, 4)
        pygame.draw.circle(surface, skin, fh, 3)
        if style == "hood":
            pygame.draw.circle(surface, jacket, (cx, y + 10), 11)
            pygame.draw.ellipse(surface, skin, (cx - 6 + self.facing * 2, y + 5, 12, 12))
        else:
            pygame.draw.ellipse(surface, skin, (cx - 9, y + 2, 18, 18))
            pygame.draw.ellipse(surface, hair, (cx - 10, y + 1, 20, 10))
            if self.facing > 0:
                pygame.draw.rect(surface, hair, (cx - 10, y + 5, 6, 9), border_radius=3)
            else:
                pygame.draw.rect(surface, hair, (cx + 4, y + 5, 6, 9), border_radius=3)
            if style == "ponytail":
                pygame.draw.line(surface, hair, (cx - self.facing * 8, y + 6),
                                 (cx - self.facing * 16, y + 20), 4)
                pygame.draw.circle(surface, hair, (cx - self.facing * 16, y + 20), 3)
            elif style == "knight":
                pygame.draw.rect(surface, (210, 222, 238), (cx - 10, y + 3, 20, 4),
                                 border_radius=2)
            elif style == "hat":
                pygame.draw.polygon(surface, jacket, [(cx - 13, y + 5), (cx + 13, y + 5),
                                                      (cx + self.facing * 3, y - 12)])
                pygame.draw.line(surface, scarf, (cx - 12, y + 5), (cx + 12, y + 5), 2)
        ex, ey = cx + self.facing * 4, y + 11
        if int(frame) % 180 < 5:
            pygame.draw.line(surface, (35, 42, 54), (ex - 2, ey), (ex + 2, ey), 2)
        else:
            pygame.draw.circle(surface, (32, 38, 50), (ex, ey), 2)
            pygame.draw.circle(surface, WHITE, (ex + (1 if self.facing > 0 else 0), ey - 1), 1)