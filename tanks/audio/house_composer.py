"""The house composer: writes a song for every home screen and battlefield that has no hand-written one."""
from __future__ import annotations

import random
import zlib
from typing import Optional

from tanks.audio.composer import METERS, SCALES, STYLES, SongSpec, deg_semi
from tanks.content.songs import SONGS


_GEN_FAMILIES = {
    "fire":     dict(styles=("metal", "metal2", "industrial", "epic", "dnb", "gothic"), scales=("phr", "hmin", "min", "phd"),
                     lead=("saw", "supersaw", "brass", "organ", "hoover", "reed"), pad=("choir", "strings", "warmpad")),
    "frost":    dict(styles=("ambient", "epic", "waltz", "cosmic", "hymn", "lullaby"), scales=("lyd", "min", "dor", "maj"),
                     lead=("celesta", "glock", "bell", "flute", "music_box", "vibes"), pad=("glasspad", "choir_o", "strings")),
    "desert":   dict(styles=("desert", "balkan", "eastern", "western", "funk", "epic"), scales=("phd", "hmin", "hung", "dor", "phr"),
                     lead=("erhu", "sitar", "reed", "flute", "theremin", "koto"), pad=("warmpad", "strings")),
    "water":    dict(styles=("dub", "house", "ambient", "synthwave", "funk", "waltz"), scales=("dor", "mix", "maj", "min", "lyd"),
                     lead=("vibes", "marimba", "ep", "flute", "hollow", "celesta"), pad=("glasspad", "pad", "warmpad")),
    "cosmic":   dict(styles=("cosmic", "synthwave", "techno", "ambient", "hyper", "glitch"), scales=("lyd", "min", "dor", "phr"),
                     lead=("theremin", "supersaw", "glasspad", "hollow", "celesta", "square"), pad=("glasspad", "pad", "choir_o")),
    "city":     dict(styles=("synthwave", "techno", "house", "funk", "dnb", "trap", "glitch", "industrial"), scales=("min", "dor", "mix", "phr"),
                     lead=("square", "supersaw", "ep", "hollow", "bell", "saw"), pad=("pad", "glasspad", "warmpad")),
    "storm":    dict(styles=("dnb", "metal2", "epic", "industrial", "hyper"), scales=("min", "phr", "hmin", "dor"),
                     lead=("supersaw", "brass", "saw", "hoover", "choir"), pad=("choir", "strings", "pad")),
    "wild":     dict(styles=("jig", "eastern", "folk", "funk", "epic", "dub"), scales=("mix", "dor", "maj", "min"),
                     lead=("flute", "marimba", "koto", "harp", "reed", "pizz"), pad=("warmpad", "strings")),
    "dark":     dict(styles=("gothic", "horror", "waltz", "industrial", "clock", "hymn"), scales=("hmin", "loc", "phr", "min", "hung"),
                     lead=("organ", "choir", "theremin", "music_box", "harpsi", "erhu"), pad=("choir", "strings", "warmpad")),
    "pastoral": dict(styles=("jig", "folk", "waltz", "fanfare", "march", "hymn"), scales=("maj", "mix", "dor", "lyd"),
                     lead=("flute", "reed", "harp", "guitar", "ep", "horn"), pad=("strings", "warmpad")),
    "plain":    dict(styles=("march", "epic", "metal2", "western", "chip", "funk", "synthwave", "metal", "fanfare"), scales=("min", "dor", "maj", "mix"),
                     lead=("brass", "saw", "square", "reed", "guitar", "supersaw"), pad=("strings", "pad", "choir")),
}
_GEN_TEMPO = {"ambient": (62, 88), "balkan": (138, 168), "chip": (140, 168), "clock": (100, 120), "cosmic": (72, 112), "desert": (86, 126),
              "dnb": (166, 176), "dub": (72, 94), "eastern": (96, 130), "epic": (96, 124), "fanfare": (84, 124), "folk": (80, 110),
              "funk": (94, 124), "glitch": (118, 152), "gothic": (78, 104), "horror": (60, 110), "house": (116, 126), "hymn": (60, 76),
              "hyper": (168, 180), "industrial": (96, 126), "jig": (104, 140), "lullaby": (74, 90), "march": (104, 124), "metal": (140, 162),
              "metal2": (104, 142), "synthwave": (106, 134), "techno": (124, 138), "trap": (134, 150), "waltz": (84, 108), "western": (122, 146)}
_GEN_METERS = {"waltz": ("34",), "lullaby": ("34",), "hymn": ("34",), "jig": ("68",), "balkan": ("78", "98"), "folk": ("68", "44", "34"),
               "ambient": ("44", "34", "54"), "cosmic": ("44", "54"), "desert": ("44", "54"), "glitch": ("44", "54", "78"), "epic": ("44", "44", "34"),
               "gothic": ("44", "34"), "horror": ("44", "34"), "eastern": ("44", "44", "54"), "fanfare": ("44", "34")}
_GEN_METER_GROOVE = {"34": ("waltz", "waltz2"), "54": ("five", "five2"), "78": ("balkan", "balkan2"), "98": ("nine",), "128": ("twelve",),
                     "68": ("jig", "jig2", "march68"), "58": ("five8",)}
_GEN_CELLS = {      # rhythm cells (16th-step durations) per bar length, low energy first
    16: ((16,), (8, 8), (12, 4), (8, 4, 4), (4, 4, 8), (6, 2, 8), (4, 4, 4, 4), (6, 2, 4, 4), (4, 2, 2, 8), (2, 2, 4, 8),
         (3, 3, 2, 4, 4), (4, 2, 2, 4, 4), (2, 2, 2, 2, 8), (2, 2, 4, 2, 2, 4), (2, 2, 2, 2, 4, 4), (2, 2, 2, 2, 2, 2, 4)),
    12: ((12,), (8, 4), (6, 6), (4, 8), (4, 4, 4), (6, 2, 4), (3, 1, 2, 6), (4, 2, 4, 2), (2, 2, 2, 6), (2, 2, 2, 2, 4), (2, 2, 2, 2, 2, 2)),
    14: ((14,), (8, 6), (4, 4, 6), (6, 2, 6), (2, 2, 4, 6), (4, 4, 2, 2, 2), (2, 2, 2, 2, 6), (2, 2, 2, 2, 2, 2, 2)),
    18: ((18,), (12, 6), (6, 6, 6), (4, 2, 6, 6), (6, 4, 2, 6), (2, 2, 2, 6, 6), (4, 2, 4, 2, 6)),
    20: ((20,), (10, 10), (6, 4, 10), (6, 4, 6, 4), (4, 2, 4, 4, 6), (2, 2, 2, 4, 4, 6), (6, 2, 2, 6, 4)),
    24: ((24,), (12, 12), (6, 6, 12), (6, 6, 6, 6), (4, 2, 6, 6, 6), (2, 2, 2, 6, 6, 6)),
    10: ((10,), (4, 6), (6, 4), (2, 2, 6), (2, 2, 2, 4)),
}
_GEN_PROGS_MAJ = ("1 5 6 4", "1 6 4 5", "1 4 6 5", "6 4 1 5", "1 3 4 4", "1 5 4 4", "4 1 5 6", "1 2 4 5", "1 4 2 5", "1 6 2 5",
                  "1 4 1 5", "1 5 6 3", "4 5 1 1", "1 3 6 4")
_GEN_PROGS_MIN = ("1 6 7 1", "1 4 5 1", "1 6 3 7", "1 7 6 7", "1 4 7 3", "6 7 1 1", "1 3 4 5", "1 6 4 5", "1 4 6 5", "1 7 4 1",
                  "1 5 6 4", "4 6 7 1", "1 3 7 4", "6 4 1 7")
_GEN_PROGS_B = ("4 5 3 6", "6 4 5 5", "4 1 5 5", "2 5 1 6", "6 7 4 5", "4 6 5 5", "3 6 4 5", "6 3 4 5", "4 5 6 6", "2 4 5 5", "7 6 4 5")


def _gen_chord(sc: tuple, deg: int, seventh: bool) -> str:
    """A diatonic chord written with its quality (so pentatonic-free, unambiguous); the tonic is never diminished."""
    third = deg_semi(sc, deg + 2) - deg_semi(sc, deg)
    fifth = deg_semi(sc, deg + 4) - deg_semi(sc, deg)
    q = {(4, 7): "M", (3, 7): "m", (3, 6): "d", (4, 8): "+"}.get((third, fifth), "m")
    if deg == 1 and q in ("d", "+"):
        q = "m" if third == 3 else "M"
    if q == "+" and deg != 3:
        q = "M"
    return f"{deg}{q}{'7' if seventh and q in 'Mm' else ''}"


def _gen_deg_token(idx: int, L: int) -> str:
    o, d = divmod(idx, L)
    return f"{d + 1}" + ("'" * o if o > 0 else "," * (-o))


def _gen_melody(rng: random.Random, sc: tuple, bar: int, chords: list, energy: float, lo: int, hi: int, start: int, final: int) -> str:
    """Four bars: motif, answer (sequenced), climb (new rhythm, toward the peak), cadence (approach + long final note)."""
    L = len(sc)
    cells = _GEN_CELLS[bar]
    n = len(cells)
    pick = lambda e: cells[max(0, min(n - 1, int(round(e * (n - 1) + rng.uniform(-1.6, 1.6)))))]
    r1, r3 = pick(energy), pick(min(1.0, energy + 0.15))
    cad_opts = [c for c in cells if c[-1] >= bar // 2 and len(c) <= 3] or [cells[0]]
    r4 = rng.choice(cad_opts)

    def tones(ch: int) -> list:
        base = [(ch - 1) % L, (ch + 1) % L, (ch + 3) % L]
        return [b + 7 * 0 + L * o for b in base for o in range(-2, 4)]

    def nearest_tone(x: int, ch: int, lo_: int = lo, hi_: int = hi) -> int:
        cand = [t for t in tones(ch) if lo_ <= t <= hi_]
        return min(cand, key=lambda t: (abs(t - x), rng.random())) if cand else max(lo_, min(hi_, x))

    def strong(pos: int) -> bool:
        return pos == 0 or pos == bar // 2 or (bar in (12,) and pos in (6,)) or (bar == 20 and pos in (6, 10, 16))

    out, cur = [], start
    contour = rng.choice((1, 1, -1, 0))
    motif = []
    for bi in range(4):
        ch = chords[bi % len(chords)]
        rh = r1 if bi < 2 else (r3 if bi == 2 else r4)
        pos = 0
        notes = []
        for k, d in enumerate(rh):
            last_of_song = bi == 3 and k == len(rh) - 1
            if bi == 1 and k < len(motif) and len(r1) == len(rh):     # the answer: the motif's shape, moved by a sequence step
                shift = motif_shift
                cur = max(lo, min(hi, motif[k] + shift))
                if strong(pos):
                    cur = nearest_tone(cur, ch)
            elif last_of_song:
                cur = final
            elif strong(pos):
                aim = cur + (contour if contour else rng.choice((-1, 1))) * rng.choice((1, 2, 2, 3))
                cur = nearest_tone(aim, ch)
            else:
                step = rng.choice((1, 1, 1, 2)) * (contour if contour and rng.random() < 0.75 else rng.choice((-1, 1)))
                cur = max(lo, min(hi, cur + step))
            if cur >= hi - 1:
                contour = -1
            elif cur <= lo + 1:
                contour = 1
            if bi == 3 and k == len(rh) - 2:                           # approach the final note by step
                cur = final + rng.choice((1, -1, 2))
            notes.append(cur)
            pos += d
        if bi == 0:
            motif = notes[:]
            motif_shift = rng.choice((-2, -1, 1, 2, 2))
        if bi == 2:
            contour = -1 if cur > (lo + hi) // 2 else 1
        toks = [f"{_gen_deg_token(p, L)}:{d}" for p, d in zip(notes, rh)]
        if bi == 1 and energy < 0.7 and rh[-1] >= 4 and rng.random() < 0.35:   # a breath before the climb
            toks[-1] = f"r:{rh[-1]}"
        out.append(" ".join(toks))
    return " | ".join(out)


def gen_song(sid: str, name: str, cat: str, family: str, desc: str, hint: Optional[str] = None) -> None:
    """Writes one complete song into SONGS (deterministic: the same name always gives the same music)."""
    rng = random.Random(zlib.crc32(sid.encode()) ^ 0x5EED)
    fam = _GEN_FAMILIES.get(family, _GEN_FAMILIES["plain"])
    pool = list(fam["styles"])
    if cat == "menu":                                         # home screens are for browsing: keep the heaviest genres for battle
        calm = [s_ for s_ in pool if s_ not in ("hyper", "dnb", "metal", "metal2", "trap")]
        pool = calm if (calm and (family not in ("fire", "storm") or rng.random() < 0.6)) else pool
    else:
        pool = [s_ for s_ in pool if s_ not in ("hymn", "lullaby")] or pool
    style = hint if hint in STYLES else rng.choice(pool)
    scale = SONGS[hint].scale if hint in SONGS else rng.choice(fam["scales"])
    if hint in SONGS:
        style = SONGS[hint].style
    meter = rng.choice(_GEN_METERS.get(style, ("44",)))
    lo_t, hi_t = _GEN_TEMPO.get(style, (96, 132))
    mid = (lo_t + hi_t) / 2
    bpm = int(rng.uniform(mid, hi_t) if cat == "battle" else rng.uniform(lo_t, mid + 4))
    root = rng.randint(38, 51)
    sc = SCALES[scale]
    minorish = deg_semi(sc, 3) == 3
    jazzy = style in ("funk", "house", "dub", "lullaby") or (style in ("ambient", "cosmic") and rng.random() < 0.4)
    def stable(d: int) -> int:                                # no full bars of diminished / augmented harmony
        for c in (d, d + 2, d - 2, d + 4, 1):
            c = (c - 1) % 7 + 1
            t3, t5 = deg_semi(sc, c + 2) - deg_semi(sc, c), deg_semi(sc, c + 4) - deg_semi(sc, c)
            if t5 == 7 and t3 in (3, 4):
                return c
        return 1
    pa = [stable(int(t)) for t in rng.choice(_GEN_PROGS_MIN if minorish else _GEN_PROGS_MAJ).split()]
    pb = [stable(int(t)) for t in rng.choice(_GEN_PROGS_B).split()]
    pc = [stable(int(t)) for t in rng.choice(_GEN_PROGS_MIN if minorish else _GEN_PROGS_MAJ).split()]
    prog = {"A": " ".join(_gen_chord(sc, d, jazzy and rng.random() < 0.6) for d in pa),
            "B": " ".join(_gen_chord(sc, d, jazzy and rng.random() < 0.6) for d in pb)}
    energy = {"metal": .9, "metal2": .85, "dnb": .8, "hyper": .95, "techno": .7, "trap": .6, "chip": .85, "balkan": .9, "jig": .8,
              "industrial": .65, "glitch": .8, "funk": .7, "house": .6, "synthwave": .6, "western": .75, "march": .6, "epic": .55,
              "fanfare": .5, "eastern": .55, "desert": .5, "folk": .45, "dub": .35, "waltz": .45, "gothic": .4, "horror": .3, "clock": .6,
              "cosmic": .3, "ambient": .15, "hymn": .1, "lullaby": .15}.get(style, .5)
    if cat == "battle":
        energy = min(1.0, energy + 0.1)
    L = len(sc)
    bar = METERS[meter][0]
    mels = {"A": _gen_melody(rng, sc, bar, pa, energy, 0, L + 4, rng.choice((0, 2, 4)), 0),
            "B": _gen_melody(rng, sc, bar, pb, min(1.0, energy + 0.1), 2, L + 6, rng.choice((L, L + 2, 4)), 4)}
    form = rng.choice(("I A B A2 C X O", "I A A2 B X O", "I A B C A2 X O", "I A B A2 D X B2 O", "I A B2 C A2 X O", "A B A2 C X O"))
    if "C" in form:
        prog["C"] = " ".join(_gen_chord(sc, d, jazzy) for d in pc)
        mels["C"] = _gen_melody(rng, sc, bar, pc, max(0.0, energy - 0.35), 0, L + 4, rng.choice((2, 4)), rng.choice((0, 4)))
    kw = {}
    if not hint:
        kw["lead"] = rng.choice(fam["lead"])
        others = [x for x in fam["lead"] if x != kw["lead"]]
        kw["lead2"] = rng.choice(others)
        kw["counter"] = rng.choice(fam["pad"] + tuple(others[:2]))
        if STYLES[style].get("pad") is not None and rng.random() < 0.7:
            kw["pad"] = rng.choice(fam["pad"])
    else:
        kw["lead"] = rng.choice(fam["lead"])
    if meter in _GEN_METER_GROOVE and _GEN_METERS.get(style, ("44",))[0] != meter:
        kw["groove"] = rng.choice(_GEN_METER_GROOVE[meter])
    if style in ("funk", "house", "dub", "jig", "folk") and rng.random() < 0.6:
        kw["swing"] = round(rng.uniform(0.06, 0.2), 2)
    SONGS[sid] = SongSpec(sid, name, cat, bpm, root, scale, meter, style, prog, mels, form, desc, **kw)
