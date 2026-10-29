"""The computer players: per-difficulty profiles and the aim solver that learns from its misses."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Optional

from tanks.battle.physics import Impact, ImpactKind
from tanks.battle.tank import Tank
from tanks.battle.terrain import Terrain
from tanks.battle.world import BattleWorld
from tanks.colors import clamp
from tanks.config import PHYS
from tanks.settings import Difficulty


@dataclass(frozen=True)
class AIProfile:
    angle_sigma: float
    power_sigma: float
    gravity_error: float
    sim_dt: float
    terrain_aware: bool
    learn_rate: float
    think_time: float
    angle_step: int
    pick_from: int
    refine: bool
    wind_error: float          # how badly the AI misreads the wind (fraction)
    adaptive: bool = False     # Master: ensemble planning + physics-model calibration


AI_PROFILES = {
    Difficulty.EASY: AIProfile(10.0, 0.18, 0.30, 0.06, False, 0.35, 2.0, 6, 8, False, 0.65),
    Difficulty.NORMAL: AIProfile(5.5, 0.09, 0.16, 0.04, True, 0.65, 1.5, 3, 3, False, 0.30),
    Difficulty.HARD: AIProfile(4.2, 0.075, 0.10, 0.025, True, 0.92, 1.1, 3, 1, True, 0.12),
    # Same hands as a very good human (it still shakes), but it reasons much better:
    # it picks the shot that is most likely to land under its own execution noise and
    # fits its gravity model to every miss instead of nudging an aim offset.
    Difficulty.MASTER: AIProfile(1.8, 0.032, 0.06, 0.02, True, 0.9, 0.9, 3, 1, True, 0.03, True),
}


@dataclass
class AimPlan:
    angle: float
    power: float
    intended_rel: float
    intended_power: float
    think_time: float
    status: str
    prob: float = 0.0


@dataclass
class ShotRecord:
    rel: float
    power: float
    error_x: float
    hit: bool


class ModelProbe:
    """The AI's own (imperfect) world model used while solving for a shot."""

    def __init__(self, terrain: Terrain, foe: Tank, aware: bool) -> None:
        self.terrain, self.rect, self.aware, self.flat = terrain, foe.rect, aware, foe.y
        self.w = terrain.width

    def __call__(self, x: float, y: float):
        if x < 0 or x >= self.w:
            return ImpactKind.OUT, None
        x0, y0, x1, y1 = self.rect
        if x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1:
            return ImpactKind.TANK, None
        ground = self.terrain.heights[int(x)] if self.aware else self.flat
        if y < ground:
            return ImpactKind.TERRAIN, None
        return None


class AIController:
    """Searches (angle, power) pairs against an imperfect ballistic model and learns from misses."""

    def __init__(self, difficulty: Difficulty, rng: random.Random, precision: float = 1.0) -> None:
        self.profile = AI_PROFILES[difficulty]
        if precision != 1.0:        # Tournament levels fine-tune the hands: <1 sharper, >1 sloppier
            self.profile = replace(self.profile, angle_sigma=self.profile.angle_sigma * precision,
                                   power_sigma=self.profile.power_sigma * precision)
        self.rng = rng
        self.gravity_bias = 1 + rng.uniform(-self.profile.gravity_error, self.profile.gravity_error)
        self.correction = 0.0
        self.last_wind: Optional[float] = None
        self.history: list[ShotRecord] = []
        self._ctx = None

    def _shoot(self, ctx, rel: float, power: float, g_scale: float) -> Impact:
        me, _, world, wind, probe = ctx
        ang = rel if me.facing > 0 else 180 - rel
        phys = world.physics
        M = me.ammo.mechanics if getattr(world, "ammo_fx", True) else {}
        launch = phys.make_launch(me.launch_origin(ang), ang, power, phys.cfg.gravity * g_scale * M.get("g", 1.0), wind * M.get("wind", 1.0))
        if M.get("speed", 1.0) != 1.0:
            launch = replace(launch, vx=launch.vx * M["speed"], vy=launch.vy * M["speed"])
        return phys.trace(launch, probe, dt=self.profile.sim_dt, max_time=10.0).impact

    @staticmethod
    def _is_hit(imp: Impact, foe: Tank, world: BattleWorld) -> bool:
        return imp.kind is ImpactKind.TANK or (
            imp.kind is ImpactKind.TERRAIN and world.distance_to_tank(foe, imp.x, imp.y) <= PHYS.splash_reach)

    def plan(self, me: Tank, foe: Tank, world: BattleWorld) -> AimPlan:
        p = self.profile
        aim_x = clamp(foe.x + self.correction, 3, world.width - 4)
        aim_y = foe.y + foe.height / 2
        wind = world.wind * (1 + self.rng.uniform(-p.wind_error, p.wind_error))
        if self.last_wind is not None and abs(world.wind - self.last_wind) > 0.5:
            self.correction *= 0.5     # old corrections were learned in different wind
        self.last_wind = world.wind
        ctx = self._ctx = (me, foe, world, wind, ModelProbe(world.terrain, foe, p.terrain_aware))

        def miss(rel: float, power: float) -> float:
            imp = self._shoot(ctx, rel, power, self.gravity_bias)
            d = abs(imp.x - foe.x) * 0.15 if imp.kind is ImpactKind.TANK else math.hypot(imp.x - aim_x, imp.y - aim_y)
            for rec in self.history:
                if not rec.hit and abs(rec.rel - rel) < 1.5 and abs(rec.power - power) < 3:
                    d += 12
            return d + 0.02 * abs(rel - 52)

        scored = []
        for rel in range(18, 83, p.angle_step):
            for power in range(22, 101, 3):
                scored.append((miss(rel, power) + self.rng.random() * 0.4, rel, power))
        scored.sort()
        prob = 0.0
        if p.adaptive:
            rel, power, prob = self._ensemble_pick(scored, miss, ctx, foe, world)
        else:
            _, rel, power = self.rng.choice(scored[:p.pick_from])
            if p.refine:
                best = (miss(rel, power), rel, power)
                for da in range(-2, 3):
                    for dp in range(-3, 4):
                        pw = clamp(power + dp, 15, 100)
                        cand = (miss(rel + da, pw), rel + da, pw)
                        if cand < best:
                            best = cand
                _, rel, power = best
        exec_rel = clamp(rel + self.rng.gauss(0, p.angle_sigma), 4, 176)
        exec_power = clamp(power * (1 + self.rng.gauss(0, p.power_sigma)), 12, 100)
        angle = exec_rel if me.facing > 0 else 180 - exec_rel
        if p.adaptive:
            status = f"ENSEMBLE SOLVE - P(HIT) {prob:.0%}"
            if self.history:
                status += f" - MODEL RECALIBRATED x{len(self.history)}"
        elif self.history:
            last = self.history[-1]
            long_shot = last.error_x * me.facing > 0
            status = f"LAST SHOT {'LONG' if long_shot else 'SHORT'} {abs(last.error_x):.0f}PX - RECALIBRATING"
            if last.hit:
                status = "TARGET LOCKED - REPEATING SOLUTION"
        else:
            status = "SOLVING FIRING SOLUTION"
        return AimPlan(angle, exec_power, rel, power, p.think_time * self.rng.uniform(0.85, 1.2), status, prob)

    def _ensemble_pick(self, scored, miss, ctx, foe, world) -> tuple:
        """Refine the best distinct candidates, then keep the one most likely to hit under execution noise."""
        p, picks, seen = self.profile, [], set()
        for _, rel, power in scored:
            key = (round(rel / 2), round(power / 3))
            if key not in seen:
                seen.add(key)
                picks.append((rel, power))
            if len(picks) == 8:
                break
        best = None
        for rel0, pow0 in picks:
            local = (miss(rel0, pow0), rel0, pow0)
            for da in (-1, 0, 1):
                for dp in (-2, 0, 2):
                    pw = clamp(pow0 + dp, 15, 100)
                    cand = (miss(rel0 + da, pw), rel0 + da, pw)
                    if cand < local:
                        local = cand
            dist, rel, power = local
            hits, n = 0, 14
            for _ in range(n):
                imp = self._shoot(ctx, rel + self.rng.gauss(0, p.angle_sigma),
                                  clamp(power * (1 + self.rng.gauss(0, p.power_sigma)), 12, 100), self.gravity_bias)
                hits += self._is_hit(imp, foe, world)
            score = hits / n - 0.003 * dist
            if best is None or score > best[0]:
                best = (score, rel, power, hits / n)
        return best[1], best[2], best[3]

    def observe(self, plan: AimPlan, impact: Impact, foe: Tank, hit: bool) -> None:
        err = impact.x - foe.x
        self.history.append(ShotRecord(plan.intended_rel, plan.intended_power, err, hit))
        if self.profile.adaptive:
            if not hit and self._ctx is not None:
                self._fit_gravity(plan, impact)
            return
        if not hit:
            self.correction = clamp(self.correction - err * self.profile.learn_rate, -30, 30)

    def _fit_gravity(self, plan: AimPlan, impact: Impact) -> None:
        """Bisect for the gravity scale that makes the model reproduce where the shell really landed."""
        ctx = self._ctx
        f = lambda g: self._shoot(ctx, plan.intended_rel, plan.intended_power, g).x - impact.x
        lo, hi = 0.75, 1.25
        flo, fhi = f(lo), f(hi)
        if flo * fhi > 0:
            return
        for _ in range(10):
            mid = (lo + hi) / 2
            fm = f(mid)
            if flo * fm <= 0:
                hi, fhi = mid, fm
            else:
                lo, flo = mid, fm
        self.gravity_bias = clamp(self.gravity_bias + ((lo + hi) / 2 - self.gravity_bias) * 0.6, 0.8, 1.2)
