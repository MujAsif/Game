"""
ENTITIES — Player character, Particle system, and FloatingText popups.
The Player renders from the sprite bank when available, with a procedural
fallback (recolored + styled per character) when it is not.
"""
import pygame
import math
import random

import config
from config import (WIDTH, HEIGHT, GROUND_Y, MOVE_SPEED, JUMP_SPEED,
                    ACCEL_GROUND, ACCEL_AIR, FRICTION_GROUND, FRICTION_AIR,
                    WHITE, GOLD, fonts)
from ui import clamp, lerp, blend_color
from sprites import bank, ROSTER


class Particle:
    """Small visual effect: dust puff, sparkle, or expanding ring."""

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

    def update(self, dt=1.0):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.vx *= 0.985 ** dt
        if self.ring:
            self.size += 1.5 * dt
        self.life -= dt

    def draw(self, surface):
        ratio = clamp(self.life / max(1.0, self.max_life), 0.0, 1.0)
        if self.ring:
            r = max(2, int(self.size))
            rs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(rs, (*self.color[:3], int(140 * ratio)),
                                (2, max(2, r // 2), r * 2, max(4, r)), 2)
            surface.blit(rs, (int(self.x - r - 2), int(self.y - r)))
            return
        radius = max(1, int(self.size * ratio + 0.5))
        color = tuple(int(c * (0.48 + 0.52 * ratio)) for c in self.color[:3])
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), radius)


class FloatingText:
    """Score/feedback popup that floats upward and fades out."""

    def __init__(self, text, x, y, color=GOLD):
        self.text, self.x, self.y, self.color, self.life = text, float(x), float(y), color, 64.0

    def update(self, dt=1.0):
        self.y -= 0.68 * dt
        self.life -= dt

    def draw(self, surface):
        alpha = int(255 * clamp(self.life / 22.0, 0.0, 1.0))
        shade = fonts.SMALL.render(self.text, True, (6, 11, 20))
        shade.set_alpha(alpha)
        img = fonts.SMALL.render(self.text, True, self.color)
        img.set_alpha(alpha)
        r = img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(shade, r.move(1, 2))
        surface.blit(img, r)


class Player:
    """
    Climber hero. Sprite-sheet animation (idle / walk / run / air / crouch)
    with a procedural fallback, physics-driven scarf, and landing squash.
    Character traits (speed, glide, …) are applied by the game orchestrator.
    """

    def __init__(self, character=None):
        self.character = character or ROSTER[0]
        self.cid = self.character["id"]
        traits = self.character.get("traits", {})
        self.speed_mul = traits.get("speed_mul", 1.0)
        self.accel_mul = traits.get("accel_mul", 1.0)
        self.max_speed = MOVE_SPEED * self.speed_mul
        self.can_glide = bool(traits.get("glide", False))

        self.w, self.h = 32, 54
        self.x, self.y = 64.0, float(GROUND_Y - self.h)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        self.vx = self.vel_y = 0.0
        self.on_ground = True
        self.facing = 1
        self.walking = False
        self.gliding = False
        self.air_phase = 0
        self.anim = self.land_squash = self.coyote_timer = self.jump_buffer = self.hurt_timer = 0.0
        self.scarf_points = [(self.x + 16, self.y + 22) for _ in range(4)]
        self.state_timers = {"idle": 0.0, "walk": 0.0, "run": 0.0, "air": 0.0, "crouch": 0.0}
        self.anim_state_name = "idle"

    def sync_rect(self):
        self.rect.topleft = (int(round(self.x)), int(round(self.y)))

    def request_jump(self):
        self.jump_buffer = 7.0

    def execute_jump(self, particles, audio):
        self.vel_y = JUMP_SPEED
        self.on_ground = False
        self.gliding = False
        self.air_phase = 0
        self.coyote_timer = self.jump_buffer = 0.0
        particles.append(Particle(self.rect.centerx, self.rect.bottom, (205, 232, 235), ring=True))
        for _ in range(9):
            particles.append(Particle(self.rect.centerx, self.rect.bottom, (200, 226, 230), dust=True))
        audio.play("jump")

    def cut_jump(self):
        if self.vel_y < -5.5:
            self.vel_y *= 0.56

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

    def update_scarf(self, dt=1.0):
        self.scarf_points[0] = (self.x + self.w * 0.5 - self.facing * 3, self.y + 22)
        for i in range(1, len(self.scarf_points)):
            px, py = self.scarf_points[i - 1]
            cx, cy = self.scarf_points[i]
            tx = px - self.facing * 5.2 - self.vx * 0.35
            ty = py + 1.2 - self.vel_y * 0.12 + math.sin(self.anim * 0.35 + i * 1.1) * 1.1
            t = clamp(0.36 * dt, 0.0, 1.0)
            self.scarf_points[i] = (lerp(cx, tx, t), lerp(cy, ty, t))

        state = self.anim_state()
        self.anim_state_name = state
        rate = {"idle": 0.075, "walk": 0.15, "run": 0.22, "air": 0.1, "crouch": 0.18}[state]
        if state == "walk":
            rate *= clamp(abs(self.vx) / self.max_speed, 0.4, 1.2)
        self.state_timers[state] += dt * rate

    # ── rendering ────────────────────────────────────────────────
    def draw(self, surface, frame, shadow_surface_y):
        self.sync_rect()
        rect, cx = self.rect, self.rect.centerx

        d = max(0.0, shadow_surface_y - rect.bottom)
        sc = clamp(1.0 - d / 220.0, 0.35, 1.0)
        sw, sh = max(12, int(30 * sc)), max(4, int(7 * sc))
        ss = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.ellipse(ss, (6, 12, 22, int(130 * sc)), ss.get_rect())
        surface.blit(ss, (cx - sw // 2, int(shadow_surface_y) - sh // 2))

        hurt = self.hurt_timer > 0 and int(frame / 4) % 2 == 0

        if bank.has(self.cid):
            state = self.anim_state_name
            n = bank.count(self.cid, state)
            if state == "air":
                # Hysteresis: hold the apex pose until clearly rising / falling.
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

        self._draw_procedural(surface, frame, rect, cx, hurt)

    def _draw_procedural(self, surface, frame, rect, cx, hurt):
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

        pts = [(int(px), int(py)) for px, py in self.scarf_points]
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
            pygame.draw.rect(surface, boots, (foot_x - 4 + self.facing, foot_y - 2, 9, 5), border_radius=2)

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
                pygame.draw.rect(surface, (210, 222, 238), (cx - 10, y + 3, 20, 4), border_radius=2)
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