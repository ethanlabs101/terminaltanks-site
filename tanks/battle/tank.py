"""A tank on the field: position, angle, power, health, design, ammo, colours and hover."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from tanks.art.barrels import muzzle_point
from tanks.colors import RGB
from tanks.config import MAX_HP, TANK_H, TANK_W
from tanks.content.ammo import AmmoType, DEFAULT_AMMO
from tanks.content.tanks import DEFAULT_DESIGN, TankDesign


@dataclass
class Tank:
    index: int
    name: str
    label: str
    color: RGB
    shot_color: RGB
    is_ai: bool
    x: float
    y: float
    facing: int
    angle: float
    power: float = 60.0
    hp: int = MAX_HP
    max_hp: int = MAX_HP
    hull_sentinel: tuple = (250, 3, 251)   # which animated colour (RGB / ASTRAL) the hull and shell use when the flags below are set
    shot_sentinel: tuple = (250, 3, 251)
    rgb_hull: bool = False       # RGB unlocks: the colour is re-rolled every frame by BattleWorld
    rgb_shot: bool = False
    hurt: float = 0.0
    recoil: float = 0.0
    destroyed: bool = False
    design: TankDesign = DEFAULT_DESIGN
    ammo: AmmoType = DEFAULT_AMMO
    team: int = 0                # tanks on the same team never end a round against each other
    owner: int = 0               # LAN: which machine controls this tank (0 = host)
    kind: str = ""               # "" = ordinary tank, "ufo" = large hovering saucer
    scale: float = 1.0           # hit-box / size multiplier (UFOs are big)
    hover: float = 0.0           # height above the ground it floats at
    shield: int = 0              # hits the shield still absorbs
    volley: int = 0              # extra shots left in the current turn
    turns: int = 0               # turns taken (drives UFO behaviour)
    charge: int = 0              # special attack: forfeited turns banked (2 = ready)
    guard: bool = False          # shielded for as long as another tank on its team is alive (the Mothership)
    vis_dx: float = 0.0          # visual-only offset that eases a teleporting UFO into place
    phase: int = 0               # UFO damage phases already triggered

    @property
    def width(self) -> float:
        return TANK_W * self.scale

    @property
    def height(self) -> float:
        return TANK_H * self.scale

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.destroyed

    @property
    def rel_angle(self) -> float:
        return self.angle if self.facing > 0 else 180 - self.angle

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return self.x - self.width / 2, self.y, self.x + self.width / 2, self.y + self.height

    def launch_origin(self, angle: Optional[float] = None) -> tuple[float, float]:
        ang = self.angle if angle is None else angle
        if self.scale == 1.0:
            return muzzle_point(self.x, self.y, ang, self.design)
        a = math.radians(ang)                    # big units fire from their belly cannon
        d, ph = self.width * 0.45 + 1.0, self.height * 0.35
        return self.x + d * math.cos(a), self.y + ph + d * math.sin(a)
