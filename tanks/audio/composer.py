"""The composer: performs a song spec. Songs are sequenced at runtime from a small bank of pre-rendered notes, so
music costs almost no memory or CPU once a song is loaded."""
from __future__ import annotations

import random

from tanks.audio.synth import AU_SR, drum_gain


SCALES = {"maj": (0, 2, 4, 5, 7, 9, 11), "min": (0, 2, 3, 5, 7, 8, 10), "dor": (0, 2, 3, 5, 7, 9, 10), "phr": (0, 1, 3, 5, 7, 8, 10),
          "lyd": (0, 2, 4, 6, 7, 9, 11), "mix": (0, 2, 4, 5, 7, 9, 10), "hmin": (0, 2, 3, 5, 7, 8, 11), "phd": (0, 1, 4, 5, 7, 8, 10),
          "hung": (0, 2, 3, 6, 7, 8, 11), "pent": (0, 2, 4, 7, 9), "mpent": (0, 3, 5, 7, 10), "wt": (0, 2, 4, 6, 8, 10),
          "loc": (0, 1, 3, 5, 6, 8, 10), "insen": (0, 1, 5, 7, 10)}
METERS = {"44": (16, (4, 4, 4, 4)), "34": (12, (4, 4, 4)), "68": (12, (6, 6)), "78": (14, (4, 4, 6)), "54": (20, (6, 4, 6, 4)),
          "58": (10, (4, 6)), "98": (18, (6, 6, 6)), "128": (24, (6, 6, 6, 6))}


def deg_semi(sc: tuple, d: int) -> int:
    """Scale degree (1-based, may exceed the octave or go below 1) -> semitones above the tonic."""
    L = len(sc)
    q, r = divmod(d - 1, L)
    return sc[r] + 12 * q


def parse_chord(tok: str, sc: tuple) -> tuple:
    """'1', '6M', 'b7M', '4m7', '5s' (sus4), '1p' (power), '2d' (dim) -> (root semitone, (intervals...))."""
    acc = 0
    while tok and tok[0] in "b#":
        acc += -1 if tok[0] == "b" else 1
        tok = tok[1:]
    i = 0
    while i < len(tok) and tok[i].isdigit():
        i += 1
    d, q = int(tok[:i] or 1), tok[i:]
    root = deg_semi(sc, d) + acc
    if "M" in q:
        iv = [0, 4, 7]
    elif "m" in q:
        iv = [0, 3, 7]
    elif "d" in q:
        iv = [0, 3, 6]
    elif "+" in q:
        iv = [0, 4, 8]
    elif "s" in q:
        iv = [0, 5, 7]
    elif "p" in q:
        iv = [0, 7, 12]
    elif acc:
        iv = [0, 4, 7]
    else:                                                    # diatonic: stack scale thirds
        iv = [0, deg_semi(sc, d + 2) - deg_semi(sc, d), deg_semi(sc, d + 4) - deg_semi(sc, d)]
    if "7" in q:
        iv.append(10 if ("M" not in q or "m" in q) else 11)
    if "9" in q:
        iv.append(14)
    return root, tuple(iv)


def parse_mel(text: str, sc: tuple, meter: int) -> list:
    """'5:4 3:2 2 1:8 r:4 1#\\':2 ...' -> [(step, semitone, length)]; durations in 16th steps (carry over), r = rest, ~ = tie,
    ' / , raise / lower an octave, # / b alter. A bar line '|' is decorative."""
    out, step, dur = [], 0, 4
    for tok in text.replace("|", " ").split():
        if ":" in tok:
            tok, ds = tok.split(":")
            dur = int(ds)
        if tok == "~":
            if out:
                s0, m0, l0 = out[-1]
                out[-1] = (s0, m0, l0 + dur)
            step += dur
            continue
        if tok != "r":
            octv, acc = 0, 0
            core = tok
            while core and core[-1] in "',":
                octv += 12 if core[-1] == "'" else -12
                core = core[:-1]
            while core and core[-1] in "#b":
                acc += 1 if core[-1] == "#" else -1
                core = core[:-1]
            out.append((step, deg_semi(sc, int(core)) + acc + octv, dur))
        step += dur
    return out


# ---- grooves: lane -> pattern per bar ('x' hit, 'o' ghost, '-' rest); every pattern must be the metre's step count ------
GROOVES = {
    "four":    {"K": "x---x---x---x---", "C": "----x-------x---", "H": "--x---x---x---x-", "h": "x-x-x-x-x-x-x-x-"},
    "rock":    {"K": "x-----x-x-------", "S": "----x-------x---", "h": "x-x-x-x-x-x-x-x-"},
    "rock2":   {"K": "x--x--x---x-x---", "S": "----x-------x--o", "R": "x-x-x-x-x-x-x-x-"},
    "boom":    {"K": "x-----x---x-----", "S": "----x-------x-x-", "T": "x---------------", "P": "--x-----x-x---x-"},
    "boom2":   {"K": "x--x----x-x-----", "S": "--------x-------", "T": "x-------x-------", "P": "x-x-x-x-x-x-x-x-"},
    "march":   {"K": "x-------x-------", "S": "x-oxx-x-x-oxx-x-", "T": "x-------x-------"},
    "dnb":     {"K": "x---------x-----", "S": "----x-------x---", "h": "x-x-x-x-x-x-x-x-", "s": "-------o-o----o-"},
    "trap":    {"K": "x------x--x-----", "S": "--------x-------", "h": "xxxxxxxxxxxxxxxx", "O": "-----------x----"},
    "metal":   {"K": "xxxxxxxxxxxxxxxx", "S": "----x-------x---", "R": "x-x-x-x-x-x-x-x-"},
    "metal2":  {"K": "x-xxx-xxx-xxx-xx", "S": "----x-------x---", "h": "x-x-x-x-x-x-x-x-"},
    "techno":  {"K": "x---x---x---x---", "h": "--x---x---x---x-", "C": "----x-------x---", "P": "--x--x--x-----x-"},
    "chip":    {"K": "x-------x-x-----", "S": "----x-------x---", "h": "x-x-x-x-x-x-x-x-"},
    "break":   {"K": "x-----x---x-----", "S": "----x-------x---", "h": "x-x-x-x-x-x-x-x-", "s": "--o---o---o-o---"},
    "dub":     {"K": "x---------x-----", "S": "--------x-------", "h": "--x---x---x---x-"},
    "half":    {"K": "x---------x--x--", "S": "--------x-------", "h": "x-x-x-x-x-x-x-x-"},
    "glitch":  {"K": "x--x---x-x----x-", "S": "----x--x----x-x-", "h": "xx-x-xx-xx-x-xx-", "G": "---x------x---x-"},
    "desert":  {"D": "x------x-x------", "E": "--x-x---x---x-x-", "h": "x-x-x-x-x-x-x-x-"},
    "eastern": {"K": "x-------x---x---", "B": "--x---x---x---x-", "P": "----x-------x---"},
    "house":   {"K": "x---x---x---x---", "C": "----x-------x---", "O": "--x---x---x---x-", "h": "x-xxx-xxx-xxx-xx"},
    "soft":    {"K": "x-------x-------", "h": "----x-------x---"},
    "ambient": {"K": "x---------------", "h": "--------x-------"},
    "clock":   {"K": "x-------x-------", "P": "x---x---x---x---", "B": "--x---x---x---x-"},
    "indus":   {"K": "x--x--x-x--x--x-", "S": "----x-------x---", "A": "-------x-------x", "h": "x-x-x-x-x-x-x-x-"},
    "hyper":   {"K": "x---x---x---x---", "O": "--x---x---x---x-", "C": "----x-------x---", "h": "xxxxxxxxxxxxxxxx"},
    "western": {"K": "x-----x-x-----x-", "S": "----x-------x---", "P": "x-xx-xx-x-xx-xx-"},
    "funk":    {"K": "x--x--x---x--x--", "S": "----x--o-o--x---", "h": "x-x-x-x-x-x-x-x-", "P": "--x---x---x---x-"},
    "waltz":   {"K": "x-----------", "S": "----o---o---", "h": "x-x-x-x-x-x-"},
    "waltz2":  {"T": "x-----------", "P": "----x---x---", "R": "x---x---x---"},
    "jig":     {"K": "x--x-xx--x-x", "P": "x-xx-xx-xx-x", "S": "------x-----"},
    "jig2":    {"K": "x-----x-----", "S": "---x-x---x-x", "h": "x-xx-xx-xx-x"},
    "march68": {"K": "x-----x-----", "S": "x-ox-ox-ox-o", "T": "x-----------"},
    "balkan":  {"D": "x---x---x-----", "E": "--x---x---x-x-", "C": "----------x---"},
    "balkan2": {"K": "x---x---x--x--", "S": "--x---x-----x-", "h": "x-x-x-x-x-x-x-"},
    "five":    {"K": "x-----x---x-----x---", "S": "----x-------x-----x-", "h": "x-x-x-x-x-x-x-x-x-x-"},
    "five2":   {"K": "x-----------x-------", "P": "x--x--x---x--x--x---", "B": "------x---------x---"},
    "five8":   {"K": "x---x-----", "S": "------x---", "h": "x-x-x-x-x-"},
    "nine":    {"K": "x-----x-----x-----", "S": "---x-----x-----x-x", "h": "x-xx-xx-xx-xx-xx-x"},
    "twelve":  {"K": "x-----x-----x-----x-----", "S": "------x-----------x-----", "h": "x-xx-xx-xx-xx-xx-xx-xx-x"},
    "none":    {},
}
FILLS = {"tom": {"T": "----x-x-xxxxxxxx"}, "snare": {"S": "x-x-x-x-xxxxxxxx"}, "taiko": {"K": "x---x---x-x-xxxx", "P": "--x---x---x-x-x-"},
         "glitch": {"G": "xxxx-xx-xxxxxxxx", "S": "----x---x-x-xxxx"}, "chip": {"S": "x-x-x-x-xxxxxxxx"}, "none": {}}
KITS = {   # lane -> drum sample
    "pop":    {"K": "kick", "S": "snare", "C": "clap", "H": "ohat", "h": "hat", "O": "ohat", "R": "ride", "T": "tom", "P": "shaker", "s": "snare.tight"},
    "808":    {"K": "kick.808", "S": "snare.tight", "C": "clap", "h": "hat.tight", "O": "ohat", "H": "ohat", "P": "rim", "T": "tom"},
    "rock":   {"K": "kick.hard", "S": "snare", "h": "hat", "R": "ride", "O": "ohat", "T": "tom", "P": "tom.hi", "C": "clap"},
    "orch":   {"K": "taiko", "S": "snare.orch", "T": "timpani", "P": "taiko.rim", "h": "shaker", "C": "clap", "R": "ride"},
    "chip":   {"K": "chip.k", "S": "chip.s", "h": "chip.h", "C": "chip.s", "T": "chip.k", "O": "chip.h"},
    "lofi":   {"K": "kick.soft", "S": "snare.lofi", "h": "hat", "O": "ohat", "P": "shaker", "R": "ride", "C": "rim"},
    "dub":    {"K": "kick.soft", "S": "rim", "h": "hat", "O": "ohat", "P": "shaker", "C": "clap"},
    "tribal": {"K": "taiko", "B": "block", "P": "taiko.rim", "D": "doum", "E": "tek", "S": "snare.orch", "T": "tom", "h": "shaker"},
    "desert": {"D": "doum", "E": "tek", "h": "shaker", "K": "doum", "S": "tek", "C": "clap", "T": "tom", "P": "tabla"},
    "metal":  {"K": "kick.hard", "S": "snare.tight", "R": "ride", "h": "hat", "T": "tom", "A": "anvil", "C": "clap", "O": "ohat"},
    "indus":  {"K": "kick.hard", "S": "snare.tight", "A": "anvil", "h": "hat.tight", "C": "clap", "T": "tom", "O": "ohat"},
    "glitch": {"K": "kick.hard", "S": "glitch", "G": "glitch.blip", "h": "hat.tight", "C": "glitch.zap", "T": "tom.hi", "O": "ohat"},
    "clock":  {"K": "kick.soft", "P": "clave", "B": "block", "S": "rim", "h": "hat.tight", "T": "timpani"},
    "celtic": {"K": "bodhran", "P": "shaker", "S": "rim", "h": "shaker", "T": "bodhran"},
    "soft":   {"K": "kick.soft", "h": "shaker", "S": "rim", "P": "shaker", "T": "timpani", "R": "ride"},
}

# ---- bass, harmony and arpeggio figures ---------------------------------------------------------------------------------
def bass_figure(name: str, meter: int, groups: tuple) -> list:
    """[(step, semitone offset from chord root, length)] for one bar."""
    beats, acc = [], 0
    for g in groups:
        beats.append(acc)
        acc += g
    if name == "root":
        return [(0, 0, meter)]
    if name == "pulse8":
        return [(s, 0, 2) for s in range(0, meter, 2)]
    if name == "pulse16":
        return [(s, 0, 1) for s in range(meter)]
    if name == "beats":
        return [(b, 0, g) for b, g in zip(beats, groups)]
    if name == "march":
        return [(b, 0 if k % 2 == 0 else 7, g) for k, (b, g) in enumerate(zip(beats, groups))]
    if name == "octave":
        return [(s, 12 if (s // 2) % 2 else 0, 2) for s in range(0, meter, 2)]
    if name == "gallop":
        return [(s, 0, 1) for s in range(meter) if s % 4 in (0, 3)]
    if name == "walk":
        steps = [0, 4, 7, 9, 12, 10, 7, 5]
        return [(b, steps[k % len(steps)], g) for k, (b, g) in enumerate(zip(beats, groups))]
    if name == "synco":
        return [(s, 0 if s < meter - 4 else 7, 2) for s in (0, 3, 6, 10, 12) if s < meter]
    if name == "dub":
        return [(0, 0, 3), (3, 0, 1), (6, 7, 2), (10, 0, 4)] if meter == 16 else [(0, 0, meter // 2), (meter // 2, 7, meter // 2)]
    if name == "chug":
        return [(s, 0, 1) for s in range(meter) if s % 4 != 2]
    if name == "808":
        return [(0, 0, 7), (7, 0, 3), (10, -2, 6)] if meter == 16 else [(0, 0, meter)]
    if name == "waltz":
        return [(0, 0, 4)]
    if name == "jig":
        return [(b, 0 if k % 2 == 0 else 7, g) for k, (b, g) in enumerate(zip(beats, groups))]
    if name == "drone":
        return [(0, 0, meter)]
    if name == "acid":
        pat = [(0, 0), (1, 12), (3, 0), (4, 0), (6, 12), (7, 0), (8, 0), (10, 0), (11, 12), (13, 0), (14, 7)]
        return [(s, o, 1) for s, o in pat if s < meter]
    if name == "boogie":
        steps = [0, 4, 7, 9, 10, 9, 7, 4]
        return [(s, steps[(s // 2) % 8], 2) for s in range(0, meter, 2)]
    return [(0, 0, meter)]


ARPS = {"up": [0, 1, 2, 3], "updown": [0, 1, 2, 3, 2, 1], "down": [3, 2, 1, 0], "broken": [0, 2, 1, 3], "alberti": [0, 2, 1, 2],
        "octave": [0, 3], "trill": [0, 1], "pulse": [0, -1], "spread": [0, 2, 3, 4, 3, 2], "five": [0, 1, 2, 1, 3]}

# ---- arrangement styles ----------------------------------------------------------------------------------------------------
# kit/groove/fill: drums. bass/bass_i: bass figure + instrument. harm: "pad" | "arp:<shape>:<rate>" | "stab:<rhythm>" |
# "oompah" | "power:<rhythm>" | "strum:<rhythm>"; harm_i its instrument. pad: optional sustained bed. lead/lead2/counter:
# instruments. swing (0..0.3), pump (sidechain depth), echo (lead echo in beats), oct (lead octave shift).
STYLES = {
    "epic":     dict(kit="orch", groove="boom", fill="taiko", bass="beats", bass_i="strings", harm="arp:alberti:2", harm_i="stacc", pad="strings",
                     lead="brass", lead2="choir", counter="horn", oct=0),
    "march":    dict(kit="orch", groove="march", fill="snare", bass="march", bass_i="pizz", harm="stab:x---x---x---x---", harm_i="brass", pad="strings",
                     lead="brass", lead2="flute", counter="horn"),
    "synthwave": dict(kit="pop", groove="four", fill="tom", bass="pulse8", bass_i="bass", harm="arp:up:1", harm_i="pizz", pad="pad",
                      lead="supersaw", lead2="hollow", counter="glasspad", pump=0.45, echo=0.75),
    "chip":     dict(kit="chip", groove="chip", fill="chip", bass="octave", bass_i="chipbass", harm="arp:up:1", harm_i="chip", pad=None,
                     lead="square", lead2="chiptri", counter="chip", oct=12),
    "dnb":      dict(kit="pop", groove="dnb", fill="snare", bass="root", bass_i="reese", harm="arp:broken:2", harm_i="pizz", pad="pad",
                     lead="hollow", lead2="glasspad", counter="strings", pump=0.25, echo=0.75),
    "trap":     dict(kit="808", groove="trap", fill="snare", bass="808", bass_i="808", harm="arp:pulse:2", harm_i="bell", pad="warmpad",
                     lead="bell", lead2="flute", counter="choir_o"),
    "metal":    dict(kit="metal", groove="metal", fill="tom", bass="chug", bass_i="chug", harm="power:x-------x---x---", harm_i="power", pad=None,
                     lead="saw", lead2="organ", counter="choir", oct=0),
    "metal2":   dict(kit="metal", groove="metal2", fill="tom", bass="gallop", bass_i="chug", harm="power:x-----x-x-------", harm_i="power", pad="choir",
                     lead="supersaw", lead2="brass", counter="organ"),
    "techno":   dict(kit="808", groove="techno", fill="snare", bass="acid", bass_i="acid", harm="stab:--x---x---x-x---", harm_i="stacc", pad="pad",
                     lead="square", lead2="glasspad", counter="hollow", pump=0.5, echo=0.75),
    "ambient":  dict(kit="soft", groove="ambient", fill="none", bass="root", bass_i="sub", harm="pad", harm_i="warmpad", pad="glasspad",
                     lead="celesta", lead2="flute", counter="glasspad", echo=1.0),
    "waltz":    dict(kit="lofi", groove="waltz", fill="none", bass="waltz", bass_i="fingerbass", harm="oompah", harm_i="pizz", pad="strings",
                     lead="flute", lead2="music_box", counter="strings"),
    "jig":      dict(kit="celtic", groove="jig", fill="none", bass="jig", bass_i="fingerbass", harm="strum:x--x--", harm_i="guitar", pad=None,
                     lead="flute", lead2="harp", counter="reed"),
    "balkan":   dict(kit="desert", groove="balkan", fill="none", bass="beats", bass_i="fingerbass", harm="stab:x---x---x-----", harm_i="organ", pad=None,
                     lead="reed", lead2="flute", counter="brass"),
    "desert":   dict(kit="desert", groove="desert", fill="none", bass="drone", bass_i="drone", harm="arp:spread:2", harm_i="sitar", pad="warmpad",
                     lead="erhu", lead2="sitar", counter="reed"),
    "eastern":  dict(kit="tribal", groove="eastern", fill="taiko", bass="beats", bass_i="fingerbass", harm="arp:broken:2", harm_i="koto", pad="warmpad",
                     lead="flute", lead2="koto", counter="erhu"),
    "gothic":   dict(kit="orch", groove="boom2", fill="taiko", bass="beats", bass_i="organ", harm="pad", harm_i="organ", pad="choir",
                     lead="organ", lead2="choir_o", counter="harpsi"),
    "industrial": dict(kit="indus", groove="indus", fill="tom", bass="pulse16", bass_i="reese", harm="power:x--x--x---x-----", harm_i="power", pad="drone",
                       lead="saw", lead2="theremin", counter="stacc", pump=0.35),
    "dub":      dict(kit="dub", groove="dub", fill="none", bass="dub", bass_i="sub", harm="stab:----x-------x---", harm_i="organ", pad="warmpad",
                     lead="theremin", lead2="ep", counter="vibes", echo=0.75),
    "glitch":   dict(kit="glitch", groove="glitch", fill="glitch", bass="synco", bass_i="acid", harm="arp:spread:1", harm_i="bell", pad="glasspad",
                     lead="square", lead2="music_box", counter="hollow", pump=0.4, echo=0.5),
    "cosmic":   dict(kit="soft", groove="soft", fill="none", bass="root", bass_i="sub", harm="arp:spread:2", harm_i="celesta", pad="choir",
                     lead="glasspad", lead2="theremin", counter="choir_o", echo=1.0),
    "horror":   dict(kit="orch", groove="ambient", fill="none", bass="drone", bass_i="drone", harm="pad", harm_i="glasspad", pad="choir_o",
                     lead="theremin", lead2="music_box", counter="strings"),
    "hymn":     dict(kit="soft", groove="none", fill="none", bass="root", bass_i="organ", harm="pad", harm_i="organ", pad="choir",
                     lead="choir_o", lead2="celesta", counter="strings"),
    "hyper":    dict(kit="metal", groove="hyper", fill="snare", bass="octave", bass_i="hoover", harm="stab:x-x-x-x-x-x-x-x-", harm_i="supersaw", pad=None,
                     lead="supersaw", lead2="square", counter="hoover", pump=0.6),
    "clock":    dict(kit="clock", groove="clock", fill="none", bass="march", bass_i="pizz", harm="arp:alberti:2", harm_i="harpsi", pad="strings",
                     lead="harpsi", lead2="music_box", counter="reed"),
    "western":  dict(kit="rock", groove="western", fill="tom", bass="gallop", bass_i="fingerbass", harm="strum:x--x--x---x--x--", harm_i="guitar", pad=None,
                     lead="guitar", lead2="theremin", counter="brass"),
    "folk":     dict(kit="lofi", groove="soft", fill="none", bass="beats", bass_i="fingerbass", harm="strum:x---x-x-x---x-x-", harm_i="guitar", pad="warmpad",
                     lead="flute", lead2="harp", counter="strings"),
    "house":    dict(kit="pop", groove="house", fill="snare", bass="octave", bass_i="bass", harm="stab:--x---x---x---x-", harm_i="ep", pad="warmpad",
                     lead="ep", lead2="vibes", counter="strings", pump=0.4),
    "funk":     dict(kit="pop", groove="funk", fill="tom", bass="boogie", bass_i="fingerbass", harm="stab:--x--x----x--x--", harm_i="brass", pad=None,
                     lead="brass", lead2="organ", counter="ep"),
    "lullaby":  dict(kit="soft", groove="none", fill="none", bass="root", bass_i="sub", harm="arp:alberti:2", harm_i="music_box", pad="warmpad",
                     lead="celesta", lead2="music_box", counter="glasspad", echo=1.0),
    "fanfare":  dict(kit="orch", groove="march", fill="snare", bass="march", bass_i="horn", harm="stab:x---x-x-x---x---", harm_i="brass", pad="strings",
                     lead="brass", lead2="horn", counter="choir"),
}
STEMS = ("drums", "bass", "harm", "pad", "lead", "counter")
STEM_PAN = {"drums": 0.0, "bass": 0.0, "harm": -0.35, "pad": 0.15, "lead": 0.2, "counter": -0.25}
STEM_GAIN = {"drums": 0.85, "bass": 0.9, "harm": 0.6, "pad": 0.5, "lead": 0.9, "counter": 0.5}
SECTION_BARS = {"I": 4, "A": 8, "A2": 8, "B": 8, "B2": 8, "C": 8, "D": 4, "X": 8, "O": 4}


class SongSpec:
    """One hand-specified piece of music."""

    def __init__(self, key, name, cat, bpm, root, scale, meter, style, prog, mel, form="I A B A2 C X O", desc="", **kw):
        self.key, self.name, self.cat, self.bpm, self.root, self.scale = key, name, cat, bpm, root, scale
        self.meter, self.style, self.prog, self.mel, self.form, self.desc = meter, style, prog, mel, form, desc
        self.kw = kw

    def get(self, k, default=None):
        return self.kw.get(k, STYLES[self.style].get(k, default))


class Song:
    """A composed song: time-sorted events (sample, stem, note key, velocity, pan) plus section markers."""

    def __init__(self, sid, events, total, secs, spb) -> None:
        self.sid, self.events, self.total, self.secs, self.spb = sid, events, total, secs, spb
        self.times = [e[0] for e in events]
        self.keys = {e[2] for e in events}


def compose(spec: SongSpec) -> Song:
    sc = SCALES[spec.scale]
    meter, groups = METERS[spec.meter]
    spb = 60.0 / spec.bpm / 4                                   # seconds per 16th step
    rng = random.Random(sum(map(ord, spec.key)) * 7919)
    st = STYLES[spec.style]
    kit = KITS[spec.get("kit")]
    root = spec.root
    swing = spec.get("swing", 0.0)
    oct_ = spec.get("oct", 0)
    ev, secs = [], {}
    step0 = 0

    def add(step, stem, key, vel, pan=None):
        sw = swing * spb if (step % 2 == 1) else 0.0
        ev.append((int((step * spb + sw) * AU_SR), stem, key, max(0.05, min(1.2, vel)), STEM_PAN[stem] if pan is None else pan))

    progs = {k: [parse_chord(t, sc) for t in v.split()] for k, v in spec.prog.items()}
    mels = {k: parse_mel(v, sc, meter) for k, v in spec.mel.items()}
    mel_len = {k: max(1, -(-max((s + l for s, _, l in v), default=meter) // meter)) for k, v in mels.items()}
    lead_i, lead2_i, counter_i = spec.get("lead"), spec.get("lead2"), spec.get("counter")
    harm, harm_i, pad_i = spec.get("harm"), spec.get("harm_i"), spec.get("pad")
    bass_name, bass_i = spec.get("bass"), spec.get("bass_i")
    groove, groove_b = GROOVES[spec.get("groove")], GROOVES[spec.get("groove_b", spec.get("groove"))]
    fill = FILLS[spec.get("fill")]
    lead_base = root + 24 + oct_
    seq = spec.get("seq", 2)                                    # how far (in scale steps) the varied restatement moves
    for sec in spec.form.split():
        bars = SECTION_BARS.get(sec, 8)
        secs.setdefault(sec, int(step0 * spb * AU_SR))
        letter = sec[0]
        prog = progs.get("B" if letter == "B" else "C" if (letter == "C" and "C" in progs) else "A")
        melk = "B" if letter == "B" else "C" if (letter == "C" and "C" in mels) else "A"
        mel = mels.get(melk, mels["A"])
        mlen = mel_len.get(melk, 2)
        loud = {"I": 0.55, "A": 0.85, "A2": 0.95, "B": 0.85, "B2": 0.95, "C": 0.6, "D": 0.8, "X": 1.0, "O": 0.5}.get(sec, 0.85)
        drums_on = sec in ("A", "A2", "B", "B2", "X", "D") or (sec == "C" and spec.get("c_drums", False))
        for bar in range(bars):
            b0 = step0 + bar * meter
            ch_root, iv = prog[bar % len(prog)]
            croot = root + ch_root
            tones = [croot + i for i in iv[:3]] + [croot + 12]
            last_bar = bar == bars - 1
            # --- drums
            if drums_on and st.get("groove") != "none":
                g = fill if (last_bar and bars >= 8 and fill and meter == 16) else (groove_b if letter == "B" else groove)
                if sec == "D":
                    g = {"S": "x-x-x-x-x-x-x-x-" if bar < bars - 1 else "xxxxxxxxxxxxxxxx", "K": "x---x---x---x---"} if meter == 16 else groove
                for lane, pat in g.items():
                    name = kit.get(lane)
                    if not name:
                        continue
                    for s, c in enumerate(pat[:meter]):
                        if c in "xo":
                            v = (1.0 if c == "x" else 0.45) * (1.08 if s == 0 else 1.0) * rng.uniform(0.9, 1.0) * loud
                            if sec == "D" and lane == "S":
                                v *= 0.4 + 0.6 * (bar * meter + s) / (bars * meter)
                            add(b0 + s, "drums", ("drum", name), v * drum_gain(name))
                if bar == 0 and sec in ("A", "A2", "X", "B2"):
                    add(b0, "drums", ("drum", "gong" if spec.style in ("eastern", "gothic", "hymn") else "crash"), 0.5 * loud)
            elif sec in ("I", "C") and st.get("kit") in ("orch", "tribal") and bar % 2 == 0:
                add(b0, "drums", ("drum", "timpani" if st.get("kit") == "orch" else "taiko"), 0.45 * loud)
            if sec == "D" and bar == 0:
                add(b0, "drums", ("drum", "riser"), 0.55)
            # --- outro: one held cadence chord, low root and a closing hit, for the whole outro
            if sec == "O":
                if bar == 0:
                    L_ = bars * meter
                    for t_ in tones[:3]:
                        add(b0, "harm", (pad_i or harm_i, t_ + 12, L_), 0.45)
                    add(b0, "bass", (bass_i if bass_i not in ("chug", "acid", "808", "wob") else "sub", croot - 12 if croot - 12 >= root - 12 else croot, L_), 0.7)
                    add(b0, "drums", ("drum", "gong" if spec.style in ("eastern", "gothic", "hymn", "horror") else "timpani" if st.get("kit") == "orch" else "crash"), 0.5)
                    add(b0 + meter, "lead", (lead2_i, _nearest_tone(lead_base, tones), (bars - 1) * meter), 0.4)
                continue
            # --- bass
            if sec != "O" or bar == 0:
                fig = bass_figure("root" if sec in ("I", "C", "O") else bass_name, meter, groups)
                for s, off, ln in fig:
                    m = croot - 12 + off
                    while m < root - 12:
                        m += 12
                    add(b0 + s, "bass", (bass_i, m, ln), 0.9 * loud * rng.uniform(0.92, 1.0))
            # --- harmony figure
            hseq = harm.split(":")
            if sec in ("O",) and bar > 0:
                pass
            elif hseq[0] == "pad" or sec in ("I", "C", "O"):
                if bar % 2 == 0 or meter < 16:
                    ln = meter * (2 if meter >= 16 else 1)
                    for k, t_ in enumerate(tones[:3]):
                        add(b0, "harm", (harm_i if hseq[0] == "pad" else (pad_i or "pad"), t_ + 12, ln), 0.5 * loud)
            elif hseq[0] == "arp":
                shape, rate = ARPS[hseq[1]], int(hseq[2])
                for k, s in enumerate(range(0, meter, rate)):
                    idx = shape[k % len(shape)]
                    if idx < 0:
                        continue
                    n = tones[idx % 4] + (12 if idx >= 4 else 0) + 12
                    add(b0 + s, "harm", (harm_i, n, rate if rate > 1 else 2), 0.62 * loud * (1.05 if s % 4 == 0 else 0.9))
            elif hseq[0] in ("stab", "power", "strum"):
                rhythm = (hseq[1] * 4)[:meter]
                for s, c in enumerate(rhythm):
                    if c != "x":
                        continue
                    if hseq[0] == "power":
                        add(b0 + s, "harm", (harm_i, croot - 12 if croot - 12 >= root - 12 else croot, 3), 0.7 * loud)
                    elif hseq[0] == "strum":
                        for k, t_ in enumerate(tones[:4]):
                            add(b0 + s, "harm", (harm_i, t_ + 12, 6), 0.45 * loud, -0.35 + 0.2 * k)
                    else:
                        for t_ in tones[:3]:
                            add(b0 + s, "harm", (harm_i, t_ + 12, 2), 0.42 * loud)
            elif hseq[0] == "oompah":
                for b in range(1, len(groups)):
                    s = sum(groups[:b])
                    for t_ in tones[:3]:
                        add(b0 + s, "harm", (harm_i, t_ + 12, 2), 0.4 * loud)
            # --- sustained bed
            if pad_i and hseq[0] != "pad" and sec not in ("I", "C", "O") and bar % 2 == 0 and spec.get("bed", True):
                for t_ in tones[:3]:
                    add(b0, "pad", (pad_i, t_ + 12, meter * 2), 0.38 * loud)
            # --- melody
            mbar = bar % mlen
            phrase = bar // mlen
            for s, semi, ln in mel:
                if not (mbar * meter <= s < (mbar + 1) * meter):
                    continue
                ss = s - mbar * meter
                if sec in ("I", "O"):
                    if bar >= 2 or sec == "O":
                        continue
                    inst, vel, octs = lead2_i, 0.55, 0
                elif sec == "C":
                    inst, vel, octs = lead2_i, 0.6, 0
                elif sec == "D":
                    continue
                else:
                    inst, vel, octs = lead_i, 0.8, (12 if sec in ("X",) and spec.get("x_up", True) else 0)
                m = lead_base + semi + octs
                if sec in ("A2", "B2", "X") and phrase % 2 == 1 and spec.get("vary", True):
                    m = lead_base + deg_shift(sc, semi, seq) + octs              # the restatement climbs
                if last_bar and ss + ln >= meter - 1 and sec not in ("C",):
                    m = _nearest_tone(m, tones)                                 # cadence onto a chord tone
                L = ln if sec != "C" else ln * 2
                add(b0 + ss, "lead", (inst, m, L), vel * loud * (1.06 if ss % groups[0] == 0 else 0.94))
                if sec in ("A2", "B2", "X") and counter_i:
                    add(b0 + ss, "counter", (counter_i, _below_tone(m, tones), max(ln, 4)), 0.42 * loud)
        step0 += bars * meter
    ev.sort(key=lambda e: e[0])
    return Song(spec.key, ev, int(step0 * spb * AU_SR), secs, spb)


def deg_shift(sc: tuple, semi: int, k: int) -> int:
    """Move a melody note k scale steps (keeps it in the mode)."""
    octv, rem = divmod(semi, 12)
    L = len(sc)
    best = min(range(L), key=lambda i: abs(sc[i] - rem))
    return deg_semi(sc, best + 1 + k) + 12 * octv + (rem - sc[best])


def _nearest_tone(m: int, tones: list) -> int:
    cands = [t + 12 * o for t in tones[:3] for o in range(-2, 5)]
    return min(cands, key=lambda c: (abs(c - m), c))


def _below_tone(m: int, tones: list) -> int:
    cands = [t + 12 * o for t in tones[:3] for o in range(-2, 5) if t + 12 * o <= m - 3]
    return max(cands) if cands else m - 12
