"""Battlefields. Theme is a map's look (sky, ground, colours, weather); MapDefinition is a terrain profile plus a
theme. MAPS is the free random pool; SHOP_MAPS are sold in four price tiers of 15 and a premium tier; MISSION_MAPS,
TICKET_MAPS and ANCIENT_MAPS are earned. Keys are saved in progress files: never rename one."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from tanks.colors import RGB


@dataclass(frozen=True)
class Theme:
    sky_top: RGB
    sky_bottom: RGB
    far: RGB
    orb: RGB
    surface: RGB
    topsoil: RGB
    soil: RGB
    deep: RGB
    star_density: float
    aurora: bool = False
    fx: str = ""            # animated sky: a key of MOTE_STYLES in art/scenery.py (embers, snow, stardust, ...) or "storm"
    buildings: str = ""     # a silhouette skyline baked into the sky behind the terrain (styles: _bake_buildings in art/scenery.py)


@dataclass(frozen=True)
class MapDefinition:
    key: str
    name: str
    description: str
    profile: tuple[tuple[float, float], ...]
    smooth: bool
    roughness: float
    spawns: tuple[float, float]
    theme: Theme
    cover: int
    relief: int
    special: bool = False                    # Tournament-reward map (not part of the 50-map library)
    accent: RGB = (255, 206, 100)            # colour of its name in the battlefield list


MAPS: tuple[MapDefinition, ...] = (
    MapDefinition("valley", "VALLEY", "A wide bowl. Open lines of fire, but shells roll into the basin.",
                  ((0, .60), (.12, .48), (.30, .20), (.5, .10), (.70, .20), (.88, .48), (1, .60)), True, 0.0,
                  (.09, .91), Theme((14, 22, 60), (232, 140, 120), (60, 50, 100), (255, 220, 160), (110, 210, 120),
                                    (70, 140, 80), (92, 84, 70), (40, 36, 40), 0.003), 1, 2),
    MapDefinition("pass", "MOUNTAIN PASS", "Twin peaks wall off the centre. Lob it over or wear it down.",
                  ((0, .28), (.14, .34), (.30, .78), (.40, .52), (.50, .30), (.60, .52), (.70, .78), (.86, .34), (1, .28)),
                  False, 0.012, (.08, .92),
                  Theme((8, 14, 34), (90, 120, 170), (40, 60, 100), (220, 235, 255), (235, 240, 250),
                        (140, 150, 165), (86, 90, 104), (34, 36, 48), 0.005), 3, 3),
    MapDefinition("wasteland", "WASTELAND", "Broken dunes and blast scars. Nothing to hide behind but luck.",
                  ((0, .22), (.2, .30), (.35, .18), (.5, .34), (.65, .18), (.8, .30), (1, .22)), False, 0.05,
                  (.10, .90), Theme((40, 14, 20), (230, 120, 60), (110, 50, 50), (255, 130, 60), (220, 170, 90),
                                    (190, 130, 70), (140, 90, 60), (60, 36, 30), 0.002), 1, 1),
    MapDefinition("industrial", "INDUSTRIAL", "Steel terraces and a central bulwark. Angles matter.",
                  ((0, .30), (.10, .30), (.13, .44), (.28, .44), (.31, .18), (.42, .18), (.45, .62), (.55, .62),
                   (.58, .18), (.69, .18), (.72, .44), (.87, .44), (.90, .30), (1, .30)), False, 0.0,
                  (.205, .795), Theme((6, 14, 26), (30, 90, 110), (24, 50, 70), (120, 240, 255), (120, 150, 170),
                                      (84, 104, 120), (60, 72, 86), (26, 32, 40), 0.001), 3, 2),
    MapDefinition("canyon", "CANYON", "High cliffs, a deep chasm and a lone rock spire between you.",
                  ((0, .62), (.24, .62), (.32, .50), (.36, .12), (.44, .08), (.48, .40), (.52, .40), (.56, .08),
                   (.64, .12), (.68, .50), (.76, .62), (1, .62)), False, 0.015, (.13, .87),
                  Theme((30, 20, 50), (250, 170, 110), (120, 70, 80), (255, 240, 200), (232, 150, 90),
                        (190, 100, 60), (150, 72, 50), (70, 34, 34), 0.002), 2, 3),
)


def sample_profile(points: Sequence[tuple[float, float]], u: float, smooth: bool) -> float:
    n = len(points)
    for i in range(n - 1):
        x0, h0 = points[i]
        x1, h1 = points[i + 1]
        if u <= x1:
            t = (u - x0) / (x1 - x0) if x1 > x0 else 1.0
            if not smooth:
                return h0 + (h1 - h0) * t
            p0 = points[max(0, i - 1)][1]
            p3 = points[min(n - 1, i + 2)][1]
            return max(0.02, 0.5 * (2 * h0 + (-p0 + h1) * t + (2 * p0 - 5 * h0 + 4 * h1 - p3) * t * t
                                    + (-p0 + 3 * h0 - 3 * h1 + p3) * t ** 3))
    return points[-1][1]


def _mirror(half: Sequence[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    return tuple(half) + tuple((round(1 - x, 4), h) for x, h in reversed(list(half)[:-1]))


def _rate(points: Sequence[tuple[float, float]], spawns: tuple[float, float]) -> tuple[int, int]:
    hs = [h for _, h in points]
    span = max(hs) - min(hs)
    base = (sample_profile(points, spawns[0], False) + sample_profile(points, spawns[1], False)) / 2
    bump = max([h for x, h in points if 0.3 <= x <= 0.7] or hs) - base
    return 1 + (bump > 0.15) + (bump > 0.35), 1 + (span > 0.3) + (span > 0.55)


_THEMES: dict[str, Theme] = {
    "valley": MAPS[0].theme, "alpine": MAPS[1].theme, "waste": MAPS[2].theme, "steel": MAPS[3].theme, "canyon": MAPS[4].theme,
    "arctic": Theme((10, 20, 48), (150, 200, 230), (70, 100, 150), (235, 245, 255), (240, 248, 255), (190, 215, 235), (120, 150, 185), (50, 70, 100), 0.003),
    "jungle": Theme((8, 30, 30), (120, 200, 120), (30, 90, 70), (255, 240, 170), (90, 200, 90), (50, 140, 60), (86, 66, 44), (34, 30, 26), 0.001),
    "volcano": Theme((20, 6, 8), (200, 60, 30), (80, 24, 24), (255, 150, 60), (120, 100, 100), (78, 66, 68), (52, 42, 44), (22, 18, 20), 0.002),
    "moon": Theme((2, 3, 8), (40, 44, 60), (50, 54, 70), (210, 215, 230), (180, 182, 190), (140, 142, 150), (100, 102, 110), (46, 48, 54), 0.012),
    "cyber": Theme((8, 4, 26), (180, 40, 160), (60, 24, 110), (80, 255, 240), (90, 255, 240), (60, 170, 200), (56, 56, 110), (24, 22, 56), 0.004),
    "swamp": Theme((10, 20, 16), (120, 140, 80), (40, 60, 50), (230, 230, 160), (120, 160, 70), (84, 110, 60), (70, 60, 44), (30, 28, 24), 0.002),
    "beach": Theme((30, 50, 120), (255, 190, 120), (90, 110, 160), (255, 230, 170), (250, 225, 160), (225, 190, 120), (170, 135, 90), (84, 68, 50), 0.001),
    "midnight": Theme((3, 6, 24), (30, 50, 110), (20, 30, 70), (180, 200, 255), (90, 110, 180), (60, 76, 130), (44, 52, 96), (20, 22, 44), 0.008),
    "ember": Theme((24, 10, 16), (220, 110, 70), (90, 40, 48), (255, 200, 120), (200, 110, 70), (160, 80, 56), (110, 60, 50), (50, 30, 30), 0.002),
    "toxic": Theme((6, 18, 10), (140, 220, 60), (40, 70, 40), (220, 255, 120), (150, 230, 70), (100, 170, 60), (70, 80, 50), (28, 34, 24), 0.002),
    "steppe": Theme((20, 30, 70), (240, 200, 130), (100, 100, 110), (255, 230, 170), (190, 190, 100), (150, 150, 80), (120, 100, 70), (56, 48, 40), 0.002),
    "rust": Theme((12, 14, 22), (170, 100, 70), (70, 56, 60), (230, 200, 170), (180, 110, 70), (130, 80, 56), (94, 62, 50), (40, 30, 30), 0.002),
}

_S = (0.08, 0.92)
# (name, description, profile, theme, spawns, smooth, roughness)
_EXTRA_MAPS = (
    ("DUNES", "Soft rolling sand. Shells drop short in the dips.", _mirror([(0, .25), (.15, .36), (.3, .2), (.5, .4)]), "beach", _S, True, 0.015),
    ("TWIN TOWERS", "A narrow tower guards each tank. Go high.", _mirror([(0, .2), (.2, .2), (.22, .7), (.27, .7), (.29, .2), (.5, .2)]), "cyber", (.09, .91), False, 0.0),
    ("BASIN", "A deep bowl. Shells roll to the bottom.", _mirror([(0, .7), (.2, .5), (.4, .15), (.5, .1)]), "toxic", _S, True, 0.0),
    ("HILLTOP", "One fat hill owns the middle.", _mirror([(0, .15), (.3, .2), (.42, .55), (.5, .6)]), "jungle", _S, False, 0.01),
    ("SAWTOOTH", "Jagged teeth break every flat line.", _mirror([(0, .22), (.16, .22), (.2, .5), (.22, .22), (.3, .5), (.32, .22), (.4, .5), (.42, .22), (.5, .5)]), "rust", _S, False, 0.0),
    ("CRATER LAKE", "A huge impact basin between two rims.", _mirror([(0, .4), (.15, .4), (.25, .2), (.35, .05), (.5, .03)]), "midnight", _S, False, 0.01),
    ("PLATEAU", "A flat-topped mesa dominates the centre.", _mirror([(0, .2), (.2, .2), (.3, .5), (.5, .5)]), "steppe", _S, False, 0.0),
    ("BUNKER", "Sunken firing pits behind a central berm.", _mirror([(0, .35), (.15, .35), (.18, .2), (.3, .2), (.33, .5), (.5, .5)]), "steel", _S, False, 0.0),
    ("ROLLING HILLS", "Gentle swells hide low shots.", _mirror([(0, .3), (.12, .42), (.25, .22), (.38, .45), (.5, .28)]), "valley", _S, True, 0.0),
    ("THE NEEDLE", "A single needle of rock splits the field.", _mirror([(0, .18), (.4, .18), (.47, .85), (.5, .88)]), "alpine", _S, False, 0.0),
    ("FORTRESS WALLS", "A rampart stands in front of each tank.", _mirror([(0, .25), (.2, .25), (.22, .55), (.28, .55), (.3, .25), (.5, .25)]), "steel", _S, False, 0.0),
    ("LAUNCH RAMPS", "High launch pads fall to a low centre.", _mirror([(0, .55), (.22, .55), (.42, .1), (.5, .08)]), "ember", _S, False, 0.0),
    ("ISLANDS", "Stepping stones across a deep gap.", _mirror([(0, .3), (.16, .3), (.2, .05), (.3, .05), (.34, .35), (.4, .35), (.44, .05), (.5, .05)]), "beach", _S, False, 0.0),
    ("CALDERA", "A volcanic cone with a hollow heart.", _mirror([(0, .15), (.22, .2), (.38, .62), (.44, .72), (.47, .5), (.5, .4)]), "volcano", _S, False, 0.005),
    ("CENTRE STAIRS", "Terraces climb toward the middle.", _mirror([(0, .15), (.16, .15), (.18, .25), (.26, .25), (.28, .35), (.36, .35), (.38, .45), (.5, .45)]), "steel", _S, False, 0.0),
    ("CASCADE", "Terraces fall toward the middle.", _mirror([(0, .6), (.16, .6), (.18, .5), (.28, .5), (.3, .4), (.38, .4), (.4, .2), (.5, .2)]), "arctic", _S, False, 0.0),
    ("TRENCHES", "Narrow gaps swallow flat shots.", _mirror([(0, .3), (.16, .3), (.18, .08), (.26, .08), (.28, .3), (.42, .3), (.44, .08), (.5, .08)]), "swamp", _S, False, 0.0),
    ("BROKEN BRIDGE", "A central pier stands over two gaps.", _mirror([(0, .4), (.26, .4), (.3, .05), (.4, .05), (.42, .4), (.5, .4)]), "beach", _S, False, 0.0),
    ("DOUBLE HUMP", "A hump in front of each tank.", _mirror([(0, .2), (.14, .2), (.22, .65), (.3, .3), (.4, .22), (.5, .25)]), "jungle", _S, False, 0.01),
    ("BADLANDS", "Crumbling ground. Nothing is flat.", _mirror([(0, .3), (.2, .4), (.35, .25), (.5, .38)]), "rust", _S, False, 0.07),
    ("GLACIER", "Smooth ice swells with a central trough.", _mirror([(0, .45), (.2, .3), (.4, .38), (.5, .2)]), "arctic", _S, True, 0.02),
    ("CLIFFSIDE", "Tanks perch on high cliffs over a wide floor.", _mirror([(0, .7), (.16, .7), (.2, .22), (.5, .2)]), "canyon", _S, False, 0.0),
    ("PYRAMID", "A huge pyramid fills the middle.", _mirror([(0, .1), (.2, .1), (.5, .8)]), "waste", _S, False, 0.0),
    ("ZIGZAG", "Peaks and valleys in every direction.", _mirror([(0, .3), (.16, .3), (.24, .55), (.32, .2), (.4, .55), (.5, .25)]), "cyber", _S, False, 0.0),
    ("MOONSCAPE", "Pockmarked lunar ground.", _mirror([(0, .25), (.25, .2), (.5, .28)]), "moon", _S, False, 0.06),
    ("THE GORGE", "A narrow, bottomless-looking gorge.", _mirror([(0, .5), (.22, .5), (.32, .4), (.38, .05), (.5, .03)]), "canyon", _S, False, 0.0),
    ("TWIN MESAS", "Flat-topped mesas with a saddle between.", _mirror([(0, .15), (.16, .15), (.2, .5), (.3, .5), (.34, .15), (.42, .15), (.46, .4), (.5, .4)]), "steppe", _S, False, 0.0),
    ("RAMPARTS", "Stepped battlements in layers.", _mirror([(0, .3), (.16, .3), (.18, .45), (.24, .45), (.26, .3), (.34, .3), (.36, .6), (.42, .6), (.44, .3), (.5, .3)]), "midnight", _S, False, 0.0),
    ("QUARRY", "Cut terraces drop into a deep pit.", _mirror([(0, .55), (.2, .55), (.24, .3), (.3, .3), (.34, .1), (.5, .1)]), "rust", _S, False, 0.0),
    ("TUNDRA WAVES", "Long frozen waves. Mind the crests.", _mirror([(0, .3), (.1, .4), (.2, .3), (.3, .4), (.4, .3), (.5, .4)]), "arctic", _S, True, 0.015),
    ("SHARK FIN", "A lone fin rises close to player two.", ((0, .3), (.4, .3), (.56, .3), (.6, .8), (.66, .3), (1, .3)), "midnight", (.09, .91), False, 0.0),
    ("LOPSIDED PEAK", "One big peak off-centre. Shots curve around it.", ((0, .25), (.2, .3), (.35, .75), (.5, .3), (.7, .25), (.85, .3), (1, .25)), "alpine", _S, False, 0.01),
    ("DRAGON SPINE", "A ridge of spikes down the whole field.", ((0, .3), (.1, .3), (.2, .5), (.3, .3), (.4, .6), (.5, .3), (.6, .7), (.7, .3), (.8, .5), (.9, .3), (1, .3)), "volcano", _S, False, 0.0),
    ("LANDSLIDE", "A collapsed slope with a deep scar.", ((0, .4), (.2, .4), (.4, .2), (.5, .3), (.6, .15), (.8, .4), (1, .4)), "rust", _S, False, 0.02),
    ("ICE SHELF", "High ice with a crack off-centre.", ((0, .5), (.35, .5), (.38, .1), (.46, .1), (.48, .5), (1, .5)), "arctic", _S, False, 0.0),
    ("WATCHTOWER", "A tall tower on the left, a ledge on the right.", ((0, .2), (.2, .2), (.24, .65), (.27, .65), (.3, .2), (.72, .2), (.78, .4), (.9, .4), (1, .2)), "steel", (.08, .85), False, 0.0),
    ("SINKHOLES", "The ground is full of holes.", ((0, .35), (.18, .35), (.22, .05), (.3, .05), (.34, .35), (.56, .35), (.6, .05), (.68, .05), (.72, .35), (1, .35)), "swamp", _S, False, 0.0),
    ("HOGBACK", "A long ridge sloping away to the right.", ((0, .2), (.2, .3), (.4, .7), (.55, .6), (.75, .3), (1, .2)), "waste", _S, True, 0.0),
    ("CAUSEWAY", "Raised roads between flooded lowlands.", ((0, .3), (.12, .3), (.17, .1), (.4, .1), (.45, .3), (.55, .3), (.6, .1), (.83, .1), (.88, .3), (1, .3)), "toxic", _S, False, 0.0),
    ("FANG GAP", "Two uneven fangs guard the gap.", ((0, .25), (.2, .25), (.28, .75), (.31, .25), (.7, .25), (.73, .75), (.8, .25), (1, .25)), "ember", _S, False, 0.0),
    ("CAULDRON", "A boiling pit ringed by high walls.", ((0, .3), (.22, .3), (.28, .6), (.4, .6), (.45, .1), (.55, .1), (.6, .6), (.72, .6), (.78, .3), (1, .3)), "volcano", _S, False, 0.0),
    ("SWITCHBACK", "Sharp spikes and narrow valleys.", ((0, .2), (.14, .2), (.22, .6), (.3, .15), (.4, .6), (.5, .15), (.6, .6), (.7, .15), (.78, .6), (.86, .2), (1, .2)), "jungle", _S, False, 0.0),
    ("THE NOTCH", "A raised block with a notch in the middle.", ((0, .25), (.25, .25), (.3, .5), (.45, .5), (.5, .3), (.55, .5), (.7, .5), (.75, .25), (1, .25)), "cyber", _S, False, 0.0),
    ("BREAKWATER", "A chain of jetties across the bay.", ((0, .3), (.18, .3), (.22, .5), (.28, .2), (.34, .5), (.4, .2), (.5, .5), (.6, .2), (.66, .5), (.72, .2), (.78, .5), (.82, .3), (1, .3)), "midnight", _S, False, 0.0),
    ("LAST STAND", "Both tanks dig in on raised bluffs.", ((0, .4), (.12, .4), (.17, .6), (.35, .15), (.65, .15), (.83, .6), (.88, .4), (1, .4)), "ember", (.06, .94), False, 0.0),
)


def _build_maps(rows) -> tuple[MapDefinition, ...]:
    out = []
    for name, desc, pts, theme, spawns, smooth, rough in rows:
        cover, relief = _rate(pts, spawns)
        out.append(MapDefinition(name.lower().replace(" ", "-"), name, desc, tuple(pts), smooth, rough, spawns,
                                 _THEMES[theme], cover, relief))
    return tuple(out)


MAPS = MAPS + _build_maps(_EXTRA_MAPS)
assert len({m.key for m in MAPS}) == len(MAPS)

# Tournament reward maps. They are not part of the 50-map library: Level 8, 9 and 10 each unlock one, and
# the level is fought on it. The three build up in spectacle: embers -> thunderstorm -> aurora citadel.
FORGE_MAP = MapDefinition(
    "forge", "THE FORGE", "A lava foundry: molten trench, tall battlements and embers in the air.",
    _mirror([(0, .40), (.10, .40), (.14, .58), (.20, .58), (.23, .30), (.31, .30), (.35, .66), (.40, .66), (.43, .14), (.5, .10)]),
    False, 0.008, (.07, .93),
    Theme((18, 4, 8), (196, 62, 22), (74, 22, 24), (255, 126, 44), (120, 96, 90), (86, 62, 60), (62, 44, 44), (22, 14, 16),
          0.002, False, "embers"),
    3, 3, True, (255, 140, 60))

SPIRE_MAP = MapDefinition(
    "spire", "STORM SPIRE", "Needle spires in a raging thunderstorm. Lightning splits the sky.",
    _mirror([(0, .38), (.10, .38), (.14, .24), (.19, .24), (.21, .72), (.24, .72), (.27, .26), (.35, .26), (.38, .54),
             (.42, .54), (.46, .20), (.5, .80)]),
    False, 0.006, (.06, .94),
    Theme((4, 6, 16), (46, 58, 96), (22, 28, 52), (176, 196, 255), (126, 136, 170), (88, 96, 126), (62, 68, 96), (22, 24, 38),
          0.002, False, "storm"),
    3, 3, True, (150, 205, 255))

# The exclusive Master Map and the finale: bastions, towers, an aurora sky and drifting golden motes.
MASTER_MAP = MapDefinition(
    "citadel", "THE CITADEL", "The Master's fortress: bastions, towers and a burning aurora sky.",
    _mirror([(0, .52), (.13, .52), (.17, .34), (.23, .34), (.26, .74), (.30, .74), (.33, .30), (.41, .30), (.45, .88), (.5, .92)]),
    False, 0.006, (.07, .93),
    Theme((6, 4, 18), (120, 50, 120), (40, 24, 70), (255, 214, 120), (255, 206, 90), (120, 90, 60), (64, 50, 60), (22, 18, 30), 0.008,
          True, "motes"),
    3, 3, True, (255, 206, 100))

# Shop maps: 5 cheap, 5 mid, 5 pro and 3 citadel-level (aurora skies, drifting particles, towering ground).
_TIER_ACCENT = ((170, 205, 175), (120, 190, 255), (255, 165, 90), (255, 206, 100))


def _shop_map(tier: int, name: str, desc: str, half, theme, smooth: bool = False, rough: float = 0.0,
              spawns: tuple = (0.08, 0.92), fx: str = "", aurora: bool = False, buildings: str = "") -> MapDefinition:
    pts = _mirror(half)
    th = _THEMES[theme] if isinstance(theme, str) else theme
    if fx or aurora or buildings:
        th = replace(th, fx=fx or th.fx, aurora=aurora or th.aurora, buildings=buildings or th.buildings)
    cover, relief = _rate(pts, spawns)
    return MapDefinition(name.lower().replace(" ", "-"), name, desc, pts, smooth, rough, spawns, th, cover, relief, True,
                         _TIER_ACCENT[tier])


_SANCTUM = Theme((4, 8, 26), (60, 110, 170), (30, 50, 100), (210, 240, 255), (190, 235, 255), (120, 180, 220), (70, 100, 150),
                 (24, 32, 60), 0.012, True, "snow")
_ECLIPSE = Theme((8, 2, 12), (150, 40, 70), (50, 16, 50), (255, 160, 90), (255, 150, 90), (130, 70, 56), (70, 40, 50),
                 (26, 14, 24), 0.01, True, "embers")
_ASTRAL = Theme((4, 2, 22), (90, 50, 150), (34, 22, 80), (190, 170, 255), (210, 190, 255), (110, 90, 170), (64, 52, 110),
                (22, 18, 44), 0.014, True, "stardust")

SHOP_MAPS: tuple[MapDefinition, ...] = (
    _shop_map(0, "HAYSTACK", "Soft mounds dot an open field.", [(0, .22), (.12, .32), (.24, .2), (.36, .34), (.5, .24)], "steppe", True, 0.01),
    _shop_map(0, "CULVERT", "A shallow drainage ditch splits the field.", [(0, .35), (.3, .35), (.38, .12), (.5, .1)], "swamp"),
    _shop_map(0, "PICNIC KNOLL", "One gentle knoll rises in the middle.", [(0, .2), (.25, .22), (.4, .42), (.5, .46)], "valley", True),
    _shop_map(0, "BOULDER FIELD", "Scattered boulders break every sightline.",
              [(0, .25), (.1, .25), (.13, .4), (.17, .4), (.2, .25), (.3, .25), (.33, .45), (.37, .45), (.4, .25), (.5, .3)], "rust"),
    _shop_map(0, "CROSSROADS", "Flat ground with a low berm at the junction.", [(0, .28), (.4, .28), (.44, .4), (.5, .4)], "waste"),
    _shop_map(1, "ANTHILL", "A terraced mound crawling with ledges.",
              [(0, .15), (.18, .15), (.2, .28), (.28, .28), (.3, .4), (.38, .4), (.4, .55), (.5, .55)], "jungle"),
    _shop_map(1, "TIDEPOOLS", "Rock pools at every stride.",
              [(0, .3), (.1, .3), (.13, .1), (.2, .1), (.23, .3), (.3, .3), (.33, .12), (.4, .12), (.43, .32), (.5, .32)], "beach"),
    _shop_map(1, "WATCH RIDGE", "A long ridge with lookout posts.",
              [(0, .2), (.2, .3), (.3, .55), (.34, .55), (.36, .4), (.46, .45), (.5, .7)], "alpine", False, 0.01),
    _shop_map(1, "SALT FLATS", "A blinding flat studded with posts.", [(0, .2), (.2, .2), (.22, .5), (.24, .5), (.26, .2), (.5, .2)], "steppe"),
    _shop_map(1, "COPPER MINE", "Cut shafts and a towering spoil heap.",
              [(0, .5), (.15, .5), (.2, .2), (.28, .2), (.32, .45), (.4, .2), (.5, .2)], "rust"),
    _shop_map(2, "SKYBRIDGE", "A narrow span high above the void.",
              [(0, .2), (.2, .2), (.24, .04), (.3, .04), (.34, .62), (.5, .62)], "cyber", fx="stardust"),
    _shop_map(2, "THE MAW", "A pit ringed with stone fangs, ash falling.",
              [(0, .35), (.14, .35), (.18, .7), (.2, .35), (.28, .5), (.3, .1), (.5, .05)], "volcano", fx="ash"),
    _shop_map(2, "CLOCKWORK", "Alternating towers tick across the field.",
              [(0, .3), (.1, .3), (.13, .7), (.17, .7), (.2, .3), (.28, .3), (.3, .55), (.34, .55), (.37, .3), (.5, .7)], "steel", fx="stardust"),
    _shop_map(2, "FROZEN FALLS", "Frozen terraces cascade into a deep pool.",
              [(0, .7), (.16, .7), (.2, .55), (.28, .55), (.32, .4), (.4, .4), (.44, .1), (.5, .08)], "arctic", fx="snow"),
    _shop_map(2, "OBELISK FIELD", "Slim obelisks stand in ranks under fireflies.",
              [(0, .2), (.1, .2), (.12, .6), (.14, .2), (.24, .2), (.26, .7), (.28, .2), (.38, .2), (.4, .55), (.42, .2), (.5, .8)],
              "midnight", fx="fireflies"),
    _shop_map(3, "CRYSTAL SANCTUM", "Gem spires under an aurora and falling snow.",
              [(0, .45), (.1, .45), (.14, .28), (.2, .28), (.23, .8), (.26, .8), (.3, .3), (.38, .3), (.42, .9), (.5, .95)],
              _SANCTUM, False, 0.004, (.07, .93)),
    _shop_map(3, "ECLIPSE GATE", "A colossal gate beneath a bleeding sky of embers.",
              [(0, .4), (.1, .4), (.14, .2), (.22, .2), (.24, .85), (.3, .85), (.32, .4), (.4, .4), (.44, .95), (.5, .2)],
              _ECLIPSE, False, 0.004, (.07, .93)),
    _shop_map(3, "ASTRAL BASTION", "Tiered ramparts adrift in a river of stars.",
              [(0, .55), (.12, .55), (.16, .4), (.22, .4), (.25, .7), (.3, .7), (.33, .35), (.4, .35), (.43, .95), (.5, .98)],
              _ASTRAL, False, 0.004, (.07, .93)),
    _shop_map(3, "VOID CATHEDRAL", "Twin spires over a bottomless nave of stars.",
              [(0, .5), (.1, .5), (.13, .3), (.2, .3), (.22, .9), (.25, .9), (.28, .35), (.36, .2), (.4, .2), (.44, .75), (.5, .1)],
              Theme((2, 0, 14), (80, 30, 140), (30, 12, 70), (200, 150, 255), (190, 140, 255), (100, 70, 150), (60, 40, 100),
                    (16, 10, 36), 0.014, True, "stardust"), False, 0.004, (.07, .93)),
    _shop_map(3, "SOLAR TEMPLE", "Stepped golden terraces beneath a burning sky.",
              [(0, .35), (.08, .35), (.11, .5), (.18, .5), (.21, .65), (.28, .65), (.31, .8), (.4, .8), (.44, .98), (.5, .98)],
              Theme((16, 4, 8), (230, 100, 50), (90, 30, 40), (255, 230, 140), (255, 210, 110), (150, 100, 60), (80, 56, 50),
                    (28, 14, 20), 0.008, True, "embers"), False, 0.004, (.07, .93)),
)
_SHOP_BASE_MAPS = SHOP_MAPS
_M = _shop_map
_NEW_MAPS = (
    (  # cheap
        _M(0, "SLEEPY HOLLOW", "A gentle bowl: shells roll to the middle.", [(0, .4), (.2, .25), (.35, .2), (.5, .18)], "valley", True),
        _M(0, "TWIN HILLS", "Two matched hills with a flat between.", [(0, .2), (.1, .35), (.2, .2), (.35, .2), (.45, .4), (.5, .45)], "steppe", True),
        _M(0, "FANG ROW", "A long row of teeth.", [(0, .3), (.05, .4), (.1, .28), (.15, .4), (.2, .28), (.25, .4), (.3, .28), (.35, .4), (.4, .28), (.45, .4), (.5, .3)], "rust"),
        _M(0, "THE DITCH", "Flat ground and one deep, narrow ditch.", [(0, .35), (.4, .35), (.45, .05), (.5, .03)], "swamp"),
        _M(0, "MESA", "Two high mesas and a step down.", [(0, .5), (.2, .5), (.25, .3), (.5, .3)], "canyon"),
        _M(0, "BUMPY ROAD", "Nothing but small, random bumps.", [(0, .3), (.5, .32)], "waste", False, 0.08),
        _M(0, "WAVES", "Rolling swells and troughs.", [(0, .3), (.06, .42), (.12, .3), (.18, .18), (.24, .3), (.3, .42), (.36, .3), (.42, .18), (.5, .3)], "beach", True),
        _M(0, "STAIRCASE", "Climbing steps toward the middle.", [(0, .15), (.1, .15), (.12, .25), (.22, .25), (.24, .35), (.34, .35), (.36, .45), (.5, .45)], "alpine"),
        _M(0, "FOXHOLES", "Small pits to duck into.", [(0, .3), (.08, .3), (.1, .15), (.14, .15), (.16, .3), (.28, .3), (.3, .15), (.34, .15), (.36, .3), (.5, .3)], "valley"),
        _M(0, "LONE TREE", "One tall spire in a flat meadow.", [(0, .2), (.45, .2), (.48, .7), (.5, .72)], "jungle", False, 0.0, (.08, .92), "fireflies")),
    (  # mid
        _M(1, "NAVE", "Twin arch towers flanking a long hall.", [(0, .25), (.12, .25), (.14, .6), (.17, .6), (.19, .25), (.3, .25), (.34, .5), (.5, .5)], "midnight"),
        _M(1, "HANGING GARDENS", "Alternating green terraces.", [(0, .5), (.1, .5), (.12, .3), (.2, .3), (.22, .55), (.3, .55), (.32, .35), (.5, .35)], "jungle", False, 0.0, (.08, .92), "fireflies"),
        _M(1, "CREVASSE", "A glacier split by a deep crack.", [(0, .6), (.15, .6), (.2, .1), (.24, .1), (.28, .5), (.5, .5)], "arctic", False, 0.0, (.08, .92), "snow"),
        _M(1, "SLUDGE PITS", "Toxic pools between low banks.", [(0, .3), (.1, .3), (.14, .08), (.22, .08), (.26, .3), (.34, .3), (.38, .1), (.5, .1)], "toxic", False, 0.0, (.08, .92), "ash"),
        _M(1, "VOLCANO RIM", "A central caldera and ember rain.", [(0, .2), (.2, .2), (.3, .55), (.38, .7), (.42, .35), (.5, .3)], "volcano", False, 0.0, (.08, .92), "embers"),
        _M(1, "OASIS", "Dunes around a sunken oasis.", [(0, .4), (.12, .3), (.22, .45), (.34, .25), (.4, .12), (.5, .1)], "steppe", True),
        _M(1, "RAIL YARD", "Low walls like freight cars.", [(0, .2), (.1, .2), (.11, .35), (.14, .35), (.15, .2), (.3, .2), (.31, .35), (.34, .35), (.35, .2), (.5, .2)], "steel"),
        _M(1, "MOON BASE", "Cratered grey regolith.", [(0, .3), (.1, .3), (.14, .1), (.22, .1), (.26, .32), (.36, .32), (.4, .15), (.5, .15)], "moon", False, 0.0, (.08, .92), "stardust"),
        _M(1, "WINDMILL FIELD", "Hills with tall thin windmills.", [(0, .25), (.1, .35), (.12, .55), (.13, .35), (.25, .3), (.3, .5), (.31, .3), (.5, .25)], "valley"),
        _M(1, "BONE YARD", "Ribs of some enormous creature.", [(0, .2), (.08, .4), (.1, .2), (.16, .45), (.18, .2), (.24, .5), (.26, .2), (.32, .4), (.34, .2), (.5, .22)], "rust", False, 0.0, (.08, .92), "ash")),
    (  # pro
        _M(2, "THE SPIRAL", "Terraces wind up to a central summit.", [(0, .1), (.1, .1), (.12, .2), (.2, .2), (.22, .3), (.3, .3), (.32, .45), (.4, .45), (.42, .6), (.5, .6)], "cyber", False, 0.0, (.08, .92), "stardust"),
        _M(2, "SKYSCRAPER ROW", "A downtown of sheer towers.", [(0, .3), (.08, .3), (.09, .7), (.14, .7), (.15, .3), (.2, .3), (.21, .9), (.26, .9), (.27, .3), (.32, .3), (.33, .6), (.38, .6), (.39, .3), (.5, .3)], "midnight", False, 0.0, (.08, .92), "stardust", False, "skyline"),
        _M(2, "THE FUNNEL", "A huge V: everything slides inward.", [(0, .7), (.2, .55), (.35, .25), (.5, .04)], "steel"),
        _M(2, "ICE SPIKES", "Needles of frozen rock.", [(0, .3), (.06, .65), (.09, .3), (.15, .8), (.18, .3), (.25, .55), (.28, .3), (.5, .3)], "arctic", False, 0.0, (.08, .92), "snow"),
        _M(2, "LAVA FLOW", "Cooled cliffs stepping down to the fire.", [(0, .8), (.1, .8), (.12, .55), (.25, .55), (.27, .3), (.4, .3), (.42, .1), (.5, .1)], "volcano", False, 0.0, (.08, .92), "embers"),
        _M(2, "TWIN FORTS", "Two fortress blocks and a killing field.", [(0, .2), (.05, .2), (.06, .7), (.2, .7), (.21, .5), (.25, .5), (.26, .15), (.5, .15)], "rust", False, 0.0, (.08, .92), "", False, "castle"),
        _M(2, "CORAL REEF", "Organic, lumpy cover.", [(0, .2), (.05, .45), (.1, .3), (.16, .55), (.22, .25), (.28, .5), (.34, .3), (.4, .45), (.5, .3)], "beach", False, 0.0, (.08, .92), "fireflies"),
        _M(2, "TWIN CLIFFS", "Sheer cliffs at both edges.", [(0, .9), (.12, .9), (.14, .3), (.5, .1)], "canyon"),
        _M(2, "PIPE ORGAN", "Columns of rising height.", [(0, .2), (.04, .2), (.05, .35), (.1, .35), (.11, .5), (.16, .5), (.17, .65), (.22, .65), (.23, .8), (.28, .8), (.29, .3), (.5, .3)], "cyber"),
        _M(2, "SHATTERED MOON", "Floating-looking islands between bottomless gaps.", [(0, .4), (.06, .4), (.08, .05), (.12, .05), (.14, .55), (.2, .55), (.22, .05), (.26, .05), (.28, .45), (.34, .45), (.36, .05), (.5, .05)], "moon", False, 0.0, (.08, .92), "stardust")),
    (  # master tier
        _M(3, "OBSIDIAN SPIRES", "Jagged black glass over a lava sky.", [(0, .4), (.06, .8), (.1, .35), (.16, .95), (.2, .3), (.28, .85), (.34, .3), (.42, .98), (.5, .5)], _ECLIPSE, False, 0.004, (.07, .93)),
        _M(3, "AURORA FJORD", "A narrow valley under a curtain of light.", [(0, .98), (.12, .98), (.16, .5), (.2, .08), (.5, .05)], replace(_THEMES["arctic"], aurora=True, fx="snow"), False, 0.0, (.07, .93)),
        _M(3, "CRYSTAL CAVERNS", "A field of glittering crystal teeth.", [(0, .3), (.04, .6), (.08, .25), (.12, .8), (.16, .3), (.22, .7), (.26, .25), (.32, .9), (.36, .3), (.44, .75), (.5, .4)], _SANCTUM, False, 0.0, (.07, .93)),
        _M(3, "STARFALL PLATEAU", "A high plateau with a single spire.", [(0, .6), (.35, .6), (.4, .55), (.44, .55), (.46, .98), (.5, .98)], _ASTRAL, False, 0.003, (.07, .93)),
        _M(3, "SOLAR FORGE", "Stepped furnace terraces under a burning sky.", [(0, .15), (.08, .15), (.1, .3), (.18, .3), (.2, .5), (.28, .5), (.3, .7), (.38, .7), (.4, .9), (.5, .9)], _ECLIPSE, False, 0.0, (.07, .93)),
        _M(3, "NEBULA GARDENS", "Floating gardens in a violet river of stars.", [(0, .45), (.08, .45), (.1, .25), (.2, .25), (.22, .6), (.3, .6), (.32, .3), (.42, .3), (.44, .75), (.5, .75)], _ASTRAL, False, 0.0, (.07, .93)),
        _M(3, "TITAN'S THRONE", "A colossal stone chair at the centre.", [(0, .3), (.15, .3), (.16, .55), (.22, .55), (.23, .3), (.3, .3), (.31, .7), (.4, .7), (.41, .95), (.5, .95)], replace(_THEMES["steel"], aurora=True), False, 0.0, (.07, .93)),
        _M(3, "GLITCH ZONE", "Corrupted, chaotic terrain.", [(0, .4), (.5, .4)], replace(_THEMES["cyber"], aurora=True, fx="stardust"), False, 0.22, (.07, .93)),
        _M(3, "THE LABYRINTH", "A maze of tall and short walls.", [(0, .2), (.05, .2), (.06, .7), (.08, .7), (.09, .2), (.14, .2), (.15, .7), (.17, .7), (.18, .2), (.23, .2), (.24, .7), (.26, .7), (.27, .2), (.32, .2), (.33, .7), (.35, .7), (.36, .2), (.5, .2)], replace(_THEMES["midnight"], aurora=True), False, 0.0, (.07, .93)),
        _M(3, "CELESTIAL STEPS", "Giant stairs that climb into the aurora.", [(0, .1), (.06, .1), (.08, .22), (.16, .22), (.18, .36), (.26, .36), (.28, .5), (.36, .5), (.38, .66), (.5, .66)], _SANCTUM, False, 0.0, (.07, .93))),
)
_PREMIUM_ACCENT = (255, 70, 140)
_PREMIUM_MAPS = tuple(replace(m, accent=_PREMIUM_ACCENT) for m in (
    _M(3, "GLASS DESERT", "Dunes of fused glass under twin suns: every shell throws prisms.",
       [(0, .3), (.06, .42), (.12, .28), (.2, .5), (.28, .3), (.36, .44), (.44, .26), (.5, .34)],
       Theme((30, 10, 66), (255, 150, 104), (116, 62, 110), (255, 232, 170), (150, 232, 244), (92, 182, 204), (62, 112, 142), (20, 40, 72), 0.004, False, "stardust"), True, 0.01),
    _M(3, "LANTERN TERRACES", "Stepped temple terraces under a sky of rising lanterns.",
       [(0, .15), (.06, .15), (.08, .28), (.16, .28), (.18, .42), (.26, .42), (.28, .56), (.4, .56), (.42, .62), (.5, .62)],
       Theme((8, 6, 30), (196, 76, 62), (62, 22, 42), (255, 204, 124), (232, 172, 84), (152, 84, 52), (82, 42, 42), (30, 16, 24), 0.006, False, "fireflies", "pagoda")),
    _M(3, "WORLDTREE ROOTS", "Colossal glowing roots arch over bottomless hollows.",
       [(0, .45), (.04, .6), (.1, .2), (.16, .52), (.22, .18), (.3, .55), (.38, .22), (.44, .5), (.5, .35)],
       Theme((2, 14, 24), (40, 164, 134), (10, 62, 62), (192, 255, 232), (112, 242, 172), (52, 152, 112), (30, 82, 70), (10, 30, 34), 0.008, True, "fireflies"), True),
    _M(3, "WHALEFALL", "The bleached ribs of a sky-whale, arching over the dark.",
       [(0, .2), (.04, .5), (.08, .2), (.12, .55), (.16, .2), (.2, .6), (.24, .2), (.28, .55), (.32, .2), (.36, .5), (.4, .2), (.5, .25)],
       Theme((2, 6, 24), (32, 92, 164), (16, 42, 92), (204, 232, 255), (224, 232, 242), (162, 176, 202), (92, 102, 132), (30, 34, 60), 0.01, True, "stardust")),
    _M(3, "SHATTERLINE", "Floating plates of cracked glass above a prismatic void.",
       [(0, .4), (.05, .4), (.07, .02), (.1, .02), (.12, .5), (.2, .5), (.22, .02), (.26, .02), (.28, .62), (.36, .62), (.38, .02), (.44, .02), (.46, .45), (.5, .45)],
       Theme((10, 4, 28), (122, 62, 202), (62, 32, 112), (255, 255, 255), (222, 202, 255), (152, 132, 232), (92, 72, 172), (30, 20, 70), 0.012, True, "stardust")),
    # --- premium II ----------------------------------------------------------------------------------------------------
    _M(3, "MARIANA DEEP", "Ledges falling into a black trench; jellyfish drift up past the kelp.",
       [(0, .55), (.1, .55), (.14, .42), (.22, .4), (.27, .22), (.35, .2), (.4, .06), (.5, .04)],
       Theme((2, 10, 30), (14, 62, 96), (8, 30, 54), (90, 170, 190), (50, 140, 120), (30, 90, 84), (20, 50, 60), (8, 18, 28), 0.006, False, "plankton", "kelp")),
    _M(3, "TORII PATH", "A stone stair climbing through vermilion gates under a full moon.",
       [(0, .18), (.08, .18), (.1, .26), (.16, .26), (.18, .34), (.24, .34), (.26, .42), (.32, .42), (.34, .5), (.42, .5), (.44, .58), (.5, .58)],
       Theme((10, 6, 34), (120, 62, 124), (54, 30, 80), (255, 242, 222), (124, 150, 104), (92, 100, 72), (72, 58, 62), (30, 22, 30), 0.01, False, "sakura", "torii")),
    _M(3, "NEON GRIDLOCK", "Rain-slick rooftops between towers of flickering holograms.",
       [(0, .3), (.07, .3), (.08, .45), (.15, .45), (.16, .25), (.22, .25), (.23, .6), (.28, .6), (.29, .35), (.36, .35), (.37, .7), (.42, .7), (.43, .4), (.5, .4)],
       Theme((8, 4, 26), (150, 40, 120), (40, 16, 60), (255, 120, 220), (90, 230, 255), (60, 60, 90), (36, 30, 56), (14, 10, 26), 0.004, False, "rain", "holo")),
    _M(3, "PARADOX ENGINE", "Slabs of space adrift beneath a hypercube that should not exist.",
       [(0, .4), (.08, .4), (.1, .03), (.13, .03), (.15, .45), (.22, .55), (.24, .03), (.27, .03), (.29, .3), (.35, .38), (.37, .03), (.4, .03), (.42, .6), (.5, .6)],
       Theme((4, 2, 18), (80, 30, 140), (30, 14, 70), (220, 200, 255), (220, 200, 255), (150, 120, 230), (80, 60, 160), (26, 18, 60), 0.014, True, "stardust", "tesseract")),
    _M(3, "KAIJU BAY", "A flattened harbour. A footprint the size of a block. Something sleeps offshore.",
       [(0, .35), (.07, .35), (.08, .5), (.12, .5), (.13, .35), (.2, .32), (.24, .12), (.3, .1), (.34, .14), (.36, .4), (.4, .45), (.41, .25), (.5, .22)],
       Theme((14, 16, 30), (90, 100, 130), (40, 44, 60), (200, 220, 255), (110, 120, 130), (80, 84, 92), (56, 56, 64), (24, 24, 30), 0.003, False, "storm", "kaiju")),
    _M(3, "MYCELIA", "Soft rolling caps on a forest floor that glows from underneath.",
       [(0, .32), (.1, .4), (.2, .3), (.3, .45), (.4, .32), (.5, .38)],
       Theme((6, 10, 30), (60, 120, 130), (20, 40, 56), (190, 255, 220), (150, 230, 190), (70, 120, 100), (50, 60, 60), (20, 24, 28), 0.008, False, "spores", "shrooms"), True),
    _M(3, "WORM'S MAW", "Dunes sliding into the open throat of a sandworm.",
       [(0, .4), (.1, .48), (.18, .36), (.26, .5), (.34, .42), (.4, .2), (.44, .06), (.5, .03)],
       Theme((20, 12, 40), (240, 160, 110), (140, 90, 70), (255, 236, 200), (236, 196, 130), (200, 150, 96), (150, 100, 64), (70, 44, 30), 0.006, False, "sandfall", "wormarch"), True),
    _M(3, "SERPENT STAIRS", "Two stepped pyramids face each other across a jungle valley.",
       [(0, .2), (.06, .2), (.08, .3), (.12, .3), (.14, .4), (.18, .4), (.2, .5), (.24, .5), (.26, .4), (.3, .4), (.32, .3), (.36, .3), (.38, .18), (.5, .15)],
       Theme((40, 30, 80), (255, 170, 110), (60, 90, 70), (255, 220, 130), (90, 170, 100), (70, 120, 70), (90, 80, 60), (40, 34, 26), 0.002, False, "fireflies", "stepped")),
    _M(3, "ASTROLABE", "Brass rings turn across the stars above a curved brass floor.",
       [(0, .3), (.1, .42), (.18, .46), (.24, .4), (.28, .3), (.32, .2), (.38, .18), (.44, .3), (.48, .5), (.5, .52)],
       Theme((4, 6, 30), (50, 50, 120), (26, 28, 70), (255, 220, 140), (220, 190, 120), (170, 140, 80), (90, 76, 60), (30, 26, 30), 0.016, False, "stardust", "orrery"), True),
    _M(3, "GHOST REEF", "Wrecked galleons on a reef of fog; their lanterns are still lit.",
       [(0, .25), (.08, .25), (.1, .38), (.14, .42), (.18, .36), (.22, .2), (.27, .18), (.3, .32), (.33, .48), (.36, .46), (.38, .3), (.44, .22), (.5, .24)],
       Theme((2, 10, 16), (60, 110, 100), (20, 44, 46), (196, 255, 216), (120, 170, 150), (70, 110, 100), (46, 60, 60), (16, 24, 26), 0.01, False, "ghostlights", "wrecks")),
))
SHOP_MAPS = (_SHOP_BASE_MAPS[0:5] + _NEW_MAPS[0] + _SHOP_BASE_MAPS[5:10] + _NEW_MAPS[1] + _SHOP_BASE_MAPS[10:15] + _NEW_MAPS[2]
             + _SHOP_BASE_MAPS[15:20] + _NEW_MAPS[3] + _PREMIUM_MAPS)

_SPACE = Theme((2, 4, 24), (40, 70, 170), (16, 24, 80), (190, 220, 255), (170, 210, 255), (90, 120, 180), (50, 70, 120),
               (14, 20, 44), 0.014, True, "stardust")
_ROCK = Theme((4, 2, 14), (60, 50, 80), (24, 20, 40), (200, 190, 230), (170, 160, 190), (110, 100, 120), (70, 64, 80),
              (20, 18, 30), 0.014, True, "stardust")
_ALIEN = Theme((2, 10, 16), (30, 150, 110), (10, 60, 70), (150, 255, 190), (120, 255, 170), (60, 140, 110), (30, 80, 70),
               (8, 26, 30), 0.012, True, "stardust")
MISSION_MAPS: tuple[MapDefinition, ...] = (
    _shop_map(1, "BUNKER LINE", "Trenches and a ruined bunker under falling ash.",
              [(0, .3), (.1, .3), (.13, .12), (.2, .12), (.23, .3), (.3, .3), (.33, .45), (.4, .2), (.5, .2)], "rust", fx="ash"),
    _shop_map(1, "RADAR HILL", "A lonely hill crowned by a humming radar.",
              [(0, .2), (.2, .3), (.35, .6), (.4, .62), (.45, .5), (.5, .55)], "alpine", fx="fireflies"),
    _shop_map(2, "SHELLED FIELD", "A cratered field, still smouldering.",
              [(0, .3), (.08, .3), (.12, .12), (.18, .12), (.22, .32), (.3, .32), (.34, .14), (.4, .14), (.44, .34), (.5, .34)],
              "waste", fx="embers"),
    _shop_map(3, "SPACE ELEVATOR", "A cable to the stars rises from the middle of the field.",
              [(0, .25), (.25, .25), (.3, .4), (.4, .4), (.43, .98), (.5, .98)], _SPACE, False, 0.004, (.07, .93)),
    _shop_map(3, "ASTEROID FIELD", "Jagged rock in an endless starfield.",
              [(0, .4), (.06, .55), (.1, .3), (.16, .6), (.22, .25), (.3, .7), (.36, .3), (.42, .65), (.5, .5)], _ROCK, False, 0.004, (.07, .93)),
    _shop_map(3, "MOTHERSHIP", "The alien flagship's flight deck, lit in green.",
              [(0, .3), (.1, .3), (.14, .5), (.2, .5), (.24, .3), (.3, .3), (.34, .55), (.38, .55), (.42, .4), (.5, .6)],
              _ALIEN, False, 0.004, (.07, .93), "", True),
)
_K = lambda name, desc, half, theme, fx="", aurora=False, b="": _shop_map(3, name, desc, half, theme, False, 0.0, (.07, .93), fx, aurora, b)
TICKET_MAPS: tuple[MapDefinition, ...] = (
    _K("NEON SKYLINE", "A glittering city of towers behind the battlefield.", [(0, .3), (.15, .3), (.17, .5), (.22, .5), (.24, .3), (.34, .3), (.36, .4), (.5, .4)], "midnight", "stardust", False, "skyline"),
    _K("CLOCK PLAZA", "A vast clock tower rises over the plaza.", [(0, .3), (.2, .3), (.3, .2), (.5, .2)], "steel", "", False, "clock"),
    _K("FROZEN CATHEDRAL", "A cathedral of ice under the aurora.", [(0, .4), (.1, .4), (.15, .55), (.2, .4), (.35, .25), (.5, .25)], "arctic", "snow", True, "cathedral"),
    _K("SUN TEMPLE", "A great stepped temple catches the last light.", [(0, .25), (.12, .25), (.14, .4), (.22, .4), (.24, .55), (.32, .55), (.34, .7), (.5, .7)], _ECLIPSE, "", False, "temple"),
    _K("SUNKEN METROPOLIS", "Broken towers of a drowned city.", [(0, .15), (.1, .15), (.12, .35), (.15, .12), (.25, .12), (.28, .4), (.5, .1)], "midnight", "fireflies", False, "ruins"),
    _K("PYRAMID PLAIN", "Three pyramids on the horizon.", [(0, .2), (.2, .2), (.3, .3), (.5, .3)], "steppe", "ash", False, "pyramids"),
    _K("CHEMICAL WORKS", "Chimneys and sawtooth roofs, smoke in the air.", [(0, .3), (.1, .3), (.12, .15), (.2, .15), (.22, .3), (.5, .3)], "toxic", "ash", False, "factory"),
    _K("GOTHIC KEEP", "A castle of towers and battlements.", [(0, .25), (.15, .25), (.17, .6), (.24, .6), (.26, .25), (.5, .25)], "midnight", "", False, "castle"),
    _K("ORBITAL CITY", "A space station city above a blue world.", [(0, .35), (.2, .35), (.25, .5), (.35, .5), (.4, .35), (.5, .35)], _SPACE, "stardust", True, "station"),
    _K("PAGODA PEAK", "Tiered pagodas on a snowy summit.", [(0, .5), (.15, .5), (.2, .35), (.3, .35), (.35, .6), (.5, .6)], "alpine", "snow", False, "pagoda"),
)
_EMBER = Theme((16, 2, 6), (196, 54, 18), (70, 16, 12), (255, 160, 70), (56, 44, 50), (255, 120, 40), (60, 30, 32), (22, 10, 12), 0.003,
               False, "inferno", "volcano")
_TEMPEST = Theme((4, 16, 30), (40, 110, 140), (14, 44, 70), (190, 240, 255), (70, 100, 120), (120, 200, 230), (40, 70, 90), (14, 26, 40), 0.004,
                 True, "tempest", "isles")
_RIFT = Theme((4, 0, 18), (210, 170, 110), (46, 24, 90), (255, 244, 205), (46, 38, 86), (255, 226, 150), (40, 28, 76), (12, 8, 34), 0.012,
              True, "rift", "rift")
ANCIENT_MAPS: tuple[MapDefinition, ...] = tuple(replace(m, accent=a) for m, a in (
    (_shop_map(3, "EMBER SANCTUM", "A volcanic temple over a lava chasm. Pillars of basalt, rivers of fire.",
               [(0, .34), (.1, .34), (.12, .52), (.17, .52), (.19, .30), (.26, .30), (.28, .60), (.32, .60), (.34, .40), (.4, .18), (.45, .06), (.5, .04)],
               _EMBER, False, 0.006, (.07, .93)), (255, 150, 60)),
    (_shop_map(3, "TEMPEST SPIRES", "Storm-lashed spires above floating isles. Rain, wind and lightning.",
               [(0, .30), (.08, .30), (.10, .58), (.15, .58), (.17, .30), (.22, .30), (.24, .62), (.27, .62), (.29, .25), (.36, .25), (.38, .50), (.42, .50), (.44, .12), (.5, .12)],
               _TEMPEST, False, 0.0, (.07, .93)), (120, 232, 255)),
    (_shop_map(3, "ASTRAL RIFT", "The end of time: a colossal ring of light and dark turns over a shattered world.",
               [(0, .40), (.06, .40), (.08, .55), (.14, .55), (.16, .32), (.22, .32), (.25, .50), (.28, .70), (.31, .50), (.34, .30), (.40, .20), (.44, .46), (.47, .46), (.48, .20), (.5, .20)],
               _RIFT, False, 0.0, (.07, .93)), (214, 170, 255)),
))
SPECIAL_MAPS: tuple[MapDefinition, ...] = (FORGE_MAP, SPIRE_MAP, MASTER_MAP) + SHOP_MAPS + MISSION_MAPS + TICKET_MAPS + ANCIENT_MAPS
SPECIAL_MAP_BY_KEY = {m.key: m for m in SPECIAL_MAPS}
assert len({m.key for m in MAPS + SPECIAL_MAPS}) == len(MAPS) + len(SPECIAL_MAPS)


def all_maps() -> dict:
    return {m.key: m for m in MAPS + SPECIAL_MAPS}
