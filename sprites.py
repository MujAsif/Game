"""
SPRITES — Character roster + loader for the uniform hero grid sheet.

Reads assets/sprites/heroes.png: six rows, one character per row in ROSTER
order. Figures are located per row by connected components (immune to stray
feet / hat-tips from neighbouring rows), re-packed into equal-size cells
anchored on a shared foot baseline and a head-centred axis.
"""
import os
import json
import math
from collections import deque

import pygame

import config
from config import INK, GOLD, GOLD_SOFT, MINT, MUTED, SUBTLE, BLUE, CORAL, WHITE
from ui import clamp, blend_color, draw_text, get_radial_glow, gradient_rect

PIPELINE_VERSION = 11
SHEET_NAME = "heroes.png"

ROSTER = [
    {
        "id": 0, "name": "ASH", "title": "The Wayfarer", "short": "WAYFARER",
        "perk": "FORTUNE +10%",
        "perk_desc": "A seasoned road-walker. Every trial answered true pays a little more — fortune favors the steady.",
        "accent": BLUE,
        "colors": {"jacket": (46, 114, 138), "scarf": (242, 168, 76),
                   "pants": (36, 46, 64), "hair": (44, 48, 62)},
        "traits": {"score_mul": 1.10},
        "stats": {"SPEED": 3, "LEAP": 3, "HEART": 3, "FORTUNE": 4},
        "style": "scarf",
    },
    {
        "id": 1, "name": "LYRA", "title": "The Ember Scholar", "short": "SCHOLAR",
        "perk": "SCORE +25%",
        "perk_desc": "Scholar of the ember codex. Correct answers burn brighter: +25% score on every solved trial.",
        "accent": CORAL,
        "colors": {"jacket": (186, 58, 70), "scarf": (210, 44, 60),
                   "pants": (52, 38, 44), "hair": (58, 36, 34)},
        "traits": {"score_mul": 1.25},
        "stats": {"SPEED": 3, "LEAP": 3, "HEART": 3, "FORTUNE": 5},
        "style": "ponytail",
    },
    {
        "id": 2, "name": "ALDRIC", "title": "The Sentinel", "short": "SENTINEL",
        "perk": "+1 HEART",
        "perk_desc": "Oathbound sentinel of the ridge. Begins every expedition with one extra heart above the company.",
        "accent": (168, 208, 252),
        "colors": {"jacket": (96, 120, 156), "scarf": (236, 242, 250),
                   "pants": (40, 48, 66), "hair": (70, 52, 40)},
        "traits": {"bonus_hearts": 1},
        "stats": {"SPEED": 2, "LEAP": 2, "HEART": 5, "FORTUNE": 2},
        "style": "knight",
    },
    {
        "id": 3, "name": "NYX", "title": "The Shadow", "short": "SHADOW",
        "perk": "SPEED +18%",
        "perk_desc": "Whisper of the hollow. Moves 18% faster than any companion — the beacons blur past.",
        "accent": (168, 124, 244),
        "colors": {"jacket": (56, 48, 84), "scarf": (126, 88, 196),
                   "pants": (30, 28, 44), "hair": (30, 26, 40)},
        "traits": {"speed_mul": 1.18, "accel_mul": 1.15},
        "stats": {"SPEED": 5, "LEAP": 3, "HEART": 3, "FORTUNE": 2},
        "style": "hood",
    },
    {
        "id": 4, "name": "MIRAE", "title": "The Rune Weaver", "short": "WEAVER",
        "perk": "FORESIGHT",
        "perk_desc": "Weaver of runes. Once per region, press H during a trial to strike two false answers from the scroll.",
        "accent": (198, 142, 255),
        "colors": {"jacket": (98, 66, 172), "scarf": (152, 106, 236),
                   "pants": (44, 36, 64), "hair": (40, 30, 56)},
        "traits": {"hint": 1},
        "stats": {"SPEED": 3, "LEAP": 3, "HEART": 3, "FORTUNE": 4},
        "style": "hat",
    },
    {
        "id": 5, "name": "FEN", "title": "The Verdant Scout", "short": "SCOUT",
        "perk": "FEATHERFALL",
        "perk_desc": "Warden of the canopy. Hold JUMP while falling to feather your descent and drift onto distant ledges.",
        "accent": (146, 214, 128),
        "colors": {"jacket": (88, 130, 76), "scarf": (122, 170, 94),
                   "pants": (46, 44, 38), "hair": (64, 44, 30)},
        "traits": {"glide": True},
        "stats": {"SPEED": 3, "LEAP": 5, "HEART": 3, "FORTUNE": 3},
        "style": "hood",
    },
]


class Frame:
    __slots__ = ("surf", "ax", "ay", "h")

    def __init__(self, surf, ax, ay, ref_h):
        self.surf = surf
        self.ax = float(ax)
        self.ay = float(ay)
        self.h = float(ref_h)


def _find_sheet():
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    tried = []
    for base in (here, cwd):
        for sub in (os.path.join("assets", "sprites"), "sprites", "assets", ""):
            d = os.path.join(base, sub) if sub else base
            if d in tried:
                continue
            tried.append(d)
            p = os.path.join(d, SHEET_NAME)
            if os.path.isfile(p):
                return p
    return None


# ── Background removal ───────────────────────────────────────────
def _background_mask(surf):
    w, h = surf.get_size()
    data = pygame.image.tobytes(surf, "RGBA")

    trans = white = black = 0
    samples = []

    def classify(i):
        o = i * 4
        if data[o + 3] <= 20:
            return 0
        r, g, b = data[o], data[o + 1], data[o + 2]
        samples.append((r, g, b))
        if r > 234 and g > 234 and b > 234:
            return 1
        if r < 26 and g < 26 and b < 26:
            return 2
        return 3

    for x in range(0, w, 5):
        for i in (x, (h - 1) * w + x):
            c = classify(i)
            if c == 0: trans += 1
            elif c == 1: white += 1
            elif c == 2: black += 1
    for y in range(0, h, 5):
        for i in (y * w, y * w + w - 1):
            c = classify(i)
            if c == 0: trans += 1
            elif c == 1: white += 1
            elif c == 2: black += 1

    target = None
    if trans > (white + black):
        mode = "alpha"
    elif white >= black and white > 0:
        mode = "white"
    elif black > 0:
        mode = "black"
    elif samples:
        mode = "solid"
        samples.sort()
        target = samples[len(samples) // 2]
    else:
        mode = "alpha"

    def is_bg_pixel(i):
        o = i * 4
        if mode == "white":
            return data[o] > 234 and data[o + 1] > 234 and data[o + 2] > 234
        if mode == "black":
            return data[o] < 26 and data[o + 1] < 26 and data[o + 2] < 26 and data[o + 3] > 20
        return (abs(data[o] - target[0]) <= 14 and abs(data[o + 1] - target[1]) <= 14
                and abs(data[o + 2] - target[2]) <= 14 and data[o + 3] > 20)

    bg = bytearray(w * h)
    if mode != "alpha":
        dq = deque()
        for x in range(w):
            for i in (x, (h - 1) * w + x):
                if not bg[i] and is_bg_pixel(i):
                    bg[i] = 1
                    dq.append(i)
        for y in range(h):
            for i in (y * w, y * w + w - 1):
                if not bg[i] and is_bg_pixel(i):
                    bg[i] = 1
                    dq.append(i)
        while dq:
            i = dq.popleft()
            x = i % w
            if x > 0:
                j = i - 1
                if not bg[j] and is_bg_pixel(j):
                    bg[j] = 1
                    dq.append(j)
            if x < w - 1:
                j = i + 1
                if not bg[j] and is_bg_pixel(j):
                    bg[j] = 1
                    dq.append(j)
            if i >= w:
                j = i - w
                if not bg[j] and is_bg_pixel(j):
                    bg[j] = 1
                    dq.append(j)
            if i < (h - 1) * w:
                j = i + w
                if not bg[j] and is_bg_pixel(j):
                    bg[j] = 1
                    dq.append(j)

    alpha = data[3::4]
    if mode == "alpha":
        fg = bytearray(1 if a > 20 else 0 for a in alpha)
    else:
        fg = bytearray(1 if (a > 20 and not b) else 0 for a, b in zip(alpha, bg))
    return data, bg, fg, w, h, mode


def _clean_surface(data, bg, w, h):
    alpha = bytearray(data[3::4])
    for i in range(w * h):
        if bg[i] or alpha[i] <= 20:
            alpha[i] = 0
    buf = bytearray(data)
    buf[3::4] = alpha
    return pygame.image.frombytes(bytes(buf), (w, h), "RGBA").convert_alpha()


# ── Row bands ────────────────────────────────────────────────────
def _bands(counts, thresh, min_size, merge_gap=0):
    raw, start = [], None
    for i, c in enumerate(counts):
        if c > thresh:
            if start is None:
                start = i
        elif start is not None:
            raw.append([start, i])
            start = None
    if start is not None:
        raw.append([start, len(counts)])
    if not raw:
        return []
    merged = [raw[0]]
    for b in raw[1:]:
        if b[0] - merged[-1][1] <= merge_gap:
            merged[-1][1] = b[1]
        else:
            merged.append(b)
    return [b for b in merged if b[1] - b[0] >= min_size]


def _row_bands(fg, w, region, min_h):
    x0, y0, x1, y1 = region
    counts = [fg[y * w + x0: y * w + x1].count(1) for y in range(y0, y1)]
    thresh = max(4, int((x1 - x0) * 0.015))
    return [(y0 + a, y0 + b) for a, b in _bands(counts, thresh, min_h, merge_gap=0)]


# ── Connected components ─────────────────────────────────────────
def _components(fg, w, region):
    x0, y0, x1, y1 = region
    seen = bytearray(w * (y1 - y0))
    comps = []
    for y in range(y0, y1):
        row = (y - y0) * w
        for x in range(x0, x1):
            si = row + x
            if seen[si] or not fg[y * w + x]:
                continue
            seen[si] = 1
            dq = deque([y * w + x])
            minx = maxx = x
            miny = maxy = y
            area = 0
            while dq:
                j = dq.popleft()
                jy, jx = divmod(j, w)
                area += 1
                if jx < minx: minx = jx
                if jx > maxx: maxx = jx
                if jy < miny: miny = jy
                if jy > maxy: maxy = jy
                if jx > x0:
                    sj = (jy - y0) * w + jx - 1
                    if not seen[sj] and fg[j - 1]:
                        seen[sj] = 1
                        dq.append(j - 1)
                if jx < x1 - 1:
                    sj = (jy - y0) * w + jx + 1
                    if not seen[sj] and fg[j + 1]:
                        seen[sj] = 1
                        dq.append(j + 1)
                if jy > y0:
                    sj = (jy - 1 - y0) * w + jx
                    if not seen[sj] and fg[j - w]:
                        seen[sj] = 1
                        dq.append(j - w)
                if jy < y1 - 1:
                    sj = (jy + 1 - y0) * w + jx
                    if not seen[sj] and fg[j + w]:
                        seen[sj] = 1
                        dq.append(j + w)
            comps.append([minx, miny, maxx + 1, maxy + 1, area])
    return comps


def _trim(fg, w, xa, ya, xb, yb):
    minx, miny, maxx, maxy = xb, yb, xa - 1, ya - 1
    area = 0
    for y in range(ya, yb):
        base = y * w
        for x in range(xa, xb):
            if fg[base + x]:
                area += 1
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
    if area < 60 or maxx < minx or maxy < miny:
        return None
    return [minx, miny, maxx + 1, maxy + 1, area]


def _merge_side(comps, gap=6, ov=0.4):
    """Re-attach side capes / ponytails that vertically overlap the body.
    Never merges vertically-stacked fragments (feet from the row above)."""
    changed = True
    while changed:
        changed = False
        res = []
        for c in comps:
            for o in res:
                v_overlap = min(c[3], o[3]) - max(c[1], o[1])
                smaller = min(c[3] - c[1], o[3] - o[1])
                h_gap = max(c[0], o[0]) - min(c[2], o[2])
                if smaller > 0 and v_overlap >= ov * smaller and h_gap <= gap:
                    o[0] = min(o[0], c[0])
                    o[1] = min(o[1], c[1])
                    o[2] = max(o[2], c[2])
                    o[3] = max(o[3], c[3])
                    o[4] += c[4]
                    changed = True
                    break
            else:
                res.append(c[:])
        comps = res
    return comps


def _split_wide(fg, w, cells, med_w, ya, yb, depth=0):
    if depth > 3 or not cells:
        return cells
    out = []
    for c in cells:
        cw = c[2] - c[0]
        if cw > med_w * 1.6 and cw > 40:
            xa, xb = c[0], c[2]
            rows = [fg[y * w + xa: y * w + xb] for y in range(ya, yb)]
            counts = [sum(col) for col in zip(*rows)] if rows else []
            if counts:
                lo = max(1, int(len(counts) * 0.30))
                hi = min(len(counts) - 1, int(len(counts) * 0.70))
                if hi > lo:
                    cut = min(range(lo, hi), key=lambda k: counts[k]) + xa
                    left = _trim(fg, w, xa, ya, cut, yb)
                    right = _trim(fg, w, cut, ya, xb, yb)
                    if left and right:
                        out.extend(_split_wide(fg, w, [left, right], med_w, ya, yb, depth + 1))
                        continue
        out.append(c)
    return out


def _row_figures(fg, w, ya, yb):
    """One clean bbox per pose in a row, free of neighbouring-row debris."""
    comps = [c for c in _components(fg, w, (0, ya, w, yb)) if c[4] > 60]
    if not comps:
        return []
    comps = _merge_side(comps)
    hs = sorted(c[3] - c[1] for c in comps)
    med = hs[len(hs) // 2]
    comps = [c for c in comps
             if med * 0.45 <= (c[3] - c[1]) <= med * 1.9
             and (c[2] - c[0]) >= med * 0.2]
    for c in comps:
        if (c[3] - c[1]) > med * 1.45:
            c[1] = c[3] - int(med * 1.45)
    comps = _split_wide(fg, w, comps, med, ya, yb)
    comps.sort(key=lambda c: c[0])
    return comps


# ── Packing ──────────────────────────────────────────────────────
def _head_anchor_x(cleaned, box, ref_h):
    x0, y0, x1, y1 = box[:4]
    yb = min(y1, y0 + max(3, int(ref_h * 0.14)))
    if yb <= y0 or x1 <= x0:
        return (x1 - x0) * 0.5
    sub = cleaned.subsurface(pygame.Rect(x0, y0, x1 - x0, yb - y0))
    d = pygame.image.tobytes(sub, "RGBA")
    fw, fh = sub.get_size()
    total = n = 0
    for yy in range(fh):
        row = yy * fw
        for xx in range(fw):
            if d[(row + xx) * 4 + 3] > 20:
                total += xx
                n += 1
    return (total / n) if n else fw * 0.5


def _build_cells(cleaned, figs):
    idle = figs[:2] if len(figs) >= 2 else figs[:1]
    baseline = max(b[3] for b in idle)
    hs = sorted(b[3] - b[1] for b in idle)
    ref_h = float(hs[len(hs) // 2])

    heads = [_head_anchor_x(cleaned, b, ref_h) for b in figs]
    left_ext = max(heads)
    right_ext = max((b[2] - b[0]) - hx for b, hx in zip(figs, heads))
    cw = int(math.ceil(2 * max(left_ext, right_ext))) + 8
    top_ext = max(baseline - b[1] for b in figs)
    bot_ext = max(0, max(b[3] - baseline for b in figs))
    ch = int(top_ext + bot_ext) + 8
    base_y = int(top_ext) + 4

    cells = []
    for b, hx in zip(figs, heads):
        x0, y0, x1, y1 = b[:4]
        sub = cleaned.subsurface(pygame.Rect(x0, y0, x1 - x0, y1 - y0)).copy()
        cell = pygame.Surface((cw, ch), pygame.SRCALPHA)
        cell.blit(sub, (int(round(cw * 0.5 - hx)), int(base_y - (baseline - y0))))
        cells.append(Frame(cell, cw * 0.5, float(base_y), ref_h))
    return cells, ref_h


def _map_animations(cells):
    n = len(cells)
    if n >= 8:
        idle, walk, run = cells[0:2], cells[2:6], cells[6:n - 2]
        rise, fall = cells[n - 2], cells[n - 1]
    elif n >= 4:
        idle, walk = cells[0:1], cells[1:n - 2]
        run = list(walk)
        rise, fall = cells[n - 2], cells[n - 1]
    else:
        idle = walk = run = list(cells)
        rise = fall = cells[-1]
    if not idle:
        idle = [cells[0]]
    if not walk:
        walk = list(idle)
    if not run:
        run = list(walk)
    return {"idle": idle, "walk": walk, "run": run,
            "air": [rise, rise, fall], "crouch": [fall]}


def _default_progress(step, total, label):
    try:
        pygame.event.pump()
        s = config.screen
        if s is None:
            return
        w, h = s.get_size()
        gradient_rect(s, (0, 0, w, h), (13, 22, 38), (24, 40, 52))
        s.blit(get_radial_glow(180, GOLD, 30, 6), (w // 2 - 180, h // 2 - 220))
        draw_text(s, "THE THREE TRIALS", config.fonts.LARGE, WHITE, (w // 2, h // 2 - 90), center=True, shadow=True)
        draw_text(s, "SUMMONING THE COMPANY", config.fonts.SMALL, GOLD_SOFT, (w // 2, h // 2 - 40), center=True)
        bw, bh = 440, 14
        bx, by = w // 2 - bw // 2, h // 2
        pygame.draw.rect(s, (30, 44, 64), (bx, by, bw, bh), border_radius=7)
        p = max(0.0, min(1.0, step / max(1, total)))
        if p > 0:
            pygame.draw.rect(s, MINT, (bx, by, max(10, int(bw * p)), bh), border_radius=7)
        pygame.draw.rect(s, (120, 150, 178), (bx, by, bw, bh), 1, border_radius=7)
        draw_text(s, label, config.fonts.TINY, MUTED, (w // 2, by + 40), center=True)
        pygame.display.flip()
    except Exception:
        pass


class SpriteBank:
    def __init__(self):
        self.ready = False
        self.attempted = False
        self.status = ""
        self.dir = None
        self.chars = {}
        self._cache = {}

    def ensure(self):
        if not self.attempted:
            self.load()

    def has(self, cid):
        self.ensure()
        return self.ready and cid in self.chars and bool(self.chars[cid]["anims"].get("idle"))

    def count(self, cid, anim):
        self.ensure()
        return len(self.chars[cid]["anims"].get(anim) or self.chars[cid]["anims"]["idle"])

    def base_h(self, cid):
        return self.chars[cid]["base_h"]

    def portrait(self, cid):
        return self.chars[cid].get("portrait")

    def _scaled(self, key, frame, height, flip, tint):
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        s = max(1.0, height) / max(1.0, frame.h)
        w = max(1, int(round(frame.surf.get_width() * s)))
        h = max(1, int(round(frame.surf.get_height() * s)))
        surf = pygame.transform.smoothscale(frame.surf, (w, h))
        if flip:
            surf = pygame.transform.flip(surf, True, False)
        if tint:
            surf = surf.copy()
            surf.fill((120, 18, 26), special_flags=pygame.BLEND_RGB_ADD)
        ax = (w - frame.ax * s) if flip else (frame.ax * s)
        ay = frame.ay * s
        if len(self._cache) > 1400:
            self._cache.clear()
        out = (surf, ax, ay)
        self._cache[key] = out
        return out

    def draw(self, surface, cid, anim, idx, cx, bottom, height, facing=1, tint=False):
        entry = self.chars[cid]
        frames = entry["anims"].get(anim) or entry["anims"]["idle"]
        i = idx % len(frames)
        flip = (facing < 0) != (getattr(config, "SPRITE_SOURCE_FACING", 1) < 0)
        key = ("f", cid, anim, i, int(height), flip, tint)
        surf, ax, ay = self._scaled(key, frames[i], height, flip, tint)
        surface.blit(surf, (int(round(cx - ax)), int(round(bottom - ay))))

    def draw_portrait(self, surface, cid, cx, bottom, height, facing=1):
        self.draw(surface, cid, "idle", 0, cx, bottom, height, facing)

    def _cache_dir(self):
        return os.path.join(self.dir, "_cache")

    def _cache_key(self, path):
        st = os.stat(path)
        return {"v": PIPELINE_VERSION, "file": [int(st.st_mtime), st.st_size]}

    def _try_load_cache(self, key):
        with open(os.path.join(self._cache_dir(), "index.json"), "r", encoding="utf-8") as f:
            index = json.load(f)
        if index.get("key") != key:
            return False
        chars = {}
        for cid_s, entry in index["chars"].items():
            anims = {}
            for anim, metas in entry["anims"].items():
                frames = []
                for i, (ax, ay, ref) in enumerate(metas):
                    p = os.path.join(self._cache_dir(), f"{cid_s}_{anim}_{i}.png")
                    frames.append(Frame(pygame.image.load(p).convert_alpha(), ax, ay, ref))
                anims[anim] = frames
            chars[int(cid_s)] = {"anims": anims, "portrait": None, "base_h": entry["base_h"]}
        self.chars = chars
        return True

    def _write_cache(self, key):
        os.makedirs(self._cache_dir(), exist_ok=True)
        index = {"key": key, "chars": {}}
        for cid, entry in self.chars.items():
            anims = {}
            for anim, frames in entry["anims"].items():
                metas = []
                for i, fr in enumerate(frames):
                    pygame.image.save(fr.surf, os.path.join(self._cache_dir(), f"{cid}_{anim}_{i}.png"))
                    metas.append([fr.ax, fr.ay, fr.h])
                anims[anim] = metas
            index["chars"][str(cid)] = {"anims": anims, "base_h": entry["base_h"]}
        with open(os.path.join(self._cache_dir(), "index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f)

    def _process(self, path):
        surf = pygame.image.load(path).convert_alpha()
        data, bg, fg, w, h, mode = _background_mask(surf)
        cleaned = _clean_surface(data, bg, w, h)
        print(f"[sprites] {path} {surf.get_size()} bg={mode}")

        rows = _row_bands(fg, w, (0, 0, w, h), max(8, int(h * 0.05)))
        if len(rows) != len(ROSTER):
            rows = [(int(i * h / len(ROSTER)), int((i + 1) * h / len(ROSTER)))
                    for i in range(len(ROSTER))]

        chars = {}
        for idx, ch in enumerate(ROSTER):
            ya, yb = rows[idx]
            figs = _row_figures(fg, w, ya, yb)
            if not figs:
                print(f"[sprites] {ch['name']}: NO FIGURES")
                continue
            cells, ref_h = _build_cells(cleaned, figs)
            anims = _map_animations(cells)
            chars[ch["id"]] = {"anims": anims, "portrait": None, "base_h": ref_h}
            print(f"[sprites] {ch['name']}: {len(cells)} poses -> " +
                  ", ".join(f"{k}×{len(v)}" for k, v in anims.items()))
        self.chars = chars

    def load(self, progress=None):
        self.attempted = True
        if progress is None:
            progress = _default_progress

        def tick(step, total, label):
            try:
                progress(step, total, label)
            except Exception:
                pass

        try:
            path = _find_sheet()
            if path is None:
                self.status = "heroes.png NOT FOUND — PUT IT IN assets/sprites/ NEXT TO main.py"
                print("[sprites] " + self.status)
                tick(1, 1, self.status)
                self.ready = False
                return self
            self.dir = os.path.dirname(path)
            key = self._cache_key(path)
            try:
                tick(1, 2, "Restoring the company…")
                if self._try_load_cache(key):
                    self.ready = True
                    self.status = f"{len(self.chars)} heroes restored from cache"
                    print(f"[sprites] {self.status}")
                    tick(2, 2, "The company awaits.")
                    return self
            except Exception:
                pass

            tick(1, 4, "Reading the hero grid…")
            self._process(path)
            tick(3, 4, "Sealing the cache…")
            try:
                self._write_cache(key)
            except Exception as exc:
                print(f"[sprites] cache write skipped: {exc}")
            self.ready = bool(self.chars)
            n = sum(len(f) for e in self.chars.values() for f in e["anims"].values())
            self.status = (f"{len(self.chars)} heroes · {n} frames" if self.ready
                           else "NO FIGURES FOUND IN heroes.png")
            print(f"[sprites] {self.status}")
            tick(4, 4, "The company awaits.")
        except Exception as exc:
            self.ready = False
            self.status = f"SPRITE PIPELINE ERROR: {exc}"
            print(f"[sprites] disabled: {exc}")
        return self


bank = SpriteBank()