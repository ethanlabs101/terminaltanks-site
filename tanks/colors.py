"""Colour maths (RGB tuples, mixing, gradients, HSV, flicker noise), the interface palette and the terminal colour modes."""
from __future__ import annotations

import colorsys
import os
from enum import Enum
from typing import Sequence

from tanks.config import IS_WEB


RGB = tuple[int, int, int]


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(a: RGB, b: RGB, t: float) -> RGB:
    if t <= 0:
        return a
    if t >= 1:
        return b
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def shade(c: RGB, k: float) -> RGB:
    return (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))


def ease_out(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def gradient(stops: Sequence[tuple[float, RGB]], t: float) -> RGB:
    if t <= stops[0][0]:
        return stops[0][1]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 1.0)
    return stops[-1][1]


class Palette:
    BG = (5, 9, 15)
    PANEL = (9, 16, 26)
    PANEL_HI = (16, 38, 52)
    LINE = (38, 118, 128)
    PRIMARY = (96, 232, 212)
    PRIMARY_DIM = (44, 116, 112)
    AMBER = (255, 184, 64)
    TEXT = (208, 222, 232)
    MUTED = (104, 124, 140)
    DANGER = (255, 92, 92)
    HEART = (255, 82, 108)
    HEART_OFF = (76, 52, 66)
    OK = (124, 240, 152)
    WHITE = (255, 255, 255)
    INK = (8, 12, 18)


class ColorMode(Enum):
    AUTO = "AUTO"
    TRUE = "24-BIT"
    ANSI256 = "256"
    ANSI16 = "16"


def resolve_color_mode(mode: ColorMode) -> ColorMode:
    if mode is not ColorMode.AUTO:
        return mode
    if IS_WEB:
        return ColorMode.TRUE
    env = os.environ
    if env.get("COLORTERM", "").lower() in ("truecolor", "24bit") or env.get("WT_SESSION"):
        return ColorMode.TRUE
    if os.name == "nt":
        return ColorMode.TRUE
    term = env.get("TERM", "")
    if any(k in term for k in ("kitty", "alacritty", "direct")):
        return ColorMode.TRUE
    if "256" in term or env.get("TERM_PROGRAM") in ("Apple_Terminal", "iTerm.app"):
        return ColorMode.ANSI256
    return ColorMode.ANSI16 if "color" in term or term in ("xterm", "linux") else ColorMode.ANSI256


_ANSI16 = [(0, 0, 0), (205, 49, 49), (13, 188, 121), (229, 229, 16), (36, 114, 200),
           (188, 63, 188), (17, 168, 205), (229, 229, 229), (102, 102, 102), (241, 76, 76),
           (35, 209, 139), (245, 245, 67), (59, 142, 234), (214, 112, 214), (41, 184, 219),
           (255, 255, 255)]


def nearest16(c: RGB) -> int:
    return min(range(16), key=lambda i: sum((c[k] - _ANSI16[i][k]) ** 2 for k in range(3)))


def to_256(c: RGB) -> int:
    r, g, b = c
    if abs(r - g) < 10 and abs(g - b) < 10:
        avg = (r + g + b) // 3
        if avg < 8:
            return 16
        if avg > 248:
            return 231
        return 232 + round((avg - 8) / 247 * 23)
    return 16 + 36 * round(r / 255 * 5) + 6 * round(g / 255 * 5) + round(b / 255 * 5)


def hsv(h: float, s: float = 1.0, v: float = 1.0) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def flicker(t: float, a: int, b: int) -> float:
    """Cheap deterministic flicker noise in 0..1 that changes ~30 times a second."""
    return (((int(t * 30) * 73856093) ^ (a * 19349663) ^ (b * 83492791)) & 255) / 255.0


GOLD = (255, 206, 100)
