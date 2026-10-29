"""The synthesis core: oscillators, wavetable instruments, plucks, drum kits and DSP helpers (filters, echo, space)."""
from __future__ import annotations

import math
import random


AU_SR = 22050                    # sample rate of every synthesized buffer
AU_TAU = math.tau


def mtof(m: float) -> float:
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


# ---- generic DSP (plain lists of floats) ------------------------------------------------------------------------------
def au_tone(freq, dur, wv="sine", amp=1.0, decay=4.0, attack=0.003, f1=None, vib=0.0, duty=0.5, det=0.0, lp=None, curve=1.0) -> list:
    """One oscillator with an exponential (or swept) pitch, attack + exponential decay, optional detune/lowpass."""
    n = max(1, int(dur * AU_SR))
    out = [0.0] * n
    ph = ph2 = y = 0.0
    sin, exp = math.sin, math.exp
    for i in range(n):
        t = i / AU_SR
        f = freq if f1 is None else freq * (f1 / freq) ** ((i / n) ** curve)
        if vib:
            f *= 1 + vib * sin(AU_TAU * 6 * t)
        ph += f / AU_SR
        p = ph % 1.0
        if wv == "sine":
            v = sin(AU_TAU * ph)
        elif wv == "saw":
            v = 2 * p - 1
        elif wv == "square":
            v = 1.0 if p < duty else -1.0
        elif wv == "tri":
            v = 4 * abs(p - 0.5) - 1
        else:                                                            # "fm": a bright two-operator tone
            v = sin(AU_TAU * ph + 2.2 * sin(AU_TAU * ph * 2.0))
        if det:
            ph2 += f * (1 + det) / AU_SR
            v = (v + (2 * (ph2 % 1.0) - 1 if wv == "saw" else sin(AU_TAU * ph2))) * 0.5
        if lp:
            y += lp * (v - y)
            v = y
        out[i] = v * min(1.0, t / attack) * exp(-decay * t) * amp
    return out


def au_noise(dur, lp=1.0, hp=0.0, decay=0.0, attack=0.002, amp=1.0, seed=7, lp1=None) -> list:
    r = random.Random(seed)
    n = max(1, int(dur * AU_SR))
    out = [0.0] * n
    y = z = 0.0
    exp = math.exp
    for i in range(n):
        x = r.random() * 2 - 1
        a = lp if lp1 is None else lp + (lp1 - lp) * (i / n)
        y += a * (x - y)
        v = y
        if hp:
            z += hp * (v - z)
            v -= z
        t = i / AU_SR
        out[i] = v * min(1.0, t / attack) * exp(-decay * t) * amp
    return out


def au_mix(parts) -> list:
    """parts: (buffer, start_seconds, gain)."""
    out: list = []
    for buf, at, g in parts:
        o = int(at * AU_SR)
        if o + len(buf) > len(out):
            out.extend([0.0] * (o + len(buf) - len(out)))
        out[o:o + len(buf)] = [a + b * g for a, b in zip(out[o:o + len(buf)], buf)]
    return out


def au_peak(buf, level=0.8) -> list:
    m = max((abs(v) for v in buf), default=0.0) or 1.0
    k = level / m
    return [v * k for v in buf]


def au_drive(buf, k=3.0) -> list:
    tk = math.tanh(k)
    return [math.tanh(v * k) / tk for v in buf]


def au_lowpass(buf, a) -> list:
    y = 0.0
    out = [0.0] * len(buf)
    for i, v in enumerate(buf):
        y += a * (v - y)
        out[i] = y
    return out


def au_crush(buf, bits=5, hold=3) -> list:
    """Bit-crush + sample-and-hold: the gritty digital edge of the glitch/technical sounds."""
    q = 2 ** (bits - 1)
    out, last = [0.0] * len(buf), 0.0
    for i, v in enumerate(buf):
        if i % hold == 0:
            last = round(v * q) / q
        out[i] = last
    return out


def au_echo(buf, d_secs, taps=((1, .38), (2, .17)), lp=0.0) -> list:
    """Baked multi-tap echo (optionally darker on each repeat)."""
    d = int(d_secs * AU_SR)
    out = buf + [0.0] * (d * max(k for k, _ in taps))
    src = buf
    for k, g in taps:
        if lp:
            src = au_lowpass(src, lp)
        o = k * d
        out[o:o + len(src)] = [a + b * g for a, b in zip(out[o:o + len(src)], src)]
    return out


def au_space(buf, size=0.6, wet=0.35) -> list:
    """A small, cheap 'room': four decaying comb echoes at prime-ish spacings (baked into a note or effect)."""
    out = buf + [0.0] * int(size * AU_SR * 1.2)
    for ms, g in ((29.7, .5), (37.1, .44), (41.1, .4), (43.7, .36)):
        d = int(ms * size * 0.001 * AU_SR * 9)
        for k in range(1, 4):
            o = d * k
            gk = wet * g ** k
            seg = buf
            out[o:o + len(seg)] = [a + b * gk for a, b in zip(out[o:o + len(seg)], seg)]
    return out


def au_finish(buf) -> list:
    """Remove DC and de-click both ends so no effect can pop."""
    n = len(buf)
    if n == 0:
        return buf
    m = sum(buf) / n
    buf = [v - m for v in buf]
    f, a = min(n // 4, int(0.012 * AU_SR)), min(n // 4, int(0.0008 * AU_SR))
    for i in range(f):
        buf[n - 1 - i] *= i / max(1, f)
    for i in range(a):
        buf[i] *= i / max(1, a)
    return buf


def au_tail(buf, secs=0.006) -> list:
    n = min(len(buf) // 3, int(secs * AU_SR))
    for i in range(n):
        buf[len(buf) - 1 - i] *= i / max(1, n)
    return buf


def au_bell(freq, dur=0.6, amp=1.0, decay=6.0) -> list:
    return au_mix([(au_tone(freq, dur, "sine", amp, decay), 0, 1), (au_tone(freq * 2.76, dur, "sine", amp, decay * 1.7), 0, 0.33),
                   (au_tone(freq * 5.4, dur * 0.6, "sine", amp, decay * 2.6), 0, 0.14)])


# ---- wavetable instrument engine ---------------------------------------------------------------------------------------
_AU_TBL = 512
_au_tables: dict = {}


def au_table(key: tuple) -> list:
    """A single-cycle wavetable from harmonic weights (cached). key = tuple of amplitudes for harmonics 1..n."""
    t = _au_tables.get(key)
    if t is None:
        t = [0.0] * _AU_TBL
        sin = math.sin
        for k, w in enumerate(key):
            if w:
                for i in range(_AU_TBL):
                    t[i] += w * sin(AU_TAU * (k + 1) * i / _AU_TBL)
        m = max(abs(v) for v in t) or 1.0
        t = [v / m for v in t]
        _au_tables[key] = t
    return t


def _formant_weights(f: float, formants, n_max: int = 40) -> tuple:
    """Harmonic amplitudes of a voiced sound at pitch f shaped by vowel formants (centre Hz, width Hz, gain)."""
    out = []
    for k in range(1, n_max + 1):
        fk = f * k
        if fk > AU_SR * 0.45:
            break
        w = 0.08 / k
        for c, bw, g in formants:
            w += g * math.exp(-((fk - c) / bw) ** 2)
        out.append(round(w, 3))
    return tuple(out)


def au_wave(f, dur, vel, table, env=(0.01, 0.0, 1.0, 0.08), voices=(1.0,), vib=(0.0, 5.5, 0.15), table2=None, morph=0.0,
            div=1, trem=0.0, glide=0.0) -> list:
    """Wavetable voice. env=(attack, decay, sustain, release) seconds/level; voices = detune ratios (supersaw-style unison);
    vib=(depth, rate, delay); table2+morph crossfades bright->dark over `morph` seconds; div renders at SR/div (cheap pads)."""
    sr = AU_SR // div
    n = max(1, int(dur * sr))
    out = [0.0] * n
    a, d, s, r = env
    nv = len(voices)
    phs = [k * 0.137 for k in range(nv)]
    sin = math.sin
    T = _AU_TBL
    vd, vr, vdel = vib
    for i in range(n):
        t = i / sr
        if t < a:
            e = t / a
        elif t < a + d:
            e = 1.0 - (1.0 - s) * (t - a) / d
        else:
            e = s
        if t > dur - r:
            e *= max(0.0, (dur - t) / r)
        fm = f
        if glide and t < glide:
            fm = f * (0.5 + 0.5 * t / glide) if glide > 0 else f
        if vd and t > vdel:
            fm *= 1 + vd * sin(AU_TAU * vr * t) * min(1.0, (t - vdel) * 3)
        v = 0.0
        for k in range(nv):
            phs[k] += fm * voices[k] / sr
            idx = int((phs[k] % 1.0) * T)
            if table2 is not None:
                m = min(1.0, t / morph) if morph else 1.0
                v += table[idx] * (1 - m) + table2[idx] * m
            else:
                v += table[idx]
        v /= nv
        if trem:
            v *= 1 - trem * (0.5 + 0.5 * sin(AU_TAU * 5.2 * t))
        out[i] = v * e * vel
    if div > 1:
        up = [0.0] * (n * div)
        prev = 0.0
        for i, v in enumerate(out):
            dv = (v - prev) / div
            for j in range(div):
                up[i * div + j] = prev + dv * (j + 1)
            prev = v
        return up
    return out


def au_pluck(f, dur, vel, bright=0.5, damp=0.996, buzz=0.0, seed=3) -> list:
    """Karplus-Strong plucked string (harp, koto, guitar, sitar with `buzz`)."""
    n = max(1, int(dur * AU_SR))
    p = max(2, int(AU_SR / max(f, 20)))
    rng = random.Random(seed + int(f))
    line = [rng.random() * 2 - 1 for _ in range(p)]
    if bright < 1.0:
        line = au_lowpass(line, 0.2 + 0.8 * bright)
    out = [0.0] * n
    tanh = math.tanh
    for i in range(n):
        j = i % p
        v = line[j]
        nxt = line[(j + 1) % p]
        line[j] = damp * 0.5 * (v + nxt)
        if buzz:
            v = tanh(v * (1 + buzz * 4)) * 0.8 + v * 0.2
        out[i] = v * vel
    return au_tail(out, 0.02)


def au_inst_table():
    """Named instruments: (render(f, dur, vel) -> buffer, mix gain)."""
    saw = au_table(tuple(1.0 / k for k in range(1, 30)))
    dsaw = au_table(tuple(1.0 / k ** 1.6 for k in range(1, 16)))
    sq = au_table(tuple((1.0 / k if k % 2 else 0.0) for k in range(1, 26)))
    dsq = au_table(tuple((1.0 / k ** 1.5 if k % 2 else 0.0) for k in range(1, 12)))
    sine = au_table((1.0,))
    organ = au_table((1.0, 0.8, 0.0, 0.6, 0.0, 0.45, 0.0, 0.35, 0.0, 0.0, 0.0, 0.2, 0.0, 0.0, 0.0, 0.12))
    reed = au_table((0.6, 0.1, 1.0, 0.1, 0.7, 0.08, 0.5, 0.05, 0.35, 0.0, 0.2))
    flute = au_table((1.0, 0.25, 0.08, 0.04))
    brass_b = au_table(tuple(1.0 / k ** 0.9 for k in range(1, 22)))
    brass_d = au_table(tuple(1.0 / k ** 2.2 for k in range(1, 10)))
    glass = au_table((1.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.25))
    hollow = au_table((1.0, 0.0, 0.33, 0.0, 0.2, 0.0, 0.14))
    vox_a = ((700, 130, 1.0), (1220, 140, 0.55), (2600, 220, 0.25))
    vox_o = ((450, 110, 1.0), (800, 120, 0.6), (2830, 240, 0.12))
    I = {}

    def W(name, gain, **kw):
        I[name] = (lambda f, d, v, kw=kw: au_wave(f, d, v, **kw), gain)
    # --- synths
    W("supersaw", .42, table=saw, env=(0.01, 0.3, 0.7, 0.08), voices=(0.988, 0.994, 1.0, 1.006, 1.012))
    W("saw", .5, table=saw, env=(0.005, 0.2, 0.6, 0.05), voices=(1.0, 1.004))
    W("square", .45, table=sq, env=(0.004, 0.15, 0.7, 0.04))
    W("hollow", .5, table=hollow, env=(0.01, 0.2, 0.8, 0.06), vib=(0.004, 5.5, 0.2))
    W("pad", .38, table=dsaw, env=(0.45, 0.0, 1.0, 0.6), voices=(0.996, 1.0, 1.004), div=4)
    W("warmpad", .4, table=dsq, env=(0.6, 0.0, 1.0, 0.8), voices=(0.997, 1.003), div=4, vib=(0.003, 4.0, 0.5))
    W("glasspad", .34, table=glass, env=(0.3, 0.0, 1.0, 0.7), voices=(0.995, 1.0, 1.005), div=2, trem=0.2)
    W("strings", .36, table=dsaw, env=(0.18, 0.0, 1.0, 0.25), voices=(0.994, 1.0, 1.006), vib=(0.004, 5.2, 0.15), div=2)
    W("stacc", .5, table=dsaw, env=(0.004, 0.09, 0.15, 0.05), voices=(0.996, 1.004))
    W("pizz", .55, table=hollow, env=(0.002, 0.12, 0.0, 0.03))
    W("brass", .45, table=brass_b, table2=brass_d, morph=0.5, env=(0.03, 0.2, 0.75, 0.07), voices=(0.997, 1.003), vib=(0.004, 5.0, 0.3))
    W("horn", .45, table=brass_d, env=(0.06, 0.2, 0.8, 0.12), voices=(1.0,), vib=(0.003, 4.8, 0.35))
    W("organ", .36, table=organ, env=(0.012, 0.0, 1.0, 0.05), voices=(1.0, 2.0 * 1.001), trem=0.15)
    W("reed", .45, table=reed, env=(0.03, 0.1, 0.85, 0.06), vib=(0.006, 5.8, 0.18))
    W("flute", .5, table=flute, env=(0.06, 0.1, 0.85, 0.07), vib=(0.006, 5.0, 0.2))
    W("erhu", .45, table=dsaw, env=(0.08, 0.1, 0.9, 0.1), vib=(0.014, 6.0, 0.12))
    W("theremin", .5, table=sine, env=(0.12, 0.0, 1.0, 0.2), vib=(0.012, 5.5, 0.05))
    W("sub", .8, table=sine, env=(0.006, 0.0, 1.0, 0.04))
    W("chip", .32, table=sq, env=(0.001, 0.15, 0.55, 0.02))
    W("chiptri", .5, table=au_table((1.0, 0.0, 0.11, 0.0, 0.04)), env=(0.001, 0.0, 1.0, 0.02))
    W("music_box", .5, table=au_table((1.0, 0.0, 0.0, 0.3, 0.0, 0.0, 0.0, 0.12)), env=(0.001, 0.6, 0.0, 0.05))
    I["choir"] = (lambda f, d, v: au_wave(f, d, v, au_table(_formant_weights(f, vox_a)), env=(0.35, 0.0, 1.0, 0.5),
                                          voices=(0.994, 1.0, 1.006), vib=(0.005, 5.0, 0.3), div=2), .42)
    I["choir_o"] = (lambda f, d, v: au_wave(f, d, v, au_table(_formant_weights(f, vox_o)), env=(0.4, 0.0, 1.0, 0.6),
                                            voices=(0.995, 1.005), vib=(0.004, 4.6, 0.3), div=2), .44)
    # --- plucked / struck
    I["harp"] = (lambda f, d, v: au_pluck(f, d, v, 0.55, 0.997), .7)
    I["koto"] = (lambda f, d, v: au_pluck(f, d, v, 0.9, 0.993), .65)
    I["guitar"] = (lambda f, d, v: au_pluck(f, d, v, 0.75, 0.995), .65)
    I["sitar"] = (lambda f, d, v: au_pluck(f, d, v, 0.95, 0.996, buzz=0.6), .55)
    I["harpsi"] = (lambda f, d, v: au_mix([(au_pluck(f, d, v, 1.0, 0.990), 0, 1), (au_pluck(f * 2, d, v, 1.0, 0.985), 0, .35)]), .55)
    I["piano"] = (lambda f, d, v: [s * v for s in au_mix([(au_tone(f, d, "sine", 1, 2.2), 0, 1), (au_tone(f * 2, d, "sine", 1, 3.5), 0, .35),
                                                          (au_tone(f * 3, d, "sine", 1, 5), 0, .15), (au_tone(f, d * .25, "fm", 1, 14), 0, .2)])], .6)
    I["ep"] = (lambda f, d, v: [math.sin(AU_TAU * f * (i / AU_SR) + 1.1 * math.exp(-4 * i / AU_SR) * math.sin(AU_TAU * f * (i / AU_SR)))
                                * math.exp(-2.4 * i / AU_SR) * min(1.0, (i / AU_SR) / 0.002) * v for i in range(int(d * AU_SR))], .6)
    I["bell"] = (lambda f, d, v: [math.sin(AU_TAU * f * (i / AU_SR) + 1.7 * math.exp(-5 * i / AU_SR) * math.sin(AU_TAU * f * 2.0 * (i / AU_SR)))
                                  * math.exp(-3.0 * i / AU_SR) * min(1.0, (i / AU_SR) / 0.002) * v for i in range(int(d * AU_SR))], .55)
    I["celesta"] = (lambda f, d, v: [s * v for s in au_bell(f, d, 1, 5)], .55)
    I["marimba"] = (lambda f, d, v: [s * v for s in au_mix([(au_tone(f, d, "sine", 1, 9), 0, 1), (au_tone(f * 4, d, "sine", 1, 30), 0, .3)])], .7)
    I["vibes"] = (lambda f, d, v: [s * v * (1 - 0.3 * (0.5 + 0.5 * math.sin(AU_TAU * 5 * i / AU_SR)))
                                   for i, s in enumerate(au_mix([(au_tone(f, d, "sine", 1, 2.0), 0, 1), (au_tone(f * 4, d, "sine", 1, 6), 0, .18)]))], .6)
    I["glock"] = (lambda f, d, v: [s * v for s in au_bell(f * 2, d, 1, 7)], .4)
    # --- basses
    I["bass"] = (lambda f, d, v: _i_bass(f, d, v), .75)
    I["fingerbass"] = (lambda f, d, v: au_pluck(f, d, v, 0.35, 0.998), .9)
    I["reese"] = (lambda f, d, v: au_lowpass(au_wave(f, d, v, saw, env=(0.01, 0.0, 1.0, 0.05), voices=(0.993, 1.007, 0.5)), 0.12), .9)
    I["acid"] = (lambda f, d, v: _i_acid(f, d, v), .65)
    I["808"] = (lambda f, d, v: _i_808(f, d, v), .9)
    I["wob"] = (lambda f, d, v: _i_wob(f, d, v), .7)
    I["chipbass"] = (lambda f, d, v: au_wave(f, d, v, sq, env=(0.001, 0.0, 1.0, 0.02)), .4)
    I["power"] = (lambda f, d, v: _i_power(f, d, v), .5)
    I["chug"] = (lambda f, d, v: _i_power(f, min(d, 0.14), v, mute=True), .55)
    I["hoover"] = (lambda f, d, v: au_wave(f, d, v, saw, env=(0.01, 0.2, 0.8, 0.06), voices=(0.98, 0.99, 1.0, 1.01, 1.02, 0.5), glide=0.06), .4)
    I["drone"] = (lambda f, d, v: au_wave(f, d, v, reed, env=(0.8, 0.0, 1.0, 0.8), voices=(0.999, 1.001, 0.5), div=4), .4)
    return I


def _i_bass(f, dur, vel=1.0):
    n = int(dur * AU_SR)
    out = [0.0] * n
    ph = y = 0.0
    sin, exp = math.sin, math.exp
    for i in range(n):
        t = i / AU_SR
        ph += f / AU_SR
        v = (2 * (ph % 1.0) - 1) * 0.65 + sin(AU_TAU * ph) * 0.55
        y += (0.05 + 0.42 * exp(-t * 8)) * (v - y)
        out[i] = y * min(1.0, t / 0.004) * vel
    return out


def _i_acid(f, dur, vel=1.0):
    n = int(dur * AU_SR)
    out = [0.0] * n
    ph = y1 = y2 = 0.0
    exp, tanh = math.exp, math.tanh
    for i in range(n):
        t = i / AU_SR
        ph += f / AU_SR
        v = 2 * (ph % 1.0) - 1
        c = 0.06 + 0.34 * exp(-t * 14)
        y1 += c * (v - y1 + 0.8 * (y1 - y2))
        y2 += c * (y1 - y2)
        out[i] = tanh(y2 * 1.8) * min(1.0, t / 0.003) * (1.0 if t < dur - 0.02 else max(0.0, (dur - t) / 0.02)) * vel
    return out


def _i_808(f, dur, vel=1.0):
    n = int(max(dur, 0.25) * AU_SR)
    sin, exp = math.sin, math.exp
    out = [0.0] * n
    ph = 0.0
    for i in range(n):
        t = i / AU_SR
        ph += f * (1 + 1.4 * exp(-t * 40)) / AU_SR
        out[i] = math.tanh(sin(AU_TAU * ph) * 1.6) * exp(-t * 1.4) * min(1.0, t / 0.002) * vel
    return out


def _i_wob(f, dur, vel=1.0, rate=2.0):
    n = int(dur * AU_SR)
    out = [0.0] * n
    ph = y = 0.0
    sin = math.sin
    for i in range(n):
        t = i / AU_SR
        ph += f / AU_SR
        v = (2 * (ph % 1.0) - 1) * 0.7 + sin(AU_TAU * ph * 0.5) * 0.5
        y += (0.04 + 0.30 * (0.5 + 0.5 * sin(AU_TAU * rate * t))) * (v - y)
        out[i] = y * min(1.0, t / 0.004) * vel
    return out


def _i_power(f, dur, vel=1.0, mute=False):
    """A distorted power chord (root + fifth + octave), the 'guitar' of the metal and industrial themes."""
    n = int(dur * AU_SR)
    out = [0.0] * n
    p1 = p2 = p3 = y = 0.0
    tanh, exp = math.tanh, math.exp
    for i in range(n):
        t = i / AU_SR
        p1 += f / AU_SR
        p2 += f * 1.4983 / AU_SR
        p3 += f * 2.003 / AU_SR
        v = (p1 % 1.0) + (p2 % 1.0) * 0.8 + (p3 % 1.0) * 0.5 - 1.15
        v = tanh(v * 4.0)
        y += (0.18 if mute else 0.35) * (v - y)
        env = exp(-t * (18 if mute else 1.2)) * min(1.0, t / 0.003)
        out[i] = y * env * vel
    return au_tail(out, 0.01)


# ---- drum kits ------------------------------------------------------------------------------------------------------------
def au_drum(name: str) -> list:
    """Every drum sound in the game. Names are 'kind' or 'kind.variant'."""
    T, N, M = au_tone, au_noise, au_mix
    if name == "kick":
        return M([(T(150, .42, "sine", 1, 10, .001, f1=45), 0, 1.2), (N(.012, 1, .3, 100), 0, .45)])
    if name == "kick.808":
        return M([(T(140, .9, "sine", 1, 3.0, .001, f1=34), 0, 1.3), (N(.01, 1, .3, 120), 0, .3)])
    if name == "kick.hard":
        return au_drive(M([(T(190, .32, "sine", 1, 9, .001, f1=48), 0, 1.3), (N(.02, 1, .2, 90), 0, .6)]), 2.5)
    if name == "kick.soft":
        return M([(T(110, .35, "sine", 1, 12, .004, f1=50), 0, 1.0)])
    if name == "snare":
        return M([(N(.24, 1, .12, 19), 0, .9), (T(210, .14, "sine", 1, 26, f1=150), 0, .8)])
    if name == "snare.tight":
        return M([(N(.16, 1, .2, 28), 0, 1.0), (T(260, .1, "sine", 1, 30, f1=180), 0, .7)])
    if name == "snare.orch":
        return M([(N(.32, .9, .15, 12), 0, 1.0), (T(190, .2, "sine", 1, 18, f1=170), 0, .5)])
    if name == "snare.lofi":
        return au_lowpass(M([(N(.2, 1, .1, 22), 0, .8), (T(180, .12, "sine", 1, 24, f1=140), 0, .8)]), 0.4)
    if name == "rim":
        return M([(T(1700, .03, "square", 1, 120, lp=.6), 0, .8), (N(.02, 1, .4, 150), 0, .4)])
    if name == "clap":
        return M([(N(.05, .9, .1, 60, seed=s), t, 1) for s, t in ((1, 0), (2, .011), (3, .023))] + [(N(.18, .8, .1, 22, seed=9), .03, .8)])
    if name == "hat":
        return N(.05, 1, .45, 80, .001, .6)
    if name == "hat.tight":
        return N(.025, 1, .55, 150, .001, .55)
    if name == "ohat":
        return N(.22, 1, .45, 14, .001, .6)
    if name == "ride":
        return M([(N(.6, 1, .5, 5, .001, .35), 0, 1), (T(3400, .6, "sine", 1, 6), 0, .08), (T(5100, .5, "sine", 1, 8), 0, .05)])
    if name == "crash":
        return M([(N(1.6, 1, .35, 2.2, .001, .7, seed=11), 0, 1), (N(.4, .6, .2, 6, seed=12), 0, .4)])
    if name == "shaker":
        return N(.07, 1, .6, 50, .02, .45, seed=5)
    if name == "tom":
        return M([(T(140, .35, "sine", 1, 9, .001, f1=95), 0, 1.0), (N(.03, .6, .1, 60), 0, .3)])
    if name == "tom.hi":
        return M([(T(220, .28, "sine", 1, 11, .001, f1=150), 0, 1.0), (N(.03, .6, .1, 60), 0, .3)])
    if name == "taiko":
        return M([(T(82, .9, "sine", 1, 4.2, .002, f1=55), 0, 1.4), (N(.08, .25, .05, 25), 0, .9), (T(160, .1, "sine", 1, 30), 0, .4)])
    if name == "taiko.rim":
        return M([(T(900, .05, "square", 1, 80, lp=.4), 0, .7), (N(.04, .8, .2, 90), 0, .5)])
    if name == "timpani":
        return M([(T(98, 1.6, "sine", 1, 2.0, .004, f1=92), 0, 1.2), (T(196, 1.0, "sine", 1, 3.5), 0, .35), (N(.06, .3, .05, 30), 0, .5)])
    if name == "doum":
        return M([(T(120, .5, "sine", 1, 7, .001, f1=80), 0, 1.2), (N(.02, .5, .1, 80), 0, .3)])
    if name == "tek":
        return M([(T(820, .07, "sine", 1, 55), 0, .7), (N(.04, 1, .4, 90), 0, .6)])
    if name == "clave":
        return T(2500, .06, "sine", 1, 60)
    if name == "block":
        return M([(T(1200, .07, "sine", 1, 55), 0, 1.0), (T(2650, .05, "sine", 1, 70), 0, .3)])
    if name == "cowbell":
        return au_lowpass(M([(T(540, .25, "square", 1, 14), 0, .6), (T(800, .25, "square", 1, 14), 0, .6)]), .5)
    if name == "anvil":
        return M([(T(f, .8, "sine", 1, 5), 0, g) for f, g in ((1350, .8), (2370, .5), (3610, .35), (4980, .2))] + [(N(.03, 1, .3, 90), 0, .8)])
    if name == "gong":
        return M([(T(f, 3.0, "sine", 1, 1.0, .02, vib=.003), 0, g) for f, g in ((110, 1.0), (163, .6), (247, .5), (391, .3), (523, .2))]
                 + [(N(1.0, .2, .02, 2, .05), 0, .3)])
    if name == "glitch":
        return au_crush(M([(T(3100, .05, "square", 1, 50), 0, .7), (N(.04, 1, .3, 60, seed=21), .01, .7)]), 3, 4)
    if name == "glitch.blip":
        return M([(T(f, .03, "sine", 1, 90), k * .018, 1) for k, f in enumerate((1800, 2700, 1200))])
    if name == "glitch.zap":
        return au_crush(T(2400, .12, "saw", 1, 20, f1=200, lp=.6), 4, 3)
    if name == "riser":
        return au_noise(1.8, .02, .02, 0.0, 1.6, .7, seed=33, lp1=.8)
    if name == "boom":
        return M([(T(70, 2.0, "sine", 1, 2.2, .002, f1=30), 0, 1.5), (N(1.4, .08, .0, 2.5, .005), 0, .8)])
    if name == "chip.k":
        return au_crush(T(220, .12, "square", 1, 20, f1=60), 4, 2)
    if name == "chip.s":
        return au_crush(N(.1, 1, .3, 28, seed=4), 4, 3)
    if name == "chip.h":
        return au_crush(N(.03, 1, .5, 110, seed=6), 3, 3)
    if name == "bodhran":
        return M([(T(95, .35, "sine", 1, 10, .001, f1=70), 0, 1.0), (N(.05, .4, .1, 50), 0, .4)])
    if name == "tabla":
        return M([(T(330, .4, "sine", 1, 9, .001, f1=360), 0, .9), (N(.02, 1, .4, 90), 0, .3)])
    return au_noise(.05, 1, .4, 80)


DRUM_GAIN = {"kick": 1.0, "snare": .8, "hat": .45, "ohat": .45, "clap": .6, "ride": .35, "crash": .45, "shaker": .4, "rim": .6, "tom": .8,
             "taiko": .95, "timpani": .8, "doum": .9, "tek": .6, "clave": .5, "block": .6, "cowbell": .4, "anvil": .45, "gong": .6,
             "glitch": .5, "riser": .45, "boom": .9, "chip": .55, "bodhran": .85, "tabla": .7}


def drum_gain(name: str) -> float:
    return DRUM_GAIN.get(name.split(".")[0], 0.6)
