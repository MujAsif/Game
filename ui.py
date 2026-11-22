"""
UI — Drawing toolkit: text, gradients, panels, pills, glows, shapes, Button.
FIX: removed the harsh white top-highlight lines from pills/panels.
"""
import pygame
import math
import config
from config import (INK, PANEL_BG, PANEL_BORDER, WHITE, MUTED, SUBTLE,
                    GOLD, GOLD_SOFT, MINT, CORAL, BLUE)

_SURFACE_CACHE = {}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def blend_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def draw_text(surface, text, font, color, pos, center=False, right=False, shadow=False, valign="top"):
    img = font.render(str(text), True, color)
    rect = img.get_rect()
    if center:
        rect.center = (int(pos[0]), int(pos[1]))
    elif right:
        rect.midright = (int(pos[0]), int(pos[1]))
    elif valign == "middle":
        rect.midleft = (int(pos[0]), int(pos[1]))
    else:
        rect.topleft = (int(pos[0]), int(pos[1]))
    if shadow:
        shade = font.render(str(text), True, (6, 10, 18))
        shade.set_alpha(140)
        surface.blit(shade, rect.move(1, 2))
    surface.blit(img, rect)
    return rect


def wrap_text(text, font, max_width):
    lines, line = [], ""
    for word in str(text).split():
        test = word if not line else line + " " + word
        if font.size(test)[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def veil(alpha):
    s = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
    s.fill((6, 11, 20, alpha))
    return s


def _shadow_box(w, h, radius, layers):
    pad = 14
    box = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    for ox, oy, a, r in layers:
        pygame.draw.rect(box, (3, 7, 15, a), (pad + ox, pad + oy, w, h), border_radius=r)
    return box, pad


def get_gradient_surface(size, top, bottom, radius=0):
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    key = ("grad", w, h, tuple(top[:3]), tuple(bottom[:3]), radius)
    cached = _SURFACE_CACHE.get(key)
    if cached is not None:
        return cached
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        c = blend_color(top, bottom, y / max(1, h - 1))
        pygame.draw.line(grad, (*c, 255), (0, y), (w - 1, y))
    if radius > 0:
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    if len(_SURFACE_CACHE) > 260:
        _SURFACE_CACHE.clear()
    _SURFACE_CACHE[key] = grad
    return grad


def gradient_rect(surface, rect, top, bottom, radius=0):
    rect = pygame.Rect(rect)
    if rect.w > 0 and rect.h > 0:
        surface.blit(get_gradient_surface((rect.w, rect.h), top, bottom, radius), rect.topleft)


def draw_pill(surface, rect, fill=(16, 26, 42, 224), border=(145, 175, 200, 75), shadow=True):
    rect = pygame.Rect(rect)
    radius = rect.h // 2
    key = ("pill", rect.w, rect.h, tuple(fill), tuple(border), shadow)
    cached = _SURFACE_CACHE.get(key)
    if cached is None:
        if shadow:
            box, pad = _shadow_box(rect.w, rect.h, radius,
                                   [(-4, 6, 50, radius + 2), (-2, 3, 80, radius + 1), (0, 2, 110, radius)])
        else:
            box, pad = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA), 0
        inner = pygame.Rect(pad, pad, rect.w, rect.h)
        pygame.draw.rect(box, fill, inner, border_radius=radius)
        pygame.draw.rect(box, border, inner, 1, border_radius=radius)
        if len(_SURFACE_CACHE) > 260:
            _SURFACE_CACHE.clear()
        cached = (box, pad)
        _SURFACE_CACHE[key] = cached
    box, pad = cached
    surface.blit(box, (rect.x - pad, rect.y - pad))


def panel(surface, rect, fill=PANEL_BG, border=PANEL_BORDER, radius=20, shadow=True):
    rect = pygame.Rect(rect)
    key = ("panel", rect.w, rect.h, tuple(fill), tuple(border), radius, shadow)
    cached = _SURFACE_CACHE.get(key)
    if cached is None:
        if shadow:
            box, pad = _shadow_box(rect.w, rect.h, radius,
                                   [(-6, 8, 40, radius + 4), (-3, 5, 70, radius + 2), (0, 3, 100, radius)])
        else:
            box, pad = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA), 0
        inner = pygame.Rect(pad, pad, rect.w, rect.h)
        pygame.draw.rect(box, fill, inner, border_radius=radius)
        pygame.draw.rect(box, border, inner, 1, border_radius=radius)
        if len(_SURFACE_CACHE) > 260:
            _SURFACE_CACHE.clear()
        cached = (box, pad)
        _SURFACE_CACHE[key] = cached
    box, pad = cached
    surface.blit(box, (rect.x - pad, rect.y - pad))


def get_radial_glow(radius, color, max_alpha=46, rings=5):
    key = ("glow", int(radius), tuple(color[:3]), int(max_alpha), rings)
    cached = _SURFACE_CACHE.get(key)
    if cached is not None:
        return cached
    r = max(4, int(radius))
    surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(rings, 0, -1):
        frac = i / rings
        alpha = int(max_alpha * (1.0 - frac * 0.7) / rings * 1.8)
        pygame.draw.circle(surf, (*color[:3], clamp(alpha, 1, 255)), (r, r), int(r * frac))
    _SURFACE_CACHE[key] = surf
    return surf


def get_smooth_heart(size, color, filled=True):
    key = ("heart", int(size), tuple(color[:3]), filled)
    cached = _SURFACE_CACHE.get(key)
    if cached is not None:
        return cached
    scale = 3
    s = max(12, int(size)) * scale
    surf = pygame.Surface((s, s), pygame.SRCALPHA)
    r = int(s * 0.23)
    cx, cy = s // 2, int(s * 0.37)
    lc, rc = (cx - r + 1, cy), (cx + r - 1, cy)
    tip = (cx, int(s * 0.84))
    poly = [(cx - r * 2 + 2, cy + int(r * 0.25)), (cx, cy - int(r * 0.35)),
            (cx + r * 2 - 2, cy + int(r * 0.25)), tip]
    if filled:
        pygame.draw.circle(surf, color, lc, r)
        pygame.draw.circle(surf, color, rc, r)
        pygame.draw.polygon(surf, color, poly)
        pygame.draw.circle(surf, tuple(min(255, c + 55) for c in color[:3]),
                           (lc[0] - r // 3, lc[1] - r // 3), max(2, r // 3))
    else:
        o = (*color[:3], 95)
        pygame.draw.circle(surf, o, lc, r, 3 * scale // 2)
        pygame.draw.circle(surf, o, rc, r, 3 * scale // 2)
        pygame.draw.polygon(surf, (24, 36, 54, 180), poly)
        pygame.draw.line(surf, o, (cx - r * 2 + 3, cy + r // 3), tip, 3 * scale // 2)
        pygame.draw.line(surf, o, (cx + r * 2 - 3, cy + r // 3), tip, 3 * scale // 2)
    final = pygame.transform.smoothscale(surf, (int(size), int(size)))
    _SURFACE_CACHE[key] = final
    return final


def get_smooth_star(size, color):
    key = ("star", int(size), tuple(color[:3]))
    cached = _SURFACE_CACHE.get(key)
    if cached is not None:
        return cached
    s = max(12, int(size)) * 3
    surf = pygame.Surface((s, s), pygame.SRCALPHA)
    c = s // 2
    pts = []
    for i in range(8):
        a = i * math.pi / 4 - math.pi / 2
        rad = s * 0.44 if i % 2 == 0 else s * 0.16
        pts.append((c + math.cos(a) * rad, c + math.sin(a) * rad))
    pygame.draw.polygon(surf, color, pts)
    final = pygame.transform.smoothscale(surf, (int(size), int(size)))
    _SURFACE_CACHE[key] = final
    return final


class Button:
    """Interactive button with hover lift and press animation."""
    def __init__(self, key, rect, label, action, accent=GOLD):
        self.key = key
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.accent = accent
        self.hover = self.press = 0.0

    def update(self, mouse_pos, dt=1.0):
        target = 1.0 if self.rect.collidepoint(mouse_pos) else 0.0
        self.hover = lerp(self.hover, target, 1.0 - (0.76 ** dt))
        self.press = max(0.0, self.press - 0.15 * dt)

    def draw(self, surface):
        lift = int(round(self.hover * 2 - self.press * 2))
        rect = self.rect.move(0, -lift)
        radius = rect.h // 2
        box, pad = _shadow_box(rect.w, rect.h, radius,
                               [(-3, 5, 60, radius + 2), (-1, 3, 90, radius + 1), (0, 2, 120, radius)])
        surface.blit(box, (rect.x - pad, rect.y - pad))
        fill = blend_color((25, 39, 60), (38, 58, 86), self.hover)
        border = blend_color((92, 120, 148), self.accent, self.hover * 0.85)
        pygame.draw.rect(surface, fill, rect, border_radius=radius)
        pygame.draw.rect(surface, border, rect, 2 if self.hover > 0.2 else 1, border_radius=radius)
        draw_text(surface, self.label, config.fonts.SMALL, WHITE, rect.center, center=True, shadow=True)