"""
UI — Drawing toolkit: text, gradients, panels, pills, glows, shapes, Button.
All repeated surfaces (veils, shadows, gradients, glyphs) are cached.
"""
import pygame
import math
import config
from config import PANEL_BG, PANEL_BORDER, WHITE, GOLD

_SURFACE_CACHE = {}
_VEIL_CACHE = {}
_TEXT_CACHE = {}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def blend_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def _cache_put(cache, key, value, limit=260):
    if len(cache) > limit:
        cache.clear()
    cache[key] = value
    return value


def get_text_image(text, font, color):
    """Cached glyph surface. Never mutate the result; use set_alpha on a copy."""
    key = (id(font), str(text), tuple(color[:3]))
    hit = _TEXT_CACHE.get(key)
    if hit is not None:
        return hit
    return _cache_put(_TEXT_CACHE, key, font.render(str(text), True, color), 400)


def draw_text(surface, text, font, color, pos, center=False, right=False,
              shadow=False, valign="top"):
    img = get_text_image(text, font, color)
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
        shade = get_text_image(text, font, (6, 10, 18))
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
    """Cached full-screen tint. Alpha quantised to keep the cache small."""
    a = int(clamp(alpha, 0, 255))
    key = (config.WIDTH, config.HEIGHT, a)
    hit = _VEIL_CACHE.get(key)
    if hit is not None:
        return hit
    s = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
    s.fill((6, 11, 20, a))
    return _cache_put(_VEIL_CACHE, key, s, 80)


def _shadow_box(w, h, radius, layers):
    key = ("shadow", w, h, radius, tuple(layers))
    hit = _SURFACE_CACHE.get(key)
    if hit is not None:
        return hit
    pad = 14
    box = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    for ox, oy, a, r in layers:
        pygame.draw.rect(box, (3, 7, 15, a), (pad + ox, pad + oy, w, h), border_radius=r)
    return _cache_put(_SURFACE_CACHE, key, (box, pad), 320)


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
    return _cache_put(_SURFACE_CACHE, key, grad, 320)


def gradient_rect(surface, rect, top, bottom, radius=0):
    rect = pygame.Rect(rect)
    if rect.w > 0 and rect.h > 0:
        surface.blit(get_gradient_surface((rect.w, rect.h), top, bottom, radius), rect.topleft)


def _boxed_rect(rect, fill, border, radius, shadow, kind):
    rect = pygame.Rect(rect)
    key = (kind, rect.w, rect.h, tuple(fill), tuple(border), radius, shadow)
    cached = _SURFACE_CACHE.get(key)
    if cached is None:
        if shadow:
            if kind == "pill":
                layers = [(-4, 6, 50, radius + 2), (-2, 3, 80, radius + 1), (0, 2, 110, radius)]
            else:
                layers = [(-6, 8, 40, radius + 4), (-3, 5, 70, radius + 2), (0, 3, 100, radius)]
            box, pad = _shadow_box(rect.w, rect.h, radius, layers)
        else:
            box, pad = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA), 0
        inner = pygame.Rect(pad, pad, rect.w, rect.h)
        pygame.draw.rect(box, fill, inner, border_radius=radius)
        pygame.draw.rect(box, border, inner, 1, border_radius=radius)
        cached = _cache_put(_SURFACE_CACHE, key, (box, pad), 320)
    return cached


def draw_pill(surface, rect, fill=(16, 26, 42, 224), border=(145, 175, 200, 75), shadow=True):
    rect = pygame.Rect(rect)
    box, pad = _boxed_rect(rect, fill, border, rect.h // 2, shadow, "pill")
    surface.blit(box, (rect.x - pad, rect.y - pad))


def panel(surface, rect, fill=PANEL_BG, border=PANEL_BORDER, radius=20, shadow=True):
    rect = pygame.Rect(rect)
    box, pad = _boxed_rect(rect, fill, border, radius, shadow, "panel")
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
    return _cache_put(_SURFACE_CACHE, key, surf, 320)


def get_smooth_heart(size, color, filled=True):
    size = max(12, int(size))
    key = ("heart", size, tuple(color[:3]), filled)
    cached = _SURFACE_CACHE.get(key)
    if cached is not None:
        return cached
    scale = 3
    s = size * scale
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
    final = pygame.transform.smoothscale(surf, (size, size))
    return _cache_put(_SURFACE_CACHE, key, final, 320)


class Button:
    """Interactive button with hover lift and press animation."""

    def __init__(self, key, rect, label, action, accent=GOLD):
        self.key = key
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.accent = accent
        self.hover = self.press = 0.0

    def update(self, mouse_pos, dt=1.0, selected=False):
        target = 1.0 if (self.rect.collidepoint(mouse_pos) or selected) else 0.0
        self.hover = lerp(self.hover, target, 1.0 - (0.76 ** dt))
        self.press = max(0.0, self.press - 0.15 * dt)

    def draw(self, surface):
        lift = int(round(self.hover * 2 - self.press * 2))
        rect = self.rect.move(0, -lift)
        radius = rect.h // 2
        box, pad = _shadow_box(rect.w, rect.h, radius,
                               [(-3, 5, 60, radius + 2), (-1, 3, 90, radius + 1),
                                (0, 2, 120, radius)])
        surface.blit(box, (rect.x - pad, rect.y - pad))
        fill = blend_color((25, 39, 60), (38, 58, 86), self.hover)
        border = blend_color((92, 120, 148), self.accent, self.hover * 0.85)
        pygame.draw.rect(surface, fill, rect, border_radius=radius)
        pygame.draw.rect(surface, border, rect, 2 if self.hover > 0.2 else 1,
                         border_radius=radius)
        draw_text(surface, self.label, config.fonts.SMALL, WHITE, rect.center,
                  center=True, shadow=True)