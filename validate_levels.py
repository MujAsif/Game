#!/usr/bin/env python3
"""
VALIDATE LEVELS — standalone audit of data.py.   Run:  python validate_levels.py

Exit 0 = clean, 1 = warnings, 2 = cannot run.
No display needed; only config constants are imported.
"""
import math
import sys

import config

TILE = config.TILE
SKY_ROWS = config.SKY_ROWS
GRAVITY = config.GRAVITY
JUMP_V = abs(config.JUMP_SPEED)
MOVE_SPEED = config.MOVE_SPEED
PLAYER_H = config.PLAYER_H
SAFE_FACTOR = 0.80

MAX_JUMP_H = JUMP_V * JUMP_V / (2 * GRAVITY)
AIR_TIME = 2 * JUMP_V / GRAVITY
MAX_JUMP_D = MOVE_SPEED * AIR_TIME
SAFE_STEP = SAFE_FACTOR * MAX_JUMP_H
SAFE_GAP = SAFE_FACTOR * MAX_JUMP_D

KNOWN = set("=|-M^v~KPG ")
LEFTOVER = set("cEF")
SURFACELESS_DECOR = ("waterfall", "rope_bridge")


def air_time_to_height(h):
    if h >= 0:
        disc = max(0.0, JUMP_V * JUMP_V - 2 * GRAVITY * h)
        return (JUMP_V + math.sqrt(disc)) / GRAVITY
    return (JUMP_V + math.sqrt(JUMP_V * JUMP_V + 2 * GRAVITY * (-h))) / GRAVITY


class Rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)

    @property
    def left(self): return self.x

    @property
    def right(self): return self.x + self.w

    @property
    def top(self): return self.y

    @property
    def bottom(self): return self.y + self.h

    @property
    def centerx(self): return self.x + self.w // 2

    def overlaps_x(self, o):
        return self.left < o.right and o.left < self.right

    def rowcol(self):
        return f"(row {self.y // TILE - SKY_ROWS}, col {self.x // TILE})"


def strip_rows(text):
    out, widths = [], []
    for ln in text.split("\n"):
        s = ln
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        widths.append(len(s))
        out.append(s)
    return out, widths


def parse(text):
    rows, widths = strip_rows(text)
    cols = max(widths, default=0)
    rows = [r.ljust(cols) for r in rows]
    d = {"rows": rows, "widths": widths, "cols": cols,
         "platforms": [], "one_way": [], "movers": [], "water": [],
         "spikes_ceil": [], "spike_runs": [], "water_runs": [],
         "checkpoints": [], "start": None, "goal": None,
         "leftovers": [], "unknown": [], "p_count": 0, "g_count": 0,
         "solid_cells": set()}
    for r, line in enumerate(rows):
        c = 0
        while c < cols:
            ch = line[c]
            x, y = c * TILE, (r + SKY_ROWS) * TILE
            if ch in "=|":
                c0 = c
                while c < cols and line[c] in "=|":
                    d["solid_cells"].add((c, r))
                    c += 1
                d["platforms"].append(Rect(x, y, (c - c0) * TILE, TILE))
                continue
            if ch == "-":
                c0 = c
                while c < cols and line[c] == "-":
                    c += 1
                d["one_way"].append(Rect(x, y + TILE - 12, (c - c0) * TILE, 12))
                continue
            if ch == "M":
                c0 = c
                while c < cols and line[c] == "M":
                    c += 1
                w = (c - c0) * TILE
                d["movers"].append(Rect(x - 3 * TILE, y + TILE - 14, w + 6 * TILE, 14))
                continue
            if ch == "^":
                c0 = c
                while c < cols and line[c] == "^":
                    d["solid_cells"].add((c, r))
                    c += 1
                w = (c - c0) * TILE
                d["platforms"].append(Rect(x, y, w, TILE))
                d["spike_runs"].append(Rect(x, y, w, TILE))
                continue
            if ch == "v":
                c0 = c
                while c < cols and line[c] == "v":
                    c += 1
                d["spikes_ceil"].append(Rect(x + 6, y, (c - c0) * TILE - 12, 24))
                continue
            if ch == "~":
                c0 = c
                while c < cols and line[c] == "~":
                    c += 1
                w = (c - c0) * TILE
                d["water"].append(Rect(x, y, w, TILE))
                d["water_runs"].append(Rect(x, y, w, TILE))
                continue
            if ch == "K":
                d["checkpoints"].append((x + TILE // 2, y + TILE, r, c))
            elif ch == "P":
                d["p_count"] += 1
                d["start"] = (x + TILE // 2, y + TILE, r, c)
            elif ch == "G":
                d["g_count"] += 1
                d["goal"] = Rect(x + 4, y - 10, TILE - 8, TILE + 10)
            elif ch in LEFTOVER:
                d["leftovers"].append((ch, r, c))
            elif ch not in KNOWN:
                d["unknown"].append((ch, r, c))
            c += 1
    return d


def gap(a, b):
    if b.left >= a.right:
        return b.left - a.right
    if a.left >= b.right:
        return a.left - b.right
    return 0


def can_edge(a, b):
    rise = a.top - b.top
    if rise > SAFE_STEP + 0.5:
        return False
    g = gap(a, b)
    if g > SAFE_GAP + 0.5:
        return False
    t = air_time_to_height(max(0.0, rise))
    return g <= SAFE_FACTOR * MOVE_SPEED * t + 0.5


def audit(index, text, decorations, decor_sizes):
    warns = []
    d = parse(text)

    if len(set(d["widths"])) > 1:
        base = max(set(d["widths"]), key=d["widths"].count)
        for r, w in enumerate(d["widths"]):
            if w != base:
                warns.append(f"row {r} width {w} != {base}")
    if len(d["rows"]) != 32:
        warns.append(f"{len(d['rows'])} rows (expected 32) — check for missing newlines")
    if d["p_count"] != 1:
        warns.append(f"expected 1 'P', found {d['p_count']}")
    if d["g_count"] != 1:
        warns.append(f"expected 1 'G', found {d['g_count']}")
    for ch, r, c in d["leftovers"]:
        warns.append(f"leftover '{ch}' at (row {r}, col {c})")
    for ch, r, c in d["unknown"]:
        warns.append(f"unknown char '{ch}' at (row {r}, col {c})")

    if d["start"]:
        sx, gy, sr, sc = d["start"]
        if (sc, sr + 1) not in d["solid_cells"]:
            warns.append(f"'P' (row {sr}, col {sc}) not on solid ground")

    nodes = [(p, True) for p in d["platforms"]]
    nodes += [(o, False) for o in d["one_way"]]
    nodes += [(m, True) for m in d["movers"]]

    # rope_bridge decorations create real one-way surfaces
    bridges = []
    for dec in decorations:
        if dec["type"] != "rope_bridge":
            continue
        wt = dec.get("width", decor_sizes.get("rope_bridge", (4, 1))[0])
        br = Rect(dec["col"] * TILE, (dec["row"] + SKY_ROWS) * TILE, wt * TILE, 12)
        bridges.append(br)
        nodes.append((br, False))

    start_i = -1
    if d["start"]:
        sx, gy = d["start"][0], d["start"][1]
        for i, (r, _s) in enumerate(nodes):
            if abs(r.top - gy) < 2 and r.left <= sx <= r.right:
                start_i = i
                break
    reach = [False] * len(nodes)
    if start_i >= 0:
        reach[start_i] = True
        frontier = [start_i]
        while frontier:
            i = frontier.pop()
            for j in range(len(nodes)):
                if not reach[j] and can_edge(nodes[i][0], nodes[j][0]):
                    reach[j] = True
                    frontier.append(j)
    else:
        warns.append("spawn surface not found — cannot start reachability search")

    for i, (r, _s) in enumerate(nodes):
        if not reach[i]:
            warns.append(f"UNREACHABLE surface {r.rowcol()}")

    for i, (r, _s) in enumerate(nodes):
        for (o, osolid) in nodes:
            if osolid and o is not r and o.overlaps_x(r) and o.bottom < r.top \
                    and r.top - PLAYER_H < o.bottom <= r.top:
                warns.append(f"LOW CEILING over {r.rowcol()} — "
                             f"{r.top - o.bottom}px clearance, player is {PLAYER_H}px")
                break

    for (cx, cgy, r, c) in d["checkpoints"]:
        if not any(reach[i] and rr.left <= cx <= rr.right and abs(rr.top - cgy) < 4
                   for i, (rr, _s) in enumerate(nodes)):
            warns.append(f"UNREACHABLE checkpoint (row {r}, col {c})")

    if d["goal"] is not None:
        g = d["goal"]
        if not any(reach[i] and rr.left <= g.centerx <= rr.right
                   and -40 <= rr.top - g.bottom <= MAX_JUMP_H
                   for i, (rr, _s) in enumerate(nodes)):
            warns.append(f"UNREACHABLE goal 'G' {g.rowcol()}")
    else:
        warns.append("MISSING goal 'G'")

    for run in d["spike_runs"]:
        if run.w > SAFE_GAP:
            warns.append(f"spike run {run.rowcol()} {run.w}px wide "
                         f"(safe {SAFE_GAP:.0f}px)")
        if not [rr for (rr, _s) in nodes
                if run.right - TILE <= rr.left <= run.right + SAFE_GAP
                and abs(rr.top - run.top) <= SAFE_STEP]:
            warns.append(f"spike run {run.rowcol()} has no landing spot after it")
    for run in d["water_runs"]:
        if run.w > SAFE_GAP:
            warns.append(f"water gap {run.rowcol()} {run.w}px wide "
                         f"(safe {SAFE_GAP:.0f}px)")
        if not [rr for (rr, _s) in nodes
                if run.right - TILE <= rr.left <= run.right + SAFE_GAP]:
            warns.append(f"water gap {run.rowcol()} has no landing spot after it")

    surfaces = [r for (r, _s) in nodes]
    for dec in decorations:
        t = dec["type"]
        if t in SURFACELESS_DECOR:
            continue
        wt, ht = decor_sizes.get(t, (1, 1))
        wt, ht = dec.get("width", wt), dec.get("height", ht)
        row, col = dec["row"], dec["col"]
        x = col * TILE
        pw, ph = wt * TILE, ht * TILE
        top = (row + SKY_ROWS) * TILE - ph
        body = Rect(x, top, pw, ph)
        if t != "crate" and any((c, r) in d["solid_cells"]
                                for r in range(row - ht, row)
                                for c in range(col, col + wt)):
            warns.append(f"decor '{t}' (row {row}, col {col}) inside solid blocks")
        foot = (row + SKY_ROWS) * TILE
        if not any(abs(s.top - foot) <= TILE and s.overlaps_x(body) for s in surfaces):
            warns.append(f"decor '{t}' (row {row}, col {col}) floats — no surface at feet")
        if t == "crate":
            above = [s for s in surfaces if s.overlaps_x(body) and s.top < body.top]
            if above and not any(s.top <= body.top - PLAYER_H for s in above):
                warns.append(f"crate (row {row}, col {col}) may block the path")

    tag = "OK" if not warns else f"{len(warns)} WARNING(S)"
    print(f"[validate] level {index + 1}: {len(nodes)} surfaces, {sum(reach)} reachable, "
          f"{d['cols']}x{len(d['rows'])} — {tag}")
    for w in warns:
        print(f"  [level {index + 1}] {w}")
    return warns


def main():
    print(f"[validate] jump height {MAX_JUMP_H:.1f}px, airtime {AIR_TIME:.1f}f, "
          f"distance {MAX_JUMP_D:.1f}px")
    print(f"[validate] safe limits ({int(SAFE_FACTOR * 100)}%): step {SAFE_STEP:.1f}px, "
          f"gap {SAFE_GAP:.1f}px | player {PLAYER_H}px tall vs {TILE}px tiles")
    try:
        import data
    except Exception as exc:
        print(f"[validate] CANNOT RUN — import data failed: {exc}")
        return 2
    missing = [n for n in ("LEVEL_LAYOUTS", "LEVEL_THEMES", "DECORATIONS", "DECOR_SIZES")
               if not hasattr(data, n)]
    if missing:
        print(f"[validate] CANNOT RUN — data.py missing: {', '.join(missing)}")
        return 2
    total = 0
    for i, lay in enumerate(data.LEVEL_LAYOUTS):
        total += len(audit(i, lay, data.DECORATIONS.get(i, []), data.DECOR_SIZES))
    print(f"[validate] done — {total} warning(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())