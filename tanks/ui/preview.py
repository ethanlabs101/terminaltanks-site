"""PreviewStage: a tank firing its ammo on loop, used by setup, the shop, the tournament and reward screens."""
from __future__ import annotations

import math
import random
from typing import Optional

from tanks.art.barrels import muzzle_point, visual_lift
from tanks.art.projectiles import draw_projectile
from tanks.art.scenery import Scenery
from tanks.art.tanks import draw_tank
from tanks.battle.effects import EffectsFactory, Explosion, ParticleSystem
from tanks.battle.terrain import Terrain
from tanks.colors import RGB, mix, shade
from tanks.content.ammo import AmmoType, DEFAULT_AMMO
from tanks.content.maps import MapDefinition
from tanks.content.paints import COLOR_CHOICES, live_color
from tanks.content.tanks import DEFAULT_DESIGN, TankDesign
from tanks.screen import PixelCanvas
from tanks.settings import Settings


class PreviewStage:
    """A tiny looping range: the tank aims, fires one shell in its ammo's style and the shell detonates."""
    PERIOD = 3.4

    def __init__(self, settings: Settings, w: int = 46, h: int = 26, scale: int = 2, seed: int = 3) -> None:
        self.w, self.h, self.scale = w, h, scale
        self.ps = ParticleSystem(500)
        self.fx = EffectsFactory(self.ps, settings, random.Random(seed))
        self.explosions: list[Explosion] = []
        self.design, self.ammo = DEFAULT_DESIGN, DEFAULT_AMMO
        self.body, self.shot = COLOR_CHOICES[0][1], COLOR_CHOICES[6][1]
        self.t = self.clock = 0.0
        self.phase = 0
        self.n = 0
        self.recoil = 0.0
        self.sky = [[mix((14, 22, 60), (200, 120, 110), (py / h) ** 1.4)] * w for py in range(h)]
        self.dim = 0.0
        self.scn = None
        self.gy = self.ty = 4.0

    def set_map(self, mapdef: Optional[MapDefinition]) -> None:
        """Use a real battlefield (sky, terrain, aurora, weather) as the backdrop; None = the plain workshop range."""
        self.t, self.phase = 0.0, 0
        self.explosions.clear()
        if mapdef is None:
            self.scn, self.gy, self.ty = None, 4.0, 4.0
            return
        rng = random.Random(5)
        terrain = Terrain(self.w, self.h, mapdef, rng)
        terrain.flatten(self.tank_x, 10)
        terrain.flatten(self.target_x, 10)
        self.scn = Scenery(self.w, self.h, mapdef.theme, rng)
        self.scn.apply_terrain(terrain)
        self.gy, self.ty = float(terrain.support_height(int(self.tank_x))), float(terrain.support_height(self.target_x))

    def set_kit(self, design: TankDesign, body: RGB, ammo: AmmoType, shot: RGB, dim: float = 0.0) -> None:
        if (design, ammo, body, shot) != (self.design, self.ammo, self.body, self.shot):
            self.t, self.phase = 0.0, 0
            self.ps.items.clear()
            self.explosions.clear()
        self.design, self.ammo, self.body, self.shot, self.dim = design, ammo, body, shot, dim

    @property
    def target_x(self) -> int:
        return self.w - 6

    def update(self, dt: float) -> None:
        self.t += dt
        self.clock += dt
        self.recoil = max(0.0, self.recoil - dt)
        self.ps.update(dt)
        self.fx.ambient(self.design, self.tank_x, self.gy, live_color(self.body, self.clock), dt)     # particle ambients (embers, mist, sparks...)
        for e in self.explosions:
            e.update(dt)
        self.explosions = [e for e in self.explosions if not e.done]
        if self.t > self.PERIOD:
            self.t, self.phase = 0.0, 0
        if self.phase == 0 and self.t > 0.6:
            self.phase, self.recoil = 1, 0.2
            self._launch()
        if self.phase == 1:
            u = (self.t - 0.6) / 1.2
            x, y = self._shell(u)
            self.n += 1
            shot = live_color(self.shot, self.clock)
            self.fx.trail(x, y, shot, self.ammo, self.n, self.clock)
            if u >= 1:
                self.phase = 2
                self.explosions.append(Explosion(self.target_x, self.ty, 4.5, shot, 0.8, self.ammo.boom))
                self.fx.impact(self.target_x, self.ty, shot, (92, 84, 70), 0.6, self.ammo)

    def _angle(self) -> float:
        return 26 + 9 * math.sin(self.clock * 2.2)

    @property
    def tank_x(self) -> float:
        return 5.5 * self.scale + 6

    def _launch(self) -> None:
        """Latch the muzzle position and barrel angle at the instant of firing; the shell then arcs from there to the target."""
        ang = self._angle()
        self.fire_angle = ang
        self.fire_from = muzzle_point(self.tank_x, self.gy + visual_lift(self.design, self.clock, self.scale), ang, self.design, self.scale)

    def _shell(self, u: float) -> tuple[float, float]:
        x0, y0 = getattr(self, "fire_from", (self.tank_x, 8.0))
        x1, y1 = self.target_x, self.ty
        k = math.tan(math.radians(getattr(self, "fire_angle", 26.0))) * (x1 - x0) - (y1 - y0)    # start slope == barrel slope
        return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + k * u * (1 - u)

    def render(self) -> PixelCanvas:
        w, h, s = self.w, self.h, self.scale
        if self.scn is not None:
            cv = self.scn.canvas()
            self.scn.draw_stars(cv, self.clock)
            self.scn.draw_aurora(cv, self.clock)
            self.scn.draw_fx(cv, self.clock)
        else:
            cv = PixelCanvas(w, h, rows=[r[:] for r in self.sky])
            for x in range(w):
                for y in range(3):
                    cv.plot(x, y, shade((92, 84, 70), 0.75 + 0.1 * ((x + y) % 3)))
                cv.plot(x, 3, (110, 210, 120))
        draw_tank(cv, self.tank_x, self.gy, 1, self._angle() if self.phase != 1 else self.fire_angle, self.body, scale=s, recoil=self.recoil,
                  design=self.design, t=self.clock)
        if self.phase == 1:
            u = (self.t - 0.6) / 1.2
            x, y = self._shell(u)
            x2, y2 = self._shell(min(1.0, u + 0.02))
            draw_projectile(cv, x, y, x2 - x + 1e-3, y2 - y, self.shot, self.ammo, self.clock)
        self.ps.draw(cv)
        for e in self.explosions:
            e.draw(cv)
        if self.dim:
            for row in cv.rows:
                row[:] = [mix(c, (6, 10, 16), self.dim) for c in row]
        return cv
