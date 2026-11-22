"""
ASSET PREP — automatically converts your raw AI sheets into game-ready assets.
Drop the raw images (magenta background is fine) into  assets/raw/ :
    tiles.png   props.png   bg1.png   bg2.png   bg3.png
On first launch (or whenever a raw file changes) this module removes the
magenta, slices the sheets and WRITES the results into the normal folders:
    assets/tiles/sakura_tiles.png, assets/props/<name>.png, assets/bg/levelN.png
Those converted files then stay in the folders and are used directly.
"""
import os
import json
import pygame

T = 32
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "assets", "raw")
TILES_OUT = os.path.join(HERE, "assets", "tiles", "sakura_tiles.png")
PROPS_OUT = os.path.join(HERE, "assets", "props")
BG_OUT = os.path.join(HERE, "assets", "bg")
STATE = os.path.join(RAW, ".prep_state.json")

PROP_CELLS = [
    ("torii", 0, 0, 96), ("stone_lantern", 1, 0, 64), ("lantern_post", 2, 0, 64), ("banner", 3, 0, 64),
    ("shrine", 0, 1, 72), ("sakura_tree", 1, 1, 110), ("bush_pink", 2, 1, 40), ("crate", 3, 1, 30),
    ("fence", 0, 2, 34), ("signpost", 1, 2, 44), ("rope_bridge", 2, 2, 48), ("waterfall", 3, 2, 120),
]
RAW_NAMES = ("tiles", "props", "bg1", "bg2", "bg3")


def _key_magenta(surf):
    w, h = surf.get_size()
    data = bytearray(pygame.image.tobytes(surf, "RGBA"))
    for i in range(w * h):
        o = i * 4
        r, g, b = data[o], data[o + 1], data[o + 2]
        if r > 150 and b > 150 and g < 90:
            data[o + 3] = min(data[o + 3], int(255 * min(1.0, max(0.0, (g - 40) / 50.0))))
    return pygame.image.frombytes(bytes(data), (w, h), "RGBA").convert_alpha()


def _alpha_bbox(s):
    w, h = s.get_size()
    d = pygame.image.tobytes(s, "RGBA")
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        row = y * w
        for x in range(w):
            if d[(row + x) * 4 + 3] > 24:
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
    return pygame.Rect(minx, miny, maxx - minx + 1, maxy - miny + 1) if maxx >= 0 else None


def _slice_tiles(sheet):
    w, h = sheet.get_size()
    d = pygame.image.tobytes(sheet, "RGBA")
    col_any = [any(d[(y * w + x) * 4 + 3] > 24 for y in range(0, h, 3)) for x in range(w)]
    tiles = []
    for ya, yb in ((0, h // 2), (h // 2, h)):
        clusters, start = [], None
        for x in range(w):
            if col_any[x] and start is None:
                start = x
            elif not col_any[x] and start is not None:
                clusters.append((start, x))
                start = None
        if start is not None:
            clusters.append((start, w))
        for xa, xb in clusters[:8]:
            sub = sheet.subsurface(pygame.Rect(xa, ya, xb - xa, yb - ya))
            bb = _alpha_bbox(sub)
            if bb:
                tiles.append(pygame.transform.smoothscale(sub.subsurface(bb), (T, T)))
    return tiles


def _sig(p):
    st = os.stat(p)
    return [int(st.st_mtime), st.st_size]


def _outputs_ok():
    return (os.path.isfile(TILES_OUT)
            and os.path.isfile(os.path.join(PROPS_OUT, "torii.png"))
            and os.path.isfile(os.path.join(BG_OUT, "level1.png")))


def ensure():
    """Convert raw sheets if needed. Never raises; returns True if assets exist."""
    try:
        if not os.path.isdir(RAW):
            return _outputs_ok()
        present = {n: os.path.join(RAW, f"{n}.png") for n in RAW_NAMES}
        present = {k: p for k, p in present.items() if os.path.isfile(p)}
        if not present:
            return _outputs_ok()
        state = {}
        if os.path.isfile(STATE):
            with open(STATE, "r", encoding="utf-8") as f:
                state = json.load(f)
        changed = any(state.get(k) != _sig(p) for k, p in present.items())
        if not changed and _outputs_ok():
            return True
        os.makedirs(os.path.join(HERE, "assets", "tiles"), exist_ok=True)
        os.makedirs(PROPS_OUT, exist_ok=True)
        os.makedirs(BG_OUT, exist_ok=True)
        if "tiles" in present:
            tiles = _slice_tiles(_key_magenta(pygame.image.load(present["tiles"]).convert_alpha()))
            sheet = pygame.Surface((T * 8, T * 2), pygame.SRCALPHA)
            for i, t in enumerate(tiles[:16]):
                sheet.blit(t, ((i % 8) * T, (i // 8) * T))
            pygame.image.save(sheet, TILES_OUT)
            print(f"[asset_prep] tiles: {len(tiles)} sliced -> {TILES_OUT}")
        if "props" in present:
            sheet = _key_magenta(pygame.image.load(present["props"]).convert_alpha())
            w, h = sheet.get_size()
            cw, ch = w // 4, h // 3
            for name, cx, cy, th in PROP_CELLS:
                bb = _alpha_bbox(sheet.subsurface(pygame.Rect(cx * cw, cy * ch, cw, ch)))
                if not bb:
                    continue
                crop = sheet.subsurface(pygame.Rect(cx * cw, cy * ch, cw, ch)).subsurface(bb)
                nw = max(4, int(round(crop.get_width() * (th / crop.get_height()))))
                pygame.image.save(pygame.transform.smoothscale(crop, (nw, th)),
                                  os.path.join(PROPS_OUT, f"{name}.png"))
            print("[asset_prep] props: 12 sprites written")
        for i in (1, 2, 3):
            k = f"bg{i}"
            if k in present:
                art = _key_magenta(pygame.image.load(present[k]).convert_alpha())
                nw = int(round(art.get_width() * (650 / art.get_height())))
                pygame.image.save(pygame.transform.smoothscale(art, (nw, 650)),
                                  os.path.join(BG_OUT, f"level{i}.png"))
                print(f"[asset_prep] bg{i}: {nw}x650 written")
        for k, p in present.items():
            state[k] = _sig(p)
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f)
        print("[asset_prep] done — converted assets are now stored in assets/")
        return True
    except Exception as exc:
        print(f"[asset_prep] skipped ({exc}) — using procedural fallbacks")
        return _outputs_ok()