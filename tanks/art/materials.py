"""Material pixels for tank masks: the letters beyond the basic palette (prism, fire, void, gold, rune, ...), each a
function of position and time."""
from __future__ import annotations

import math
from typing import Callable

from tanks.colors import clamp, flicker, gradient, hsv, mix, shade


# ---- Material pixels in tank masks: letters beyond the basic t/h/g/k/w/d/a/l palette. A material is a function
# (body, accent, t, col, row, flash) -> colour, so any design can use crystal, fire, void or storm pixels.
def _mat_prism(body, a, t, c, r, f):          # a refracting crystal facet: hue shifts across the tank and in time
    return hsv(t * 0.35 + c * 0.085 + r * 0.14, 0.62, 1.0)


def _mat_prism_hi(body, a, t, c, r, f):       # a bright glint travelling across the crystal
    k = max(0.0, 1 - abs((c + r) - ((t * 7) % 18 - 3)) / 2.2)
    return mix(hsv(t * 0.35 + c * 0.085 + r * 0.14, 0.25, 1.0), (255, 255, 255), k)


def _mat_fire(body, a, t, c, r, f):           # licking flame
    k = clamp(0.55 + 0.45 * math.sin(t * 21 + c * 2.3 + r * 1.7) * math.sin(t * 9 + c), 0, 1)
    return gradient(((0, (150, 20, 8)), (0.5, (255, 110, 20)), (1, (255, 236, 120))), k)


def _mat_ember(body, a, t, c, r, f):          # glowing-hot armour that breathes
    return gradient(((0, shade(body, 0.4)), (1, (255, 90, 30))), 0.5 + 0.5 * math.sin(t * 3 + c * 0.9 + r))


def _mat_void(body, a, t, c, r, f):
    return mix((8, 4, 20), (110, 50, 200), 0.5 + 0.5 * math.sin(t * 4 + c * 0.8 - r))


def _mat_bolt(body, a, t, c, r, f):
    return (240, 248, 255) if flicker(t, c * 7 + r, 11) > 0.84 else mix(shade(body, 0.35), a, 0.45)


def _mat_gold(body, a, t, c, r, f):
    k = max(0.0, 1 - abs((c * 1.3 + r) - ((t * 6) % 20 - 4)) / 2.5)
    return mix((196, 150, 50), (255, 244, 180), k)


MATERIALS: dict[str, Callable] = {"p": _mat_prism, "q": _mat_prism_hi, "f": _mat_fire, "e": _mat_ember, "v": _mat_void,
                                  "b": _mat_bolt, "y": _mat_gold}


def _mat_solar(body, a, t, c, r, f):
    return gradient(((0, (255, 130, 30)), (0.5, (255, 222, 96)), (1, (255, 255, 236))), 0.5 + 0.5 * math.sin(t * 5 - r * 1.6 + c * 0.45))


def _mat_rune(body, a, t, c, r, f):
    if flicker(t * 0.7, c * 3 + r, 13) > 0.78:
        return (255, 244, 190)
    return mix((140, 100, 28), (226, 176, 70), 0.5 + 0.5 * math.sin(t * 2.4 + c * 0.9 - r))


def _mat_star(body, a, t, c, r, f):
    return mix((196, 212, 255), (255, 255, 255), 0.5 + 0.5 * math.sin(t * 9 + c * 2.1 + r))


def _mat_night(body, a, t, c, r, f):
    if flicker(t * 0.8, c * 5 + r, 17) > 0.93:
        return (226, 206, 255)
    return mix((10, 6, 26), (74, 32, 146), 0.5 + 0.5 * math.sin(t * 2 + c * 0.7 + r))


def _mat_aether(body, a, t, c, r, f):
    return mix((20, 110, 150), (150, 255, 240), 0.5 + 0.5 * math.sin(t * 3.5 - c * 0.9 + r * 0.6))


def _mat_chrono(body, a, t, c, r, f):
    k = max(0.0, 1 - abs((c + r * 2) - ((t * 8) % 24 - 6)) / 2.2)
    return mix(mix((120, 70, 30), (232, 172, 72), 0.5 + 0.5 * math.sin(t * 1.5 + c)), (255, 250, 222), k)


MATERIALS.update({"o": _mat_solar, "r": _mat_rune, "s": _mat_star, "n": _mat_night, "m": _mat_aether, "z": _mat_chrono})


def _mat_abyss(body, a, t, c, r, f):          # deep-water hide: caustic light rippling over dark blue
    return mix((8, 20, 46), (34, 78, 126), 0.5 + 0.5 * math.sin(t * 1.3 + c * 0.7 + r * 1.1) * math.sin(t * 0.7 - c * 0.4))


def _mat_biolume(body, a, t, c, r, f):        # bioluminescent spots: a slow wave of light, a rare white flash
    if flicker(t * 0.5, c * 3 + r, 29) > 0.96:
        return (240, 255, 255)
    return mix((18, 80, 130), (140, 255, 236), 0.5 + 0.5 * math.sin(t * 4 - c * 0.9 + r))


def _mat_foxfire(body, a, t, c, r, f):
    k = clamp(0.55 + 0.45 * math.sin(t * 19 + c * 2.1 + r * 1.3) * math.sin(t * 7 + c), 0, 1)
    return gradient(((0, (40, 60, 200)), (0.5, (90, 180, 255)), (1, (236, 250, 255))), k)


def _mat_spirit(body, a, t, c, r, f):         # white spirit-fur with a gold sheen sweeping across
    return mix((232, 228, 244), (255, 214, 140), 0.7 * max(0.0, 1 - abs((c + r * 1.5) - ((t * 5) % 20 - 4)) / 2.5))


def _mat_holo(body, a, t, c, r, f):           # hard-light hologram: scanlines, shimmer and the odd magenta glitch
    if flicker(t * 0.6, c, r + 40) > 0.95:
        return (255, 60, 200)
    if (int(t * 14) + r) % 6 == 0:
        return (210, 255, 255)
    return mix((18, 50, 100), (90, 230, 255), 0.55 + 0.3 * math.sin(t * 6 + r * 2 + c * 0.3))


def _mat_hardsteel(body, a, t, c, r, f):      # katana steel: a glint sliding along the edge
    return mix((150, 162, 184), (255, 255, 255), max(0.0, 1 - abs((c - r) - ((t * 9) % 22 - 5)) / 1.8))


def _mat_wire(body, a, t, c, r, f):           # the tesseract's edges: violet light folding along the wire
    k = max(0.0, 1 - abs((c + r) - ((t * 7) % 20 - 4)) / 2.0)
    return mix(hsv(0.74 + 0.08 * math.sin(t * 2 + c * 0.5), 0.45, 1.0), (255, 255, 255), k)


def _mat_hypervoid(body, a, t, c, r, f):      # the space inside the cube: dark with drifting stars
    if flicker(t * 0.4, c * 3 + r, 23) > 0.9:
        return (240, 236, 255)
    return mix((6, 4, 20), (52, 22, 112), 0.5 + 0.5 * math.sin(t * 1.7 + c * 0.6 - r))


def _mat_scales(body, a, t, c, r, f):         # kaiju scales: an armoured checker that shifts as it breathes
    k = (c + (r % 2)) % 2
    return mix((26, 40, 34), (78, 108, 90), 0.25 + 0.3 * k + 0.15 * math.sin(t * 1.2 + c))


def _mat_atomic(body, a, t, c, r, f):         # dorsal plates: a charge climbing from tail to head before the roar
    k = max(0.0, 1 - abs(c - ((t * 6) % 16 - 3)) / 2.5)
    return mix((40, 90, 170), (220, 244, 255), 0.35 + 0.65 * k)


def _mat_cap(body, a, t, c, r, f):            # mushroom cap: crimson-violet with glowing spots
    if (c * 3 + r * 5) % 7 == 0:
        return mix((255, 240, 200), (170, 255, 220), 0.5 + 0.5 * math.sin(t * 2.5 + c))
    return mix((140, 26, 56), (206, 64, 116), 0.5 + 0.5 * math.sin(t * 1.5 + c * 0.6))


def _mat_spore(body, a, t, c, r, f):
    return mix((50, 170, 130), (210, 255, 226), 0.5 + 0.5 * math.sin(t * 3.3 + c * 1.7 + r))


def _mat_worm(body, a, t, c, r, f):           # sandworm rings rippling down the body
    return mix((112, 74, 38), (218, 174, 104), 0.5 + 0.5 * math.sin(c * 1.6 - t * 3 + r * 0.4))


def _mat_maw(body, a, t, c, r, f):            # the furnace-hot throat
    return gradient(((0, (90, 20, 10)), (0.6, (240, 110, 40)), (1, (255, 222, 150))), 0.5 + 0.5 * math.sin(t * 8 + c * 1.3))


def _mat_jade(body, a, t, c, r, f):           # carved jade threaded with gold veins
    if abs(math.sin(c * 1.3 + r * 2.1 + t * 0.6)) < 0.14:
        return (250, 214, 120)
    return mix((18, 104, 76), (96, 214, 156), 0.5 + 0.5 * math.sin(t * 1.1 + c * 0.5 + r))


def _mat_plume(body, a, t, c, r, f):          # quetzal feathers: iridescent green-blue with crimson tips
    if (c + r) % 5 == 0:
        return mix((220, 50, 50), (255, 150, 90), 0.5 + 0.5 * math.sin(t * 3 + c))
    return hsv(0.40 + 0.10 * math.sin(t * 1.8 + c * 0.5 + r * 0.8), 0.75, 0.95)


def _mat_chart(body, a, t, c, r, f):          # a star chart: midnight blue, a faint grid, twinkling stars
    if (c * 7 + r * 3) % 9 == 0:
        return mix((140, 150, 220), (255, 250, 220), 0.5 + 0.5 * math.sin(t * 6 + c * 2))
    return (36, 52, 120) if c % 4 == 0 else mix((12, 18, 56), (24, 34, 90), 0.5 + 0.5 * math.sin(t + c * 0.4))


def _mat_goldline(body, a, t, c, r, f):
    return mix((176, 136, 56), (255, 240, 180), 0.5 + 0.5 * math.sin(t * 5 + c * 1.1))


def _mat_ghostwood(body, a, t, c, r, f):      # spectral planks, a green shimmer running along the grain
    k = max(0.0, 1 - abs(c - ((t * 4 + r * 3) % 18 - 3)) / 3.0)
    return mix(mix((24, 44, 46), (50, 86, 82), 0.5 + 0.5 * math.sin(c * 2.2 + r)), (120, 255, 170), 0.45 * k)


def _mat_ghostfire(body, a, t, c, r, f):
    k = clamp(0.5 + 0.5 * math.sin(t * 17 + c * 2.3 + r) * math.sin(t * 6 + c * 0.7), 0, 1)
    return gradient(((0, (20, 90, 50)), (0.5, (90, 255, 150)), (1, (224, 255, 234))), k)


MATERIALS.update({"J": _mat_abyss, "U": _mat_biolume, "F": _mat_foxfire, "X": _mat_spirit, "H": _mat_holo, "K": _mat_hardsteel,
                  "Q": _mat_wire, "Z": _mat_hypervoid, "R": _mat_scales, "N": _mat_atomic, "M": _mat_cap, "S": _mat_spore,
                  "W": _mat_worm, "O": _mat_maw, "E": _mat_jade, "P": _mat_plume, "C": _mat_chart, "G": _mat_goldline,
                  "B": _mat_ghostwood, "L": _mat_ghostfire})
