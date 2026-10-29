"""Battle HUD pieces: the turn phases, the screen layout, floating text, banners and screen shake."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

from tanks.colors import RGB


class Phase(Enum):
    INTRO = auto()
    AIMING = auto()
    AI_THINKING = auto()
    FLIGHT = auto()
    IMPACT = auto()
    SETTLE = auto()
    DESTRUCTION = auto()
    BLESSING = auto()          # MARTYR'S BLESSING: the cosmic-clock detonation (see BlessingFX)


@dataclass
class Layout:
    cols: int
    rows: int
    fx: int
    fy: int
    fcols: int
    frows: int
    top: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    color: RGB
    age: float = 0.0
    life: float = 1.4


@dataclass
class Banner:
    text: str
    sub: str
    color: RGB
    life: float = 1.2
    age: float = 0.0


class ScreenShake:
    def __init__(self) -> None:
        self.mag = 0.0

    def kick(self, m: float) -> None:
        self.mag = max(self.mag, m)

    def update(self, dt: float) -> None:
        self.mag = max(0.0, self.mag - dt * 7)

    def offset(self, rng: random.Random, enabled: bool) -> tuple[int, int]:
        if not enabled or self.mag < 0.35:
            return 0, 0
        return round(rng.uniform(-1, 1) * self.mag), round(rng.uniform(-1, 1) * self.mag * 0.6)
