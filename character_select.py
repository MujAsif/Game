"""
CHARACTER SELECT — The company roster screen.
Six animated cards, a detail ledger with live stats, portrait, run preview,
keyboard + mouse navigation, staggered entrance, and launch buttons.
"""
import math
import pygame

import config
from config import (WIDTH, HEIGHT, GROUND_Y, INK, WHITE, MUTED, SUBTLE,
                    GOLD, GOLD_SOFT, MINT, CORAL, BLUE, fonts)
from ui import (draw_text, wrap_text, panel, draw_pill, veil, get_radial_glow,
                clamp, blend_color)
from sprites import bank, ROSTER

CARD_W, CARD_H, CARD_GAP = 160, 258, 14
CARD_X0, CARD_Y = 35, 136
CARD_SPRITE_H = 112
DETAIL_RECT = (35, 410, 1030, 158)


def draw_fallback_hero(surface, ch, cx, bottom, height, frame=0.0, facing=1):
    """Tiny procedural stand-in used only when sprite sheets are absent."""
    s = height / 78.0
    c = ch["colors"]
    y = bottom - height
    bob = math.sin(frame * 0.08) * 2 * s
    yy = int(y + bob)
    sh = pygame.Surface((int(34 * s), int(8 * s)), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (6, 12, 22, 120), sh.get_rect())
    surface.blit(sh, (cx - sh.get_width() // 2, bottom - sh.get_height() // 2))
    pygame.draw.line(surface, c["scarf"], (cx, yy + int(24 * s)),
                     (cx - facing * int(20 * s), yy + int(30 * s)), max(2, int(5 * s)))
    pygame.draw.rect(surface, c["pants"], (cx - int(7 * s), yy + int(48 * s),
                                           int(14 * s), int(26 * s)), border_radius=int(4 * s))
    pygame.draw.rect(surface, c["jacket"], (cx - int(10 * s), yy + int(24 * s),
                                            int(20 * s), int(26 * s)), border_radius=int(6 * s))
    pygame.draw.rect(surface, c["scarf"], (cx - int(8 * s), yy + int(22 * s),
                                           int(16 * s), int(5 * s)), border_radius=int(2 * s))
    pygame.draw.circle(surface, (236, 194, 162), (cx, yy + int(12 * s)), int(10 * s))
    if ch["style"] == "hat":
        pygame.draw.polygon(surface, c["jacket"], [(cx - int(13 * s), yy + int(6 * s)),
                                                   (cx + int(13 * s), yy + int(6 * s)),
                                                   (cx + facing * int(3 * s), yy - int(12 * s))])
    elif ch["style"] == "hood":
        pygame.draw.circle(surface, c["jacket"], (cx, yy + int(10 * s)), int(11 * s))
        pygame.draw.circle(surface, (236, 194, 162), (cx + facing * int(3 * s), yy + int(12 * s)), int(6 * s))
    else:
        pygame.draw.ellipse(surface, c["hair"], (cx - int(10 * s), yy + int(2 * s),
                                                 int(20 * s), int(10 * s)))
        if ch["style"] == "ponytail":
            pygame.draw.line(surface, c["hair"], (cx - facing * int(8 * s), yy + int(6 * s)),
                             (cx - facing * int(17 * s), yy + int(22 * s)), max(2, int(4 * s)))
    pygame.draw.circle(surface, (32, 38, 50), (cx + facing * int(4 * s), yy + int(12 * s)), max(1, int(2 * s)))


class CharacterSelect:
    def __init__(self, game):
        self.game = game
        self.intro = 0.0
        self.pulse = 0.0
        self.hover = -1
        self.card_rects = []
        self._last_click = (-1, -999.0)

    # ── input ────────────────────────────────────────────────────
    def _move(self, delta):
        g = self.game
        g.selected_character = (g.selected_character + delta) % len(ROSTER)
        g.character = ROSTER[g.selected_character]
        self.pulse = 1.0
        g.audio.play("click")

    def _pick(self, idx):
        g = self.game
        if idx != g.selected_character:
            g.selected_character = idx
            g.character = ROSTER[idx]
            self.pulse = 1.0
            g.audio.play("click")

    def handle_key(self, key):
        if key in (pygame.K_LEFT, pygame.K_a):
            self._move(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self._move(1)
        elif key in (pygame.K_1, pygame.K_KP1): self._pick(0)
        elif key in (pygame.K_2, pygame.K_KP2): self._pick(1)
        elif key in (pygame.K_3, pygame.K_KP3): self._pick(2)
        elif key in (pygame.K_4, pygame.K_KP4): self._pick(3)
        elif key in (pygame.K_5, pygame.K_KP5): self._pick(4)
        elif key in (pygame.K_6, pygame.K_KP6): self._pick(5)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            self.game.handle_button_action("begin_run")
        elif key == pygame.K_ESCAPE:
            self.game.handle_button_action("select_back")
        return True

    def handle_click(self, pos):
        for i, r in enumerate(self.card_rects):
            if r.collidepoint(pos):
                if self._last_click[0] == i and self.game.frame - self._last_click[1] < 26:
                    self.game.handle_button_action("begin_run")
                else:
                    self._pick(i)
                    self._last_click = (i, self.game.frame)
                return True
        return False

    # ── drawing ──────────────────────────────────────────────────
    def draw(self):
        g = self.game
        cv = config.canvas
        self.intro += g.dt_scale
        self.pulse = max(0.0, self.pulse - 0.05 * g.dt_scale)

        g.world_scenery(cv, g.frame)
        cv.blit(veil(150), (0, 0))

        draw_text(cv, "CHOOSE YOUR TRAVELER", fonts.LARGE, WHITE, (WIDTH // 2, 62), center=True, shadow=True)
        draw_text(cv, "Six companions walk the trials — each with a gift of their own.",
                  fonts.BODY, MUTED, (WIDTH // 2, 106), center=True)

        self.hover = -1
        self.card_rects = []
        for i, ch in enumerate(ROSTER):
            r = pygame.Rect(CARD_X0 + i * (CARD_W + CARD_GAP), CARD_Y, CARD_W, CARD_H)
            self.card_rects.append(r)
            if r.collidepoint(g.mouse_pos):
                self.hover = i

        for i, ch in enumerate(ROSTER):
            self._draw_card(ch, i)

        self._draw_detail()

        g.make_button("select_begin", (886, 436, 164, 50), "SET FORTH", "begin_run", GOLD)
        g.make_button("select_back", (886, 498, 164, 42), "BACK", "select_back", BLUE)

        draw_text(cv, "← →  CHOOSE      1–6  QUICK PICK      ENTER  BEGIN      ESC  BACK",
                  fonts.TINY, MUTED, (WIDTH // 2, 598), center=True)
        if not bank.ready:
            draw_text(cv, bank.status or "SPRITE SHEETS NOT LOADED",
                      fonts.TINY, CORAL, (WIDTH // 2, 622), center=True)

    def _draw_card(self, ch, i):
        g = self.game
        cv = config.canvas
        base = self.card_rects[i]
        selected = (i == g.selected_character)
        hovered = (i == self.hover)

        e = clamp((self.intro - i * 4.0) / 22.0, 0.0, 1.0)
        ease = 1.0 - (1.0 - e) ** 3
        lift = int((1.0 - ease) * 26) + (4 if hovered and not selected else 0) + (6 if selected else 0)
        r = base.move(0, -lift)

        border = (*GOLD, 220) if selected else ((*ch["accent"], 190) if hovered else (110, 138, 166, 80))
        fill = (24, 38, 58, 240) if selected else ((20, 32, 50, 232) if hovered else (15, 25, 40, 224))
        panel(cv, r, fill, border, 18, True)
        if selected:
            pygame.draw.rect(cv, GOLD, r, 2, border_radius=18)
            glow_a = int(40 + 26 * self.pulse + 8 * math.sin(g.frame * 0.09))
            cv.blit(get_radial_glow(58, ch["accent"], clamp(glow_a, 20, 90), 5),
                    (r.centerx - 58, r.y + 96 - 58))

        draw_text(cv, str(i + 1), fonts.TINY, GOLD_SOFT if selected else SUBTLE, (r.x + 14, r.y + 12))

        feet = r.y + 158
        if bank.has(ch["id"]):
            if selected:
                n = bank.count(ch["id"], "run")
                idx = int(g.frame * 0.22) % n
                bank.draw(cv, ch["id"], "run", idx, r.centerx, feet, CARD_SPRITE_H, facing=1)
            else:
                n = bank.count(ch["id"], "idle")
                idx = int(g.frame * 0.07 + i * 1.7) % n
                bank.draw(cv, ch["id"], "idle", idx, r.centerx, feet, CARD_SPRITE_H, facing=1)
        else:
            draw_fallback_hero(cv, ch, r.centerx, feet, CARD_SPRITE_H, g.frame + i * 20)

        draw_text(cv, ch["name"], fonts.SMALL, WHITE if (selected or hovered) else MUTED,
                  (r.centerx, r.y + 176), center=True)
        draw_text(cv, ch["title"].upper(), fonts.TINY, SUBTLE, (r.centerx, r.y + 196), center=True)
        pygame.draw.line(cv, (255, 255, 255, 26), (r.x + 22, r.y + 212), (r.right - 22, r.y + 212), 1)
        draw_text(cv, ch["perk"], fonts.TINY, ch["accent"], (r.centerx, r.y + 226), center=True)

        if selected:
            rib = pygame.Rect(r.centerx - 42, r.y - 11, 84, 22)
            draw_pill(cv, rib, (*GOLD, 235), (*GOLD_SOFT, 255), shadow=False)
            draw_text(cv, "CHOSEN", fonts.TINY, INK, rib.center, center=True)

    def _draw_detail(self):
        g = self.game
        cv = config.canvas
        ch = ROSTER[g.selected_character]
        panel(cv, DETAIL_RECT, (15, 25, 40, 238), (*ch["accent"], 120), 22, True)

        cv.blit(get_radial_glow(72, ch["accent"], 46, 5), (120 - 72, 486 - 72))
        if bank.has(ch["id"]):
            bank.draw_portrait(cv, ch["id"], 120, 552, 132, facing=1)
        else:
            draw_fallback_hero(cv, ch, 120, 552, 128, g.frame)

        draw_text(cv, ch["name"], fonts.FONT, WHITE, (200, 428), shadow=True)
        draw_text(cv, ch["title"], fonts.SMALL, ch["accent"], (200, 460))
        y = 490
        for line in wrap_text(ch["perk_desc"], fonts.BODY, 430)[:2]:
            draw_text(cv, line, fonts.BODY, (208, 220, 234), (200, y))
            y += 26

        if bank.has(ch["id"]):
            n = bank.count(ch["id"], "run")
            bank.draw(cv, ch["id"], "run", int(g.frame * 0.24) % n, 655, 552, 92, facing=1)
            if int(g.frame) % 7 == 0:
                pygame.draw.circle(cv, (*ch["accent"], 90),
                                   (655 - 30 - int((g.frame * 2) % 22), 548), 2)
        else:
            draw_fallback_hero(cv, ch, 655, 552, 90, g.frame * 2)

        sy = 436
        for label, val in ch["stats"].items():
            draw_text(cv, label, fonts.TINY, MUTED, (712, sy), valign="middle")
            for k in range(5):
                px = 792 + k * 15
                if k < val:
                    pygame.draw.circle(cv, ch["accent"], (px, sy), 5)
                    pygame.draw.circle(cv, blend_color(ch["accent"], WHITE, 0.5), (px - 1, sy - 1), 1)
                else:
                    pygame.draw.circle(cv, SUBTLE, (px, sy), 4, 1)
            sy += 30