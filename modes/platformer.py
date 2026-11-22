"""
MODES/PLATFORMER — "The Ascent" gameplay logic.
Handles physics, collision, quiz UI, and world rendering.
"""
import pygame
import math
import random
import config
from config import (WIDTH, HEIGHT, GROUND_Y, INK, WHITE, MUTED, SUBTLE,
                    GOLD, GOLD_SOFT, MINT, CORAL, MAX_HEARTS,
                    QUESTIONS_PER_REGION, STEP_HEIGHTS, PILLAR_BLOCK, PILLAR_W,
                    GRAVITY, MAX_FALL_SPEED, MOVE_SPEED, ACCEL_GROUND, ACCEL_AIR,
                    FRICTION_GROUND, FRICTION_AIR, fonts)
from data import LEVELS, LEVEL_THEMES, make_question_deck
from ui import draw_text, wrap_text, gradient_rect, draw_pill, panel, get_radial_glow, veil, clamp, blend_color, lerp
from entities import Player, Particle, FloatingText

class PlatformerMode:
    def __init__(self, manager):
        self.manager = manager
        self.stats = {"lives": MAX_HEARTS, "score": 0, "combo": 0, "best_combo": 0}
        self.level_index = 0
        self.begin_level(0)

    def begin_level(self, level_index):
        self.level_index = int(clamp(level_index, 0, len(LEVELS) - 1))
        level = LEVELS[self.level_index]
        self.theme = LEVEL_THEMES[self.level_index]
        self.topic = level["topic"]
        self.manager.bg_base = self.manager.make_background() # Regenerate bg
        
        self.player = Player()
        self.platforms = []
        for i in range(QUESTIONS_PER_REGION):
            step = STEP_HEIGHTS[i]
            self.platforms.append({
                "x": 200 + i * PILLAR_W, "w": PILLAR_W,
                "target": float(step), "height": float(step + PILLAR_BLOCK),
                "solved": False, "played_sound": False, "hit_ground": False,
            })
        self.summit_ledge = pygame.Rect(800, GROUND_Y - 260, 200, 260)
        self.flag_rect = pygame.Rect(892, GROUND_Y - 348, 56, 88)
        self.beacon_rect = None
        self.deck = make_question_deck(level["questions"])
        self.q_index = self.current = 0
        self.question, self.asking = None, False
        self.answer_feedback_timer = 0.0
        self.selected_answer, self.last_answer_ok = None, False
        self.beacon_cooldown = self.shake = self.win_timer = 0.0
        self.particles, self.popups = [], []
        self.score_display = float(self.stats["score"])

    # ── Update Loop ─────────────────────────────────────────────
    def update(self):
        if self.beacon_cooldown > 0: self.beacon_cooldown = max(0.0, self.beacon_cooldown - self.manager.dt_scale)
        if self.asking:
            if self.selected_answer is not None and self.answer_feedback_timer > 0:
                self.answer_feedback_timer = max(0.0, self.answer_feedback_timer - self.manager.dt_scale)
                if self.answer_feedback_timer == 0: self.close_question()
        elif self.win_timer == 0:
            self.update_player()
            
        # Update pillars
        for p in self.platforms:
            if p["solved"] and p["height"] > p["target"]:
                if not p["played_sound"]:
                    self.manager.audio.play("lower")
                    p["played_sound"] = True
                old_top = GROUND_Y - p["height"]
                p["height"] = max(p["height"] - max(1.0, (p["height"] - p["target"]) * 0.08) * self.manager.dt_scale, p["target"])
                new_top = GROUND_Y - p["height"]
                # Carry player
                if new_top - old_top > 0 and self.player.vel_y >= 0:
                    if (self.player.rect.right > p["x"] and self.player.rect.left < p["x"] + p["w"] and abs(self.player.rect.bottom - old_top) <= 4):
                        self.player.rect.bottom = int(round(new_top))
                        self.player.y = float(self.player.rect.y)
                        self.player.on_ground = True
                        self.player.vel_y = 0.0
                if p["height"] <= p["target"] + 0.5 and not p["hit_ground"]:
                    p["hit_ground"] = True
                    self.shake = 6.0
                    self.manager.audio.play("land")

        # Victory check
        if self.win_timer == 0 and self.player.rect.colliderect(self.flag_rect):
            self.win_timer = 95.0
            bonus = 50 * self.stats["lives"]
            self.stats["score"] += bonus
            self.add_popup(f"SUMMIT REACHED +{bonus}", WIDTH // 2, 210, MINT)
            self.manager.audio.play("level")
            
        if self.win_timer > 0:
            self.win_timer = max(0.0, self.win_timer - self.manager.dt_scale)
            if self.win_timer == 0:
                self.manager.change_scene("LEVEL_COMPLETE") # You'll need to handle this in manager
                
        if self.stats["lives"] <= 0 and not self.asking:
            self.manager.change_scene("GAME_OVER")

        # Update particles
        for pt in self.particles[:]:
            pt.update(self.manager.dt_scale)
            if pt.life <= 0: self.particles.remove(pt)
        for pp in self.popups[:]:
            pp.update(self.manager.dt_scale)
            if pp.life <= 0: self.popups.remove(pp)

    # ── Physics & Collision ─────────────────────────────────────
    def update_player(self):
        player = self.player
        keys = pygame.key.get_pressed()
        move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        if move:
            player.facing = move
            player.vx = clamp(player.vx + move * (ACCEL_GROUND if player.on_ground else ACCEL_AIR) * self.manager.dt_scale, -MOVE_SPEED, MOVE_SPEED)
        else:
            player.vx *= (FRICTION_GROUND if player.on_ground else FRICTION_AIR) ** self.manager.dt_scale
            if abs(player.vx) < 0.08: player.vx = 0.0
            
        player.walking = abs(player.vx) > 0.35
        if player.walking:
            player.anim += self.manager.dt_scale * (abs(player.vx) / MOVE_SPEED)
            
        solids = self.get_solid_rects()
        player.x = clamp(player.x + player.vx * self.manager.dt_scale, 0.0, float(WIDTH - player.w))
        player.sync_rect()
        
        # X Collision
        for s in solids:
            if player.rect.colliderect(s):
                step_up = player.rect.bottom - s.top
                if 0 < step_up <= 10 and player.vel_y >= 0:
                    player.rect.bottom = s.top
                    player.y = float(player.rect.y)
                    player.on_ground = True
                else:
                    if player.vx > 0: player.rect.right = s.left
                    elif player.vx < 0: player.rect.left = s.right
                    player.x = float(player.rect.x)
                    player.vx = 0.0
                    
        # Y Collision
        was_ground = player.on_ground
        player.coyote_timer = 7.0 if was_ground else max(0.0, player.coyote_timer - self.manager.dt_scale)
        if player.jump_buffer > 0:
            player.jump_buffer = max(0.0, player.jump_buffer - self.manager.dt_scale)
            if player.on_ground or player.coyote_timer > 0:
                player.execute_jump(self.particles, self.manager.audio)
                
        prev_bottom = player.rect.bottom
        player.vel_y = min(player.vel_y + GRAVITY * self.manager.dt_scale, MAX_FALL_SPEED)
        player.y += player.vel_y * self.manager.dt_scale
        player.sync_rect()
        player.on_ground = False
        landed = False
        
        if player.rect.bottom >= GROUND_Y:
            player.rect.bottom = GROUND_Y
            player.y = float(player.rect.y)
            landed = True
        else:
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
                self.manager.audio.play("land")
            player.vel_y = 0.0
            player.on_ground = True
            if player.jump_buffer > 0: player.execute_jump(self.particles, self.manager.audio)
            
        player.land_squash = max(0.0, player.land_squash - 0.14 * self.manager.dt_scale)
        player.hurt_timer = max(0.0, player.hurt_timer - self.manager.dt_scale)
        player.update_scarf(self.manager.dt_scale)

    def get_solid_rects(self):
        solids = [pygame.Rect(p["x"], int(round(GROUND_Y - p["height"])), p["w"], HEIGHT) for p in self.platforms]
        solids.append(self.summit_ledge)
        return solids

    # ── Quiz Interaction ────────────────────────────────────────
    def beacon_center(self, p):
        return (p["x"] + p["w"] / 2, GROUND_Y - p["height"] - 40)
        
    def question_nearby(self):
        if self.current >= QUESTIONS_PER_REGION: return False
        bx, by = self.beacon_center(self.platforms[self.current])
        return (abs(self.player.rect.centerx - bx) <= 150 and abs(self.player.rect.centery - by) <= 220)
        
    def open_question(self):
        if self.current >= QUESTIONS_PER_REGION or self.asking or self.win_timer > 0 or self.beacon_cooldown > 0: return
        self.question = self.deck[self.q_index % len(self.deck)]
        self.asking = True
        self.selected_answer = None
        self.answer_feedback_timer = 0.0
        self.player.vx = 0.0
        self.manager.audio.play("click")
        
    def close_question(self):
        if not self.asking or self.selected_answer is None: return
        self.q_index += 1
        self.asking = False
        self.selected_answer = None
        self.answer_feedback_timer = 0.0
        self.beacon_cooldown = 55.0
        
    def answer_question(self, answer_index):
        if not self.asking or self.selected_answer is not None or answer_index not in range(4): return
        self.selected_answer = answer_index
        if answer_index == self.question["answer"]:
            self.last_answer_ok = True
            self.stats["combo"] += 1
            self.stats["best_combo"] = max(self.stats["best_combo"], self.stats["combo"])
            reward = 100 + self.stats["combo"] * 25
            self.stats["score"] += reward
            self.platforms[self.current]["solved"] = True
            self.current += 1
            self.add_particle_burst(self.player.rect.centerx, self.player.rect.centery, MINT, 26, 4.2)
            self.add_popup(f"+{reward}", self.player.rect.centerx, self.player.rect.y - 16, GOLD)
            self.manager.audio.play("correct")
        else:
            self.last_answer_ok = False
            self.stats["lives"] = max(0, self.stats["lives"] - 1)
            self.stats["combo"] = 0
            self.player.hurt_timer = 48.0
            self.shake = 10.0
            self.add_particle_burst(self.player.rect.centerx, self.player.rect.centery, CORAL, 20, 3.8)
            self.manager.audio.play("wrong")
        self.answer_feedback_timer = 110.0

    # ── Helpers ─────────────────────────────────────────────────
    def add_particle_burst(self, x, y, color, count=20, power=4.0):
        if self.manager.settings["particles"]:
            self.particles.extend(Particle(x, y, color, power=power) for _ in range(count))
    def add_popup(self, text, x, y, color=GOLD):
        self.popups.append(FloatingText(text, x, y, color))

    # ── Drawing ─────────────────────────────────────────────────
    def draw(self):
        self.draw_game_world()
        if self.asking:
            self.draw_question_panel()

    def draw_game_world(self):
        # ... [Your existing draw_game_world logic here] ...
        # Use self.manager.frame instead of self.frame
        # Use self.manager.settings["particles"]
        pass

    def draw_question_panel(self):
        # ... [Your existing draw_question_panel logic here] ...
        pass

    # ── Input Delegation ────────────────────────────────────────
    def handle_click(self, pos):
        if self.asking:
            if self.selected_answer is not None:
                self.close_question()
                return
            for i, r in enumerate(getattr(self, "question_option_rects", [])):
                if r.collidepoint(pos):
                    self.answer_question(i)
                    return
            return
        if self.beacon_rect and self.beacon_rect.collidepoint(pos) and self.question_nearby():
            self.open_question()
            return

    def handle_key(self, key):
        if not self.asking and self.player:
            if key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE):
                self.player.request_jump()
            if key in (pygame.K_e, pygame.K_RETURN) and self.question_nearby():
                self.open_question()
        elif self.asking:
            if self.selected_answer is not None:
                if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e): self.close_question()
            elif key in (pygame.K_1, pygame.K_KP1, pygame.K_2, pygame.K_KP2, pygame.K_3, pygame.K_KP3, pygame.K_4, pygame.K_KP4):
                self.answer_question({pygame.K_1: 0, pygame.K_KP1: 0, pygame.K_2: 1, pygame.K_KP2: 1, pygame.K_3: 2, pygame.K_KP3: 2, pygame.K_4: 3, pygame.K_KP4: 3}[key])