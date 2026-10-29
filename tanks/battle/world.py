"""BattleWorld: one battlefield (terrain, scenery, tanks, wind, particles) and its collision tests."""
from __future__ import annotations

import math
import random
from typing import Callable, Optional, Sequence, TYPE_CHECKING

from tanks.art.scenery import Scenery
from tanks.battle.effects import EffectsFactory, Explosion, ParticleSystem
from tanks.battle.physics import ImpactKind, PhysicsEngine
from tanks.battle.tank import Tank
from tanks.battle.terrain import Terrain
from tanks.colors import clamp, mix
from tanks.config import PHYS, TANK_W
from tanks.content.ammo import AMMO_BY_KEY
from tanks.content.maps import MapDefinition
from tanks.content.paints import LIVE_COLORS, live_color
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.screen import PixelCanvas
from tanks.settings import Settings

if TYPE_CHECKING:
    from tanks.match.sessions import PlayerSetup


class BattleWorld:
    def __init__(self, width: int, height: int, mapdef: MapDefinition, seed: int, players: Sequence["PlayerSetup"],
                 settings: Settings) -> None:
        self.width, self.height, self.mapdef, self.settings = width, height, mapdef, settings
        self.rng = random.Random(seed)
        self.terrain = Terrain(width, height, mapdef, self.rng)
        self.physics = PhysicsEngine(PHYS, width)
        self.vrng = random.Random(seed ^ 0x5EED)       # visuals only: effects must never touch the simulation's rng (LAN sync)
        self.tanks: list[Tank] = []
        slots: dict = {}
        for i, pl in enumerate(players):
            jitter = self.rng.uniform(-0.02, 0.02)
            team = pl.team if pl.team >= 0 else i
            k = slots[team] = slots.get(team, -1) + 1
            gap = 0.13 if all(p.scale == 1.0 for p in players) else 0.18
            frac = mapdef.spawns[0] + k * gap if team == 0 else mapdef.spawns[1] - k * gap
            half = int(TANK_W * pl.scale / 2)
            x = int(clamp((frac + jitter) * width, 9 + half, width - 10 - half))
            self.terrain.flatten(x + 0.5, 10)
            hover = pl.hover or DESIGN_BY_KEY[pl.design].hover
            self.tanks.append(Tank(i, pl.name, pl.label, pl.tank_color, pl.shot_color, pl.is_ai, x + 0.5,
                                   float(self.terrain.support_height(x)) + hover, 1 if team == 0 else -1,
                                   50.0 if team == 0 else 130.0,
                                   hp=pl.hp, max_hp=pl.hp, hull_sentinel=pl.tank_color, shot_sentinel=pl.shot_color, rgb_hull=pl.tank_color in LIVE_COLORS, rgb_shot=pl.shot_color in LIVE_COLORS,
                                   design=DESIGN_BY_KEY[pl.design], ammo=AMMO_BY_KEY[pl.ammo], team=team, owner=pl.owner,
                                   kind=pl.kind, scale=pl.scale, hover=hover, shield=pl.shield, guard=pl.guard))
        self.scenery = Scenery(width, height, mapdef.theme, self.rng)
        self.scenery.apply_terrain(self.terrain)
        self.particles = ParticleSystem()
        self.explosions: list[Explosion] = []
        self.fx = EffectsFactory(self.particles, settings, self.vrng)
        self._smoke_timer = 0.0
        self.clock = 0.0
        self.wind = 0.0
        self.roll_wind()
        self._make_streaks()

    # -- wind ----------------------------------------------------------------
    def roll_wind(self) -> None:
        m, lo = self.settings.wind, getattr(self.settings, "wind_min", 0.0)
        if m <= 0:
            self.wind = 0.0
        elif lo > 0:
            self.wind = round(self.rng.choice((-1, 1)) * self.rng.uniform(lo, m), 1)
        else:
            self.wind = round(self.rng.choice((-1, 1)) * self.rng.uniform(0.2, 1.0) * m, 1)

    def drift_wind(self) -> None:
        m, lo = self.settings.wind, getattr(self.settings, "wind_min", 0.0)
        if m > 0:
            w = clamp(self.wind + self.rng.uniform(-0.45, 0.45) * max(m - lo, 1.0) * (1.0 if lo > 0 else m / max(m - lo, 1.0)), -m, m)
            if lo > 0 and abs(w) < lo:                       # stay inside the band: bounce off its calm edge
                w = math.copysign(lo + (lo - abs(w)), w or self.wind or 1.0)
                w = clamp(w, -m, m)
            self.wind = round(w, 1)

    def _make_streaks(self) -> None:
        n = max(8, self.width * self.height // 450)
        self.streaks = [[self.rng.uniform(0, self.width), self.rng.uniform(self.height * 0.25, self.height - 2)] for _ in range(n)]

    def draw_wind(self, canvas: PixelCanvas) -> None:
        if abs(self.wind) < 0.3:
            return
        sgn = 1 if self.wind > 0 else -1
        length = 3 + int(abs(self.wind) * 0.9)
        sky = self.scenery.sky
        for x, y in self.streaks:
            py = self.height - 1 - int(y)
            if not 0 <= py < self.height:
                continue
            for i in range(length):
                px = int(x) - sgn * i
                if 0 <= px < self.width and canvas.rows[py][px] == sky[py][px]:
                    canvas.rows[py][px] = mix(sky[py][px], (235, 242, 255), 0.22 * (1 - i / length))

    # -- collision -----------------------------------------------------------
    def collision_at(self, x: float, y: float, skip: Optional[int]):
        if x < 0 or x >= self.width:
            return ImpactKind.OUT, None
        if y < self.terrain.heights[int(x)]:
            return ImpactKind.TERRAIN, None
        r = PHYS.projectile_radius
        for t in self.tanks:
            if t.index == skip or t.destroyed:
                continue
            x0, y0, x1, y1 = t.rect
            if x0 - r <= x <= x1 + r and y0 - r <= y <= y1 + r:
                return ImpactKind.TANK, t.index
        return None

    def inside_tank(self, idx: int, x: float, y: float) -> bool:
        x0, y0, x1, y1 = self.tanks[idx].rect
        return x0 - 1.5 <= x <= x1 + 1.5 and y0 - 1.5 <= y <= y1 + 1.5

    def owner_probe(self, owner: int) -> Callable:
        state = {"left": False}

        def probe(x: float, y: float):
            if not state["left"] and not self.inside_tank(owner, x, y):
                state["left"] = True
            return self.collision_at(x, y, None if state["left"] else owner)
        return probe

    def distance_to_tank(self, tank: Tank, x: float, y: float) -> float:
        x0, y0, x1, y1 = tank.rect
        return math.hypot(x - clamp(x, x0, x1), y - clamp(y, y0, y1))

    # -- state updates -------------------------------------------------------
    def settle(self, dt: float) -> bool:
        moving = False
        for t in self.tanks:
            if t.destroyed:
                continue
            target = float(self.terrain.support_height(t.x)) + t.hover
            if t.y > target:
                t.y = max(target, t.y - PHYS.fall_speed * dt)
                moving = True
            elif t.y < target:
                t.y = target
        return moving

    def carve(self, x: float, y: float, r: float) -> None:
        x0, x1 = self.terrain.carve(x, y, r)
        self.scenery.apply_terrain(self.terrain, x0 - 1, x1 + 1)

    def terrain_op(self, mode: str, x: float, y: float, r: float) -> None:
        """Shell-specific ground effects. 'blast' digs a crater; the others are what makes some ammo a different tool."""
        t = self.terrain
        if mode == "mound":
            x0, x1 = t.mound(x, r * 1.25, r * 0.9)
        elif mode == "trench":
            x0, x1 = t.trench(x, max(2.0, r * 0.45), r * 1.5)
        elif mode == "glass":
            x0, x1 = t.smooth(x, r * 1.4)
        else:
            return self.carve(x, y, r)
        self.scenery.apply_terrain(t, x0 - 1, x1 + 1)

    def update_effects(self, dt: float) -> None:
        self.clock += dt
        for t in self.tanks:
            if t.vis_dx:
                t.vis_dx = 0.0 if abs(t.vis_dx) < 0.05 else t.vis_dx * max(0.0, 1 - dt * 3.2)
        if any(t.rgb_hull or t.rgb_shot for t in self.tanks):
            for t in self.tanks:
                if t.rgb_hull:
                    t.color = live_color(t.hull_sentinel, self.clock)
                if t.rgb_shot:
                    t.shot_color = live_color(t.shot_sentinel, self.clock)
        self.particles.wind = self.wind
        drift = self.wind * 7 * dt
        for st in self.streaks:
            st[0] = (st[0] + drift) % self.width
        self.particles.update(dt, self.terrain)
        for e in self.explosions:
            e.update(dt)
        self.explosions = [e for e in self.explosions if not e.done]
        for t in self.tanks:
            t.hurt = max(0.0, t.hurt - dt)
            t.recoil = max(0.0, t.recoil - dt)
            if t.alive:
                if t.kind != "ufo":
                    self.fx.ambient(t.design, t.x, t.y, t.color, dt)
        self._smoke_timer -= dt
        if self._smoke_timer <= 0:
            self._smoke_timer = 0.09
            for t in self.tanks:
                if t.destroyed:
                    self.fx.smoke(t.x, t.y + 4, 1, 3.0)
                elif t.hp == 1 and self.vrng.random() < 0.35:
                    self.fx.smoke(t.x, t.y + 6, 1, 1.5)

    def resize(self, w: int, h: int) -> None:
        sx, sy = w / self.width, h / self.height
        old, oldsc = self.terrain.heights, self.terrain.scorch
        self.terrain.heights = [int(clamp(old[min(len(old) - 1, int(x / sx))] * sy, 2, h - 10)) for x in range(w)]
        self.terrain.scorch = [oldsc[min(len(oldsc) - 1, int(x / sx))] for x in range(w)]
        self.terrain.width, self.terrain.height = w, h
        self.width, self.height = w, h
        self.physics = PhysicsEngine(PHYS, w)
        self.scenery = Scenery(w, h, self.mapdef.theme, self.rng)
        self.scenery.apply_terrain(self.terrain)
        for t in self.tanks:
            t.x = int(clamp(t.x * sx, 9, w - 10)) + 0.5
            t.y = float(self.terrain.support_height(t.x)) + t.hover
        self.particles.items.clear()
        self.explosions.clear()
        self._make_streaks()
