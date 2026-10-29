"""draw_tank(): a design painted with its colours, materials, glow animation, ambient particles and hover thrusters."""
from __future__ import annotations

import math
from typing import Optional

from tanks.art.barrels import barrel_color, barrel_spec
from tanks.art.materials import MATERIALS
from tanks.colors import RGB, clamp, flicker, gradient, hsv, mix, shade
from tanks.config import PIVOT_H, TANK_H, TANK_W
from tanks.content.paints import PAINT_PX, PIXEL_PAINTS, RAINBOW, live_color, paint_shade, void_px
from tanks.content.tanks import DEFAULT_DESIGN, TankDesign
from tanks.screen import PixelCanvas


# Glow styles recolour the 'l' pixels; ambient kinds are particle / overlay flavours (combine with '+').
GLOW_STYLES = ("none", "pulse", "blink", "flame", "prism", "scan", "plasma", "lava", "storm", "matrix",
               "refract", "ember", "void", "ice", "toxic", "neon", "gold", "aeon",
               "biolume", "foxfire", "hologlitch", "phase", "atomic", "spore", "maw", "jade", "zodiac", "ghost")
AMBIENT_KINDS = ("none", "sparks", "embers", "mist", "sparkle", "static", "frost", "flare", "bits",
                 "smoke", "fire", "burn", "prism", "orbit", "void", "lightning", "bubbles", "petals", "halo", "glyphs", "riftmotes",
                 "lure", "tails", "foxfire", "scanlines", "hypercube", "radiation", "spores", "sand", "feathers", "constellation",
                 "sails", "ghostfire")


def _glow_color(design: TankDesign, body: RGB, t: float, idx: int) -> RGB:
    g, a = design.glow, design.accent
    if g == "aeon":
        return gradient(((0, (90, 40, 190)), (0.5, (255, 214, 120)), (1, (255, 255, 244))), 0.5 + 0.5 * math.sin(t * 3.2 + idx * 0.8))
    if g == "biolume":
        return mix((20, 90, 140), (160, 255, 240), max(0.0, math.sin(t * 3 - idx * 0.8)) ** 2)
    if g == "foxfire":
        return gradient(((0, (50, 70, 210)), (0.5, (110, 190, 255)), (1, (240, 252, 255))), 0.5 + 0.5 * math.sin(t * 15 + idx * 1.9))
    if g == "hologlitch":
        return (255, 70, 210) if flicker(t, idx, 31) > 0.9 else mix((40, 140, 220), (200, 255, 255), 0.5 + 0.5 * math.sin(t * 9 + idx))
    if g == "phase":
        return hsv(0.70 + 0.12 * math.sin(t * 2.2 + idx * 0.6), 0.55, 1.0)
    if g == "atomic":
        k = 0.5 + 0.5 * math.sin(t * 2.6)
        return mix((50, 110, 210), (235, 250, 255), k ** 3)
    if g == "spore":
        return mix((40, 150, 110), (190, 255, 220), 0.5 + 0.5 * math.sin(t * 2 + idx * 1.4))
    if g == "maw":
        return gradient(((0, (120, 30, 10)), (0.6, (255, 120, 40)), (1, (255, 230, 160))), 0.5 + 0.5 * math.sin(t * 7 + idx * 1.1))
    if g == "jade":
        k = max(0.0, 1 - abs(idx - ((t * 5) % 15 - 2)) / 2.5)
        return mix((40, 170, 110), (255, 226, 130), k)
    if g == "zodiac":
        return (255, 250, 220) if (int(t * 2) + idx) % 5 == 0 else mix((90, 110, 220), (255, 214, 130), 0.5 + 0.5 * math.sin(t * 2 + idx))
    if g == "ghost":
        return mix((30, 90, 60), (160, 255, 190), 0.5 + 0.5 * math.sin(t * 5 + idx * 0.9) * math.sin(t * 2.3))
    if g == "pulse":
        return mix(shade(a, 0.3), a, 0.5 + 0.5 * math.sin(t * 4 + idx))
    if g == "blink":
        return a if int(t * 3 + idx) % 2 == 0 else shade(a, 0.25)
    if g == "flame":
        k = 0.5 + 0.5 * math.sin(t * 23 + idx * 2.1) * math.sin(t * 11 + idx)
        return gradient(((0, (120, 30, 10)), (0.5, (255, 120, 20)), (1, (255, 232, 130))), k)
    if g == "prism":
        return hsv(t * 0.4 + idx * 0.13, 0.7, 1.0)
    if g == "scan":          # a bright bar sweeping along the visor
        k = max(0.0, 1 - abs(idx - ((t * 9) % 15 - 2)) / 2.5)
        return mix(mix(shade(a, 0.28), a, 0.35), (255, 255, 255), k * 0.85)
    if g == "plasma":
        return gradient(((0, (255, 90, 20)), (0.5, a), (1, (255, 250, 205))), 0.5 + 0.5 * math.sin(t * 4.5 + idx * 0.7))
    if g == "lava":
        k = clamp(0.5 + 0.4 * math.sin(t * 2.2 + idx * 1.7) + 0.2 * (flicker(t, idx, 3) - 0.5), 0, 1)
        return gradient(((0, (90, 10, 6)), (0.6, (230, 70, 18)), (1, (255, 196, 80))), k)
    if g == "storm":
        f = flicker(t, idx, 5)
        return mix(shade(a, 0.22), (235, 245, 255), 0.85) if f > 0.86 else mix(shade(a, 0.22), a, f * 0.6)
    if g == "matrix":
        return (96, 255, 130) if flicker(t, idx, 9) > 0.5 else (18, 96, 44)
    if g == "refract":       # prism light with white glints sweeping through it
        k = max(0.0, 1 - abs(idx - ((t * 8) % 16 - 2)) / 2.0)
        return mix(hsv(t * 0.4 + idx * 0.09, 0.6, 1.0), (255, 255, 255), k * 0.8)
    if g == "ember":
        return gradient(((0, (110, 14, 8)), (0.6, (230, 60, 20)), (1, (255, 190, 90))),
                        clamp(0.5 + 0.35 * math.sin(t * 2.6 + idx * 1.3) + 0.3 * (flicker(t, idx, 7) - 0.5), 0, 1))
    if g == "void":
        return mix((10, 4, 24), a, 0.5 + 0.5 * math.sin(t * 3 + idx * 0.9))
    if g == "ice":
        return mix(shade(a, 0.5), (240, 252, 255), 0.5 + 0.5 * math.sin(t * 2.4 + idx * 0.8))
    if g == "toxic":
        return mix((20, 70, 20), (170, 255, 60), 0.5 + 0.5 * math.sin(t * 5 + idx * 1.1))
    if g == "neon":
        return (255, 70, 220) if (int(t * 4) + idx) % 2 == 0 else (60, 240, 255)
    if g == "gold":
        k = max(0.0, 1 - abs(idx - ((t * 6) % 15 - 2)) / 2.5)
        return mix((190, 140, 40), (255, 244, 170), k)
    return mix(body, (255, 255, 255), 0.6)


def draw_tank(canvas: PixelCanvas, x: float, y: float, facing: int, angle: float, body: RGB, scale: int = 1,
              flash: float = 0.0, wreck: bool = False, recoil: float = 0.0,
              design: TankDesign = DEFAULT_DESIGN, t: float = 0.0, lift: Optional[float] = None,
              hover: Optional[float] = None) -> None:
    """Draws a tank whose base is at (x, y). `lift` is extra height added here (None = the design's own hover, which is
    what previews want; battles pass 0 because the simulated tank already floats). `hover` is how far the body is
    above the ground, used for the shadow and thruster (None = same as lift)."""
    paint = body if (body in PIXEL_PAINTS and not wreck) else None
    galaxy_on = paint is not None                                 # per-pixel paint (ASTRAL / PRISMATIC / VOID) overrides a design's own paint
    if galaxy_on:
        body = live_color(paint, t)
    elif design.paint is not None:
        body = design.paint
    elif body == RAINBOW:
        body = live_color(body, t)
    lift = design.hover if lift is None else lift
    air = lift if hover is None else hover
    ground_y = y
    if air > 0 and not wreck:
        bob = 0.6 * math.sin(t * 2.4) * scale
        y = y + lift + bob
        ground_y = y - air * scale - bob if hover is not None else y - lift - bob
    elif lift:
        y = y + lift
    if air > 0 and not wreck:                                  # soft shadow on the ground + thruster glow under the hull
        sh = clamp(1.0 - air * scale / 16.0, 0.35, 0.9)
        for dx in range(int(-5.5 * scale), int(5.5 * scale) + 1):
            k = 1 - abs(dx) / (5.5 * scale)
            canvas.blendf(x + dx, ground_y, (0, 0, 0), 0.55 * sh * k)
        for k in range(3):
            canvas.blendf(x + (k - 1) * 2 * scale, y - 1, design.accent, 0.35 + 0.25 * math.sin(t * 17 + k * 2))
    if wreck:
        pal = {"t": (34, 34, 38), "h": (28, 28, 32), "g": (44, 40, 40), "k": (18, 18, 20), "w": (30, 30, 34),
               "d": (20, 20, 22), "a": (44, 40, 38), "l": (62, 34, 22)}
    else:
        pal = {"t": mix(body, (255, 255, 255), 0.28), "h": body, "g": mix(body, (255, 255, 255), 0.5),
               "k": mix(shade(body, 0.3), (36, 40, 48), 0.5), "w": mix(body, (200, 210, 220), 0.3),
               "d": shade(body, 0.38), "a": design.accent}
    if flash > 0:
        pal = {k: mix(v, (255, 255, 255), flash) for k, v in pal.items()}
    if not wreck:
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        spec = barrel_spec(design.barrel)
        px, py = x, y + PIVOT_H * scale
        length = (spec.length - recoil * 2.5) * scale
        base = mix(body, (225, 232, 240), 0.4)
        if flash > 0:
            base = mix(base, (255, 255, 255), flash)
        for lane, off in enumerate(spec.offsets):
            for k in range(int(length * 2) + 1):
                d = k * 0.5
                bx, by = px + d * ca - off * scale * sa, py + d * sa + off * scale * ca
                col = barrel_color(spec.style, base, design.accent, t, d, lane)
                for ox in range(scale):
                    for oy in range(scale):
                        canvas.plotf(bx + ox * 0.9 - (scale - 1) * 0.45, by + oy * 0.9 - (scale - 1) * 0.45, col)
        canvas.plotf(px + length * ca, py + length * sa, mix(base, (255, 255, 255), 0.6))
    base_x, base_y = int(x // 1) - 5 * scale, int(round(y))
    for r, row in enumerate(design.mask):
        if wreck and r < 2 and (r == 0 or facing > 0):
            continue
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            cc = c if facing > 0 else TANK_W - 1 - c
            if ch == "l" and not wreck:
                col = _glow_color(design, body, t, cc)
            elif ch in MATERIALS and not wreck:
                col = MATERIALS[ch](body, design.accent, t, cc, r, flash)
            elif galaxy_on and ch in "thgkwd":
                gb = PAINT_PX.get(paint, void_px)(t, cc, r)
                col = paint_shade(paint, gb, ch)
            else:
                col = pal.get(ch, pal["h"])
            if flash > 0 and (ch == "l" or ch in MATERIALS) and not wreck:
                col = mix(col, (255, 255, 255), flash)
            wx, wy = base_x + cc * scale, base_y + (TANK_H - 1 - r) * scale
            for ox in range(scale):
                for oy in range(scale):
                    canvas.plot(wx + ox, wy + oy, col)
    if not wreck:
        _draw_ambient_overlay(canvas, x, y, scale, design, t)


def _draw_ambient_overlay(canvas: PixelCanvas, x: float, y: float, scale: int, design: TankDesign, t: float) -> None:
    """Draw-time halves of the ambient kinds (twinkles, orbiting motes, arcs). Particle halves live in EffectsFactory."""
    kinds = design.ambient.split("+")
    if "halo" in kinds:                                      # a slowly turning ring of gold light over the turret
        for i in range(14):
            ang = t * 1.2 + i * math.tau / 14
            hx, hy = x + math.cos(ang) * 6.5 * scale, y + 9 * scale + math.sin(ang) * 1.6 * scale
            canvas.blendf(hx, hy, (255, 232, 150), 0.35 + 0.5 * (0.5 + 0.5 * math.sin(ang * 2 - t * 4)))
    if "glyphs" in kinds:                                    # tiny rune crosses drifting around the hull
        for i in range(4):
            ang = -t * 0.9 + i * math.pi / 2
            gx, gy = x + math.cos(ang) * 8.5 * scale, y + 4 * scale + math.sin(ang) * 3.2 * scale
            a_ = 0.45 + 0.45 * math.sin(t * 5 + i * 1.9)
            canvas.blendf(gx, gy, design.accent, a_)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                canvas.blendf(gx + dx, gy + dy, design.accent, a_ * 0.4)
    if "lure" in kinds:                                      # the angler's lure: a bending stalk and a glowing bulb
        sw = math.sin(t * 1.3) * 2.6
        for k in range(10):
            f = k / 9
            canvas.blendf(x + sw * f * f * scale, y + (6 + 4.5 * f) * scale, (40, 90, 120), 0.75)
        bx, by = x + sw * scale, y + 10.5 * scale
        glow = 0.6 + 0.4 * math.sin(t * 4.2)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= 3.2:
                    canvas.blendf(bx + dx, by + dy, (150, 255, 240) if d < 1.2 else (60, 200, 220), (1 - d / 3.4) * glow)
        canvas.plotf(bx, by, (240, 255, 255))
    if "tails" in kinds:                                     # nine spectral tails fanning up behind the fox
        for i in range(9):
            base_a = math.radians(28 + i * 15.5)
            n_ = 12 * scale
            for s in range(2, n_ + 1):
                f = s / n_
                a_ = base_a + 0.35 * math.sin(t * 2.2 + i * 0.7 + f * 2.5) * f
                tx_, ty_ = x + math.cos(a_) * f * 11 * scale, y + 3 * scale + math.sin(a_) * f * 9.5 * scale
                col = gradient(((0, (236, 232, 246)), (0.55, (120, 180, 255)), (1, (235, 250, 255))), f)
                canvas.blendf(tx_, ty_, col, 0.7 * (1 - f * 0.45))
                if f > 0.7:                                   # the tail tips flare into foxfire
                    canvas.blendf(tx_ + math.cos(a_ + 1.6), ty_ + math.sin(a_ + 1.6), (120, 190, 255), 0.35)
    if "foxfire" in kinds:                                   # three wisps of blue flame circling
        for i in range(3):
            ang = t * 1.8 + i * math.tau / 3
            fx_, fy_ = x + math.cos(ang) * 8.5 * scale, y + 4 * scale + math.sin(ang) * 2.6 * scale
            fl = 0.6 + 0.4 * flicker(t, i, 3)
            canvas.blendf(fx_, fy_, (240, 252, 255), 0.95 * fl)
            canvas.blendf(fx_, fy_ + 1, (110, 190, 255), 0.8 * fl)
            canvas.blendf(fx_, fy_ + 2, (60, 90, 230), 0.5 * fl)
            canvas.blendf(fx_ - 1, fy_, (90, 160, 255), 0.4 * fl)
            canvas.blendf(fx_ + 1, fy_, (90, 160, 255), 0.4 * fl)
    if "scanlines" in kinds:                                 # hologram scan bars rising, and the odd torn slice
        for k in range(2):
            sy = y + ((t * 6 + k * 4) % 9) * scale
            for dx in range(-6 * scale, 6 * scale + 1):
                canvas.blendf(x + dx, sy, (120, 240, 255), 0.22)
        if flicker(t * 0.5, 7, 11) > 0.8:
            gy = y + int(flicker(t, 3, 5) * 6) * scale
            for dx in range(-5 * scale, 5 * scale + 1, 2):
                canvas.blendf(x + dx + 2, gy, (255, 70, 210), 0.5)
    if "hypercube" in kinds:                                 # a rotating tesseract: two wire cubes, joined corner to corner
        cx_, cy_ = x, y + 4.5 * scale
        ay, ax_ = t * 0.9, t * 0.55
        pts = []
        for s_ in (7.5, 4.0):
            ring = []
            for vx_ in (-1, 1):
                for vy_ in (-1, 1):
                    for vz_ in (-1, 1):
                        X, Y, Z = vx_ * s_ * 0.5, vy_ * s_ * 0.5, vz_ * s_ * 0.5
                        ang = ay * (1 if s_ > 5 else -1.6)
                        X, Z = X * math.cos(ang) - Z * math.sin(ang), X * math.sin(ang) + Z * math.cos(ang)
                        Y, Z = Y * math.cos(ax_) - Z * math.sin(ax_), Y * math.sin(ax_) + Z * math.cos(ax_)
                        ring.append((cx_ + X * scale * 1.5, cy_ + Y * scale * 1.2))
            pts.append(ring)
        def _line(p, q, col, a_):
            n_ = int(max(abs(q[0] - p[0]), abs(q[1] - p[1]))) + 1
            for j in range(n_ + 1):
                canvas.blendf(p[0] + (q[0] - p[0]) * j / n_, p[1] + (q[1] - p[1]) * j / n_, col, a_)
        edges = [(i, j) for i in range(8) for j in range(i + 1, 8) if bin(i ^ j).count("1") == 1]
        for i, j in edges:
            _line(pts[0][i], pts[0][j], (200, 160, 255), 0.55)
            _line(pts[1][i], pts[1][j], (255, 255, 255), 0.45)
        for i in range(8):
            _line(pts[0][i], pts[1][i], (140, 100, 240), 0.3)
    if "constellation" in kinds:                             # twelve zodiac stars turning round the astrolabe, joined by gold lines
        prev = None
        for i in range(13):
            ang = t * 0.4 + (i % 12) * math.tau / 12
            rr = (9.5 + 1.2 * math.sin(i * 2.7)) * scale
            sx, sy = x + math.cos(ang) * rr, y + 4 * scale + math.sin(ang) * rr * 0.42
            if prev is not None:
                for j in range(1, 6):
                    canvas.blendf(prev[0] + (sx - prev[0]) * j / 6, prev[1] + (sy - prev[1]) * j / 6, (200, 170, 90), 0.25)
            if i < 12:
                tw = 0.5 + 0.5 * math.sin(t * 4 + i * 1.3)
                canvas.blendf(sx, sy, (255, 250, 220), 0.6 + 0.4 * tw)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    canvas.blendf(sx + dx, sy + dy, (255, 214, 130), 0.3 * tw)
            prev = (sx, sy)
    if "sails" in kinds:                                     # tattered spectral sails billowing on the three masts
        for m_, h_ in ((-3, 3.5), (0, 4.5), (3, 3.5)):
            top = y + (6 + h_) * scale
            for k in range(int(h_ * scale) + 1):                  # the mast rising above the hull
                canvas.blendf(x + m_ * scale, y + 6 * scale + k, (60, 100, 96), 0.9)
            for row in range(1, int(h_ * scale)):
                f = row / max(1, h_ * scale)
                belly = math.sin(f * math.pi) * (0.9 + 0.5 * math.sin(t * 2 + m_)) * scale
                w_ = max(1, int((1.8 - f * 0.6) * scale))
                for dx in range(-w_, w_ + 1):
                    if (dx * 7 + row * 3 + int(t * 3)) % 9 == 0:
                        continue                                  # holes in the tattered canvas
                    edge = abs(dx) == w_ or row == 1
                    canvas.blendf(x + m_ * scale + dx + belly, top - row, (190, 255, 214), 0.5 if edge else 0.16)
    if "riftmotes" in kinds:                                 # light and dark sparks circling in opposition
        for i in range(8):
            ang = t * 1.5 + i * math.tau / 8
            rx, ry = x + math.cos(ang) * (6 + i % 3) * scale, y + 4 * scale + math.sin(ang) * 3 * scale
            canvas.blendf(rx, ry, (255, 244, 205) if i % 2 == 0 else (120, 60, 220), 0.85)
    if "sparkle" in kinds:
        for i in range(4):
            ang = t * 1.3 + i * math.pi / 2
            sx, sy = x + math.cos(ang) * 8 * scale, y + 3 * scale + math.sin(ang) * 5 * scale
            tw = 0.5 + 0.5 * math.sin(t * 9 + i * 1.7)
            canvas.blendf(sx, sy, (255, 230, 150), 0.85 * tw)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                canvas.blendf(sx + dx, sy + dy, (255, 200, 110), 0.3 * tw)
    if "prism" in kinds:                                     # refraction glints: rainbow stars popping around the crystal
        for i in range(6):
            ph = (t * 0.9 + i * 0.37) % 1.0
            sx = x + math.cos(i * 2.4 + t * 0.6) * (5 + i % 3) * scale
            sy = y + (1.5 + 3.2 * ((i * 5) % 4) / 3) * scale + 2 * math.sin(t * 2 + i)
            col, a = hsv((i / 6 + t * 0.4) % 1, 0.5, 1.0), math.sin(ph * math.pi)
            canvas.blendf(sx, sy, (255, 255, 255), 0.95 * a)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                canvas.blendf(sx + dx, sy + dy, col, 0.55 * a)
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                canvas.blendf(sx + dx, sy + dy, col, 0.25 * a)
    if "orbit" in kinds:
        for i in range(5):
            ang = t * (1.6 + 0.2 * i) + i * 1.26
            sx, sy = x + math.cos(ang) * (7 + i % 2) * scale, y + 3.5 * scale + math.sin(ang) * 2.4 * scale
            canvas.blendf(sx, sy, design.accent, 0.9)
            canvas.blendf(sx - math.cos(ang + 1.5) * 0.9, sy - math.sin(ang + 1.5) * 0.9, design.accent, 0.35)
    if "lightning" in kinds:
        step = int(t * 14)
        for i in range(2):
            if flicker(step / 30.0, i, 33) > 0.55:
                px, py = x + (flicker(step / 30.0, i, 1) - 0.5) * 9 * scale, y + 6 * scale
                for s in range(5):
                    px += (flicker(step / 30.0, i, 10 + s) - 0.5) * 3
                    py += 1.6
                    canvas.blendf(px, py, (230, 245, 255), 0.9 - s * 0.14)
    if "void" in kinds:                                      # motes drawn inward to the hull
        for i in range(6):
            k = (t * 0.8 + i / 6) % 1.0
            ang = i * 1.05 + t * 0.7
            sx, sy = x + math.cos(ang) * (1 - k) * 9 * scale, y + 3 * scale + math.sin(ang) * (1 - k) * 5 * scale
            canvas.blendf(sx, sy, (170, 110, 255), 0.7 * k)
