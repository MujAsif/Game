<div align="center">

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║        T H E   T H R E E   T R I A L S                           ║
║        ─────────────────────────────────                         ║
║        A  P Y T H O N  J O U R N E Y                             ║
║                                                                  ║
║        six travelers · five ascents · one flag                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

**A hand-built 2D platformer in pure Python + pygame.**
Autotiled terrain, a sprite-slicing pipeline, synthesized audio, a jump-reachability
auditor, and six characters with distinct movement perks — **zero binary assets required.**

![Python](https://img.shields.io/badge/python-3.9%2B-68B0F2?style=flat-square&logo=python&logoColor=white)
![pygame](https://img.shields.io/badge/pygame-2.1.3%2B-56D6A6?style=flat-square)
![Dependencies](https://img.shields.io/badge/dependencies-pygame%20only-F6C45C?style=flat-square)
![Assets](https://img.shields.io/badge/art%20assets-optional-FF8ABA?style=flat-square)
![Modes](https://img.shields.io/badge/modes-1%20playable%20%2F%203-DC3C50?style=flat-square)
![Resolution](https://img.shields.io/badge/canvas-1100%C3%97650%20%40%2060fps-9CAEC2?style=flat-square)

</div>

---

## Table of contents

1. [What this is](#what-this-is)
2. [Quick start](#quick-start)
3. [Controls](#controls)
4. [The six travelers](#the-six-travelers)
5. [The five trials](#the-five-trials)
6. [Game systems](#game-systems)
7. [Level format](#level-format)
8. [The reachability auditor](#the-reachability-auditor)
9. [Optional art pipeline](#optional-art-pipeline)
10. [Architecture](#architecture)
11. [Configuration](#configuration)
12. [Audio design](#audio-design)
13. [Art direction](#art-direction)
14. [Troubleshooting](#troubleshooting)
15. [Known gaps](#known-gaps)
16. [Roadmap](#roadmap)
17. [Project layout](#project-layout)

---

## What this is

**The Three Trials** is a single-player side-scrolling platformer rendered entirely at
runtime. Every terrain tile, lantern glow, sakura petal, hero silhouette, heart icon and
sound wave is generated procedurally in Python — the game boots and plays to completion
with **no image or audio files on disk at all**.

Drop art in and it upgrades itself: a magenta-keying sheet slicer, a connected-component
hero extractor, and a parallax background loader each detect their inputs and silently
replace the procedural fallbacks.

The menu offers three trials. **Trial I — The Ascent** is the complete, five-level
platformer described in this document. Trials II and III are wired into the menu, scene
router and mode plumbing, and currently present a styled "coming in the full release"
panel.

> The OS window caption reads `RISE TO THE FLAG — Premium Edition`; the in-game title
> card reads **THE THREE TRIALS**. Both names refer to this project.

### Highlights

| | |
|---|---|
| 🎮 **Complete loop** | Menu → character select → 5 levels → victory → replay, with pause, restart and settings reachable at every step |
| 🧗 **Tuned movement** | Coyote time, jump buffering, variable jump height on key release, air control, ground friction, landing squash |
| 🗺️ **Text-map levels** | Levels are ASCII grids — edit a string, reload, play. No editor, no JSON |
| 🧱 **Autotiling** | 16-tile sheet resolved per cell from its 4-neighbour mask, plus deterministic grass tufts and hanging roots |
| 🔍 **Boot-time auditor** | BFS over every standable surface proves each platform, coin and exit is reachable *before you play* |
| 🧑‍🎨 **Six heroes** | Distinct stats, accent colours, scarf physics and procedural vector fallbacks |
| 🔊 **Synthesized audio** | 8 SFX + a 12-second ambient chord loop, generated sample-by-sample at startup |
| 🖼️ **Optional art** | Raw AI sheets → keyed, sliced, cached game assets, automatically |
| 📐 **Resolution independent** | Fixed 1100×650 logical canvas, letterboxed and smooth-scaled to any window or fullscreen |
| ⚡ **Cached everything** | Gradients, pills, panels, glows, hearts, stars, petals, scaled sprites and decor all memoized |

---

## Quick start

### Requirements

| | |
|---|---|
| **Python** | 3.9 or newer |
| **pygame** | 2.1.3+ (2.5.x recommended — `pygame.image.tobytes` / `frombytes` are used) |
| **Everything else** | Standard library only. No numpy, no Pillow, no asset downloads |
| **Display** | Any desktop OS with a video driver. Audio is optional and fails silent |

### Install and run

```bash
# 1 — clone or copy the project folder
cd the-three-trials

# 2 — create an isolated environment (recommended)
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3 — install the single dependency
pip install "pygame>=2.5.0"

# 4 — play
python main.py
```

`main.py` is the only entry point. It initializes pygame, builds the font set, allocates
the three render surfaces (`screen`, `canvas`, `world`), and hands control to `Game.run()`.

**First launch** may pause on a *SUMMONING THE COMPANY* progress screen while the hero
sheet is sliced. That work is cached to `assets/sprites/_cache/` and skipped on every
subsequent launch. With no `heroes.png` present, startup is instant.

### Font selection

The game probes for, in order:

- **UI:** Segoe UI → SF Pro Display → Inter → Ubuntu → DejaVu Sans → Arial
- **Mono:** Consolas → JetBrains Mono → Fira Code → DejaVu Sans Mono → Courier New

If none are found it falls back to pygame's bundled font. Nothing breaks; the type just
gets plainer.

---

## Controls

### Trial I — The Ascent (gameplay)

| Action | Keys |
|---|---|
| Move | `A` / `D` or `←` / `→` |
| Jump | `W`, `↑` or `Space` |
| Short hop | **Tap and release** jump — release early cuts upward velocity to 56% |
| Full jump | **Hold** jump through the rise |
| Featherfall *(FEN only)* | **Hold** jump while falling — 42% gravity, 50% terminal velocity |
| Pause | `Esc` or `P` |

### Main menu

| Action | Keys |
|---|---|
| Trial I — The Ascent | `1` or click |
| Trial II — The Labyrinth | `2` or click |
| Trial III — The Storm | `3` or click |
| Settings | `S` or click |
| Quit | `Esc` or click |

### Character select

| Action | Keys |
|---|---|
| Cycle traveler | `←` / `→` or `A` / `D` |
| Quick pick | `1`–`6` (numpad works too) |
| Begin the run | `Enter`, `Space` or `E` |
| Begin via mouse | Click a card to select, **click it again** to begin |
| Back | `Esc` |

### Pause · Settings · Victory

| Scene | Keys |
|---|---|
| **Paused** | `Esc` → main menu · buttons: Resume / Restart / Main Menu |
| **Settings** | `Esc` → return to wherever you came from · drag the volume sliders |
| **Victory** | `Enter` or `Space` → play again · `Esc` → main menu |

### Mouse

Every button, card and slider is mouse-driven. Coordinates are converted through the
letterbox viewport, so clicks land correctly at any window size or in fullscreen.
Volume sliders track while dragged and release on mouse-up.

---

## The six travelers

Each traveler changes how the run *feels*, not just how it looks. Selection persists
across levels and is shown in the menu chip, the HUD chip, the pause header and the
victory portrait.

| # | Name | Title | Perk | Effect |
|:-:|---|---|---|---|
| 1 | **ASH** | The Wayfarer | `STEADY GRIP` | +4 frames coyote time, +3 frames jump buffer |
| 2 | **LYRA** | The Ember Scholar | `HIGHER LEAP` | Jump velocity ×1.07 — roughly half a tile more height |
| 3 | **ALDRIC** | The Sentinel | `+1 HEART` | Starts every level with **6** hearts instead of 5 |
| 4 | **NYX** | The Shadow | `SPEED +18%` | Top speed ×1.18, acceleration ×1.15 |
| 5 | **MIRAE** | The Rune Weaver | `SOFT RECOVERY` | Double invincibility window after a hit |
| 6 | **FEN** | The Verdant Scout | `FEATHERFALL` | Hold jump while descending to glide onto distant ledges |

> ⚠️ **Three perks are declared but not yet applied by the physics code.**
> ALDRIC, NYX and FEN are fully live. ASH, LYRA and MIRAE currently play identically to
> baseline. See [Known gaps](#known-gaps) for the exact one-line fixes.

### Stat pips

The detail panel reads five-point pips straight from `ROSTER`:

| Traveler | SPEED | LEAP | HEART | GRIP | FORTUNE |
|---|:-:|:-:|:-:|:-:|:-:|
| ASH | 3 | 3 | 3 | 5 | — |
| LYRA | 3 | 5 | 3 | — | — |
| ALDRIC | 2 | 2 | 5 | — | 2 |
| NYX | 5 | 3 | 3 | — | 2 |
| MIRAE | 3 | 3 | 3 | 4 | — |
| FEN | 3 | 5 | 3 | — | 3 |

---

## The five trials

| # | Level | Region | Width | Platforms | Coins | Accent |
|:-:|---|---|--:|--:|--:|---|
| 1 | **The Sakura Sanctum** | Twilight shrine | 3260 px | 14 | 20 | `#FF8ABA` |
| 2 | **The Ember Canopy** | Desert dunes | 2800 px | 12 | 6 | `#F8A46C` |
| 3 | **The Verdant Hollow** | Jungle ruins | 3000 px | 13 | 7 | `#62DCAA` |
| 4 | **The Frostbound Ridge** | Snowfield | 2600 px | 14 | 8 | `#7CD0FC` |
| 5 | **The Moonlit Cascades** | Twilight falls | 3400 px | 13 | 24 | `#FF8ABA` |

Each region carries its own sky gradient, celestial body colour, three mountain-ridge
layers, ground gradient, accent and mote colour, and prop palette. Themes swap on level
transition and the sky, background and terrain surfaces are rebuilt.

**Perfect run:** 65 coins × 50 + 5 exits × 500 = **5,750 points.**

---

## Game systems

### Movement physics

All values are **per frame at 60 fps**, scaled by `dt_scale` so behaviour stays consistent
if a frame runs long.

| Constant | Value | Meaning |
|---|--:|---|
| `GRAVITY` | 0.78 | Downward acceleration |
| `JUMP_SPEED` | −14.8 | Initial jump velocity |
| `MAX_FALL_SPEED` | 16.5 | Terminal velocity (990 px/s) |
| `MOVE_SPEED` | 5.2 | Top horizontal speed (312 px/s) |
| `ACCEL_GROUND` | 0.90 | Ground acceleration |
| `ACCEL_AIR` | 0.60 | Air acceleration — deliberate, committed jumps |
| `FRICTION_GROUND` | 0.75 | Ground decay when no input |
| `FRICTION_AIR` | 0.92 | Air decay — momentum carries |
| `TILE` | 40 | Grid unit |

### Derived jump envelope

Printed to the console at boot and used as the auditor's ground truth:

```
MAX_JUMP_H = JUMP_V² / (2 · GRAVITY)     = 140.4 px   ≈ 3.51 tiles
AIR_TIME   = 2 · JUMP_V / GRAVITY        =  37.9 f    ≈ 0.63 s
MAX_JUMP_D = MOVE_SPEED · AIR_TIME       = 197.3 px   ≈ 4.93 tiles

SAFE_STEP  = 0.75 · MAX_JUMP_H           = 105.3 px   ≈ 2.63 tiles
SAFE_GAP   = 0.75 · MAX_JUMP_D           = 148.0 px   ≈ 3.70 tiles
```

The **75% safety margin** is the design contract: every authored jump must be clearable
with room for imperfect timing.

### Forgiveness windows

| System | Frames | Behaviour |
|---|:-:|---|
| **Coyote time** | 7 | Jump still fires up to 7 frames after leaving a ledge |
| **Jump buffer** | 7 | Pressing jump up to 7 frames before landing still fires on contact |
| **Jump cut** | — | Releasing jump while rising faster than −5.5 multiplies velocity by 0.56 |
| **Invincibility** | 60 | One second of hazard immunity after a hit; sprite blinks every 3 frames |
| **Hurt flash** | 16 | Red tint pulse on the sprite |
| **Landing squash** | ~7 | Sprite compresses 10% and recovers at 0.14/frame |

### Collision

Movement resolves on **separate axes** — horizontal first, then vertical — against
`platforms + crate_solids + mover rects`:

- **Horizontal:** push out to the touching edge, zero `vx`.
- **Vertical down:** land only if `prev_bottom <= surface.top + 14` (no snapping through floors).
- **Vertical up:** bonk only if `rect.top >= surface.bottom - 14`, zero `vel_y`.
- **One-way (`-`, rope bridges):** land only when descending and previously above the cap.
- **Movers:** on landing, the player latches to the platform and inherits `last_dx` each
  frame, gated by a collision test so a moving platform never pushes you into a wall.

### Hazards & respawn

| Hazard | Trigger | Popup |
|---|---|---|
| **Floor spikes** `^` | Overlap a 24 px strip inset 6 px per side | `SPIKED` |
| **Ceiling spikes** `v` | Overlap a 24 px downward strip | `SPIKED` |
| **Water** `~` | Any overlap | `DROWNED` |
| **The void** | `rect.top > level_height + 60` | `FELL` |

On a hit: lose one heart, respawn at the last activated checkpoint `K` (or the level
spawn `P`), zero all velocity, detach from movers, snap the camera, play the failure tone.

**Running out of hearts is not a permanent game over.** The level rebuilds, hearts refill
to max, and the score rolls back to its value at level entry. There is no dead-end state —
the run always continues.

### Scoring

| Event | Points |
|---|--:|
| Coin `c` | **+50** |
| Exit flag `G` | **+500** |
| Checkpoint `K` | 0 — sets respawn anchor |
| Heart lost | 0 — but hearts refill only on level restart |
| Hearts exhausted | Score resets to level-entry value |

The HUD score **lerps** toward the true value at 0.16/frame, so gains count up rather than
snap. Coin pickups spawn a 10-particle gold burst; the exit spawns 45.

### Camera & depth

The camera lerps at `0.14 · dt_scale` toward the player, biased **30 px upward** so you see
what you're jumping into, and clamped to the level bounds on both axes.

Five independent parallax rates build depth:

| Layer | Rate |
|---|---|
| Background art | `0.05–0.50`, auto-derived from art width vs. level width |
| Clouds | `0.10` |
| Ambient motes | `0.25` |
| Foreground petals | `0.35` |
| Terrain & entities | `1.00` |

### Ambient life

26 drifting sakura petals (sine sway, cached rotation frames) · 38 pulsing motes ·
3 translucent clouds · flickering radial glows on lanterns and shrines · animated
waterfall streaks and mist · spinning coins with pulse-modulated halos · waving
checkpoint and exit flags · a four-point verlet-ish scarf that trails every hero.

---

## Level format

Levels are **ASCII grids**. One character = one 40×40 cell. Row 0 sits `SKY_ROWS = 5`
tiles (200 px) below the world origin, so there is always headroom above the top row.

### Legend

| Char | Element | Notes |
|:-:|---|---|
| `=` `\|` | **Solid terrain** | Runs merge into one rect; autotiled from neighbours |
| `-` | **One-way platform** | 12 px cap at the cell bottom; land from above only |
| `M` | **Moving platform** | 14 px thick, patrols ±3 tiles at 1.4 px/frame, carries the player |
| `^` | **Spiked floor** | Solid cell **plus** a 24 px spike strip on top |
| `v` | **Ceiling spikes** | 24 px downward strip, no solid body |
| `~` | **Water** | Lethal on contact |
| `c` | **Coin** | +50, centred in the cell |
| `K` | **Checkpoint** | Flag pole; sets respawn on touch |
| `P` | **Player spawn** | Feet placed on the cell bottom |
| `G` | **Exit flag** | +500, advances the level |
| ` ` | Empty | — |

A leading and trailing `|` on each line is stripped as a decorative frame — interior `|`
characters remain solid. Short lines are right-padded to the widest row.

### Example

```python
LEVEL_LAYOUTS = [
"""
|                                        |
|              c c c                     |
|            =====                       |
|      c                    c c          |
|    -----        MM        ====         |
|  c                            c        |
| ====      ^^        ~~~~      ===  G   |
| P                                  ====|
|====  K  ============================   |
""",
]
```

### Adding a level

1. Append a grid string to `LEVEL_LAYOUTS` in `data.py`.
2. Append a matching theme dict to `LEVEL_THEMES`.
3. Optionally append a prop list to `DECORATIONS`.
4. Update the `LEVEL {n}/5` label in `Game.draw_hud`.
5. Launch — the auditor validates it automatically before you can play it.

---

## The reachability auditor

On the first level load, `audit_level()` runs a **breadth-first search over every standable
surface** in every level and reports problems to the console.

**Graph nodes:** all solid platforms, all one-way platforms, and every mover at its start
position.

**An edge A → B exists when all three hold:**

```
rise = A.top - B.top   ≤  SAFE_STEP                       (105.3 px)
gap  = horizontal_gap  ≤  SAFE_GAP                        (148.0 px)
gap                    ≤  0.75 · MOVE_SPEED · airtime(rise)
```

The third condition is the honest one — it computes the *actual* frames available to
cross a gap at a given rise, rather than trusting the flat maximum.

**Warnings emitted:**

| Warning | Meaning |
|---|---|
| `UNREACHABLE platform (row r, col c)` | No safe path from spawn reaches this surface |
| `LOW CEILING over platform (row r, col c)` | A solid sits within 60 px above a standable top |
| `UNREACHABLE coin #n (row r, col c)` | No reachable surface can put the coin within jump height |
| `UNREACHABLE exit (row r, col c)` | The flag cannot be reached from spawn |
| `MISSING exit G` | The grid has no goal character |

**Sample output:**

```
[jump] height=140.4px airtime=37.9f distance=197.3px | safe step=105.3px safe gap=148.0px
[audit] level 1: 14 surfaces, 14 reachable — OK
[audit] level 2: 12 surfaces, 11 reachable — 1 WARNING(S)
  [level 2] UNREACHABLE coin #4 (row 3, col 30)
```

This turns level design from guesswork into a checked invariant.

---

## Optional art pipeline

**Nothing here is required.** Every path below has a procedural fallback. Add files and
the game upgrades itself; remove them and it degrades cleanly.

### 1 — Raw sheet conversion (`asset_prep.py`)

Place magenta-background sheets in `assets/raw/`:

```
assets/raw/tiles.png    8 columns × 2 rows of terrain tiles
assets/raw/props.png    4 columns × 3 rows of decorations
assets/raw/bg1.png      level 1 parallax background
assets/raw/bg2.png      level 2 parallax background
assets/raw/bg3.png      level 3 parallax background
```

Run the converter (it needs a display surface for `convert_alpha`):

```bash
python -c "import pygame; pygame.init(); pygame.display.set_mode((1,1)); import asset_prep; print(asset_prep.ensure())"
```

It will:

- **Key out magenta** — pixels with `R>150, B>150, G<90` get alpha ramped from the green channel.
- **Slice tiles** by scanning column occupancy in each half, cropping to the alpha bounding box, and smooth-scaling to 32×32.
- **Slice props** into the 4×3 grid, trim, and scale each to its authored pixel height (torii 96, sakura tree 110, waterfall 120, crate 30, …).
- **Normalize backgrounds** to 650 px tall, preserving aspect.
- **Write results** to `assets/tiles/`, `assets/props/`, `assets/bg/`.
- **Record mtimes + sizes** in `assets/raw/.prep_state.json` and skip all work when nothing changed.

The whole routine is wrapped in a `try` — any failure prints a skip notice and the game
continues on fallbacks.

### 2 — Hero sheet (`sprites.py`)

Place **`assets/sprites/heroes.png`**: six rows, one character per row in `ROSTER` order
(ASH, LYRA, ALDRIC, NYX, MIRAE, FEN), poses left to right.

The pipeline is genuinely non-trivial:

1. **Background detection** — samples the border, classifies transparent / white / black / solid, then flood-fills inward from every edge. Interior white shirts survive; the page behind them does not.
2. **Row banding** — finds horizontal occupancy bands; falls back to six equal slices if the count disagrees with the roster.
3. **Connected components** — one bounding box per pose, immune to stray feet or hat-tips bleeding in from neighbouring rows.
4. **Side merging** — re-attaches capes and ponytails that vertically overlap a body, while refusing to merge vertically stacked fragments.
5. **Wide splitting** — cuts touching figures at the lowest-occupancy column in the middle 40%.
6. **Repacking** — every pose is re-anchored into an equal-size cell on a **shared foot baseline** and a **head-centred horizontal axis**, so animations never jitter.
7. **Animation mapping** — pose count determines the split:

   | Poses | idle | walk | run | air | crouch |
   |--:|---|---|---|---|---|
   | ≥ 8 | 2 | 4 | remainder | rise + fall | fall |
   | 4–7 | 1 | middle | = walk | rise + fall | fall |
   | 1–3 | all | = idle | = walk | last | last |

8. **Disk cache** — cells and anchors are written to `assets/sprites/_cache/` keyed on
   `PIPELINE_VERSION` + file mtime + size.

**Force a re-slice** after editing the sheet or changing the pipeline:

```bash
rm -rf assets/sprites/_cache
```

### 3 — Direct drop-in paths

Already-clean art can skip conversion entirely.

| Asset | Search order |
|---|---|
| **Title background** | `assets/ui/title_bg.png` → `assets/title_bg.png` → `title_bg.png` |
| **Tileset** (8×2, 16 tiles) | `assets/tiles/sakura_tiles.png` → `assets/tiles/tiles.png` → `assets/sprites/sakura_tiles.png` → `assets/tileset.png` → cwd |
| **Individual props** | `assets/props/` → `assets/sprites/` → `assets/props/props/` → `assets/` → cwd |
| **Prop sheet** (4×3) | `assets/props/decorations.png` → `assets/sprites/decorations.png` → `assets/props/props.png` → `assets/props.png` → cwd |
| **Level background** | `assets/bg/level{N}.png` → `assets/bg/bg{N}.png` |

**Prop filenames:** `torii`, `stone_lantern`, `lantern_post`, `banner`, `shrine`,
`sakura_tree`, `bush_pink`, `crate`, `fence`, `signpost`, `rope_bridge`, `waterfall`.

Crates become **solid collision**; rope bridges become **one-way collision**; waterfalls
are **decorative only**. Everything else is scenery.

---

## Architecture

### Module map

| File | Lines of responsibility |
|---|---|
| **`main.py`** | Entry point. `pygame.init()`, font probing, surface allocation, `Game().run()`, guaranteed `pygame.quit()` |
| **`config.py`** | All tunables: display, tilemap, physics, gameplay, sprite paths, palette. Owns the global `screen` / `canvas` / `world` / `clock` / `fonts` |
| **`game.py`** | The orchestrator. Level parsing, autotiling, camera, collision, hazards, scoring, the auditor, every scene's draw + input routing, and the frame loop |
| **`data.py`** | Level content, per-region themes, decoration placement, question banks for future modes |
| **`entities.py`** | `Player`, `Particle`, `FloatingText`, `MovingPlatform` |
| **`sprites.py`** | `ROSTER` definitions + the hero-sheet extraction pipeline + `SpriteBank` with scaled-frame memoization |
| **`character_select.py`** | The roster screen: engraved cards, accent rims, stat pips, live run preview, vector fallback heroes |
| **`ui.py`** | Drawing toolkit: text, wrapping, gradients, panels, pills, radial glows, supersampled hearts and stars, veils, `Button` |
| **`audio.py`** | Sample-level tone / chord / ambient synthesis and `AudioManager` |
| **`asset_prep.py`** | Raw-sheet → game-asset conversion with change detection |

### Dependency direction

```
main.py
   └── game.py ──┬── config.py        (constants + globals; imported by everything)
                 ├── data.py         (content only — no engine imports)
                 ├── entities.py ────┬── sprites.py ── ui.py
                 ├── sprites.py ─────┘
                 ├── character_select.py
                 ├── ui.py
                 └── audio.py

asset_prep.py      (standalone; run manually)
```

`config.py` and `ui.py` are leaves. `data.py` holds content and never imports the engine.
There is no circular dependency.

### Render pipeline

Three surfaces, one direction:

```
world  (1100×650)  ← sky · bg art · clouds · motes · decor · terrain · water ·
                     movers · coins · checkpoints · flag · player · particles · popups
   │
   ├─ blit with screen-shake offset ──▶ canvas (1100×650)
   │                                     ← petals · HUD · scene overlays · fade veil
   │
   └─ letterbox smoothscale ──────────▶ screen (any size / fullscreen)
```

The logical canvas is **always** 1100×650. Resizing changes only the final scale, so
layout, hit-testing and physics are resolution-independent. `convert_mouse()` maps
physical pointer coordinates back through the viewport rect.

### Scene state machine

```
MENU ──1──▶ CHARACTER_SELECT ──Enter──▶ PLAYING ──G──▶ PLAYING (next level)
 │  ▲              │ Esc                  │ Esc/P            │
 │  └──────────────┘                      ▼                  └─ level 5 ─▶ VICTORY
 ├──2/3──▶ PLACEHOLDER_GAME            PAUSED                                │
 ├──S────▶ SETTINGS ◀────────────────────┘                                   │
 └──Esc──▶ quit         ▲                                                    │
                        └──────────────── Enter / Esc ───────────────────────┘
```

`change_scene()` resets the button list and triggers a 160-alpha fade that decays at
14/frame. Buttons are cached by key and reused across frames, so hover and press
animations survive redraws.

### Frame loop

```python
dt_scale = clamp(clock.tick(60) / 16.667, 0.35, 2.0)   # never spiral, never freeze
frame   += dt_scale
mouse    = convert_mouse(pygame.mouse.get_pos())
handle_events()
if scene == "PLAYING" and mode == 0:
    update_gameplay()
draw_scene()
present_letterboxed()
```

Every timer, velocity, lerp and particle integrates against `dt_scale`.

### Caching

| Cache | Owner | Eviction |
|---|---|---|
| Gradients, pills, panels, glows, hearts, stars | `ui._SURFACE_CACHE` | clear at 260 entries |
| Menu gradients, petal rotations | `game._MENU_CACHE` | clear at 60 entries |
| Scaled + flipped + tinted sprite frames | `SpriteBank._cache` | clear at 1400 entries |
| Scaled decor surfaces | `Game._decor_scaled` | clear at 120 entries |
| Sliced hero cells | `assets/sprites/_cache/` | invalidated by version + mtime + size |
| Converted raw sheets | `assets/raw/.prep_state.json` | invalidated by mtime + size |

---

## Configuration

Everything worth tuning lives in **`config.py`**.

```python
# Display
WIDTH, HEIGHT = 1100, 650
FPS           = 60
GROUND_Y      = 544

# Tilemap
TILE      = 40
SKY_ROWS  = 5          # empty sky rows above every level

# Physics — see the derived envelope above before changing these
GRAVITY        = 0.78
MAX_FALL_SPEED = 16.5
JUMP_SPEED     = -14.8
MOVE_SPEED     = 5.2
ACCEL_GROUND   = 0.90
ACCEL_AIR      = 0.60
FRICTION_GROUND = 0.75
FRICTION_AIR    = 0.92

# Gameplay
MAX_HEARTS = 5

# Sprites
SPRITE_DIR           = "assets/sprites"
PLAYER_SPRITE_H      = 54
SPRITE_SOURCE_FACING = 1     # set to -1 if your sheet faces left
```

> **Changing `JUMP_SPEED`, `GRAVITY` or `MOVE_SPEED` re-derives the entire safe-jump
> envelope.** The auditor picks up the new limits automatically and will immediately
> flag any level that no longer clears them. That is the intended workflow.

### In-game settings

Reachable from the menu (`S`), persisted for the session:

| Setting | Default | Control |
|---|---|---|
| Music volume | 28% | drag slider |
| Sound effects | 62% | drag slider |
| Fullscreen | Off | toggle button |
| Particles | On | toggle button |

Turning particles off suppresses dust, jump rings, landing rings and pickup bursts —
the cheapest available performance lever.

---

## Audio design

**No audio files exist.** Every sound is synthesized sample-by-sample at 22,050 Hz,
16-bit mono, at startup.

| Cue | Synthesis |
|---|---|
| `jump` | 340 Hz triangle, 0.13 s, **+180 Hz slide** |
| `land` | 125 Hz triangle, 0.08 s, −40 Hz slide |
| `coin` | 920 Hz bell (3 harmonics), 0.08 s, +240 Hz slide |
| `correct` | C-major arpeggio, C5→E5→G5→C6 |
| `wrong` | 190 Hz triangle, 0.25 s, −55 Hz slide |
| `click` | 580 Hz bell, 45 ms |
| `level` | Five-note ascending fanfare to E6 |
| `lower` | 180 Hz sine, 0.4 s, −80 Hz slide |

**Ambient music** is a 12-second seamless loop: four chords (Am → C → Dm → G), each held
three seconds, four sine partials per chord with a slow tremolo on the top voice and a
`sin(πt)^0.45` crossfade envelope per bar.

Every tone uses an attack/release envelope — 6% attack, power-curve decay — so nothing
clicks. The mixer reserves **16 channels** and grabs a free one per cue, so rapid coin
pickups never starve the jump sound.

**Failure is silent, never fatal.** If `pygame.mixer.init()` raises, `available` stays
`False`, every `play()` returns immediately, and the game runs perfectly without sound.

---

## Art direction

The palette is derived from the subject — twilight shrines, ember dunes, verdant hollows
and frostbound ridges — not from a generic UI kit.

### Core palette

| Token | Hex | Role |
|---|---|---|
| `INK` | `#0C131F` | Letterbox, base fill, deepest shadow |
| `WHITE` | `#F5F8FC` | Primary text |
| `MUTED` | `#9CAEC2` | Secondary text, inactive labels |
| `SUBTLE` | `#5C6E82` | Empty hearts, empty pips, dormant flags |
| `GOLD` | `#F6C45C` | Coins, score, exit flag, primary actions |
| `GOLD_SOFT` | `#FFE4A8` | Subtitles, coin highlights |
| `MINT` | `#56D6A6` | Checkpoints, success, resume |
| `CORAL` | `#F26270` | Hearts, damage, destructive actions |
| `BLUE` | `#68B0F2` | Information, navigation, ASH |
| `CRIMSON` | `#DC3C50` | Title shadow, procedural menu accent |

### Regional accents

| Trial | Accent | Sky top → bottom |
|---|---|---|
| I · Sakura Sanctum | `#FF8ABA` | `#120C28` → `#E25C84` |
| II · Ember Canopy | `#F8A46C` | `#87CEEB` → `#FFE4B5` |
| III · Verdant Hollow | `#62DCAA` | `#0F1C2E` → `#386266` |
| IV · Frostbound Ridge | `#7CD0FC` | `#0D1830` → `#3A6086` |
| V · Moonlit Cascades | `#FF8ABA` | `#120C28` → `#E25C84` |

### UI language

Pills and panels are built from **layered offset shadow boxes** — three passes at
decreasing offset and increasing alpha — rather than a single hard drop shadow. Gradients
are rendered line-by-line and masked to a rounded rect. Hearts and stars are drawn at **3×
and smooth-downscaled**, giving clean anti-aliased curves that `pygame.draw` cannot
produce directly. Radial glows are concentric alpha rings, cached per radius/colour.

Buttons lift 2 px on hover, depress 2 px on press, and blend both fill and border toward
their accent — every interactive surface answers the pointer.

---

## Troubleshooting

### Startup

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'LEVEL_LAYOUTS' from 'data'` | `game.py` imports `LEVEL_LAYOUTS`, `DECORATIONS`, `DECOR_SIZES`; the shipped `data.py` defines a rect-based `LEVELS` list instead | Add the three symbols — see [Known gaps](#known-gaps) for the exact contract |
| `NameError: name 'file' is not defined` | `__file__` lost its underscores | Restore `__file__` in `asset_prep.py`, `game.py`, `sprites.py` |
| `SyntaxError` on `def init(self)` | Dunders lost their underscores | Restore `__init__`, `__slots__`, `__name__`, `__main__` |
| `SyntaxError` on a `── Section ──` line | Box-drawing section rules are not comments | Prefix each with `#` |
| `SyntaxError: invalid syntax` near a number | A space split a literal (`32 767`, `26 2`) | Remove the space |
| Strings like `"assets "` with a trailing space | Paste artifact inside literals | Strip the stray spaces — path and tile-character comparisons depend on them |
| `def <strong>init</strong>` in `ui.py` | HTML markup leaked into the source | Replace with `def __init__` |

> These are all **transcription damage**, not design faults. If your working copy came
> from a chat paste, run `python -m compileall .` first — it will point at every one.

### Runtime

| Symptom | Cause | Fix |
|---|---|---|
| `AttributeError: module 'pygame.image' has no attribute 'tobytes'` | pygame older than 2.1.3 | `pip install -U pygame` |
| No sound at all | Mixer init failed (no device, headless, container) | Expected and harmless — the game is designed to run silent |
| Heroes are blank or clipped | Background detection misread the sheet | Delete `assets/sprites/_cache/`, verify the sheet has six clean rows on a uniform background |
| Heroes face backwards | Sheet drawn facing left | Set `SPRITE_SOURCE_FACING = -1` in `config.py` |
| Magenta fringes on props | Key threshold too tight for anti-aliased edges | Re-export the raw sheet with harder edges, or supply pre-keyed PNGs with real alpha |
| Terrain is flat coloured blocks | No tileset found | Console prints `[game] tileset NOT found` — add `assets/tiles/sakura_tiles.png` |
| `[sprites] heroes.png NOT FOUND` | Sheet missing | Expected — vector fallback heroes are used, and the select screen shows a hint |
| Low frame rate | Particle count or software scaling | Turn **Particles: Off** in Settings; prefer windowed over a very large fullscreen |
| Clicks land in the wrong place | Letterbox mapping | Already handled by `convert_mouse()`; if you modify presentation, keep the viewport rect in sync |
| Long first-launch pause | Pure-Python component labelling over a large sheet | One-time only — the disk cache skips it afterwards |

### Reading the console

The game narrates its own asset resolution. A healthy boot looks like:

```
[jump] height=140.4px airtime=37.9f distance=197.3px | safe step=105.3px safe gap=148.0px
[sprites] assets/sprites/heroes.png (2048, 1536) bg=white
[sprites] ASH: 9 poses -> idle×2, walk×4, run×1, air×3, crouch×1
[sprites] 6 heroes · 54 frames
[game] tileset loaded: assets/tiles/sakura_tiles.png
[audit] level 1: 14 surfaces, 14 reachable — OK
```

Anything reading `NOT found`, `fallback`, `skipped` or `WARNING(S)` is a pointer to the
exact missing input.

---

## Known gaps

Listed plainly so nothing here is a surprise.

### 1 — `data.py` / `game.py` contract mismatch *(blocks startup)*

`game.py` requires three symbols that the shipped `data.py` does not define:

| Symbol | Type | Shape |
|---|---|---|
| `LEVEL_LAYOUTS` | `list[str]` | Five ASCII grids using the [legend](#legend) above |
| `DECORATIONS` | `dict[int, list[dict]]` | Level index → props, each `{"type": str, "col": int, "row": int}` with optional `"width"` / `"height"` in tiles |
| `DECOR_SIZES` | `dict[str, tuple[int, int]]` | Prop type → default `(width_tiles, height_tiles)` |

`LEVEL_THEMES` **is** present and correctly shaped. The shipped `LEVELS` list uses an
older rect-based format (`platforms`, `props`, `coins` in absolute pixels) that the
current engine no longer reads. Either author `LEVEL_LAYOUTS` grids, or write a small
adapter that rasterizes `LEVELS` into grids at load time.

### 2 — Three character perks are declared but not applied

`Player.__init__` reads `speed_mul`, `accel_mul` and `glide`. It does **not** read
`jump_mul`, `coyote_bonus`, `buffer_bonus` or `invuln_bonus`. The corresponding call
sites use hardcoded values:

| Perk | Current code | Location | Should be |
|---|---|---|---|
| ASH · coyote | `p.coyote_timer = 7.0` | `game.update_player` | `7.0 + traits["coyote_bonus"]` |
| ASH · buffer | `self.jump_buffer = 7.0` | `Player.request_jump` | `7.0 + traits["buffer_bonus"]` |
| LYRA · leap | `self.vel_y = JUMP_SPEED` | `Player.execute_jump` | `JUMP_SPEED * traits["jump_mul"]` |
| MIRAE · recovery | `p.invincible_timer = 60.0` | `game._hurt` | `60.0 + traits["invuln_bonus"]` |

Store the traits on the `Player` in `__init__`, then read them at those four sites.
ALDRIC (`bonus_hearts`, applied in `Game.new_stats`), NYX and FEN already work.

### 3 — Other notes

- **`JUMP_V`** in `game.py` must be `abs(JUMP_SPEED)`. If it reads `abs(1)`, the derived
  envelope and every audit result are wrong.
- **Trials II & III** are intentional placeholders. The question banks in `data.py`
  (`LEVEL1_QUESTIONS` … `LEVEL3_QUESTIONS`, plus `make_question_deck`) are authored and
  ready, but no quiz scene consumes them yet.
- **`_get_tile_type()`** in `game.py` is superseded by the inline neighbour-mask logic in
  `_build_terrain()` and is currently dead code.
- **`config.PHYSICS_HZ`** and **`config.SPRITE_CACHE_DIR`** are declared but unused —
  the sprite cache path is derived from the sheet's own directory.
- **`PixelArray.replace_color()`** in `Game._strip_magenta` is not a pygame API; the call
  raises, is caught, and the `set_colorkey` fallback runs. Harmless, but `arr.replace(...)`
  is the correct method.
- **No persistent save.** Settings, best score and character choice reset each launch.
- **No gamepad support.** Keyboard and mouse only.

---

## Roadmap

**Trial I — polish**
- [ ] Reconcile `data.py` with the `LEVEL_LAYOUTS` contract
- [ ] Wire the four remaining character traits
- [ ] Persist settings, best score and last traveler to a local JSON profile
- [ ] Per-level par time and a coin-completion medal on the victory screen
- [ ] Gamepad support via `pygame.joystick`

**Trial II — The Labyrinth**
- [ ] Grid-maze scene consuming the existing question banks
- [ ] Logic-and-memory puzzle loop with a move budget
- [ ] Deck shuffling through `make_question_deck()`

**Trial III — The Storm**
- [ ] Arcade survival scene with escalating waves
- [ ] Reflex scoring, combo multiplier, run leaderboard

**Engine**
- [ ] Vertical and circular mover variants
- [ ] Additional hazard types (crumbling tiles, wind zones)
- [ ] Optional in-game level editor over the ASCII format
- [ ] Rebindable keys

---

## Project layout

```
the-three-trials/
│
├── main.py                  ← RUN THIS
├── config.py                constants · physics · palette · globals
├── game.py                  orchestrator · scenes · collision · auditor
├── data.py                  levels · themes · decorations · question banks
├── entities.py              Player · Particle · FloatingText · MovingPlatform
├── sprites.py               ROSTER · hero-sheet pipeline · SpriteBank
├── character_select.py      roster screen
├── ui.py                    drawing toolkit · Button
├── audio.py                 synthesized SFX + ambient loop
├── asset_prep.py            raw sheet → game asset converter
├── README.md
│
└── assets/                  ← entirely optional
    ├── raw/                 drop AI sheets here
    │   ├── tiles.png
    │   ├── props.png
    │   ├── bg1.png  bg2.png  bg3.png
    │   └── .prep_state.json        (generated)
    │
    ├── sprites/
    │   ├── heroes.png              six rows, ROSTER order
    │   └── _cache/                 (generated — delete to re-slice)
    │       ├── index.json
    │       └── {char}_{anim}_{i}.png
    │
    ├── tiles/
    │   └── sakura_tiles.png        8 × 2 grid, 16 tiles
    │
    ├── props/
    │   ├── torii.png  stone_lantern.png  lantern_post.png  banner.png
    │   ├── shrine.png  sakura_tree.png  bush_pink.png  crate.png
    │   └── fence.png  signpost.png  rope_bridge.png  waterfall.png
    │
    ├── bg/
    │   └── level1.png … level5.png
    │
    └── ui/
        └── title_bg.png
```

---

## Credits & license

**Design, engine, art pipeline and audio synthesis** — built from scratch in Python.
No third-party assets, no external audio, no engine framework beyond pygame itself.

Built on **[pygame](https://www.pygame.org/)**, the enduring Python SDL wrapper.

Add your license of choice here (`MIT` is a reasonable default for a project of this
shape) and your name here.

---

<div align="center">

```
        ╱╲          the flag is always
       ╱  ╲         within reach —
      ╱ ▓▓ ╲        the auditor
     ╱______╲       proves it.
        │
        │  ▸
        │
   ═════╧═════
```

**Six companions walk the trials — each with a gift of their own.**

`python main.py`

</div>