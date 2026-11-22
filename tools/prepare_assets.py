"""
TOOL — Keys magenta, slices the AI sheets, and writes game-ready assets.
Put raw images in tools/raw/:  tiles.png  props.png  bg1.png  bg2.png  bg3.png
Run once:  python tools/prepare_assets.py
Outputs:   assets/tiles/sakura_tiles.png (256x64), assets/props/<type>.png,
           assets/bg/level1..3.png (keyed, 650px tall)
"""
import os
import pygame

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
ROOT = os.path.join(HERE, "..")
T = 32

PROP_CELLS = [
    ("torii", 0, 0, 96), ("stone_lantern", 1, 0, 64), ("lantern_post", 2, 0, 64), ("banner", 3, 0, 64),
    ("shrine", 0, 1, 72), ("sakura_tree", 1, 1, 110), ("bush_pink", 2, 1, 40), ("crate", 3, 1, 30),
    ("fence", 0, 2, 34), ("signpost", 1, 2, 44), ("rope_bridge", 2, 2, 48), ("waterfall", 3, 2, 120),
]


def key_magenta(surf):
    w, h = surf.get_size()
    data = bytearray(pygame.image.tobytes(surf, "RGBA"))
    for i in range(w * h):
        o = i * 4
        r, g, b = data[o], data[o + 1], data[o + 2]
        if r > 150 and b > 150 and g < 90:
            a = int(255 * min(1.0, max(0.0, (g - 40) / 50.0)))
            data[o + 3] = min(data[o + 3], a)
    return pygame.image.frombytes(bytes(data), (w, h), "RGBA").convert_alpha()


def alpha_bbox(s):
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
    if maxx < 0:
        return None
    return pygame.Rect(minx, miny, maxx - minx + 1, maxy - miny + 1)


def slice_tiles(sheet):
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
            bb = alpha_bbox(sub)
            if not bb:
                continue
            crop = sub.subsurface(bb)
            tiles.append(pygame.transform.smoothscale(crop, (T, T)))
    return tiles


def main():
    pygame.init()
    os.makedirs(os.path.join(ROOT, "assets", "tiles"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "assets", "props"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "assets", "bg"), exist_ok=True)
    tp = os.path.join(RAW, "tiles.png")
    if os.path.isfile(tp):
        tiles = slice_tiles(key_magenta(pygame.image.load(tp).convert_alpha()))
        sheet = pygame.Surface((T * 8, T * 2), pygame.SRCALPHA)
        for i, t in enumerate(tiles[:16]):
            sheet.blit(t, ((i % 8) * T, (i // 8) * T))
        pygame.image.save(sheet, os.path.join(ROOT, "assets", "tiles", "sakura_tiles.png"))
        print(f"[prep] tiles: {len(tiles)} -> assets/tiles/sakura_tiles.png")
    pp = os.path.join(RAW, "props.png")
    if os.path.isfile(pp):
        sheet = key_magenta(pygame.image.load(pp).convert_alpha())
        w, h = sheet.get_size()
        cw, ch = w // 4, h // 3
        for name, cx, cy, target_h in PROP_CELLS:
            cell = sheet.subsurface(pygame.Rect(cx * cw, cy * ch, cw, ch))
            bb = alpha_bbox(cell)
            if not bb:
                continue
            crop = cell.subsurface(bb)
            scale = target_h / crop.get_height()
            nw = max(4, int(round(crop.get_width() * scale)))
            pygame.image.save(pygame.transform.smoothscale(crop, (nw, target_h)),
                              os.path.join(ROOT, "assets", "props", f"{name}.png"))
        print("[prep] props: 12 sprites -> assets/props/")
    for i in (1, 2, 3):
        bp = os.path.join(RAW, f"bg{i}.png")
        if os.path.isfile(bp):
            art = key_magenta(pygame.image.load(bp).convert_alpha())
            scale = 650 / art.get_height()
            nw = int(round(art.get_width() * scale))
            pygame.image.save(pygame.transform.smoothscale(art, (nw, 650)),
                              os.path.join(ROOT, "assets", "bg", f"level{i}.png"))
            print(f"[prep] bg{i}: {nw}x650 -> assets/bg/level{i}.png")
    print("[prep] done.")


if __name__ == "__main__":
    main()