"""
SAKURA — Twilight shrine theme for Stage 1 (THE SAKURA SANCTUM).
Fully procedural: background, stone-and-blossom platforms, shrine props,
coins, mist and petal weather. No external assets required.
"""
import math
import random
import pygame
from config import WIDTH, HEIGHT
from ui import clamp, lerp, blend_color, gradient_rect, get_radial_glow

# ── palette ────────────────────────────────────────────────────
STONE_TOP  = (86, 62, 112)
STONE_MID  = (56, 40, 82)
STONE_BOT  = (28, 20, 46)
STONE_LINE = (22, 15, 36)
GRASS      = (226, 92, 164)
GRASS_HI   = (255, 148, 200)
GRASS_LO   = (178, 64, 128)
BLOSSOM    = (255, 176, 214)
BLOSSOM_HI = (255, 214, 236)
BLOSSOM_LO = (214, 88, 150)
TRUNK      = (64, 38, 56)
WOOD       = (122, 80, 68)
WOOD_DK    = (84, 54, 48)
TORII      = (186, 58, 84)
TORII_DK   = (128, 36, 60)
LANTERN    = (255, 206, 120)
LANTERN_HI = (255, 236, 180)
ROOF       = (58, 44, 74)
ROOF_HI    = (96, 74, 116)
PAPER      = (232, 96, 148)
MIST       = (196, 168, 226)
WATER      = (186, 208, 255)
COIN_GOLD  = (255, 208, 92)
COIN_RIM   = (196, 142, 52)

_CACHES = {}


def _cached(key, builder):
    s = _CACHES.get(key)
    if s is None:
        if len(_CACHES) > 200:
            _CACHES.clear()
        s = builder()
        _CACHES[key] = s
    return s


def _petal_surf(sz, alpha):
    def b():
        s = pygame.Surface((sz * 2, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (255, 168, 208, alpha), (0, 0, sz * 2, sz))
        return s
    return _cached(("petal", sz, alpha), b)


def _mist_puff(w, alpha):
    def b():
        s = pygame.Surface((w, 46), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*MIST, alpha), (0, 0, w, 46))
        return s
    return _cached(("mist", w, alpha), b)


def _cloud_surf(w, h, color, alpha):
    def b():
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*color, alpha), (0, 0, w, h))
        pygame.draw.ellipse(s, (*color, alpha // 2), (int(w * 0.18), -h // 3, int(w * 0.6), h))
        return s
    return _cached(("cloud", w, h, tuple(color), alpha), b)


# ── background ─────────────────────────────────────────────────
def _sky_gradient(surf):
    stops = [(0.0, (14, 10, 36)), (0.34, (44, 22, 74)), (0.62, (122, 44, 104)),
             (0.82, (196, 70, 122)), (1.0, (238, 104, 140))]
    h = surf.get_height()
    for y in range(h):
        t = y / max(1, h - 1)
        c = stops[-1][1]
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t <= t1:
                c = blend_color(c0, c1, clamp((t - t0) / max(1e-6, t1 - t0), 0, 1))
                break
        pygame.draw.line(surf, c, (0, y), (surf.get_width() - 1, y))


def _moon(surf, cx, cy, r):
    surf.blit(get_radial_glow(int(r * 2.2), (255, 140, 180), 60, 6),
              (cx - int(r * 2.2), cy - int(r * 2.2)))
    pygame.draw.circle(surf, (255, 158, 196), (cx, cy), r)
    for dx, dy, rr in ((-0.32, -0.10, 0.16), (0.22, 0.18, 0.12),
                       (0.05, -0.34, 0.09), (-0.10, 0.30, 0.10)):
        pygame.draw.circle(surf, (244, 138, 178),
                           (cx + int(dx * r), cy + int(dy * r)), max(3, int(rr * r)))
    pygame.draw.circle(surf, (255, 214, 232), (cx, cy), r, 2)


def _pagoda(surf, x, y, s, color):
    for i in range(3):
        tw = int((86 - i * 18) * s)
        ty = y - int((i + 1) * 34 * s)
        bw = int((46 - i * 10) * s)
        pygame.draw.rect(surf, color, (x - bw // 2, ty, bw, int(30 * s)))
        pygame.draw.polygon(surf, color, [(x - tw // 2, ty), (x + tw // 2, ty),
                                          (x + tw // 2 - int(4 * s), ty - int(8 * s)),
                                          (x - tw // 2 + int(4 * s), ty - int(8 * s))])
        pygame.draw.polygon(surf, color, [(x - tw // 2, ty), (x - tw // 2 - int(6 * s), ty - int(6 * s)),
                                          (x - tw // 2 + int(8 * s), ty - int(4 * s))])
        pygame.draw.polygon(surf, color, [(x + tw // 2, ty), (x + tw // 2 + int(6 * s), ty - int(6 * s)),
                                          (x + tw // 2 - int(8 * s), ty - int(4 * s))])
    pygame.draw.line(surf, color, (x, y - int(3 * 34 * s) - int(8 * s)),
                     (x, y - int(3 * 34 * s) - int(20 * s)), max(1, int(2 * s)))


def _torii_shape(surf, x, y, s, col, col_dk):
    pw, ph = max(2, int(10 * s)), int(64 * s)
    lx, rx = x - int(26 * s), x + int(26 * s)
    pygame.draw.rect(surf, col, (lx - pw // 2, y - ph, pw, ph))
    pygame.draw.rect(surf, col, (rx - pw // 2, y - ph, pw, ph))
    lw = int(76 * s)
    pygame.draw.rect(surf, col_dk, (x - lw // 2, y - ph - int(10 * s), lw, int(9 * s)))
    pygame.draw.polygon(surf, col_dk, [(x - lw // 2, y - ph - int(10 * s)),
                                       (x - lw // 2 - int(6 * s), y - ph - int(16 * s)),
                                       (x - lw // 2 + int(10 * s), y - ph - int(8 * s))])
    pygame.draw.polygon(surf, col_dk, [(x + lw // 2, y - ph - int(10 * s)),
                                       (x + lw // 2 + int(6 * s), y - ph - int(16 * s)),
                                       (x + lw // 2 - int(10 * s), y - ph - int(8 * s))])
    pygame.draw.rect(surf, col, (x - int(34 * s), y - ph + int(14 * s), int(68 * s), int(7 * s)))
    pygame.draw.rect(surf, col_dk, (x - int(4 * s), y - ph - int(2 * s), int(8 * s), int(16 * s)))
    pygame.draw.rect(surf, col_dk, (lx - pw // 2 - 2, y - 6, pw + 4, 6))
    pygame.draw.rect(surf, col_dk, (rx - pw // 2 - 2, y - 6, pw + 4, 6))


def make_background(theme):
    bg = pygame.Surface((WIDTH, HEIGHT)).convert()
    _sky_gradient(bg)
    rng = random.Random(77)
    for _ in range(70):
        xx, yy = rng.randrange(WIDTH), rng.randrange(20, 300)
        c = blend_color((14, 10, 36), (255, 230, 244), rng.randint(90, 200) / 255.0)
        pygame.draw.circle(bg, c, (xx, yy), 1)
    _moon(bg, 620, 180, 108)
    bg.blit(_cloud_surf(260, 34, (255, 140, 184), 70), (180, 150))
    bg.blit(_cloud_surf(320, 30, (255, 150, 190), 60), (520, 236))
    bg.blit(_cloud_surf(220, 26, (240, 120, 170), 55), (60, 262))
    pygame.draw.polygon(bg, (96, 52, 118), [(0, 400), (150, 300), (300, 392), (470, 292),
                                            (640, 388), (820, 300), (980, 386), (1100, 320),
                                            (1100, HEIGHT), (0, HEIGHT)])
    pygame.draw.polygon(bg, (70, 40, 96), [(0, 440), (190, 350), (360, 430), (560, 344),
                                           (760, 432), (950, 352), (1100, 420),
                                           (1100, HEIGHT), (0, HEIGHT)])
    _pagoda(bg, 950, 336, 1.0, (44, 26, 66))
    _pagoda(bg, 250, 360, 0.7, (52, 30, 74))
    _torii_shape(bg, 150, 402, 1.1, (120, 44, 84), (96, 34, 70))
    haze = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
    for y in range(120):
        pygame.draw.line(haze, (255, 140, 184, int(46 * (y / 120))), (0, y), (WIDTH, y))
    bg.blit(haze, (0, 340))
    for x in range(-20, WIDTH + 40, 46):
        r = 26 + ((x * 13) % 18)
        pygame.draw.circle(bg, (30, 18, 46), (x, 560 + ((x * 7) % 22)), r)
    pygame.draw.rect(bg, (30, 18, 46), (0, 566, WIDTH, HEIGHT - 566))
    return bg


# ── ambient fx ─────────────────────────────────────────────────
def draw_sky_fx(surf, frame, cam_x):
    for cx0, cy0, sc, sp in ((160, 120, 1.2, 0.10), (620, 90, 0.9, 0.14), (900, 180, 1.1, 0.08)):
        x = (cx0 + frame * sp - cam_x * 0.18) % (WIDTH + 400) - 200
        surf.blit(_cloud_surf(int(180 * sc), int(30 * sc), (255, 150, 190), 40), (int(x), cy0))


_prng = random.Random(1234)
PETALS = [(_prng.randrange(0, 4000), _prng.randrange(0, 700), _prng.uniform(0.5, 1.2),
           _prng.randint(3, 5), _prng.uniform(0, 6.28)) for _ in range(30)]


def draw_petals(surf, frame, cam_x, front=True):
    group = PETALS[:18] if front else PETALS[18:]
    for px, py, sp, sz, ph in group:
        x = (px + frame * (0.5 + sp * 0.4) - cam_x * (0.55 if front else 0.3)) % (WIDTH + 160) - 80
        y = (py + frame * sp * 0.9) % (HEIGHT + 80) - 40
        x += math.sin(frame * 0.03 + ph) * 22
        surf.blit(_petal_surf(sz, 210 if front else 110), (int(x), int(y)))


def draw_mist(surf, frame, cam_x):
    for layer, (alpha, speed, y0) in enumerate(((46, 0.25, 596), (34, 0.40, 616), (26, 0.60, 634))):
        w = 300 + layer * 60
        puff = _mist_puff(w, alpha)
        off = (frame * speed - cam_x * (0.25 + layer * 0.15)) % 210
        x = -260 + off
        while x < WIDTH + 260:
            surf.blit(puff, (int(x), y0))
            x += 210


# ── platforms ──────────────────────────────────────────────────
def draw_platform(surf, rect, cam_x, frame=0):
    rx, ry = int(rect.x - cam_x), int(rect.y)
    if rx + rect.w < -40 or rx > WIDTH + 40:
        return
    rng = random.Random(int(rect.x) * 31 + int(rect.y))
    floating = rect.h <= 40
    if floating:
        body = pygame.Rect(rx - 2, ry, rect.w + 4, rect.h + 10)
        gradient_rect(surf, body, STONE_TOP, STONE_MID, radius=8)
        for _ in range(max(2, rect.w // 34)):
            vx = rx + rng.randint(6, rect.w - 6)
            vl = rng.randint(8, 22)
            pygame.draw.line(surf, STONE_BOT, (vx, body.bottom - 4),
                             (vx + rng.randint(-3, 3), body.bottom - 4 + vl), 2)
    else:
        body = pygame.Rect(rx, ry, rect.w, rect.h)
        gradient_rect(surf, body, STONE_TOP, STONE_BOT)
        yy, row = ry + 16, 0
        while yy < ry + rect.h - 6:
            pygame.draw.line(surf, STONE_LINE, (rx + 2, yy), (rx + rect.w - 2, yy), 1)
            xx = rx + (14 if row % 2 else 0)
            while xx < rx + rect.w - 4:
                pygame.draw.line(surf, STONE_LINE, (xx, yy), (xx, min(yy + 24, ry + rect.h - 4)), 1)
                xx += rng.randint(26, 44)
            yy += 24
            row += 1
        for _ in range(max(3, rect.w // 60)):
            bx, by = rx + rng.randint(8, rect.w - 8), ry + rng.randint(20, rect.h - 8)
            pygame.draw.circle(surf, blend_color(STONE_MID, STONE_BOT, 0.5), (bx, by), rng.randint(2, 4))
        for _ in range(max(1, rect.w // 120)):
            vx = rx + rng.choice([2, rect.w - 3])
            vl = rng.randint(18, 46)
            pygame.draw.line(surf, GRASS_LO, (vx, ry + 8), (vx, ry + 8 + vl), 2)
            pygame.draw.circle(surf, BLOSSOM_LO, (vx, ry + 8 + vl), 2)
    cap = pygame.Rect(rx - 4, ry - 9, rect.w + 8, 13)
    pygame.draw.rect(surf, GRASS, cap, border_radius=6)
    pygame.draw.line(surf, GRASS_HI, (cap.x + 5, cap.y + 2), (cap.right - 5, cap.y + 2), 2)
    tx = cap.x + 4
    while tx < cap.right - 4:
        th = rng.randint(3, 7)
        col = GRASS_HI if rng.random() < 0.4 else GRASS
        pygame.draw.line(surf, col, (tx, cap.y + 2), (tx + rng.randint(-2, 2), cap.y + 2 - th), 1)
        tx += rng.randint(5, 9)
    for _ in range(max(2, rect.w // 70)):
        fx = rx + rng.randint(4, rect.w - 4)
        pygame.draw.circle(surf, BLOSSOM_HI, (fx, ry - rng.randint(4, 8)), 2)


# ── props ──────────────────────────────────────────────────────
def _sakura_tree(surf, x, y, frame, s=1.0, seed=7):
    rng = random.Random(seed)
    h = int(96 * s)
    pygame.draw.line(surf, TRUNK, (x, y), (x - int(6 * s), y - int(h * 0.55)), max(3, int(7 * s)))
    pygame.draw.line(surf, TRUNK, (x - int(6 * s), y - int(h * 0.55)), (x + int(4 * s), y - int(h * 0.8)), max(2, int(5 * s)))
    pygame.draw.line(surf, TRUNK, (x - int(6 * s), y - int(h * 0.55)), (x - int(20 * s), y - int(h * 0.75)), max(2, int(4 * s)))
    pygame.draw.line(surf, TRUNK, (x + int(4 * s), y - int(h * 0.8)), (x + int(18 * s), y - int(h * 0.9)), max(2, int(3 * s)))
    cy = y - int(h * 0.92)
    blobs = [(-20, 6, 20), (0, -6, 24), (20, 4, 19), (-8, 12, 17), (12, 12, 16)]
    cols = [BLOSSOM_LO, BLOSSOM, BLOSSOM_HI, BLOSSOM, BLOSSOM_LO]
    for i, (dx, dy, r) in enumerate(blobs):
        pygame.draw.circle(surf, cols[i], (x + int(dx * s), cy + int(dy * s)), max(2, int(r * s)))
    for _ in range(6):
        pygame.draw.circle(surf, BLOSSOM_HI,
                           (x + int(rng.randint(-24, 24) * s), cy + int(rng.randint(-14, 14) * s)),
                           max(1, int(2 * s)))
    for i in range(4):
        t = (frame * 0.9 + i * 41) % 120
        px = x + int(math.sin((frame + i * 53) * 0.05) * 18 * s) + (i - 2) * int(14 * s)
        py = cy + int(t * 0.9 * s)
        if py < y + 6:
            pygame.draw.ellipse(surf, BLOSSOM, (px, py, max(2, int(4 * s)), max(1, int(3 * s))))


def _lantern_post(surf, x, y, frame, s=1.0):
    ph = int(58 * s)
    pygame.draw.rect(surf, WOOD_DK, (x - int(3 * s), y - ph, int(6 * s), ph))
    pygame.draw.rect(surf, WOOD_DK, (x - int(3 * s), y - ph, int(20 * s), int(5 * s)))
    lx = x + int(16 * s)
    pulse = 0.75 + 0.25 * math.sin(frame * 0.09 + x * 0.7)
    surf.blit(get_radial_glow(int(26 * s), (255, 176, 96), int(50 * pulse), 4),
              (lx - int(26 * s), y - ph + int(2 * s)))
    pygame.draw.line(surf, WOOD_DK, (lx, y - ph + int(4 * s)), (lx, y - ph + int(10 * s)), max(1, int(2 * s)))
    body = pygame.Rect(lx - int(7 * s), y - ph + int(10 * s), int(14 * s), int(18 * s))
    pygame.draw.rect(surf, LANTERN, body, border_radius=max(1, int(4 * s)))
    pygame.draw.rect(surf, (120, 70, 50), (body.x, body.centery - 1, body.w, 2))
    pygame.draw.rect(surf, WOOD_DK, (body.x - 1, body.y - int(4 * s), body.w + 2, int(4 * s)))
    pygame.draw.rect(surf, WOOD_DK, (body.x - 1, body.bottom, body.w + 2, int(3 * s)))
    pygame.draw.circle(surf, LANTERN_HI, (lx - int(2 * s), body.y + int(6 * s)), max(1, int(3 * s)))


def _stone_lantern(surf, x, y, frame, s=1.0):
    c, cd = (148, 128, 168), (104, 86, 128)
    pygame.draw.rect(surf, cd, (x - int(10 * s), y - int(6 * s), int(20 * s), int(6 * s)))
    pygame.draw.rect(surf, c, (x - int(4 * s), y - int(20 * s), int(8 * s), int(14 * s)))
    pygame.draw.rect(surf, cd, (x - int(9 * s), y - int(26 * s), int(18 * s), int(6 * s)))
    box = pygame.Rect(x - int(7 * s), y - int(40 * s), int(14 * s), int(14 * s))
    pygame.draw.rect(surf, c, box)
    pygame.draw.rect(surf, LANTERN, (box.x + int(3 * s), box.y + int(3 * s), int(8 * s), int(8 * s)))
    pulse = 0.7 + 0.3 * math.sin(frame * 0.08 + x)
    surf.blit(get_radial_glow(int(18 * s), (255, 176, 96), int(40 * pulse), 4),
              (x - int(18 * s), box.centery - int(18 * s)))
    pygame.draw.polygon(surf, cd, [(x - int(12 * s), box.y), (x + int(12 * s), box.y),
                                   (x + int(8 * s), box.y - int(8 * s)), (x - int(8 * s), box.y - int(8 * s))])
    pygame.draw.circle(surf, c, (x, box.y - int(10 * s)), max(1, int(3 * s)))


def _banner(surf, x, y, frame, s=1.0):
    ph = int(96 * s)
    pygame.draw.rect(surf, WOOD_DK, (x - int(2 * s), y - ph, int(4 * s), ph))
    pygame.draw.rect(surf, WOOD_DK, (x - int(2 * s), y - ph, int(16 * s), int(4 * s)))
    sway = math.sin(frame * 0.06 + x * 0.3) * 3
    bw, bh = int(20 * s), int(56 * s)
    bx = x + int(12 * s)
    top = y - ph + int(4 * s)
    pts = [(bx, top), (bx + bw, top + int(sway)), (bx + bw + int(sway), top + bh),
           (bx + bw // 2 + int(sway * 0.5), top + bh - int(8 * s)), (bx + int(sway * 0.3), top + bh)]
    pygame.draw.polygon(surf, PAPER, pts)
    cx0, cy0 = bx + bw // 2 + int(sway * 0.5), top + int(bh * 0.35)
    for k in range(5):
        a = k * math.tau / 5 - math.pi / 2
        pygame.draw.circle(surf, BLOSSOM_HI, (cx0 + int(math.cos(a) * 4 * s), cy0 + int(math.sin(a) * 4 * s)),
                           max(1, int(3 * s)))
    pygame.draw.circle(surf, COIN_GOLD, (cx0, cy0), max(1, int(2 * s)))
    pygame.draw.circle(surf, WOOD_DK, (x, y - ph - 2), max(1, int(3 * s)))


def _shrine(surf, x, y, frame, s=1.0):
    w, h = int(72 * s), int(40 * s)
    pygame.draw.rect(surf, (92, 70, 92), (x - w // 2 - int(5 * s), y - int(6 * s), w + int(10 * s), int(6 * s)))
    pygame.draw.rect(surf, (148, 106, 94), (x - w // 2, y - h, w, h - int(6 * s)))
    pygame.draw.rect(surf, (60, 42, 46), (x - int(9 * s), y - int(28 * s), int(18 * s), int(22 * s)), border_radius=2)
    pygame.draw.circle(surf, COIN_GOLD, (x + int(5 * s), y - int(17 * s)), max(1, int(2 * s)))
    ry, rw = y - h, int(w * 1.3)
    pygame.draw.polygon(surf, ROOF, [(x - rw // 2, ry), (x + rw // 2, ry),
                                     (x + rw // 2 - int(10 * s), ry - int(12 * s)),
                                     (x - rw // 2 + int(10 * s), ry - int(12 * s))])
    pygame.draw.polygon(surf, ROOF, [(x - rw // 2, ry), (x - rw // 2 - int(7 * s), ry - int(8 * s)),
                                     (x - rw // 2 + int(9 * s), ry - int(5 * s))])
    pygame.draw.polygon(surf, ROOF, [(x + rw // 2, ry), (x + rw // 2 + int(7 * s), ry - int(8 * s)),
                                     (x + rw // 2 - int(9 * s), ry - int(5 * s))])
    pygame.draw.rect(surf, (148, 106, 94), (x - int(14 * s), ry - int(22 * s), int(28 * s), int(12 * s)))
    rw2 = int(44 * s)
    pygame.draw.polygon(surf, ROOF, [(x - rw2 // 2, ry - int(20 * s)), (x + rw2 // 2, ry - int(20 * s)),
                                     (x + rw2 // 2 - int(7 * s), ry - int(30 * s)),
                                     (x - rw2 // 2 + int(7 * s), ry - int(30 * s))])
    pygame.draw.rect(surf, ROOF_HI, (x - int(10 * s), ry - int(34 * s), int(20 * s), int(5 * s)))


def _crate(surf, x, y, s=1.0):
    w = int(30 * s)
    r = pygame.Rect(int(x - w / 2), int(y - w), w, w)
    pygame.draw.rect(surf, (146, 104, 74), r, border_radius=3)
    pygame.draw.rect(surf, (96, 66, 48), r, 2, border_radius=3)
    pygame.draw.line(surf, (96, 66, 48), r.topleft, r.bottomright, 2)
    pygame.draw.line(surf, (96, 66, 48), r.topright, r.bottomleft, 2)


def _signpost(surf, x, y, s=1.0):
    pygame.draw.rect(surf, WOOD_DK, (int(x - 3 * s), int(y - 44 * s), int(6 * s), int(44 * s)))
    b = pygame.Rect(int(x - 26 * s), int(y - 46 * s), int(52 * s), int(18 * s))
    pygame.draw.polygon(surf, WOOD, [(b.left, b.top), (b.right - 8, b.top), (b.right, b.centery),
                                     (b.right - 8, b.bottom), (b.left, b.bottom)])
    pygame.draw.line(surf, (90, 60, 50), (b.left + 6, b.centery - 3), (b.right - 14, b.centery - 3), 2)
    pygame.draw.line(surf, (90, 60, 50), (b.left + 6, b.centery + 3), (b.right - 18, b.centery + 3), 2)


def _fence(surf, x, y, s=1.0):
    for i in range(3):
        px = int(x + i * 18 * s)
        pygame.draw.rect(surf, WOOD, (px, int(y - 26 * s), int(5 * s), int(26 * s)))
    pygame.draw.rect(surf, WOOD_DK, (int(x), int(y - 22 * s), int(36 * s + 5), int(4 * s)))
    pygame.draw.rect(surf, WOOD_DK, (int(x), int(y - 12 * s), int(36 * s + 5), int(4 * s)))


def _bush(surf, x, y, s=1.0, seed=3):
    rng = random.Random(seed)
    for dx, r in ((-10, 10), (0, 13), (10, 9)):
        pygame.draw.circle(surf, BLOSSOM_LO, (int(x + dx * s), int(y - r * s * 0.8)), max(2, int(r * s)))
    for dx, r in ((-6, 8), (4, 9)):
        pygame.draw.circle(surf, BLOSSOM, (int(x + dx * s), int(y - r * s * 0.9)), max(2, int(r * s)))
    for _ in range(5):
        pygame.draw.circle(surf, BLOSSOM_HI, (x + rng.randint(-12, 12), y - rng.randint(6, 18)), 1)


def _waterfall(surf, x, y, frame, s=1.0):
    w = int(30 * s)
    top, bot = int(y), HEIGHT + 20
    srf = pygame.Surface((w, bot - top), pygame.SRCALPHA)
    srf.fill((*WATER, 70))
    for i in range(5):
        xx = int((i + 0.5) * w / 5)
        off = int((frame * 4 + i * 37) % 46)
        for yy in range(-46 + off, bot - top, 46):
            pygame.draw.line(srf, (235, 244, 255, 150), (xx, max(0, yy)), (xx, min(bot - top, yy + 22)), 2)
    pygame.draw.rect(surf, (210, 228, 255), (x - w // 2 - 3, top - 4, w + 6, 6), border_radius=3)
    surf.blit(srf, (x - w // 2, top))
    for i in range(3):
        mw = int(60 + 26 * math.sin(frame * 0.05 + i * 2))
        surf.blit(get_radial_glow(max(8, mw // 2), MIST, 46, 4), (x - mw // 2, bot - 60 - i * 14))


def _rope_bridge(surf, x1, y1, x2, y2, frame):
    sag = 16 + math.sin(frame * 0.04) * 2
    n = 14
    deck, hand = [], []
    for i in range(n + 1):
        t = i / n
        bx, by = lerp(x1, x2, t), lerp(y1, y2, t) + math.sin(math.pi * t) * sag
        deck.append((int(bx), int(by)))
        hand.append((int(bx), int(by - 26)))
    pygame.draw.lines(surf, WOOD_DK, False, hand, 2)
    pygame.draw.lines(surf, WOOD_DK, False, deck, 2)
    for i in range(n + 1):
        pygame.draw.line(surf, WOOD, (deck[i][0], deck[i][1] - 2), (deck[i][0], deck[i][1] + 2), 4)
        if i % 3 == 0:
            pygame.draw.line(surf, WOOD_DK, deck[i], hand[i], 1)
    mx, my = deck[n // 2]
    pulse = 0.7 + 0.3 * math.sin(frame * 0.1)
    surf.blit(get_radial_glow(20, (255, 176, 96), int(46 * pulse), 4), (mx - 20, my + 4))
    pygame.draw.rect(surf, LANTERN, (mx - 5, my + 6, 10, 14), border_radius=3)
    pygame.draw.rect(surf, WOOD_DK, (mx - 6, my + 3, 12, 4))


def draw_prop(surf, prop, cam_x, frame):
    px, py = int(prop["x"] - cam_x), int(prop["y"])
    if px < -160 or px > WIDTH + 160:
        return
    t = prop["type"]
    s = prop.get("scale", 1.0)
    if t == "sakura_tree":
        _sakura_tree(surf, px, py, frame, s, seed=int(prop["x"]))
    elif t == "torii":
        _torii_shape(surf, px, py, s, TORII, TORII_DK)
    elif t == "lantern_post":
        _lantern_post(surf, px, py, frame, s)
    elif t == "stone_lantern":
        _stone_lantern(surf, px, py, frame, s)
    elif t == "banner":
        _banner(surf, px, py, frame, s)
    elif t == "shrine":
        _shrine(surf, px, py, frame, s)
    elif t == "crate":
        _crate(surf, px, py, s)
    elif t == "signpost":
        _signpost(surf, px, py, s)
    elif t == "fence":
        _fence(surf, px, py, s)
    elif t == "bush_pink":
        _bush(surf, px, py, s, seed=int(prop["x"]))
    elif t == "waterfall":
        _waterfall(surf, px, py, frame, s)
    elif t == "rope_bridge":
        _rope_bridge(surf, px, py, int(prop.get("x2", prop["x"] + 80) - cam_x),
                     int(prop.get("y2", py)), frame)


# ── collectibles ───────────────────────────────────────────────
def draw_coin(surf, x, y, frame, i=0):
    bob = math.sin(frame * 0.06 + i * 0.9) * 3
    cy = int(y + bob)
    sq = abs(math.cos(frame * 0.055 + i * 0.5))
    w, h = max(3, int(16 * sq)), 18
    surf.blit(get_radial_glow(16, (255, 208, 92), 40, 4), (int(x) - 16, cy - 16))
    r = pygame.Rect(int(x) - w // 2, cy - h // 2, w, h)
    pygame.draw.ellipse(surf, COIN_RIM, r)
    if w > 6:
        inner = r.inflate(-4, -4)
        pygame.draw.ellipse(surf, COIN_GOLD, inner)
        pygame.draw.ellipse(surf, (255, 236, 170), inner.inflate(-4, -6))