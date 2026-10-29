"""Home-screen backdrops: the ambient menu backdrop, the MASTER citadel, the SECRET screen and ThemeBackdrop (any
HomeTheme), with their logos and menus."""
from __future__ import annotations

import math
import random
from typing import Optional

from tanks.art.barrels import muzzle_point, visual_lift
from tanks.art.home_layers import LAYER_DRAWERS
from tanks.art.projectiles import draw_projectile
from tanks.art.scenery import MOTE_STYLES
from tanks.art.tanks import draw_tank
from tanks.battle.effects import EffectsFactory, Explosion, Particle, ParticleSystem
from tanks.battle.physics import Launch
from tanks.colors import GOLD, Palette, RGB, clamp, gradient, hsv, lerp, mix, shade
from tanks.content.ammo import AMMO_BY_KEY
from tanks.content.homes import HomeTheme
from tanks.content.paints import COLOR_CHOICES
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.screen import PixelCanvas, Screen
from tanks.settings import Settings
from tanks.ui.widgets import MenuList, big_word


class AmbientBackdrop:
    def __init__(self, seed: int = 11) -> None:
        self.rng = random.Random(seed)
        self.ps = ParticleSystem(1600)
        self.explosions: list[Explosion] = []
        self.shells: list[dict] = []
        self.size = (0, 0)
        self.layer: Optional[PixelCanvas] = None
        self.ridge: list[int] = []
        self.stars: list = []
        self.spawn_timer = 1.0
        self.celebrate: Optional[list] = None
        self.fw_timer = 0.0

    def ensure(self, cols: int, rows: int) -> None:
        if self.size == (cols, rows):
            return
        self.size = (cols, rows)
        w, h = cols, rows * 2
        r = self.rng
        ph = [r.uniform(0, math.tau) for _ in range(6)]
        self.ridge = [int(h * (0.22 + 0.06 * math.sin(x / w * math.tau * 2 + ph[0]) + 0.04 * math.sin(x / w * math.tau * 6 + ph[1])
                               + 0.015 * math.sin(x / w * math.tau * 19 + ph[2]))) for x in range(w)]
        far = [int(h * (0.34 + 0.08 * math.sin(x / w * math.tau * 3 + ph[3]) + 0.04 * math.sin(x / w * math.tau * 9 + ph[4]))) for x in range(w)]
        rows_px = []
        for py in range(h):
            y = h - 1 - py
            base = gradient(((0, (4, 8, 20)), (0.55, (8, 26, 44)), (0.85, (16, 70, 84)), (1, (30, 110, 120))),
                            1 - y / h) if False else gradient(((0, (30, 110, 120)), (0.25, (16, 62, 78)), (0.6, (8, 24, 42)), (1, (4, 8, 20))), y / h)
            row = []
            for x in range(w):
                c = base
                if y < self.ridge[x]:
                    c = mix((10, 26, 34), (4, 12, 18), 1 - y / max(1, self.ridge[x]))
                elif y < far[x]:
                    c = mix(base, (20, 48, 62), 0.75)
                vx, vy = (x / w - 0.5) * 2, (py / h - 0.5) * 2
                c = shade(c, max(0.25, 1 - 0.42 * (vx * vx + vy * vy) * 0.8))
                if (py // 2) % 2:
                    c = shade(c, 0.9)
                row.append(c)
            rows_px.append(row)
        self.layer = PixelCanvas(w, h, rows=rows_px)
        self.stars = [(r.randrange(w), r.randrange(int(h * 0.6)), r.uniform(0, 6), r.uniform(1, 3)) for _ in range(w // 3)]

    def _spawn_shell(self) -> None:
        r, w = self.rng, self.size[0]
        left = r.random() < 0.5
        x0 = r.uniform(0.05, 0.3) * w if left else r.uniform(0.7, 0.95) * w
        tx = r.uniform(0.3, 0.7) * w
        th = math.radians(r.uniform(48, 68))
        y0 = self.ridge[int(x0)] + 2
        hh = self.layer.h if self.layer is not None else 56
        tmax = 4 * (hh - 9 - y0) / max(4.0, abs(tx - x0))              # apex = range*tan(angle)/4 must stay inside the canvas
        if math.tan(th) > tmax:
            th = math.atan(max(0.45, tmax))
        v = math.sqrt(32 * abs(tx - x0) / math.sin(2 * th))
        self.shells.append({"l": Launch(x0, y0, math.copysign(v * math.cos(th), tx - x0), v * math.sin(th), 32),
                            "t": 0.0, "c": r.choice(COLOR_CHOICES)[1]})

    def celebrate_with(self, colors: Optional[list]) -> None:
        self.celebrate = colors

    def update(self, dt: float) -> None:
        if self.layer is None:
            return
        self.ps.update(dt)
        for e in self.explosions:
            e.update(dt)
        self.explosions = [e for e in self.explosions if not e.done]
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.shells) < 3 and not self.celebrate:
            self.spawn_timer = self.rng.uniform(1.0, 2.8)
            self._spawn_shell()
        for s in self.shells[:]:
            s["t"] += dt
            x, y = s["l"].at(s["t"])
            self.ps.emit(Particle(x, y, 0, 0, 0.6, 0.6, mix(Palette.WHITE, s["c"], 0.5), shade(s["c"], 0.15), alpha=0.9))
            if x < 0 or x >= self.size[0] or y < self.ridge[int(x)]:
                self.shells.remove(s)
                if 0 <= x < self.size[0]:
                    self.explosions.append(Explosion(x, y, 3.5, s["c"], 0.7))
                    for _ in range(18):
                        a, sp = self.rng.uniform(0.2, 2.9), self.rng.uniform(10, 34)
                        self.ps.emit(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, 0.8, 0.8, Palette.WHITE, shade(s["c"], 0.2), gravity=60))
        if self.celebrate:
            self.fw_timer -= dt
            if self.fw_timer <= 0:
                self.fw_timer = self.rng.uniform(0.25, 0.6)
                bx, by = self.rng.uniform(0.15, 0.85) * self.size[0], self.rng.uniform(0.45, 0.85) * self.size[1] * 2
                col = self.rng.choice(self.celebrate)
                for _ in range(60):
                    a, sp = self.rng.uniform(0, math.tau), self.rng.uniform(8, 34)
                    life = self.rng.uniform(0.9, 1.6)
                    self.ps.emit(Particle(bx, by, math.cos(a) * sp, math.sin(a) * sp, life, life, mix(Palette.WHITE, col, 0.5),
                                          shade(col, 0.2), gravity=26, drag=1.1))

    def draw(self, screen: Screen, t: float) -> None:
        self.ensure(screen.cols, screen.rows)
        canvas = self.layer.copy()
        for x, py, ph, sp in self.stars:
            canvas.rows[py][x] = mix(canvas.rows[py][x], (220, 240, 255), 0.25 + 0.5 * math.sin(t * sp + ph) ** 2)
        self.ps.draw(canvas)
        for e in self.explosions:
            e.draw(canvas)
        for s in self.shells:
            x, y = s["l"].at(s["t"])
            canvas.plotf(x, y, Palette.WHITE)
        screen.blit(canvas, 0, 0)


class MasterBackdrop:
    """Same interface as AmbientBackdrop, but a far richer scene."""

    def __init__(self, settings: Settings, seed: int = 21) -> None:
        self.rng = random.Random(seed)
        self.settings = settings
        self.ps = ParticleSystem(2600)
        self.fx = EffectsFactory(self.ps, settings, self.rng)
        self.explosions: list[Explosion] = []
        self.shells: list[dict] = []
        self.size = (0, 0)
        self.layer: Optional[PixelCanvas] = None
        self.ridge: list[int] = []
        self.stars: list = []
        self.beacons: list = []
        self.shooting: list[list] = []
        self.timer = 1.5
        self.fire_timer = 2.0
        self.clock = 0.0
        self.celebrate: Optional[list] = None
        self.fw_timer = 0.0
        self.hero_x = 0.0
        self.hero_angle = 40.0
        self.hero_target = 40.0
        self.recoil = 0.0
        self.pending: Optional[tuple] = None
        self.n = 0

    def celebrate_with(self, colors: Optional[list]) -> None:
        self.celebrate = colors

    def ensure(self, cols: int, rows: int) -> None:
        if self.size == (cols, rows):
            return
        self.size = (cols, rows)
        w, h = cols, rows * 2
        r = self.rng
        sky = ((0, (255, 166, 96)), (0.16, (214, 78, 124)), (0.42, (74, 26, 116)), (1, (5, 3, 24)))
        ph = [r.uniform(0, math.tau) for _ in range(6)]
        far = [int(h * (0.30 + 0.07 * math.sin(x / w * math.tau * 3 + ph[0]) + 0.04 * math.sin(x / w * math.tau * 9 + ph[1]))) for x in range(w)]
        ground = [int(h * (0.15 + 0.03 * math.sin(x / w * math.tau * 2.4 + ph[2]) + 0.015 * math.sin(x / w * math.tau * 13 + ph[3]))) for x in range(w)]
        self.hero_x = w * 0.13
        hx = int(self.hero_x)
        plat = ground[hx]
        for x in range(max(0, hx - 10), min(w, hx + 11)):
            ground[x] = int(lerp(ground[x], plat + 2, 1.0 if abs(x - hx) <= 7 else 0.5))
        # the citadel: curtain wall, towers and spires on the right
        cx = int(w * 0.80)
        self.beacons = []
        wall = int(h * 0.26)
        towers = [(-0.17, 0.42, 5), (-0.09, 0.34, 4), (-0.02, 0.62, 6), (0.07, 0.38, 4), (0.15, 0.48, 5)]
        cit = [0] * w
        windows = []
        for off, th, tw in towers:
            tx = cx + int(off * w)
            top = int(h * th)
            for x in range(tx - tw, tx + tw + 1):
                if 0 <= x < w:
                    cit[x] = max(cit[x], top)
            for k in range(1, 5):                                    # spire
                for x in range(tx - tw + k, tx + tw - k + 1):
                    if 0 <= x < w and (k * 2 + top) > cit[x] and k < tw:
                        cit[x] = max(cit[x], top + k * 2)
            if 0 <= tx < w:
                self.beacons.append((tx, top + tw * 2))
            for _ in range(5):
                windows.append((tx + r.randint(-tw + 1, tw - 1), r.randint(int(h * 0.2), max(int(h * 0.21), top - 2))))
        for x in range(int(cx - 0.2 * w), int(cx + 0.2 * w)):
            if 0 <= x < w:
                cit[x] = max(cit[x], wall)               # the curtain wall rises from the ordinary ground; no raised plateau line
        self.ridge = [max(ground[x], cit[x] - 1) for x in range(w)]
        rows_px = []
        for py in range(h):
            y = h - 1 - py
            base = gradient(sky, y / h)
            row = []
            for x in range(w):
                c = base
                if y < far[x]:
                    c = mix(base, (46, 20, 78), 0.7)
                if y < cit[x]:
                    c = mix(c, (10, 5, 22), 0.94)
                if y < ground[x]:
                    c = mix((20, 10, 34), (8, 4, 16), 1 - y / max(1, ground[x]))
                    if y == ground[x] - 1:
                        c = (150, 104, 56)
                vx, vy = (x / w - 0.5) * 2, (py / h - 0.5) * 2
                c = shade(c, max(0.3, 1 - 0.38 * (vx * vx + vy * vy) * 0.8))
                if (py // 2) % 2:
                    c = shade(c, 0.92)
                row.append(c)
            rows_px.append(row)
        for wx, wy in windows:
            py = h - 1 - wy
            if 0 <= wx < w and 0 <= py < h and wy < cit[wx] - 2:
                rows_px[py][wx] = (255, 196, 96)
        self.layer = PixelCanvas(w, h, rows=rows_px)
        self.stars = [(r.randrange(w), r.randrange(int(h * 0.62)), r.uniform(0, 6), r.uniform(1, 4)) for _ in range(w // 2)]

    def _sky_ok(self, x: int, y: int) -> bool:
        return 0 <= x < self.size[0] and y > self.ridge[x] + 2

    def _fire(self) -> None:
        r, w = self.rng, self.size[0]
        tx = r.uniform(0.66, 0.92) * w
        th = r.uniform(42, 62)
        self.hero_target = th
        self.pending = (tx, th)

    def update(self, dt: float) -> None:
        if self.layer is None:
            return
        self.clock += dt
        self.recoil = max(0.0, self.recoil - dt)
        w, h = self.size[0], self.size[1] * 2
        self.ps.wind = 0.0
        self.ps.update(dt)
        for e in self.explosions:
            e.update(dt)
        self.explosions = [e for e in self.explosions if not e.done]
        r = self.rng
        # rising golden motes
        if r.random() < dt * 14 * self.settings.particle_density:
            self.ps.emit(Particle(r.uniform(0, w), r.uniform(0, h * 0.2), r.uniform(-1.5, 1.5), r.uniform(3, 8),
                                  r.uniform(3, 6), 5, (255, 214, 120), (140, 60, 120), alpha=0.85))
        # shooting stars
        self.timer -= dt
        if self.timer <= 0:
            self.timer = r.uniform(2.5, 6)
            self.shooting.append([r.uniform(0.1, 0.9) * w, r.uniform(0.6, 0.95) * h, r.uniform(40, 70), -r.uniform(10, 24), 0.0])
        for s in self.shooting:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] += dt
        self.shooting = [s for s in self.shooting if s[4] < 1.1]
        # the hero tank: aim, fire, recoil
        self.hero_angle += (self.hero_target - self.hero_angle) * min(1.0, dt * 4)
        self.fire_timer -= dt
        if self.fire_timer <= 0 and self.pending is None and not self.celebrate:
            self.fire_timer = r.uniform(2.2, 3.6)
            self._fire()
        if self.pending and abs(self.hero_angle - self.hero_target) < 1.5:
            tx, th = self.pending
            self.pending = None
            hy = self.ridge[int(self.hero_x)]
            th = self.hero_angle
            rad = math.radians(th)
            ox, oy = muzzle_point(int(self.hero_x) + 0.5, hy, th, DESIGN_BY_KEY["sovereign"], 2)
            reach = max(10.0, tx - ox)
            reach = min(reach, 4 * max(10.0, self.size[1] * 2 - 10 - oy) / max(0.3, math.tan(rad)))    # never let the arc leave the canvas
            v = math.sqrt(32 * reach / max(0.2, math.sin(2 * rad)))
            self.shells.append({"l": Launch(ox, oy, v * math.cos(rad), v * math.sin(rad), 32.0), "t": 0.0})
            self.recoil = 0.25
            self.fx.muzzle(ox, oy, th, (255, 214, 120))
        for s in self.shells[:]:
            s["t"] += dt
            x, y = s["l"].at(s["t"])
            self.n += 1
            self.fx.trail(x, y, GOLD, AMMO_BY_KEY["aurora"], self.n, self.clock)
            if x < 0 or x >= w or (y < self.ridge[int(x)] and s["t"] > 0.2):
                self.shells.remove(s)
                if 0 <= x < w:
                    self.explosions.append(Explosion(x, y, 6.0, GOLD, 0.95, "prism"))
                    self.fx.impact(x, y, GOLD, (90, 60, 80), 0.9, AMMO_BY_KEY["aurora"])
        if self.celebrate:
            self.fw_timer -= dt
            if self.fw_timer <= 0:
                self.fw_timer = r.uniform(0.2, 0.5)
                bx, by = r.uniform(0.15, 0.85) * w, r.uniform(0.45, 0.85) * h
                col = r.choice(self.celebrate)
                for _ in range(60):
                    a, sp = r.uniform(0, math.tau), r.uniform(8, 34)
                    life = r.uniform(0.9, 1.6)
                    self.ps.emit(Particle(bx, by, math.cos(a) * sp, math.sin(a) * sp, life, life, mix(Palette.WHITE, col, 0.5),
                                          shade(col, 0.2), gravity=26, drag=1.1))

    def draw(self, screen: Screen, t: float) -> None:
        self.ensure(screen.cols, screen.rows)
        cv = self.layer.copy()
        w, h, c = cv.w, cv.h, self.clock
        # aurora ribbons
        for b in range(3):
            for x in range(0, w):
                mid = h * (0.64 + 0.09 * b) + h * 0.06 * math.sin(x * 0.045 + c * 0.6 + b * 2.1) + h * 0.035 * math.sin(x * 0.11 - c * 0.9 + b)
                thick = 5 + 3 * math.sin(x * 0.07 + c + b)
                col = hsv(0.46 + 0.22 * math.sin(x * 0.02 + c * 0.25 + b * 1.3), 0.65, 1.0)
                for dy in range(-int(thick), int(thick) + 1):
                    y = int(mid) + dy
                    if self._sky_ok(x, y):
                        cv.blend(x, y, col, 0.30 * (1 - abs(dy) / (thick + 1)) ** 1.3)
        # stars + shooting stars
        for x, py, ph, sp in self.stars:
            if self._sky_ok(x, h - 1 - py):
                cv.rows[py][x] = mix(cv.rows[py][x], (240, 235, 255), 0.25 + 0.55 * math.sin(c * sp + ph) ** 2)
        for sx, sy, vx, vy, age in self.shooting:
            for k in range(10):
                cv.blendf(sx - vx * 0.03 * k, sy - vy * 0.03 * k, (255, 240, 220), (1 - k / 10) * (1 - age / 1.1))
        # rotating sunburst behind the logo
        cx, cy = w * 0.5, h * 0.74
        for k in range(16):
            a = k * math.tau / 16 + c * 0.05
            ca, sa = math.cos(a), math.sin(a)
            for s in range(6, int(h * 0.5), 1):
                x, y = cx + ca * s * 1.7, cy + sa * s * 0.8
                if self._sky_ok(int(x), int(y)):
                    cv.blendf(x, y, GOLD, 0.075 * (1 - s / (h * 0.5)))
        # beacons
        for bx, by in self.beacons:
            pulse = 0.5 + 0.5 * math.sin(c * 3 + bx)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    cv.blendf(bx + dx, by + dy, (255, 150, 90), 0.5 * pulse / (1 + abs(dx) + abs(dy)))
        self.ps.draw(cv)
        hy = self.ridge[int(self.hero_x)]
        draw_tank(cv, int(self.hero_x) + 0.5, hy, 1, self.hero_angle, GOLD, scale=2, recoil=self.recoil, design=DESIGN_BY_KEY["sovereign"], t=c)
        for s in self.shells:
            x, y = s["l"].at(s["t"])
            draw_projectile(cv, x, y, s["l"].vx, s["l"].vy - 32 * s["t"], GOLD, AMMO_BY_KEY["aurora"], c)
        for e in self.explosions:
            e.draw(cv)
        screen.blit(cv, 0, 0)


def prism_text(screen: Screen, x: int, y: int, text: str, t: float, base: float = 0.1, spread: float = 0.04,
               sat: float = 0.55, val: float = 1.0, bg: Optional[RGB] = None) -> None:
    for i, ch in enumerate(text):
        if ch != " ":
            screen.put(x + i, y, ch, hsv(base + 0.09 * math.sin(t * 1.5 + i * spread * 3) + i * spread * 0.2, sat, val), bg)


def draw_master_logo(screen: Screen, y: int, t: float, tall: bool) -> int:
    """Gold logo with a travelling prismatic shimmer and animated ornament lines."""
    y += 1                                                   # (ornament removed; row kept for breathing room)
    words = [big_word("TERMINAL")] + ([big_word("TANKS")] if tall else [])
    shimmer = (t * 36) % 120 - 25
    for wi, rows in enumerate(words):
        x0 = (screen.cols - len(rows[0])) // 2
        for r, line in enumerate(rows):
            top = mix((255, 236, 150), (214, 120, 60), (r + wi * 6) / 11)
            for i, ch in enumerate(line):
                if ch == " ":
                    continue
                if ch == "█":
                    b = max(0.0, 1 - abs(i + r * 2 + wi * 14 - shimmer) / 10)
                    col = mix(top, hsv(0.55 + i * 0.01 + t * 0.3, 0.45, 1.0), b * 0.8)
                    screen.put(x0 + i, y, ch, col, Palette.BG)
                else:
                    screen.put(x0 + i, y, ch, (70, 32, 90), Palette.BG)
            y += 1
    if not tall:
        sub = "◆  T  A  N  K  S  ◆"
        prism_text(screen, (screen.cols - len(sub)) // 2, y, sub, t, 0.1, 0.05, 0.6)
        y += 1
    edition = "M A S T E R   E D I T I O N"
    screen.center(y + 1, edition, GOLD)
    prism_text(screen, (screen.cols - len(edition)) // 2, y + 1, edition, t, 0.1, 0.06, 0.45)
    return y + 2


def draw_master_menu(screen: Screen, menu: "MenuList", cx: int, y: int, t: float, gap: int = 2) -> None:
    items = menu.items
    w, h = 38, len(items) * gap + 1
    x0 = cx - w // 2
    screen.fill(x0, y - 1, w, h + 2, (10, 6, 22))
    per = 2 * (w + h)
    for i in range(w):                      # animated border, top and bottom
        for yy, k in ((y - 1, i), (y + h - 0, per // 2 - i)):
            screen.put(x0 + i, yy, "━", hsv(0.1 + 0.12 * math.sin((k / per) * math.tau * 2 + t * 1.4), 0.6, 1.0), (10, 6, 22))
    for j in range(h + 2):
        screen.put(x0, y - 1 + j, "┃", hsv(0.1 + 0.1 * math.sin(j * 0.4 + t * 1.4), 0.6, 1.0), (10, 6, 22))
        screen.put(x0 + w - 1, y - 1 + j, "┃", hsv(0.1 + 0.1 * math.sin(j * 0.4 - t * 1.4), 0.6, 1.0), (10, 6, 22))
    for (cxx, cyy, ch) in ((x0, y - 1, "◆"), (x0 + w - 1, y - 1, "◆"), (x0, y + h, "◆"), (x0 + w - 1, y + h, "◆")):
        screen.put(cxx, cyy, ch, GOLD, (10, 6, 22))
    for i, label in enumerate(items):
        row = y + i * gap
        if i == menu.index:
            for k in range(w - 4):
                glow = 0.5 + 0.5 * math.sin(t * 5 - k * 0.15)
                screen.put(x0 + 2 + k, row, " ", Palette.WHITE, mix((60, 34, 8), (120, 70, 16), glow))
            screen.center(row, label, (255, 248, 220), None, x0, w)
            screen.put(x0 + 3, row, "◆", GOLD, None)
            screen.put(x0 + w - 4, row, "◆", GOLD, None)
        else:
            screen.center(row, label, (178, 140, 110), (10, 6, 22), x0, w)


class SecretBackdrop:
    """The secret home theme: green code rain over a dark CRT, with an ASCIIBOT lobbing glyph shells along the bottom."""
    GLYPHS = "01ABCDEF{}[]<>/\\|#$%&*+=~;:?"

    def __init__(self, settings: Settings, seed: int = 33) -> None:
        self.rng = random.Random(seed)
        self.settings = settings
        self.size = (0, 0)
        self.drops: list = []
        self.clock = 0.0
        self.celebrate: Optional[list] = None
        self.shells: list = []
        self.explosions: list = []
        self.timer = 1.2
        self.recoil = 0.0

    def celebrate_with(self, colors: Optional[list]) -> None:
        self.celebrate = colors

    def ensure(self, cols: int, rows: int) -> None:
        if self.size == (cols, rows):
            return
        self.size = (cols, rows)
        r = self.rng
        self.drops = [[r.uniform(-rows, rows), r.uniform(8, 26), r.randint(6, 16)] for _ in range(cols)]

    def update(self, dt: float) -> None:
        self.clock += dt
        rows = self.size[1]
        for d in self.drops:
            d[0] += d[1] * dt
            if d[0] - d[2] > rows:
                d[0], d[1], d[2] = -self.rng.uniform(0, rows * 0.5), self.rng.uniform(8, 26), self.rng.randint(6, 16)
        self.recoil = max(0.0, self.recoil - dt)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = self.rng.uniform(2.2, 3.4)
            self.recoil = 0.25
            v = self.rng.uniform(34, 44)
            design = DESIGN_BY_KEY["asciibot"]
            ang = 38 + 9 * math.sin(self.clock * 0.7)
            ox, oy = muzzle_point(11.5, 2 + visual_lift(design, self.clock, 2), ang, design, 2)
            a = math.radians(ang)
            cap = min(getattr(self, "size", (0, 20))[1] * 2, 72) - 10
            apex = oy + (v * math.sin(a)) ** 2 / 80
            if apex > cap > oy:
                v *= math.sqrt((cap - oy) / (apex - oy))
            self.shells.append({"l": Launch(ox, oy, v * math.cos(a), v * math.sin(a), 40.0), "t": 0.0})
        for s in self.shells[:]:
            s["t"] += dt
            x, y = s["l"].at(s["t"])
            if y < 3.5 and s["t"] > 0.2:
                self.shells.remove(s)
                self.explosions.append(Explosion(x, 3.5, 5.5, (110, 255, 150), 0.9, "code"))
        for e in self.explosions:
            e.update(dt)
        self.explosions = [e for e in self.explosions if not e.done]

    def draw(self, screen: Screen, t: float) -> None:
        self.ensure(screen.cols, screen.rows)
        cols, rows = self.size
        for y in range(rows):
            bg = mix((2, 14, 8), (0, 32, 16), y / max(1, rows - 1))
            screen.fill(0, y, cols, 1, shade(bg, 0.8) if y % 2 else bg)          # CRT scanlines
        tick = int(t * 8)
        for x, (head, _, trail) in enumerate(self.drops):
            for i in range(trail):
                y = int(head) - i
                if 0 <= y < rows:
                    ch = self.GLYPHS[(x * 7919 + y * 104729 + (tick if i < 2 else tick // 4) * 31) % len(self.GLYPHS)]
                    screen.put(x, y, ch, (205, 255, 215) if i == 0 else mix((70, 255, 120), (4, 40, 18), i / trail))
        # the hero: an ASCIIBOT on a ground strip, drawn on black and masked onto the screen
        w, h = cols, min(rows * 2, 72)
        cv = PixelCanvas(w, h, (0, 0, 0))
        for x in range(w):
            cv.plot(x, 0, (22, 96, 48))
            cv.plot(x, 1, (40, 150, 76))
        draw_tank(cv, 11.5, 2, 1, 38 + 9 * math.sin(self.clock * 0.7), (70, 220, 120), scale=2, recoil=self.recoil,
                  design=DESIGN_BY_KEY["asciibot"], t=self.clock)
        ammo = AMMO_BY_KEY["glyph"]
        for s in self.shells:
            x, y = s["l"].at(s["t"])
            draw_projectile(cv, x, y, s["l"].vx, s["l"].vy - 40 * s["t"], (110, 255, 150), ammo, self.clock)
        for e in self.explosions:
            e.draw(cv)
        top = rows - h // 2
        for r in range(h // 2):
            if not 0 <= top + r < rows:
                continue
            for c in range(w):
                a, b = cv.rows[2 * r][c], cv.rows[2 * r + 1][c]
                if a == (0, 0, 0) and b == (0, 0, 0):
                    continue
                bgc = screen.back[top + r][c][2]
                screen.back[top + r][c] = ("▀", bgc if a == (0, 0, 0) else a, bgc if b == (0, 0, 0) else b)


class ThemeBackdrop:
    """Home-screen backdrop for the shop's themed screens: gradient sky, stars / aurora / eclipse, drifting particles,
    a far ridge and a hero tank lobbing shells of its own ammo along the bottom edge. Driven entirely by a HomeTheme."""

    def __init__(self, theme: HomeTheme) -> None:
        self.th = theme
        self.rng = random.Random(sum(map(ord, theme.key)))
        self.size = (0, 0)
        self.clock = 0.0
        self.rowcol: list = []
        self.stars: list = []
        self.motes: list = []
        self.ridge: list = []
        self.shells: list = []
        self.explosions: list = []
        self.timer = 1.2
        self.recoil = 0.0

    def celebrate_with(self, colors: Optional[list]) -> None:
        pass

    def ensure(self, cols: int, rows: int) -> None:
        if self.size == (cols, rows):
            return
        self.size, r, th = (cols, rows), self.rng, self.th
        self.rowcol = [gradient(th.sky, clamp(1 - y / max(1, rows - 1), 0, 1)) for y in range(rows)]
        self.stars = [(r.randrange(cols), r.randrange(0, max(1, int(rows * 0.62))), r.uniform(0, math.tau))
                      for _ in range(cols * rows // 55)] if th.stars else []
        style = MOTE_STYLES.get(th.fx)
        n = int(cols * rows * style[0] * 3) + 8 if style else 0
        self.motes = [(r.uniform(0, cols), r.uniform(0, rows), r.uniform(0.6, 1.4), r.uniform(0, math.tau),
                       r.uniform(0.5, 2.5), r.randrange(3)) for _ in range(n)]
        self.ridge = [int(rows * 0.27 + 1.6 * math.sin(x * 0.06 + 1) + 1.1 * math.sin(x * 0.17)) for x in range(cols)]

    def update(self, dt: float) -> None:
        self.clock += dt
        self.recoil = max(0.0, self.recoil - dt)
        self.timer -= dt
        if self.timer <= 0:
            self.timer, self.recoil = self.rng.uniform(2.2, 3.4), 0.25
            v = self.rng.uniform(34, 44)
            design = DESIGN_BY_KEY[self.th.hero]
            ang = 38 + 9 * math.sin(self.clock * 0.7)                      # the angle the hero's barrel is showing right now
            ox, oy = muzzle_point(15.0, 3 + visual_lift(design, self.clock, 2), ang, design, 2)
            a = math.radians(ang)
            cap = min(self.size[1] * 2, 72) - 10
            apex = oy + (v * math.sin(a)) ** 2 / 80
            if apex > cap > oy:
                v *= math.sqrt((cap - oy) / (apex - oy))                 # keep the whole arc inside the canvas
            self.shells.append({"l": Launch(ox, oy, v * math.cos(a), v * math.sin(a), 40.0), "t": 0.0})
        for s in self.shells[:]:
            s["t"] += dt
            x, y = s["l"].at(s["t"])
            if y < 3.0 and s["t"] > 0.2:
                self.shells.remove(s)
                self.explosions.append(Explosion(x, 3.0, 5.0, self.th.accent, 0.9, AMMO_BY_KEY[self.th.hero_ammo].boom))
        for e in self.explosions:
            e.update(dt)
        self.explosions = [e for e in self.explosions if not e.done]

    def draw(self, screen: Screen, t: float) -> None:
        self.ensure(screen.cols, screen.rows)
        cols, rows = self.size
        th, rc = self.th, self.rowcol
        for y in range(rows):
            screen.fill(0, y, cols, 1, rc[y])
        for x, y, ph in self.stars:
            lvl = int((math.sin(t * 1.6 + ph) + 1) * 1.49)
            screen.put(x, y, "·" if lvl < 2 else "+", mix(rc[y], (255, 255, 255), (0.25, 0.5, 0.85)[lvl]), rc[y])
        if th.corona:
            self._corona(screen, t)
        if th.aurora:
            for b in range(2):
                for x in range(cols):
                    y = int(rows * (0.2 + 0.11 * b) + math.sin(x * 0.07 + t * 0.5 + b * 2.1) * rows * 0.05)
                    if 0 <= y < rows:
                        hue = round((0.45 + 0.2 * math.sin(x * 0.03 + t * 0.2 + b)) * 24) / 24
                        screen.put(x, y, "▒", mix(rc[y], hsv(hue, 0.6, 1.0), 0.45), rc[y])
        style = MOTE_STYLES.get(th.fx)
        if style:
            _, speed, pal, alpha = style
            for x0, y0, sp, ph, amp, ci in self.motes:
                x = int((x0 + math.sin(t * 0.8 * sp + ph) * amp) % cols)
                y = int(rows - 1 - ((y0 + t * speed * sp * 0.45) % rows))
                if 0 <= y < rows:
                    lvl = (0.5, 0.75, 1.0)[int((math.sin(t * 5 * sp + ph) + 1) * 1.49)]
                    screen.put(x, y, "•" if sp > 1.0 else "∙", mix(rc[y], pal[ci], alpha * lvl), rc[y])
        for name in th.layers:
            LAYER_DRAWERS[name](self, screen, cols, rows, t)
        for x in range(cols):
            h = self.ridge[x]
            screen.fill(x, rows - h, 1, h, th.far)
        self._hero(screen, cols, rows)

    def _corona(self, screen: Screen, t: float) -> None:
        cols, rows = self.size
        cx, cy, R = cols - 10, int(rows * 0.3), max(4, rows // 6)
        for dy in range(-R - 3, R + 4):
            for dx in range(-2 * (R + 3), 2 * (R + 3) + 1):
                x, y = cx + dx, cy + dy
                if not (0 <= x < cols and 0 <= y < rows):
                    continue
                d = math.hypot(dx / 2, dy)
                if d <= R:
                    screen.put(x, y, " ", (0, 0, 0), (2, 1, 8))
                elif d <= R + 2.6:
                    ang = math.atan2(dy, dx / 2)
                    k = round((1 - (d - R) / 2.6) * 6) / 6
                    hue = round((ang / math.tau + t * 0.08) % 1 * 24) / 24
                    screen.put(x, y, "▓" if k > 0.5 else "░", mix(self.rowcol[y], hsv(hue, 0.55, 1.0), 0.35 + 0.6 * k),
                               mix(self.rowcol[y], (255, 244, 210), 0.4 * k))

    def _hero(self, screen: Screen, cols: int, rows: int) -> None:
        th, h = self.th, min(rows * 2, 72)
        cv = PixelCanvas(cols, h, (0, 0, 0))
        for x in range(cols):
            cv.plot(x, 0, th.ground)
            cv.plot(x, 1, th.ground)
            cv.plot(x, 2, th.ground_top)
        ammo = AMMO_BY_KEY[th.hero_ammo]
        draw_tank(cv, 15.0, 3, 1, 38 + 9 * math.sin(self.clock * 0.7), th.accent, scale=2, recoil=self.recoil,
                  design=DESIGN_BY_KEY[th.hero], t=self.clock)
        for s in self.shells:
            x, y = s["l"].at(s["t"])
            draw_projectile(cv, x, y, s["l"].vx, s["l"].vy - 40 * s["t"], th.accent, ammo, self.clock)
        for e in self.explosions:
            e.draw(cv)
        top = rows - h // 2
        for r in range(h // 2):
            if not 0 <= top + r < rows:
                continue
            for c in range(cols):
                a, b = cv.rows[2 * r][c], cv.rows[2 * r + 1][c]
                if a == (0, 0, 0) and b == (0, 0, 0):
                    continue
                bgc = screen.back[top + r][c][2]
                screen.back[top + r][c] = ("▀", bgc if a == (0, 0, 0) else a, bgc if b == (0, 0, 0) else b)


def draw_theme_logo(screen: Screen, y: int, t: float, tall: bool, th: HomeTheme) -> int:
    """Gradient logo in the theme's colours with a travelling shimmer."""
    y += 1
    words = [big_word("TERMINAL")] + ([big_word("TANKS")] if tall else [])
    shimmer = (t * 36) % 140 - 25
    for wi, rows_ in enumerate(words):
        x0 = (screen.cols - len(rows_[0])) // 2
        for r, line in enumerate(rows_):
            base = mix(th.logo_a, th.logo_b, (r + wi * 6) / (11 if tall else 5))
            for i, ch in enumerate(line):
                if ch == " ":
                    continue
                if ch == "█":
                    b = max(0.0, 1 - abs(i + r * 2 + wi * 14 - shimmer) / 9)
                    screen.put(x0 + i, y, ch, mix(base, (255, 255, 255), b * 0.75), Palette.BG)
                else:
                    screen.put(x0 + i, y, ch, shade(base, 0.4), Palette.BG)
            y += 1
    if not tall:
        screen.center(y, "▌▌ T A N K S ▐▐", th.logo_b)
        y += 1
    edition = "   ".join(" ".join(w) for w in th.name.split()) + "   ·   E D I T I O N"
    if th.key == "ETERNAL":
        edition = "P R O T E C T O R   O F   T H E   U N I V E R S E"
    screen.center(y + 1, edition, th.accent)
    return y + 2


def draw_theme_menu(screen: Screen, menu: "MenuList", cx: int, y: int, t: float, th: HomeTheme, gap: int = 2) -> None:
    items = menu.items
    w, h = 40, len(items) * gap + 1
    x0, bg = cx - w // 2, shade(mix(th.ground, th.accent, 0.08), 1.0)
    screen.box(x0, y - 1, w, h + 2, "double", shade(th.accent, 0.8), bg, th.name, th.logo_a)
    sel_bg = mix(bg, th.accent, 0.28)
    for i, label in enumerate(items):
        row = y + i * gap
        if i == menu.index:
            screen.fill(x0 + 2, row, w - 4, 1, sel_bg)
            screen.center(row, f"◆ {label} ◆", Palette.WHITE, sel_bg, x0, w)
        else:
            screen.center(row, label, shade(th.accent, 0.62), bg, x0, w)


def draw_secret_logo(screen: Screen, y: int, t: float, tall: bool) -> int:
    """Terminal-green logo with glitching rows and a chroma-split edge."""
    head = "┌─[ root@tanks ]─[ ~/secret ]─┐"
    screen.center(y, head, (80, 230, 130))
    y += 1
    glitch = int(t * 6) % 9 == 0
    words = [big_word("TERMINAL")] + ([big_word("TANKS")] if tall else [])
    shimmer = (t * 40) % 130 - 25
    for wi, rows in enumerate(words):
        x0 = (screen.cols - len(rows[0])) // 2
        for r, line in enumerate(rows):
            jitter = (1 if (r + wi + int(t * 6)) % 2 else -1) if glitch and (r * 7 + int(t * 6)) % 4 == 0 else 0
            top = mix((190, 255, 205), (30, 170, 80), (r + wi * 6) / 11)
            for i, ch in enumerate(line):
                if ch == " ":
                    continue
                if ch == "█":
                    b = max(0.0, 1 - abs(i + r * 2 + wi * 14 - shimmer) / 9)
                    screen.put(x0 + i + jitter, y, ch, mix(top, (235, 255, 240), b * 0.8), Palette.BG)
                else:
                    ghost = (255, 60, 120) if glitch and i % 2 else (20, 90, 54)
                    screen.put(x0 + i + jitter, y, ch, ghost, Palette.BG)
            y += 1
    if not tall:
        screen.center(y, "▌▌ T A N K S ▐▐", (110, 255, 150))
        y += 1
    edition = "S E C R E T   E D I T I O N"
    shown = edition[:max(1, int((t % 6) * 12))] if int(t) % 6 < 3 else edition
    screen.text((screen.cols - len(edition)) // 2, y + 1, shown, (130, 255, 170))
    if int(t * 2) % 2 == 0:
        screen.put((screen.cols - len(edition)) // 2 + len(shown), y + 1, "█", (130, 255, 170))
    return y + 2


def draw_secret_menu(screen: Screen, menu: "MenuList", cx: int, y: int, t: float, gap: int = 2) -> None:
    items = menu.items
    w, h = 40, len(items) * gap + 1
    x0, bg = cx - w // 2, (2, 18, 10)
    screen.box(x0, y - 1, w, h + 2, "single", (50, 190, 95), bg, "ROOT MENU", (150, 255, 180))
    for i, label in enumerate(items):
        row = y + i * gap
        if i == menu.index:
            screen.fill(x0 + 2, row, w - 4, 1, (8, 62, 30))
            screen.center(row, f"> {label} <", (200, 255, 215), (8, 62, 30), x0, w)
            if int(t * 3) % 2 == 0:
                screen.put(x0 + w - 5, row, "_", (150, 255, 180), (8, 62, 30))
        else:
            screen.center(row, label, (60, 150, 90), bg, x0, w)
