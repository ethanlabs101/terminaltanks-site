"""The Martyr, the true final boss: health pools, damage scaling, aim, phases, rewards and his elemental ammo."""
from __future__ import annotations

from tanks.content.ammo import AMMO_BY_KEY, ANCIENT_AMMOS, AmmoType
from tanks.content.homes import ANCIENT_THEMES
from tanks.content.maps import ANCIENT_MAPS
from tanks.content.tanks import ANCIENT_DESIGNS


MARTYR_PLAYER_MULT = 10                                         # huge health pools: every hit is worth 10 (special: 30)
MARTYR_PLAYER_HP_BY_PHASE = (175, 175, 200)                     # the last phase gives you more to work with
MARTYR_MAGE_HP = (340, 525, 550)
MARTYR_MAGE_MULT = (8, 5, 6)                                    # his hits: phase I hits hard from the start...
MARTYR_RADIUS = (1.0, 1.15, 1.3)                                # ...and so do his blasts
MARTYR_PREC = (0.8, 0.68, 0.55)                                 # ...and his aim
MARTYR_PHASES = ("PHASE I  -  FIRE & EARTH", "PHASE II  -  WIND & WATER", "PHASE III  -  LIGHT & DARK")
MARTYR_TAUNT = ("LET US BEGIN WHERE ALL POWER BEGINS.", "THE SKY ITSELF WILL FIGHT YOU.", "THIS IS THE END OF TIME. HOLD NOTHING BACK.")
MARTYR_REWARD_IDS = tuple([f"tank:{d.key}" for d in ANCIENT_DESIGNS] + [f"ammo:{a.key}" for a in ANCIENT_AMMOS]
                          + [f"map:{m.key}" for m in ANCIENT_MAPS] + [f"theme:{k.lower()}" for k in ANCIENT_THEMES] + ["paint:astral"])
MARTYR_WIN_COINS = 25000
ELEMENTS = {   # element: (name, projectile, trail, blast, colour, mechanics)
    "fire": ("FIRE", "flame", "fire", "fire", (255, 130, 40), (("cluster", 5), ("cr", 0.6), ("radius", 1.2), ("dmg", 2))),
    "earth": ("EARTH", "shell", "cinders", "magma", (176, 134, 84), (("bounce", 2), ("br", 0.5), ("radius", 1.3), ("dmg", 3))),
    "wind": ("WIND", "ring", "ripple", "shock", (190, 240, 222), (("wob", (4.0, 9.0)), ("apex", ("split", 3, 1.2)), ("subr", 0.7), ("radius", 0.9), ("dmg", 1))),
    "water": ("WATER", "glyph", "tides", "tidal", (80, 170, 255), (("chain", 5), ("cstep", 7.0), ("cr", 0.7), ("radius", 1.0), ("dmg", 2))),
    "dark": ("DARK", "eye", "aeon", "eclipse", (160, 90, 240), (("pull", 12.0), ("radius", 1.5), ("fuse", 0.8), ("fr", 1.8), ("dmg", 2))),
    "light": ("LIGHT", "relic", "runes", "sigil", (255, 240, 170), (("apex", ("split", 5, 1.0)), ("subr", 0.7), ("radius", 1.3), ("dmg", 2))),
}
PHASE_ELEMENTS = (("fire", "earth", "wind"), ("fire", "earth", "wind", "water"), ("fire", "earth", "wind", "water", "dark", "light"))
MAGE_AMMO: dict = {}
for _el, (_n, _pj, _tr, _bm, _, _mech) in ELEMENTS.items():
    for _ph in range(3):
        _m = tuple((k, (round(v * MARTYR_RADIUS[_ph], 2) if k == "radius" else v)) for k, v in _mech)
        _a = AmmoType(f"m_{_el}{_ph}", _n, f"The Martyr's {_n.lower()} magic.", _pj, _tr, _bm, _m)
        MAGE_AMMO[(_el, _ph)] = _a
        AMMO_BY_KEY[_a.key] = _a
