"""Album art: a cover and a spinning disc for every song, composed from the song's name, mood and family."""
from __future__ import annotations

import math
import re
import zlib
from typing import Optional

from tanks.audio.director import family_of, song_group
from tanks.colors import RGB, clamp, gradient, hsv, mix
from tanks.content.songs import SONGS


SONG_GROUP_LABEL = {"menu": "HOME SCREEN", "battle": "BATTLEFIELD", "tbos": "TOURNAMENT BOSS", "mission": "MISSION", "ticket": "ANCIENT HOARDER",
                    "martyr": "THE MARTYR", "story": "STORY"}


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
SCALE_NAMES = {"maj": "MAJOR", "min": "MINOR", "dor": "DORIAN", "phr": "PHRYGIAN", "lyd": "LYDIAN", "mix": "MIXOLYDIAN", "hmin": "HARMONIC MINOR",
                "phd": "PHRYGIAN DOMINANT", "hung": "HUNGARIAN MINOR", "pent": "PENTATONIC", "mpent": "MINOR PENTATONIC", "wt": "WHOLE TONE",
                "loc": "LOCRIAN", "insen": "IN SEN"}


_CV_RULES = (
    # (words in the song's name or blurb, layers it asks for). First match per layer wins; the name is read before the blurb.
    ("kernel_panic glitch paradox", "sky=void icon=glitch fx=glitch"),
    ("protector universe eternal", "sky=gold orb=nova icon=shield fx=stars"),
    ("blessing martyr's", "sky=gold orb=nova icon=cross fx=rays"),
    ("time_machine arcane", "sky=night icon=hourglass fx=stars"),
    ("rift portal hypergate gate horizon wormhole", "icon=portal sky=space"),
    ("quasar pulsar supernova", "orb=nova sky=space"),
    ("volcano volcanic caldera eruption", "ground=volcano"),
    ("tesseract cube dimensions", "sky=space icon=cube fx=stars"),
    ("orrery astrolabe", "sky=space icon=orrery fx=stars"),
    ("chronos clockwork clock gear gears magistrate court", "sky=dusk icon=gear"),
    ("throne crown tyrant king regent emperor pharaoh master's", "icon=crown"),
    ("master", "icon=crown sky=inferno"),
    ("kaiju", "icon=kaiju ground=city sky=night fx=rays"),
    ("whale whalefall", "icon=whale"),
    ("worm worm's maw", "icon=worm ground=dunes"),
    ("serpent snake rattler jade", "icon=snake"),
    ("torii shrine spirit", "icon=torii fx=fireflies"),
    ("lantern lanterns", "icon=lantern fx=lanterns sky=dusk"),
    ("jellyfish biolume", "icon=jelly sky=deep fx=bubbles"),
    ("shroom glowshroom mushroom mycelia spores", "icon=mushroom fx=spores sky=fog"),
    ("worldtree roots tree canopy", "icon=tree"),
    ("armada ship ships corsair shanty sailors", "icon=ship ground=sea"),
    ("mothership flagship", "icon=mothership sky=night"),
    ("saucer saucers ufo invasion contact", "icon=saucer"),
    ("radar dish dishes", "icon=radar"),
    ("ghost ghosts specter haunt haunted dancers voice", "icon=ghost fx=fog"),
    ("skull bone bones yard revenant graveyard", "icon=skull"),
    ("eye overseer sentinel watching", "icon=eye"),
    ("crystal crystals geode prism shatterline glass", "icon=crystal"),
    ("stinger buzz", "icon=bee"),
    ("warden gate gates key", "icon=key"),
    ("colossus titan titans giant", "icon=colossus"),
    ("bastion fortress walls citadel ramparts keep castle", "ground=castle"),
    ("zephyr gale wind tornado cyclone maelstrom", "icon=swirl sky=storm"),
    ("tempest storm thunder lightning volt capacitor spire", "icon=bolt sky=storm fx=rain"),
    ("helios nova solar solaris corona", "orb=nova sky=inferno"),
    ("wrath rage fury", "sky=inferno"),
    ("sun sunset sunrise evening", "orb=sun sky=dusk"),
    ("glacier frost frozen ice snow arctic tundra winter cryo", "icon=snowflake fx=snow sky=night"),
    ("magma lava volcano molten volcanic caldera ember embers forge obsidian inferno cinders ash", "icon=flame fx=embers sky=inferno"),
    ("toxic sludge miasma baron poison", "icon=skull sky=toxic fx=bubbles"),
    ("arcade cartridge chip eight_bits", "icon=invader sky=neon"),
    ("armory shop", "icon=shell sky=dusk"),
    ("workshop spanners sparks", "icon=wrench fx=sparks"),
    ("training", "icon=target sky=day"),
    ("tank tanks treads artillery anthem", "icon=tank"),
    ("squad co-op", "icon=tanks2"),
    ("boss_rush", "icon=crowns"),
    ("tavern ale", "icon=mug fx=embers sky=dusk"),
    ("lullaby music_box", "icon=note fx=snow"),
    ("pyramid pharaoh sand desert dune dunes mirage", "ground=dunes sky=dusk"),
    ("twin_suns twin", "orb=twinsun"),
    ("three_moons", "orb=threemoon"),
    ("harvest_moon", "orb=bigmoon"),
    ("moon moonlight moonscape lunar", "orb=moon"),
    ("star stars starlight starfall nebula galaxy cosmic orbital orbit space void astral rift light-years", "sky=space fx=stars"),
    ("city cities neon cyber cyberpunk megacity holo holograms skyline rooftops gridlock tokyo metro", "ground=city fx=rain sky=neon"),
    ("sea ocean reef tide tidebreaker waves wave undertow harbor harbour bay lagoon coast", "ground=sea"),
    ("trench mariana abyss sunken drowned leviathan underwater", "sky=deep fx=bubbles ground=reef"),
    ("jungle bamboo forest green leaves pine pines grove", "ground=pines"),
    ("hills hill meadow field fields fields prairie hedgerow farm valley spring", "ground=hills"),
    ("mountain mountains peak ridge cliff cliffs", "ground=mountains"),
    ("mesa mesas plateau canyon badlands", "ground=mesa"),
    ("bridge span skybridge", "ground=bridge"),
    ("stairs staircase steps terraces temple", "ground=stairs"),
    ("tower towers needle watchtower obelisk spires spire", "ground=needles"),
    ("spikes fang fangs sawtooth teeth spines spine", "ground=spikes"),
    ("ruins cathedral nave pipe organ mausoleums", "ground=ruins"),
    ("grave graves cemetery tombs mausoleum", "ground=graves"),
    ("trench trenches foxholes ditch bunker pits sinkholes craters shelled", "ground=trenches"),
    ("quarry mine pit funnel gorge maw", "ground=pit"),
    ("scrap scrapyard rust rivets factory industrial rail yard copper", "ground=factory"),
    ("rain", "fx=rain"),
    ("fireflies", "fx=fireflies"),
    ("sakura blossom petals", "fx=petals"),
    ("aurora", "sky=aurora"),
    ("fog mist ghostly midnight", "sky=fog"),
)
_CV_FAMILY = {"fire": ("inferno", "mountains", "embers", 0.03), "frost": ("night", "spikes", "snow", 0.56),
              "desert": ("dusk", "dunes", "sand", 0.09), "water": ("day", "sea", "bubbles", 0.55),
              "cosmic": ("space", "moonscape", "stars", 0.75), "city": ("neon", "city", "rain", 0.86),
              "storm": ("storm", "hills", "rain", 0.62), "wild": ("dawn", "pines", "fireflies", 0.33),
              "dark": ("fog", "graves", "fog", 0.78), "pastoral": ("day", "hills", "petals", 0.24),
              "plain": ("dusk", "hills", "none", 0.08)}
_CV_STYLE_ICON = {"chip": "invader", "glitch": "glitch", "hymn": "cross", "lullaby": "note", "clock": "gear", "jig": "fiddle",
                  "waltz": "note", "dub": "speaker", "techno": "speaker", "trap": "speaker", "house": "speaker", "funk": "note",
                  "synthwave": "gridsun", "metal": "flame", "metal2": "bolt", "horror": "ghost", "gothic": "skull",
                  "western": "cactus", "balkan": "swirl", "eastern": "torii", "desert": "cactus", "march": "shield",
                  "fanfare": "crown", "ambient": "none", "cosmic": "none", "industrial": "gear", "dnb": "bolt", "hyper": "bolt",
                  "epic": "sword", "folk": "tree", "jig2": "fiddle"}
_COVER_CACHE: dict = {}


def _cv_words(s: str) -> set:
    return set(re.findall(r"[a-z][a-z'-]*", s.lower()))


def _cover_plan(sid: str) -> dict:
    """Read the song: which sky, which orb, which ground, which centrepiece and which weather its cover gets."""
    sp = SONGS[sid]
    desc = sp.desc
    for pre in ("Home screen. ", "Battlefield. ", "Battlefield theme. ", "Ticket boss. "):
        desc = desc.replace(pre, "")
    plan: dict = {}
    for text in (sp.name, desc):
        ws = _cv_words(text)
        joined = " " + " ".join(re.findall(r"[a-z][a-z'-]*", text.lower())) + " "
        for keys, sets in _CV_RULES:
            if not any((k.replace("_", " ") in joined) if "_" in k else (k in ws) for k in keys.split(" ")):
                continue
            for kv in sets.split():
                slot, val = kv.split("=")
                plan.setdefault(slot, val)
    fam = family_of(f"{sp.name} {desc}", "")
    sky, ground, fx, hue = _CV_FAMILY.get(fam, _CV_FAMILY["plain"])
    seed = zlib.crc32(sid.encode())
    if fam in ("plain", "pastoral", "desert") and "sky" not in plan:
        sky = ("dusk", "day", "dawn", "night", "dusk", "day")[seed % 6]
    plan.setdefault("sky", sky)
    plan.setdefault("ground", ground)
    plan.setdefault("fx", fx)
    if "icon" not in plan and not sid.startswith(("map_", "home_")):
        plan["icon"] = _CV_STYLE_ICON.get(sp.style, "none")
    plan.setdefault("icon", "none")
    if "orb" not in plan:
        plan["orb"] = ("sun", "moon", "crescent", "planet", "none", "sun", "moon", "bigsun")[seed % 8] if plan["sky"] not in ("deep", "void", "paper") else "none"
    plan["fam"] = fam
    plan["hue"] = (hue + ((seed >> 4) % 1000) / 1000 * 0.12 - 0.06) % 1.0
    plan["seed"] = seed
    return plan


def _cv_sky(kind: str, u: float, v: float, hue: float, rnd: float) -> RGB:
    if kind == "night":
        return mix(hsv(hue, 0.7, 0.16), hsv(hue, 0.55, 0.42), v ** 1.4)
    if kind == "dusk":
        return gradient(((0, hsv((hue + 0.72) % 1, 0.6, 0.3)), (0.55, hsv((hue + 0.95) % 1, 0.6, 0.85)), (1, (255, 196, 120))), v)
    if kind == "dawn":
        return gradient(((0, hsv(hue, 0.35, 0.55)), (1, (255, 214, 170))), v)
    if kind == "day":
        return mix(hsv(0.58, 0.55, 0.85), (220, 236, 250), v ** 1.2)
    if kind == "space":
        neb = max(0.0, math.sin(u * 4.1 + rnd * 6) * math.sin(v * 3.3 + rnd * 4)) * 0.45
        return mix((6, 6, 16), hsv(hue, 0.7, 0.7), neb)
    if kind == "deep":
        ray = max(0.0, math.sin((u - v * 0.35) * 14 + rnd * 5)) ** 6 * (1 - v) * 0.35
        return mix(mix((10, 70, 110), (2, 8, 26), v ** 0.8), (160, 230, 255), ray)
    if kind == "inferno":
        return gradient(((0, (20, 4, 6)), (0.6, (120, 20, 14)), (1, (255, 110, 30))), v)
    if kind == "storm":
        return mix((26, 30, 44), (80, 88, 110), abs(math.sin(u * 3 + v * 2 + rnd * 5)) * 0.5 * (1 - v) + 0.2 * v)
    if kind == "aurora":
        band = max(0.0, 1 - abs(v - 0.3 - 0.12 * math.sin(u * 7 + rnd * 6)) * 7)
        return mix((6, 10, 22), mix((60, 240, 160), (170, 90, 255), u), band * 0.85)
    if kind == "fog":
        return mix(hsv(hue, 0.25, 0.22), hsv(hue, 0.18, 0.55), v)
    if kind == "neon":
        return gradient(((0, (16, 6, 34)), (0.7, hsv(hue, 0.75, 0.55)), (1, (255, 120, 190))), v)
    if kind == "toxic":
        return mix((10, 22, 8), (110, 220, 60), v ** 2 * 0.8)
    if kind == "gold":
        return gradient(((0, (40, 24, 8)), (0.6, (200, 140, 40)), (1, (255, 236, 170))), 1 - abs(v - 0.5) * 2)
    if kind == "void":
        return (8, 8, 10)
    return mix((235, 225, 205), (210, 196, 170), v)


def _cv_orb(kind: str, u: float, v: float, hue: float, rnd: float) -> Optional[RGB]:
    ox = 0.25 + rnd * 0.5
    if kind in ("sun", "bigsun"):
        r = 0.15 if kind == "sun" else 0.26
        d = math.hypot(u - ox, v - 0.32)
        if d < r:
            return gradient(((0, (255, 244, 190)), (1, (255, 150, 70))), d / r)
        if d < r + 0.08:
            return None if d > r + 0.04 else (255, 200, 120)
        return None
    if kind == "twinsun":
        for cx, cy, r, col in ((0.3, 0.3, 0.13, (255, 236, 160)), (0.7, 0.22, 0.09, (255, 160, 110))):
            if math.hypot(u - cx, v - cy) < r:
                return col
        return None
    if kind in ("moon", "bigmoon"):
        r = 0.15 if kind == "moon" else 0.27
        if math.hypot(u - ox, v - 0.3) < r:
            return (255, 168, 70) if kind == "bigmoon" else mix((240, 238, 222), (190, 192, 200), max(0.0, u - ox + 0.05) * 3)
        return None
    if kind == "crescent":
        if math.hypot(u - ox, v - 0.28) < 0.15 and math.hypot(u - ox - 0.07, v - 0.24) > 0.13:
            return (245, 240, 215)
        return None
    if kind == "threemoon":
        for cx, cy, r in ((0.22, 0.2, 0.08), (0.5, 0.14, 0.11), (0.8, 0.24, 0.06)):
            if math.hypot(u - cx, v - cy) < r:
                return (236, 226, 200)
        return None
    if kind == "planet":
        x, y = u - ox, v - 0.3
        ring = abs((x * 0.95 + y * 0.3) ** 2 / 0.06 + (y - x * 0.3) ** 2 / 0.004 - 1) < 0.6
        body = math.hypot(x, y) < 0.13
        if ring and (y - x * 0.3 > 0 or not body):
            return (255, 226, 170)
        if body:
            return mix(hsv((hue + 0.4) % 1, 0.55, 0.95), (20, 14, 30), clamp((x + y + 0.12) * 2.5, 0, 0.8))
        return None
    if kind == "nova":
        d = math.hypot(u - 0.5, v - 0.42)
        ang = math.atan2(v - 0.42, u - 0.5)
        if d < 0.14:
            return (255, 255, 236)
        ray = max(0.0, math.cos(ang * 6 + rnd * 3)) ** 4
        if d < 0.14 + 0.35 * ray:
            return mix((255, 236, 160), (255, 150, 60), d * 2.2)
        return None
    if kind == "eclipse":
        d = math.hypot(u - ox, v - 0.32)
        if d < 0.15:
            return (6, 6, 8)
        if d < 0.2:
            return (255, 240, 200)
        return None
    return None


def _cv_ground(kind: str, u: float, v: float, hue: float, rnd: float, sk: str) -> Optional[RGB]:
    dark = mix(hsv(hue, 0.6, 0.18), (0, 0, 0), 0.4)
    mid = hsv(hue, 0.5, 0.36)
    s = rnd * 6.28
    if kind == "hills":
        h1 = 0.62 + 0.08 * math.sin(u * 5 + s)
        h2 = 0.76 + 0.06 * math.sin(u * 7 + s * 2)
        if v > h2:
            return hsv(0.3 + rnd * 0.06, 0.6, 0.35)
        if v > h1:
            return hsv(0.3 + rnd * 0.06, 0.5, 0.55)
        return None
    if kind == "mountains":
        tri = lambda c, w_, top: top + abs(u - c) / w_ * (1 - top)
        if v > min(tri(0.3 + rnd * 0.2, 0.55, 0.3), tri(0.78, 0.4, 0.46)):
            snow = v < min(tri(0.3 + rnd * 0.2, 0.55, 0.3), tri(0.78, 0.4, 0.46)) + 0.05 and v < 0.5
            return (236, 240, 250) if snow else mix(dark, mid, 0.5 * (1 - v))
        return None
    if kind == "moonscape":
        h = 0.74 + 0.04 * math.sin(u * 9 + s)
        if v > h:
            crater = math.hypot((u - 0.3 - rnd * 0.4) * 1.0, (v - 0.86) * 2.4) < 0.12
            return (70, 70, 84) if crater else (130, 130, 146)
        return None
    if kind == "dunes":
        h1 = 0.62 + 0.07 * math.sin(u * 4 + s)
        h2 = 0.78 + 0.05 * math.sin(u * 6 + s + 1)
        if v > h2:
            return (176, 112, 52)
        if v > h1:
            return (226, 164, 84)
        return None
    if kind == "sea":
        if v > 0.66:
            wave = math.sin(u * 22 + v * 40 + s) > 0.82
            return (220, 240, 255) if wave else mix(hsv(0.57, 0.7, 0.6), (4, 20, 50), (v - 0.66) * 2.6)
        return None
    if kind == "reef":
        h = 0.78 + 0.06 * math.sin(u * 13 + s)
        if v > h:
            return mix(hsv((hue + 0.9) % 1, 0.6, 0.6), (20, 10, 30), (v - h) * 3)
        if abs((u * 7 + s) % 1 - 0.5) < 0.08 and v > 0.58 + 0.1 * math.sin(u * 30):
            return hsv((hue + 0.1) % 1, 0.7, 0.75)
        return None
    if kind in ("city", "factory"):
        col = int(u * 9)
        rr = (zlib.crc32(bytes([col % 256, int(rnd * 200)])) % 100) / 100
        top = 0.38 + rr * 0.34 if kind == "city" else 0.55 + rr * 0.2
        if kind == "factory" and col in (2, 6) and v > 0.2 and abs((u * 9) % 1 - 0.5) < 0.22:
            return (40, 38, 44)
        if v > top:
            win = ((int(u * 27) + int(v * 22) * 3 + col) % 4 == 0) and v < 0.94
            return mix((255, 220, 120), hsv(hue, 0.4, 1), 0.3) if win and kind == "city" else (14, 12, 22)
        return None
    if kind == "pines":
        for i in range(5):
            cx = (i + 0.5) / 5 + (rnd - 0.5) * 0.08
            top = 0.4 + ((i * 7 + int(rnd * 10)) % 4) * 0.06
            if v > top and abs(u - cx) < (v - top) * 0.45:
                return mix((10, 40, 24), (30, 90, 50), 0.4 * (1 - v))
        return (8, 26, 16) if v > 0.9 else None
    if kind == "spikes":
        for i in range(6):
            cx = (i + 0.3 + rnd * 0.4) / 6
            top = 0.38 + ((i * 5 + int(rnd * 10)) % 3) * 0.12
            if v > top and abs(u - cx) < (v - top) * 0.18:
                return mix((200, 230, 255), (90, 130, 190), (v - top) * 2)
        return (180, 210, 236) if v > 0.9 else None
    if kind == "mesa":
        for cx, w_, top in ((0.25 + rnd * 0.1, 0.18, 0.48), (0.72, 0.14, 0.58)):
            if abs(u - cx) < w_ + (v - top) * 0.25 and v > top:
                return mix((160, 70, 40), (90, 34, 24), (v - top) * 2)
        return (120, 52, 30) if v > 0.86 else None
    if kind == "bridge":
        if 0.58 < v < 0.64 and not 0.44 < u < 0.56:
            return (40, 34, 40)
        if v > 0.58 and abs(u - 0.5) < 0.04:
            return (40, 34, 40)
        return None
    if kind == "stairs":
        step = int(abs(u - 0.5) * 8)
        if v > 0.42 + step * 0.09:
            return mix((150, 70, 50), (70, 30, 30), step / 4)
        return None
    if kind == "needles":
        for cx, top in ((0.3 + rnd * 0.1, 0.2), (0.72, 0.4)):
            if v > top and abs(u - cx) < 0.03 + (v - top) * 0.07:
                return (24, 20, 34)
        return (24, 20, 34) if v > 0.88 else None
    if kind == "ruins":
        for i in range(4):
            cx = 0.16 + i * 0.23
            top = 0.4 + ((i * 3 + int(rnd * 5)) % 3) * 0.12
            if v > top and abs(u - cx) < 0.05:
                return (150, 140, 130) if v < top + 0.04 else (100, 94, 96)
        return (60, 56, 60) if v > 0.88 else None
    if kind == "graves":
        for i in range(3):
            cx = 0.2 + i * 0.3 + (rnd - 0.5) * 0.06
            if 0.66 < v < 0.9 and abs(u - cx) < 0.025:
                return (150, 150, 160)
            if 0.71 < v < 0.75 and abs(u - cx) < 0.08:
                return (150, 150, 160)
        return (20, 26, 22) if v > 0.88 else None
    if kind == "castle":
        if v > 0.5 and 0.15 < u < 0.85 and not (v < 0.56 and int(u * 14) % 2 == 0):
            gate = abs(u - 0.5) < 0.08 and v > 0.74
            return (20, 14, 16) if gate else (60, 56, 64)
        return None
    if kind == "trenches":
        if v > 0.7:
            dip = abs(math.sin(u * 9 + s)) > 0.82 and v < 0.82
            return None if dip else mix((80, 64, 40), (40, 30, 20), (v - 0.7) * 3)
        return None
    if kind == "volcano":
        top = 0.42
        if v > top and abs(u - 0.5) < 0.08 + (v - top) * 0.75:
            if v < top + 0.06 and abs(u - 0.5) < 0.09:
                return (255, 150, 40)
            lava = abs(u - 0.5 - 0.05 * math.sin(v * 20)) < 0.025 and v < 0.8
            return (255, 110, 30) if lava else mix((60, 30, 26), (20, 10, 12), (v - top) * 1.5)
        return (30, 14, 12) if v > 0.9 else None
    if kind == "pit":
        if v > 0.6:
            d = abs(u - 0.5)
            if d < 0.3 - (v - 0.6) * 0.5:
                return (10, 6, 8)
            return mix((130, 100, 70), (70, 50, 40), (v - 0.6) * 2)
        return None
    return None


def _cv_icon(kind: str, u: float, v: float, hue: float, rnd: float) -> Optional[RGB]:
    x, y = u - 0.5, v - 0.5
    acc = hsv((hue + 0.5) % 1, 0.6, 1.0)
    light = (240, 240, 236)
    if kind == "skull":
        if math.hypot(x, y + 0.05) < 0.25 or (abs(x) < 0.14 and 0.1 < y < 0.28):
            if math.hypot(abs(x) - 0.1, y + 0.03) < 0.07 or (abs(x) < 0.03 and 0.06 < y < 0.12):
                return (10, 8, 12)
            if 0.18 < y < 0.28 and int((x + 0.2) * 25) % 2 == 0:
                return (10, 8, 12)
            return light
        return None
    if kind == "ghost":
        if (math.hypot(x, y + 0.08) < 0.22 or (abs(x) < 0.22 and -0.08 < y < 0.22 + 0.05 * math.sin(x * 40))):
            if math.hypot(abs(x) - 0.08, y + 0.08) < 0.045:
                return (20, 20, 40)
            return (226, 236, 255)
        return None
    if kind == "eye":
        if abs(y) < 0.2 * math.sqrt(max(0.0, 1 - (x / 0.4) ** 2)):
            d = math.hypot(x, y)
            return (10, 6, 10) if d < 0.07 else acc if d < 0.15 else light
        return None
    if kind in ("crown", "crowns"):
        for c in ((0.0,) if kind == "crown" else (-0.2, 0.2)):
            sc = 1.0 if kind == "crown" else 0.55
            xx, yy = (x - c) / sc, (y - (0.0 if kind == "crown" else 0.05)) / sc
            if 0.04 < yy < 0.22 and abs(xx) < 0.3:
                if abs(yy - 0.13) < 0.035 and int((xx + 0.3) / 0.15) % 2 == 1:
                    return (230, 40, 70)
                return (255, 196, 50) if yy > 0.17 else (255, 220, 90)
            for px in (-0.26, 0.0, 0.26):
                if -0.24 < yy <= 0.04 and abs(xx - px) < 0.075 * (yy + 0.24) / 0.28:
                    return (255, 220, 90)
                if math.hypot(xx - px, yy + 0.27) < 0.04:
                    return (255, 250, 220)
        return None
    if kind == "flame":
        r = 0.22 * (1 - max(0.0, -y - 0.05) * 1.6)
        if r > 0 and abs(x + 0.04 * math.sin(v * 12)) < r * math.sqrt(max(0.0, 1 - ((y - 0.1) / 0.32) ** 2)) * 1.4:
            return gradient(((0, (255, 248, 190)), (0.5, (255, 160, 40)), (1, (230, 50, 30))), clamp(abs(x) / 0.2 + max(0.0, -y) * 1.5, 0, 1))
        return None
    if kind == "bolt":
        pts = ((0.1, -0.38), (-0.12, 0.04), (0.04, 0.04), (-0.1, 0.38), (0.14, -0.06), (-0.02, -0.06))
        if _cv_inpoly(x, y, pts):
            return (255, 236, 110)
        return None
    if kind == "snowflake":
        d, a = math.hypot(x, y), math.atan2(y, x)
        arm = abs(math.sin(a * 3)) < 0.18 / max(d, 0.05) * 0.12 + 0.05
        if d < 0.32 and (arm or d < 0.06):
            return (230, 244, 255)
        return None
    if kind == "ship":
        if 0.14 < y < 0.26 and abs(x) < 0.3 - (y - 0.14) * 0.9:
            return (70, 48, 34)
        if -0.3 < y < 0.14 and 0 < (x + 0.02) < 0.2 * (y + 0.3) / 0.44 + 0.02:
            return (230, 226, 210)
        if -0.24 < y < 0.12 and -0.22 * (y + 0.24) / 0.36 < x + 0.04 < 0:
            return (210, 206, 190)
        return None
    if kind in ("tank", "tanks2"):
        offs = ((0.0, acc, 1),) if kind == "tank" else ((-0.22, (90, 200, 255), 1), (0.22, (255, 120, 90), -1))
        sc = 1.0 if kind == "tank" else 0.6
        for o, col, face in offs:
            xx, yy = (x - o) / sc * face, (y - 0.1) / sc
            if 0.08 < yy < 0.2 and abs(xx) < 0.3:
                return (40, 40, 46) if int((xx + 1) * 18) % 2 else (90, 90, 96)
            if -0.04 < yy <= 0.08 and abs(xx) < 0.26:
                return col
            if math.hypot(xx, yy + 0.04) < 0.13 and yy < -0.04:
                return col
            if abs((yy + 0.1) + (xx - 0.05) * 0.55) < 0.035 and 0.05 < xx < 0.36:
                return mix(col, (0, 0, 0), 0.3)
        return None
    if kind in ("saucer", "mothership"):
        sc = 1.0 if kind == "saucer" else 1.6
        xx, yy = x / sc, (y + 0.08) / sc
        if (xx / 0.32) ** 2 + (yy / 0.08) ** 2 < 1:
            return (180, 190, 210) if int((xx + 1) * 20) % 3 else (120, 255, 200)
        if math.hypot(xx, yy + 0.06) < 0.13 and yy < 0:
            return (140, 230, 255)
        if kind == "saucer" and yy > 0.08 and abs(xx) < (yy - 0.04) * 0.9 and yy < 0.5:
            return mix((140, 255, 200), (0, 0, 0), 0.55)
        return None
    if kind == "tree":
        if abs(x) < 0.05 and 0 < y < 0.36:
            return (80, 50, 34)
        if math.hypot(x, y + 0.08) < 0.28 + 0.03 * math.sin(math.atan2(y, x) * 7):
            return mix((60, 170, 90), (20, 70, 40), clamp(y + 0.3, 0, 1))
        return None
    if kind == "mushroom":
        if abs(x) < 0.07 and 0 < y < 0.3:
            return (236, 226, 210)
        if y < 0.02 and (x / 0.32) ** 2 + ((y + 0.0) / 0.26) ** 2 < 1:
            dot = math.hypot((x * 6) % 1 - 0.5, (y * 6) % 1 - 0.5) < 0.2
            return (255, 255, 236) if dot else hsv((hue + 0.1) % 1, 0.7, 0.95)
        return None
    if kind == "whale":
        if ((x + 0.04) / 0.38) ** 2 + (y / 0.16) ** 2 < 1:
            if math.hypot(x + 0.26, y + 0.03) < 0.025:
                return (10, 10, 20)
            return (200, 220, 240) if y > 0.06 else (90, 120, 170)
        if 0.3 < x < 0.46 and abs(y + (x - 0.3) * 1.2) < 0.06 + (x - 0.3) * 0.5:
            return (90, 120, 170)
        return None
    if kind == "kaiju":
        body = ((x - 0.12) / 0.26) ** 2 + ((y - 0.2) / 0.4) ** 2 < 1
        head = math.hypot(x + 0.16, y + 0.2) < 0.13
        if body or head:
            if math.hypot(x + 0.2, y + 0.23) < 0.035:
                return (255, 60, 40)
            return mix((40, 70, 64), (110, 150, 130), clamp(-x * 2 + 0.3, 0, 1))
        if 0.04 < x < 0.36 and -0.3 < y < 0.1 and abs(((y + 0.3) * 10) % 1 - 0.5) < (x - 0.04) * 0.6 and x < 0.06 + (y + 0.3) * 0.3:
            return (90, 200, 230)
        return None
    if kind == "worm":
        if v > 0.36 and abs(x - 0.06 * math.sin(v * 9)) < 0.17 + 0.05 * v:
            if v < 0.5 and abs(x) < 0.11:
                ring = int(math.hypot(x, v - 0.36) * 40) % 2
                return (40, 10, 12) if ring else (230, 210, 180)
            return mix((190, 140, 90), (120, 80, 50), int(v * 16) % 2 * 0.6)
        return None
    if kind == "snake":
        a = y * 9 + rnd * 6
        if abs(x - 0.16 * math.sin(a)) < 0.07 and -0.34 < y < 0.36:
            return (60, 200, 110) if int((y + 1) * 14) % 2 else (240, 210, 70)
        if math.hypot(x - 0.16 * math.sin(-0.34 * 9 + rnd * 6), y + 0.36) < 0.09:
            return (60, 200, 110)
        return None
    if kind == "torii":
        red = (220, 50, 40)
        if -0.26 < y < -0.19 and abs(x) < 0.38 - (y + 0.26) * 0:
            return red
        if -0.12 < y < -0.07 and abs(x) < 0.28:
            return red
        if -0.19 < y < 0.36 and abs(abs(x) - 0.2) < 0.045:
            return red
        return None
    if kind == "lantern":
        if (x / 0.18) ** 2 + (y / 0.24) ** 2 < 1:
            return mix((255, 230, 140), (240, 90, 40), abs(x) / 0.18) if int((y + 1) * 12) % 3 else (200, 60, 30)
        if abs(x) < 0.08 and (abs(y + 0.26) < 0.03 or abs(y - 0.26) < 0.03):
            return (60, 30, 20)
        return None
    if kind in ("gear", "clock", "orrery"):
        d, a = math.hypot(x, y), math.atan2(y, x)
        if kind == "orrery":
            if d < 0.08:
                return (255, 214, 90)
            for r_, sp_, col in ((0.18, 1.0, (120, 200, 255)), (0.3, 0.6, (255, 140, 110)), (0.4, 0.35, (200, 170, 255))):
                if abs(d - r_) < 0.015:
                    return (170, 140, 90)
                px, py = r_ * math.cos(rnd * 9 * sp_ + r_ * 9), r_ * math.sin(rnd * 9 * sp_ + r_ * 9)
                if math.hypot(x - px, y - py) < 0.05:
                    return col
            return None
        teeth = 0.3 + (0.06 if math.cos(a * 8) > 0.2 else 0)
        if d < teeth and d > 0.1:
            return (210, 170, 90) if d < 0.26 else (180, 140, 70)
        return None
    if kind == "hourglass":
        if abs(y) < 0.36 and abs(x) < 0.04 + abs(y) * 0.6:
            sand = (y > 0.12) or (y < -0.0 and y > -0.16)
            return (255, 210, 120) if sand else (180, 220, 240)
        if 0.36 <= abs(y) < 0.42 and abs(x) < 0.3:
            return (130, 90, 50)
        return None
    if kind == "portal":
        d = math.hypot(x / 0.75, y)
        if 0.24 < d < 0.34:
            return mix(hsv(hue, 0.6, 1.0), (255, 255, 255), 0.4 * (1 - abs(d - 0.29) * 20))
        if d <= 0.24:
            sw = math.sin(math.atan2(y, x) * 3 + d * 30 + rnd * 6)
            return mix((20, 10, 40), hsv((hue + 0.15) % 1, 0.6, 0.9), 0.4 + 0.3 * sw)
        return None
    if kind == "cube":
        def sq(cx, cy, r):
            return max(abs(x - cx), abs(y - cy)) < r and max(abs(x - cx), abs(y - cy)) > r - 0.05
        if sq(-0.08, 0.08, 0.22):
            return (130, 240, 255)
        if sq(0.08, -0.08, 0.22):
            return (255, 140, 240)
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            ax_, ay_ = -0.08 + sx * 0.2, 0.08 + sy * 0.2
            t_ = (x - ax_) / 0.16
            if 0 <= t_ <= 1 and abs(y - (ay_ - 0.16 * t_)) < 0.03:
                return (200, 200, 255)
        return None
    if kind == "crystal":
        pts = ((0.0, -0.4), (0.18, -0.1), (0.1, 0.36), (-0.1, 0.36), (-0.18, -0.1))
        if _cv_inpoly(x, y, pts):
            return mix(hsv(hue, 0.5, 1.0), (255, 255, 255), 0.5 if x < 0 else 0.0)
        return None
    if kind == "cross":
        if (abs(x) < 0.05 and -0.36 < y < 0.36) or (abs(y + 0.12) < 0.05 and abs(x) < 0.22):
            return (255, 246, 210)
        return None
    if kind == "shield":
        if abs(x) < 0.26 * (1 - max(0.0, y) ** 1.5 * 6) and -0.3 < y < 0.36:
            return (255, 214, 90) if abs(x) < 0.04 or abs(y + 0.05) < 0.04 else acc
        return None
    if kind == "sword":
        if abs(x) < 0.03 and -0.38 < y < 0.16:
            return (220, 230, 240)
        if abs(y - 0.16) < 0.03 and abs(x) < 0.14:
            return (255, 200, 80)
        if abs(x) < 0.03 and 0.16 < y < 0.32:
            return (120, 70, 40)
        return None
    if kind == "bee":
        if ((x) / 0.2) ** 2 + (y / 0.14) ** 2 < 1:
            return (30, 24, 20) if int((x + 1) * 14) % 2 else (255, 210, 50)
        if ((x + 0.04) / 0.1) ** 2 + ((y + 0.18) / 0.12) ** 2 < 1:
            return (220, 240, 255)
        if 0.18 < x < 0.32 and abs(y) < 0.02:
            return (30, 24, 20)
        return None
    if kind == "key":
        if math.hypot(x + 0.18, y) < 0.13 and math.hypot(x + 0.18, y) > 0.06:
            return (255, 200, 80)
        if abs(y) < 0.035 and -0.05 < x < 0.32:
            return (255, 200, 80)
        if 0.12 < x < 0.32 and 0 < y < 0.12 and int((x + 1) * 20) % 2:
            return (255, 200, 80)
        return None
    if kind == "colossus":
        if math.hypot(x, y + 0.24) < 0.1:
            return (60, 64, 76) if abs(y + 0.24) > 0.02 or abs(x) > 0.06 else (255, 120, 60)
        if abs(x) < 0.24 and -0.14 < y < 0.16:
            return (70, 74, 88)
        if 0.16 <= y < 0.4 and abs(abs(x) - 0.12) < 0.07:
            return (56, 58, 70)
        return None
    if kind == "swirl":
        d, a = math.hypot(x, y), math.atan2(y, x)
        if d < 0.38 and abs(((a / 6.283 + d * 2.2 + rnd) % 0.5) - 0.25) < 0.07:
            return mix((220, 240, 255), (120, 150, 200), d * 2)
        return None
    if kind == "jelly":
        if y < 0 and (x / 0.24) ** 2 + (y / 0.2) ** 2 < 1:
            return mix(hsv(hue, 0.5, 1.0), (255, 255, 255), 0.4 * (1 + y * 3))
        if 0 <= y < 0.38 and abs(((x + 0.24) % 0.1) - 0.05 + 0.02 * math.sin(y * 20)) < 0.013 and abs(x) < 0.22:
            return hsv(hue, 0.5, 0.85)
        return None
    if kind == "glitch":
        row = int(v * 10)
        off = ((zlib.crc32(bytes([row % 256, int(rnd * 99)])) % 7) - 3) * 0.03
        if abs(x + off) < 0.3 and abs(y) < 0.3 and row % 3 != 1:
            return ((255, 40, 120), (40, 255, 200), (255, 255, 255))[row % 3 if row % 3 else 0]
        return None
    if kind == "invader":
        grid = ("..#...#..", "...#.#...", "..#####..", ".##.#.##.", "#########", "#.#####.#", "#.#...#.#", "...##.##.")
        gx, gy = int((x + 0.36) / 0.72 * 9), int((y + 0.3) / 0.6 * 8)
        if 0 <= gx < 9 and 0 <= gy < 8 and grid[gy][gx] == "#":
            return mix(acc, (120, 255, 120), 0.5)
        return None
    if kind == "note":
        if math.hypot((x + 0.1) / 1.3, y - 0.22) < 0.1:
            return light
        if abs(x - 0.03) < 0.03 and -0.3 < y < 0.22:
            return light
        if -0.32 < y < -0.2 and 0.03 < x < 0.03 + 0.18 - (y + 0.32) * 0.6:
            return light
        return None
    if kind == "speaker":
        d = math.hypot(x, y + 0.02)
        if abs(x) < 0.28 and abs(y) < 0.38:
            if d < 0.2:
                return (40, 40, 48) if d > 0.08 and int(d * 40) % 2 == 0 else (90, 90, 104)
            if math.hypot(x, y + 0.28) < 0.05:
                return (110, 110, 124)
            return (24, 24, 30)
        return None
    if kind == "gridsun":
        d = math.hypot(x, y + 0.06)
        if d < 0.3 and not (y > -0.02 and (y * 100) % 9 < 2.8):
            return gradient(((0, (255, 230, 110)), (1, (255, 60, 150))), clamp((y + 0.3) / 0.5, 0, 1))
        return None
    if kind == "fiddle":
        if ((x) / 0.15) ** 2 + ((y - 0.14) / 0.16) ** 2 < 1 or ((x) / 0.12) ** 2 + ((y + 0.06) / 0.12) ** 2 < 1:
            return (180, 90, 40) if abs(x) > 0.02 else (40, 20, 10)
        if abs(x) < 0.025 and -0.38 < y < -0.1:
            return (40, 20, 10)
        return None
    if kind == "cactus":
        if abs(x) < 0.06 and -0.3 < y < 0.38:
            return (60, 150, 70)
        if abs(x + 0.17) < 0.045 and -0.16 < y < 0.06 or (-0.17 < x < 0 and abs(y - 0.06) < 0.045):
            return (60, 150, 70)
        if abs(x - 0.17) < 0.045 and -0.24 < y < -0.02 or (0 < x < 0.17 and abs(y + 0.02) < 0.045):
            return (60, 150, 70)
        return None
    if kind == "shell":
        if abs(x) < 0.12 and -0.06 < y < 0.34:
            return (210, 170, 80) if y > 0.22 else (150, 160, 170)
        if y <= -0.06 and abs(x) < 0.12 * math.sqrt(max(0.0, 1 - ((y + 0.06) / 0.3) ** 2)):
            return (190, 200, 210)
        return None
    if kind == "wrench":
        if abs(x + y) < 0.06 and abs(x - y) < 0.6:
            d = math.hypot(x + 0.22, y + 0.22)
            return None if d < 0.06 else (180, 190, 200)
        if math.hypot(x + 0.22, y + 0.22) < 0.13 and math.hypot(x + 0.27, y + 0.27) > 0.07:
            return (180, 190, 200)
        return None
    if kind == "target":
        d = math.hypot(x, y)
        if d < 0.34:
            return (240, 60, 60) if int(d / 0.085) % 2 == 0 else light
        return None
    if kind == "mug":
        if abs(x + 0.04) < 0.17 and -0.18 < y < 0.3:
            return (255, 250, 236) if y < -0.08 else (230, 160, 40)
        if math.hypot(x - 0.17, y - 0.05) < 0.12 and math.hypot(x - 0.17, y - 0.05) > 0.06 and x > 0.13:
            return (200, 150, 60)
        return None
    if kind == "radar":
        if y < 0.06 and math.hypot(x, y + 0.02) < 0.3 and math.hypot(x - 0.14, y + 0.17) > 0.3:
            return (210, 216, 226)
        if abs(x) < 0.03 and 0 < y < 0.34:
            return (130, 136, 150)
        return None
    return None


def _cv_inpoly(x: float, y: float, pts) -> bool:
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            inside = not inside
        j = i
    return inside


def _cv_fx(kind: str, u: float, v: float, hue: float, rnd: float, seed: int) -> Optional[RGB]:
    cell = zlib.crc32(seed.to_bytes(8, "little")) % 97 + 2
    if kind == "stars":
        return (236, 236, 255) if cell < 4 and v < 0.7 else None
    if kind == "snow":
        return (240, 246, 255) if cell < 6 else None
    if kind == "rain":
        return (150, 180, 230) if cell < 12 else None
    if kind == "embers":
        return (255, 170, 60) if cell < 5 and v > 0.25 else None
    if kind == "fireflies":
        return (230, 255, 120) if cell < 4 and v > 0.35 else None
    if kind == "bubbles":
        return (180, 230, 255) if cell < 4 else None
    if kind == "spores":
        return (220, 255, 200) if cell < 5 else None
    if kind == "petals":
        return (255, 190, 210) if cell < 4 else None
    if kind == "sparks":
        return (255, 236, 160) if cell < 4 else None
    if kind == "lanterns":
        return (255, 190, 90) if cell < 5 and v < 0.6 else None
    if kind == "sand":
        return (240, 200, 140) if cell < 3 and v < 0.6 else None
    return None


def song_cover(sid: str, size: int = 10) -> list:
    """The sleeve for one song: a little picture built from the song's own name and blurb (sky, sun or moon, the land,
    a centrepiece and the weather), supersampled 3 x 3 and cached. Every song gets a different one."""
    key = (sid, size)
    if key in _COVER_CACHE:
        return _COVER_CACHE[key]
    p = _cover_plan(sid)
    hue, seed = p["hue"], p["seed"]
    rnd = (seed % 997) / 997
    icon = p["icon"]
    big = icon in ("kaiju", "whale", "worm", "mothership", "tree", "torii")
    sc = 1.0 if big else 0.86
    lift = 0.0 if big or icon == "none" else 0.03
    orb = p["orb"] if icon in ("none", "kaiju", "whale", "torii", "ship", "tree", "worm", "lantern", "mushroom", "radar", "cactus") else "none"
    if icon == "gridsun":
        orb = "none"
    gshift = 0.0 if icon in ("none", "kaiju", "worm", "ship", "tree", "torii", "radar", "cactus", "mushroom") else 0.14
    flat = p["icon"] in ("cube", "glitch", "orrery", "eye", "hourglass", "cross", "shield", "nova") and p["sky"] in ("space", "void", "gold", "night")

    def icon_at(u, v):
        if icon == "none":
            return None
        return _cv_icon(icon, 0.5 + (u - 0.5) / sc, 0.5 + (v - 0.5) / sc + lift, hue, rnd)
    grid = []
    for py in range(size):
        row = []
        for px in range(size):
            acc = [0, 0, 0]
            for i in range(3):
                for j in range(3):
                    u, v = (px + (i + 0.5) / 3) / size, (py + (j + 0.5) / 3) / size
                    col = _cv_sky(p["sky"], u, v, hue, rnd)
                    o = _cv_orb(orb, u, v, hue, rnd)
                    if o:
                        col = o
                    if p["fx"] == "fog" and abs(math.sin(v * 9 + u * 3 + rnd * 5)) < 0.25:
                        col = mix(col, (200, 210, 220), 0.25)
                    g = None if flat else _cv_ground(p["ground"], u, v - gshift, hue, rnd, p["sky"])
                    if g:
                        col = g
                    ic = icon_at(u, v)
                    if ic:
                        col = ic
                    elif icon != "none":                         # a dark rim so the centrepiece reads at this size
                        e = 0.045
                        if any(icon_at(u + du, v + dv) for du, dv in ((e, 0), (-e, 0), (0, e), (0, -e))):
                            col = mix(col, (6, 6, 12), 0.75)
                    acc[0] += col[0]; acc[1] += col[1]; acc[2] += col[2]
            c = (acc[0] // 9, acc[1] // 9, acc[2] // 9)
            f = _cv_fx(p["fx"], (px + 0.5) / size, (py + 0.5) / size, hue, rnd, seed % 100000 * 1000 + px * 31 + py)
            if f and not icon_at((px + 0.5) / size, (py + 0.5) / size):
                c = mix(c, f, 0.8)
            row.append(c)
        grid.append(row)
    _COVER_CACHE[key] = grid
    return grid


_DISC_CACHE: dict = {}
_DISC_KINDS = ("black", "colour", "splatter", "marble", "split", "picture", "clear", "glow", "smoke", "rings")


def _cover_palette(sid: str) -> tuple:
    """The two colours that say the most about a song's cover: its boldest (most saturated, bright) and its average."""
    grid = song_cover(sid, 10)
    px = [c for row in grid for c in row]
    avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))

    def punch(c):
        mx, mn = max(c), min(c)
        return (mx - mn) * 1.2 + mx * 0.4
    bold = max(px, key=punch)
    return bold, avg


def song_disc(sid: str) -> dict:
    """The record that lives in this song's sleeve. Its vinyl (black, coloured, splatter, marbled, split, picture disc,
    clear, glowing, smoke or ringed) and its centre label are chosen from the song itself: the label and vinyl colours
    are taken from the song's own cover, bosses and legends press picture or glowing discs, and the label's pattern and
    the record's speed (33, 45 or 78) follow the tempo."""
    if sid in _DISC_CACHE:
        return _DISC_CACHE[sid]
    sp = SONGS[sid]
    grp = song_group(sid)
    seed = zlib.crc32(("disc:" + sid).encode())
    bold, avg = _cover_palette(sid)
    if grp in ("martyr",) or sid in ("protector", "the_blessing", "time_machine", "masters_throne"):
        kind = "glow"
    elif grp in ("ticket", "tbos") or sid.startswith(("h_", "m_")):
        kind = ("picture", "splatter", "marble", "split", "picture")[seed % 5]
    elif sp.style in ("glitch", "chip"):
        kind = ("split", "rings")[seed % 2]
    elif sp.style in ("ambient", "cosmic", "dub", "lullaby"):
        kind = ("clear", "smoke", "marble")[seed % 3]
    elif sp.style in ("metal", "metal2", "industrial", "gothic", "horror"):
        kind = ("black", "splatter", "smoke")[seed % 3]
    else:
        kind = _DISC_KINDS[seed % 7]
    label_pat = ("solid", "split", "ring", "star", "stripe", "dot")[(seed >> 5) % 6]
    rpm = 78 if sp.bpm >= 150 else 45 if sp.bpm >= 110 else 33
    second = hsv(((seed >> 9) % 1000) / 1000, 0.65, 0.95)
    d = {"kind": kind, "bold": bold, "avg": avg, "second": second, "label": label_pat, "rpm": rpm, "seed": seed,
         "lr": 0.34 + ((seed >> 13) % 9) * 0.015,
         "tilt": (seed % 628) / 100}
    _DISC_CACHE[sid] = d
    return d


_DISC_TEX: dict = {}
_DISC_N = 28


def disc_texture(sid: str) -> list:
    """The record pressed once at rest (28 x 28, supersampled) so the card only has to turn it each frame."""
    tex = _DISC_TEX.get(sid)
    if tex is None:
        n, h = _DISC_N, _DISC_N / 2
        tex = []
        for y in range(n):
            row = []
            for x in range(n):
                acc = [0, 0, 0]
                for ox, oy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
                    dx, dy = (x + ox - h) / h, (y + oy - h) / h
                    c = disc_px(sid, min(1.0, math.hypot(dx, dy)), math.atan2(dy, dx), 0.0, False)
                    acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]
                row.append((acc[0] // 4, acc[1] // 4, acc[2] // 4))
            tex.append(row)
        _DISC_TEX[sid] = tex
        if len(_DISC_TEX) > 64:
            _DISC_TEX.pop(next(iter(_DISC_TEX)))
    return tex


def disc_sample(sid: str, dx: float, dy: float, spin: float) -> RGB:
    """The turning record at (dx, dy) in -1..1 record space: the pressed texture rotated, with a glint that stays put."""
    tex = disc_texture(sid)
    cs, sn = math.cos(spin), math.sin(spin)
    rx, ry = dx * cs + dy * sn, -dx * sn + dy * cs
    h = _DISC_N / 2
    col = tex[min(_DISC_N - 1, max(0, int(ry * h + h)))][min(_DISC_N - 1, max(0, int(rx * h + h)))]
    d = math.hypot(dx, dy)
    if d > song_disc(sid)["lr"]:
        g = max(0.0, math.cos(math.atan2(dy, dx) - 0.6)) ** 10 * 0.75
        if g > 0.01:
            col = mix(col, (236, 240, 255), g)
    return col


def disc_px(sid: str, d: float, ang: float, spin: float, glint_on: bool = True) -> RGB:
    """One point of the record at distance d (0 centre .. 1 rim) and angle ang, turned by spin."""
    D = song_disc(sid)
    a = ang - spin + D["tilt"]                                     # angle in the record's own frame (patterns turn with it)
    bold, avg, second, seed = D["bold"], D["avg"], D["second"], D["seed"]
    if d < 0.11:
        return (14, 14, 18)                                        # the spindle hole
    lr = D["lr"]
    if d < lr:                                                     # the centre label, coloured from the cover
        lab = mix(bold, (255, 255, 255), 0.12)
        alt = mix(avg, (0, 0, 0), 0.25) if sum(avg) > 160 else mix(avg, (255, 255, 255), 0.35)
        p = D["label"]
        if p == "split" and math.sin(a) > 0:
            lab = alt
        elif p == "ring" and 0.24 < d < 0.31:
            lab = alt
        elif p == "star" and math.cos(a * 5) > 0.55 and d > 0.2:
            lab = alt
        elif p == "stripe" and abs(math.sin(a) * d) < 0.06:
            lab = alt
        elif p == "dot" and math.hypot(d * math.cos(a) - 0.27, d * math.sin(a)) < 0.08:
            lab = alt
        return lab if d < lr - 0.03 else mix(lab, (0, 0, 0), 0.4)
    k = D["kind"]
    groove = 0.5 + 0.5 * math.sin(d * 30)
    glint = max(0.0, math.cos(ang - 0.6)) ** 10 * 0.75 if glint_on else 0.0   # the light stays put while the record turns
    if k == "black":
        base = mix((12, 12, 16), (44, 44, 54), groove * 0.6)
    elif k == "colour":
        base = mix(mix(bold, (0, 0, 0), 0.35), mix(bold, (0, 0, 0), 0.6), groove)
    elif k == "splatter":
        base = mix((14, 14, 18), (40, 40, 50), groove * 0.5)
        spot = zlib.crc32(bytes([int(d * 9) % 256, int((a % 6.283) * 2.2) % 256, seed % 256])) % 5
        if spot == 0:
            base = bold
        elif spot == 1:
            base = second
    elif k == "marble":
        sw = 0.5 + 0.5 * math.sin(a * 2 + d * 9 + math.sin(a * 3) * 1.5)
        base = mix(mix(bold, (0, 0, 0), 0.25), mix(second, (255, 255, 255), 0.25), sw)
        base = mix(base, (0, 0, 0), 0.25 * groove)
    elif k == "split":
        base = mix(bold, (0, 0, 0), 0.3) if math.sin(a) > 0 else mix(second, (0, 0, 0), 0.3)
        base = mix(base, (0, 0, 0), 0.3 * groove)
    elif k == "picture":                                            # the album cover printed on the vinyl itself
        u = 0.5 + 0.5 * d * math.cos(a)
        v = 0.5 + 0.5 * d * math.sin(a)
        grid = song_cover(sid, 10)
        base = grid[min(9, int(v * 10))][min(9, int(u * 10))]
        base = mix(base, (0, 0, 0), 0.12 * groove)
    elif k == "clear":
        base = mix((70, 76, 96), mix(avg, (255, 255, 255), 0.4), 0.35 + 0.25 * groove)
    elif k == "glow":
        base = mix((255, 214, 120), (255, 250, 220), 0.5 + 0.5 * math.sin(d * 18 - spin * 2))
    elif k == "smoke":
        sw = 0.5 + 0.5 * math.sin(a * 1.5 + d * 6 + math.sin(d * 13 + a) * 2)
        base = mix((20, 20, 26), mix(avg, (160, 160, 170), 0.5), sw * 0.6)
    else:                                                           # rings: concentric colour bands
        base = (bold, second, mix(bold, second, 0.5))[int(d * 7) % 3]
        base = mix(base, (0, 0, 0), 0.35)
    if d > 0.95:
        base = mix(base, (0, 0, 0), 0.45)                           # the rim
    return mix(base, (236, 240, 255), glint)
