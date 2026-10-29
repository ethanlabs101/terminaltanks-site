"""Shells in flight (every projectile style), the UFO, and the tiny pixel glyphs drawn on shells."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from tanks.colors import RGB, clamp, flicker, gradient, hsv, mix, shade
from tanks.content.ammo import AmmoType
from tanks.content.paints import live_color
from tanks.screen import PixelCanvas

if TYPE_CHECKING:
    from tanks.battle.tank import Tank


# 3x5 bitmaps for the ASCII easter-egg ammo (row 0 is the top of the glyph)
_GLYPH_BITS = (
    ("#.#", "###", "#.#", "###", "#.#"), ("###", "#.#", "#.#", "#.#", "###"), (".#.", "##.", ".#.", ".#.", "###"),
    ("...", ".#.", "###", ".#.", "..."), ("#.#", ".#.", "###", ".#.", "#.#"), ("#.#", "..#", ".#.", "#..", "#.#"),
    (".#.", "#.#", ".#.", "#.#", ".##"), ("..#", "..#", ".#.", "#..", "#.."),
)


def draw_glyph(canvas: PixelCanvas, x: float, y: float, k: int, col: RGB, a: float) -> None:
    for r, row in enumerate(_GLYPH_BITS[k % len(_GLYPH_BITS)]):
        for c, ch in enumerate(row):
            if ch == "#":
                canvas.blendf(x + c - 1, y + 2 - r, col, a)


def draw_ufo(canvas: PixelCanvas, t: Tank, now: float, flash: float = 0.0) -> None:
    """A big, glowing, bobbing flying saucer (drawn inside the tank's hit box so what you see is what you hit)."""
    cx = t.x + t.vis_dx
    w, h = t.width, t.height
    cy = t.y + 0.9 * math.sin(now * 2.0 + t.index)                   # bob is visual only; the hit box never moves
    if t.destroyed:
        return
    body = t.color
    firing = t.recoil > 0
    gy = t.y - t.hover                                                   # the ground under the saucer
    for dx in range(int(-w * 0.42), int(w * 0.42) + 1):                  # a shadow that shrinks/darkens with height
        k = 1 - abs(dx) / (w * 0.42)
        canvas.blendf(t.x + dx, gy, (0, 0, 0), 0.5 * k * clamp(1.2 - t.hover / 40.0, 0.35, 0.9))
        if k > 0.5:
            canvas.blendf(t.x + dx, gy + 1, (0, 0, 0), 0.25 * k)
    hull_a, hull_b = mix(body, (255, 255, 255), 0.35), shade(body, 0.45)
    for ix in range(int(-w / 2) - 1, int(w / 2) + 2):
        for iy in range(-1, int(h) + 2):
            u, v = ix / (w / 2), (iy - h * 0.40) / (h * 0.5)
            px, py = cx + ix, cy + iy
            col = None
            # saucer disc
            if (u / 1.0) ** 2 + (v / 0.42) ** 2 <= 1.0:
                shade_k = 0.5 + 0.5 * (-v / 0.42)
                col = mix(hull_b, hull_a, clamp(shade_k, 0, 1))
                if abs(v) < 0.06:                                        # glowing rim ring
                    col = mix(col, (255, 255, 255), 0.5)
            # glass dome
            dv = (iy - h * 0.52) / (h * 0.42)
            if u * u / 0.25 * 1.0 + dv * dv <= 1.0 and dv >= -0.05:
                col = mix((60, 220, 200), (190, 255, 255), clamp(0.3 + 0.7 * dv, 0, 1))
                if dv > 0.45 and u < -0.05:
                    col = mix(col, (255, 255, 255), 0.55)                # highlight
            # underside cannon pod
            if (u / 0.28) ** 2 + ((iy - h * 0.16) / (h * 0.16)) ** 2 <= 1.0:
                col = mix(shade(body, 0.3), (255, 220, 120) if firing else (90, 100, 120), 0.7 if firing else 0.3)
            if col is not None:
                if flash > 0:
                    col = mix(col, (255, 255, 255), min(1.0, flash))
                canvas.plotf(px, py, col)
    # chasing rim lights
    n = 9
    for k in range(n):
        ang = k / n * math.tau
        lx, ly = cx + math.cos(ang) * w * 0.44, cy + h * 0.40 + math.sin(ang) * h * 0.14
        on = int(now * 6 + k) % 3 == 0
        canvas.plotf(lx, ly, hsv((k / n + now * 0.2) % 1, 0.5, 1.0) if on else shade(body, 0.4))
    for dy in range(1, int(min(8, t.hover)) + 1):                        # thruster glow separating it from the ground
        canvas.blendf(cx, cy + h * 0.1 - dy, (150, 255, 200), 0.38 - dy * 0.04 + 0.1 * math.sin(now * 14 + dy))
    if firing or int(now * 3) % 5 == 0:                                  # tractor-beam glow under the cannon
        for dy in range(1, 6):
            canvas.blendf(cx, cy + h * 0.08 - dy, (170, 255, 200), 0.5 - dy * 0.08)
    if t.shield > 0:                                                     # shimmering shield bubble
        for k in range(int(w * 4)):
            ang = k / (w * 4) * math.tau
            fl = 0.35 + 0.3 * math.sin(now * 9 + k * 0.7)
            canvas.blendf(cx + math.cos(ang) * w * 0.62, cy + h * 0.5 + math.sin(ang) * h * 0.78, (140, 230, 255), fl)


def draw_projectile(canvas: PixelCanvas, x: float, y: float, vx: float, vy: float, accent: RGB,
                    ammo: AmmoType, t: float) -> None:
    """Draws the shell head in the style of its ammo type (looks only)."""
    accent = live_color(accent, t)
    sp = math.hypot(vx, vy) or 1.0
    ux, uy = vx / sp, vy / sp
    white = (255, 255, 255)
    nb = ((1, 0), (-1, 0), (0, 1), (0, -1))
    style = ammo.proj
    if style == "streak":
        for i in range(6):
            canvas.blendf(x - ux * i, y - uy * i, mix(white, accent, i / 6), 1.0 - i / 7)
    elif style == "orb":
        r = 1.5 + 0.4 * math.sin(t * 14)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= r + 0.5:
                    canvas.blendf(x + dx, y + dy, mix(accent, white, 0.4), 0.9)
                elif d <= 3.2:
                    canvas.blendf(x + dx, y + dy, accent, 0.22)
        canvas.plotf(x, y, white)
    elif style == "spark":
        canvas.plotf(x, y, white)
        for k in range(3):
            canvas.blendf(x + (flicker(t, k, 1) - 0.5) * 3.5, y + (flicker(t, k, 2) - 0.5) * 3.5, accent, 0.9)
    elif style == "comet":
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                canvas.blendf(x + dx, y + dy, mix(accent, white, 0.3), 0.7)
        canvas.plotf(x, y, white)
    elif style == "drip":
        canvas.plotf(x, y, mix(accent, white, 0.35))
        for dx, dy in nb:
            canvas.blendf(x + dx, y + dy, accent, 0.6)
        canvas.blendf(x, y - 2, accent, 0.55)
        canvas.blendf(x, y - 3, accent, 0.25)
    elif style in ("star", "prism"):
        tw = 0.5 + 0.5 * math.sin(t * 12)
        cols = [accent] * 4 if style == "star" else [hsv(t * 1.2 + k * 0.25, 0.6, 1.0) for k in range(4)]
        canvas.plotf(x, y, white)
        for (dx, dy), c in zip(nb, cols):
            canvas.blendf(x + dx, y + dy, c, 0.95)
            canvas.blendf(x + dx * 2, y + dy * 2, c, 0.35 + 0.5 * tw)
        if tw > 0.55:
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                canvas.blendf(x + dx, y + dy, white, 0.5)
    elif style == "relic":                                   # spinning gold diamond inside a halo of light
        ang0 = t * 6
        for k in range(12):
            a_ = k * math.tau / 12 - ang0 * 0.5
            canvas.blendf(x + math.cos(a_) * 3.4, y + math.sin(a_) * 3.4, (255, 226, 140), 0.35)
        for k in range(4):
            a_ = ang0 + k * math.pi / 2
            canvas.blendf(x + math.cos(a_) * 2.2, y + math.sin(a_) * 2.2, mix(accent, white, 0.5), 0.9)
        for dx, dy in nb:
            canvas.blendf(x + dx, y + dy, accent, 0.95)
        canvas.plotf(x, y, white)
    elif style == "eye":                                     # a watching eye with a slit pupil
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx * 0.8, dy * 1.25)
                if d <= 2.6:
                    canvas.blendf(x + dx, y + dy, mix(accent, white, 0.55) if d > 1.1 else shade(accent, 0.1), 0.95)
        for dy in (-1, 0, 1):
            canvas.blendf(x, y + dy, (10, 4, 20), 0.9)
        for k in range(10):
            a_ = k * math.tau / 10 + t * 3
            canvas.blendf(x + math.cos(a_) * 3.8, y + math.sin(a_) * 3.8, accent, 0.4)
    elif style == "runes":                                   # four rune spokes spinning (Tempest's shell; was shadowing GLYPH's digits)
        a0 = t * 9
        for k in range(4):
            a_ = a0 + k * math.pi / 2
            for sp in (1, 2, 3):
                canvas.blendf(x + math.cos(a_) * sp, y + math.sin(a_) * sp, accent if sp < 3 else white, 0.95 - 0.2 * sp)
        canvas.plotf(x, y, white)
    elif style == "sigil":                                   # a burning hexagram
        a0 = -t * 5
        for k in range(6):
            a_ = a0 + k * math.tau / 6
            canvas.blendf(x + math.cos(a_) * 2.6, y + math.sin(a_) * 2.6, (255, 150, 40) if k % 2 else white, 0.95)
            canvas.blendf(x + math.cos(a_) * 1.4, y + math.sin(a_) * 1.4, (255, 214, 120), 0.7)
        canvas.plotf(x, y, white)
    elif style == "sandglass":                               # two triangles and a falling grain
        for dy in range(-3, 4):
            w = abs(dy) * 0.8
            for dx in range(-3, 4):
                if abs(dx) <= w and abs(dy) >= 1:
                    canvas.blendf(x + dx, y + dy, mix(accent, white, 0.4), 0.85)
        canvas.plotf(x, y + 1 - (t * 14) % 3, white)
    elif style == "void":
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= 1.2:
                    canvas.blendf(x + dx, y + dy, shade(accent, 0.08), 1.0)
                elif d <= 2.2:
                    canvas.blendf(x + dx, y + dy, mix(accent, white, 0.25), 0.95)
                elif d <= 3.2:
                    canvas.blendf(x + dx, y + dy, shade(accent, 0.2), 0.3)
    elif style == "ring":
        r = 2.4 + 1.1 * abs(math.sin(t * 9))
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                d = math.hypot(dx, dy)
                if abs(d - r) < 0.75:
                    canvas.blendf(x + dx, y + dy, mix(accent, white, 0.3), 0.9)
                elif d < r - 0.75:
                    canvas.blendf(x + dx, y + dy, accent, 0.18)
        canvas.plotf(x, y, white)
    elif style == "shard":
        px, py = -uy, ux
        for i in range(-3, 4):
            k = 1 - abs(i) / 4
            canvas.blendf(x + ux * i, y + uy * i, mix(accent, (225, 248, 255), k), 0.95)
            if abs(i) < 2:
                canvas.blendf(x + ux * i + px * 0.9, y + uy * i + py * 0.9, accent, 0.7)
                canvas.blendf(x + ux * i - px * 0.9, y + uy * i - py * 0.9, accent, 0.7)
        if int(t * 14) % 3 == 0:
            canvas.blendf(x, y + 2, white, 0.6)
    elif style == "sun":
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= 1.6:
                    canvas.blendf(x + dx, y + dy, mix((255, 250, 210), white, 0.5), 1.0)
                elif d <= 3.2:
                    canvas.blendf(x + dx, y + dy, accent, 0.28)
        for k in range(8):
            a = k * math.pi / 4 + t * 7
            for s in (2.4, 3.4, 4.4 if k % 2 == 0 else 3.4):
                canvas.blendf(x + math.cos(a) * s, y + math.sin(a) * s, mix(accent, white, 0.5), 0.85 - (s - 2.4) * 0.15)
    elif style == "lava":
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                hot = flicker(t, dx + 3, dy + 7) > 0.45
                canvas.blendf(x + dx, y + dy, (255, 190, 70) if hot else (200, 60, 18), 0.95)
        canvas.plotf(x, y, (255, 240, 170))
        canvas.blendf(x - ux * 2.2, y - uy * 2.2 - 1, (255, 120, 30), 0.8)
        canvas.blendf(x - ux * 3.4, y - uy * 3.4 - 2, (170, 40, 12), 0.6)
        canvas.blendf(x + 1.5, y - 2.5 - (t * 14) % 2, (255, 150, 40), 0.7)
    elif style == "bolt":
        canvas.plotf(x, y, white)
        for dx, dy in nb:
            canvas.blendf(x + dx, y + dy, mix(accent, white, 0.5), 0.9)
        for k in range(4):                      # crackling arcs leaping off the orb
            ang = flicker(t, k, 4) * math.tau
            for s in range(1, 4):
                nx = x + math.cos(ang) * s * 1.5 + (flicker(t, k, s + 10) - 0.5) * 2
                ny = y + math.sin(ang) * s * 1.5 + (flicker(t, k, s + 20) - 0.5) * 2
                canvas.blendf(nx, ny, mix(accent, white, 0.7), 0.85 - s * 0.2)
    elif style == "alien":
        pulse = 0.5 + 0.5 * math.sin(t * 11)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= 1.5:
                    canvas.blendf(x + dx, y + dy, mix((170, 255, 190), white, 0.5 * pulse), 1.0)
                elif d <= 2.8:
                    canvas.blendf(x + dx, y + dy, (60, 230, 150), 0.35 + 0.25 * pulse)
        for k in range(2):
            a = t * 10 + k * math.pi
            canvas.blendf(x + math.cos(a) * 3.4, y + math.sin(a) * 3.4, (200, 120, 255), 0.95)
            canvas.blendf(x + math.cos(a - 0.5) * 3.4, y + math.sin(a - 0.5) * 3.4, (150, 80, 230), 0.5)
    elif style == "blessing":                                # MARTYR'S BLESSING: a golden eight-point star, a ticking clock-hand, orbiting violet stars
        for k in range(8):
            a_ = t * 5 + k * math.pi / 4
            ln = 5 if k % 2 == 0 else 3
            for s in range(1, ln + 1):
                canvas.blendf(x + math.cos(a_) * s, y + math.sin(a_) * s, (255, 226, 120) if k % 2 == 0 else (255, 255, 255), 0.95 - s * 0.12)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if math.hypot(dx, dy) <= 2.2:
                    canvas.blendf(x + dx, y + dy, (255, 250, 220), 0.9)
        for s in range(2, 8):
            canvas.blendf(x + math.cos(t * 3) * s, y + math.sin(t * 3) * s, (255, 200, 80), 0.9 - s * 0.08)
        for k in range(3):
            a_ = -t * 6 + k * math.tau / 3
            canvas.blendf(x + math.cos(a_) * 6.5, y + math.sin(a_) * 6.5, (176, 120, 255), 0.95)
    elif style == "phase":                                   # PHASE SHIFT: a plain flickering ghost that blinks between two positions
        flick = int(t * 18) % 2
        canvas.blendf(x, y, (170, 255, 200), 0.95 if flick else 0.5)
        canvas.blendf(x - ux * 3, y - uy * 3, (190, 130, 255), 0.45 if flick else 0.9)
        canvas.plotf(x, y, white)
    elif style == "xenon":                                   # XENON: a caged star - white core, 2 counter-rotating ion orbits, cross-flares
        pulse = 0.5 + 0.5 * math.sin(t * 9)
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                d = math.hypot(dx, dy)
                if d <= 1.6:
                    canvas.blendf(x + dx, y + dy, mix((235, 255, 245), white, 0.6 * pulse), 1.0)
                elif d <= 3.6:
                    canvas.blendf(x + dx, y + dy, mix((60, 235, 160), (120, 80, 230), (d - 1.6) / 2.0), 0.3 + 0.25 * pulse)
        for k in range(6):                                   # outer orbit
            a_ = t * 8 + k * math.tau / 6
            canvas.blendf(x + math.cos(a_) * 4.6, y + math.sin(a_) * 4.6, (210, 140, 255) if k % 2 else (150, 255, 210), 0.95)
            canvas.blendf(x + math.cos(a_ - 0.35) * 4.6, y + math.sin(a_ - 0.35) * 4.6, (120, 70, 220), 0.5)
        for k in range(4):                                   # inner orbit, opposite way
            a_ = -t * 12 + k * math.pi / 2
            canvas.blendf(x + math.cos(a_) * 2.6, y + math.sin(a_) * 2.6, white, 0.9)
        for k in range(4):                                   # pulsing cross-flares
            a_ = math.pi / 4 + k * math.pi / 2 + t * 1.5
            for s in range(3, 3 + int(3 + 3 * pulse)):
                canvas.blendf(x + math.cos(a_) * s, y + math.sin(a_) * s, (180, 255, 220), 0.55 - s * 0.05)
    elif style == "lure":                                    # ANGLER'S LURE: a glowing bulb on a short trailing filament
        glow = 0.6 + 0.4 * math.sin(t * 9)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= 3.0:
                    canvas.blendf(x + dx, y + dy, (150, 255, 236) if d < 1.3 else (40, 170, 210), (1 - d / 3.2) * glow)
        for s in range(1, 6):
            canvas.blendf(x - ux * s + math.sin(t * 6 + s) * 0.6, y - uy * s, (60, 140, 170), 0.7 - s * 0.1)
        canvas.plotf(x, y, (240, 255, 255))
    elif style == "foxfire":                                 # a blue flame with a white heart, licking backwards
        for k in range(7):
            fl = flicker(t, k, 41)
            canvas.blendf(x - ux * k * 0.9 + (fl - 0.5) * 1.6, y - uy * k * 0.9 + k * 0.25, gradient(((0, (236, 250, 255)), (0.5, (110, 180, 255)), (1, (50, 70, 220))), k / 6), 0.95 - k * 0.11)
        canvas.plotf(x, y, white)
    elif style == "lance":                                   # HARDLIGHT LANCE: a long rod of light with a white tip
        for i in range(12):
            col = (255, 255, 255) if i < 2 else mix((150, 250, 255), (40, 140, 255), i / 12)
            canvas.blendf(x - ux * i, y - uy * i, col, 1.0 - i / 14)
            canvas.blendf(x - ux * i - uy * 0.9, y - uy * i + ux * 0.9, (90, 220, 255), 0.25 * (1 - i / 12))
    elif style == "paradox":                                 # two shells half a step out of phase, swapping places
        ph = math.sin(t * 13)
        for sgn, col in ((1, (210, 170, 255)), (-1, (255, 255, 255))):
            ox, oy = -uy * 1.6 * ph * sgn, ux * 1.6 * ph * sgn
            for dx, dy in ((0, 0),) + nb:
                canvas.blendf(x + ox + dx, y + oy + dy, col, 0.95 if (dx, dy) == (0, 0) else 0.45)
    elif style == "atomic":                                  # a crackling blue-white core with a halo
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= 3.2:
                    canvas.blendf(x + dx, y + dy, (230, 248, 255) if d < 1.4 else (70, 140, 255), (1 - d / 3.4) * (0.8 + 0.2 * flicker(t, dx, dy)))
        for k in range(3):
            a_ = flicker(t, k, 13) * math.tau
            canvas.blendf(x + math.cos(a_) * 3.5, y + math.sin(a_) * 3.5, (200, 230, 255), 0.9)
    elif style == "spore":                                   # a pulsing spore pod trailing glowing motes
        r_ = 1.6 + 0.4 * math.sin(t * 7)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                d = math.hypot(dx, dy)
                if d <= r_:
                    canvas.blendf(x + dx, y + dy, (180, 40, 90) if d > 1.0 else (255, 220, 190), 0.95)
        for k in range(3):
            a_ = t * 4 + k * math.tau / 3
            canvas.blendf(x + math.cos(a_) * 3, y + math.sin(a_) * 3, (170, 255, 210), 0.8)
    elif style == "worm":                                    # a ringed sandworm head, maw glowing
        for k in range(6):
            off = math.sin(t * 12 - k * 1.1) * 1.0
            cx_, cy_ = x - ux * k * 1.4 - uy * off, y - uy * k * 1.4 + ux * off
            col = (255, 170, 90) if k == 0 else mix((214, 170, 100), (120, 80, 40), (k % 2) * 0.6)
            for dx, dy in ((0, 0),) + nb:
                canvas.blendf(cx_ + dx, cy_ + dy, col, (0.95 if (dx, dy) == (0, 0) else 0.5) * (1 - k / 8))
    elif style == "serpent":                                 # a jade serpent head and a weaving feathered body
        px, py = -uy, ux
        for k in range(9):
            off = math.sin(t * 10 - k * 0.8) * 1.6
            col = (250, 214, 120) if k % 3 == 0 else (40, 190, 120)
            canvas.blendf(x - ux * k + px * off, y - uy * k + py * off, col, 0.95 - k * 0.08)
        canvas.plotf(x, y, (255, 240, 180))
    elif style == "astro":                                   # a gold four-point star turning on a blue halo
        for k in range(4):
            a_ = t * 3 + k * math.pi / 2
            for s in range(1, 4):
                canvas.blendf(x + math.cos(a_) * s, y + math.sin(a_) * s, (255, 226, 140), 0.95 - s * 0.22)
        for dx, dy in nb:
            canvas.blendf(x + dx * 2, y + dy * 2, (120, 140, 255), 0.35)
        canvas.plotf(x, y, white)
    elif style == "cannonball":                              # an iron ball wrapped in green ghost-flame
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                d = math.hypot(dx, dy)
                if d <= 1.5:
                    canvas.blendf(x + dx, y + dy, (40, 50, 56), 1.0)
                elif d <= 2.6:
                    canvas.blendf(x + dx, y + dy, (90, 255, 160), 0.45 + 0.3 * flicker(t, dx + 3, dy + 3))
        canvas.blendf(x - ux * 3, y - uy * 3 + 1, (140, 255, 190), 0.5)
    elif style == "helix":
        px, py = -uy, ux
        for k in range(8):
            ph, s = t * 14 - k * 0.9, k * 1.3
            off = math.sin(ph) * 2.2
            col, a = hsv(t * 0.8 + k * 0.1, 0.6, 1.0), 0.95 - k * 0.1
            canvas.blendf(x - ux * s + px * off, y - uy * s + py * off, col, a)
            canvas.blendf(x - ux * s - px * off, y - uy * s - py * off, mix(col, white, 0.4), a)
        canvas.plotf(x, y, white)
    elif style == "glyph":
        k = int(t * 12)
        draw_glyph(canvas, x, y, k, mix((90, 255, 130), white, 0.35), 1.0)
        draw_glyph(canvas, x - ux * 5, y - uy * 5 + 1, k + 3, (40, 190, 80), 0.45)
    elif style == "flame":
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if flicker(t, dx + 5, dy + 5) > 0.25:
                    canvas.blendf(x + dx, y + dy, gradient(((0, (255, 236, 150)), (1, mix((255, 100, 20), accent, 0.3))),
                                                          flicker(t, dx, dy)), 0.95)
        for k in range(1, 3):
            canvas.blendf(x + (flicker(t, k, 9) - 0.5), y + k + 1, (255, 150, 40), 0.7 / k)
        canvas.plotf(x, y, (255, 250, 220))
    else:   # standard shell
        canvas.plotf(x, y, white)
        for dx, dy in nb:
            canvas.blendf(x + dx, y + dy, accent, 0.75)
