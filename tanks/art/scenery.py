"""Battlefield scenery: far buildings baked into a map's sky (skylines, temples, pyramids, kelp, kaiju, ...), the
terrain look and the animated weather and motes."""
from __future__ import annotations

import math
import random
from typing import Optional, TYPE_CHECKING

from tanks.colors import RGB, clamp, hsv, mix, shade
from tanks.content.maps import Theme
from tanks.screen import PixelCanvas

if TYPE_CHECKING:
    from tanks.battle.terrain import Terrain


# ---- Background buildings, baked once into a map's sky. Every style is a few primitives on a baseline; windows are lit
# deterministically so both LAN machines (and every redraw) show the same city.
def _b_rect(put, x0, y0, w, h, col):
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + h):
            put(x, y, col)


def _b_tri(put, cx, y0, half, h, col):
    for k in range(h):
        hw = int(half * (1 - k / h))
        for x in range(cx - hw, cx + hw + 1):
            put(x, y0 + k, col)


def _b_dome(put, cx, y0, rx, ry, col):
    for x in range(cx - rx, cx + rx + 1):
        for y in range(y0, y0 + ry):
            if ((x - cx) / rx) ** 2 + ((y - y0) / ry) ** 2 <= 1:
                put(x, y, col)


def _b_windows(put, x0, y0, w, h, lit, seed):
    for x in range(x0 + 1, x0 + w - 1, 2):
        for y in range(y0 + 2, y0 + h - 1, 3):
            if (x * 7 + y * 13 + seed) % 5 < 3:
                put(x, y, lit)


def _bake_buildings(kind: str, w: int, h: int, base_y: int, col: RGB, lit: RGB, put) -> None:
    r = random.Random(w * 31 + h * 7 + sum(map(ord, kind)))
    if kind in _BAKE_EXTRA:
        _BAKE_EXTRA[kind](w, h, base_y, col, lit, put, r)
        return
    if kind == "skyline":
        x = 2
        while x < w - 4:
            bw, bh = r.randint(5, 9), int(h * r.uniform(0.22, 0.62))
            _b_rect(put, x, base_y, bw, bh, col)
            _b_windows(put, x, base_y, bw, bh, lit, x)
            if r.random() < 0.4:
                _b_rect(put, x + bw // 2, base_y + bh, 1, r.randint(3, 7), col)
            x += bw + r.randint(0, 2)
    elif kind == "clock":
        cx = w // 2
        _b_rect(put, cx - 6, base_y, 12, int(h * 0.55), col)
        _b_tri(put, cx, base_y + int(h * 0.55), 8, int(h * 0.22), col)
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if dx * dx + dy * dy <= 16:
                    put(cx + dx, base_y + int(h * 0.42) + dy, lit if dx * dx + dy * dy > 6 else shade(lit, 0.5))
        for sx in (w // 6, w - w // 6):
            _b_rect(put, sx - 5, base_y, 10, int(h * 0.3), col)
            _b_windows(put, sx - 5, base_y, 10, int(h * 0.3), lit, sx)
    elif kind == "cathedral":
        cx = w // 2
        _b_rect(put, cx - 14, base_y, 28, int(h * 0.3), col)
        _b_tri(put, cx, base_y + int(h * 0.3), 14, int(h * 0.14), col)
        for sx in (cx - 18, cx + 18):
            _b_rect(put, sx - 3, base_y, 6, int(h * 0.55), col)
            _b_tri(put, sx, base_y + int(h * 0.55), 4, int(h * 0.2), col)
        _b_dome(put, cx, base_y + 3, 6, int(h * 0.2), lit)
    elif kind == "temple":
        cx = w // 2
        for i in range(6):
            _b_rect(put, cx - 24 + i * 4, base_y + i * 4, 48 - i * 8, 4, col)
        _b_rect(put, cx - 3, base_y + 24, 6, 5, lit)
        for sx in (w // 7, w - w // 7):
            for k in range(4):
                _b_rect(put, sx + k * 4 - 8, base_y, 2, int(h * 0.3), col)
    elif kind == "ruins":
        x = 4
        while x < w - 6:
            bh = int(h * r.uniform(0.1, 0.45))
            _b_rect(put, x, base_y, 3, bh, col)
            if r.random() < 0.5:
                _b_rect(put, x, base_y + bh, 9, 2, col)
            x += r.randint(8, 14)
    elif kind == "pyramids":
        for cx, ph in ((w // 5, 0.45), (w // 2, 0.6), (w - w // 4, 0.35)):
            _b_tri(put, cx, base_y, int(h * ph * 0.9), int(h * ph), col)
            put(cx, base_y + int(h * ph), lit)
    elif kind == "factory":
        x = 3
        while x < w - 8:
            bw = r.randint(10, 16)
            _b_rect(put, x, base_y, bw, int(h * 0.2), col)
            for sx in range(x, x + bw - 3, 5):
                _b_tri(put, sx + 2, base_y + int(h * 0.2), 2, 4, col)
            if r.random() < 0.7:
                _b_rect(put, x + bw - 3, base_y, 3, int(h * r.uniform(0.35, 0.6)), col)
            _b_windows(put, x, base_y, bw, int(h * 0.2), lit, x)
            x += bw + 2
    elif kind == "castle":
        _b_rect(put, 2, base_y, w - 4, int(h * 0.22), col)
        for x in range(2, w - 4, 4):
            _b_rect(put, x, base_y + int(h * 0.22), 2, 3, col)
        for sx in (w // 8, w // 3, w - w // 3, w - w // 8):
            _b_rect(put, sx - 4, base_y, 8, int(h * 0.5), col)
            _b_tri(put, sx, base_y + int(h * 0.5), 5, int(h * 0.16), col)
            _b_windows(put, sx - 4, base_y, 8, int(h * 0.5), lit, sx)
    elif kind == "station":
        cx = w // 2
        _b_dome(put, cx, base_y, 16, int(h * 0.3), col)
        _b_rect(put, cx - 30, base_y + int(h * 0.12), 60, 3, col)
        for sx in (cx - 30, cx + 30):
            _b_rect(put, sx - 1, base_y, 3, int(h * 0.4), col)
            put(sx, base_y + int(h * 0.4), lit)
        _b_windows(put, cx - 14, base_y, 28, int(h * 0.2), lit, 3)
    elif kind == "volcano":
        for cx, ph, hw in ((w // 4, 0.58, 0.30), (w - w // 3, 0.44, 0.24)):
            _b_tri(put, cx, base_y, int(h * hw * 2.6), int(h * ph), col)
            top = base_y + int(h * ph)
            for dx in range(-3, 4):
                put(cx + dx, top, lit)
            for k in range(7):
                put(cx + (k % 2) * 2 - 1, top - 2 - k * 3, lit)
    elif kind == "isles":
        for cx, cy, rw in ((w // 6, 0.55, 12), (w // 2, 0.7, 18), (w - w // 5, 0.5, 13), (w // 3, 0.38, 8), (w - w // 3, 0.36, 9)):
            y0 = base_y + int(h * cy)
            _b_rect(put, cx - rw, y0, 2 * rw, 2, col)
            for k in range(1, rw):
                _b_rect(put, cx - rw + k, y0 - k // 2 - 1, 2 * (rw - k), 1, col)
            _b_rect(put, cx - 1, y0 + 2, 3, 6 + rw // 3, col)
            put(cx, y0 + 7 + rw // 3, lit)
    elif kind == "rift":
        cx, cy, R = w // 2, base_y + int(h * 0.5), max(6, int(h * 0.34))
        for a in range(0, 720):
            ang = a * math.pi / 360
            for rr in (R - 1, R, R + 1):
                put(int(cx + math.cos(ang) * rr), int(cy + math.sin(ang) * rr), lit if rr == R else col)
        for sx in (w // 7, w - w // 7):
            _b_rect(put, sx - 3, base_y, 3, int(h * 0.5), col)
            _b_rect(put, sx + 4, base_y, 3, int(h * 0.35), col)
            _b_rect(put, sx - 3, base_y + int(h * 0.5), 10, 2, col)
        for _ in range(9):
            px, py = r.randint(4, max(5, w - 5)), base_y + int(h * r.uniform(0.3, 0.8))
            _b_tri(put, px, py, 2, r.randint(3, 6), col)
    elif kind == "pagoda":
        for cx, sc in ((w // 4, 0.8), (w // 2, 1.0), (w - w // 4, 0.8)):
            for tier in range(4):
                tw = int((14 - tier * 3) * sc)
                _b_rect(put, cx - tw // 2, base_y + tier * int(h * 0.1), tw, int(h * 0.07), col)
                _b_rect(put, cx - tw // 2 - 2, base_y + tier * int(h * 0.1) + int(h * 0.07), tw + 4, 2, col)
            _b_rect(put, cx, base_y + 4 * int(h * 0.1) + 2, 1, 5, col)


def _bk_line(put, x0, y0, x1, y1, col):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        put(int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n)), col)


def _bk_kelp(w, h, b, col, lit, put, r):
    """MARIANA DEEP: a forest of giant kelp swaying up toward the light, with rock arches between."""
    for cx in (w // 5, w - w // 4):
        R = int(h * 0.18)
        for a in range(0, 181, 2):
            ang = math.radians(a)
            for t_ in range(3):
                put(int(cx + math.cos(ang) * (R - t_)), int(b + math.sin(ang) * (R - t_) * 1.3), col)
    for _ in range(max(6, w // 6)):
        x0, ht = r.randint(2, w - 3), int(h * r.uniform(0.3, 0.72))
        ph = r.uniform(0, math.tau)
        for y in range(ht):
            x = int(x0 + math.sin(y * 0.18 + ph) * 2.2)
            put(x, b + y, col)
            if y % 3 == 0:
                put(x + (1 if (y // 3) % 2 else -1), b + y, col)
                put(x + (2 if (y // 3) % 2 else -2), b + y + 1, col)
            if y % 9 == 4:
                put(x, b + y + 1, lit)


def _bk_torii(w, h, b, col, lit, put, r):
    """TORII PATH: a mountain with a stair of gates up its flank and a lantern-lit shrine at the top."""
    cx, top = int(w * 0.62), b + int(h * 0.55)
    for x in range(w):
        y_ = top - int(abs(x - cx) * 0.9)
        for y in range(b, max(b, y_)):
            put(x, y, col)
    for k in range(5):                                                   # gates climbing the left flank
        gx = int(cx - (5 - k) * (w * 0.07))
        gy = top - int(abs(gx - cx) * 0.9)
        s = 0.75 + k * 0.08
        hw, hh = int(6 * s), int(10 * s)
        for side in (-1, 1):
            _b_rect(put, gx + side * hw, gy, 2, hh, lit)
        for x in range(gx - hw - 2, gx + hw + 4):
            lift = 1 if abs(x - gx) > hw else 0
            put(x, gy + hh + lift, lit)
            put(x, gy + hh + 1 + lift, (40, 20, 24))
        for x in range(gx - hw, gx + hw + 1):
            put(x, gy + hh - 3, lit)
    _b_rect(put, cx - 5, top, 11, 5, col)
    _b_tri(put, cx, top + 5, 8, 4, col)
    put(cx, top + 2, lit)
    put(cx, top + 3, lit)


def _bk_holo(w, h, b, col, lit, put, r):
    """NEON GRIDLOCK: dense towers carrying huge hologram billboards and blinking aircraft lights."""
    x = 1
    while x < w - 3:
        bw, bh = r.randint(5, 10), int(h * r.uniform(0.25, 0.7))
        _b_rect(put, x, b, bw, bh, col)
        _b_windows(put, x, b, bw, bh, shade(lit, 0.6), x)
        if r.random() < 0.45 and bw >= 6:                                # a billboard: a glowing panel with scanlines
            by, bh2 = b + bh - r.randint(6, 10), r.randint(4, 6)
            c1 = lit if r.random() < 0.5 else (255, 80, 210)
            for yy in range(by, by + bh2 + 1):
                for xx in range(x - 1, x + bw + 1):
                    edge = yy in (by, by + bh2) or xx in (x - 1, x + bw)
                    put(xx, yy, c1 if edge else (shade(c1, 0.75) if yy % 2 else shade(c1, 0.4)))
        if r.random() < 0.5:
            _b_rect(put, x + bw // 2, b + bh, 1, r.randint(3, 8), col)
            put(x + bw // 2, b + bh + 8, (255, 70, 90))
        x += bw + r.randint(0, 2)


def _bk_tesseract(w, h, b, col, lit, put, r):
    """PARADOX ENGINE: a vast wire hypercube hanging in the sky over drifting slabs."""
    cx, cy, S = w // 2, b + int(h * 0.42), int(h * 0.16)
    a, c = 0.6, 0.45
    pts = []
    for i in range(16):
        v = [(1 if i >> k & 1 else -1) for k in range(4)]
        x, y, z, ww = v
        x, ww = x * math.cos(a) - ww * math.sin(a), x * math.sin(a) + ww * math.cos(a)
        y, z = y * math.cos(c) - z * math.sin(c), y * math.sin(c) + z * math.cos(c)
        k4 = 2.2 / (3.2 - ww)
        k3 = 3.0 / (4.2 - z * k4)
        pts.append((cx + x * k4 * k3 * S * 1.5, cy + y * k4 * k3 * S))
    for i in range(16):
        for j in range(i + 1, 16):
            if bin(i ^ j).count("1") == 1:
                _bk_line(put, *pts[i], *pts[j], lit)
    for k in range(7):                                                   # floating slabs
        sx, sy = r.randint(4, w - 12), b + int(h * r.uniform(0.05, 0.6))
        sw = r.randint(5, 10)
        _b_rect(put, sx, sy, sw, 2, col)
        _b_tri(put, sx + sw // 2, sy - 3, sw // 2, 3, col)


def _bk_kaiju(w, h, b, col, lit, put, r):
    """KAIJU BAY: a broken harbour skyline on the left; on the right, the monster itself, asleep in the water."""
    x = 1
    while x < w * 0.4:
        bw, bh = r.randint(4, 8), int(h * r.uniform(0.15, 0.45))
        _b_rect(put, x, b, bw, bh, col)
        if r.random() < 0.4:                                             # a smashed top
            for k in range(bw):
                if (k * 3) % 5 < 2:
                    put(x + k, b + bh, col)
        _b_windows(put, x, b, bw, bh, lit, x)
        x += bw + r.randint(1, 2)
    kx, sc = int(w * 0.78), h / 70.0
    body = [(-24, 0), (-22, 20), (-14, 34), (-4, 42), (6, 46), (14, 44), (18, 38), (14, 33), (10, 29), (12, 21), (22, 12), (25, 0)]
    for y in range(0, int(48 * sc)):                                     # fill the outline row by row
        yy = y / sc
        xs = []
        for i in range(len(body) - 1):
            (ax, ay), (bx_, by_) = body[i], body[i + 1]
            if (ay <= yy < by_) or (by_ <= yy < ay):
                xs.append(ax + (yy - ay) * (bx_ - ax) / (by_ - ay))
        if len(xs) >= 2:
            for xx in range(int(min(xs) * sc), int(max(xs) * sc) + 1):
                put(kx - xx, b + y, col)
    for k in range(9):                                                   # its dorsal plates, faintly glowing
        f = k / 8
        px_, py_ = kx - int((-16 + f * 22) * sc), b + int((22 + f * 22) * sc)
        for s in range(int((4 + 3 * math.sin(f * math.pi)) * sc)):
            put(px_, py_ + s, lit)
    put(kx - int(13 * sc), b + int(41 * sc), (255, 120, 60))


def _bk_shrooms(w, h, b, col, lit, put, r):
    """MYCELIA: giant mushroom silhouettes, their caps dotted with glowing spots."""
    for i in range(max(4, w // 22)):
        cx = int(w * (0.05 + i * 0.9 / max(1, w // 22 - 1))) if w // 22 > 1 else w // 2
        stem = int(h * r.uniform(0.12, 0.32))
        _b_rect(put, cx - 1, b, 3, stem, col)
        rx, ry = r.randint(9, 17), r.randint(4, 7)
        for x in range(cx - rx, cx + rx + 1):
            for y in range(0, ry):
                d = ((x - cx) / rx) ** 2 + (y / ry) ** 2
                if d <= 1:
                    put(x, b + stem + y, shade(lit, 0.45) if d > 0.7 else col)
        for x in range(cx - rx + 1, cx + rx):                            # the glowing gills under the cap
            put(x, b + stem - 1, shade(lit, 0.6) if x % 2 else col)
        for _ in range(5):
            put(cx + r.randint(-rx + 2, rx - 2), b + stem + r.randint(1, ry - 1), lit)


def _bk_wormarch(w, h, b, col, lit, put, r):
    """WORM'S MAW: a colossal sandworm arching out of the dunes on the horizon, ring by ring."""
    x0, x1 = int(w * 0.18), int(w * 0.82)
    for k in range(240):
        u = k / 239
        x = x0 + (x1 - x0) * u
        y = b + math.sin(u * math.pi) * h * 0.5
        rad = 4 + 3 * math.sin(u * math.pi)
        for dy in range(-int(rad), int(rad) + 1):
            put(int(x), int(y + dy), lit if (k % 8 < 2 and abs(dy) < rad - 1) else col)
    for x in range(w):                                                   # dunes along the horizon
        for y in range(int(4 + 3 * math.sin(x * 0.07) + 2 * math.sin(x * 0.19))):
            put(x, b + y, col)


def _bk_stepped(w, h, b, col, lit, put, r):
    """SERPENT STAIRS: two stepped pyramids with temples on top, jungle crowns between them."""
    for cx, s in ((w // 4, 1.0), (w - w // 4, 0.8)):
        tiers, tw = 6, int(h * 0.3 * s)
        for k in range(tiers):
            ww = int(tw * (1 - k / (tiers + 1)))
            _b_rect(put, cx - ww, b + k * int(4 * s + 1), 2 * ww + 1, int(4 * s + 1), col)
        top = b + tiers * int(4 * s + 1)
        _b_rect(put, cx - 3, top, 7, int(5 * s) + 1, col)
        put(cx, top + 1, lit)
        put(cx, top + 2, lit)
        _b_rect(put, cx - 1, b, 3, top - b, shade(col, 0.8))           # the central stair
    for _ in range(w // 5):
        cx = r.randint(0, w - 1)
        R = r.randint(3, 6)
        for x in range(cx - R, cx + R + 1):
            for y in range(R):
                if ((x - cx) / R) ** 2 + (y / R) ** 2 <= 1:
                    put(x, b + int(h * 0.05) + y, col)


def _bk_orrery(w, h, b, col, lit, put, r):
    """ASTROLABE: the rings of a brass orrery cutting across the stars, with its planets."""
    cx, cy = w // 2, b + int(h * 0.45)
    for R, tilt in ((h * 0.12, 0.45), (h * 0.2, 0.38), (h * 0.3, 0.3), (h * 0.4, 0.24)):
        n = int(R * 12)
        for k in range(n):
            a = k * math.tau / n
            put(int(cx + math.cos(a) * R * 2.2), int(cy + math.sin(a) * R * tilt * 2), (240, 200, 120) if k % 24 == 0 else lit)
        a = r.uniform(0, math.tau)
        px_, py_ = int(cx + math.cos(a) * R * 2.2), int(cy + math.sin(a) * R * tilt * 2)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx * dx + dy * dy <= 4:
                    put(px_ + dx, py_ + dy, lit)
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            if dx * dx + dy * dy <= 16:
                put(cx + dx, cy + dy, lit)
    for k in range(2):                                                   # the meridian frame
        R = h * 0.46
        for j in range(200):
            a = math.pi * j / 199
            put(int(cx + math.cos(a) * R * 2.2 * (0.5 + 0.5 * k)), int(cy + math.sin(a) * R), col)


def _bk_wrecks(w, h, b, col, lit, put, r):
    """GHOST REEF: the broken hulls of galleons on the reef, masts snapped and leaning, ghost-lanterns still burning."""
    b += int(h * 0.14)                                                   # the wrecks sit up on the reef, clear of the battlefield
    for i in range(4):
        cx = int(w * (0.12 + i * 0.25)) + r.randint(-4, 4)
        L_, hh = r.randint(16, 26), r.randint(4, 7)
        tilt = r.uniform(-0.25, 0.25)
        for x in range(-L_ // 2, L_ // 2):
            top = int(hh * (1 - (abs(x) / (L_ / 2)) ** 3)) + int(x * tilt)
            for y in range(max(0, top)):
                put(cx + x, b + y, col)
        for _ in range(2):
            mx = cx + r.randint(-L_ // 3, L_ // 3)
            ml = int(h * r.uniform(0.2, 0.4))
            lean = r.uniform(-0.6, 0.6)
            for s in range(ml):
                put(int(mx + s * lean * 0.5), b + hh + s, col)
                put(int(mx + s * lean * 0.5) + 1, b + hh + s, col)
            for s in range(6, ml - 3, 8):                                # tattered sails, ghost-lit at the edges
                sw = 6 - s // 10
                for yy in range(6):
                    for k in range(-sw, sw + 1):
                        if (k, yy) in ((1, 2), (-2, 4), (2, 3)):
                            continue                                     # rips
                        edge = abs(k) == sw or yy == 0
                        put(int(mx + (s - yy) * lean * 0.5) + k, b + hh + s - yy, (110, 190, 160) if edge else (34, 62, 58))
        put(cx + L_ // 2 - 2, b + hh + 2, lit)
        put(cx - L_ // 2 + 3, b + 2, lit)


_BAKE_LIT = {"kelp": (110, 230, 210), "torii": (214, 58, 44), "holo": (90, 230, 255), "tesseract": (200, 170, 255), "kaiju": (120, 190, 255),
             "shrooms": (170, 255, 210), "wormarch": (150, 104, 62), "stepped": (255, 190, 90), "orrery": (130, 102, 58), "wrecks": (130, 255, 180)}
_BAKE_EXTRA = {"kelp": _bk_kelp, "torii": _bk_torii, "holo": _bk_holo, "tesseract": _bk_tesseract, "kaiju": _bk_kaiju,
               "shrooms": _bk_shrooms, "wormarch": _bk_wormarch, "stepped": _bk_stepped, "orrery": _bk_orrery, "wrecks": _bk_wrecks}


class Scenery:
    """Sky, distant ridges, stars and the shaded terrain layer (cached, patched per crater)."""

    def __init__(self, width: int, height: int, theme: Theme, rng: random.Random) -> None:
        self.w, self.h, self.theme = width, height, theme
        self.sky = self._build_sky(rng)
        if theme.buildings:
            col = mix(theme.sky_bottom, (0, 0, 0), 0.62)
            lit = mix(theme.sun if hasattr(theme, "sun") else (255, 220, 140), (255, 230, 150), 0.5)

            def put(x, y, c, sky=self.sky, hh=height, ww=width):
                if 0 <= x < ww and 0 <= y < hh:
                    sky[hh - 1 - y][x] = c
            _bake_buildings(theme.buildings, width, height, int(height * 0.2), col, _BAKE_LIT.get(theme.buildings, lit), put)
        self.rows = [r[:] for r in self.sky]
        self.stars = []
        for _ in range(int(width * height * theme.star_density * 3) + 8):
            self.stars.append((rng.randrange(width), rng.randrange(0, max(1, int(height * 0.38))),
                               rng.uniform(0, math.tau), rng.uniform(1.0, 3.0), rng.uniform(0.4, 1.0)))
        self._terrain: Optional[Terrain] = None
        self._aur_key: Optional[int] = None
        self._aur_cells: list = []
        self._bolt_key: Optional[int] = None
        self._bolt: list = []
        self.motes: list = []
        if theme.fx in MOTE_STYLES:        # only fx maps draw extra random numbers, so other maps stay seed-identical
            n = max(16, int(width * height * MOTE_STYLES[theme.fx][0]))
            self.motes = [(rng.uniform(0, width), rng.uniform(0, height), rng.uniform(0.6, 1.4), rng.uniform(0, math.tau),
                           rng.uniform(0.5, 2.5), rng.randrange(3)) for _ in range(n)]

    def _build_sky(self, rng: random.Random) -> list[list[RGB]]:
        th, w, h = self.theme, self.w, self.h
        rows = [[mix(th.sky_top, th.sky_bottom, (py / max(1, h - 1)) ** 1.4)] * w for py in range(h)]
        ox, oy, r = int(w * rng.uniform(0.35, 0.65)), int(h * 0.7), max(3, int(h * 0.09))
        for py in range(max(0, h - 1 - oy - 3 * r), min(h, h - 1 - oy + 3 * r)):
            for x in range(max(0, ox - 3 * r), min(w, ox + 3 * r)):
                d = math.hypot(x - ox, (h - 1 - py) - oy)
                if d <= r:
                    rows[py][x] = mix(rows[py][x], th.orb, 0.95)
                elif d < 3 * r:
                    rows[py][x] = mix(rows[py][x], th.orb, 0.35 * (1 - (d - r) / (2 * r)) ** 2)
        ph = [rng.uniform(0, math.tau) for _ in range(6)]
        for layer, (base, k, dark) in enumerate(((0.36, 0.55, 1.0), (0.24, 0.75, 0.7))):
            far = shade(th.far, dark)
            for x in range(w):
                u = x / w
                ridge = h * (base + 0.08 * math.sin(u * math.tau * 3 + ph[layer])
                             + 0.05 * math.sin(u * math.tau * 8 + ph[layer + 2]) + 0.02 * math.sin(u * math.tau * 21 + ph[layer + 4]))
                for py in range(max(0, h - 1 - int(ridge)), h):
                    rows[py][x] = mix(rows[py][x], far, k)
        return rows

    def _pixel(self, x: int, y: int, h: int, scorch: float) -> RGB:
        th = self.theme
        depth = h - 1 - y
        if depth == 0:
            c = th.surface
        elif depth < 3:
            c = mix(th.topsoil, th.soil, depth / 3)
        else:
            c = mix(th.soil, th.deep, min(1.0, (depth - 3) / (self.h * 0.5)))
        n = ((x * 374761393 + y * 668265263) ^ (x * y * 2246822519 + 1013904223)) & 0xFF
        if depth < 4 and scorch > 0.02:
            c = shade(c, 1 - 0.6 * scorch)
        return shade(c, 0.94 + n / 255 * 0.12)

    def apply_terrain(self, terrain: Terrain, x0: int = 0, x1: Optional[int] = None) -> None:
        self._terrain = terrain
        x1 = self.w - 1 if x1 is None else min(x1, self.w - 1)
        h = self.h
        for x in range(max(0, x0), x1 + 1):
            top = terrain.heights[x]
            sc = terrain.scorch[x]
            for py in range(h):
                y = h - 1 - py
                self.rows[py][x] = self._pixel(x, y, top, sc) if y < top else self.sky[py][x]

    def canvas(self) -> PixelCanvas:
        return PixelCanvas(self.w, self.h, rows=[r[:] for r in self.rows])

    def draw_stars(self, canvas: PixelCanvas, t: float) -> None:
        for x, py, ph, sp, b in self.stars:
            if canvas.rows[py][x] == self.sky[py][x]:
                canvas.rows[py][x] = mix(canvas.rows[py][x], (235, 240, 255), (0.3 + 0.5 * math.sin(t * sp + ph) ** 2) * b)

    def _build_aurora(self, c: float) -> list:
        """Aurora ribbon cells (row, column, final colour) for animation time c.

        Hue and strength are quantised so the sky only ever uses a few hundred distinct colours (it used to mint
        thousands of new ones per frame, which flooded the terminal and the colour cache), and the ribbons are only
        rebuilt ten times a second instead of every frame."""
        h, w, sky = self.h, self.w, self.sky
        cells = []
        for b in range(3):
            for x in range(w):
                mid = h * (0.66 + 0.08 * b) + h * 0.05 * math.sin(x * 0.07 + c * 0.6 + b * 2.1) + h * 0.03 * math.sin(x * 0.17 - c * 0.9 + b)
                thick = 3 + 2 * math.sin(x * 0.09 + c + b)
                col = hsv(round((0.46 + 0.22 * math.sin(x * 0.03 + c * 0.25 + b * 1.3)) * 24) / 24, 0.65, 1.0)
                for dy in range(-int(thick), int(thick) + 1):
                    py = h - 1 - (int(mid) + dy)
                    if 0 <= py < h:
                        a = round(0.32 * (1 - abs(dy) / (thick + 1)) ** 1.3 * 25) / 25
                        if a > 0.02:
                            cells.append((py, x, mix(sky[py][x], col, a)))
        return cells

    def draw_aurora(self, canvas: PixelCanvas, t: float) -> None:
        """Animated aurora ribbons (only on themes that ask for it, i.e. the Citadel)."""
        if not self.theme.aurora:
            return
        key = int(t * 10)
        if key != self._aur_key:
            self._aur_key, self._aur_cells = key, self._build_aurora(key / 10)
        rows, sky = canvas.rows, self.sky
        for py, x, col in self._aur_cells:
            if rows[py][x] == sky[py][x]:
                rows[py][x] = col

    # -- extra sky layers: embers (Forge), thunderstorm (Spire), golden motes (Citadel) -----------------------------
    def draw_fx(self, canvas: PixelCanvas, t: float, flashes: bool = True) -> None:
        fx = self.theme.fx
        if fx in MOTE_STYLES:
            self._draw_motes(canvas, t, MOTE_STYLES[fx])
        if fx in ("storm", "tempest"):
            self._draw_storm(canvas, t, flashes)
        elif fx == "inferno":
            self._draw_lavaglow(canvas, t)
        elif fx == "rift":
            self._draw_rift(canvas, t)
        elif fx == "plankton":
            self._draw_jellies(canvas, t)

    def _draw_jellies(self, canvas: PixelCanvas, t: float) -> None:
        """Mariana Deep: pale jellyfish drifting up through the water, bells pulsing, tendrils trailing."""
        w, h = self.w, self.h
        sb = lambda x, y, c, a: self._sky_blend(canvas, x, y, c, a)
        for j, (xf, sz, spd, col) in enumerate(((0.22, 1.0, 1.0, (255, 150, 220)), (0.7, 0.8, 1.3, (140, 220, 255)), (0.48, 0.55, 1.7, (190, 255, 210)))):
            y = ((t * spd * 2.2 + j * h * 0.5) % (h * 1.2)) - h * 0.1          # y up
            x = w * xf + math.sin(t * 0.5 + j) * 4
            pulse = 0.5 + 0.5 * math.sin(t * 2.3 + j)
            rx, ry = 6 * sz * (1 + 0.15 * pulse), 4 * sz * (1 - 0.12 * pulse)
            for k in range(7):
                tx = x + (k - 3) * rx * 0.28
                for s in range(int(16 * sz)):
                    sb(tx + math.sin(s * 0.3 - t * 2 + k) * 1.1, y - s, col, 0.4 * (1 - s / (16 * sz)))
            for dy in range(0, int(ry) + 1):
                ww = rx * math.sqrt(max(0.0, 1 - (dy / max(1, ry)) ** 2))
                for dx in range(-int(ww), int(ww) + 1):
                    edge = abs(dx) >= int(ww) - 1 or dy == int(ry)
                    sb(x + dx, y + dy, mix(col, (255, 255, 255), 0.4), 0.75 if edge else 0.3)

    def _draw_motes(self, canvas: PixelCanvas, t: float, style: tuple) -> None:
        _, speed, pal, alpha = style
        h, w, sky, rows = self.h, self.w, self.sky, canvas.rows
        top = h * 0.92
        for x0, y0, sp, ph, amp, ci in self.motes:
            xi = int((x0 + math.sin(t * 0.8 * sp + ph) * amp) % w)
            py = h - 1 - int((y0 + t * speed * sp) % top)
            if 0 <= py < h and rows[py][xi] == sky[py][xi]:
                lvl = (0.5, 0.75, 1.0)[int((math.sin(t * 5 * sp + ph) + 1) * 1.49)]     # 3 brightness steps only
                rows[py][xi] = mix(sky[py][xi], pal[ci], alpha * lvl)

    def _sky_blend(self, canvas: PixelCanvas, x: float, y: float, col: RGB, a: float) -> None:
        xi, py = int(x), self.h - 1 - int(y)
        if 0 <= xi < self.w and 0 <= py < self.h and canvas.rows[py][xi] == self.sky[py][xi]:
            canvas.rows[py][xi] = mix(self.sky[py][xi], col, a)

    def _draw_lavaglow(self, canvas: PixelCanvas, t: float) -> None:
        """Ember Sanctum: the horizon pulses with the heat of the lava below."""
        h, w, sky, rows = self.h, self.w, self.sky, canvas.rows
        pulse = 0.5 + 0.5 * math.sin(t * 1.7)
        y0 = int(h * 0.62)
        for py in range(y0, h):
            a = round(0.24 * pulse * ((py - y0) / max(1, h - y0)) ** 1.5 * 20) / 20
            if a < 0.03:
                continue
            row, srow = rows[py], sky[py]
            for x in range(w):
                if row[x] == srow[x]:
                    row[x] = mix(srow[x], (255, 110, 30), a)

    def _draw_rift(self, canvas: PixelCanvas, t: float) -> None:
        """Astral Rift: a colossal ring of light and dark turning in the sky, with spiralling arms and an eclipsed core."""
        w, h = self.w, self.h
        cx, cy, R = w * 0.5, h * 0.62, h * 0.36
        sb = lambda x, y, c, a: self._sky_blend(canvas, x, y, c, a)
        for rad, spd in ((R, 0.35), (R * 0.78, -0.55), (R * 1.2, 0.2)):
            n = int(math.tau * rad * 1.6)
            for i in range(n):
                ang = i / n * math.tau + t * spd
                col = (255, 240, 190) if math.sin(ang) > 0 else (150, 90, 255)
                sb(cx + math.cos(ang) * rad, cy + math.sin(ang) * rad, col, 0.55 + 0.35 * math.sin(ang * 6 + t * 3))
        for k in range(12):
            ang = k * math.tau / 12 + t * 0.15
            for j in range(int(R * 0.3), int(R * 1.6)):
                sb(cx + math.cos(ang) * j, cy + math.sin(ang) * j, (255, 236, 190) if k % 2 else (140, 90, 230), 0.28 * (1 - j / (R * 1.7)))
        for arm in range(3):
            for k in range(44):
                rr = k / 44 * R * 0.95
                ang = arm * math.tau / 3 + k * 0.17 + t * 1.1
                sb(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr, (255, 250, 230), 0.8 * (1 - k / 50))
        r0 = R * 0.3
        for yy in range(int(cy - r0), int(cy + r0) + 1):
            for xx in range(int(cx - r0), int(cx + r0) + 1):
                d = math.hypot(xx - cx, yy - cy)
                if d <= r0:
                    sb(xx, yy, (6, 2, 16), 0.8)
                elif d <= r0 + 1.2:
                    sb(xx, yy, (255, 214, 120), 0.6 + 0.3 * math.sin(t * 5))

    def _make_bolt(self, k: int) -> list:
        """Deterministic jagged bolt for strike number k: a list of (x0, y0, x1, y1) segments plus its ground x."""
        r = random.Random(k * 7919 + self.w)
        x, y = r.uniform(0.12, 0.88) * self.w, float(self.h - 1)
        segs, ground = [], self._terrain
        stop = lambda px: (ground.heights[int(clamp(px, 0, self.w - 1))] if ground else 0) + 1

        def run(px, py, limit, branch):
            while py > limit:
                nx, ny = px + r.uniform(-4.5, 4.5), py - r.uniform(2.0, 5.0)
                segs.append((px, py, nx, ny))
                if not branch and r.random() < 0.16:
                    run(nx, ny, max(limit, ny - r.uniform(8, 18)), True)
                px, py = nx, ny
        run(x, y, stop(x), False)
        return segs

    def _draw_storm(self, canvas: PixelCanvas, t: float, flashes: bool) -> None:
        period = 3.4
        k = int(t / period)
        off = 0.5 + (((k * 2654435761) >> 8) & 255) / 255 * 1.6
        local = t - k * period - off
        if not 0 <= local < 0.42:
            return
        if k != self._bolt_key:
            self._bolt_key, self._bolt = k, self._make_bolt(k)
        flick = 1.0 if (local < 0.1 or int(local * 25) % 2 == 0) else 0.5
        inten = round((1 - local / 0.42) * flick * 4) / 4
        if inten <= 0 or not self._bolt:
            return
        h, w, sky, rows = self.h, self.w, self.sky, canvas.rows
        bx = self._bolt[0][0]
        if flashes:                                       # soft local glow around the strike, never the whole sky
            for py in range(h):
                row, srow = rows[py], sky[py]
                for x in range(max(0, int(bx) - 22), min(w, int(bx) + 23)):
                    if row[x] == srow[x]:
                        a = round(0.2 * inten * (1 - abs(x - bx) / 23) * 20) / 20
                        if a > 0.02:
                            row[x] = mix(srow[x], (170, 200, 255), a)
        for x0, y0, x1, y1 in self._bolt:
            n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
            for i in range(n + 1):
                u = i / n
                px, py = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
                canvas.blendf(px, py, (235, 245, 255), min(1.0, inten * 1.3))
                if inten > 0.5:
                    canvas.blendf(px + 1, py, (130, 170, 255), 0.35 * inten)
                    canvas.blendf(px - 1, py, (130, 170, 255), 0.35 * inten)


# (density per pixel, rise speed, three colours, strength) for the drifting-particle sky layers
MOTE_STYLES = {
    "embers": (0.0085, 9.0, ((255, 236, 150), (255, 150, 50), (230, 70, 24)), 0.85),
    "motes": (0.0035, 4.0, ((255, 240, 190), (255, 206, 100), (255, 170, 80)), 0.7),
    "snow": (0.007, -6.0, ((255, 255, 255), (220, 238, 255), (190, 220, 250)), 0.85),
    "fireflies": (0.003, 1.2, ((220, 255, 140), (170, 255, 110), (255, 240, 150)), 0.8),
    "ash": (0.006, -3.5, ((170, 168, 170), (130, 126, 130), (200, 196, 200)), 0.6),
    "stardust": (0.005, 2.5, ((255, 255, 255), (190, 170, 255), (140, 220, 255)), 0.8),
    "inferno": (0.011, 14.0, ((255, 236, 150), (255, 140, 40), (220, 50, 20)), 0.9),
    "tempest": (0.010, -42.0, ((190, 220, 255), (130, 180, 240), (220, 240, 255)), 0.55),
    "rift": (0.007, 6.0, ((255, 244, 205), (160, 110, 255), (255, 255, 255)), 0.85),
    "plankton": (0.006, 1.6, ((140, 255, 230), (110, 200, 255), (210, 170, 255)), 0.8),
    "sakura": (0.006, -4.5, ((255, 196, 220), (255, 160, 196), (255, 230, 240)), 0.9),
    "rain": (0.012, -48.0, ((170, 190, 240), (130, 150, 210), (200, 210, 255)), 0.55),
    "spores": (0.006, 1.8, ((190, 255, 220), (230, 190, 255), (150, 230, 255)), 0.85),
    "sandfall": (0.008, -7.0, ((240, 210, 160), (220, 180, 120), (255, 230, 190)), 0.7),
    "ghostlights": (0.004, 2.0, ((150, 255, 190), (100, 230, 160), (210, 255, 230)), 0.85),
}
