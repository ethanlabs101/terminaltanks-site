"""Sound effects: named effects for the interface, battles, story and the Blessing, plus a unique fire and impact sound
for every ammo (its launch and blast families, varied by a seed from the ammo's key)."""
from __future__ import annotations

import random
import zlib

from tanks.audio.synth import (
    _formant_weights, au_bell, au_crush, au_drive, au_drum, au_mix, au_noise, au_peak, au_space, au_table, au_tone, au_wave
)
from tanks.content.ammo import AMMO_BY_KEY


def _sfx_named() -> dict:
    T, N, M, P, B = au_tone, au_noise, au_mix, au_peak, au_bell
    R = {}
    C5, E5, G5, C6, E6, G6 = 523.25, 659.25, 783.99, 1046.5, 1318.5, 1568.0
    shimmer = lambda d, amp=0.4: N(d, 1.0, 0.25, 6.0 / max(d, 0.1), 0.01, amp, seed=3)
    swell = lambda fs, d, amp=.5, lpa=.18: M([(T(f, d, "saw", amp, 1.2, .18, det=.006, lp=lpa), 0, 1) for f in fs])
    # ---- interface
    R["ui_move"] = lambda: P(M([(T(1500, .045, "sine", 1, 60), 0, 1), (T(3000, .03, "sine", 1, 90), 0, .3)]), .34)
    R["ui_tab"] = lambda: P(M([(N(.02, 1, .3, 100), 0, .5), (T(980, .035, "sine", 1, 60), 0, 1)]), .36)
    R["ui_select"] = lambda: P(M([(T(740, .07, "square", 1, 20, duty=.4, lp=.5), 0, 1), (T(1110, .11, "square", 1, 16, duty=.4, lp=.5), .055, 1)]), .46)
    R["ui_back"] = lambda: P(M([(T(620, .06, "square", 1, 22, lp=.5), 0, 1), (T(410, .1, "square", 1, 18, lp=.5), .05, 1)]), .42)
    R["ui_error"] = lambda: P(M([(au_drive(T(120, .12, "saw", 1, 8), 3), 0, 1), (au_drive(T(120, .14, "saw", 1, 8), 3), .15, 1)]), .5)
    R["ui_toggle"] = lambda: P(M([(T(1320, .04, "square", 1, 50, lp=.5), 0, 1), (T(1760, .05, "square", 1, 40, lp=.5), .035, .8)]), .4)
    R["ui_buy"] = lambda: P(M([(B(f, .55, 1, 7), i * .07, 1) for i, f in enumerate((1047, 1319, 1568, 2093, 2637))] + [(shimmer(.45), .25, .5)]), .66)
    R["ui_equip"] = lambda: P(M([(N(.08, .25, 0, 40), 0, 1.0), (T(300, .16, "saw", 1, 14, f1=900, lp=.3), .03, .6), (T(1800, .05, "sine", 1, 60), .16, .5)]), .56)
    R["ui_unlock"] = lambda: P(M([(swell([C5, E5, G5, C6], 1.1, .5), 0, 1)] + [(B(f, 1.0, 1, 4), .08 * i, .6) for i, f in enumerate((C6, E6, G6, 2093))]
                                 + [(shimmer(.7), .3, .4)]), .72)
    R["ui_open"] = lambda: P(N(.3, .03, 0.02, 4, .04, lp1=.6), .4)
    R["ui_type"] = lambda: P(T(2300, .014, "square", 1, 120, lp=.6), .26)
    R["ui_page"] = lambda: P(M([(N(.09, .5, .2, 25, .01, seed=8), 0, 1), (T(700, .06, "sine", 1, 40, f1=1100), 0, .4)]), .38)
    R["ui_start"] = lambda: P(M([(N(.6, .02, .0, 2.5, .2, lp1=.7), 0, .7), (T(110, .7, "saw", 1, 2.4, .02, f1=440, lp=.2), 0, .6),
                                 (B(880, .8, 1, 4), .5, .5), (B(1320, .8, 1, 4), .58, .4)]), .7)
    R["coin"] = lambda: P(M([(B(1976, .25, 1, 10), 0, 1), (B(2637, .3, 1, 9), .06, .8)]), .48)
    R["achieve"] = lambda: P(M([(B(f, .9, 1, 5), .09 * i, 1) for i, f in enumerate((G5, 1174.7, 1568, 2349))] + [(shimmer(.6), .2, .4)]), .7)
    R["rps_shake"] = lambda: P(M([(N(.06, .3, .05, 40, seed=12), 0, 1), (T(180, .07, "sine", 1, 30, f1=120), 0, .7)]), .5)
    R["rps_reveal"] = lambda: P(M([(N(.12, .6, .1, 20, seed=13), 0, .8), (T(440, .2, "square", 1, 12, lp=.5), .01, .5), (B(880, .4, 1, 7), .02, .6)]), .6)
    # ---- battle
    R["aim_tick"] = lambda: P(M([(T(2600, .012, "square", 1, 160, lp=.5), 0, 1), (N(.01, 1, .5, 200, seed=14), 0, .4)]), .16)
    R["power_tick"] = lambda: P(T(900, .02, "tri", 1, 100), .16)
    R["turn_you"] = lambda: P(M([(B(988, .35, 1, 8), 0, 1), (B(1319, .4, 1, 7), .08, 1)]), .44)
    R["turn_cpu"] = lambda: P(M([(T(392, .12, "square", 1, 18, lp=.35), 0, 1), (T(330, .14, "square", 1, 16, lp=.35), .1, 1)]), .32)
    R["tank_hit"] = lambda: P(M([(T(f, .5, "sine", 1, 7), 0, g) for f, g in ((180, 1.0), (437, .5), (811, .3), (1290, .2))]
                                + [(N(.25, .5, .05, 14, seed=15), 0, .9), (T(70, .3, "sine", 1, 10, f1=40), 0, 1.2)]), .85)
    R["shield_block"] = lambda: P(M([(B(1568, .55, 1, 6), 0, 1), (T(700, .4, "sine", 1, 6), 0, .5), (T(2800, .2, "saw", 1, 14, f1=300, lp=.5), 0, .5)]), .66)
    R["tank_destroy"] = lambda: P(M([(T(75, 1.6, "sine", 1, 2.6, f1=26), 0, 1.6), (N(1.4, .45, 0, 2.8, .001, lp1=.02), 0, 1.3),
                                     (N(.06, 1, .15, 40), 0, 1.0), (N(.9, .2, .02, 3.5, .02, seed=16), .25, .8),
                                     (M([(N(.03, 1, .3, 90, seed=40 + k), 0, 1) for k in range(1)]), .45, .5),
                                     (M([(T(1200 + 300 * k, .08, "sine", 1, 40), 0, 1) for k in range(1)]), .6, .3)]), .95)
    R["debris"] = lambda: P(M([(N(.03, .8, .2, 80, seed=50 + k), .05 * k + .02 * k * k, .6 - .05 * k) for k in range(8)]), .5)
    R["settle"] = lambda: P(M([(N(.9, .06, 0, 3, .1, seed=17, lp1=.02), 0, 1), (T(55, .8, "sine", 1, 3), 0, .5)]), .45)
    R["mound"] = lambda: P(M([(N(.5, .08, 0, 5, .05, seed=18), 0, 1), (T(140, .3, "sine", 1, 8, f1=220), 0, .5)]), .5)
    R["wind_gust"] = lambda: P(N(1.6, .02, .005, 0.0, .6, .6, seed=19, lp1=.09), .4)
    R["special_charge"] = lambda: P(M([(T(220, .9, "saw", 1, 1.2, .1, f1=880, lp=.25), 0, 1), (shimmer(.6), .3, .5)]), .55)
    R["special_fire"] = lambda: P(M([(T(60, .8, "sine", 1, 3.5, f1=30), 0, 1.4), (N(.7, .35, 0, 3.0, .01), 0, 1.0),
                                     (T(880, .6, "saw", 1, 3, f1=110, lp=.4), 0, .5)]), .9)
    R["ufo_hop"] = lambda: P(M([(T(300, .35, "sine", 1, 4, f1=1800, vib=.05), 0, 1), (T(1800, .3, "sine", 1, 5, f1=300), .2, .6)]), .55)
    R["ufo_volley"] = lambda: P(M([(T(1400, .18, "square", 1, 12, f1=400, lp=.5), k * .14, .8) for k in range(3)]), .6)
    R["round_win"] = lambda: P(M([(B(f, .7, 1, 5), .1 * i, 1) for i, f in enumerate((C5, E5, G5, C6))]), .66)
    R["round_lose"] = lambda: P(M([(T(f, .45, "saw", 1, 3.5, .02, lp=.12), .18 * i, 1) for i, f in enumerate((392, 349, 311))]), .55)
    R["match_win"] = lambda: P(M([(swell([C5, E5, G5, C6], 2.2, .6, .25), 0, 1)] + [(B(f, 1.6, 1, 3.5), .13 * i, .8) for i, f in enumerate((C6, E6, G6, 2093, 2637))]
                                 + [(T(65, 1.2, "sine", 1, 2), 0, 1.0), (au_drum("crash"), 0, .5)]), .85)
    R["match_lose"] = lambda: P(M([(T(f, .6, "saw", 1, 3.0, .02, lp=.12), .25 * i, 1) for i, f in enumerate((330, 294, 262, 247))]
                                  + [(T(55, 1.6, "sine", 1, 1.6), 0, .8), (au_drum("gong"), .9, .4)]), .7)
    R["payout"] = lambda: P(M([(B(f, .3, 1, 9), .055 * i, 1) for i, f in enumerate((1976, 2349, 2637, 3136, 2637, 3520))]), .55)
    R["banner"] = lambda: P(M([(N(.35, .05, .01, 6, .05, lp1=.5), 0, .8), (T(220, .3, "saw", 1, 6, f1=660, lp=.3), 0, .5)]), .5)
    # ---- story
    R["whisper"] = lambda: P(au_space(M([(au_wave(f, 2.4, 1, au_table(_formant_weights(f, ((450, 120, 1.0), (850, 140, .5), (2700, 260, .15)))),
                                                   env=(0.6, 0.0, 1.0, 0.9), voices=(0.99, 1.01), vib=(0.01, 3.5, 0.0)), 0, .5) for f in (196, 293.7, 392)]
                                         + [(N(2.4, .3, .1, 0.6, .6, .3, seed=21), 0, .6)]), 0.8, 0.4), .5)
    R["cine_hit"] = lambda: P(M([(au_drum("boom"), 0, 1), (au_drum("gong"), 0, .4)]), .8)
    R["time_machine"] = lambda: P(au_space(M([(au_tone(f, 3.0, "sine", 1, .8, .4, vib=.004), 0, .5) for f in (110, 165, 220, 277, 330)]
                                              + [(au_drum("clave"), .25 * k, .5) for k in range(10)] + [(au_drum("riser"), 1.2, .7), (au_drum("gong"), 3.0, .9)]), 1.0, .35), .85)
    # ---- Martyr's Blessing
    R["bless_tick"] = lambda: P(M([(au_drum("clave"), 0, 1), (B(2093, .3, 1, 9), 0, .4)]), .45)
    R["bless_choir"] = lambda: P(au_space(M([(au_wave(f, 3.0, 1, au_table(_formant_weights(f, ((700, 130, 1.0), (1220, 140, .55), (2600, 220, .25)))),
                                                      env=(0.8, 0.0, 1.0, 0.6), voices=(0.994, 1.0, 1.006), vib=(0.005, 5.0, 0.3)), 0, .4)
                                             for f in (261.6, 329.6, 392.0, 523.3, 659.3)]), 1.0, .4), .75)
    R["bless_star"] = lambda: P(M([(T(1800, .35, "sine", 1, 8, f1=600), 0, 1), (B(2637, .4, 1, 7), .02, .5)]), .45)
    R["bless_pillar"] = lambda: P(M([(T(2400, .3, "saw", 1, 10, f1=200, lp=.5), 0, .6), (T(80, .9, "sine", 1, 4, f1=35), .12, 1.4),
                                     (N(.6, .4, .02, 5, .005), .12, 1.0), (B(1568, .9, 1, 4), .12, .5)]), .9)
    R["bless_nuke"] = lambda: P(M([(N(4.0, .9, 0, 1.0, .001, 1.0, seed=31, lp1=.01), 0, 1.4), (T(48, 4.0, "sine", 1, .7, .01, f1=24), 0, 1.8),
                                   (T(90, 3.0, "saw", 1, 1.0, .02, f1=30, lp=.08), 0, .8), (N(.08, 1, .2, 30), 0, 1.0)]), .98)
    R["bless_firewall"] = lambda: P(N(3.0, .25, .01, 0.6, .4, .9, seed=32, lp1=.04), .7)
    R["bless_grant"] = lambda: P(au_space(M([(swell([261.6, 329.6, 392, 523.3, 659.3], 3.0, .55, .22), 0, 1)]
                                             + [(B(f, 1.6, 1, 3), .12 * i + .3, .7) for i, f in enumerate((1047, 1319, 1568, 2093, 2637, 3136))]
                                             + [(au_drum("gong"), 0, .6), (shimmer(1.6), .4, .5)]), 1.0, .4), .85)
    return R


SFX_RECIPES = _sfx_named()


def _ammo_rng(key: str, salt: int) -> random.Random:
    return random.Random(zlib.crc32(key.encode()) * 31 + salt)


def sfx_fire(key: str, proj: str) -> list:
    """The launch sound of one ammo: its family's character, varied by the ammo's own seed."""
    r = _ammo_rng(key, 1)
    T, N = au_tone, au_noise
    k = r.uniform(0.78, 1.32)
    base = [(N(.08, .5, .05, 30, .001, seed=r.randrange(999)), 0, .9), (T(95 * k, .2, "sine", 1, 14, f1=45 * k), 0, 1.1)]   # the cannon thump
    fam = {
        "shell": [(N(.04, 1, .2, 60), 0, .6)],
        "streak": [(N(.18, .9, .3, 18, lp1=.3), 0, .7), (T(3000 * k, .15, "sine", 1, 14, f1=900), 0, .4)],
        "comet": [(N(.4, .4, .1, 6, .02, lp1=.9), 0, .7), (T(2400 * k, .3, "sine", 1, 8, f1=4000), .05, .3)],
        "flame": [(N(.5, .25, .02, 4, .02, seed=5), 0, 1.0), (T(140 * k, .45, "saw", 1, 5, lp=.15), 0, .5)],
        "ring": [(T(1200 * k, .35, "sine", 1, 9), 0, .6), (T(1800 * k, .3, "sine", 1, 11), .02, .4)],
        "sun": [(T(220 * k, .4, "saw", 1, 6, f1=660 * k, lp=.3), 0, .6), (N(.25, .5, .1, 10), 0, .5)],
        "drip": [(T(500 * k, .18, "sine", 1, 12, f1=1300 * k), 0, .8), (T(300 * k, .14, "sine", 1, 18, f1=900 * k), .08, .5)],
        "star": [(au_bell(1760 * k, .4, 1, 8), 0, .6), (au_bell(2640 * k, .3, 1, 10), .05, .4)],
        "lava": [(N(.45, .12, .01, 4, .03, seed=6), 0, 1.0), (T(70 * k, .4, "sine", 1, 5, vib=.06), 0, .7)],
        "orb": [(T(700 * k, .4, "sine", 1, 6, vib=.04), 0, .7), (T(1050 * k, .35, "sine", 1, 7, vib=.05), 0, .4)],
        "shard": [(au_bell(2200 * k, .3, 1, 12), 0, .7), (N(.1, 1, .5, 40), 0, .4)],
        "spark": [(au_crush(N(.15, 1, .3, 25), 5, 2), 0, .7), (T(2800 * k, .1, "square", 1, 30, lp=.5), 0, .3)],
        "bolt": [(au_drive(N(.2, 1, .2, 16), 3), 0, .7), (T(4000 * k, .2, "saw", 1, 16, f1=300, lp=.6), 0, .4)],
        "prism": [(au_bell(f * k, .5, 1, 6), .03 * i, .4) for i, f in enumerate((1047, 1319, 1568))],
        "helix": [(T(600 * k, .4, "sine", 1, 6, f1=2400 * k, vib=.08), 0, .7)],
        "glyph": [(au_crush(T(f * k, .04, "square", 1, 40), 3, 3), .035 * i, .6) for i, f in enumerate((1200, 1800, 900, 2400))],
        "relic": [(T(f * k, .7, "sine", 1, 3), 0, g) for f, g in ((220, 1.0), (330, .5), (523, .3))],
        "eye": [(T(440 * k, .6, "sine", 1, 3, vib=.03), 0, .5), (T(466 * k, .6, "sine", 1, 3, vib=.03), 0, .5)],
        "void": [(T(400 * k, .5, "sine", 1, 4, f1=60), 0, .8), (N(.4, .1, .01, 4, .1, lp1=.01), 0, .5)],
        "phase": [(T(1500 * k, .25, "sine", 1, 9, f1=200, vib=.03), 0, .7), (T(200 * k, .25, "sine", 1, 9, f1=1500), .1, .5)],
        "xenon": [(au_wave(f * k, .5, 1, au_table(_formant_weights(f, ((450, 120, 1.), (800, 120, .6), (2800, 240, .12)))), env=(.05, .1, .7, .1),
                           voices=(.99, 1.01)), 0, .4) for f in (330, 495)] + [(T(1800 * k, .3, "sine", 1, 9, f1=400), 0, .4)],
        "blessing": [(au_bell(f, 1.0, 1, 4), .05 * i, .5) for i, f in enumerate((1047, 1319, 1568, 2093))] + [(au_drum("clave"), 0, .5)],
        "runes": [(T(f * k, .3, "tri", 1, 8), .05 * i, .5) for i, f in enumerate((660, 990, 880))],
        "sigil": [(au_bell(523 * k, .7, 1, 4), 0, .6), (T(130 * k, .6, "saw", 1, 4, lp=.15), 0, .5)],
        "sandglass": [(N(.6, .9, .4, 3, .1, seed=7), 0, .4), (au_drum("clave"), 0, .5), (au_drum("clave"), .15, .4)],
        "lure": [(T(880 * k, .5, "sine", 1, 5, f1=1320 * k, vib=.05), 0, .5), (au_bell(1760 * k, .5, 1, 6), .05, .35), (N(.3, .2, .05, 8, lp1=.05), 0, .4)],
        "foxfire": [(N(.5, .3, .05, 4, .04, seed=21, lp1=.6), 0, .8), (T(1400 * k, .4, "tri", 1, 6, f1=2100 * k, vib=.06), .02, .35),
                    (au_bell(2349 * k, .4, 1, 7), .08, .25)],
        "lance": [(au_drive(T(3200 * k, .35, "saw", 1, 10, f1=1600 * k, lp=.7), 2.0), 0, .55), (T(6400 * k, .25, "sine", 1, 14), 0, .3),
                  (N(.06, 1, .6, 50), 0, .5)],
        "paradox": [(T(700 * k, .35, "sine", 1, 7, f1=1400 * k), 0, .5), (list(reversed(T(700 * k, .35, "sine", 1, 7, f1=1400 * k))), .05, .45)],
        "atomic": [(T(55 * k, .7, "saw", 1, 3, f1=110 * k, lp=.1), 0, .8), (au_drive(N(.5, .6, .2, 5, .05, seed=22), 2.5), 0, .6),
                   (T(2600 * k, .4, "saw", 1, 7, f1=600, lp=.4), .05, .3)],
        "spore": [(T(300 * k, .12, "sine", 1, 20, f1=700 * k), 0, .7), (N(.35, .4, .1, 8, .02, seed=23, lp1=.3), .03, .5)],
        "worm": [(N(.6, .25, .02, 3.5, .04, seed=24, lp1=.4), 0, .9), (T(65 * k, .6, "saw", 1, 4, vib=.15, lp=.08), 0, .6)],
        "serpent": [(N(.5, .9, .7, 5, .05, seed=25), 0, .5), (T(900 * k, .4, "tri", 1, 6, f1=450 * k, vib=.12), 0, .4)],
        "astro": [(au_bell(f * k, .6, 1, 6), .04 * i, .35) for i, f in enumerate((1568, 1976, 2349, 3136))],
        "cannonball": [(N(.1, 1, .1, 30, seed=26), 0, 1.0), (T(60 * k, .5, "sine", 1, 6, f1=34), 0, 1.2), (N(.5, .3, .02, 5, .03, seed=27, lp1=.5), .03, .5)],
    }.get(proj, [])
    extra = []
    if r.random() < 0.35:                                         # some ammo carry an extra signature layer
        extra.append((au_bell(r.choice((880, 1175, 1568, 2093)) * k, .3, 1, 9), .03, .25))
    return au_peak(au_mix(base + fam + extra), r.uniform(0.62, 0.78))


def sfx_impact(key: str, boom: str, big: float = 1.0) -> list:
    """The blast of one ammo: its family's explosion, varied by the ammo's own seed."""
    r = _ammo_rng(key, 2)
    T, N, M = au_tone, au_noise, au_mix
    k = r.uniform(0.75, 1.3)
    d = r.uniform(0.8, 1.25)
    core = [(T(70 * k, .9 * d, "sine", 1, 4.5 / d, f1=30 * k), 0, 1.4), (N(.8 * d, .45, 0, 4.5 / d, .001, seed=r.randrange(999), lp1=.03), 0, 1.0),
            (N(.05, 1, .15, 40, seed=r.randrange(999)), 0, .9)]
    fam = {
        "classic": [],
        "nova": [(au_bell(1568 * k, .8, 1, 4), .02, .4), (N(.6, 1, .4, 6), .02, .3)],
        "implode": [(T(60 * k, .5, "sine", 1, 1.0, f1=400 * k, curve=2), 0, .7), (N(.4, .1, .05, 1, .35, lp1=.8), 0, .5)],
        "magma": [(N(1.0, .15, .01, 2.5, .05, seed=9), .05, .9), (T(45 * k, 1.0, "sine", 1, 2.5, vib=.08), 0, .8)],
        "cluster": [(M([(N(.05, .8, .1, 45, seed=60 + j), 0, 1), (T((300 + 90 * j) * k, .08, "sine", 1, 30, f1=90), 0, 1)]), .09 + .11 * j, .7) for j in range(4)],
        "starrays": [(au_bell(f * k, .6, 1, 6), .04 * i, .3) for i, f in enumerate((1319, 1760, 2349, 2637))],
        "fire": [(N(.9, .3, .02, 3.2, .03, seed=10), 0, 1.0), (T(120 * k, .7, "saw", 1, 3.5, lp=.12), 0, .5)],
        "shock": [(au_drive(T(2400 * k, .5, "saw", 1, 5, f1=70, lp=.5), 2.5), 0, .6), (au_crush(N(.3, 1, .3, 10), 4, 3), 0, .5)],
        "shatter": [(N(.5, 1, .55, 7, seed=11), 0, .8)] + [(au_bell(f * k, .35, 1, 12), .02 * i, .35) for i, f in enumerate((2637, 3136, 3951, 4699))],
        "thunder": [(N(2.2, .1, .0, 1.6, .002, seed=12, lp1=.02), 0, 1.3), (au_crush(N(.15, 1, .2, 25), 5, 2), 0, .6)],
        "ring": [(T(f * k, 1.0, "sine", 1, 3), 0, g) for f, g in ((880, .5), (1320, .3), (2200, .2))],
        "cloud": [(N(1.2, .5, .2, 2.4, .05, seed=13), 0, .8)],
        "rays": [(T(3000 * k, .4, "saw", 1, 8, f1=600, lp=.5), 0, .5), (T(2000 * k, .4, "saw", 1, 8, f1=400, lp=.5), .05, .4)],
        "prism": [(au_bell(f * k, .9, 1, 4), .03 * i, .35) for i, f in enumerate((1047, 1319, 1568, 2093))],
        "embers": [(M([(N(.02, 1, .4, 120, seed=70 + j), 0, 1)]), .05 + .07 * j * r.uniform(.6, 1.4), .45) for j in range(9)],
        "bloom": [(T(200 * k, .9, "sine", 1, 3, f1=900 * k), 0, .5), (au_bell(1760 * k, .8, 1, 5), .1, .4)],
        "sigil": [(au_bell(f * k, 1.2, 1, 3), 0, .4) for f in (523, 659, 784)] + [(au_drum("gong"), 0, .3)],
        "eclipse": [(T(55 * k, 1.6, "sine", 1, 2), 0, 1.0), (au_wave(130 * k, 1.4, 1, au_table(_formant_weights(130, ((450, 110, 1.), (800, 120, .6))))
                                                                        , env=(.2, 0, 1, .6)), 0, .4)],
        "tidal": [(N(1.2, .35, .05, 2.6, .02, seed=14, lp1=.08), 0, 1.1), (T(160 * k, .5, "sine", 1, 5, f1=90, vib=.1), 0, .5)],
        "alien": [(T(900 * k, .6, "sine", 1, 4, f1=300, vib=.06), 0, .6)],
        "xenon": [(T(f * k, 1.0, "sine", 1, 3, vib=.02), .02 * i, .35) for i, f in enumerate((660, 990, 1320, 1980))] + [(N(.6, 1, .4, 6), 0, .3)],
        "code": [(au_crush(N(.6, 1, .1, 5, seed=15), 3, 6), 0, .7)] + [(T(f, .05, "square", 1, 30), .06 * i, .4) for i, f in enumerate((880, 1320, 660, 1760, 990))],
        "blessing": [(SFX_RECIPES["bless_pillar"](), 0, .7)],
        "cinderstorm": [(N(1.6, .3, .02, 1.8, .05, seed=16), 0, 1.0)] + [(N(.02, 1, .4, 120, seed=80 + j), .2 + .1 * j, .4) for j in range(8)],
        "rewind": [(list(reversed(au_mix([(N(.6, .4, .05, 6), 0, 1), (au_bell(880 * k, .6, 1, 6), 0, .5)]))), 0, .8)],
        "biolume": [(T(f * k, 1.4, "sine", 1, 2.5, vib=.03), .03 * i, .3) for i, f in enumerate((392, 587, 784, 1175))] + [(N(1.0, .2, .05, 2.5, .05, lp1=.04), 0, .5)],
        "foxfire": [(N(1.0, .35, .05, 3, .03, seed=28, lp1=.5), 0, .9)] + [(au_bell(f * k, .5, 1, 6), .05 * i, .25) for i, f in enumerate((1175, 1397, 1760))],
        "hardlight": [(au_drive(T(4000 * k, .6, "saw", 1, 6, f1=200, lp=.6), 2.0), 0, .6), (T(110 * k, .5, "square", 1, 6, lp=.2), 0, .5)],
        "paradox": [(list(reversed(au_mix([(N(.7, .5, .1, 5), 0, 1), (T(300 * k, .6, "sine", 1, 4), 0, .6)]))), 0, .7), (au_bell(1319 * k, .7, 1, 4), .3, .3)],
        "atomic": [(T(40 * k, 2.0, "sine", 1, 1.6, f1=24), 0, 1.4), (N(2.0, .12, .0, 1.5, .01, seed=29, lp1=.02), 0, 1.2),
                   (au_drive(N(.4, 1, .2, 6, seed=30), 3), 0, .5)],
        "spore": [(M([(T((500 + 120 * j) * k, .08, "sine", 1, 30, f1=200), 0, 1)]), .9 + .08 * j, .5) for j in range(6)]
                 + [(N(.8, .4, .2, 4, .1, seed=31, lp1=.2), 0, .5)],
        "eruption": [(N(1.6, .2, .01, 2.2, .06, seed=32, lp1=.05), 0, 1.3), (T(38 * k, 1.4, "sine", 1, 2.2, vib=.1), 0, 1.0),
                     (N(.8, .9, .7, 3, .1, seed=33), .1, .4)],
        "jade": [(au_bell(f * k, .9, 1, 4), .04 * i, .35) for i, f in enumerate((659, 784, 988))] + [(au_drum("anvil"), 0, .4)],
        "zodiac": [(au_bell(f * k, 1.0, 1, 4), .07 * i, .3) for i, f in enumerate((1047, 1319, 1568, 1976, 2637))],
        "ghostfire": [(N(1.0, .3, .05, 3, .03, seed=34, lp1=.4), 0, .9),
                      (au_wave(110 * k, .9, 1, au_table(_formant_weights(110, ((300, 100, 1.), (870, 120, .5)))), env=(.05, .2, .6, .4)), .05, .4)],
    }.get(boom, [])
    if r.random() < 0.3:
        fam = fam + [(au_drum(r.choice(("tom", "tom.hi", "anvil", "rim"))), .05, .25)]
    return au_peak(au_mix(core + fam), min(0.98, r.uniform(0.75, 0.9) * big))


def sfx_build(name: str) -> list:
    """name -> buffer. 'fire:<ammo>' and 'hit:<ammo>' are generated on demand from the ammo catalogue."""
    if name.startswith("fire:"):
        a = AMMO_BY_KEY.get(name[5:])
        return sfx_fire(name[5:], a.proj if a else "shell")
    if name.startswith("hit:"):
        a = AMMO_BY_KEY.get(name[4:])
        return sfx_impact(name[4:], a.boom if a else "classic")
    fn = SFX_RECIPES.get(name)
    return fn() if fn else [0.0]


SFX_DUCK = {"tank_destroy", "match_win", "match_lose", "bless_nuke", "bless_grant", "time_machine", "special_fire", "cine_hit"}
