"""Ballistics: launches, the shell trace with wind and gravity, and impacts."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional

from tanks.colors import clamp
from tanks.config import PhysicsConfig


class ImpactKind(Enum):
    TERRAIN = auto()
    TANK = auto()
    OUT = auto()


@dataclass(frozen=True)
class Impact:
    x: float
    y: float
    kind: ImpactKind
    tank: Optional[int] = None


@dataclass(frozen=True)
class Launch:
    x0: float
    y0: float
    vx: float
    vy: float
    g: float
    ax: float = 0.0   # horizontal wind acceleration
    wa: float = 0.0   # corkscrew amplitude (px) - a sideways oscillation across the flight line
    wf: float = 0.0   # corkscrew angular frequency

    def at(self, t: float) -> tuple[float, float]:
        x, y = self.x0 + self.vx * t + 0.5 * self.ax * t * t, self.y0 + self.vy * t - 0.5 * self.g * t * t
        if self.wa:
            sp = math.hypot(self.vx, self.vy) or 1.0
            s = self.wa * math.sin(self.wf * t) * min(1.0, t * 2.5)
            x, y = x - self.vy / sp * s, y + self.vx / sp * s
        return x, y


@dataclass
class TraceResult:
    impact: Impact
    points: list
    time: float


class PhysicsEngine:
    def __init__(self, cfg: PhysicsConfig, field_width: int) -> None:
        self.cfg = cfg
        self.max_speed = math.sqrt(cfg.gravity * field_width * cfg.range_factor)

    def speed_for(self, power: float) -> float:
        return self.max_speed * clamp(power / self.cfg.max_power, 0, 1) ** self.cfg.power_curve

    def make_launch(self, origin: tuple[float, float], angle: float, power: float,
                    gravity: Optional[float] = None, wind: float = 0.0) -> Launch:
        a, v = math.radians(angle), self.speed_for(power)
        return Launch(origin[0], origin[1], v * math.cos(a), v * math.sin(a),
                      self.cfg.gravity if gravity is None else gravity, wind)

    def trace(self, launch: Launch, probe: Callable, dt: float = 0.02, spacing: float = 0.0,
              max_time: float = 12.0) -> TraceResult:
        pts, acc, t = [], 0.0, 0.0
        px, py = launch.x0, launch.y0
        while t < max_time:
            t += dt
            x, y = launch.at(t)
            hit = probe(x, y)
            if spacing:
                acc += math.hypot(x - px, y - py)
                if acc >= spacing:
                    pts.append((x, y))
                    acc = 0.0
            if hit:
                return TraceResult(Impact(x, y, hit[0], hit[1]), pts, t)
            px, py = x, y
        return TraceResult(Impact(px, py, ImpactKind.OUT), pts, t)


class Projectile:
    def __init__(self, launch: Launch, owner: int, probe: Callable) -> None:
        self.launch, self.owner, self.probe = launch, owner, probe
        self.t = 0.0
        self.x, self.y = launch.x0, launch.y0


def advance_projectile(proj: Projectile, dt: float, cfg: PhysicsConfig,
                       on_step: Optional[Callable[[float, float], None]] = None) -> Optional[Impact]:
    """Moves a shell along its analytic arc in sub-steps so it can never tunnel."""
    t0, t1 = proj.t, proj.t + dt
    x1, y1 = proj.launch.at(t1)
    n = max(1, int(math.hypot(x1 - proj.x, y1 - proj.y) / cfg.substep) + 1)
    for i in range(1, n + 1):
        tt = t0 + dt * i / n
        x, y = proj.launch.at(tt)
        hit = proj.probe(x, y)
        if hit:
            proj.t, proj.x, proj.y = tt, x, y
            return Impact(x, y, hit[0], hit[1])
        if on_step:
            on_step(x, y)
    proj.t, proj.x, proj.y = t1, x1, y1
    return None
