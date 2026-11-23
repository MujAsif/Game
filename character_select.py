"""
CHARACTER SELECT — roster screen: engraved cards, accent rims,
animated scarf fallback heroes, stat pips with glow, live run preview.
"""
import math
import pygame
import config
from config import (WIDTH, INK, WHITE, MUTED, SUBTLE,
                    GOLD, GOLD_SOFT, CORAL, BLUE, fonts)
from ui import (draw_text, wrap_text, panel, draw_pill, veil, get_radial_glow,
                clamp, blend_color, gradient_rect)
from sprites import bank, ROSTER

CARD_W, CARD_H, CARD_GAP = 160, 258, 14
CARD_X0, CARD_Y = 35, 136
CARD_SPRITE_H = 112
DETAIL_RECT = (35, 410, 1030, 158)
_HERO_CACHE = {}


def _hero_shadow(w, h):
    key = (w, h)
    hit = _HERO_CACHE.get(key)
    if hit is None:
        hit = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(hit, (6, 12, 22, 130), hit.get_rect())
        if len(_HERO_CACHE) > 60:
            _HERO_CACHE.clear()
        _HERO_CACHE[key] = hit
    return hit


def draw_fallback_hero(surface, ch, cx, bottom, height, frame=0.0, facing=1):
    """Stylized vector hero: shaded jacket, animated scarf, styled hair."""
    s = height / 78.0
    c = ch["colors"]
    bob = math.sin(frame * 0.08) * 2 * s
    y = int(bottom - height + bob)
    sh = _hero_shadow(max(2, int(36 * s)), max(2, int(9 * s)))
    surface.blit(sh, (cx - sh.get_width() // 2, bottom - sh.get_height() // 2))
    wave = math.sin(frame * 0.15) * 3 * s
    pygame.draw.lines(surface, c["scarf"], False,
                      [(cx, y + int(26 * s)),
                       (cx - facing * int(10 * s), y + int(30 * s) + int(wave * 0.4)),
                       (cx - facing * int(20 * s), y + int(28 * s) + int(wave))],
                      max(2, int(5 * s)))
    stride = math.sin(frame * 0.22) * 4 * s
    for side, sw in ((-1, stride), (1, -stride)):
        pygame.draw.line(surface, c["pants"], (cx + side * int(4 * s), y + int(48 * s)),
                         (cx + side * int(4 * s) + int(sw), y + int(70 * s)), max(2, int(5 * s)))
        pygame.draw.rect(surface, (66, 50, 44),
                         (cx + side * int(4 * s) + int(sw) - int(4 * s), y + int(68 * s),
                          int(9 * s), int(5 * s)), border_radius=2)
    jacket_dark = blend_color(c["jacket"], (0, 0, 0), 0.30)
    pygame.draw.rect(surface, jacket_dark,
                     (cx - int(10 * s), y + int(24 * s), int(20 * s), int(26 * s)),
                     border_radius=int(6 * s))
    pygame.draw.rect(surface, c["jacket"],
                     (cx - int(10 * s), y + int(24 * s), int(14 * s), int(26 * s)),
                     border_radius=int(6 * s))
    pygame.draw.line(surface, blend_color(c["jacket"], WHITE, 0.35),
                     (cx - int(8 * s), y + int(27 * s)), (cx - int(8 * s), y + int(46 * s)),
                     max(1, int(s)))
    pygame.draw.rect(surface, c["scarf"],
                     (cx - int(8 * s), y + int(22 * s), int(16 * s), int(5 * s)), border_radius=2)
    pygame.draw.circle(surface, (236, 194, 162), (cx, y + int(12 * s)), int(10 * s))
    if ch["style"] == "hat":
        pygame.draw.polygon(surface, c["jacket"],
                            [(cx - int(13 * s), y + int(6 * s)), (cx + int(13 * s), y + int(6 * s)),
                             (cx + facing * int(3 * s), y - int(12 * s))])
        pygame.draw.line(surface, c["scarf"], (cx - int(12 * s), y + int(6 * s)),
                         (cx + int(12 * s), y + int(6 * s)), max(1, int(2 * s)))
    elif ch["style"] == "hood":
        pygame.draw.circle(surface, c["jacket"], (cx, y + int(10 * s)), int(11 * s))
        pygame.draw.circle(surface, (236, 194, 162), (cx + facing * int(3 * s), y + int(12 * s)),
                           int(6 * s))
    else:
        pygame.draw.ellipse(surface, c["hair"],
                            (cx - int(10 * s), y + int(1 * s), int(20 * s), int(10 * s)))
    if ch["style"] == "ponytail":
        pygame.draw.line(surface, c["hair"], (cx - facing * int(8 * s), y + int(6 * s)),
                         (cx - facing * int(17 * s), y + int(22 * s) + int(wave * 0.5)),
                         max(2, int(4 * s)))
    elif ch["style"] == "knight":
        pygame.draw.rect(surface, (210, 222, 238),
                         (cx - int(10 * s), y + int(3 * s), int(20 * s), int(4 * s)),
                         border_radius=2)
    pygame.draw.circle(surface, (32, 38, 50), (cx + facing * int(4 * s), y + int(12 * s)),
                       max(1, int(2 * s)))
    pygame.draw.circle(surface, WHITE, (cx + facing * int(4 * s) + 1, y + int(11 * s)), 1)


class CharacterSelect:
    def __init__(self, game):
        self.game = game
        self.intro = 0.0
        self.pulse = 0.0
        self.hover = -1
        self.card_rects = []
        self._last_click = (-1, -999.0)

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

    def draw(self):
        g = self.game
        cv = config.canvas
        self.intro += g.dt_scale
        self.pulse = max(0.0, self.pulse - 0.05 * g.dt_scale)
        g.world_scenery(cv, g.frame)
        cv.blit(veil(150), (0, 0))
        g._draw_petals(cv)
        draw_text(cv, "CHOOSE YOUR TRAVELER", fonts.LARGE, WHITE, (WIDTH // 2, 62),
                  center=True, shadow=True)
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
            draw_text(cv, bank.status or "SPRITE SHEETS NOT LOADED", fonts.TINY, CORAL,
                      (WIDTH // 2, 622), center=True)

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
        panel(cv, r, (24, 38, 58, 240) if selected else
              ((20, 32, 50, 232) if hovered else (15, 25, 40, 224)),
              (110, 138, 166, 80), 18, True)
        inner = r.inflate(-10, -10)
        gradient_rect(cv, (inner.x, inner.y, inner.w, 74),
                      (*ch["accent"], 46), (*ch["accent"], 0), 14)
        if selected:
            pulse = 0.6 + 0.4 * math.sin(g.frame * 0.09)
            pygame.draw.rect(cv, blend_color(GOLD, ch["accent"], 0.35 + 0.25 * pulse),
                             r, 3, border_radius=18)
            cv.blit(get_radial_glow(58, ch["accent"], int(40 + 26 * self.pulse), 5),
                    (r.centerx - 58, r.y + 96 - 58))
        else:
            pygame.draw.rect(cv, (*ch["accent"], 150 if hovered else 80), r, 2, border_radius=18)
        badge = pygame.Rect(r.x + 10, r.y + 10, 24, 24)
        pygame.draw.circle(cv, blend_color(ch["accent"], INK, 0.35), badge.center, 12)
        pygame.draw.circle(cv, (*ch["accent"], 200), badge.center, 12, 2)
        draw_text(cv, str(i + 1), fonts.TINY, WHITE, badge.center, center=True)
        feet = r.y + 158
        if bank.has(ch["id"]):
            anim = "run" if selected else "idle"
            speed = 0.22 if selected else 0.07
            phase = g.frame * speed + (0 if selected else i * 1.7)
            bank.draw(cv, ch["id"], anim, int(phase) % bank.count(ch["id"], anim),
                      r.centerx, feet, CARD_SPRITE_H, facing=1)
        else:
            draw_fallback_hero(cv, ch, r.centerx, feet, CARD_SPRITE_H, g.frame + i * 20)
        draw_text(cv, ch["name"], fonts.SMALL, WHITE if (selected or hovered) else MUTED,
                  (r.centerx, r.y + 176), center=True)
        draw_text(cv, ch["title"].upper(), fonts.TINY, SUBTLE, (r.centerx, r.y + 196), center=True)
        pygame.draw.line(cv, (255, 255, 255, 26), (r.x + 22, r.y + 212), (r.right - 22, r.y + 212), 1)
        perk = pygame.Rect(r.centerx - 56, r.y + 220, 112, 20)
        draw_pill(cv, perk, (*ch["accent"], 60), (*ch["accent"], 140), shadow=False)
        draw_text(cv, ch["perk"], fonts.TINY, blend_color(ch["accent"], WHITE, 0.4),
                  perk.center, center=True)
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
        pygame.draw.ellipse(cv, (10, 16, 30, 160), (78, 540, 84, 18))
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
            bank.draw(cv, ch["id"], "run", int(g.frame * 0.24) % bank.count(ch["id"], "run"),
                      655, 552, 92, facing=1)
        else:
            draw_fallback_hero(cv, ch, 655, 552, 90, g.frame * 2)
        sy = 436
        for label, val in ch["stats"].items():
            draw_text(cv, label, fonts.TINY, MUTED, (712, sy), valign="middle")
            for k in range(5):
                px = 792 + k * 15
                if k < val:
                    pygame.draw.circle(cv, ch["accent"], (px, sy), 5)
                    pygame.draw.circle(cv, blend_color(ch["accent"], WHITE, 0.55), (px - 1, sy - 1), 2)
                else:
                    pygame.draw.circle(cv, SUBTLE, (px, sy), 4, 1)
            sy += 30