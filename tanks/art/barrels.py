"""Barrel hardware (single, twin, howitzer, crystal, ...): muzzle positions, lengths and colours."""
from __future__ import annotations

import math
from dataclasses import dataclass

from tanks.colors import RGB, clamp, flicker, gradient, hsv, mix, shade
from tanks.config import BARREL_LEN, PIVOT_H
from tanks.content.tanks import TankDesign


# ---- Barrels: reusable muzzle hardware. `offsets` are lateral barrel positions, `length` is the muzzle distance from the
# pivot (it also decides where shells leave the gun), `style` picks the per-pixel colouring in barrel_color().
@dataclass(frozen=True)
class BarrelSpec:
    offsets: tuple = (0.0,)
    length: float = BARREL_LEN
    style: str = "plain"


BARRELS: dict[str, BarrelSpec] = {
    "single": BarrelSpec(), "double": BarrelSpec((-1.1, 1.1)), "heavy": BarrelSpec((-0.5, 0.5)),
    "rail": BarrelSpec((0.0,), BARREL_LEN, "rail"), "triple": BarrelSpec((-1.6, 0.0, 1.6), BARREL_LEN, "rail"),
    "prism": BarrelSpec((-0.5, 0.5), BARREL_LEN, "prism"),
    "sniper": BarrelSpec((0.0,), 10.5, "plain"), "howitzer": BarrelSpec((-0.7, 0.7), 6.0, "plain"),
    "needle": BarrelSpec((0.0,), 9.5, "rail"), "quad": BarrelSpec((-2.1, -0.7, 0.7, 2.1), 7.0, "plain"),
    "gatling": BarrelSpec((-0.9, 0.0, 0.9), 7.0, "spin"), "coil": BarrelSpec((0.0,), 8.0, "coil"),
    "crystal": BarrelSpec((-0.4, 0.4), 8.5, "crystal"), "flame": BarrelSpec((0.0,), 7.5, "flame"),
    "void": BarrelSpec((0.0,), 8.0, "void"), "bolt": BarrelSpec((-0.6, 0.6), 8.0, "bolt"),
    "sunlance": BarrelSpec((0.0,), 10.0, "flame"), "umbra": BarrelSpec((-0.6, 0.6), 9.0, "void"), "gale": BarrelSpec((-1.2, 0.0, 1.2), 8.5, "coil"),
    "magmacannon": BarrelSpec((-0.5, 0.5), 8.5, "flame"), "ancient": BarrelSpec((-0.9, 0.0, 0.9), 9.5, "rune"),
    "lure": BarrelSpec((0.0,), 8.0, "biolume"), "spirit": BarrelSpec((0.0,), 9.0, "spirit"), "katana": BarrelSpec((0.0,), 11.0, "hardlight"),
    "tesseract": BarrelSpec((-0.8, 0.8), 8.5, "tesseract"), "atomic": BarrelSpec((-0.6, 0.0, 0.6), 8.0, "atomic"),
    "fungal": BarrelSpec((0.0,), 7.0, "fungal"), "wyrm": BarrelSpec((-0.5, 0.5), 7.5, "maw"), "serpent": BarrelSpec((0.0,), 9.5, "serpent"),
    "astrolabe": BarrelSpec((-1.0, 0.0, 1.0), 8.5, "astrolabe"), "broadside": BarrelSpec((-1.2, 0.0, 1.2), 6.5, "ghostfire"),
}


def barrel_spec(name: str) -> BarrelSpec:
    return BARRELS.get(name, BARRELS["single"])


def muzzle_point(x: float, y: float, angle: float, design: "TankDesign", scale: float = 1.0, recoil: float = 0.0) -> tuple[float, float]:
    """Where a shell leaves the gun for a tank drawn at (x, y) with the barrel at `angle` degrees. THE single source of
    truth: draw_tank, Tank.launch_origin and every title-screen / shop animation use it, so shells always start at the
    visible muzzle (a one-pixel margin keeps them clear of the barrel itself)."""
    a = math.radians(angle)
    d = (barrel_spec(design.barrel).length - recoil * 2.5 + 1.0) * scale
    return x + d * math.cos(a), y + PIVOT_H * scale + d * math.sin(a)


def visual_lift(design: "TankDesign", t: float, scale: float = 1.0) -> float:
    """How far draw_tank raises a hovering design (hover height + bob). Muzzle users add it so shells leave the barrel."""
    return design.hover + 0.6 * math.sin(t * 2.4) * scale if design.hover > 0 else 0.0


def barrel_color(style: str, base: RGB, accent: RGB, t: float, d: float, lane: int) -> RGB:
    if style == "rune":
        if int(d * 3 - t * 10) % 7 == 0:
            return (255, 252, 230)
        return mix(shade(base, 0.7), accent, 0.5 + 0.5 * math.sin(d * 1.4 - t * 7 + lane))
    if style == "rail":
        return accent if int(d * 2 - t * 14) % 6 == 0 else base
    if style == "coil":
        return accent if int(d * 2.2 - t * 9) % 3 == 0 else shade(base, 0.7)
    if style == "prism":
        return hsv(t * 0.5 + d * 0.04, 0.55, 1.0)
    if style == "crystal":
        f = 0.5 + 0.5 * math.sin(d * 1.7 - t * 5 + lane * 2.0)
        return mix(hsv(t * 0.45 + d * 0.07 + lane * 0.2, 0.5, 1.0), (255, 255, 255), 0.6 * f)
    if style == "flame":
        k = clamp(d / 8.0 + 0.2 * math.sin(t * 20 + d * 3), 0, 1)
        return gradient(((0, base), (0.55, (255, 120, 30)), (1, (255, 230, 120))), k)
    if style == "spin":
        return accent if (int(t * 18) + lane) % 3 == 0 else base
    if style == "void":
        return mix((20, 10, 40), (170, 90, 255), 0.5 + 0.5 * math.sin(d * 1.3 - t * 6))
    if style == "bolt":
        return (235, 245, 255) if flicker(t, int(d * 2), lane) > 0.8 else mix(base, accent, 0.5)
    if style == "biolume":                                   # cold light pulsing up the stalk
        return mix((16, 40, 70), (140, 255, 240), 0.15 + 0.85 * max(0.0, math.sin(d * 1.6 - t * 7)) ** 3)
    if style == "spirit":
        k = clamp(d / 9.0 + 0.25 * math.sin(t * 17 + d * 2.6), 0, 1)
        return gradient(((0, (236, 232, 246)), (0.5, (110, 170, 255)), (1, (230, 248, 255))), k)
    if style == "hardlight":                                 # a blade of light: white core, cyan edge, a glint running out
        return (255, 255, 255) if int(d * 2 - t * 22) % 7 == 0 else ((200, 250, 255) if lane == 0 and d > 1.5 else (90, 220, 255))
    if style == "tesseract":
        return hsv(0.72 + 0.08 * math.sin(d * 0.9 - t * 3 + lane * 2), 0.5, 1.0) if int(d * 2 + t * 6) % 4 else (255, 255, 255)
    if style == "atomic":
        return mix((40, 80, 160), (225, 245, 255), max(0.0, math.sin(d * 0.9 - t * 8 + lane)) ** 2)
    if style == "fungal":
        return mix((206, 196, 176), (120, 255, 190), 0.5 + 0.5 * math.sin(d * 1.3 - t * 2.4))
    if style == "maw":
        return gradient(((0, (150, 104, 60)), (0.6, (226, 120, 50)), (1, (255, 214, 140))), clamp(d / 7.5 + 0.15 * math.sin(t * 9 + d), 0, 1))
    if style == "serpent":
        return (244, 206, 110) if int(d * 2) % 3 == 0 else mix((24, 112, 78), (100, 220, 160), 0.5 + 0.5 * math.sin(d - t * 4))
    if style == "astrolabe":
        return (255, 250, 220) if flicker(t * 0.6, int(d * 2), lane + 7) > 0.88 else mix((150, 110, 50), (240, 206, 120), 0.5 + 0.5 * math.sin(d * 1.2 + t))
    if style == "ghostfire":
        return mix((34, 60, 56), (130, 255, 180), clamp(0.3 + 0.7 * math.sin(d * 1.8 - t * 6 + lane * 1.7), 0, 1))
    return base
