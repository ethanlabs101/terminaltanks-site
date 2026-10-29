"""Destructible terrain: a height per column, craters, scorch marks, flattening and the generators for map profiles."""
from __future__ import annotations

import math
import random

from tanks.colors import clamp, lerp
from tanks.content.maps import MapDefinition, sample_profile


class Terrain:
    """Column heightmap; craters carve columns, so the battlefield is destructible."""

    def __init__(self, width: int, height: int, mapdef: MapDefinition, rng: random.Random) -> None:
        self.width, self.height = width, height
        self.version = 0
        phases = [rng.uniform(0, math.tau) for _ in range(3)]
        scale = min(height, width * 0.55) * 0.74
        self.heights: list[int] = []
        for x in range(width):
            u = x / max(1, width - 1)
            h = sample_profile(mapdef.profile, u, mapdef.smooth)
            r = mapdef.roughness
            if r:
                h += r * (math.sin(u * math.tau * 7 + phases[0]) + 0.5 * math.sin(u * math.tau * 17 + phases[1])
                          + 0.25 * math.sin(u * math.tau * 41 + phases[2]))
            self.heights.append(int(clamp(h * scale + 2, 2, height - 10)))
        self.scorch = [0.0] * width

    def height_at(self, x: float) -> int:
        return self.heights[int(clamp(x, 0, self.width - 1))]

    def support_height(self, x: float) -> int:
        xi = int(x)
        return min(self.heights[max(0, xi - 5):min(self.width, xi + 6)])

    def flatten(self, cx: float, half: int = 7) -> None:
        xc = int(cx)
        target = self.heights[xc]
        for x in range(max(0, xc - half), min(self.width, xc + half + 1)):
            edge = half - abs(x - xc)
            weight = 1.0 if edge >= 3 else edge / 3
            self.heights[x] = int(round(lerp(self.heights[x], target, weight)))

    def carve(self, cx: float, cy: float, r: float) -> tuple[int, int]:
        x0, x1 = max(0, int(cx - r) - 1), min(self.width - 1, int(cx + r) + 1)
        for x in range(x0, x1 + 1):
            dx = x + 0.5 - cx
            if abs(dx) > r:
                continue
            dy = math.sqrt(r * r - dx * dx)
            low, h = cy - dy, self.heights[x]
            if low < h and cy + dy >= h - 1:
                self.heights[x] = max(0, int(low))
                self.scorch[x] = max(self.scorch[x], 1 - abs(dx) / r * 0.6)
        self.version += 1
        return x0, x1


def _terrain_mound(self, cx: float, r: float, height: float) -> tuple[int, int]:
    """Builds earth up in a bell shape (a shell that makes ground instead of destroying it)."""
    x0, x1 = max(0, int(cx - r) - 1), min(self.width - 1, int(cx + r) + 1)
    for x in range(x0, x1 + 1):
        u = (x + 0.5 - cx) / r
        if abs(u) <= 1:
            self.heights[x] = int(min(self.height - 12, self.heights[x] + height * (1 - u * u)))
    self.version += 1
    return x0, x1


def _terrain_trench(self, cx: float, half: float, depth: float) -> tuple[int, int]:
    """A narrow, deep shaft."""
    x0, x1 = max(0, int(cx - half) - 1), min(self.width - 1, int(cx + half) + 1)
    for x in range(x0, x1 + 1):
        u = abs(x + 0.5 - cx) / half
        if u <= 1:
            self.heights[x] = max(1, int(self.heights[x] - depth * (1 - 0.5 * u * u)))
            self.scorch[x] = max(self.scorch[x], 0.8)
    self.version += 1
    return x0, x1


def _terrain_smooth(self, cx: float, r: float) -> tuple[int, int]:
    """Glassing: melts the ground in the radius down to one flat level."""
    x0, x1 = max(0, int(cx - r) - 1), min(self.width - 1, int(cx + r) + 1)
    seg = [self.heights[x] for x in range(x0, x1 + 1)]
    level = sum(seg) // max(1, len(seg))
    for x in range(x0, x1 + 1):
        u = abs(x + 0.5 - cx) / r
        if u <= 1:
            self.heights[x] = int(lerp(self.heights[x], level, 1.0 if u < 0.7 else (1 - u) / 0.3))
            self.scorch[x] = max(self.scorch[x], 0.4)
    self.version += 1
    return x0, x1


Terrain.mound, Terrain.trench, Terrain.smooth = _terrain_mound, _terrain_trench, _terrain_smooth
