"""Scenery layers for themed home screens. A HomeTheme lists layer names; LAYER_DRAWERS maps each name to the
function that paints it (moon, city, grid, worldtree, sky whale, ...). Add a function and an entry to create a new layer."""
from __future__ import annotations

import math
import random
from typing import Optional

from tanks.art.bosses import draw_artifact, draw_mage
from tanks.colors import RGB, clamp, hsv, mix, shade
from tanks.content.martyr import ELEMENTS
from tanks.content.paints import rainbow
from tanks.screen import PixelCanvas, Screen


def _cell(screen: Screen, x: int, y: int, col: RGB, ch: str = " ", fg: Optional[RGB] = None) -> None:
    if 0 <= x < screen.cols and 0 <= y < screen.rows:
        screen.put(x, y, ch, fg or col, col)


def _L_disc(self, screen, cols, rows, cx, cy, r, col, glow=True):
    for y in range(int(cy - r * 1.8), int(cy + r * 1.8) + 1):
        for x in range(int(cx - r * 3.4), int(cx + r * 3.4) + 1):
            d = math.hypot((x - cx) / 2.0, y - cy)
            if d <= r:
                _cell(screen, x, y, col)
            elif glow and d <= r * 1.7 and 0 <= y < rows and 0 <= x < cols:
                bg = screen.back[y][x][2]
                screen.back[y][x] = (screen.back[y][x][0], screen.back[y][x][1], mix(bg, col, 0.32 * (1 - (d - r) / (r * 0.7))))


def _L_moon(self, screen, cols, rows, t):
    r = max(3, rows // 8)
    cx, cy = cols * 0.2, rows * 0.22
    _L_disc(self, screen, cols, rows, cx, cy, r, mix(self.th.accent, (255, 255, 255), 0.7))
    for dx, dy, cr in ((-0.3, -0.2, 0.28), (0.25, 0.25, 0.22), (0.1, -0.4, 0.15)):
        _L_disc(self, screen, cols, rows, cx + dx * r * 2, cy + dy * r, r * cr, mix(self.th.accent, (60, 60, 80), 0.4), False)


def _L_sun(self, screen, cols, rows, t):
    r = max(4, rows // 6)
    cx, cy = cols * 0.66, rows * 0.58 + math.sin(t * 0.2) * 0.4
    _L_disc(self, screen, cols, rows, cx, cy, r, mix(self.th.accent, (255, 255, 235), 0.5))
    for k in range(0, int(r * 2), 3):                                    # horizontal slits through the lower half (retro sun)
        for x in range(int(cx - r * 2), int(cx + r * 2) + 1):
            y = int(cy + r * 0.2 + k * 0.6)
            if 0 <= y < rows and 0 <= x < cols and math.hypot((x - cx) / 2.0, y - cy) <= r:
                screen.back[y][x] = (" ", (0, 0, 0), self.rowcol[y])


def _L_city(self, screen, cols, rows, t):
    r = random.Random(self.th.key)
    x, hz = 0, int(rows * 0.76)
    while x < cols:
        bw, bh = r.randint(4, 9), r.randint(rows // 8, rows // 3)
        for yy in range(hz - bh, hz):
            for xx in range(x, min(cols, x + bw)):
                lit = (xx * 7 + yy * 13 + x) % 5 < 2 and (xx - x) % 2 == 1 and (yy % 2 == 0) and (int(t * 0.4) + xx + yy) % 11 != 0
                _cell(screen, xx, yy, mix(self.th.far, (0, 0, 0), 0.45) if not lit else mix(self.th.accent, (255, 230, 160), 0.5))
        x += bw + r.randint(0, 2)


def _L_mountains(self, screen, cols, rows, t):
    hz = int(rows * 0.76)
    for x in range(cols):
        h = int(rows * 0.2 + rows * 0.12 * math.sin(x * 0.045 + 1) + rows * 0.07 * math.sin(x * 0.11) + 3 * abs(math.sin(x * 0.02)))
        for k in range(h):
            y = hz - k
            cap = k >= h - 2 and h > rows * 0.24
            _cell(screen, x, y, mix(self.th.far, (255, 255, 255), 0.65) if cap else mix(self.th.far, (0, 0, 0), 0.25 + 0.2 * k / max(1, h)))


def _L_grid(self, screen, cols, rows, t):
    hz = int(rows * 0.72)
    for y in range(hz, rows):
        k = (y - hz) / max(1, rows - hz)
        for x in range(cols):
            on_h = int((k * 8 + t * 0.9) * 2) % 4 == 0
            vx = (x - cols / 2) / max(0.3, 0.25 + k * 1.6)
            on_v = abs(vx - round(vx / 6) * 6) < 0.5
            bg = self.rowcol[y]
            if on_h or on_v:
                _cell(screen, x, y, mix(bg, self.th.accent, 0.45 + 0.4 * k))
            else:
                _cell(screen, x, y, mix(bg, (0, 0, 0), 0.55))


def _L_ocean(self, screen, cols, rows, t):
    hz = int(rows * 0.7)
    for y in range(hz, rows):
        k = (y - hz) / max(1, rows - hz)
        for x in range(cols):
            w = math.sin(x * 0.35 + t * 1.6 + y * 0.9) + math.sin(x * 0.13 - t * 0.7)
            base = mix(self.th.far, (0, 0, 0), 0.3 + 0.3 * k)
            _cell(screen, x, y, mix(base, self.th.accent, 0.35) if w > 1.25 else base, "~" if w > 1.25 else " ", mix(base, self.th.accent, 0.8))


def _L_planet(self, screen, cols, rows, t):
    r = max(5, rows // 5)
    cx, cy = cols * 0.74, rows * 0.28
    _L_disc(self, screen, cols, rows, cx, cy, r, mix(self.th.far, self.th.accent, 0.5), False)
    for x in range(int(cx - r * 3.3), int(cx + r * 3.3) + 1):
        y = int(cy + (x - cx) * 0.12)
        if abs((x - cx) / 2.0) > r * 0.4 and 0 <= y < rows and 0 <= x < cols:
            _cell(screen, x, y, mix(self.th.accent, (255, 255, 255), 0.4), "─")
            _cell(screen, x, y + 1, mix(self.th.accent, (255, 255, 255), 0.2), "─")


def _L_pyramids(self, screen, cols, rows, t):
    hz = int(rows * 0.76)
    for cx, h in ((cols * 0.25, rows * 0.28), (cols * 0.55, rows * 0.4), (cols * 0.82, rows * 0.22)):
        for k in range(int(h)):
            hw = int((h - k) * 1.9)
            for x in range(int(cx - hw), int(cx + hw) + 1):
                _cell(screen, x, hz - k, mix(self.th.far, (255, 255, 255), 0.18) if x >= cx else mix(self.th.far, (0, 0, 0), 0.3))


def _L_trees(self, screen, cols, rows, t):
    hz, r = int(rows * 0.77), random.Random(self.th.key + "t")
    x = 1
    while x < cols - 2:
        h = r.randint(rows // 8, rows // 4)
        for k in range(h):
            hw = int((h - k) * 0.55) + (1 if k % 3 == 0 else 0)
            for xx in range(x - hw, x + hw + 1):
                _cell(screen, xx, hz - k, mix(self.th.far, (0, 0, 0), 0.5))
        x += r.randint(3, 7)


def _L_rain(self, screen, cols, rows, t):
    for i in range(cols // 2):
        x0, sp = (i * 37) % cols, 14 + (i * 5) % 9
        y = int((t * sp + i * 11) % rows)
        x = int(x0 - y * 0.3) % cols
        if 0 <= y < rows:
            bg = screen.back[y][x][2]
            screen.back[y][x] = ("╱", mix(bg, (200, 220, 255), 0.55), bg)


def _L_lightning(self, screen, cols, rows, t):
    period = 3.2
    k = int(t / period)
    local = t - k * period
    if local > 0.3:
        return
    r = random.Random(k)
    x, y = r.randint(cols // 6, cols - cols // 6), 0
    while y < int(rows * 0.76):
        _cell(screen, x, y, (240, 245, 255), "█" if local < 0.15 else "▓", (240, 245, 255))
        x += r.choice((-1, 0, 1)) * 2
        y += 1


def _L_tower(self, screen, cols, rows, t):
    hz, cx = int(rows * 0.76), int(cols * 0.3)
    for k in range(int(rows * 0.7)):
        hw = max(0, int(3 - k * 3.0 / (rows * 0.7)) + (1 if k % 6 == 0 else 0))
        for x in range(cx - hw, cx + hw + 1):
            _cell(screen, x, hz - k, mix(self.th.far, (0, 0, 0), 0.35))
        if k % 5 == 2:
            _cell(screen, cx, hz - k, mix(self.th.accent, (255, 255, 255), 0.4))
    if int(t * 2) % 2 == 0:
        _cell(screen, cx, hz - int(rows * 0.7), (255, 80, 80))


def _L_comet(self, screen, cols, rows, t):
    for i in range(3):
        k = ((t * 0.18 + i * 0.37) % 1.0)
        x, y = int(cols * (1.1 - k * 1.3)), int(rows * (0.05 + k * 0.5 + i * 0.07))
        for s in range(10):
            _cell(screen, x + s * 2, y - s // 2, mix(self.rowcol[min(rows - 1, max(0, y))], (255, 255, 255), 0.9 * (1 - s / 10)), "─", mix(self.rowcol[min(rows - 1, max(0, y))], (255, 255, 255), 0.9 * (1 - s / 10)))


def _L_glitch(self, screen, cols, rows, t):
    r = random.Random(int(t * 6))
    for _ in range(3):
        y, w, x0 = r.randrange(rows), r.randint(cols // 8, cols // 3), r.randrange(cols)
        for x in range(x0, min(cols, x0 + w)):
            ch, fg, bg = screen.back[y][x]
            screen.back[y][x] = (ch, bg, mix(fg, self.th.accent, 0.5))


def _L_volcano(self, screen, cols, rows, t):
    hz, pulse = int(rows * 0.78), 0.5 + 0.5 * math.sin(t * 1.6)
    for cx, h, wd in ((cols * 0.28, rows * 0.46, 2.4), (cols * 0.74, rows * 0.36, 2.0)):
        for k in range(int(h)):
            hw = int((h - k) * wd) + 1
            for x in range(int(cx - hw), int(cx + hw) + 1):
                base = mix(self.th.far, (0, 0, 0), 0.35)
                if k > h - 4 and abs(x - cx) < 4:
                    base = mix((255, 90, 20), (255, 210, 90), pulse)
                _cell(screen, x, hz - k, base)
        for k in range(int(h * 0.7)):
            f = 0.5 + 0.5 * math.sin(t * 3 + k * 0.6)
            _cell(screen, int(cx + math.sin(k * 0.5) * 1.3), hz - int(h) + 3 + k, mix((200, 50, 14), (255, 190, 80), f))


def _L_isles(self, screen, cols, rows, t):
    for fx_, fy, rw in ((0.15, 0.30, 9), (0.5, 0.22, 13), (0.82, 0.34, 10)):
        cx = int(cols * fx_)
        cy = int(rows * fy + math.sin(t * 0.7 + fx_ * 9) * 1.0)
        for dx in range(-rw, rw + 1):
            _cell(screen, cx + dx, cy, mix(self.th.accent, (255, 255, 255), 0.2))
        for k in range(1, rw // 2 + 1):
            half = rw - k * 2
            for dx in range(-half, half + 1):
                _cell(screen, cx + dx, cy + k, mix(self.th.far, self.th.accent, 0.25))
        for k in range(1, 7):
            f = 0.5 + 0.5 * math.sin(t * 8 + k)
            _cell(screen, cx, cy + rw // 2 + k, mix((120, 200, 240), (230, 250, 255), f), "│" if k % 2 else "╎", (200, 240, 255))


def _L_riftring(self, screen, cols, rows, t):
    cx, cy, R = cols * 0.5, rows * 0.42, rows * 0.34
    for rad, spd in ((R, 0.35), (R * 0.72, -0.55)):
        n = int(rad * 14)
        for i in range(n):
            ang = i / n * math.tau + t * spd
            col = (255, 240, 190) if math.sin(ang) > 0 else (170, 110, 255)
            _cell(screen, int(cx + math.cos(ang) * rad * 2.0), int(cy + math.sin(ang) * rad), col)
    for k in range(12):
        ang = k * math.tau / 12 + t * 0.15
        for j in range(int(R * 0.4), int(R * 1.5), 2):
            x, y = int(cx + math.cos(ang) * j * 2.0), int(cy + math.sin(ang) * j)
            if 0 <= x < cols and 0 <= y < rows:
                screen.put(x, y, "·", (255, 236, 190) if k % 2 else (150, 100, 240))
    r0 = R * 0.28
    for yy in range(int(cy - r0), int(cy + r0) + 1):
        for xx in range(int(cx - r0 * 2), int(cx + r0 * 2) + 1):
            d = math.hypot((xx - cx) / 2.0, yy - cy)
            if d <= r0:
                _cell(screen, xx, yy, (6, 2, 16))
            elif d <= r0 + 0.9:
                _cell(screen, xx, yy, mix((255, 200, 100), (255, 250, 220), 0.5 + 0.5 * math.sin(t * 5)))


def _L_hourglass(self, screen, cols, rows, t):
    cx, top, H = int(cols * 0.5), int(rows * 0.1), int(rows * 0.6)
    Wd = max(6, int(rows * 0.3))
    level = (t * 0.06) % 1.0
    for k in range(H):
        f = abs(H / 2 - k) / (H / 2)                      # 1 at the ends, 0 at the waist
        hw = int(3 + f * Wd)
        y = top + k
        sand = (k < H / 2 and k > (H / 2) * level) or (k >= H / 2 and (k - H / 2) / (H / 2) > 1 - level)
        for dx in range(-hw, hw + 1):
            edge = abs(dx) >= hw - 1 or k in (0, H - 1)
            if edge:
                _cell(screen, cx + dx * 2 // 1, y, (255, 226, 150))
            elif sand:
                _cell(screen, cx + dx * 2, y, mix((200, 140, 50), (255, 230, 150), 0.5 + 0.5 * math.sin(t * 2 + dx + k)))
        if abs(H / 2 - k) < H / 2 * 0.5 and 0 < level < 1:
            screen.put(cx, y, "│" if int(t * 12 + k) % 2 else "╎", (255, 236, 180))
    for i in range(80):
        ang = i / 80 * math.tau + t * 0.4
        _cell(screen, int(cx + math.cos(ang) * Wd * 3.2), int(top + H / 2 + math.sin(ang) * H * 0.6), mix((255, 226, 150), (255, 255, 255), 0.5 + 0.5 * math.sin(ang * 5 + t * 3)))


def _L_sunburst(self, screen, cols, rows, t):
    cx, cy, R = cols * 0.5, rows * 0.45, rows * 0.28
    for k in range(18):
        ang = k * math.tau / 18 + t * 0.12
        for j in range(int(R * 1.1), int(R * 3.2), 2):
            x, y = int(cx + math.cos(ang) * j * 2.0), int(cy + math.sin(ang) * j)
            if 0 <= x < cols and 0 <= y < rows:
                screen.put(x, y, "·" if k % 2 else "∙", (255, 226, 130) if k % 3 else (255, 255, 235))
    for yy in range(int(cy - R), int(cy + R) + 1):
        for xx in range(int(cx - R * 2), int(cx + R * 2) + 1):
            d = math.hypot((xx - cx) / 2.0, yy - cy)
            if d <= R:
                _cell(screen, xx, yy, mix((255, 250, 220), (255, 190, 70), d / R * 0.8 + 0.1 * math.sin(t * 2 + d)))
            elif d <= R + 1.0:
                _cell(screen, xx, yy, mix((255, 210, 90), (255, 255, 255), 0.5 + 0.5 * math.sin(t * 4)))
    n = int(R * 12)
    for i in range(n):
        ang = i / n * math.tau - t * 0.5
        _cell(screen, int(cx + math.cos(ang) * R * 1.45 * 2.0), int(cy + math.sin(ang) * R * 1.45), (255, 226, 130))


def _L_arcane(self, screen, cols, rows, t):
    cx, cy, R = cols * 0.5, rows * 0.42, rows * 0.36
    def P(a, rad):
        return int(cx + math.cos(a) * rad * 2.0), int(cy + math.sin(a) * rad)
    for rad, spd in ((R * 1.08, 0.15), (R * 0.92, -0.2)):
        n = int(rad * 16)
        for i in range(n):
            ang = i / n * math.tau + t * spd
            x, y = P(ang, rad)
            if 0 <= x < cols and 0 <= y < rows and i % 3 != 0:
                screen.put(x, y, "◦" if i % 2 else "·", (255, 226, 150))
    for tri in (0, 1):                                              # a slowly turning hexagram
        pts = [P(t * 0.25 + tri * math.pi / 3 + k * math.tau / 3, R * 0.9) for k in range(3)]
        for k in range(3):
            (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % 3]
            for j in range(40):
                f = j / 40
                x, y = int(x0 + (x1 - x0) * f), int(y0 + (y1 - y0) * f)
                if 0 <= x < cols and 0 <= y < rows:
                    screen.put(x, y, "·", (255, 240, 190) if tri else (190, 140, 255))
    for i, el in enumerate(ELEMENTS):                                  # the six elements circling
        ang = t * 0.7 + i * math.tau / 6
        x, y = P(ang, R * 1.08)
        col = ELEMENTS[el][4]
        for dx, dy in ((0, 0), (1, 0), (-1, 0)):
            _cell(screen, x + dx, y + dy, col)


def _L_sanctum(self, screen, cols, rows, t):
    """PROTECTOR OF THE UNIVERSE: the Martyr (the cutscene's archmage) stands on the ridge, and above him hangs the Arcane Time
    Machine itself (the cutscene's own artifact: a glowing hourglass wrapped in turning rune rings). A thin thread of light
    ties the two together; three elemental orbs circle the machine and a quiet rune circle glows at his feet."""
    rc, G, V = self.rowcol, (255, 214, 100), (176, 120, 255)
    mx = int(cols * 0.88)
    rid = self.ridge[min(cols - 1, mx)]
    sc = clamp(rows * 2 * 0.40 / 32.0, 0.9, 2.2)                      # the mage is ~40% of the screen height
    tm_s = clamp(rows * 2 * 0.02, 0.9, 1.6)                          # the Time Machine hangs above him
    tcy = rows * 2 - int(rows * 2 * 0.20)                             # its centre, in canvas pixels (y up)
    head = rid * 2 + 2 + int(32 * sc)                                 # top of the mage, canvas pixels
    for yy in range(head + 3, tcy - int(7 * tm_s), 3):               # the thread of light between them
        r_ = rows - 1 - yy // 2
        if 0 <= r_ < rows - rid:
            screen.put(mx, r_, "·", shade(mix(G, V, 0.5 + 0.5 * math.sin(yy * 0.4 - t * 3)), 0.8), rc[r_])
    for k, col in enumerate(((255, 120, 70), (110, 190, 255), (150, 255, 170))):               # fire, water, earth orbs round the machine
        ang = t * 0.8 + k * math.tau / 3
        x = mx + int(math.cos(ang) * 9 * tm_s)
        y = rows - 1 - int(tcy / 2) + int(math.sin(ang) * 3 * tm_s)
        if 0 <= x < cols - 1 and 0 <= y < rows - rid:
            screen.put(x, y, "●", col, rc[y])
    cv = PixelCanvas(cols, rows * 2, (0, 0, 0))
    draw_artifact(cv, mx, tcy, tm_s, t)
    draw_mage(cv, mx, rid * 2 + 2, sc, t, 1.0, True)
    for r in range(rows):
        for c in range(max(0, mx - 34), min(cols, mx + 34)):
            a_, b_ = cv.rows[2 * r][c], cv.rows[2 * r + 1][c]
            if a_ == (0, 0, 0) and b_ == (0, 0, 0):
                continue
            bgc = screen.back[r][c][2]
            screen.back[r][c] = ("▀", bgc if a_ == (0, 0, 0) else a_, bgc if b_ == (0, 0, 0) else b_)
    gy = rows - rid                                                   # a quiet rune circle at his feet
    for i in range(36):
        ang = i * math.tau / 36 - t * 0.35
        x, y = mx + int(math.cos(ang) * 11), gy + int(math.sin(ang) * 1.2)
        if 0 <= x < cols and 0 <= y < rows:
            screen.put(x, y, "✦" if i % 9 == 0 else "·", shade(mix(G, V, 0.5 + 0.5 * math.sin(ang * 3 + t)), 0.8), rc[min(rows - 1, y)])


def _L_twinsuns(self, screen, cols, rows, t):
    """GLASS DESERT: two suns of different size sinking into the same haze, with sun-pillars of light on the dune-glass."""
    for cx_f, cy_f, r, col in ((0.26, 0.34, max(3, rows // 6), (255, 236, 176)), (0.44, 0.45, max(2, rows // 10), (255, 150, 110))):
        _L_disc(self, screen, cols, rows, int(cols * cx_f), int(rows * cy_f), r, col)
    for k, cx_f in enumerate((0.26, 0.44)):                                  # the sun-pillars: a slow shimmering column down to the dunes
        x = int(cols * cx_f)
        for y in range(int(rows * 0.5), rows - 4):
            if (y + int(t * 6)) % 3 == 0 and 0 <= x < cols:
                screen.put(x + int(math.sin(y * 0.5 + t * 2) * (1 + k)), y, "│", mix(self.rowcol[min(rows - 1, y)], (255, 230, 170), 0.5))
    for i in range(14):                                                      # glints: glass catching the light
        gx = int((i * 53 + 11) % cols)
        gy = rows - 3 - int((i * 7) % 6)
        if (int(t * 3) + i) % 5 == 0 and 0 <= gy < rows:
            screen.put(gx, gy, "✦", rainbow(t * 0.7 + i * 0.3))


def _L_lanterns(self, screen, cols, rows, t):
    """LANTERN FEST: solid paper lanterns (red, gold, white) drifting up from the temple roofs, swaying, with soft warm halos."""
    rc = self.rowcol
    for i in range(30):
        ph = (t * (0.04 + (i % 5) * 0.01) + i * 0.173) % 1.0
        x = int((i * 37 + 9) % cols + math.sin(t * 0.8 + i) * 2)
        y = int(rows * 0.9 - ph * rows * 0.88)
        if not (1 <= x < cols - 3 and 2 <= y < rows - 4):
            continue
        glow = 0.7 + 0.3 * math.sin(t * 3 + i * 1.7)
        base = ((255, 90, 50), (255, 190, 80), (255, 236, 200))[i % 3]
        col = shade(base, 0.7 + 0.3 * glow)
        for dy in (-2, -1, 0, 1, 2):                                     # soft halo
            for dx in range(-3, 4):
                if abs(dx) + abs(dy) * 2 <= 4 and (dx, dy) != (0, 0):
                    cell = screen.back[y + dy][x + dx] if 0 <= y + dy < rows and 0 <= x + dx < cols else None
                    if cell is not None:
                        _cell(screen, x + dx, y + dy, mix(rc[y + dy], col, 0.14 * glow))
        for dx in (0, 1):                                                # the lantern body: a solid 2x2 block with a top cap and tassel
            _cell(screen, x + dx, y, col, "▀", mix(col, (255, 255, 255), 0.3))
            _cell(screen, x + dx, y + 1, shade(col, 0.8), "▄", shade(col, 0.55))
        screen.put(x, y - 1, "▂", (90, 40, 20))
        screen.put(x, y + 2, "╵", shade(col, 0.6))


def _L_worldtree(self, screen, cols, rows, t):
    """WORLDTREE: a colossal solid trunk at the left, a canopy of glowing leaf-masses across the whole sky, veins of light pulsing
    up the bark and petals drifting down."""
    rc = self.rowcol
    tx = int(cols * 0.13)
    for y in range(0, rows - 3):
        w_ = 5 + int((y / max(1, rows)) * 9) + int(math.sin(y * 0.5) * 1.2)
        for dx in range(-w_, w_ + 1):
            u = abs(dx) / max(1, w_)
            if 0 <= tx + dx < cols:
                _cell(screen, tx + dx, y, mix((26, 60, 50), (6, 20, 22), u ** 0.7 * 0.9 + (0.12 if (dx + y // 3) % 4 == 0 else 0)))
        pulse = (y * 0.35 - t * 3) % 9
        for k in range(-2, 3):
            if pulse < 1.5 and 0 <= tx + k * 2 < cols:
                _cell(screen, tx + k * 2 + int(math.sin(y * 0.5) * 1.5), y, mix((30, 120, 90), (150, 255, 210), 1 - pulse / 1.5))
    for y in range(0, max(4, int(rows * 0.3))):                          # the canopy: overlapping leaf-masses
        for x in range(0, cols):
            v = math.sin(x * 0.16 + y * 0.9 + t * 0.15) + math.sin(x * 0.06 - y * 0.55 + 1.3) * 0.9 + math.cos(x * 0.11 + t * 0.1) * 0.5
            if v > 0.45 - y * 0.05:
                k = clamp((v - 0.2) / 2.2, 0, 1)
                _cell(screen, x, y, mix(rc[y], mix((14, 90, 70), (80, 230, 160), k), 0.55 + 0.35 * k), "▒" if k > 0.5 else "░", mix((120, 255, 200), (255, 255, 255), k * 0.5))
    for i in range(22):                                                  # glowing petals
        ph = (t * 0.06 + i * 0.137) % 1.0
        x = int((i * 41 + 7) % cols + math.sin(t + i) * 3)
        y = int(ph * (rows - 4))
        if 0 <= x < cols and 0 <= y < rows - 3:
            screen.put(x, y, "✿" if i % 2 else "❀", mix((150, 255, 200), (255, 255, 255), 0.5 + 0.5 * math.sin(t * 4 + i)))


def _L_whale(self, screen, cols, rows, t):
    """SKY WHALE: a vast solid whale sailing slowly through the stars (belly lighter than its back, flukes sweeping, glowing spots,
    a calf drifting far behind it)."""
    rc = self.rowcol
    for scale, yf, spd, off, dim in ((1.0, 0.30, 0.010, 0.25, 0.0), (0.4, 0.62, 0.016, 0.55, 0.5)):
        L_ = max(20, int(cols * 0.98 * scale))
        x0 = int((cols + L_) * ((off + t * spd) % 1.0) - L_)
        cy = int(rows * yf + math.sin(t * 0.3) * 1.3)
        for i in range(L_):
            u = i / L_
            hgt = max(0.0, math.sin(min(1.0, u * 1.08) * math.pi)) ** 0.7 * (rows * 0.26 * scale) * (1.0 - 0.6 * max(0.0, u - 0.7) / 0.3)
            if u > 0.86:
                hgt += (u - 0.86) * 20 * scale * (0.5 + 0.5 * math.sin(t * 1.6))      # the flukes sweeping
            x = x0 + i
            for dy in range(-int(hgt), int(hgt * 0.75) + 1):
                if 0 <= x < cols and 0 <= cy + dy < rows - 3:
                    f = (dy + hgt) / max(1.0, hgt * 1.75)                                 # 0 at the back, 1 at the belly
                    col = mix((18, 34, 84), (150, 190, 235), f ** 1.5)
                    _cell(screen, x, cy + dy, mix(rc[cy + dy], col, 1.0 - dim * 0.6))
            if i % 6 == 0 and 0 <= x < cols and 0 <= cy - int(hgt * 0.35) < rows:
                screen.put(x, cy - int(hgt * 0.35), "•", shade((150, 235, 255), (0.45 + 0.55 * math.sin(t * 2 + i)) * (1 - dim * 0.5)))
            if int(hgt * 0.7) > 1 and i % 3 == 0 and 0 <= x < cols and 0 <= cy + int(hgt * 0.45) < rows:        # throat grooves
                screen.put(x, cy + int(hgt * 0.45), "─", (170, 205, 245))
        ex = x0 + int(L_ * 0.13)
        if 0 <= ex < cols - 1 and 0 <= cy < rows:
            _cell(screen, ex, cy - 1, (240, 250, 255), "●", (20, 40, 90))


def _L_shards(self, screen, cols, rows, t):
    """SHATTERLINE: big slabs of translucent glass drifting over a cracked moon; each facet flashes its own prism colour as it turns."""
    rc = self.rowcol
    mx_, my_ = int(cols * 0.5), int(rows * 0.34)
    for a in range(9):                                                   # cracks radiating from the moon across the whole sky
        ang = a * math.tau / 9 + 0.4
        for s in range(3, int(rows * 0.62)):
            x, y = mx_ + int(math.cos(ang) * s * 2), my_ + int(math.sin(ang) * s)
            if 0 <= x < cols and 0 <= y < rows - 3 and (s + a) % 3:
                screen.put(x, y, "╱" if (a % 2) else "╲", (214, 204, 255))
    for i in range(12):
        cx_ = int((i * 61 + 5) % cols + math.sin(t * 0.3 + i) * 3)
        cy_ = int(rows * (0.1 + (i * 29 % 50) / 100) + math.sin(t * 0.5 + i * 2) * 1.5)
        w_ = 5 + (i * 7) % 7
        tilt = math.sin(t * 0.6 + i)
        for dx in range(-w_, w_ + 1):
            for dy in range(-2, 3):
                if abs(dx) + abs(dy) * 3 <= w_ + 1 and 0 <= cx_ + dx < cols and 0 <= cy_ + dy < rows - 3:
                    k = (dx * tilt * 0.25 + dy * 0.4) + t * 0.35 + i * 0.2
                    edge = abs(dx) + abs(dy) * 3 >= w_
                    _cell(screen, cx_ + dx, cy_ + dy, mix(rc[cy_ + dy], rainbow(k), 0.30 if not edge else 0.7),
                          "◆" if (dx + dy + i) % 5 == 0 else " ", (255, 255, 255))


class _Px:
    """A half-block pixel layer over the home screen (top-down pixel coordinates, 2 pixels per text row).
    Starts from the screen's current backgrounds so everything can be alpha-blended, and writes back only changed cells."""

    def __init__(self, screen, cols: int, rows: int) -> None:
        self.screen, self.W, self.H = screen, cols, rows * 2
        self.rows = []
        for r in range(rows):
            line = [screen.back[r][c][2] for c in range(cols)]
            self.rows.append(line)
            self.rows.append(line[:])
        self.base = [row[:] for row in self.rows]

    def blend(self, x: float, y: float, c: RGB, a: float) -> None:
        xi, yi = int(x), int(y)
        if 0 <= xi < self.W and 0 <= yi < self.H and a > 0.02:
            row = self.rows[yi]
            row[xi] = mix(row[xi], c, min(1.0, a))

    def put(self, x: float, y: float, c: RGB) -> None:
        xi, yi = int(x), int(y)
        if 0 <= xi < self.W and 0 <= yi < self.H:
            self.rows[yi][xi] = c

    def get(self, x: int, y: int) -> RGB:
        return self.rows[max(0, min(self.H - 1, y))][max(0, min(self.W - 1, x))]

    def line(self, x0: float, y0: float, x1: float, y1: float, c: RGB, a: float = 1.0) -> None:
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for j in range(n + 1):
            self.blend(x0 + (x1 - x0) * j / n, y0 + (y1 - y0) * j / n, c, a)

    def disc(self, cx: float, cy: float, r: float, c: RGB, a: float = 1.0, glow: float = 0.0, glow_c: Optional[RGB] = None) -> None:
        R = r + glow
        for y in range(int(cy - R) - 1, int(cy + R) + 2):
            for x in range(int(cx - R) - 1, int(cx + R) + 2):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if d <= r:
                    self.blend(x, y, c, a)
                elif glow and d <= R:
                    self.blend(x, y, glow_c or c, a * 0.45 * (1 - (d - r) / glow) ** 2)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, fn) -> None:
        """fn(u, v) -> (colour, alpha) or None, with u, v in -1..1 across the ellipse."""
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                u, v = (x + 0.5 - cx) / max(0.5, rx), (y + 0.5 - cy) / max(0.5, ry)
                if u * u + v * v <= 1.0:
                    res = fn(u, v)
                    if res:
                        self.blend(x, y, res[0], res[1])

    def poly(self, pts: list, c: RGB, a: float = 1.0) -> None:
        """Filled polygon (even-odd scanline)."""
        if len(pts) < 3:
            return
        y0, y1 = int(min(p[1] for p in pts)), int(max(p[1] for p in pts)) + 1
        for y in range(max(0, y0), min(self.H, y1 + 1)):
            yc, xs = y + 0.5, []
            for i in range(len(pts)):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
                if (ay <= yc < by) or (by <= yc < ay):
                    xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(xs[k] + 0.5), int(xs[k + 1] + 0.5)):
                    self.blend(x, y, c, a)

    def commit(self) -> None:
        scr = self.screen
        q = lambda c: (c[0] & 0xFC, c[1] & 0xFC, c[2] & 0xFC)          # 6-bit channels: steadier cells, less terminal traffic
        for r in range(self.H // 2):
            top, bot, b0, b1 = self.rows[2 * r], self.rows[2 * r + 1], self.base[2 * r], self.base[2 * r + 1]
            for c in range(self.W):
                if top[c] != b0[c] or bot[c] != b1[c]:
                    scr.back[r][c] = ("▀", q(top[c]), q(bot[c]))


def _L_abyss(self, screen, cols, rows, t):
    """BIOLUME TRENCH: shafts of light from a surface far above, giant jellyfish pulsing as they drift up through the
    dark (translucent bells, radial canals, frilled arms, long tendrils), plankton, bubbles and an angler's lure below."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    for k in range(7):                                                   # god-rays swaying from the surface
        x0 = W * (-0.05 + k * 0.17) + math.sin(t * 0.3 + k * 1.7) * 6
        for y in range(0, int(H * 0.75)):
            f = y / (H * 0.75)
            xc = x0 + y * 0.45
            w_ = 2 + f * 8
            for dx in range(int(-w_), int(w_) + 1):
                P.blend(xc + dx, y, (110, 210, 230), 0.13 * (1 - f) * (1 - abs(dx) / (w_ + 1)) * (0.7 + 0.3 * math.sin(t * 0.8 + k)))
    for i in range(80):                                                  # plankton
        x = (i * 97.3 + math.sin(t * 0.4 + i) * 4) % W
        y = (i * 53.1 - t * (1.5 + i % 4)) % H
        tw = 0.5 + 0.5 * math.sin(t * 3 + i * 2.1)
        P.blend(x, y, (120, 255, 230) if i % 3 else (200, 160, 255), 0.25 + 0.6 * tw)
    S = min(1.4, max(0.7, H / 80))
    for j, (xf, sz, spd, hue) in enumerate(((0.13, 1.0, 1.0, (255, 130, 220)), (0.87, 1.15, 0.75, (130, 220, 255)), (0.76, 0.55, 1.4, (190, 255, 210)),
                                            (0.25, 0.45, 1.7, (255, 210, 140)))):
        span = H * 1.5
        cy = H * 0.95 - ((t * spd * 2.4 + j * span * 0.31) % span) + H * 0.1
        cx = W * xf + math.sin(t * 0.5 + j * 2) * 4
        pulse = 0.5 + 0.5 * math.sin(t * 2.2 + j * 1.3)
        rx, ry = 12 * sz * S * (1.0 + 0.12 * pulse), 9 * sz * S * (1.0 - 0.15 * pulse)
        for k in range(10):                                              # long trailing tendrils
            tx = cx + (k - 4.5) * rx * 0.19
            ln = int(36 * sz * S)
            for s in range(ln):
                sw = math.sin(s * 0.2 - t * 2.0 + k) * (0.6 + s * 0.07)
                P.blend(tx + sw, cy + ry * 0.15 + s, mix(hue, (255, 255, 255), 0.25), 0.55 * (1 - s / ln))
        for k in range(4):                                               # frilled oral arms
            tx = cx + (k - 1.5) * rx * 0.22
            for s in range(int(16 * sz * S)):
                w_ = 1.6 * (1 - s / (16 * sz * S))
                for dw in (-1, 0, 1):
                    P.blend(tx + math.sin(s * 0.45 + t * 2.6 + k) * 1.8 + dw * w_, cy + 1 + s, mix(hue, (255, 255, 255), 0.5), 0.5 * (1 - s / (16 * sz * S)))

        def bell(u, v, hue=hue):
            if v > 0.2:
                return None
            d = u * u + v * v
            canal = 0.25 if abs(math.sin(math.atan2(v, u) * 4)) < 0.18 else 0.0
            return (mix(hue, (255, 255, 255), 0.6 * (1 - d) + canal), 0.30 + 0.45 * d + canal)
        P.ellipse(cx, cy, rx, ry, bell)
        P.ellipse(cx, cy - ry * 0.25, rx * 0.45, ry * 0.4, lambda u, v, hue=hue: (mix(hue, (255, 255, 255), 0.7), 0.35 * (1 - (u * u + v * v))))
        for k in range(30):                                              # glowing rim lights, chasing round the bell
            a_ = math.pi + k * math.pi / 29
            P.blend(cx + math.cos(a_) * rx, cy + math.sin(a_) * ry * 0.98 + 0.5, (255, 255, 255), 0.35 + 0.6 * max(0.0, math.sin(t * 4 - k * 0.5)))
        for k in range(16):
            P.blend(cx - rx + k * rx * 2 / 15, cy + ry * 0.2, mix(hue, (255, 255, 255), 0.5), 0.8)
    for b in range(5):                                                   # bubble columns
        bx = W * (0.04 + b * 0.23)
        for i in range(9):
            y = H - ((t * 9 + i * 7 + b * 13) % (H * 0.9))
            P.disc(bx + math.sin(y * 0.3 + b) * 1.5, y, 0.6 + (i % 3) * 0.3, (200, 240, 255), 0.5)
    lx, ly = W * 0.30 + math.sin(t * 0.6) * 3, H * 0.60 + math.sin(t * 1.1) * 2     # the angler waiting in the dark
    P.ellipse(lx + 10, ly + 9, 15, 7, lambda u, v: ((3, 8, 18), 0.9))
    for k in range(8):
        P.blend(lx + 1 + k * 1.6, ly + 8 + (k % 2), (220, 230, 240), 0.75)          # needle teeth
    P.disc(lx + 17, ly + 6, 1.0, (255, 250, 210), 0.9)                                 # a pale eye
    for k in range(10):
        f = k / 9
        P.blend(lx + 8 - f * 8 + math.sin(t * 1.3) * f * f * 2, ly + 3 - f * 6, (40, 90, 110), 0.85)
    glow = 0.7 + 0.3 * math.sin(t * 3.1)
    P.disc(lx + math.sin(t * 1.3) * 2, ly - 4, 1.5, (210, 255, 245), glow, 6, (60, 210, 220))
    P.commit()


def _L_shrine(self, screen, cols, rows, t):
    """SPIRIT SHRINE: a huge moon, a vermilion path of torii gates climbing the right-hand mountain to a lantern-lit shrine,
    a stone lantern and a cherry tree on the left, petals on the wind and blue foxfire wisps drifting between the gates."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    mx, my, mr = W * 0.86, H * 0.20, min(W * 0.11, H * 0.17)
    P.disc(mx, my, mr, (255, 244, 222), 1.0, mr * 1.1, (255, 214, 200))
    for k in range(6):                                                   # moon maria
        P.disc(mx + math.cos(k * 1.9) * mr * 0.5, my + math.sin(k * 2.7) * mr * 0.45, mr * 0.15, (236, 224, 204), 0.7)
    for layer, (base, amp, col) in enumerate(((0.52, 0.14, (62, 42, 92)), (0.64, 0.10, (40, 26, 64)))):   # far ranges
        pts = [(0, H)] + [(x, H * base - amp * H * (0.5 + 0.5 * math.sin(x * 0.035 + layer * 2) * math.cos(x * 0.013 + layer))) for x in range(0, W + 4, 4)] + [(W, H)]
        P.poly(pts, col, 1.0)
    peak_x, peak_y = W * 0.86, H * 0.36                                  # the shrine mountain on the right
    P.poly([(W * 0.62, H), (W * 0.74, H * 0.55), (peak_x - 6, peak_y + 3), (peak_x + 6, peak_y + 3), (W * 1.02, H * 0.5), (W * 1.02, H)], (30, 18, 46), 1.0)
    P.poly([(peak_x - 9, peak_y), (peak_x + 9, peak_y), (peak_x + 6, peak_y - 5), (peak_x - 6, peak_y - 5)], (160, 32, 30), 1.0)   # shrine roof
    P.poly([(peak_x - 6, peak_y), (peak_x + 6, peak_y), (peak_x + 6, peak_y + 5), (peak_x - 6, peak_y + 5)], (60, 18, 22), 1.0)
    P.disc(peak_x, peak_y + 2.5, 1.3, (255, 220, 140), 1.0, 4, (255, 170, 80))
    gates = [(W * (0.64 + 0.046 * k), H * (0.74 - 0.066 * k), 1.0 - 0.12 * k) for k in range(5)]
    for gx, gy, s in reversed(gates):
        red, dark, blk = (226, 58, 40), (128, 26, 22), (28, 16, 18)
        hw, hh = 8 * s, 15 * s
        for side in (-1, 1):                                             # pillars
            for y in range(int(gy - hh), int(gy) + 1):
                P.put(gx + side * hw * 0.62, y, red)
                if s > 0.5:
                    P.put(gx + side * hw * 0.62 + 1, y, dark)
        for x in range(int(gx - hw * 1.2), int(gx + hw * 1.2) + 1):    # kasagi (curved top beam) and nuki (tie beam)
            lift = ((x - gx) / (hw * 1.2)) ** 4 * 2.4 * s
            P.put(x, gy - hh - lift - 1, blk)
            P.put(x, gy - hh - lift, red)
            if abs(x - gx) <= hw * 0.85:
                P.put(x, gy - hh + 4 * s, red)
        P.put(gx, gy - hh + 2 * s, blk)
    lx, ly = W * 0.14, H * 0.70                                          # a stone lantern (toro) with a living flame
    P.poly([(lx - 6, ly), (lx + 6, ly), (lx + 4, ly - 3), (lx - 4, ly - 3)], (120, 116, 130), 1.0)
    P.poly([(lx - 2, ly - 3), (lx + 2, ly - 3), (lx + 2, ly - 12), (lx - 2, ly - 12)], (110, 106, 120), 1.0)
    P.poly([(lx - 5, ly - 12), (lx + 5, ly - 12), (lx + 5, ly - 18), (lx - 5, ly - 18)], (130, 126, 140), 1.0)
    fl = 0.75 + 0.25 * math.sin(t * 9) * math.sin(t * 4)
    P.disc(lx, ly - 15, 1.8, (255, 220, 150), fl, 6, (255, 170, 80))
    P.poly([(lx - 8, ly - 18), (lx + 8, ly - 18), (lx + 2, ly - 23), (lx - 2, ly - 23)], (100, 96, 112), 1.0)
    for b, (bx, by, ang, ln) in enumerate(((0, H * 0.06, 0.22, W * 0.26), (W * 0.05, H * 0.16, -0.12, W * 0.16), (W * 0.15, H * 0.10, 0.6, W * 0.07))):
        for s in range(int(ln)):                                         # cherry branches, heavy with blossom
            x, y = bx + s * math.cos(ang), by + s * math.sin(ang) + math.sin(s * 0.08 + b) * 3
            P.put(x, y, (44, 24, 28))
            if s < ln * 0.5:
                P.put(x, y + 1, (44, 24, 28))
            if s % 2 == 0:
                for k in range(3):
                    P.blend(x + math.sin(s * 1.7 + k * 2 + b) * 3, y + math.cos(s * 2.3 + k) * 2.6 - 1, (255, 176 + (s * 7 % 50), 210), 0.9)
    for i in range(16):                                                  # foxfire wisps between the gates
        ph = t * 0.35 + i * 0.83
        x = W * (0.62 + (i * 0.061) % 0.36) + math.sin(ph * 2) * 4 if i % 2 else W * (0.03 + (i * 0.043) % 0.26) + math.sin(ph * 2) * 4
        y = H * (0.38 + 0.3 * ((i * 0.37) % 1)) + math.sin(ph * 1.3) * 3
        fl = 0.6 + 0.4 * math.sin(t * 7 + i * 2.3)
        P.disc(x, y, 0.8, (232, 246, 255), fl, 3, (80, 140, 255))
        P.blend(x, y + 1.5, (100, 160, 255), 0.5 * fl)
    for i in range(40):                                                  # petals on the wind
        x = (i * 41.7 + t * (5 + i % 3) + math.sin(t + i) * 6) % W
        y = (i * 23.3 + t * (6 + i % 4)) % H
        P.blend(x, y, (255, 194, 218), 0.85)
        P.blend(x + 1, y, (255, 150, 190), 0.4)
    P.commit()


def _L_holocity(self, screen, cols, rows, t):
    """HOLO CITY: a rain-soaked megacity: three depths of towers with flickering windows, enormous scrolling hologram
    billboards, a hologram koi swimming between the spires, and streams of flying traffic."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    r = random.Random(77)
    for depth, (col, lit, hmin, hmax, wmin, wmax) in enumerate((((44, 24, 70), (120, 80, 160), 0.25, 0.5, 6, 12),
                                                                ((26, 14, 46), (255, 120, 220), 0.3, 0.65, 8, 16),
                                                                ((12, 8, 24), (90, 230, 255), 0.35, 0.8, 10, 20))):
        x = -r.randint(0, 6)
        while x < W:
            bw, bh = r.randint(wmin, wmax), H * r.uniform(hmin, hmax)
            top = H - bh
            P.poly([(x, H), (x + bw, H), (x + bw, top), (x, top)], col, 1.0)
            if r.random() < 0.4:
                P.line(x + bw // 2, top, x + bw // 2, top - r.randint(4, 10), col, 1.0)
                if (int(t * 2) + x) % 3:
                    P.blend(x + bw // 2, top - 10, (255, 60, 80), 1.0)
            for wy in range(int(top) + 3, H - 2, 3):
                for wx in range(x + 2, x + bw - 1, 3):
                    seed = (wx * 31 + wy * 17 + depth) % 97
                    if seed % 3 == 0 and (seed + int(t * 0.5 + seed)) % 11:
                        P.blend(wx, wy, lit, 0.35 + depth * 0.15)
            x += bw + r.randint(1, 4)
    for j, (bx, by, bw, bh, c1, c2) in enumerate(((W * 0.08, H * 0.18, 22, 26, (90, 230, 255), (255, 70, 210)),
                                                   (W * 0.78, H * 0.30, 26, 18, (255, 70, 210), (255, 220, 90)))):
        for y in range(int(bh)):                                         # hologram billboards: scrolling glyph columns
            for x in range(int(bw)):
                g = (x // 3 * 7 + (y + int(t * 8 * (1 + j))) // 3 * 13) % 9
                on = g < 4 and x % 3 != 2 and y % 3 != 2
                scan = 0.25 if (y + int(t * 20)) % 5 == 0 else 0.0
                if on or scan:
                    P.blend(bx + x, by + y, c1 if (x // 6 + j) % 2 else c2, (0.55 if on else 0) + scan)
        for x in range(int(bw) + 2):
            P.blend(bx - 1 + x, by - 1, c1, 0.8)
            P.blend(bx - 1 + x, by + bh, c1, 0.8)
    kx, ky = W * 0.5 + math.sin(t * 0.35) * W * 0.22, H * 0.22 + math.sin(t * 0.7) * 6     # the hologram koi
    head = math.copysign(1, math.cos(t * 0.35))
    for s in range(26):
        f = s / 25
        x = kx - head * s * 1.2
        y = ky + math.sin(t * 3 - s * 0.35) * 2.5 * f
        w_ = 4.5 * math.sin(min(1, f * 1.4 + 0.15) * math.pi) + (3 * f if f > 0.85 else 0)
        for dy in range(-int(w_), int(w_) + 1):
            glitch = 2 if (int(t * 6) + s) % 23 == 0 else 0
            P.blend(x + glitch, y + dy, (255, 120, 80) if (s // 4) % 2 else (240, 250, 255), 0.45 if abs(dy) < w_ - 1 else 0.8)
    for lane in range(4):                                                # flying traffic
        y = H * (0.25 + lane * 0.1)
        for car in range(5):
            spd = (14 + lane * 5) * (1 if lane % 2 else -1)
            x = (car * W / 5 + t * spd) % (W + 20) - 10
            col = (255, 240, 220) if spd > 0 else (255, 60, 60)
            for k in range(7):
                P.blend(x - math.copysign(k, spd), y, col, 0.9 - k * 0.12)
    for i in range(90):                                                  # rain
        x = (i * 37.1 + t * 18) % W
        y = (i * 61.7 + t * 70) % H
        P.blend(x, y, (150, 170, 220), 0.35)
        P.blend(x - 0.5, y - 1, (150, 170, 220), 0.25)
    P.commit()


def _L_hyper(self, screen, cols, rows, t):
    """THE TESSERACT: a true four-dimensional hypercube turning through two planes at once, its far cell bleeding violet
    and its near cell white-hot, over a receding light-grid and a slow nebula."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    for k in range(3):                                                   # nebula clouds
        cx, cy = W * (0.2 + k * 0.33), H * (0.25 + 0.08 * k)
        P.ellipse(cx + math.sin(t * 0.1 + k) * 6, cy, W * 0.18, H * 0.12, lambda u, v, k=k: (((90, 40, 170), (40, 90, 190), (170, 50, 140))[k], 0.18 * (1 - (u * u + v * v))))
    hz = int(H * 0.58)                                                   # synth grid floor
    for i in range(-16, 17):
        P.line(W / 2 + i * 3, hz, W / 2 + i * W * 0.09, H, (170, 90, 255), 0.35)
    for j in range(1, 12):
        y = hz + (H - hz) * ((j + (t * 0.6) % 1) / 12) ** 2
        for x in range(W):
            P.blend(x, y, (200, 110, 255), 0.35)
    P.line(0, hz, W, hz, (255, 160, 255), 0.7)
    cx, cy, S = W * 0.84, H * 0.36, min(W * 0.085, H * 0.16)
    a, b = t * 0.45, t * 0.31
    verts = []
    for i in range(16):
        v = [(1 if i >> k & 1 else -1) for k in range(4)]
        x, y, z, w = v
        x, w = x * math.cos(a) - w * math.sin(a), x * math.sin(a) + w * math.cos(a)        # rotate in XW
        y, z = y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)        # and YZ
        z, w = z * math.cos(a * 0.7) - w * math.sin(a * 0.7), z * math.sin(a * 0.7) + w * math.cos(a * 0.7)
        k4 = 2.2 / (3.2 - w)                                             # 4D -> 3D perspective
        x3, y3, z3 = x * k4, y * k4, z * k4
        k3 = 3.0 / (4.2 - z3)                                            # 3D -> 2D
        verts.append((cx + x3 * k3 * S * 1.6, cy + y3 * k3 * S, w))
    for i in range(16):
        for j in range(i + 1, 16):
            if bin(i ^ j).count("1") == 1:
                (x0, y0, w0), (x1, y1, w1) = verts[i], verts[j]
                f = clamp((w0 + w1) / 4 + 0.5, 0, 1)
                P.line(x0, y0, x1, y1, mix((150, 80, 255), (240, 240, 255), f), 0.55 + 0.4 * f)
    for x, y, w in verts:
        P.disc(x, y, 0.9, (255, 255, 255), 0.9, 2.5, (190, 140, 255))
    for i in range(30):                                                  # motes falling into it
        ang = i * 2.39 + t * 0.2
        rr = (S * 2.4) * (1 - ((t * 0.15 + i * 0.033) % 1))
        P.blend(cx + math.cos(ang) * rr * 1.6, cy + math.sin(ang) * rr, (220, 200, 255), 0.7)
    P.commit()


def _L_kaiju(self, screen, cols, rows, t):
    """KAIJU BAY: a storm over a harbour city. A colossal monster wades in the bay, the plates on its back flaring blue from
    tail to crown; every few seconds it rears back and breathes a beam of atomic fire over the city. Searchlights hunt it,
    lightning shows its whole outline."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    cyc = t % 9.0
    bolt = (int(t * 10) % 61) in (0, 1)
    for i in range(6):                                                   # storm clouds rolling
        cx = (i * W * 0.23 + t * 3) % (W * 1.3) - W * 0.15
        P.ellipse(cx, H * 0.08 + (i % 3) * 5, W * 0.17, 8, lambda u, v: ((52, 58, 78), 0.55 * (1 - v * v)))
    r = random.Random(9)
    x, gnd = 0, H * 0.74
    while x < W * 0.30:                                                  # the city on the left shore
        bw, bh = r.randint(5, 10), H * r.uniform(0.14, 0.36)
        P.poly([(x, gnd), (x + bw, gnd), (x + bw, gnd - bh), (x, gnd - bh)], (14, 16, 26), 1.0)
        for wy in range(int(gnd - bh) + 2, int(gnd), 3):
            for wx in range(x + 1, x + bw - 1, 2):
                if (wx * 7 + wy * 3) % 5 == 0:
                    P.blend(wx, wy, (255, 210, 120), 0.65)
        if r.random() < 0.5:
            P.blend(x + bw // 2, gnd - bh - 2, (255, 60, 60), 1.0 if int(t * 2 + x) % 2 else 0.3)
        x += bw + 1
    for k in range(2):                                                   # searchlights sweeping toward the monster
        bx, by = W * (0.08 + k * 0.14), gnd - 2
        ang = -math.pi / 2 + 0.55 + math.sin(t * 0.5 + k * 2) * 0.45
        for s in range(int(H * 0.8)):
            for dw in range(-int(s * 0.07), int(s * 0.07) + 1):
                P.blend(bx + math.cos(ang) * s - math.sin(ang) * dw, by + math.sin(ang) * s + math.cos(ang) * dw, (220, 230, 255), 0.08)
    sc = min(1.1, max(0.7, H / 80)) * 0.85
    kx, ky = W * 0.82, gnd + 2                                           # the monster, facing the city
    X = lambda dx: kx - dx * sc
    Y = lambda dy: ky - dy * sc
    rear = clamp((cyc - 5.2) / 0.8, 0, 1) * (1 - clamp((cyc - 8.0) / 0.8, 0, 1))
    body = [(X(-22), Y(0)), (X(-20), Y(22)), (X(-13), Y(36)), (X(-4), Y(44 + rear * 4)), (X(6), Y(48 + rear * 8)),
            (X(14), Y(46 + rear * 10)), (X(19), Y(40 + rear * 9)), (X(15), Y(35)), (X(10), Y(31)), (X(12), Y(23)),
            (X(22), Y(14)), (X(24), Y(0))]
    sil = (6, 8, 10) if not bolt else (2, 2, 4)
    P.poly(body, sil, 1.0)
    P.poly([(X(-20), Y(20)), (X(-34), Y(18)), (X(-40), Y(12)), (X(-24), Y(12))], sil, 1.0)    # tail sweeping behind
    P.poly([(X(10), Y(31)), (X(19), Y(27)), (X(21), Y(23)), (X(12), Y(25))], sil, 1.0)        # a clawed arm
    for i in range(len(body) - 1):                                       # rim light from the plates and the storm
        (x0, y0), (x1, y1) = body[i], body[i + 1]
        if y1 < Y(10) or y0 < Y(10):
            P.line(x0, y0, x1, y1, (90, 130, 180) if not bolt else (230, 240, 255), 0.55)
    charge = (t * 1.6) % 4.0
    for k in range(9):                                                   # dorsal plates, lit in a wave from tail to crown
        f = k / 8
        px_, py_ = X(-17 + f * 22), Y(21 + f * 25 + rear * 6 * f)
        lit = max(0.0, 1 - abs(charge - f * 3.2) * 1.5) + rear * 0.8
        h_ = (5 + 3 * math.sin(f * math.pi)) * sc
        P.poly([(px_ - 2 * sc, py_), (px_ + 2 * sc, py_), (px_ + 0.6 * sc, py_ - h_)], mix((50, 74, 100), (210, 244, 255), min(1, lit)), 1.0)
        if lit > 0.3:
            P.disc(px_, py_ - h_ * 0.5, 1.5, (120, 200, 255), 0.45 * lit, 5, (60, 140, 255))
    ex, ey = X(13), Y(42 + rear * 9)
    P.disc(ex, ey, 0.9, (255, 140, 70), 1.0, 2.5, (255, 70, 30))
    if 6.0 < cyc < 7.6:                                                  # ATOMIC BREATH over the city
        mx_, my_ = X(19), Y(40 + rear * 9)
        grow = clamp((cyc - 6.0) / 0.35, 0, 1)
        fade = 1 - clamp((cyc - 7.25) / 0.35, 0, 1)
        for s in range(int(W * 0.72 * grow)):
            y = my_ + s * 0.22 + math.sin(s * 0.3 + t * 30) * 0.6
            for dw in range(-3, 4):
                P.blend(mx_ - s, y + dw, mix((255, 255, 255), (80, 160, 255), abs(dw) / 3), (0.95 - abs(dw) * 0.22) * fade)
        P.disc(mx_, my_, 3, (255, 255, 255), 0.95 * fade, 7, (120, 190, 255))
        for y in range(int(H * 0.75)):                                   # the whole sky lit blue
            for x in range(0, W, 2):
                P.blend(x + (y % 2), y, (90, 150, 255), 0.06 * fade)
    for k in range(6):                                                   # ripples where it stands
        rx = (34 - k * 4 + (t * 4) % 4) * sc
        for j in range(48):
            a_ = j * math.pi / 47
            P.blend(kx + math.cos(a_) * rx, ky - 1 + math.sin(a_) * 1.2, (120, 150, 190), 0.25)
    for i in range(130):                                                 # driving rain
        x = (i * 29.3 - t * 30) % W
        y = (i * 71.9 + t * 80) % H
        P.blend(x, y, (170, 180, 210), 0.32)
        P.blend(x + 0.4, y - 1, (170, 180, 210), 0.2)
    if bolt:
        bx = W * (0.4 + 0.5 * ((int(t) * 37) % 10) / 10)
        y, x = 0.0, bx
        while y < H * 0.6:
            nx, ny = x + (((int(y) * 13 + int(t)) % 7) - 3), y + 4
            P.line(x, y, nx, ny, (240, 245, 255), 1.0)
            x, y = nx, ny
        for y in range(int(H * 0.75)):
            for x in range(0, W, 2):
                P.blend(x + (y % 2), y, (200, 210, 255), 0.18)
    P.commit()


def _L_shrooms(self, screen, cols, rows, t):
    """GLOWSHROOM GROVE: a forest of giant mushrooms whose caps glow and breathe, gills shining underneath, spores rising
    in slow spirals, fireflies and a drifting ground mist."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    shrooms = ((0.07, 0.78, 1.15, (150, 60, 230)), (0.24, 0.80, 0.7, (40, 200, 170)), (0.91, 0.80, 1.25, (60, 170, 255)),
               (0.74, 0.82, 0.65, (240, 80, 170)), (0.17, 0.84, 0.4, (120, 240, 130)), (0.99, 0.84, 0.55, (240, 80, 170)))
    for i, (xf, yf, s, col) in enumerate(shrooms):
        bx, by = W * xf, H * yf
        h_ = 34 * s
        sway = math.sin(t * 0.5 + i) * 1.5 * s
        for y in range(int(h_)):                                         # the stem, gently curved
            f = y / h_
            w_ = (2.2 + 1.2 * (1 - f)) * s
            cx_ = bx + sway * f * f
            for dx in range(-int(w_), int(w_) + 1):
                P.blend(cx_ + dx, by - y, mix((230, 220, 200), (140, 130, 120), abs(dx) / (w_ + 1)), 1.0)
        top = by - h_
        glow = 0.75 + 0.25 * math.sin(t * 1.3 + i * 1.7)
        rx, ry = 13 * s, 7 * s
        P.ellipse(bx + sway, top + ry * 0.2, rx * 1.6, ry * 1.8, lambda u, v, col=col: (col, 0.10 * glow * (1 - (u * u + v * v))))      # aura
        P.ellipse(bx + sway, top, rx, ry, lambda u, v, col=col: ((mix(col, (255, 255, 255), 0.35 * (1 - (u * u + v * v)) * glow), 1.0) if v <= 0.3 else None))
        for k in range(int(rx * 1.8)):                                   # gills
            gx = bx + sway - rx * 0.9 + k
            P.blend(gx, top + ry * 0.3 + 1, mix(col, (255, 255, 255), 0.5) if k % 2 else shade(col, 0.5), 0.9 * glow)
        for k in range(7):                                               # spots
            a_ = k * 2.4 + i
            sx = bx + sway + math.cos(a_) * rx * 0.6
            sy = top - ry * 0.45 + math.sin(a_ * 1.3) * ry * 0.3
            P.disc(sx, sy, 1.1 * s, (255, 250, 230), 0.8 * glow)
    for i in range(50):                                                  # rising spores
        ph = (t * 0.05 + i * 0.137) % 1.0
        x = W * ((i * 0.071) % 1) + math.sin(t + i) * 4
        y = H * (0.85 - ph * 0.8)
        P.blend(x, y, (190, 255, 220) if i % 2 else (230, 190, 255), 0.4 + 0.5 * math.sin(t * 3 + i))
    for k in range(3):                                                   # mist bands
        y0 = H * (0.66 + k * 0.05)
        for x in range(W):
            P.blend(x, y0 + math.sin(x * 0.05 + t * 0.4 + k) * 2, (150, 200, 210), 0.10)
            P.blend(x, y0 + 1 + math.sin(x * 0.05 + t * 0.4 + k) * 2, (150, 200, 210), 0.07)
    P.commit()


def _L_wormsea(self, screen, cols, rows, t):
    """THE DEEP DESERT: three moons over endless dunes. Every few seconds a colossal ringed sandworm breaches, arcs
    across the sky with sand pouring off its rings, opens its blazing maw, and dives back under."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    for mx_, my_, mr_, mc in ((0.18, 0.16, 7, (255, 236, 200)), (0.30, 0.10, 3.5, (220, 200, 255)), (0.86, 0.14, 5, (255, 190, 150))):
        P.disc(W * mx_, H * my_, mr_, mc, 1.0, mr_ * 1.2, mc)
    for layer, (base, col) in enumerate(((0.56, (160, 104, 74)), (0.64, (122, 76, 54)))):   # far dunes
        pts = [(0, H)] + [(x, H * base - 5 * math.sin(x * 0.04 + layer * 1.3 + t * 0.02) - 3 * math.sin(x * 0.11 + layer)) for x in range(0, W + 3, 3)] + [(W, H)]
        P.poly(pts, col, 1.0)
    cyc = (t % 12.0) / 12.0
    if 0.08 < cyc < 0.75:                                                # the breach
        p = (cyc - 0.08) / 0.67
        x0, x1 = W * 0.35, W * 0.95
        ground = H * 0.66
        hgt = H * 0.52
        n = 70
        pts = []
        for k in range(n):
            f = k / (n - 1)
            u = clamp(p * 1.6 - (1 - f) * 0.9, 0, 1)                  # the head leads, the body follows out of the sand
            if u <= 0:
                continue
            x = x0 + (x1 - x0) * u
            y = ground - math.sin(u * math.pi) * hgt
            pts.append((x, y, f))
        for x, y, f in pts:                                              # body: thick ringed segments
            w_ = 5.5 + 2.5 * f
            ring = math.sin(f * 50 - t * 4)
            for dy in range(-int(w_), int(w_) + 1):
                sh = 0.55 + 0.45 * (1 - abs(dy) / (w_ + 1))
                c = mix((110, 72, 40), (222, 180, 110), (0.5 + 0.5 * ring) * sh)
                P.blend(x, y + dy, c, 1.0)
            if (int(f * 70) % 3) == 0:                                   # sand pouring off the rings
                for s in range(1, 10):
                    P.blend(x + math.sin(s + t * 3) * 0.7, y + w_ + s * 1.4, (226, 196, 140), 0.5 * (1 - s / 10))
        if pts:
            hx, hy, _ = pts[-1]
            P.disc(hx, hy, 7.5, (90, 50, 30), 1.0)
            P.disc(hx, hy, 5.5, (255, 130, 50), 1.0, 4, (255, 90, 30))   # the blazing maw
            P.disc(hx, hy, 2.5, (255, 230, 170), 1.0)
            for k in range(12):
                a_ = k * math.tau / 12 + t
                P.line(hx + math.cos(a_) * 5.5, hy + math.sin(a_) * 5.5, hx + math.cos(a_) * 7.8, hy + math.sin(a_) * 7.8, (250, 240, 220), 0.9)
        for k in range(30):                                              # sand fountains where it breaks the surface
            for xx in (x0, x0 + (x1 - x0) * clamp(p * 1.6, 0, 1)):
                P.blend(xx + math.sin(k * 7.1) * 6, ground - (k * 1.7 + t * 9) % 20, (230, 200, 150), 0.4)
    for i in range(80):                                                  # blowing sand
        x = (i * 43.3 + t * 26) % W
        y = H * 0.4 + (i * 17.9) % (H * 0.4) + math.sin(t + i) * 2
        P.blend(x, y, (240, 210, 160), 0.35)
        P.blend(x - 1, y, (240, 210, 160), 0.2)
    P.commit()


def _L_jadetemple(self, screen, cols, rows, t):
    """JADE TEMPLE: a stepped pyramid on the right, a blazing carved sun-disc on the left, jungle crowns on both flanks,
    and a feathered serpent coiling round and round the pyramid - in front of it, then behind it."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    sx, sy, sr = W * 0.14, H * 0.27, min(W * 0.08, H * 0.13)
    for k in range(24):                                                  # sun rays
        a_ = k * math.tau / 24 + t * 0.05
        P.line(sx + math.cos(a_) * sr * 1.25, sy + math.sin(a_) * sr * 1.25, sx + math.cos(a_) * sr * 2.4, sy + math.sin(a_) * sr * 2.4,
               (255, 214, 120), 0.3 if k % 2 else 0.14)
    P.disc(sx, sy, sr, (255, 220, 120), 1.0, sr * 0.8, (255, 180, 80))
    P.disc(sx, sy, sr * 0.62, (240, 170, 70), 0.6)
    for k in range(8):                                                   # carved glyph ring on the sun
        a_ = k * math.tau / 8 + t * 0.1
        P.disc(sx + math.cos(a_) * sr * 0.8, sy + math.sin(a_) * sr * 0.8, 1.0, (170, 100, 40), 0.9)
    P.disc(sx, sy, sr * 0.25, (255, 240, 200), 0.9)
    base, px = H * 0.74, W * 0.84                                        # the pyramid
    tiers, tw, th_ = 7, min(W * 0.14, H * 0.24), max(3.0, H * 0.055)
    serp = []
    n = 90
    for k in range(n):                                                   # the serpent's coil: an ellipse around the pyramid
        f = k / (n - 1)
        u = t * 0.55 - f * 2.6
        r_ = tw * 1.45
        x = px + math.cos(u) * r_
        y = base - tiers * th_ * 0.62 + math.sin(u) * r_ * 0.22 - f * 3 + math.sin(k * 0.35 - t * 3) * 1.4
        serp.append((x, y, f, math.sin(u) >= 0))
    def draw_serpent(front: bool) -> None:
        for k, (x, y, f, fr) in enumerate(serp):
            if fr != front:
                continue
            w_ = 3.2 * (1 - f * 0.65)
            for dy in range(-int(w_), int(w_) + 1):
                c = (250, 214, 120) if (k + dy) % 5 == 0 else mix((20, 140, 90), (110, 230, 160), 0.5 + 0.5 * math.sin(k * 0.7 + dy))
                P.blend(x, y + dy, c if front else shade(c, 0.6), 1.0)
            if k % 4 == 0 and 4 < k < n - 3:
                P.line(x, y - w_, x + 1.5, y - w_ - 3.5, hsv(0.38 + 0.08 * math.sin(k), 0.8, 0.9 if front else 0.55), 0.85)
            if k == 0:
                P.disc(x, y, 3.2, (40, 170, 110), 1.0)
                P.blend(x - 1.5, y - 1, (255, 60, 40), 1.0)
                for s in range(6):                                       # quetzal crest
                    P.line(x + 1, y - 3, x + 2 + s, y - 8 - s * 0.6, hsv(0.36 + s * 0.02, 0.85, 0.95), 0.9)
            if k == n - 1:
                for s in range(5):                                       # tail plumes
                    P.line(x, y, x + 9, y - 6 + s * 3 + math.sin(t * 3 + s) * 2, (230, 60, 50) if s % 2 else (60, 220, 150), 0.85)
    draw_serpent(False)
    for k in range(tiers):
        w_, y_ = tw - k * tw / (tiers + 1.5), base - k * th_
        P.poly([(px - w_, y_), (px + w_, y_), (px + w_ - 2, y_ - th_), (px - w_ + 2, y_ - th_)], mix((58, 88, 66), (116, 146, 104), k / tiers), 1.0)
        P.line(px - w_ + 2, y_ - th_, px + w_ - 2, y_ - th_, (160, 190, 140), 0.85)
        P.line(px - w_, y_ - 1, px + w_, y_ - 1, (40, 60, 46), 0.6)
    top = base - tiers * th_
    P.poly([(px - 3, base), (px + 3, base), (px + 2, top), (px - 2, top)], (150, 130, 96), 1.0)        # stairs
    for y in range(int(top), int(base), 2):
        P.line(px - 2.5, y, px + 2.5, y, (96, 80, 62), 0.8)
    P.poly([(px - 5, top), (px + 5, top), (px + 5, top - 7), (px - 5, top - 7)], (74, 104, 84), 1.0)   # the temple
    P.poly([(px - 6, top - 7), (px + 6, top - 7), (px, top - 11)], (96, 130, 100), 1.0)
    P.poly([(px - 1.5, top), (px + 1.5, top), (px + 1.5, top - 4), (px - 1.5, top - 4)], (16, 20, 16), 1.0)
    fl = 0.7 + 0.3 * math.sin(t * 8)
    P.disc(px, top - 2, 0.8, (255, 180, 80), fl, 3, (255, 130, 40))
    draw_serpent(True)
    for side, x0 in ((0, 0.0), (1, W * 0.66)):                          # jungle crowns with sunlit tops
        for i in range(12):
            cx = x0 + (i * W * 0.03) if side else (i * W * 0.028)
            if side and cx > W * 0.73 and cx < W * 0.95:
                continue
            cy = H * (0.66 + 0.04 * math.sin(i * 1.7 + side))
            rx_, ry_ = 7 + (i * 5) % 4, 5 + (i * 3) % 3
            P.ellipse(cx, cy, rx_, ry_, lambda u, v, i=i: (mix((18, 60, 36), (70, 150, 80), clamp(-v * 0.8 + 0.2 + 0.15 * math.sin(u * 9 + i), 0, 1)), 1.0))
    for i in range(24):                                                  # drifting mist and tiny birds
        x = (i * 47.7 + t * 3) % W
        y = H * 0.55 + (i * 13.3) % (H * 0.15)
        P.blend(x, y, (230, 220, 200), 0.18)
    for b in range(3):
        bx = (t * (6 + b) + b * 40) % (W + 20) - 10
        by = H * (0.12 + b * 0.05) + math.sin(t * 2 + b) * 2
        wing = 1 if int(t * 6 + b) % 2 else -1
        P.blend(bx, by, (30, 30, 40), 1.0)
        P.blend(bx - 1, by + wing * 0.6, (30, 30, 40), 0.8)
        P.blend(bx + 1, by + wing * 0.6, (30, 30, 40), 0.8)
    P.commit()


def _L_orrery(self, screen, cols, rows, t):
    """THE ORRERY: a brass astrolabe filling the right of the sky. Tilted rings turn at their own speeds carrying their
    planets, the sun burns at its heart, and the twelve constellations of the zodiac glitter behind it, drawn in gold."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    r = random.Random(12)
    for c in range(12):                                                  # constellations, kept to the left half and the top
        cx = W * (0.04 + (c % 4) * 0.08) if c < 8 else W * (0.30 + (c - 8) * 0.12)
        cy = H * (0.20 + (c // 4) * 0.20) if c < 8 else H * 0.06
        pts = [(cx + r.uniform(-7, 7), cy + r.uniform(-5, 5)) for _ in range(r.randint(4, 6))]
        for i in range(len(pts) - 1):
            P.line(*pts[i], *pts[i + 1], (200, 160, 80), 0.22)
        for i, (x, y) in enumerate(pts):
            P.blend(x, y, (255, 250, 220), 0.5 + 0.5 * math.sin(t * 2 + c + i))
    cx, cy = W * 0.84, H * 0.36
    k_ = min(W * 0.15 / 60.0, H * 0.30 / 40.0)
    rings = ((14, 0.9, 0.35, (230, 180, 90), (150, 200, 255)), (22, -0.55, 0.30, (210, 160, 70), (255, 150, 100)),
             (31, 0.32, 0.26, (190, 140, 60), (200, 255, 210)), (40, -0.2, 0.22, (170, 120, 50), (255, 220, 160)))
    for i in range(3):                                                   # meridian arcs (the astrolabe's frame), turning slowly
        R = (44 + i * 2) * k_
        for k in range(160):
            a_ = math.tau * k / 159
            P.blend(cx + math.cos(a_) * R * 1.5 * math.cos(t * 0.15 + i * 1.1), cy + math.sin(a_) * R, (200, 150, 60), 0.28)
    for R0, spd, tilt, brass, planet in rings:
        R = R0 * k_
        n = int(R * 9) + 12
        for k in range(n):
            a_ = k * math.tau / n
            x, y = cx + math.cos(a_) * R * 1.5, cy + math.sin(a_) * R * tilt * 1.4
            P.blend(x, y, brass, 0.9 if math.sin(a_) > 0 else 0.45)
            if k % max(1, n // 12) == 0:
                P.blend(x, y - 1, (255, 230, 150), 0.75)                 # tick marks
    P.disc(cx, cy, 5 * k_ + 1, (255, 220, 120), 1.0, 6 * k_ + 1, (255, 170, 60))   # the sun
    for k in range(8):
        a_ = k * math.tau / 8 + t * 0.4
        P.line(cx + math.cos(a_) * (6 * k_ + 1.5), cy + math.sin(a_) * (6 * k_ + 1.5), cx + math.cos(a_) * (9 * k_ + 2), cy + math.sin(a_) * (9 * k_ + 2), (255, 200, 90), 0.6)
    for R0, spd, tilt, brass, planet in rings:                           # planets on brass arms
        R = R0 * k_
        a_ = t * spd + R0
        x, y = cx + math.cos(a_) * R * 1.5, cy + math.sin(a_) * R * tilt * 1.4
        P.line(cx, cy, x, y, (150, 110, 50), 0.4)
        P.disc(x, y, 1.2 + R0 * 0.035, planet, 1.0, 2.2, planet)
    cm = (t * 0.07) % 1.0                                                # a comet crossing the top
    hx, hy = W * (1.1 - cm * 1.3), H * (0.03 + cm * 0.12)
    for s in range(30):
        P.blend(hx + s * 1.4, hy - s * 0.2, (200, 230, 255), 0.8 * (1 - s / 30))
    P.disc(hx, hy, 1.2, (255, 255, 255), 1.0, 2.5, (160, 210, 255))
    P.commit()


def _L_armada(self, screen, cols, rows, t):
    """GHOST ARMADA: a sea of moonlit cloud, a green moon, and a fleet of spectral galleons ghosting through the fog with
    tattered glowing sails, swinging lanterns and a wake of green light."""
    P = _Px(screen, cols, rows)
    W, H = P.W, P.H
    P.disc(W * 0.86, H * 0.2, min(W * 0.09, H * 0.14), (196, 255, 216), 1.0, min(W * 0.09, H * 0.14), (90, 220, 150))
    for k in range(4):                                                   # cloud sea bands drifting
        y0 = H * (0.54 + k * 0.06)
        for x in range(W):
            hgt = 3 + 2.5 * math.sin(x * 0.07 + t * (0.3 + k * 0.1) + k * 2) + 1.5 * math.sin(x * 0.19 - t * 0.2)
            for dy in range(int(hgt) + 6):
                P.blend(x, y0 - hgt + dy, mix((160, 200, 190), (60, 90, 96), k / 3), 0.6 if dy < 2 else 0.32)
    sc = min(1.3, max(0.7, H / 80))
    ships = ((0.07, 0.36, 0.42, 0.010), (0.80, 0.44, 0.62, 0.006), (0.16, 0.54, 1.0, 0.004))
    for i, (xf, yf, s, spd) in enumerate(ships):
        s *= sc
        x = ((xf + t * spd) % 1.25 - 0.1) * W
        if W * 0.30 < x < W * 0.70 and s > 0.9:
            x = W * 0.16 + (x - W * 0.3) * 0.1                           # the flagship keeps clear of the menu
        y = H * yf + math.sin(t * 0.9 + i) * 1.5
        L_, hh = 30 * s, 6 * s
        hull = [(x - L_ * 0.5, y - hh), (x - L_ * 0.38, y - hh * 1.6), (x + L_ * 0.5, y - hh * 1.4), (x + L_ * 0.62, y - hh * 0.6), (x + L_ * 0.4, y), (x - L_ * 0.36, y)]
        P.poly(hull, (20, 36, 38), 0.95)
        for a_, b_ in zip(hull, hull[1:] + hull[:1]):
            P.line(*a_, *b_, (110, 255, 170), 0.45)
        for k in range(5):                                               # glowing gunports
            P.disc(x - L_ * 0.28 + k * L_ * 0.15, y - hh * 0.5, 0.6, (160, 255, 190), 0.95)
        for m, mh in ((-0.24, 0.9), (0.06, 1.2), (0.33, 0.85)):         # masts and tattered sails
            mx_ = x + m * L_
            mtop = y - hh - 26 * s * mh
            P.line(mx_, y - hh, mx_, mtop, (60, 84, 80), 1.0)
            for row in range(3):
                sy0 = mtop + 2 * s + row * 8 * s * mh
                sw = (6.5 - row * 1.2) * s
                sh = 6.5 * s * mh
                belly = (1.4 + 0.8 * math.sin(t * 1.5 + m * 5 + row)) * s
                quad = [(mx_ - sw, sy0), (mx_ + sw, sy0), (mx_ + sw * 0.9 + belly, sy0 + sh), (mx_ - sw * 0.9 + belly, sy0 + sh)]
                P.poly(quad, (170, 255, 210), 0.22)
                P.line(*quad[0], *quad[1], (200, 255, 225), 0.6)
                P.line(*quad[3], *quad[2], (150, 240, 200), 0.45)
                for h_ in range(2):                                      # rips in the canvas
                    hx = mx_ + ((i * 7 + row * 3 + h_ * 5) % 9 - 4) * sw / 5
                    hy = sy0 + sh * (0.35 + 0.3 * h_)
                    P.disc(hx + belly * 0.5, hy, 0.9 * s, (16, 30, 32), 0.75)
        P.line(x + L_ * 0.5, y - hh * 1.4, x + L_ * 0.9, y - hh * 2.4, (60, 84, 80), 0.9)     # bowsprit
        lx = x - L_ * 0.42 + math.sin(t * 2 + i) * 0.8                   # swinging stern lantern
        P.disc(lx, y - hh * 2.0, 0.9, (220, 255, 220), 1.0, 3.5, (90, 255, 150))
        for k in range(int(34 * s)):                                     # the wake of green light
            P.blend(x - L_ * 0.4 - k * 1.2, y + 0.5 + math.sin(k * 0.4 + t * 3) * 0.6, (100, 255, 160), 0.45 * (1 - k / (34 * s)))
    for i in range(24):                                                  # fog wisps and ghost lights
        x = (i * 53.7 + t * 5) % W
        y = H * 0.3 + (i * 19.3) % (H * 0.3)
        P.blend(x, y, (170, 255, 200), 0.3 + 0.3 * math.sin(t * 2 + i))
    P.commit()


LAYER_DRAWERS = {"twinsuns": _L_twinsuns, "lanterns": _L_lanterns, "worldtree": _L_worldtree, "whale": _L_whale, "shards": _L_shards, "sanctum": _L_sanctum, "moon": _L_moon, "sun": _L_sun, "city": _L_city, "mountains": _L_mountains, "grid": _L_grid, "ocean": _L_ocean,
                 "planet": _L_planet, "pyramids": _L_pyramids, "trees": _L_trees, "rain": _L_rain, "lightning": _L_lightning,
                 "tower": _L_tower, "comet": _L_comet, "glitch": _L_glitch, "volcano": _L_volcano, "isles": _L_isles,
                 "riftring": _L_riftring, "hourglass": _L_hourglass, "sunburst": _L_sunburst, "arcane": _L_arcane,
                 "abyss": _L_abyss, "shrine": _L_shrine, "holocity": _L_holocity, "hyper": _L_hyper, "kaiju": _L_kaiju,
                 "shrooms": _L_shrooms, "wormsea": _L_wormsea, "jadetemple": _L_jadetemple, "orrery": _L_orrery, "armada": _L_armada}
