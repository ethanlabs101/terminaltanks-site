"""Tank and shell colours. COLOR_CHOICES are the plain colours; the animated paints (RGB, ASTRAL, PRISMATIC, VOID,
MOLTEN, ...) are a colour function plus an optional per-pixel shader (PAINT_PX). PAINT_UNLOCK says which shop item
unlocks each one."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

from tanks.colors import RGB, clamp, flicker, gradient, hsv, mix, shade


COLOR_CHOICES: tuple[tuple[str, RGB], ...] = (
    ("CYAN", (70, 220, 240)), ("BLUE", (74, 122, 255)), ("PURPLE", (156, 106, 240)),
    ("MAGENTA", (240, 84, 204)), ("RED", (240, 72, 72)), ("ORANGE", (255, 150, 52)),
    ("YELLOW", (250, 222, 72)), ("GREEN", (92, 222, 112)), ("WHITE", (236, 241, 246)),
    ("AQUA", (60, 230, 190)), ("TEAL", (40, 170, 160)), ("LIME", (170, 235, 70)),
    ("OLIVE", (140, 160, 70)), ("GOLD", (240, 185, 50)), ("COPPER", (200, 110, 70)),
    ("CRIMSON", (190, 40, 70)), ("PINK", (255, 140, 190)), ("VIOLET", (110, 70, 200)),
    ("COBALT", (50, 80, 200)), ("SKY", (130, 190, 255)), ("SILVER", (180, 190, 200)),
    ("STEEL", (110, 125, 145)), ("SAND", (214, 190, 140)), ("OBSIDIAN", (70, 74, 92)),
)

# A sentinel colour: whatever holds it is drawn as a slowly cycling rainbow (the RGB hull / RGB shell unlocks).
RAINBOW: RGB = (250, 3, 251)


ASTRAL: RGB = (251, 4, 250)          # second sentinel: the Astral Rift paint (Martyr reward), selectable for hull AND shell
PRISMATIC: RGB = (252, 6, 247)       # shop paint: the Prismatic King's refracting crystal, on ANY tank
VOID: RGB = (247, 2, 252)            # shop paint: the Singularity's light-eating void, on ANY tank
MOLTEN: RGB = (246, 3, 253)          # shop paint: cooling lava, black crust over glowing cracks
CHROME: RGB = (253, 5, 246)          # shop paint: liquid mirror metal with a travelling highlight
AURORA: RGB = (245, 4, 249)          # shop paint: northern lights rippling over a night-sky hull
CIRCUIT: RGB = (249, 6, 245)         # shop paint: a circuit board with signals racing along its traces
OCEAN: RGB = (244, 5, 250)           # shop paint: deep water with sunlight caustics dancing over it
SYNTHWAVE: RGB = (250, 7, 244)       # shop paint: a black hull with a neon grid scrolling into a magenta sunset
TOXIC: RGB = (243, 6, 251)           # shop paint: glowing radioactive ooze dripping over a black hull, bubbling
GILDED: RGB = (251, 8, 243)          # shop paint: gold leaf with engraved scrollwork and a travelling glint


_GALAXY = ((0, (24, 14, 96)), (0.2, (96, 44, 190)), (0.4, (196, 64, 196)), (0.6, (56, 160, 220)), (0.8, (232, 232, 255)), (1.0, (24, 14, 96)))


def galaxy(t: float, c: float, r: float) -> RGB:
    """Per-pixel drifting nebula with twinkling stars: what the ASTRAL paint looks like on a hull."""
    v = (math.sin(c * 0.55 + t * 1.1) + math.sin(r * 0.9 - t * 0.8) + math.sin((c + r) * 0.45 + t * 0.6) + 3) / 6
    col = gradient(_GALAXY, round(v * 24) / 24)
    if flicker(t * 1.4, c * 7 + r * 3, 23) > 0.93:
        return (255, 255, 255)
    return col


def astral(t: float) -> RGB:
    """Slowly shifting Astral Rift colours: deep indigo -> violet -> starlight white -> gold -> back."""
    return gradient(_GALAXY, round((t * 0.18 % 1.0) * 48) / 48)


def prismatic(t: float) -> RGB:
    return hsv(round((t * 0.3 % 1.0) * 36) / 36, 0.35, 1.0)


def void_tint(t: float) -> RGB:
    return mix((90, 54, 190), (176, 120, 255), 0.5 + 0.5 * math.sin(t * 2.4))


def prismatic_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel refraction: a pale crystal whose facets drift through the whole spectrum, with white glints."""
    if flicker(t * 1.6, c * 5 + r * 11, 29) > 0.94:
        return (255, 255, 255)
    hue = (c * 0.05 + r * 0.035 + t * 0.3 + 0.12 * math.sin(c * 0.9 - r * 0.6 + t * 1.7)) % 1
    return hsv(round(hue * 48) / 48, 0.40 + 0.2 * math.sin(r * 0.5 + t), 1.0)


def void_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel void: near-black violet that ripples slowly and swallows light, with rare violet glints."""
    if flicker(t * 1.2, c * 3 + r * 7, 31) > 0.95:
        return (176, 126, 255)
    v = (math.sin(c * 0.7 + t * 1.3) + math.sin(r * 1.1 - t * 0.9) + 2) / 4
    return mix((6, 3, 18), (54, 30, 118), v)


def molten_tint(t: float) -> RGB:
    return mix((255, 84, 20), (255, 196, 70), round((0.5 + 0.5 * math.sin(t * 2.2)) * 16) / 16)


def chrome_tint(t: float) -> RGB:
    return mix((150, 160, 182), (250, 252, 255), round((0.5 + 0.5 * math.sin(t * 1.6)) * 16) / 16)


_AURORA = ((0, (40, 240, 150)), (0.35, (60, 200, 255)), (0.7, (170, 90, 255)), (1.0, (40, 240, 150)))


def aurora_tint(t: float) -> RGB:
    return gradient(_AURORA, round((t * 0.12 % 1.0) * 36) / 36)


def circuit_tint(t: float) -> RGB:
    return mix((30, 170, 100), (170, 255, 210), round((0.5 + 0.5 * math.sin(t * 3.0)) * 16) / 16)


def molten_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel lava: a black-red crust split by glowing cracks that slowly crawl and breathe."""
    crack = abs(math.sin(c * 0.85 + 1.8 * math.sin(r * 0.7 + t * 0.35) + r * 0.45))
    if crack < 0.2:
        heat = 0.5 + 0.5 * math.sin(t * 2.6 + c * 0.4 - r * 0.3)
        return mix((255, 96, 18), (255, 226, 120), round(heat * (1 - crack * 5) * 8) / 8)
    if crack < 0.32:
        return (150, 40, 14)
    v = (math.sin(c * 0.3 + r * 0.8) + 1) / 2
    return mix((34, 12, 10), (70, 24, 16), round(v * 4) / 4)


def chrome_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel mirror metal: sky above, dark ground below, and a bright highlight sliding along the hull."""
    sky = clamp(r / 7.0, 0, 1)
    base = mix((52, 58, 74), (214, 222, 236), round(sky * 6) / 6)
    band = (c + r * 0.7 - t * 9.0) % 26
    if band < 1.2:
        return (255, 255, 255)
    if band < 2.6:
        return mix(base, (255, 255, 255), 0.55)
    if (int(c) + int(r)) % 9 == 0 and flicker(t, c * 5 + r, 37) > 0.9:
        return (255, 255, 255)
    return base


def aurora_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel northern lights: green and violet curtains rippling over a deep night-blue hull."""
    wave = math.sin(c * 0.32 + t * 0.9 + 1.6 * math.sin(r * 0.55 + t * 0.45))
    glow = clamp((wave + 0.7) * 0.7, 0.3, 1)
    if flicker(t * 0.8, c * 9 + r * 5, 41) > 0.96:
        return (230, 240, 255)
    curtain = gradient(_AURORA, (c * 0.045 + r * 0.09 + t * 0.06) % 1.0)
    return mix((6, 12, 34), curtain, round(glow * 8) / 8)


def circuit_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel circuit board: dark green fibreglass, copper traces, and signals racing along them."""
    ic, ir = int(c), int(r)
    trace = ir % 3 == 1 or (ic % 5 == 2 and ir % 3 != 0)
    if not trace:
        return (10, 34, 26) if (ic + ir) % 2 else (14, 40, 30)
    if ic % 5 == 2 and ir % 3 == 1:
        return (200, 170, 90)                                  # a solder pad where traces meet
    pulse = (c * 1.0 + r * 2.0 - t * 14.0) % 17
    if pulse < 1.6:
        return (170, 255, 210)
    if pulse < 3.2:
        return (70, 210, 140)
    return (40, 110, 76)


def ocean_tint(t: float) -> RGB:
    return mix((20, 110, 190), (120, 230, 255), round((0.5 + 0.5 * math.sin(t * 1.8)) * 16) / 16)


def synthwave_tint(t: float) -> RGB:
    return mix((255, 60, 200), (60, 230, 255), round((0.5 + 0.5 * math.sin(t * 2.0)) * 16) / 16)


def ocean_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel deep water: blue that darkens downward, with bright caustic lines rippling across it like sun
    through waves, and the odd rising bubble."""
    depth = clamp(1 - r / 8.0, 0, 1)
    base = mix((6, 40, 92), (20, 110, 170), round((1 - depth) * 5) / 5)
    a = math.sin(c * 0.62 + t * 1.7 + math.sin(r * 0.9 - t * 1.1) * 1.4)
    b = math.sin(c * 0.41 - r * 0.73 - t * 1.3)
    caustic = 1 - abs(a + b) * 0.8
    if caustic > 0.72:
        return mix(base, (170, 245, 255), round(min(1.0, (caustic - 0.72) * 3.6) * 6) / 6)
    if flicker(t * 1.1, c * 13 + r * 7, 43) > 0.97:
        return (200, 240, 255)
    return base


def synthwave_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel outrun: a violet-to-magenta sunset on the upper hull, a cyan horizon, and a black floor below with a
    magenta grid scrolling toward you."""
    ir = int(r)                                                # rows count down from the top of the tank
    if ir <= 2:
        if ir == 2 and int(c + t * 4) % 7 < 2:
            return (255, 214, 120)                            # sun glints sliding along the horizon
        return gradient(((0, (80, 24, 140)), (0.5, (190, 50, 200)), (1, (255, 90, 150))), round(ir / 2 * 6) / 6)
    if ir == 3:
        return (70, 230, 255)
    if (int(c) - 2) % 5 == 0 or (int(r - t * 2.5) % 2 == 0 and int(c) % 2 == 0):
        return (230, 50, 190)
    return (14, 4, 26)


def toxic_tint(t: float) -> RGB:
    return mix((90, 220, 40), (200, 255, 90), round((0.5 + 0.5 * math.sin(t * 2.8)) * 16) / 16)


def gilded_tint(t: float) -> RGB:
    return mix((200, 150, 50), (255, 236, 150), round((0.5 + 0.5 * math.sin(t * 1.7)) * 16) / 16)


def toxic_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel radioactive ooze: glowing lime slime running down a near-black hull in slow drips, with bubbles that
    swell and pop."""
    ic = int(c)
    seed = (ic * 2654435761) & 0xFFFF
    drip_len = 1.5 + (seed % 5) * 0.7 + 1.2 * math.sin(t * (0.6 + (seed % 7) * 0.1) + seed)
    if r < drip_len:
        glow = 0.6 + 0.4 * math.sin(t * 3 + c * 0.7 - r)
        tip = r > drip_len - 1
        return mix((60, 170, 30), (190, 255, 80), round(glow * 6) / 6) if not tip else (220, 255, 120)
    if flicker(t * 1.3, c * 11 + r * 5, 47) > 0.95:
        return (210, 255, 120)                                 # a bubble popping
    return mix((10, 22, 10), (24, 46, 18), round(((math.sin(c * 0.5 + r * 0.8) + 1) / 2) * 3) / 3)


def gilded_px(t: float, c: float, r: float) -> RGB:
    """Per-pixel gold leaf: warm gold shading top to bottom, engraved scrollwork in a darker gold, and a glint that
    sweeps across now and then."""
    shade_k = clamp(r / 7.0, 0, 1)
    base = mix((255, 222, 120), (170, 110, 30), round(shade_k * 5) / 5)
    scroll = math.sin(c * 0.9 + math.sin(r * 1.3) * 2.2) * math.cos(r * 0.8 - c * 0.3)
    if abs(scroll) < 0.12:
        base = mix(base, (110, 66, 16), 0.6)                    # the engraving
    band = (c - r * 0.5 - t * 7.0) % 30
    if band < 1.4:
        return (255, 252, 230)
    if band < 3.0:
        return mix(base, (255, 248, 210), 0.5)
    return base


def paint_shade(paint: RGB, gb: RGB, ch: str) -> RGB:
    if paint == VOID:
        return {"t": mix(gb, (120, 80, 210), 0.22), "g": mix(gb, (180, 130, 255), 0.55), "k": shade(gb, 0.6),
                "w": mix(gb, (90, 70, 150), 0.3), "d": shade(gb, 0.7)}.get(ch, gb)
    return {"t": mix(gb, (255, 255, 255), 0.15), "g": mix(gb, (255, 255, 255), 0.4), "k": shade(gb, 0.45),
            "w": mix(gb, (200, 210, 230), 0.2), "d": shade(gb, 0.5)}.get(ch, gb)


def live_color(c: RGB, t: float) -> RGB:
    """What a stored colour looks like at time t: animated paints resolve to their tint, plain colours to themselves."""
    if c not in LIVE_COLORS:
        return c
    return _TINTS[c](t)


def rainbow(t: float) -> RGB:
    return hsv(round((t * 0.35 % 1.0) * 36) / 36, 0.85, 1.0)      # 36 steps keeps the colour cache tiny


@dataclass(frozen=True)
class AnimatedPaint:
    """A paint that moves. Wherever a colour is stored (loadouts, tanks, shells) the paint is its `sentinel`, a reserved
    colour that is never drawn as itself; `tint` is its colour at time t (shells, trails, swatches, and the whole hull when
    there is no `px`); `px` paints a hull pixel by pixel as (t, column, row) -> colour."""
    name: str
    sentinel: RGB
    tint: Callable[[float], RGB]
    px: Optional[Callable[[float, float, float], RGB]] = None


ANIMATED_PAINTS = (                                            # colour-picker order; unlocked by "paint:<name>" (RGB: "rgb:hull" / "rgb:shell")
    AnimatedPaint("RGB", RAINBOW, rainbow), AnimatedPaint("ASTRAL", ASTRAL, astral, galaxy),
    AnimatedPaint("PRISMATIC", PRISMATIC, prismatic, prismatic_px), AnimatedPaint("VOID", VOID, void_tint, void_px),
    AnimatedPaint("MOLTEN", MOLTEN, molten_tint, molten_px), AnimatedPaint("CHROME", CHROME, chrome_tint, chrome_px),
    AnimatedPaint("AURORA", AURORA, aurora_tint, aurora_px), AnimatedPaint("CIRCUIT", CIRCUIT, circuit_tint, circuit_px),
    AnimatedPaint("OCEAN", OCEAN, ocean_tint, ocean_px), AnimatedPaint("SYNTHWAVE", SYNTHWAVE, synthwave_tint, synthwave_px),
    AnimatedPaint("TOXIC", TOXIC, toxic_tint, toxic_px), AnimatedPaint("GILDED", GILDED, gilded_tint, gilded_px),
)
ANIM_PAINTS = tuple((p.name, p.sentinel) for p in ANIMATED_PAINTS)
PIXEL_PAINTS = tuple(p.sentinel for p in ANIMATED_PAINTS if p.px)     # paints that colour every hull pixel individually
LIVE_COLORS = tuple(p.sentinel for p in ANIMATED_PAINTS)              # animated sentinels (re-rolled each frame by BattleWorld)
PAINT_PX = {p.sentinel: p.px for p in ANIMATED_PAINTS if p.px}
_TINTS = {p.sentinel: p.tint for p in ANIMATED_PAINTS}
assert len(set(LIVE_COLORS)) == len(LIVE_COLORS) and not set(LIVE_COLORS) & {c for _, c in COLOR_CHOICES}   # sentinels are unique

COLOR_BY_NAME = dict(COLOR_CHOICES)
for _n, _c in ANIM_PAINTS:
    COLOR_BY_NAME[_n] = _c
PAINTS = list(COLOR_CHOICES) + list(ANIM_PAINTS)
PAINT_BY_KEY = {n.lower(): c for n, c in ANIM_PAINTS if n != "RGB"}
PAINT_UNLOCK = {"RGB": ("rgb:hull", "rgb:shell")}
PAINT_UNLOCK.update({n: (f"paint:{n.lower()}", f"paint:{n.lower()}") for n, _ in ANIM_PAINTS if n != "RGB"})


def paint_index(name: str) -> int:
    return next((i for i, (n, _) in enumerate(PAINTS) if n == name), 0)


def color_index(name: str, default: int = 0) -> int:
    return next((i for i, (n, _) in enumerate(COLOR_CHOICES) if n == name), default)
