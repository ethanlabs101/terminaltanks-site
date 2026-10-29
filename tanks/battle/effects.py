"""Particles and explosions: every blast style, smoke, debris, trails and the effects factory battles use."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from tanks.art.projectiles import draw_glyph
from tanks.battle.terrain import Terrain
from tanks.colors import RGB, clamp, ease_out, flicker, gradient, hsv, mix, shade
from tanks.content.ammo import AmmoType
from tanks.content.tanks import TankDesign
from tanks.screen import PixelCanvas
from tanks.settings import Settings


@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    c0: RGB
    c1: RGB
    gravity: float = 0.0
    drag: float = 0.0
    alpha: float = 1.0
    solid: bool = False
    size: int = 1
    windk: float = 0.0


class ParticleSystem:
    def __init__(self, cap: int = 2600) -> None:
        self.items: list[Particle] = []
        self.cap = cap
        self.wind = 0.0

    def emit(self, p: Particle) -> None:
        if len(self.items) < self.cap:
            self.items.append(p)

    def update(self, dt: float, terrain: Optional[Terrain] = None) -> None:
        alive = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            if p.drag:
                k = max(0.0, 1.0 - p.drag * dt)
                p.vx *= k
                p.vy *= k
            p.vy -= p.gravity * dt
            if p.windk:
                p.vx += self.wind * p.windk * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.solid and terrain is not None:
                xi = int(p.x)
                if p.y < 0 or (0 <= xi < terrain.width and p.y < terrain.heights[xi]):
                    continue
            alive.append(p)
        self.items = alive

    def draw(self, canvas: PixelCanvas) -> None:
        for p in self.items:
            t = 1 - p.life / p.max_life
            col = mix(p.c0, p.c1, t)
            a = p.alpha * (1 - t)
            x, y = int(p.x // 1), int(p.y // 1)
            canvas.blend(x, y, col, a)
            if p.size > 1:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    canvas.blend(x + dx, y + dy, col, a * 0.5)


_PREMIUM_BLASTS = {      # second premium set: fireball palettes (core -> rim)
    "biolume": [(0.0, (240, 255, 255)), (0.3, (150, 255, 236)), (0.6, (40, 160, 210)), (0.85, (10, 60, 110)), (1.0, (4, 20, 44))],
    "foxfire": [(0.0, (250, 252, 255)), (0.3, (170, 210, 255)), (0.6, (70, 110, 240)), (0.85, (30, 30, 140)), (1.0, (10, 8, 50))],
    "hardlight": [(0.0, (255, 255, 255)), (0.3, (200, 250, 255)), (0.6, (70, 200, 255)), (0.85, (20, 80, 180)), (1.0, (6, 20, 60))],
    "paradox": [(0.0, (255, 255, 255)), (0.3, (220, 200, 255)), (0.6, (140, 90, 240)), (0.85, (50, 20, 120)), (1.0, (12, 4, 36))],
    "atomic": [(0.0, (255, 255, 255)), (0.25, (220, 240, 255)), (0.55, (90, 160, 255)), (0.85, (30, 60, 160)), (1.0, (8, 14, 50))],
    "spore": [(0.0, (255, 240, 220)), (0.3, (255, 160, 200)), (0.6, (170, 50, 110)), (0.85, (40, 120, 90)), (1.0, (10, 34, 26))],
    "eruption": [(0.0, (255, 240, 200)), (0.3, (255, 180, 90)), (0.6, (200, 130, 60)), (0.85, (110, 74, 40)), (1.0, (40, 28, 18))],
    "jade": [(0.0, (255, 250, 220)), (0.3, (180, 255, 210)), (0.6, (40, 180, 120)), (0.85, (14, 80, 56)), (1.0, (4, 26, 20))],
    "zodiac": [(0.0, (255, 255, 240)), (0.3, (255, 226, 150)), (0.6, (120, 130, 240)), (0.85, (30, 40, 120)), (1.0, (8, 10, 40))],
    "ghostfire": [(0.0, (230, 255, 236)), (0.3, (140, 255, 180)), (0.6, (40, 160, 100)), (0.85, (20, 60, 50)), (1.0, (6, 20, 18))],
}


class Explosion:
    """Expanding fireball with radial gradient, flash core and shockwave; `style` is the ammo's blast look."""

    def __init__(self, x: float, y: float, radius: float, accent: RGB, duration: float = 0.95,
                 style: str = "classic") -> None:
        self.x, self.y, self.radius, self.duration, self.age = x, y, radius, duration, 0.0
        self.accent, self.style = accent, style
        if style == "implode":
            stops = [(0.0, shade(accent, 0.12)), (0.45, shade(accent, 0.35)), (0.8, accent), (1.0, mix(accent, (255, 255, 255), 0.6))]
        elif style == "fire":
            stops = [(0.0, (255, 250, 220)), (0.25, (255, 214, 110)), (0.55, mix((255, 110, 24), accent, 0.25)),
                     (0.85, (150, 32, 10)), (1.0, (50, 14, 8))]
        elif style == "magma":
            stops = [(0.0, (255, 244, 190)), (0.25, (255, 176, 60)), (0.55, (226, 70, 18)), (0.85, (110, 22, 10)), (1.0, (34, 10, 8))]
        elif style == "nova":
            stops = [(0.0, (255, 255, 255)), (0.3, (255, 252, 214)), (0.55, mix((255, 200, 90), accent, 0.3)),
                     (0.85, (255, 110, 34)), (1.0, (80, 22, 12))]
        elif style == "sigil":
            stops = [(0.0, (255, 252, 230)), (0.3, (255, 226, 130)), (0.6, (230, 150, 40)), (0.85, (120, 60, 20)), (1.0, (30, 16, 8))]
        elif style == "eclipse":
            stops = [(0.0, (8, 3, 18)), (0.45, (56, 20, 110)), (0.75, (255, 200, 90)), (1.0, (255, 250, 222))]
        elif style == "tidal":
            stops = [(0.0, (240, 255, 255)), (0.3, (140, 230, 255)), (0.6, (30, 120, 200)), (0.85, (10, 40, 110)), (1.0, (4, 14, 40))]
        elif style == "cinderstorm":
            stops = [(0.0, (255, 240, 200)), (0.3, (255, 150, 50)), (0.6, (180, 40, 16)), (0.85, (60, 14, 10)), (1.0, (16, 6, 6))]
        elif style == "rewind":
            stops = [(0.0, (255, 255, 250)), (0.35, (255, 226, 150)), (0.65, (150, 100, 240)), (0.9, (50, 20, 110)), (1.0, (14, 6, 40))]
        elif style == "code":
            stops = [(0.0, (230, 255, 235)), (0.3, (120, 255, 150)), (0.6, (30, 170, 70)), (0.85, (10, 70, 30)), (1.0, (4, 24, 12))]
        elif style == "blessing":
            stops = [(0.0, (255, 255, 255)), (0.25, (255, 226, 120)), (0.6, (176, 120, 255)), (1.0, (30, 10, 70))]
        elif style == "xenon":
            stops = [(0.0, (255, 255, 255)), (0.2, (150, 255, 215)), (0.5, (150, 100, 255)), (0.8, (70, 30, 150)), (1.0, (14, 6, 40))]
        elif style == "alien":
            stops = [(0.0, (235, 255, 240)), (0.25, (130, 255, 190)), (0.55, (80, 90, 220)), (0.85, (60, 20, 120)), (1.0, (16, 6, 36))]
        elif style in _PREMIUM_BLASTS:
            stops = _PREMIUM_BLASTS[style]
        else:
            stops = [(0.0, (255, 252, 238)), (0.28, mix((255, 255, 255), accent, 0.35)), (0.55, accent),
                     (0.8, shade(accent, 0.5)), (1.0, shade(accent, 0.2))]
        self.palette = [gradient(stops, i / 15) for i in range(16)]

    @property
    def done(self) -> bool:
        return self.age >= self.duration

    @property
    def progress(self) -> float:
        return self.age / self.duration

    def update(self, dt: float) -> None:
        self.age += dt

    def draw(self, canvas: PixelCanvas) -> None:
        p = self.progress
        if p >= 1:
            return
        R, style = self.radius, self.style
        grow = max(0.0, (p - 0.1) / 0.9) if style == "implode" else p
        rr = R * ease_out(grow / 0.25) if grow < 0.25 else R * (1 - 0.45 * (grow - 0.25) / 0.75)
        alpha = 1.0 if p < 0.5 else 1 - (p - 0.5) / 0.5
        span = int(max(rr, R * 2.2)) + 2
        cx, cy = int(self.x), int(self.y)
        ring = R * (0.4 + 1.6 * ease_out(p))
        flash = R * 1.9 * (1 - p / 0.12) if (p < 0.12 and style != "implode") else 0.0
        pull = R * (2.4 - 12 * p) if (style == "implode" and p < 0.2) else 0.0
        for yy in range(cy - span, cy + span + 1):
            for xx in range(cx - span, cx + span + 1):
                dx, dy = xx + 0.5 - self.x, yy + 0.5 - self.y
                d = math.hypot(dx, dy)
                if flash and d <= flash:
                    canvas.blend(xx, yy, (255, 255, 250), 0.75 * (1 - d / flash * 0.5))
                if pull and abs(d - pull) < 0.8:
                    canvas.blend(xx, yy, mix(self.accent, (255, 255, 255), 0.4), 0.8)
                if d <= rr:
                    f = min(1.0, d / max(rr, 0.1) + p * 0.55)
                    col = self.palette[int(f * 15)]
                    if style in ("prism", "bloom"):
                        col = mix(col, hsv(math.atan2(dy, dx) / math.tau + p * 0.7 + d * 0.03, 0.6, 1.0), 0.55)
                    canvas.blend(xx, yy, col, alpha * (1 - d / max(rr, 0.1) * 0.25))
                if abs(d - ring) < 0.75 and p < 0.9 and style != "implode":
                    canvas.blend(xx, yy, self.palette[3], (1 - p) * 0.55)
        if style in ("rays", "starrays", "prism"):
            self._rays(canvas, p)
        elif style == "cluster":
            self._cluster(canvas, p)
        elif style == "fire":
            self._plume(canvas, p)
        elif style == "ring":
            self._ring2(canvas, p)
        elif style == "cloud":
            self._cloud(canvas, p)
        elif style == "shock":
            self._shock(canvas, p)
        elif style == "shatter":
            self._shatter(canvas, p)
        elif style == "nova":
            self._nova(canvas, p)
        elif style == "magma":
            self._magma(canvas, p)
        elif style == "thunder":
            self._forks(canvas, p)
        elif style == "code":
            self._code(canvas, p)
        elif style == "bloom":
            self._bloom(canvas, p)
        elif style in ("sigil", "eclipse", "tidal", "cinderstorm", "rewind"):
            self._ancient(canvas, p)
        elif style == "blessing":
            self._blessing(canvas, p)
        elif style == "xenon":
            self._xenon(canvas, p)
        elif style == "alien":
            for k in range(3):
                q = clamp((p - k * 0.14) / 0.7, 0, 1)
                if 0 < q < 1:
                    self._ringline(canvas, self.radius * (0.5 + 3.0 * ease_out(q)), mix((120, 255, 190), (190, 120, 255), k / 2), (1 - q) * 0.85)
        elif style in _PREMIUM_BLASTS:
            self._premium2(canvas, p)

    def _premium2(self, canvas: PixelCanvas, p: float) -> None:
        """The second premium set's signature blasts (drawn over the shared fireball)."""
        R, x, y, st = self.radius, self.x, self.y, self.style
        if st == "biolume":                                 # a jellyfish bloom: a bell of light and trailing tendrils
            q = ease_out(clamp(p / 0.7, 0, 1))
            for k in range(40):
                a_ = math.pi * k / 39
                canvas.blendf(x + math.cos(a_) * R * 1.8 * q, y + math.sin(a_) * R * 1.3 * q, (160, 255, 236), (1 - p) * 0.8)
            for k in range(7):
                bx = x + (k - 3) * R * 0.5 * q
                for s in range(int(R * 2.2 * q)):
                    canvas.blendf(bx + math.sin(s * 0.6 + p * 9 + k) * 1.2, y - s, (90, 210, 240), (1 - p) * 0.55 * (1 - s / (R * 2.4 + 1)))
        elif st == "foxfire":                               # nine flames rising in a circle
            for k in range(9):
                a_ = k * math.tau / 9 + p * 2
                fx_, fy_ = x + math.cos(a_) * R * 1.6 * ease_out(p), y + math.sin(a_) * R * 0.7 + p * R * 1.5
                for s in range(4):
                    canvas.blendf(fx_, fy_ + s, gradient(((0, (240, 252, 255)), (1, (60, 80, 230))), s / 3), (1 - p) * (0.95 - s * 0.2))
        elif st == "hardlight":                             # a vertical pillar of light and a horizontal flare line
            q = clamp(p / 0.3, 0, 1)
            for s in range(int(R * 5 * q)):
                canvas.blendf(x, y + s, (255, 255, 255), (1 - p) * 0.9)
                canvas.blendf(x - 1, y + s, (90, 230, 255), (1 - p) * 0.5)
                canvas.blendf(x + 1, y + s, (90, 230, 255), (1 - p) * 0.5)
            for s in range(-int(R * 3.5), int(R * 3.5) + 1):
                canvas.blendf(x + s, y, (180, 245, 255), (1 - p) * 0.8 * (1 - abs(s) / (R * 3.6)))
        elif st == "paradox":                               # two rings expanding in opposite directions of time
            for k, (col, rev) in enumerate((((210, 170, 255), False), ((255, 255, 255), True))):
                q = (1 - p) if rev else p
                self._ringline(canvas, R * (0.4 + 2.6 * ease_out(q)), col, (1 - p) * 0.85)
            for k in range(4):
                a_ = k * math.pi / 2 + p * 4
                canvas.blendf(x + math.cos(a_) * R * 2 * p, y + math.sin(a_) * R * 2 * p, (255, 255, 255), 1 - p)
        elif st == "atomic":                                # a mushroom cloud: a rising stem and a rolling cap, a shockwave ring
            q = ease_out(clamp(p / 0.8, 0, 1))
            top = y + R * 3.4 * q
            for s in range(int(R * 3.4 * q)):
                w_ = R * (0.35 + 0.15 * math.sin(s * 0.5 + p * 8))
                for dx in range(-int(w_), int(w_) + 1):
                    canvas.blendf(x + dx, y + s, (170, 210, 255), (1 - p) * 0.55)
            for dx in range(-int(R * 1.9 * q), int(R * 1.9 * q) + 1):
                for dy in range(-int(R * 0.9 * q), int(R * 0.9 * q) + 1):
                    if (dx / max(1, R * 1.9 * q)) ** 2 + (dy / max(1, R * 0.9 * q)) ** 2 <= 1:
                        canvas.blendf(x + dx, top + dy, mix((240, 250, 255), (60, 110, 230), abs(dy) / max(1, R * q)), (1 - p) * 0.7)
            self._ringline(canvas, R * (1 + 3.5 * ease_out(p)), (200, 230, 255), (1 - p) * 0.7)
        elif st == "spore":                                 # a ring of spores drifting out and up
            for k in range(14):
                a_ = k * math.tau / 14
                rr = R * (0.6 + 2.2 * ease_out(p))
                canvas.blendf(x + math.cos(a_) * rr, y + math.sin(a_) * rr * 0.7 + p * R, (190, 255, 220) if k % 2 else (255, 200, 230), (1 - p) * 0.9)
        elif st == "eruption":                              # a column of sand and fire bursting straight up from below
            q = ease_out(clamp(p / 0.5, 0, 1))
            for s in range(int(R * 4.5 * q)):
                spread = 0.6 + s * 0.12
                for dx in range(-int(R * spread), int(R * spread) + 1):
                    k = s / (R * 4.5 + 1)
                    canvas.blendf(x + dx + math.sin(s * 0.7 + p * 10) * 0.8, y + s, mix((255, 200, 120), (190, 140, 80), k), (1 - p) * (0.75 - 0.4 * k))
        elif st == "jade":                                  # a jade serpent ring biting its own tail, gold glints
            for k in range(36):
                a_ = k * math.tau / 36 + p * 3
                rr = R * (0.8 + 1.6 * ease_out(p)) * (1 + 0.08 * math.sin(k * 1.3))
                canvas.blendf(x + math.cos(a_) * rr, y + math.sin(a_) * rr * 0.8, (250, 214, 120) if k % 6 == 0 else (60, 210, 140), (1 - p) * 0.9)
        elif st == "zodiac":                                # a five-point star drawn in gold lines
            q = ease_out(clamp(p / 0.4, 0, 1))
            pts = [(x + math.cos(math.pi / 2 + k * math.tau * 2 / 5) * R * 2.2 * q, y + math.sin(math.pi / 2 + k * math.tau * 2 / 5) * R * 2.2 * q) for k in range(5)]
            for k in range(5):
                (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % 5]
                n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
                for j in range(n + 1):
                    canvas.blendf(x0 + (x1 - x0) * j / n, y0 + (y1 - y0) * j / n, (255, 226, 140), (1 - p) * 0.85)
                canvas.blendf(x0, y0, (255, 255, 255), 1 - p)
        elif st == "ghostfire":                             # green ghost-flames and a skull-pale flash
            for k in range(10):
                a_ = k * math.tau / 10 + p * 1.5
                bx, by = x + math.cos(a_) * R * 1.5 * ease_out(p), y + abs(math.sin(a_)) * R * 0.8
                for s in range(5):
                    canvas.blendf(bx + math.sin(p * 12 + k + s) * 0.6, by + s + p * R * 2, gradient(((0, (220, 255, 230)), (1, (30, 120, 60))), s / 4), (1 - p) * (0.9 - s * 0.15))

    def _blessing(self, canvas: PixelCanvas, p: float) -> None:        # BLESSING burst: white core, an 8-point golden star, 3 rings, orbiting stars
        R = self.radius
        q = ease_out(clamp(p / 0.6, 0, 1))
        if p < 0.3:
            for dx in range(-int(R), int(R) + 1):
                for dy in range(-int(R), int(R) + 1):
                    if math.hypot(dx, dy) <= R * (0.4 + 1.6 * p):
                        canvas.blendf(self.x + dx, self.y + dy, (255, 252, 235), (1 - p / 0.3) * 0.95)
        for k in range(8):
            a_ = k * math.pi / 4 + p * 1.2
            ln = R * (3.4 if k % 2 == 0 else 1.9) * q
            for s in range(1, int(ln) + 1):
                canvas.blendf(self.x + math.cos(a_) * s, self.y + math.sin(a_) * s, (255, 226, 120) if k % 2 == 0 else (255, 255, 255), (1 - p) * (0.95 - 0.4 * s / max(1, ln)))
        for k, col in enumerate(((255, 214, 90), (255, 255, 255), (176, 120, 255))):
            qq = clamp((p - k * 0.1) / 0.7, 0, 1)
            if 0 < qq < 1:
                self._ringline(canvas, R * (0.5 + 3.0 * ease_out(qq)), col, (1 - qq) * 0.9)
        for k in range(10):
            a_ = -p * 5 + k * math.tau / 10
            rr = R * (1.2 + 2.2 * q)
            canvas.blendf(self.x + math.cos(a_) * rr, self.y + math.sin(a_) * rr, (255, 240, 170) if k % 2 else (176, 120, 255), (1 - p) * 0.9)

    def _xenon(self, canvas: PixelCanvas, p: float) -> None:           # XENON bloom: white flash, 5 staggered rings, a rotating 12-spoke crystal, hex star
        R = self.radius
        if p < 0.25:
            for dx in range(-int(R), int(R) + 1):
                for dy in range(-int(R), int(R) + 1):
                    d = math.hypot(dx, dy)
                    if d <= R * (0.5 + 2 * p):
                        canvas.blendf(self.x + dx, self.y + dy, mix((255, 255, 255), (150, 255, 215), d / (R * 1.5)), (1 - p / 0.25) * 0.9)
        for k in range(5):
            q = clamp((p - k * 0.1) / 0.65, 0, 1)
            if 0 < q < 1:
                self._ringline(canvas, R * (0.4 + 3.4 * ease_out(q)), mix((120, 255, 190), (190, 120, 255), k / 4), (1 - q) * 0.9)
        if p < 0.8:
            q = p / 0.8
            for k in range(12):
                a_ = k * math.tau / 12 + p * 3
                ln = R * (0.5 + 3.2 * ease_out(q)) * (1.0 if k % 2 else 0.6)
                for s in range(2, int(ln) + 1, 2):
                    canvas.blendf(self.x + math.cos(a_) * s, self.y + math.sin(a_) * s, (230, 255, 240) if s > ln - 3 else (130, 255, 200), (1 - q) * 0.85)
            for k in range(6):                               # hex star core
                a_ = k * math.pi / 3 - p * 2
                for s in range(1, int(R * 0.9)):
                    canvas.blendf(self.x + math.cos(a_) * s, self.y + math.sin(a_) * s, (255, 255, 255), (1 - q) * 0.9)

    def _ancient(self, canvas: PixelCanvas, p: float) -> None:          # the Ancient Artifact blasts: rings, rays and rune geometry
        st, R = self.style, self.radius
        gold, white = (255, 226, 130), (255, 255, 255)
        if st == "sigil":                                                 # a runic circle with a rotating hexagram
            r0 = R * (0.9 + 1.7 * ease_out(p))
            self._ringline(canvas, r0, gold, (1 - p) * 0.9)
            self._ringline(canvas, r0 * 0.72, white, (1 - p) * 0.5)
            for k in range(6):
                a = k * math.tau / 6 + p * 2.4
                for j in range(int(r0)):
                    canvas.blendf(self.x + math.cos(a) * j, self.y + math.sin(a) * j, gold, (1 - p) * 0.7)
        elif st == "eclipse":                                             # dark disc with a flaring corona
            for k in range(16):
                a = k * math.tau / 16 + p * 0.8
                ln = R * (1.0 + 2.6 * ease_out(p)) * (0.6 + 0.4 * math.sin(k * 3.1))
                for j in range(int(ln)):
                    canvas.blendf(self.x + math.cos(a) * (R * 0.6 + j), self.y + math.sin(a) * (R * 0.6 + j), gold, (1 - p) * 0.8 * (1 - j / max(1, ln)))
            self._ringline(canvas, R * (0.7 + 2.0 * ease_out(p)), (170, 110, 255), (1 - p) * 0.7)
        elif st == "tidal":                                               # staggered water rings
            for k in range(4):
                q = clamp((p - k * 0.1) / 0.7, 0, 1)
                if 0 < q < 1:
                    self._ringline(canvas, R * (0.5 + 3.2 * ease_out(q)), mix((120, 220, 255), white, 0.3 * k / 3), (1 - q) * 0.85)
        elif st == "cinderstorm":                                         # sparks flung out on arcs
            for k in range(18):
                a = k * math.tau / 18 + 0.3
                s = R * (0.6 + 2.8 * ease_out(p)) * (0.7 + 0.3 * math.sin(k * 2.3))
                canvas.blendf(self.x + math.cos(a) * s, self.y + math.sin(a) * s - 5 * p * p * R * 0.4, (255, 190, 90), (1 - p) * 0.9)
            self._ringline(canvas, R * (0.5 + 1.8 * ease_out(p)), (255, 120, 40), (1 - p) * 0.6)
        else:                                                             # rewind: rings fall back into the blast
            for k in range(3):
                q = clamp(1 - (p - k * 0.1) / 0.8, 0, 1)
                if 0 < q < 1:
                    self._ringline(canvas, R * (0.4 + 2.6 * q), mix((255, 226, 150), (170, 110, 255), k / 2), min(1.0, 1.6 * q) * 0.8)
            for k in range(8):
                a = k * math.tau / 8 - p * 3
                ln = R * 2.4 * (1 - p)
                for j in range(int(ln)):
                    canvas.blendf(self.x + math.cos(a) * (ln - j), self.y + math.sin(a) * (ln - j), white, (1 - p) * 0.5)

    def _bloom(self, canvas: PixelCanvas, p: float) -> None:            # eight prismatic petals unfolding
        reach = self.radius * (1.0 + 2.6 * ease_out(p))
        for k in range(8):
            a = k * math.tau / 8 + p * 0.7
            ca, sa = math.cos(a), math.sin(a)
            col = hsv(k / 8 + p * 0.6, 0.55, 1.0)
            for s in range(1, int(reach) + 1):
                w = math.sin(s / reach * math.pi) * (1.2 + 2.2 * p)
                for side in (-1, 1):
                    canvas.blendf(self.x + ca * s - sa * w * side, self.y + sa * s + ca * w * side, col, (1 - p) * 0.85)
        self._ringline(canvas, self.radius * (0.5 + 2.0 * ease_out(p)), (255, 255, 255), (1 - p) * 0.5)

    def _ringline(self, canvas: PixelCanvas, r: float, col: RGB, a: float) -> None:
        for k in range(int(math.tau * r * 1.5) + 1):
            ang = k / max(1.0, r * 1.5)
            canvas.blendf(self.x + math.cos(ang) * r, self.y + math.sin(ang) * r, col, a)

    def _shock(self, canvas: PixelCanvas, p: float) -> None:            # three staggered shockwaves
        for k in range(3):
            q = clamp((p - k * 0.12) / 0.7, 0, 1)
            if 0 < q < 1:
                self._ringline(canvas, self.radius * (0.6 + 2.8 * ease_out(q)), mix(self.accent, (255, 255, 255), 0.5), (1 - q) * 0.8)

    def _shatter(self, canvas: PixelCanvas, p: float) -> None:          # ice crystals flung outward
        for k in range(14):
            a = k * math.tau / 14 + 0.2
            d0 = self.radius * (0.5 + 2.2 * ease_out(p)) * (0.7 + 0.5 * ((k * 7) % 5) / 4)
            for s in range(3):
                canvas.blendf(self.x + math.cos(a) * (d0 - s), self.y + math.sin(a) * (d0 - s),
                              mix((235, 250, 255), self.accent, s / 3), (1 - p) * (0.95 - s * 0.25))

    def _nova(self, canvas: PixelCanvas, p: float) -> None:             # white flash, double ring, long rays
        if p < 0.25:
            fr = self.radius * 2.4 * (1 - p / 0.25)
            for yy in range(int(self.y - fr) - 1, int(self.y + fr) + 2):
                for xx in range(int(self.x - fr) - 1, int(self.x + fr) + 2):
                    d = math.hypot(xx + 0.5 - self.x, yy + 0.5 - self.y)
                    if d <= fr:
                        canvas.blend(xx, yy, (255, 255, 245), 0.5 * (1 - d / fr))
        self._ringline(canvas, self.radius * (0.7 + 2.2 * ease_out(p)), (255, 244, 200), (1 - p) * 0.8)
        self._ringline(canvas, self.radius * (0.4 + 3.4 * ease_out(p)), self.accent, (1 - p) * 0.5)
        for k in range(12):
            a = k * math.tau / 12 + p * 0.5
            for s in range(1, int(self.radius * (1.4 + 2.2 * ease_out(p))) + 1):
                canvas.blendf(self.x + math.cos(a) * s, self.y + math.sin(a) * s, (255, 240, 190), (1 - p) * 0.7 * (1 - s / (self.radius * 3.6)))

    def _magma(self, canvas: PixelCanvas, p: float) -> None:            # lava globs thrown up in arcs + glowing pool
        R = self.radius
        for k in range(9):
            a = 0.35 + k * (math.pi - 0.7) / 8
            v, tau = R * (2.2 + 0.5 * ((k * 5) % 3)), p * 1.6
            gx, gy = self.x + math.cos(a) * v * tau * 0.9, self.y + math.sin(a) * v * tau - 4.5 * R * tau * tau
            if p < 0.85:
                for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    canvas.blendf(gx + dx, gy + dy, (255, int(170 - 60 * p), 50), 0.9 * (1 - p))
        if p < 0.9:
            for dx in range(-int(R * 1.3), int(R * 1.3) + 1):
                canvas.blendf(self.x + dx, self.y - 1, (255, 120, 30), 0.45 * (1 - p) * (1 - abs(dx) / (R * 1.4)))

    def _forks(self, canvas: PixelCanvas, p: float) -> None:            # lightning forking out of the blast
        if p > 0.75:
            return
        R, step = self.radius, int(self.age * 22)
        for k in range(7):
            a = k * math.tau / 7 + 0.3
            x, y = self.x, self.y
            for s in range(int(R * 1.8)):
                a2 = a + (flicker(step * 0.033, k, s) - 0.5) * 1.1
                x, y = x + math.cos(a2) * 1.6, y + math.sin(a2) * 1.6
                canvas.blendf(x, y, (235, 245, 255), (1 - p / 0.75) * 0.95)
                if s % 3 == 0:
                    canvas.blendf(x + 1, y, self.accent, (1 - p / 0.75) * 0.4)

    def _code(self, canvas: PixelCanvas, p: float) -> None:             # a spray of ASCII glyphs
        R = self.radius
        for k in range(10):
            a = k * math.tau / 10 + 0.4
            d = R * (0.4 + 2.4 * ease_out(p))
            draw_glyph(canvas, self.x + math.cos(a) * d, self.y + math.sin(a) * d * 0.9, int(self.age * 10) + k,
                       (110, 255, 150), (1 - p) * 0.9)

    def _rays(self, canvas: PixelCanvas, p: float) -> None:
        n = {"rays": 8, "starrays": 12, "prism": 16}[self.style]
        length = self.radius * (1.1 + (1.0 if self.style == "rays" else 1.7) * ease_out(p))
        for k in range(n):
            a = k * math.tau / n + (0.3 if self.style == "rays" else p * 0.8 if self.style == "prism" else 0.0)
            ca, sa = math.cos(a), math.sin(a)
            col = hsv(k / n + p, 0.6, 1.0) if self.style == "prism" else mix((255, 255, 255), self.accent, 0.4)
            for s in range(1, int(length) + 1):
                canvas.blendf(self.x + ca * s, self.y + sa * s, col, (1 - p) * (1 - s / length) * 0.85)

    def _cluster(self, canvas: PixelCanvas, p: float) -> None:
        R = self.radius
        for k in range(6):
            a = k * math.tau / 6 + 0.4
            local = clamp((p - 0.12 - k * 0.05) / 0.5, 0, 1)
            if 0 < local < 1:
                r = R * 0.45 * math.sin(local * math.pi)
                bx, by = self.x + math.cos(a) * R * 1.45, self.y + math.sin(a) * R * 1.45
                for yy in range(int(by - r) - 1, int(by + r) + 2):
                    for xx in range(int(bx - r) - 1, int(bx + r) + 2):
                        d = math.hypot(xx + 0.5 - bx, yy + 0.5 - by)
                        if d <= r:
                            canvas.blend(xx, yy, mix((255, 255, 255), self.palette[2], d / max(r, 0.1)), (1 - local) * 0.9)

    def _plume(self, canvas: PixelCanvas, p: float) -> None:
        if p >= 0.8:
            return
        R = self.radius
        cols = int(R * 1.2)
        for dx in range(-cols, cols + 1):
            height = R * (1.0 + 1.4 * flicker(self.age, dx, 7)) * (1 - p / 0.8) * (1 - abs(dx) / (cols + 1))
            for dy in range(int(height)):
                col = gradient(((0, (255, 230, 140)), (0.5, (255, 120, 24)), (1, (120, 24, 8))), dy / max(1.0, height))
                canvas.blendf(self.x + dx, self.y + dy + 1, col, 0.8 * (1 - p))

    def _ring2(self, canvas: PixelCanvas, p: float) -> None:
        r = self.radius * (0.8 + 2.4 * ease_out(p))
        for k in range(int(math.tau * r * 1.6) + 1):
            a = k / max(1.0, r * 1.6)
            canvas.blendf(self.x + math.cos(a) * r, self.y + math.sin(a) * r, self.palette[2], (1 - p) * 0.7)

    def _cloud(self, canvas: PixelCanvas, p: float) -> None:
        r = self.radius * (1.0 + 1.2 * ease_out(p))
        col = mix(self.accent, (60, 90, 40), 0.4)
        for yy in range(int(self.y - r) - 1, int(self.y + r) + 2):
            for xx in range(int(self.x - r) - 1, int(self.x + r) + 2):
                if math.hypot(xx + 0.5 - self.x, yy + 0.5 - self.y) <= r:
                    canvas.blend(xx, yy, col, 0.22 * (1 - p))


class EffectsFactory:
    """Spawns the particle mixes behind muzzle flashes, trails, impacts, ambient flair and wrecks."""

    def __init__(self, particles: ParticleSystem, settings: Settings, rng: random.Random) -> None:
        self.ps, self.settings, self.rng = particles, settings, rng

    def _n(self, base: float) -> int:
        return max(1, int(base * self.settings.particle_density))

    def _burst(self, x: float, y: float, n: int, speed: tuple, life: tuple, c0, c1, gravity: float = 60.0,
               drag: float = 0.4, size: int = 1, alpha: float = 1.0, spread: tuple = (0.1, math.pi - 0.1),
               solid: bool = False, windk: float = 0.0) -> None:
        r = self.rng
        for _ in range(n):
            a, s, life_ = r.uniform(*spread), r.uniform(*speed), r.uniform(*life)
            ca, cb = (c0(), c1()) if callable(c0) else (c0, c1)
            self.ps.emit(Particle(x, y, math.cos(a) * s, math.sin(a) * s, life_, life_, ca, cb, gravity=gravity,
                                  drag=drag, alpha=alpha, size=size, solid=solid, windk=windk))

    def trail(self, x: float, y: float, accent: RGB, ammo: Optional[AmmoType] = None, n: int = 0, t: float = 0.0) -> None:
        life = self.settings.trail_life
        if life <= 0:
            return
        r, ps = self.rng, self.ps
        l = life * r.uniform(0.7, 1.0)
        white = (255, 255, 255)
        style = ammo.trail if ammo else "plain"
        plain = Particle(x, y, 0, 0, l, l, mix(white, accent, 0.5), shade(accent, 0.15), alpha=0.9)
        if style == "plain":
            ps.emit(plain)
        elif style == "dash":
            if n % 4 < 2:
                ps.emit(Particle(x, y, 0, 0, l * 0.8, l * 0.8, white, shade(accent, 0.3)))
        elif style == "glow":
            ps.emit(Particle(x, y, 0, 0, l * 1.1, l * 1.1, mix(accent, white, 0.35), shade(accent, 0.1), alpha=0.55, size=2))
        elif style == "sparks":
            ps.emit(plain)
            if r.random() < 0.5:
                ps.emit(Particle(x, y, r.uniform(-12, 12), r.uniform(-6, 14), 0.5, 0.5, white, shade(accent, 0.3), gravity=60))
        elif style == "embers":
            ps.emit(Particle(x, y, 0, 0, l * 1.4, l * 1.4, mix((255, 200, 120), accent, 0.4), (120, 30, 10), alpha=0.9))
            if r.random() < 0.4:
                ps.emit(Particle(x, y, r.uniform(-4, 4), r.uniform(3, 9), l, l, (255, 190, 100), (90, 20, 8), gravity=-6))
        elif style == "drip":
            ps.emit(Particle(x, y, 0, 0, l, l, mix(accent, white, 0.15), shade(accent, 0.2), alpha=0.9))
            if r.random() < 0.35:
                ps.emit(Particle(x, y, r.uniform(-2, 2), -8, 0.7, 0.7, accent, shade(accent, 0.2), gravity=40))
        elif style == "twinkle":
            c = white if r.random() < 0.5 else accent
            ps.emit(Particle(x + r.uniform(-0.7, 0.7), y + r.uniform(-0.7, 0.7), 0, 0, l * 0.9, l * 0.9, c, shade(accent, 0.2)))
        elif style == "runes":
            ps.emit(Particle(x + r.uniform(-1.2, 1.2), y + r.uniform(-1.2, 1.2), 0, r.uniform(0, 3), l, l,
                             (255, 240, 170) if r.random() < 0.5 else accent, (150, 100, 30), alpha=0.9))
            if r.random() < 0.25:
                ps.emit(Particle(x, y, 0, 0, l * 0.5, l * 0.5, white, accent, size=2, alpha=0.7))
        elif style == "aeon":
            for sgn in (-1, 1):
                ps.emit(Particle(x + sgn * math.sin(t * 14) * 1.6, y, 0, 0, l, l,
                                 (255, 250, 225) if sgn > 0 else (170, 110, 255), (30, 10, 60), alpha=0.8))
        elif style == "tides":
            ps.emit(Particle(x, y, r.uniform(-4, 4), r.uniform(2, 8), l, l, mix((190, 240, 255), accent, 0.3), (10, 60, 110), gravity=40, alpha=0.9))
            if r.random() < 0.3:
                ps.emit(Particle(x, y, 0, 0, l * 0.8, l * 0.8, (230, 250, 255), accent, size=2, alpha=0.5))
        elif style == "cinders":
            ps.emit(Particle(x + r.uniform(-0.8, 0.8), y, r.uniform(-4, 4), r.uniform(2, 12), l * 0.9, l * 0.9, (255, 200, 100), (60, 20, 10),
                             gravity=-12, alpha=0.9, size=2 if r.random() < 0.3 else 1))
            if r.random() < 0.4:
                ps.emit(Particle(x, y, r.uniform(-5, 5), r.uniform(-5, 5), 0.35, 0.35, (44, 22, 22), (10, 5, 5), alpha=0.8))
        elif style == "chrono":
            if n % 3 == 0:
                ps.emit(Particle(x, y, 0, 0, l * 1.4, l * 1.4, (255, 236, 170), (120, 80, 30), size=2, alpha=0.55))
            ps.emit(Particle(x, y, 0, 0, l * 0.6, l * 0.6, white, accent, alpha=0.9))
        elif style == "mist":
            ps.emit(Particle(x, y, r.uniform(-3, 3), r.uniform(-3, 3), l * 1.2, l * 1.2, shade(accent, 0.25), (8, 4, 16), alpha=0.75, size=2))
            if r.random() < 0.3:
                ps.emit(Particle(x, y, 0, 0, l * 0.6, l * 0.6, mix(accent, white, 0.3), shade(accent, 0.2)))
        elif style == "fire":
            ps.emit(Particle(x + r.uniform(-0.6, 0.6), y, r.uniform(-3, 3), r.uniform(4, 14), l * 0.8, l * 0.8,
                             mix((255, 236, 150), accent, 0.3), (120, 26, 8), gravity=-20, alpha=0.9,
                             size=2 if r.random() < 0.4 else 1))
        elif style == "ripple":
            for sgn in (-1, 1):
                ps.emit(Particle(x + sgn * 0.8, y, sgn * 3.5, 0, l, l, mix(accent, white, 0.4), shade(accent, 0.15), alpha=0.6, drag=1.2))
        elif style == "frost":
            ps.emit(Particle(x + r.uniform(-1, 1), y + r.uniform(-1, 1), r.uniform(-2, 2), -4, l * 1.1, l * 1.1,
                             mix((235, 250, 255), accent, 0.3), shade(accent, 0.2), alpha=0.9, gravity=10))
            if r.random() < 0.35:
                ps.emit(Particle(x, y, 0, 0, l * 0.7, l * 0.7, white, accent, size=2, alpha=0.6))
        elif style == "solar":
            ps.emit(Particle(x, y, 0, 0, l * 0.9, l * 0.9, (255, 250, 210), (255, 130, 30), alpha=0.95, size=2))
            a_ = r.uniform(0, math.tau)
            ps.emit(Particle(x, y, math.cos(a_) * 9, math.sin(a_) * 9, 0.4, 0.4, white, (255, 150, 40), drag=2.0))
        elif style == "lava":
            ps.emit(Particle(x, y, r.uniform(-3, 3), 0, l * 0.9, l * 0.9, (255, 170, 60), (70, 16, 8), alpha=0.95, gravity=70,
                             size=2 if r.random() < 0.3 else 1))
        elif style == "arc":
            for _ in range(2):
                ps.emit(Particle(x + r.uniform(-2.6, 2.6), y + r.uniform(-2.6, 2.6), 0, 0, r.uniform(0.1, 0.22), 0.22,
                                 (235, 245, 255), shade(accent, 0.3)))
            ps.emit(plain)
        elif style == "blessing":                            # gold stardust and violet sparks, with a white flare at the core
            for _ in range(2):
                a_ = r.uniform(0, math.tau)
                ps.emit(Particle(x, y, math.cos(a_) * 10, math.sin(a_) * 10, l * 1.4, l * 1.4, (255, 220, 110), (120, 60, 200), alpha=0.95, drag=1.6))
            ps.emit(Particle(x, y, 0, 0, l * 1.1, l * 1.1, (255, 255, 255), (255, 200, 80), size=2, alpha=0.8))
        elif style == "xenon":                               # comet of ions: green-white core motes, violet sparks, rare white flare
            for _ in range(2):
                a_ = r.uniform(0, math.tau)
                ps.emit(Particle(x, y, math.cos(a_) * 9, math.sin(a_) * 9, l * 1.3, l * 1.3, (160, 255, 215), (110, 50, 210), alpha=0.9, drag=1.8))
            ps.emit(Particle(x, y, 0, 0, l, l, (255, 255, 255), (90, 60, 200), size=2, alpha=0.7))
            if r.random() < 0.25:
                ps.emit(Particle(x, y, r.uniform(-14, 14), r.uniform(-14, 14), l * 0.7, l * 0.7, (230, 170, 255), (60, 20, 120), alpha=0.9, drag=2.0))
        elif style == "alien":
            a_ = r.uniform(0, math.tau)
            ps.emit(Particle(x, y, math.cos(a_) * 6, math.sin(a_) * 6 - 2, l * 1.2, l * 1.2, (150, 255, 190), (120, 60, 200), alpha=0.85,
                             drag=1.5))
            if r.random() < 0.3:
                ps.emit(Particle(x, y, 0, 0, l * 0.8, l * 0.8, (210, 150, 255), (60, 20, 120), size=2, alpha=0.6))
        elif style == "code":
            ps.emit(Particle(x, y, 0, -10, l * 1.1, l * 1.1, (150, 255, 175), (8, 56, 22), alpha=0.9))
            if r.random() < 0.4:
                ps.emit(Particle(x + r.uniform(-1, 1), y + 1, 0, -14, l, l, (80, 220, 110), (6, 40, 16), alpha=0.7))
        elif style == "biolume":                             # slow glowing droplets that sink and fade like plankton
            ps.emit(Particle(x, y, 0, 0, l * 1.2, l * 1.2, (150, 255, 236), (10, 50, 90), alpha=0.85))
            if r.random() < 0.45:
                ps.emit(Particle(x + r.uniform(-1, 1), y, r.uniform(-2, 2), r.uniform(-4, -1), l * 1.8, l * 1.8, (90, 220, 230), (10, 40, 70),
                                 alpha=0.7, size=2 if r.random() < 0.2 else 1))
        elif style == "foxfire":
            ps.emit(Particle(x + r.uniform(-0.8, 0.8), y, r.uniform(-2, 2), r.uniform(3, 10), l * 0.9, l * 0.9, (180, 220, 255), (40, 50, 200),
                             gravity=-14, alpha=0.95, size=2 if r.random() < 0.3 else 1))
        elif style == "hardlight":                           # a hard, bright line that lingers, edged in cyan
            ps.emit(Particle(x, y, 0, 0, l * 1.5, l * 1.5, (255, 255, 255), (30, 120, 255), alpha=0.95))
            ps.emit(Particle(x, y + 1, 0, 0, l * 0.9, l * 0.9, (90, 230, 255), (10, 40, 120), alpha=0.5))
        elif style == "paradox":                             # afterimages that alternate between now and then
            c = (255, 255, 255) if n % 2 else (190, 140, 255)
            ps.emit(Particle(x, y, 0, 0, l, l, c, (40, 20, 90), alpha=0.85))
            if n % 5 == 0:
                ps.emit(Particle(x, y, 0, 0, l * 1.6, l * 1.6, (150, 110, 255), (20, 10, 50), size=2, alpha=0.4))
        elif style == "atomic":
            ps.emit(Particle(x, y, 0, 0, l, l, (210, 240, 255), (30, 60, 160), alpha=0.9, size=2 if n % 3 == 0 else 1))
            if r.random() < 0.5:
                a_ = r.uniform(0, math.tau)
                ps.emit(Particle(x, y, math.cos(a_) * 12, math.sin(a_) * 12, 0.25, 0.25, (255, 255, 255), (80, 140, 255), drag=2.0))
        elif style == "spores":
            ps.emit(Particle(x + r.uniform(-1, 1), y + r.uniform(-1, 1), r.uniform(-3, 3), r.uniform(-1, 4), l * 1.6, l * 1.6,
                             (180, 255, 214), (40, 110, 90), alpha=0.75, windk=0.6))
        elif style == "sand":
            ps.emit(Particle(x, y, r.uniform(-3, 3), r.uniform(-2, 3), l, l, (230, 196, 130), (120, 84, 46), gravity=50, alpha=0.9))
            if r.random() < 0.3:
                ps.emit(Particle(x, y, r.uniform(-4, 4), r.uniform(2, 6), l * 1.4, l * 1.4, (200, 170, 120), (90, 70, 50), size=2, alpha=0.4, windk=0.8))
        elif style == "feathers":
            c = (60, 220, 150) if n % 3 else (230, 70, 60)
            ps.emit(Particle(x + r.uniform(-1, 1), y, r.uniform(-3, 3), r.uniform(-4, 1), l * 1.4, l * 1.4, c, shade(c, 0.3), alpha=0.9, windk=0.7))
        elif style == "constellation":                       # a dotted line of stars: every fourth step a bright one
            if n % 4 == 0:
                ps.emit(Particle(x, y, 0, 0, l * 2.0, l * 2.0, (255, 250, 220), (90, 110, 230), alpha=0.95, size=2))
            elif n % 2 == 0:
                ps.emit(Particle(x, y, 0, 0, l * 1.3, l * 1.3, (220, 190, 120), (40, 40, 110), alpha=0.6))
        elif style == "ghostfire":
            ps.emit(Particle(x + r.uniform(-0.6, 0.6), y, r.uniform(-2, 2), r.uniform(3, 10), l * 0.9, l * 0.9, (200, 255, 220), (20, 80, 50),
                             gravity=-12, alpha=0.9, size=2 if r.random() < 0.35 else 1))
            if r.random() < 0.3:
                ps.emit(Particle(x, y, r.uniform(-3, 3), r.uniform(-1, 3), l * 2, l * 2, (120, 150, 140), (20, 30, 30), size=2, alpha=0.35, windk=0.8))
        elif style == "prism":
            c = hsv(t * 0.8 + n * 0.05, 0.65, 1.0)
            ps.emit(Particle(x, y, 0, 0, l * 1.1, l * 1.1, c, shade(c, 0.15), alpha=0.95))
            if r.random() < 0.4:
                ps.emit(Particle(x + r.uniform(-1.5, 1.5), y + r.uniform(-1.5, 1.5), 0, 0, l * 0.6, l * 0.6, white, c))
        else:
            ps.emit(plain)

    def muzzle(self, x: float, y: float, angle: float, accent: RGB) -> None:
        r = self.rng
        for _ in range(self._n(12)):
            a = math.radians(angle + r.uniform(-18, 18))
            s = r.uniform(20, 55)
            self.ps.emit(Particle(x, y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.15, 0.4), 0.4,
                                  (255, 250, 220), shade(accent, 0.3), drag=3.0))

    def smoke(self, x: float, y: float, n: int = 1, spread: float = 2.0, tint: Optional[RGB] = None) -> None:
        r = self.rng
        c0 = mix((118, 118, 126), tint, 0.6) if tint else (118, 118, 126)
        for _ in range(n):
            life = r.uniform(1.2, 2.4)
            self.ps.emit(Particle(x + r.uniform(-spread, spread), y, r.uniform(-4, 4), r.uniform(5, 14), life, life,
                                  c0, (34, 36, 44), gravity=-4, drag=0.8, alpha=0.55, size=2, windk=0.8))

    def impact(self, x: float, y: float, accent: RGB, soil: RGB, scale: float = 1.0,
               ammo: Optional[AmmoType] = None) -> None:
        r = self.rng
        style = ammo.boom if ammo else "classic"
        spark_c0 = mix((255, 255, 255), accent, 0.4)
        self._burst(x, y, self._n(46 * scale), (14 * scale, 55 * scale), (0.5, 1.1), spark_c0, shade(accent, 0.2),
                    gravity=70, drag=0.4)
        for _ in range(self._n(22 * scale)):
            a, s = r.uniform(0.3, math.pi - 0.3), r.uniform(10, 38) * scale
            life = r.uniform(0.8, 1.5)
            c = shade(soil, r.uniform(0.7, 1.2))
            self.ps.emit(Particle(x, y, math.cos(a) * s, math.sin(a) * s, life, life, c, shade(c, 0.5), gravity=90, solid=True))
        tint = accent if style in ("cloud", "implode") else None
        self.smoke(x, y + 1, self._n(16 * scale), 3.0 * scale, tint)
        if style == "cloud":
            self._burst(x, y + 1, self._n(26 * scale), (2, 9), (2.0, 3.5), mix(accent, (60, 90, 40), 0.3), (20, 30, 18),
                        gravity=-3, drag=0.8, size=2, alpha=0.5, windk=0.8)
        elif style == "embers":
            self._burst(x, y, self._n(30 * scale), (10, 40), (1.2, 2.2), (255, 190, 110), (120, 30, 10), gravity=30)
        elif style == "fire":
            self._burst(x, y, self._n(36 * scale), (15, 45), (0.5, 1.1), mix((255, 230, 140), accent, 0.25), (120, 26, 8),
                        gravity=-10, drag=0.6, size=2, spread=(1.0, 2.1))
        elif style in ("prism", "bloom"):
            self._burst(x, y, self._n(50 * scale), (14, 60), (0.7, 1.4), lambda: hsv(r.random(), 0.6, 1.0), lambda: (40, 30, 70),
                        gravity=40, drag=0.5)
        elif style == "cluster":
            self._burst(x, y, self._n(24 * scale), (30, 80), (0.3, 0.45), (255, 255, 255), shade(accent, 0.3), gravity=20)
        elif style == "implode":
            self._burst(x, y, self._n(24 * scale), (8, 30), (1.0, 1.8), shade(accent, 0.3), (10, 4, 20), gravity=20,
                        size=2, alpha=0.8)
        elif style in ("rays", "starrays"):
            self._burst(x, y, self._n(30 * scale), (30, 70), (0.5, 0.9), (255, 255, 255), shade(accent, 0.3), gravity=40)
        elif style == "shock":
            self._burst(x, y, self._n(26 * scale), (25, 60), (0.4, 0.8), (255, 255, 255), shade(accent, 0.3), gravity=30, drag=1.0)
        elif style == "shatter":
            self._burst(x, y, self._n(40 * scale), (20, 75), (0.6, 1.2), (240, 252, 255), shade(accent, 0.4), gravity=55, drag=0.3)
        elif style == "nova":
            self._burst(x, y, self._n(44 * scale), (20, 80), (0.6, 1.3), (255, 250, 220), (255, 120, 30), gravity=-6, drag=0.9,
                        spread=(0.0, math.pi))
        elif style == "sigil":
            self._burst(x, y, self._n(40 * scale), (18, 64), (0.7, 1.4), (255, 240, 180), (150, 90, 20), gravity=10, drag=0.7, size=2)
        elif style == "eclipse":
            self._burst(x, y, self._n(34 * scale), (10, 44), (0.8, 1.6), (255, 220, 120), (40, 12, 90), gravity=-8, drag=0.6, size=2)
        elif style == "tidal":
            self._burst(x, y, self._n(46 * scale), (16, 58), (0.7, 1.3), (200, 245, 255), (10, 50, 120), gravity=60, drag=0.4)
        elif style == "cinderstorm":
            self._burst(x, y, self._n(44 * scale), (14, 56), (1.0, 1.8), (255, 190, 90), (70, 16, 8), gravity=45, size=2)
        elif style == "rewind":
            self._burst(x, y, self._n(36 * scale), (8, 36), (0.9, 1.6), (255, 240, 200), (60, 30, 140), gravity=-14, drag=0.8, size=2)
        elif style == "magma":
            self._burst(x, y, self._n(36 * scale), (14, 52), (1.0, 1.9), (255, 190, 80), (120, 24, 8), gravity=85, size=2,
                        solid=True, spread=(0.5, math.pi - 0.5))
            self._burst(x, y, self._n(16 * scale), (6, 22), (1.4, 2.4), (255, 140, 40), (60, 16, 8), gravity=-8, drag=0.7)
        elif style == "thunder":
            self._burst(x, y, self._n(34 * scale), (40, 95), (0.2, 0.45), (235, 245, 255), shade(accent, 0.3), gravity=10, drag=1.5)
        elif style == "code":
            self._burst(x, y, self._n(34 * scale), (10, 48), (0.7, 1.4), (150, 255, 175), (8, 56, 22), gravity=45, drag=0.5, size=2)
        elif style == "blessing":
            self._burst(x, y, self._n(60 * scale), (14, 70), (0.9, 1.9), (255, 226, 120), (150, 90, 230), gravity=-6, drag=0.9, size=2)
            self._burst(x, y, self._n(30 * scale), (30, 90), (0.5, 1.2), (255, 255, 255), (255, 200, 80), gravity=0, drag=1.4, size=1)
            for k in range(20):
                a_ = k * math.tau / 20
                self.ps.emit(Particle(x, y, math.cos(a_) * 52, math.sin(a_) * 52, 1.0, 1.0, (255, 236, 160), (176, 120, 255), alpha=0.95, drag=1.5))
        elif style == "xenon":
            self._burst(x, y, self._n(46 * scale), (12, 58), (0.9, 1.8), (170, 255, 215), (120, 60, 220), gravity=-10, drag=0.8, size=2)
            self._burst(x, y, self._n(26 * scale), (30, 80), (0.5, 1.1), (255, 255, 255), (170, 110, 255), gravity=0, drag=1.4, size=1)
            for k in range(16):                              # a ring of ions flung outward
                a_ = k * math.tau / 16
                self.ps.emit(Particle(x, y, math.cos(a_) * 44, math.sin(a_) * 44, 0.9, 0.9, (190, 255, 230), (110, 60, 220), alpha=0.9, drag=1.6))
        elif style == "alien":
            self._burst(x, y, self._n(40 * scale), (12, 52), (0.8, 1.6), (150, 255, 200), (110, 50, 200), gravity=-10, drag=0.8, size=2)
        elif style == "biolume":
            self._burst(x, y, self._n(40 * scale), (6, 30), (1.6, 2.8), (150, 255, 236), (10, 50, 90), gravity=-4, drag=0.9, alpha=0.85)
        elif style == "foxfire":
            self._burst(x, y, self._n(40 * scale), (10, 40), (0.7, 1.4), (200, 230, 255), (40, 50, 200), gravity=-22, drag=0.6, size=2)
        elif style == "hardlight":
            self._burst(x, y, self._n(34 * scale), (40, 110), (0.25, 0.5), (255, 255, 255), (40, 160, 255), gravity=0, drag=1.2)
        elif style == "paradox":
            self._burst(x, y, self._n(36 * scale), (20, 60), (0.6, 1.2), (255, 255, 255), (140, 90, 240), gravity=0, drag=1.4)
            self._burst(x, y, self._n(20 * scale), (2, 10), (1.0, 1.8), (200, 170, 255), (30, 10, 70), gravity=-6, size=2, alpha=0.6)
        elif style == "atomic":
            self._burst(x, y, self._n(50 * scale), (30, 90), (0.5, 1.0), (230, 245, 255), (40, 80, 200), gravity=10, drag=1.0)
            self._burst(x, y, self._n(26 * scale), (6, 22), (1.4, 2.4), (170, 200, 230), (30, 40, 70), gravity=-12, drag=0.6, size=2, alpha=0.6)
        elif style == "spore":
            self._burst(x, y, self._n(44 * scale), (6, 28), (1.8, 3.0), lambda: r.choice(((190, 255, 220), (255, 190, 220))), lambda: (40, 90, 70),
                        gravity=-3, drag=0.9, alpha=0.85, windk=0.7)
        elif style == "eruption":
            self._burst(x, y, self._n(56 * scale), (20, 70), (0.8, 1.6), (240, 200, 130), (110, 80, 50), gravity=70, solid=True, size=2,
                        spread=(1.2, 1.95))
        elif style == "jade":
            self._burst(x, y, self._n(40 * scale), (14, 50), (0.7, 1.4), lambda: r.choice(((60, 220, 150), (250, 214, 120), (230, 70, 60))),
                        lambda: (14, 60, 40), gravity=30, drag=0.6)
        elif style == "zodiac":
            self._burst(x, y, self._n(36 * scale), (16, 60), (0.7, 1.5), (255, 240, 190), (60, 70, 200), gravity=-4, drag=0.9)
        elif style == "ghostfire":
            self._burst(x, y, self._n(44 * scale), (10, 40), (0.6, 1.3), (200, 255, 220), (20, 90, 50), gravity=-18, drag=0.6, size=2)

    def ambient(self, design: TankDesign, x: float, y: float, body: RGB, dt: float) -> None:
        for kind in design.ambient.split("+"):
            if kind not in ("none", "sparkle", "orbit", "lightning"):
                self._ambient_one(kind, x, y, body, dt)

    def _ambient_one(self, kind: str, x: float, y: float, body: RGB, dt: float) -> None:
        r = self.rng
        rate = {"fire": 15.0, "burn": 15.0, "smoke": 7.0, "prism": 9.0, "ghostfire": 12.0, "radiation": 9.0, "sand": 10.0}.get(kind, 6.0)
        if r.random() > dt * rate * self.settings.particle_density:
            return
        if kind == "burn":                                   # a burning machine: flames, smoke and embers together
            for k in ("fire", "smoke", "embers"):
                self._ambient_one(k, x, y, body, 1e9)
            return
        if kind == "sparks":
            self.ps.emit(Particle(x + r.uniform(-4, 4), y + 6, r.uniform(-8, 8), r.uniform(10, 24), 0.5, 0.5,
                                  (255, 230, 120), (255, 120, 20), gravity=40))
        elif kind == "embers":
            self.ps.emit(Particle(x + r.uniform(-4, 4), y + 5, r.uniform(-3, 3), r.uniform(6, 14), 1.2, 1.2,
                                  (255, 150, 40), (80, 20, 10), gravity=-8, alpha=0.9))
        elif kind == "mist":
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + 2, r.uniform(-3, 3), r.uniform(2, 6), 1.8, 1.8,
                                  (150, 110, 230), (20, 10, 40), alpha=0.45, size=2, windk=0.5))
        elif kind == "static":
            a_ = r.uniform(0, math.tau)
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + r.uniform(2, 8), math.cos(a_) * 14, math.sin(a_) * 14, 0.16, 0.16,
                                  (235, 245, 255), (90, 150, 255), drag=2.0))
        elif kind == "frost":
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + 8, r.uniform(-3, 3), r.uniform(-6, -2), 1.6, 1.6,
                                  (235, 250, 255), (120, 170, 220), alpha=0.8, windk=0.6))
        elif kind == "flare":
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + 6, r.uniform(-4, 4), r.uniform(8, 18), 1.0, 1.0,
                                  (255, 244, 190), (255, 130, 30), alpha=0.9, gravity=-6))
        elif kind == "bits":
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + 7, 0, r.uniform(6, 14), 0.9, 0.9,
                                  (150, 255, 175), (8, 56, 22), alpha=0.9))
        elif kind == "fire":                                 # flame tongues licking up from the hull
            self.ps.emit(Particle(x + r.uniform(-4.5, 4.5), y + r.uniform(3, 6), r.uniform(-3, 3), r.uniform(14, 26), 0.55, 0.55,
                                  (255, 214, 90), (200, 30, 8), gravity=-24, alpha=0.95, size=2 if r.random() < 0.35 else 1))
        elif kind == "smoke":                                # dark smoke drifting up and away on the wind
            self.ps.emit(Particle(x + r.uniform(-4, 4), y + 7, r.uniform(-3, 3), r.uniform(5, 11), 2.2, 2.2,
                                  (88, 86, 92), (18, 18, 22), gravity=-4, alpha=0.55, size=2, windk=0.9))
        elif kind == "prism":                                # rainbow dust shed by a crystal
            c = hsv(r.random(), 0.5, 1.0)
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + r.uniform(1, 7), r.uniform(-4, 4), r.uniform(3, 10), 1.1, 1.1,
                                  c, shade(c, 0.2), alpha=0.9, gravity=-3))
        elif kind == "void":
            self.ps.emit(Particle(x + r.uniform(-6, 6), y + r.uniform(1, 8), r.uniform(-3, 3), r.uniform(-2, 4), 1.4, 1.4,
                                  (150, 90, 240), (10, 4, 24), alpha=0.7, size=2, windk=0.2))
        elif kind == "bubbles":
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + 2, r.uniform(-2, 2), r.uniform(5, 12), 1.5, 1.5,
                                  (190, 235, 255), (90, 150, 220), alpha=0.7, windk=0.4))
        elif kind == "petals":
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + 8, r.uniform(-5, 5), r.uniform(-6, -1), 1.8, 1.8,
                                  (255, 170, 200), (200, 80, 130), alpha=0.85, windk=0.8))
        elif kind == "radiation":                            # blue-white atomic sparks rising off the plates
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + r.uniform(5, 8), r.uniform(-2, 2), r.uniform(8, 18), 0.9, 0.9,
                                  (210, 240, 255), (40, 80, 170), gravity=-10, alpha=0.9))
        elif kind == "spores":                               # glowing spores drifting up and wandering
            self.ps.emit(Particle(x + r.uniform(-6, 6), y + r.uniform(4, 9), r.uniform(-3, 3), r.uniform(2, 6), 2.6, 2.6,
                                  (200, 255, 220), (40, 140, 110), gravity=-1.5, alpha=0.85, windk=0.7))
        elif kind == "sand":                                 # sand pouring off the rings
            self.ps.emit(Particle(x + r.choice((-5, 5)) + r.uniform(-1, 1), y + r.uniform(1, 5), r.uniform(-4, 4), r.uniform(-2, 4), 0.9, 0.9,
                                  (226, 190, 120), (130, 90, 50), gravity=40, alpha=0.8))
        elif kind == "feathers":                             # quetzal feathers spiralling down
            c = r.choice(((60, 220, 150), (40, 170, 210), (230, 60, 60)))
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + 9, r.uniform(-6, 6), r.uniform(-5, -1), 2.2, 2.2,
                                  c, shade(c, 0.4), alpha=0.85, windk=0.9))
        elif kind == "ghostfire":                            # green ghost-flame licking up from the hull
            self.ps.emit(Particle(x + r.uniform(-5, 5), y + r.uniform(2, 5), r.uniform(-2, 2), r.uniform(10, 18), 0.6, 0.6,
                                  (200, 255, 220), (20, 90, 50), gravity=-16, alpha=0.9, size=2 if r.random() < 0.3 else 1))

    def tank_debris(self, x: float, y: float, color: RGB) -> None:
        r = self.rng
        for _ in range(self._n(40)):
            a, s = r.uniform(0.2, math.pi - 0.2), r.uniform(12, 50)
            life = r.uniform(1.0, 2.0)
            c = r.choice((color, shade(color, 0.5), (36, 38, 44)))
            self.ps.emit(Particle(x, y, math.cos(a) * s, math.sin(a) * s, life, life, c, shade(c, 0.4), gravity=80,
                                  solid=True, size=2))
