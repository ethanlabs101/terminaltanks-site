"""Boss portraits: the Terminal Ticket in the shop, the Martyr's Arcane Time Machine and the Martyr himself."""
from __future__ import annotations

import math
import random

from tanks.art.tanks import draw_tank
from tanks.colors import mix
from tanks.content.martyr import ELEMENTS
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.content.tickets import TICKET_BOSS_BY_KEY
from tanks.save import SaveData
from tanks.screen import PixelCanvas


def ticket_art(save: "SaveData", t: float) -> PixelCanvas:
    """The shop preview for the Terminal Ticket: a mystery ticket, or the drawn boss once one is active."""
    cv = PixelCanvas(34, 20, (0, 0, 0))
    for py in range(20):
        cv.rows[py] = [mix((10, 6, 28), (60, 20, 80), py / 19)] * 34
    boss = TICKET_BOSS_BY_KEY.get(save.ticket_active)
    if boss:
        for x in range(34):
            for y in range(3):
                cv.plot(x, y, (40, 36, 60))
        draw_tank(cv, 17.0, 3, -1, 130, DESIGN_BY_KEY[boss.tank].accent, scale=2, design=DESIGN_BY_KEY[boss.tank], t=t)
        return cv
    for x in range(5, 29):                                   # a ticket with a notch on each side and a question mark
        for y in range(5, 15):
            if not ((x in (5, 28)) and y in (9, 10)):
                cv.plot(x, y, mix((230, 190, 90), (255, 240, 170), 0.5 + 0.5 * math.sin(t * 2 + x * 0.3)))
    for y in range(6, 14):
        cv.plot(8, y, (150, 110, 40))
    for (x, y) in ((16, 12), (17, 12), (18, 12), (18, 11), (18, 10), (17, 9), (16, 9), (16, 8), (17, 8), (18, 8)):
        pass
    for (x, y) in ((15, 11), (16, 12), (17, 12), (18, 11), (18, 10), (17, 9), (17, 8), (17, 6)):
        cv.plot(x + 4, y, (90, 40, 120))
    cv.plot(21, 6, (90, 40, 120))
    return cv


def draw_artifact(cv: PixelCanvas, cx: float, cy: float, s: float, t: float) -> None:
    """The Time Machine: a glowing hourglass wrapped in two turning rings of runes."""
    H, Wd = max(8, int(14 * s)), max(5, int(8 * s))
    for k in range(H):
        f = abs(H / 2 - k - 0.5) / (H / 2)
        hw = int(1 + f * Wd / 2)
        y = int(cy - H / 2 + k)
        for dx in range(-hw, hw + 1):
            edge = abs(dx) >= hw or k in (0, H - 1)
            col = (255, 226, 150) if edge else mix((60, 40, 110), (150, 110, 230), 0.5 + 0.5 * math.sin(t * 2 + k * 0.4))
            cv.blend(int(cx) + dx, y, col, 0.95 if edge else 0.55)
    top = int(cy - H / 2)
    for k in range(H // 2 - 2, H // 2 + 3):
        cv.plot(int(cx), top + k, (255, 236, 180))
    for k in range(int(H * 0.22)):
        for dx in range(-(k // 2), k // 2 + 1):
            cv.blend(int(cx) + dx, top + 1 + (H // 2 - 1 - k), (255, 210, 120), 0.6)
    for rx, ry, sp in ((Wd * 1.4, Wd * 0.5, 0.8), (Wd * 1.1, Wd * 0.42, -1.2)):
        for i in range(70):
            ang = i / 70 * math.tau + t * sp
            cv.blendf(cx + math.cos(ang) * rx, cy + math.sin(ang) * ry * (1.4 if sp < 0 else 1.0) + math.sin(ang * 3 + t) * 0.5,
                      (255, 226, 150) if i % 2 else (170, 120, 255), 0.55 + 0.35 * math.sin(ang * 5 + t * 3))


def _mage_sprite() -> list:
    """A 24x32 cell sprite built from shapes: pointed hood, shadowed face, long beard, gold-trimmed robe, staff."""
    g = [["."] * 24 for _ in range(32)]
    def put(x, y, c):
        if 0 <= x < 24 and 0 <= y < 32:
            g[y][x] = c
    for y in range(13, 32):                                          # robe, flaring toward the hem
        w = 4 + int((y - 13) * 0.33)
        for x in range(12 - w, 12 + w + 1):
            edge = x in (12 - w, 12 + w)
            put(x, y, "G" if edge else "L" if (x - 12) % 5 == 0 else "M" if abs(x - 12) < w - 1 else "D")
    for x in range(5, 20):                                            # shoulders and belt
        put(x, 13, "H"), put(x, 14, "D")
    for x in range(8, 17):
        put(x, 19, "G")
    for k in range(5):                                                # right arm reaching for the staff
        put(15 + k, 16 - (k // 2), "M"), put(15 + k, 17 - (k // 2), "D")
    put(20, 15, "g"), put(19, 15, "g")
    for y in range(4, 32):                                            # staff with gold rings
        put(20, y, "g" if (y - 4) % 7 == 0 else "S")
    for y in range(1, 14):                                            # pointed hood
        w = 1 + int((y - 1) * 0.5)
        for x in range(12 - w, 12 + w + 1):
            put(x, y, "H" if x in (12 - w, 12 + w) else "D")
    for y in range(7, 13):                                            # the face in shadow
        w = 2 if y < 11 else 1
        for x in range(12 - w, 12 + w + 1):
            put(x, y, "F")
    put(11, 9, "E"), put(13, 9, "E")
    for y in range(11, 22):                                           # a long white beard
        w = max(0, 3 - (y - 11) // 3)
        for x in range(12 - w, 12 + w + 1):
            put(x, y, "B")
    for (x, y) in ((8, 24), (15, 26), (10, 28), (13, 22), (7, 20), (16, 30)):
        put(x, y, "g")
    return g


_MAGE = _mage_sprite()


def draw_mage(cv: PixelCanvas, cx: float, by: float, s: float, t: float, alpha: float = 1.0, aura: bool = True) -> None:
    """The Martyr: a hooded archmage with a glowing-eyed hood, long beard, gold-trimmed robes and a staff whose orb cycles through
    his six elements, surrounded by orbiting element sparks. s = pixels per sprite cell."""
    bob = math.sin(t * 1.5) * 0.8 * s
    sz = max(1, int(math.ceil(s)))
    pal = {"D": (30, 14, 66), "M": (66, 34, 130), "L": (112, 70, 204), "H": (50, 24, 100), "G": (232, 180, 70), "g": (255, 240, 170),
           "F": (6, 2, 16), "E": (255, 250, 214), "B": (226, 226, 246), "S": (140, 96, 52)}
    for row in range(32):
        for col in range(24):
            ch = _MAGE[row][col]
            if ch == ".":
                continue
            c = pal[ch]
            if ch in "ML":                                              # shimmering robe
                c = mix(c, (150, 100, 240), 0.25 + 0.25 * math.sin(t * 2 + col * 0.6 + row * 0.35))
            elif ch == "E":
                c = mix(c, (255, 255, 255), 0.5 + 0.5 * math.sin(t * 6))
            elif ch == "B":
                c = mix(c, (190, 190, 230), 0.3 + 0.3 * math.sin(t * 1.3 + row))
            sway = math.sin(t * 2 + row * 0.25) * 0.5 * (row / 32) * s if row > 18 else 0.0
            px = cx + (col - 12) * s + sway
            py = by + bob + (31 - row) * s
            for ox in range(sz):
                for oy in range(sz):
                    cv.blend(int(px) + ox, int(py) + oy, c, alpha)
    ox_, oy_ = cx + 8 * s, by + bob + 30 * s                           # the orb at the top of the staff
    orb = ELEMENTS[list(ELEMENTS)[int(t * 0.8) % 6]][4]
    r = max(2.0, 2.6 * s)
    for dx in range(-int(r) - 1, int(r) + 2):
        for dy in range(-int(r) - 1, int(r) + 2):
            d = math.hypot(dx, dy)
            if d <= r:
                cv.blend(int(ox_) + dx, int(oy_) + dy, mix(orb, (255, 255, 255), 0.6 * (1 - d / r)), alpha * 0.95)
            elif d <= r + 1.5:
                cv.blend(int(ox_) + dx, int(oy_) + dy, orb, alpha * 0.3)
    if aura:
        for i, el in enumerate(ELEMENTS):
            ang = t * 1.1 + i * math.tau / 6
            ex, ey = cx + math.cos(ang) * 14 * s, by + 16 * s + math.sin(ang) * 7 * s
            col = ELEMENTS[el][4]
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                cv.blendf(ex + dx, ey + dy, col, alpha * (0.95 if dx == 0 and dy == 0 else 0.5))


def martyr_art(save: "SaveData", t: float) -> PixelCanvas:
    cv = PixelCanvas(34, 20, (0, 0, 0))
    for py in range(20):
        cv.rows[py] = [mix((6, 2, 20), (70, 30, 110), py / 19)] * 34
    rng = random.Random(7)
    for _ in range(16):
        cv.blendf(rng.uniform(0, 33), rng.uniform(4, 19), (255, 255, 255), 0.4 + 0.4 * math.sin(t * 3 + rng.uniform(0, 6)))
    draw_artifact(cv, 17, 10, 0.95, t)
    if save.martyr_available() and not save.martyr_won:
        draw_mage(cv, 17, 2, 0.5, t, 0.35 + 0.25 * math.sin(t * 2), False)
    return cv
