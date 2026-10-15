'use strict';
/* A port of the game's tank renderer (draw_tank and the helpers it uses in terminaltanks.py) so the website can draw any
   tank, official or custom, with the same pixels. tools/check_tank_port.py compares it against the Python original. */
const TankGfx = (() => {
  const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
  const pyRound = (x) => { const f = Math.floor(x), d = x - f; return d < 0.5 ? f : d > 0.5 ? f + 1 : f % 2 === 0 ? f : f + 1; };
  const frac = (x) => x - Math.floor(x);
  const mix = (a, b, t) => (t <= 0 ? a : t >= 1 ? b : [Math.trunc(a[0] + (b[0] - a[0]) * t), Math.trunc(a[1] + (b[1] - a[1]) * t), Math.trunc(a[2] + (b[2] - a[2]) * t)]);
  const shade = (c, k) => [Math.min(255, Math.trunc(c[0] * k)), Math.min(255, Math.trunc(c[1] * k)), Math.min(255, Math.trunc(c[2] * k))];
  const gradient = (stops, t) => {
    if (t <= stops[0][0]) return stops[0][1];
    for (let i = 0; i < stops.length - 1; i++) { const [t0, c0] = stops[i], [t1, c1] = stops[i + 1]; if (t <= t1) return mix(c0, c1, t1 > t0 ? (t - t0) / (t1 - t0) : 1.0); }
    return stops[stops.length - 1][1];
  };
  const hsv = (h, s = 1.0, v = 1.0) => {
    h = frac(h);
    if (s === 0) { const g = Math.trunc(v * 255); return [g, g, g]; }
    let i = Math.trunc(h * 6.0); const f = h * 6.0 - i, p = v * (1 - s), q = v * (1 - s * f), t = v * (1 - s * (1 - f));
    i %= 6;
    const [r, g, b] = [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i];
    return [Math.trunc(r * 255), Math.trunc(g * 255), Math.trunc(b * 255)];
  };
  const RAINBOW = 'rainbow';
  const rainbow = (t) => hsv(pyRound(frac(t * 0.35) * 36) / 36, 0.85, 1.0);
  const flick = (t, a, b) => ((((Math.trunc(t * 30) * 73856093) ^ (a * 19349663) ^ (b * 83492791)) & 255) / 255.0);

  class Px {
    constructor(w, h, fill = [0, 0, 0]) { this.w = w; this.h = h; this.rows = Array.from({ length: h }, () => Array(w).fill(fill)); }
    plot(x, y, c) { const py = this.h - 1 - y; if (x >= 0 && x < this.w && py >= 0 && py < this.h) this.rows[py][x] = c; }
    blend(x, y, c, a) { const py = this.h - 1 - y; if (x >= 0 && x < this.w && py >= 0 && py < this.h && a > 0.02) this.rows[py][x] = mix(this.rows[py][x], c, a); }
    plotf(x, y, c) { this.plot(Math.floor(x), Math.floor(y), c); }
    blendf(x, y, c, a) { this.blend(Math.floor(x), Math.floor(y), c, a); }
  }

  const MAT = {
    p: (body, a, t, c, r) => hsv(t * 0.35 + c * 0.085 + r * 0.14, 0.62, 1.0),
    q: (body, a, t, c, r) => { const k = Math.max(0.0, 1 - Math.abs((c + r) - (((t * 7) % 18) - 3)) / 2.2); return mix(hsv(t * 0.35 + c * 0.085 + r * 0.14, 0.25, 1.0), [255, 255, 255], k); },
    f: (body, a, t, c, r) => { const k = clamp(0.55 + 0.45 * Math.sin(t * 21 + c * 2.3 + r * 1.7) * Math.sin(t * 9 + c), 0, 1); return gradient([[0, [150, 20, 8]], [0.5, [255, 110, 20]], [1, [255, 236, 120]]], k); },
    e: (body, a, t, c, r) => gradient([[0, shade(body, 0.4)], [1, [255, 90, 30]]], 0.5 + 0.5 * Math.sin(t * 3 + c * 0.9 + r)),
    v: (body, a, t, c, r) => mix([8, 4, 20], [110, 50, 200], 0.5 + 0.5 * Math.sin(t * 4 + c * 0.8 - r)),
    b: (body, a, t, c, r) => (flick(t, c * 7 + r, 11) > 0.84 ? [240, 248, 255] : mix(shade(body, 0.35), a, 0.45)),
    y: (body, a, t, c, r) => { const k = Math.max(0.0, 1 - Math.abs((c * 1.3 + r) - (((t * 6) % 20) - 4)) / 2.5); return mix([196, 150, 50], [255, 244, 180], k); },
  };
  const pmod = (a, b) => ((a % b) + b) % b;                       // Python's % (the result takes the sign of the divisor)
  const S = Math.sin, AB = Math.abs, MX = Math.max;
  const W = [255, 255, 255];
  /* materials added with the Ancient, premium II and vault tanks (terminaltanks.py: _mat_solar ... _mat_ghostfire) */
  Object.assign(MAT, {
    o: (body, a, t, c, r) => gradient([[0, [255, 130, 30]], [0.5, [255, 222, 96]], [1, [255, 255, 236]]], 0.5 + 0.5 * S(t * 5 - r * 1.6 + c * 0.45)),
    r: (body, a, t, c, r) => (flick(t * 0.7, c * 3 + r, 13) > 0.78 ? [255, 244, 190] : mix([140, 100, 28], [226, 176, 70], 0.5 + 0.5 * S(t * 2.4 + c * 0.9 - r))),
    s: (body, a, t, c, r) => mix([196, 212, 255], W, 0.5 + 0.5 * S(t * 9 + c * 2.1 + r)),
    n: (body, a, t, c, r) => (flick(t * 0.8, c * 5 + r, 17) > 0.93 ? [226, 206, 255] : mix([10, 6, 26], [74, 32, 146], 0.5 + 0.5 * S(t * 2 + c * 0.7 + r))),
    m: (body, a, t, c, r) => mix([20, 110, 150], [150, 255, 240], 0.5 + 0.5 * S(t * 3.5 - c * 0.9 + r * 0.6)),
    z: (body, a, t, c, r) => { const k = MX(0.0, 1 - AB((c + r * 2) - (pmod(t * 8, 24) - 6)) / 2.2); return mix(mix([120, 70, 30], [232, 172, 72], 0.5 + 0.5 * S(t * 1.5 + c)), [255, 250, 222], k); },
    J: (body, a, t, c, r) => mix([8, 20, 46], [34, 78, 126], 0.5 + 0.5 * S(t * 1.3 + c * 0.7 + r * 1.1) * S(t * 0.7 - c * 0.4)),
    U: (body, a, t, c, r) => (flick(t * 0.5, c * 3 + r, 29) > 0.96 ? [240, 255, 255] : mix([18, 80, 130], [140, 255, 236], 0.5 + 0.5 * S(t * 4 - c * 0.9 + r))),
    F: (body, a, t, c, r) => gradient([[0, [40, 60, 200]], [0.5, [90, 180, 255]], [1, [236, 250, 255]]], clamp(0.55 + 0.45 * S(t * 19 + c * 2.1 + r * 1.3) * S(t * 7 + c), 0, 1)),
    X: (body, a, t, c, r) => mix([232, 228, 244], [255, 214, 140], 0.7 * MX(0.0, 1 - AB((c + r * 1.5) - (pmod(t * 5, 20) - 4)) / 2.5)),
    H: (body, a, t, c, r) => (flick(t * 0.6, c, r + 40) > 0.95 ? [255, 60, 200] : pmod(Math.trunc(t * 14) + r, 6) === 0 ? [210, 255, 255] : mix([18, 50, 100], [90, 230, 255], 0.55 + 0.3 * S(t * 6 + r * 2 + c * 0.3))),
    K: (body, a, t, c, r) => mix([150, 162, 184], W, MX(0.0, 1 - AB((c - r) - (pmod(t * 9, 22) - 5)) / 1.8)),
    Q: (body, a, t, c, r) => mix(hsv(0.74 + 0.08 * S(t * 2 + c * 0.5), 0.45, 1.0), W, MX(0.0, 1 - AB((c + r) - (pmod(t * 7, 20) - 4)) / 2.0)),
    Z: (body, a, t, c, r) => (flick(t * 0.4, c * 3 + r, 23) > 0.9 ? [240, 236, 255] : mix([6, 4, 20], [52, 22, 112], 0.5 + 0.5 * S(t * 1.7 + c * 0.6 - r))),
    R: (body, a, t, c, r) => mix([26, 40, 34], [78, 108, 90], 0.25 + 0.3 * pmod(c + pmod(r, 2), 2) + 0.15 * S(t * 1.2 + c)),
    N: (body, a, t, c, r) => mix([40, 90, 170], [220, 244, 255], 0.35 + 0.65 * MX(0.0, 1 - AB(c - (pmod(t * 6, 16) - 3)) / 2.5)),
    M: (body, a, t, c, r) => (pmod(c * 3 + r * 5, 7) === 0 ? mix([255, 240, 200], [170, 255, 220], 0.5 + 0.5 * S(t * 2.5 + c)) : mix([140, 26, 56], [206, 64, 116], 0.5 + 0.5 * S(t * 1.5 + c * 0.6))),
    S: (body, a, t, c, r) => mix([50, 170, 130], [210, 255, 226], 0.5 + 0.5 * S(t * 3.3 + c * 1.7 + r)),
    W: (body, a, t, c, r) => mix([112, 74, 38], [218, 174, 104], 0.5 + 0.5 * S(c * 1.6 - t * 3 + r * 0.4)),
    O: (body, a, t, c, r) => gradient([[0, [90, 20, 10]], [0.6, [240, 110, 40]], [1, [255, 222, 150]]], 0.5 + 0.5 * S(t * 8 + c * 1.3)),
    E: (body, a, t, c, r) => (AB(S(c * 1.3 + r * 2.1 + t * 0.6)) < 0.14 ? [250, 214, 120] : mix([18, 104, 76], [96, 214, 156], 0.5 + 0.5 * S(t * 1.1 + c * 0.5 + r))),
    P: (body, a, t, c, r) => (pmod(c + r, 5) === 0 ? mix([220, 50, 50], [255, 150, 90], 0.5 + 0.5 * S(t * 3 + c)) : hsv(0.40 + 0.10 * S(t * 1.8 + c * 0.5 + r * 0.8), 0.75, 0.95)),
    C: (body, a, t, c, r) => (pmod(c * 7 + r * 3, 9) === 0 ? mix([140, 150, 220], [255, 250, 220], 0.5 + 0.5 * S(t * 6 + c * 2)) : pmod(c, 4) === 0 ? [36, 52, 120] : mix([12, 18, 56], [24, 34, 90], 0.5 + 0.5 * S(t + c * 0.4))),
    G: (body, a, t, c, r) => mix([176, 136, 56], [255, 240, 180], 0.5 + 0.5 * S(t * 5 + c * 1.1)),
    B: (body, a, t, c, r) => mix(mix([24, 44, 46], [50, 86, 82], 0.5 + 0.5 * S(c * 2.2 + r)), [120, 255, 170], 0.45 * MX(0.0, 1 - AB(c - (pmod(t * 4 + r * 3, 18) - 3)) / 3.0)),
    L: (body, a, t, c, r) => gradient([[0, [20, 90, 50]], [0.5, [90, 255, 150]], [1, [224, 255, 234]]], clamp(0.5 + 0.5 * S(t * 17 + c * 2.3 + r) * S(t * 6 + c * 0.7), 0, 1)),
  });

  /* ---- animated paints (terminaltanks.py: ANIM_PAINTS, live_color, PAINT_PX, paint_shade) ------------------------------- */
  const GALAXY = [[0, [24, 14, 96]], [0.2, [96, 44, 190]], [0.4, [196, 64, 196]], [0.6, [56, 160, 220]], [0.8, [232, 232, 255]], [1.0, [24, 14, 96]]];
  const AURORA = [[0, [40, 240, 150]], [0.35, [60, 200, 255]], [0.7, [170, 90, 255]], [1.0, [40, 240, 150]]];
  const q16 = (x) => pyRound(x * 16) / 16;
  const TINT = {
    ASTRAL: (t) => gradient(GALAXY, pyRound(pmod(t * 0.18, 1.0) * 48) / 48),
    PRISMATIC: (t) => hsv(pyRound(pmod(t * 0.3, 1.0) * 36) / 36, 0.35, 1.0),
    VOID: (t) => mix([90, 54, 190], [176, 120, 255], 0.5 + 0.5 * S(t * 2.4)),
    MOLTEN: (t) => mix([255, 84, 20], [255, 196, 70], q16(0.5 + 0.5 * S(t * 2.2))),
    CHROME: (t) => mix([150, 160, 182], [250, 252, 255], q16(0.5 + 0.5 * S(t * 1.6))),
    AURORA: (t) => gradient(AURORA, pyRound(pmod(t * 0.12, 1.0) * 36) / 36),
    CIRCUIT: (t) => mix([30, 170, 100], [170, 255, 210], q16(0.5 + 0.5 * S(t * 3.0))),
    OCEAN: (t) => mix([20, 110, 190], [120, 230, 255], q16(0.5 + 0.5 * S(t * 1.8))),
    SYNTHWAVE: (t) => mix([255, 60, 200], [60, 230, 255], q16(0.5 + 0.5 * S(t * 2.0))),
    TOXIC: (t) => mix([90, 220, 40], [200, 255, 90], q16(0.5 + 0.5 * S(t * 2.8))),
    GILDED: (t) => mix([200, 150, 50], [255, 236, 150], q16(0.5 + 0.5 * S(t * 1.7))),
  };
  const PX = {
    ASTRAL: (t, c, r) => { const v = (S(c * 0.55 + t * 1.1) + S(r * 0.9 - t * 0.8) + S((c + r) * 0.45 + t * 0.6) + 3) / 6; const col = gradient(GALAXY, pyRound(v * 24) / 24); return flick(t * 1.4, c * 7 + r * 3, 23) > 0.93 ? W : col; },
    PRISMATIC: (t, c, r) => { if (flick(t * 1.6, c * 5 + r * 11, 29) > 0.94) return W; const hue = pmod(c * 0.05 + r * 0.035 + t * 0.3 + 0.12 * S(c * 0.9 - r * 0.6 + t * 1.7), 1); return hsv(pyRound(hue * 48) / 48, 0.40 + 0.2 * S(r * 0.5 + t), 1.0); },
    VOID: (t, c, r) => (flick(t * 1.2, c * 3 + r * 7, 31) > 0.95 ? [176, 126, 255] : mix([6, 3, 18], [54, 30, 118], (S(c * 0.7 + t * 1.3) + S(r * 1.1 - t * 0.9) + 2) / 4)),
    MOLTEN: (t, c, r) => {
      const crack = AB(S(c * 0.85 + 1.8 * S(r * 0.7 + t * 0.35) + r * 0.45));
      if (crack < 0.2) { const heat = 0.5 + 0.5 * S(t * 2.6 + c * 0.4 - r * 0.3); return mix([255, 96, 18], [255, 226, 120], pyRound(heat * (1 - crack * 5) * 8) / 8); }
      if (crack < 0.32) return [150, 40, 14];
      return mix([34, 12, 10], [70, 24, 16], pyRound(((S(c * 0.3 + r * 0.8) + 1) / 2) * 4) / 4);
    },
    CHROME: (t, c, r) => {
      const base = mix([52, 58, 74], [214, 222, 236], pyRound(clamp(r / 7.0, 0, 1) * 6) / 6), band = pmod(c + r * 0.7 - t * 9.0, 26);
      if (band < 1.2) return W; if (band < 2.6) return mix(base, W, 0.55);
      if (pmod(Math.trunc(c) + Math.trunc(r), 9) === 0 && flick(t, c * 5 + r, 37) > 0.9) return W;
      return base;
    },
    AURORA: (t, c, r) => {
      const wave = S(c * 0.32 + t * 0.9 + 1.6 * S(r * 0.55 + t * 0.45)), glow = clamp((wave + 0.7) * 0.7, 0.3, 1);
      if (flick(t * 0.8, c * 9 + r * 5, 41) > 0.96) return [230, 240, 255];
      return mix([6, 12, 34], gradient(AURORA, pmod(c * 0.045 + r * 0.09 + t * 0.06, 1.0)), pyRound(glow * 8) / 8);
    },
    CIRCUIT: (t, c, r) => {
      const ic = Math.trunc(c), ir = Math.trunc(r), trace = pmod(ir, 3) === 1 || (pmod(ic, 5) === 2 && pmod(ir, 3) !== 0);
      if (!trace) return pmod(ic + ir, 2) ? [10, 34, 26] : [14, 40, 30];
      if (pmod(ic, 5) === 2 && pmod(ir, 3) === 1) return [200, 170, 90];
      const pulse = pmod(c * 1.0 + r * 2.0 - t * 14.0, 17);
      return pulse < 1.6 ? [170, 255, 210] : pulse < 3.2 ? [70, 210, 140] : [40, 110, 76];
    },
    OCEAN: (t, c, r) => {
      const depth = clamp(1 - r / 8.0, 0, 1), base = mix([6, 40, 92], [20, 110, 170], pyRound((1 - depth) * 5) / 5);
      const a = S(c * 0.62 + t * 1.7 + S(r * 0.9 - t * 1.1) * 1.4), b = S(c * 0.41 - r * 0.73 - t * 1.3), caustic = 1 - AB(a + b) * 0.8;
      if (caustic > 0.72) return mix(base, [170, 245, 255], pyRound(Math.min(1.0, (caustic - 0.72) * 3.6) * 6) / 6);
      if (flick(t * 1.1, c * 13 + r * 7, 43) > 0.97) return [200, 240, 255];
      return base;
    },
    SYNTHWAVE: (t, c, r) => {
      const ir = Math.trunc(r);
      if (ir <= 2) { if (ir === 2 && pmod(Math.trunc(c + t * 4), 7) < 2) return [255, 214, 120]; return gradient([[0, [80, 24, 140]], [0.5, [190, 50, 200]], [1, [255, 90, 150]]], pyRound(ir / 2 * 6) / 6); }
      if (ir === 3) return [70, 230, 255];
      if (pmod(Math.trunc(c) - 2, 5) === 0 || (pmod(Math.trunc(r - t * 2.5), 2) === 0 && pmod(Math.trunc(c), 2) === 0)) return [230, 50, 190];
      return [14, 4, 26];
    },
    TOXIC: (t, c, r) => {
      const ic = Math.trunc(c), seed = (ic * 2654435761) & 0xFFFF;
      const drip = 1.5 + (seed % 5) * 0.7 + 1.2 * S(t * (0.6 + (seed % 7) * 0.1) + seed);
      if (r < drip) { const glow = 0.6 + 0.4 * S(t * 3 + c * 0.7 - r); return r > drip - 1 ? [220, 255, 120] : mix([60, 170, 30], [190, 255, 80], pyRound(glow * 6) / 6); }
      if (flick(t * 1.3, c * 11 + r * 5, 47) > 0.95) return [210, 255, 120];
      return mix([10, 22, 10], [24, 46, 18], pyRound(((S(c * 0.5 + r * 0.8) + 1) / 2) * 3) / 3);
    },
    GILDED: (t, c, r) => {
      let base = mix([255, 222, 120], [170, 110, 30], pyRound(clamp(r / 7.0, 0, 1) * 5) / 5);
      if (AB(S(c * 0.9 + S(r * 1.3) * 2.2) * Math.cos(r * 0.8 - c * 0.3)) < 0.12) base = mix(base, [110, 66, 16], 0.6);
      const band = pmod(c - r * 0.5 - t * 7.0, 30);
      return band < 1.4 ? [255, 252, 230] : band < 3.0 ? mix(base, [255, 248, 210], 0.5) : base;
    },
  };
  function paintShade(paint, gb, ch) {
    if (paint === 'VOID') return ({ t: mix(gb, [120, 80, 210], 0.22), g: mix(gb, [180, 130, 255], 0.55), k: shade(gb, 0.6), w: mix(gb, [90, 70, 150], 0.3), d: shade(gb, 0.7) })[ch] || gb;
    return ({ t: mix(gb, W, 0.15), g: mix(gb, W, 0.4), k: shade(gb, 0.45), w: mix(gb, [200, 210, 230], 0.2), d: shade(gb, 0.5) })[ch] || gb;
  }
  const isPaint = (b) => typeof b === 'string' && b in PX;
  const liveColor = (b, t) => (b === RAINBOW ? rainbow(t) : isPaint(b) ? TINT[b](t) : b);

  function glowColor(d, body, t, idx) {
    const g = d.glow, a = d.accent;
    switch (g) {
      case 'aeon': return gradient([[0, [90, 40, 190]], [0.5, [255, 214, 120]], [1, [255, 255, 244]]], 0.5 + 0.5 * S(t * 3.2 + idx * 0.8));
      case 'biolume': return mix([20, 90, 140], [160, 255, 240], MX(0.0, S(t * 3 - idx * 0.8)) ** 2);
      case 'foxfire': return gradient([[0, [50, 70, 210]], [0.5, [110, 190, 255]], [1, [240, 252, 255]]], 0.5 + 0.5 * S(t * 15 + idx * 1.9));
      case 'hologlitch': return flick(t, idx, 31) > 0.9 ? [255, 70, 210] : mix([40, 140, 220], [200, 255, 255], 0.5 + 0.5 * S(t * 9 + idx));
      case 'phase': return hsv(0.70 + 0.12 * S(t * 2.2 + idx * 0.6), 0.55, 1.0);
      case 'atomic': return mix([50, 110, 210], [235, 250, 255], (0.5 + 0.5 * S(t * 2.6)) ** 3);
      case 'spore': return mix([40, 150, 110], [190, 255, 220], 0.5 + 0.5 * S(t * 2 + idx * 1.4));
      case 'maw': return gradient([[0, [120, 30, 10]], [0.6, [255, 120, 40]], [1, [255, 230, 160]]], 0.5 + 0.5 * S(t * 7 + idx * 1.1));
      case 'jade': return mix([40, 170, 110], [255, 226, 130], MX(0.0, 1 - AB(idx - (pmod(t * 5, 15) - 2)) / 2.5));
      case 'zodiac': return pmod(Math.trunc(t * 2) + idx, 5) === 0 ? [255, 250, 220] : mix([90, 110, 220], [255, 214, 130], 0.5 + 0.5 * S(t * 2 + idx));
      case 'ghost': return mix([30, 90, 60], [160, 255, 190], 0.5 + 0.5 * S(t * 5 + idx * 0.9) * S(t * 2.3));
      case 'pulse': return mix(shade(a, 0.3), a, 0.5 + 0.5 * Math.sin(t * 4 + idx));
      case 'blink': return Math.trunc(t * 3 + idx) % 2 === 0 ? a : shade(a, 0.25);
      case 'flame': { const k = 0.5 + 0.5 * Math.sin(t * 23 + idx * 2.1) * Math.sin(t * 11 + idx); return gradient([[0, [120, 30, 10]], [0.5, [255, 120, 20]], [1, [255, 232, 130]]], k); }
      case 'prism': return hsv(t * 0.4 + idx * 0.13, 0.7, 1.0);
      case 'scan': { const k = Math.max(0.0, 1 - Math.abs(idx - (((t * 9) % 15) - 2)) / 2.5); return mix(mix(shade(a, 0.28), a, 0.35), [255, 255, 255], k * 0.85); }
      case 'plasma': return gradient([[0, [255, 90, 20]], [0.5, a], [1, [255, 250, 205]]], 0.5 + 0.5 * Math.sin(t * 4.5 + idx * 0.7));
      case 'lava': { const k = clamp(0.5 + 0.4 * Math.sin(t * 2.2 + idx * 1.7) + 0.2 * (flick(t, idx, 3) - 0.5), 0, 1); return gradient([[0, [90, 10, 6]], [0.6, [230, 70, 18]], [1, [255, 196, 80]]], k); }
      case 'storm': { const f = flick(t, idx, 5); return f > 0.86 ? mix(shade(a, 0.22), [235, 245, 255], 0.85) : mix(shade(a, 0.22), a, f * 0.6); }
      case 'matrix': return flick(t, idx, 9) > 0.5 ? [96, 255, 130] : [18, 96, 44];
      case 'refract': { const k = Math.max(0.0, 1 - Math.abs(idx - (((t * 8) % 16) - 2)) / 2.0); return mix(hsv(t * 0.4 + idx * 0.09, 0.6, 1.0), [255, 255, 255], k * 0.8); }
      case 'ember': return gradient([[0, [110, 14, 8]], [0.6, [230, 60, 20]], [1, [255, 190, 90]]], clamp(0.5 + 0.35 * Math.sin(t * 2.6 + idx * 1.3) + 0.3 * (flick(t, idx, 7) - 0.5), 0, 1));
      case 'void': return mix([10, 4, 24], a, 0.5 + 0.5 * Math.sin(t * 3 + idx * 0.9));
      case 'ice': return mix(shade(a, 0.5), [240, 252, 255], 0.5 + 0.5 * Math.sin(t * 2.4 + idx * 0.8));
      case 'toxic': return mix([20, 70, 20], [170, 255, 60], 0.5 + 0.5 * Math.sin(t * 5 + idx * 1.1));
      case 'neon': return (Math.trunc(t * 4) + idx) % 2 === 0 ? [255, 70, 220] : [60, 240, 255];
      case 'gold': { const k = Math.max(0.0, 1 - Math.abs(idx - (((t * 6) % 15) - 2)) / 2.5); return mix([190, 140, 40], [255, 244, 170], k); }
      default: return mix(body, [255, 255, 255], 0.6);
    }
  }

  function barrelColor(style, base, accent, t, d, lane) {
    switch (style) {
      case 'rune': return pmod(Math.trunc(d * 3 - t * 10), 7) === 0 ? [255, 252, 230] : mix(shade(base, 0.7), accent, 0.5 + 0.5 * S(d * 1.4 - t * 7 + lane));
      case 'biolume': return mix([16, 40, 70], [140, 255, 240], 0.15 + 0.85 * MX(0.0, S(d * 1.6 - t * 7)) ** 3);
      case 'spirit': return gradient([[0, [236, 232, 246]], [0.5, [110, 170, 255]], [1, [230, 248, 255]]], clamp(d / 9.0 + 0.25 * S(t * 17 + d * 2.6), 0, 1));
      case 'hardlight': return pmod(Math.trunc(d * 2 - t * 22), 7) === 0 ? [255, 255, 255] : (lane === 0 && d > 1.5 ? [200, 250, 255] : [90, 220, 255]);
      case 'tesseract': return pmod(Math.trunc(d * 2 + t * 6), 4) ? hsv(0.72 + 0.08 * S(d * 0.9 - t * 3 + lane * 2), 0.5, 1.0) : [255, 255, 255];
      case 'atomic': return mix([40, 80, 160], [225, 245, 255], MX(0.0, S(d * 0.9 - t * 8 + lane)) ** 2);
      case 'fungal': return mix([206, 196, 176], [120, 255, 190], 0.5 + 0.5 * S(d * 1.3 - t * 2.4));
      case 'maw': return gradient([[0, [150, 104, 60]], [0.6, [226, 120, 50]], [1, [255, 214, 140]]], clamp(d / 7.5 + 0.15 * S(t * 9 + d), 0, 1));
      case 'serpent': return pmod(Math.trunc(d * 2), 3) === 0 ? [244, 206, 110] : mix([24, 112, 78], [100, 220, 160], 0.5 + 0.5 * S(d - t * 4));
      case 'astrolabe': return flick(t * 0.6, Math.trunc(d * 2), lane + 7) > 0.88 ? [255, 250, 220] : mix([150, 110, 50], [240, 206, 120], 0.5 + 0.5 * S(d * 1.2 + t));
      case 'ghostfire': return mix([34, 60, 56], [130, 255, 180], clamp(0.3 + 0.7 * S(d * 1.8 - t * 6 + lane * 1.7), 0, 1));
      case 'rail': return Math.trunc(d * 2 - t * 14) % 6 === 0 ? accent : base;
      case 'coil': return Math.trunc(d * 2.2 - t * 9) % 3 === 0 ? accent : shade(base, 0.7);
      case 'prism': return hsv(t * 0.5 + d * 0.04, 0.55, 1.0);
      case 'crystal': { const f = 0.5 + 0.5 * Math.sin(d * 1.7 - t * 5 + lane * 2.0); return mix(hsv(t * 0.45 + d * 0.07 + lane * 0.2, 0.5, 1.0), [255, 255, 255], 0.6 * f); }
      case 'flame': { const k = clamp(d / 8.0 + 0.2 * Math.sin(t * 20 + d * 3), 0, 1); return gradient([[0, base], [0.55, [255, 120, 30]], [1, [255, 230, 120]]], k); }
      case 'spin': return (Math.trunc(t * 18) + lane) % 3 === 0 ? accent : base;
      case 'void': return mix([20, 10, 40], [170, 90, 255], 0.5 + 0.5 * Math.sin(d * 1.3 - t * 6));
      case 'bolt': return flick(t, Math.trunc(d * 2), lane) > 0.8 ? [235, 245, 255] : mix(base, accent, 0.5);
      default: return base;
    }
  }

  function overlay(cv, x, y, scale, d, t) {
    const kinds = d.ambient.split('+'), N4 = [[1, 0], [-1, 0], [0, 1], [0, -1]], N4b = [[2, 0], [-2, 0], [0, 2], [0, -2]], TAU = Math.PI * 2, C = Math.cos;
    if (kinds.includes('halo')) {
      for (let i = 0; i < 14; i++) { const ang = t * 1.2 + i * TAU / 14; cv.blendf(x + C(ang) * 6.5 * scale, y + 9 * scale + S(ang) * 1.6 * scale, [255, 232, 150], 0.35 + 0.5 * (0.5 + 0.5 * S(ang * 2 - t * 4))); }
    }
    if (kinds.includes('glyphs')) {
      for (let i = 0; i < 4; i++) {
        const ang = -t * 0.9 + i * Math.PI / 2, gx = x + C(ang) * 8.5 * scale, gy = y + 4 * scale + S(ang) * 3.2 * scale, a_ = 0.45 + 0.45 * S(t * 5 + i * 1.9);
        cv.blendf(gx, gy, d.accent, a_); for (const [dx, dy] of N4) cv.blendf(gx + dx, gy + dy, d.accent, a_ * 0.4);
      }
    }
    if (kinds.includes('lure')) {
      const sw = S(t * 1.3) * 2.6;
      for (let k = 0; k < 10; k++) { const f = k / 9; cv.blendf(x + sw * f * f * scale, y + (6 + 4.5 * f) * scale, [40, 90, 120], 0.75); }
      const bx = x + sw * scale, by = y + 10.5 * scale, glow = 0.6 + 0.4 * S(t * 4.2);
      for (let dx = -3; dx < 4; dx++) for (let dy = -3; dy < 4; dy++) { const dd = Math.hypot(dx, dy); if (dd <= 3.2) cv.blendf(bx + dx, by + dy, dd < 1.2 ? [150, 255, 240] : [60, 200, 220], (1 - dd / 3.4) * glow); }
      cv.plotf(bx, by, [240, 255, 255]);
    }
    if (kinds.includes('tails')) {
      for (let i = 0; i < 9; i++) {
        const baseA = (28 + i * 15.5) * Math.PI / 180, n_ = 12 * scale;
        for (let s2 = 2; s2 <= n_; s2++) {
          const f = s2 / n_, a_ = baseA + 0.35 * S(t * 2.2 + i * 0.7 + f * 2.5) * f, tx = x + C(a_) * f * 11 * scale, ty = y + 3 * scale + S(a_) * f * 9.5 * scale;
          cv.blendf(tx, ty, gradient([[0, [236, 232, 246]], [0.55, [120, 180, 255]], [1, [235, 250, 255]]], f), 0.7 * (1 - f * 0.45));
          if (f > 0.7) cv.blendf(tx + C(a_ + 1.6), ty + S(a_ + 1.6), [120, 190, 255], 0.35);
        }
      }
    }
    if (kinds.includes('foxfire')) {
      for (let i = 0; i < 3; i++) {
        const ang = t * 1.8 + i * TAU / 3, fx = x + C(ang) * 8.5 * scale, fy = y + 4 * scale + S(ang) * 2.6 * scale, fl = 0.6 + 0.4 * flick(t, i, 3);
        cv.blendf(fx, fy, [240, 252, 255], 0.95 * fl); cv.blendf(fx, fy + 1, [110, 190, 255], 0.8 * fl); cv.blendf(fx, fy + 2, [60, 90, 230], 0.5 * fl);
        cv.blendf(fx - 1, fy, [90, 160, 255], 0.4 * fl); cv.blendf(fx + 1, fy, [90, 160, 255], 0.4 * fl);
      }
    }
    if (kinds.includes('scanlines')) {
      for (let k = 0; k < 2; k++) { const sy = y + pmod(t * 6 + k * 4, 9) * scale; for (let dx = -6 * scale; dx <= 6 * scale; dx++) cv.blendf(x + dx, sy, [120, 240, 255], 0.22); }
      if (flick(t * 0.5, 7, 11) > 0.8) { const gy = y + Math.trunc(flick(t, 3, 5) * 6) * scale; for (let dx = -5 * scale; dx <= 5 * scale; dx += 2) cv.blendf(x + dx + 2, gy, [255, 70, 210], 0.5); }
    }
    if (kinds.includes('hypercube')) {
      const cx = x, cy = y + 4.5 * scale, ay = t * 0.9, ax = t * 0.55, pts = [];
      for (const s_ of [7.5, 4.0]) {
        const ring = [];
        for (const vx of [-1, 1]) for (const vy of [-1, 1]) for (const vz of [-1, 1]) {
          let X = vx * s_ * 0.5, Y = vy * s_ * 0.5, Z = vz * s_ * 0.5; const ang = ay * (s_ > 5 ? 1 : -1.6);
          [X, Z] = [X * C(ang) - Z * S(ang), X * S(ang) + Z * C(ang)]; [Y, Z] = [Y * C(ax) - Z * S(ax), Y * S(ax) + Z * C(ax)];
          ring.push([cx + X * scale * 1.5, cy + Y * scale * 1.2]);
        }
        pts.push(ring);
      }
      const line = (p, q, col, a_) => { const n_ = Math.trunc(MX(AB(q[0] - p[0]), AB(q[1] - p[1]))) + 1; for (let j = 0; j <= n_; j++) cv.blendf(p[0] + (q[0] - p[0]) * j / n_, p[1] + (q[1] - p[1]) * j / n_, col, a_); };
      const bits = (v) => { let n = 0; while (v) { n += v & 1; v >>= 1; } return n; };
      for (let i = 0; i < 8; i++) for (let j = i + 1; j < 8; j++) if (bits(i ^ j) === 1) { line(pts[0][i], pts[0][j], [200, 160, 255], 0.55); line(pts[1][i], pts[1][j], [255, 255, 255], 0.45); }
      for (let i = 0; i < 8; i++) line(pts[0][i], pts[1][i], [140, 100, 240], 0.3);
    }
    if (kinds.includes('constellation')) {
      let prev = null;
      for (let i = 0; i < 13; i++) {
        const ang = t * 0.4 + (i % 12) * TAU / 12, rr = (9.5 + 1.2 * S(i * 2.7)) * scale, sx = x + C(ang) * rr, sy = y + 4 * scale + S(ang) * rr * 0.42;
        if (prev) for (let j = 1; j < 6; j++) cv.blendf(prev[0] + (sx - prev[0]) * j / 6, prev[1] + (sy - prev[1]) * j / 6, [200, 170, 90], 0.25);
        if (i < 12) { const tw = 0.5 + 0.5 * S(t * 4 + i * 1.3); cv.blendf(sx, sy, [255, 250, 220], 0.6 + 0.4 * tw); for (const [dx, dy] of N4) cv.blendf(sx + dx, sy + dy, [255, 214, 130], 0.3 * tw); }
        prev = [sx, sy];
      }
    }
    if (kinds.includes('sails')) {
      for (const [m_, h_] of [[-3, 3.5], [0, 4.5], [3, 3.5]]) {
        const top = y + (6 + h_) * scale;
        for (let k = 0; k < Math.trunc(h_ * scale) + 1; k++) cv.blendf(x + m_ * scale, y + 6 * scale + k, [60, 100, 96], 0.9);
        for (let row = 1; row < Math.trunc(h_ * scale); row++) {
          const f = row / MX(1, h_ * scale), belly = S(f * Math.PI) * (0.9 + 0.5 * S(t * 2 + m_)) * scale, w_ = MX(1, Math.trunc((1.8 - f * 0.6) * scale));
          for (let dx = -w_; dx <= w_; dx++) { if (pmod(dx * 7 + row * 3 + Math.trunc(t * 3), 9) === 0) continue; const edge = AB(dx) === w_ || row === 1; cv.blendf(x + m_ * scale + dx + belly, top - row, [190, 255, 214], edge ? 0.5 : 0.16); }
        }
      }
    }
    if (kinds.includes('riftmotes')) {
      for (let i = 0; i < 8; i++) { const ang = t * 1.5 + i * TAU / 8; cv.blendf(x + C(ang) * (6 + i % 3) * scale, y + 4 * scale + S(ang) * 3 * scale, i % 2 === 0 ? [255, 244, 205] : [120, 60, 220], 0.85); }
    }
    if (kinds.includes('sparkle')) {
      for (let i = 0; i < 4; i++) {
        const ang = t * 1.3 + i * Math.PI / 2, sx = x + Math.cos(ang) * 8 * scale, sy = y + 3 * scale + Math.sin(ang) * 5 * scale, tw = 0.5 + 0.5 * Math.sin(t * 9 + i * 1.7);
        cv.blendf(sx, sy, [255, 230, 150], 0.85 * tw);
        for (const [dx, dy] of N4) cv.blendf(sx + dx, sy + dy, [255, 200, 110], 0.3 * tw);
      }
    }
    if (kinds.includes('prism')) {
      for (let i = 0; i < 6; i++) {
        const ph = (t * 0.9 + i * 0.37) % 1.0, sx = x + Math.cos(i * 2.4 + t * 0.6) * (5 + i % 3) * scale, sy = y + (1.5 + 3.2 * ((i * 5) % 4) / 3) * scale + 2 * Math.sin(t * 2 + i);
        const col = hsv(frac(i / 6 + t * 0.4), 0.5, 1.0), a = Math.sin(ph * Math.PI);
        cv.blendf(sx, sy, [255, 255, 255], 0.95 * a);
        for (const [dx, dy] of N4) cv.blendf(sx + dx, sy + dy, col, 0.55 * a);
        for (const [dx, dy] of N4b) cv.blendf(sx + dx, sy + dy, col, 0.25 * a);
      }
    }
    if (kinds.includes('orbit')) {
      for (let i = 0; i < 5; i++) {
        const ang = t * (1.6 + 0.2 * i) + i * 1.26, sx = x + Math.cos(ang) * (7 + i % 2) * scale, sy = y + 3.5 * scale + Math.sin(ang) * 2.4 * scale;
        cv.blendf(sx, sy, d.accent, 0.9);
        cv.blendf(sx - Math.cos(ang + 1.5) * 0.9, sy - Math.sin(ang + 1.5) * 0.9, d.accent, 0.35);
      }
    }
    if (kinds.includes('lightning')) {
      const step = Math.trunc(t * 14);
      for (let i = 0; i < 2; i++) {
        if (flick(step / 30.0, i, 33) > 0.55) {
          let px = x + (flick(step / 30.0, i, 1) - 0.5) * 9 * scale, py = y + 6 * scale;
          for (let s = 0; s < 5; s++) { px += (flick(step / 30.0, i, 10 + s) - 0.5) * 3; py += 1.6; cv.blendf(px, py, [230, 245, 255], 0.9 - s * 0.14); }
        }
      }
    }
    if (kinds.includes('void')) {
      for (let i = 0; i < 6; i++) {
        const k = (t * 0.8 + i / 6) % 1.0, ang = i * 1.05 + t * 0.7;
        cv.blendf(x + Math.cos(ang) * (1 - k) * 9 * scale, y + 3 * scale + Math.sin(ang) * (1 - k) * 5 * scale, [170, 110, 255], 0.7 * k);
      }
    }
  }

  /* spec = { mask, barrel, glow, ambient, accent, paint, hover }, R = data/render.json */
  function drawTank(R, cv, x, y, facing, angle, body, scale, d, t, opt = {}) {
    const recoil = opt.recoil || 0;
    const paint = isPaint(body) ? body : null;                  // per-pixel paints override a design's own colour, like the game
    if (paint) body = TINT[paint](t); else if (d.paint) body = d.paint; else if (body === RAINBOW) body = rainbow(t);
    let lift = opt.lift === undefined ? d.hover : opt.lift;
    const air = opt.hover === undefined ? lift : opt.hover;
    let groundY = y;
    if (air > 0) {
      const bob = 0.6 * Math.sin(t * 2.4) * scale;
      y = y + lift + bob;
      groundY = opt.hover !== undefined ? y - air * scale - bob : y - lift - bob;
    } else if (lift) y = y + lift;
    if (air > 0) {
      const sh = clamp(1.0 - air * scale / 16.0, 0.35, 0.9);
      for (let dx = Math.trunc(-5.5 * scale); dx <= Math.trunc(5.5 * scale); dx++) cv.blendf(x + dx, groundY, [0, 0, 0], 0.55 * sh * (1 - Math.abs(dx) / (5.5 * scale)));
      for (let k = 0; k < 3; k++) cv.blendf(x + (k - 1) * 2 * scale, y - 1, d.accent, 0.35 + 0.25 * Math.sin(t * 17 + k * 2));
    }
    const pal = { t: mix(body, [255, 255, 255], 0.28), h: body, g: mix(body, [255, 255, 255], 0.5), k: mix(shade(body, 0.3), [36, 40, 48], 0.5), w: mix(body, [200, 210, 220], 0.3), d: shade(body, 0.38), a: d.accent };
    const a = angle * Math.PI / 180, ca = Math.cos(a), sa = Math.sin(a), spec = R.barrels[d.barrel] || R.barrels.single;
    const px = x, py = y + R.pivot * scale, length = (spec.length - recoil * 2.5) * scale, base = mix(body, [225, 232, 240], 0.4);
    spec.offsets.forEach((off, lane) => {
      for (let k = 0; k < Math.trunc(length * 2) + 1; k++) {
        const dd = k * 0.5, bx = px + dd * ca - off * scale * sa, by = py + dd * sa + off * scale * ca, col = barrelColor(spec.style, base, d.accent, t, dd, lane);
        for (let ox = 0; ox < scale; ox++) for (let oy = 0; oy < scale; oy++) cv.plotf(bx + ox * 0.9 - (scale - 1) * 0.45, by + oy * 0.9 - (scale - 1) * 0.45, col);
      }
    });
    cv.plotf(px + length * ca, py + length * sa, mix(base, [255, 255, 255], 0.6));
    const baseX = Math.floor(x) - 5 * scale, baseY = pyRound(y);
    d.mask.forEach((row, r) => {
      for (let c = 0; c < row.length; c++) {
        const ch = row[c]; if (ch === '.') continue;
        const cc = facing > 0 ? c : R.w - 1 - c;
        const col = ch === 'l' ? glowColor(d, body, t, cc) : MAT[ch] ? MAT[ch](body, d.accent, t, cc, r, 0)
          : paint && 'thgkwd'.includes(ch) ? paintShade(paint, PX[paint](t, cc, r), ch) : (pal[ch] || pal.h);
        const wx = baseX + cc * scale, wy = baseY + (R.h - 1 - r) * scale;
        for (let ox = 0; ox < scale; ox++) for (let oy = 0; oy < scale; oy++) cv.plot(wx + ox, wy + oy, col);
      }
    });
    overlay(cv, x, y, scale, d, t);
  }

  /* The particle halves of the ambient kinds (fire, smoke, sparks...), ported from EffectsFactory._ambient_one. */
  class Particles {
    constructor(cap = 600) { this.items = []; this.cap = cap; this.wind = 0; }
    emit(p) { if (this.items.length < this.cap) this.items.push(Object.assign({ gravity: 0, drag: 0, alpha: 1, size: 1, windk: 0 }, p, { max: p.life })); }
    update(dt) {
      this.items = this.items.filter((p) => {
        p.life -= dt; if (p.life <= 0) return false;
        if (p.drag) { const k = Math.max(0, 1 - p.drag * dt); p.vx *= k; p.vy *= k; }
        p.vy -= p.gravity * dt; if (p.windk) p.vx += this.wind * p.windk * dt;
        p.x += p.vx * dt; p.y += p.vy * dt; return true;
      });
    }
    draw(cv) {
      for (const p of this.items) {
        const t = 1 - p.life / p.max, col = mix(p.c0, p.c1, t), a = p.alpha * (1 - t), x = Math.floor(p.x), y = Math.floor(p.y);
        cv.blend(x, y, col, a);
        if (p.size > 1) for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) cv.blend(x + dx, y + dy, col, a * 0.5);
      }
    }
  }
  const U = (a, b) => a + Math.random() * (b - a);
  function ambientOne(ps, kind, x, y, dt) {
    const rate = { fire: 15, burn: 15, smoke: 7, prism: 9, ghostfire: 12, radiation: 9, sand: 10 }[kind] || 6;
    if (Math.random() > dt * rate) return;
    const P = (o) => ps.emit(o);
    switch (kind) {
      case 'burn': ['fire', 'smoke', 'embers'].forEach((k) => ambientOne(ps, k, x, y, 1e9)); break;
      case 'sparks': P({ x: x + U(-4, 4), y: y + 6, vx: U(-8, 8), vy: U(10, 24), life: 0.5, c0: [255, 230, 120], c1: [255, 120, 20], gravity: 40 }); break;
      case 'embers': P({ x: x + U(-4, 4), y: y + 5, vx: U(-3, 3), vy: U(6, 14), life: 1.2, c0: [255, 150, 40], c1: [80, 20, 10], gravity: -8, alpha: 0.9 }); break;
      case 'mist': P({ x: x + U(-5, 5), y: y + 2, vx: U(-3, 3), vy: U(2, 6), life: 1.8, c0: [150, 110, 230], c1: [20, 10, 40], alpha: 0.45, size: 2, windk: 0.5 }); break;
      case 'static': { const a = U(0, Math.PI * 2); P({ x: x + U(-5, 5), y: y + U(2, 8), vx: Math.cos(a) * 14, vy: Math.sin(a) * 14, life: 0.16, c0: [235, 245, 255], c1: [90, 150, 255], drag: 2.0 }); break; }
      case 'frost': P({ x: x + U(-5, 5), y: y + 8, vx: U(-3, 3), vy: U(-6, -2), life: 1.6, c0: [235, 250, 255], c1: [120, 170, 220], alpha: 0.8, windk: 0.6 }); break;
      case 'flare': P({ x: x + U(-5, 5), y: y + 6, vx: U(-4, 4), vy: U(8, 18), life: 1.0, c0: [255, 244, 190], c1: [255, 130, 30], alpha: 0.9, gravity: -6 }); break;
      case 'bits': P({ x: x + U(-5, 5), y: y + 7, vx: 0, vy: U(6, 14), life: 0.9, c0: [150, 255, 175], c1: [8, 56, 22], alpha: 0.9 }); break;
      case 'fire': P({ x: x + U(-4.5, 4.5), y: y + U(3, 6), vx: U(-3, 3), vy: U(14, 26), life: 0.55, c0: [255, 214, 90], c1: [200, 30, 8], gravity: -24, alpha: 0.95, size: Math.random() < 0.35 ? 2 : 1 }); break;
      case 'smoke': P({ x: x + U(-4, 4), y: y + 7, vx: U(-3, 3), vy: U(5, 11), life: 2.2, c0: [88, 86, 92], c1: [18, 18, 22], gravity: -4, alpha: 0.55, size: 2, windk: 0.9 }); break;
      case 'prism': { const c = hsv(Math.random(), 0.5, 1.0); P({ x: x + U(-5, 5), y: y + U(1, 7), vx: U(-4, 4), vy: U(3, 10), life: 1.1, c0: c, c1: shade(c, 0.2), alpha: 0.9, gravity: -3 }); break; }
      case 'void': P({ x: x + U(-6, 6), y: y + U(1, 8), vx: U(-3, 3), vy: U(-2, 4), life: 1.4, c0: [150, 90, 240], c1: [10, 4, 24], alpha: 0.7, size: 2, windk: 0.2 }); break;
      case 'bubbles': P({ x: x + U(-5, 5), y: y + 2, vx: U(-2, 2), vy: U(5, 12), life: 1.5, c0: [190, 235, 255], c1: [90, 150, 220], alpha: 0.7, windk: 0.4 }); break;
      case 'petals': P({ x: x + U(-5, 5), y: y + 8, vx: U(-5, 5), vy: U(-6, -1), life: 1.8, c0: [255, 170, 200], c1: [200, 80, 130], alpha: 0.85, windk: 0.8 }); break;
      case 'radiation': P({ x: x + U(-5, 5), y: y + U(5, 8), vx: U(-2, 2), vy: U(8, 18), life: 0.9, c0: [210, 240, 255], c1: [40, 80, 170], gravity: -10, alpha: 0.9 }); break;
      case 'spores': P({ x: x + U(-6, 6), y: y + U(4, 9), vx: U(-3, 3), vy: U(2, 6), life: 2.6, c0: [200, 255, 220], c1: [40, 140, 110], gravity: -1.5, alpha: 0.85, windk: 0.7 }); break;
      case 'sand': P({ x: x + (Math.random() < 0.5 ? -5 : 5) + U(-1, 1), y: y + U(1, 5), vx: U(-4, 4), vy: U(-2, 4), life: 0.9, c0: [226, 190, 120], c1: [130, 90, 50], gravity: 40, alpha: 0.8 }); break;
      case 'feathers': { const c = [[60, 220, 150], [40, 170, 210], [230, 60, 60]][Math.floor(Math.random() * 3)]; P({ x: x + U(-5, 5), y: y + 9, vx: U(-6, 6), vy: U(-5, -1), life: 2.2, c0: c, c1: shade(c, 0.4), alpha: 0.85, windk: 0.9 }); break; }
      case 'ghostfire': P({ x: x + U(-5, 5), y: y + U(2, 5), vx: U(-2, 2), vy: U(10, 18), life: 0.6, c0: [200, 255, 220], c1: [20, 90, 50], gravity: -16, alpha: 0.9, size: Math.random() < 0.3 ? 2 : 1 }); break;
      default: break;
    }
  }
  const OVERLAY_ONLY = ['none', 'sparkle', 'orbit', 'lightning', 'halo', 'glyphs', 'riftmotes', 'lure', 'tails', 'scanlines', 'hypercube', 'constellation', 'sails'];
  const ambient = (ps, d, x, y, dt) => d.ambient.split('+').forEach((k) => { if (!OVERLAY_ONLY.includes(k)) ambientOne(ps, k, x, y, dt); });

  /* Paint a Px onto a 2D canvas context at an integer scale. */
  function paint(ctx, cv, scale) {
    const img = ctx.createImageData(cv.w, cv.h);
    for (let y = 0; y < cv.h; y++) for (let x = 0; x < cv.w; x++) { const c = cv.rows[y][x], i = (y * cv.w + x) * 4; img.data[i] = c[0]; img.data[i + 1] = c[1]; img.data[i + 2] = c[2]; img.data[i + 3] = 255; }
    ctx.canvas.width = cv.w; ctx.canvas.height = cv.h; ctx.putImageData(img, 0, 0);
    ctx.canvas.style.width = cv.w * scale + 'px'; ctx.canvas.style.height = cv.h * scale + 'px';
  }

  /* Build a design from chosen part ids, the way the game's design_from_custom does. */
  function composeDesign(R, parts) {
    const rows = [...R.turrets[parts.turret], ...R.hulls[parts.hull], ...R.tracks[parts.track]];
    const acc = R.colors.find((c) => c[0] === parts.accent);
    return { mask: rows, barrel: parts.barrel, glow: parts.glow, ambient: parts.ambient || 'none', accent: acc ? acc[1] : [236, 242, 250], paint: null, hover: parts.hover ? 3.0 : 0 };
  }
  const PAINTS = Object.keys(PX);
  return { Px, drawTank, Particles, ambient, paint, composeDesign, mix, shade, hsv, rainbow, RAINBOW, PAINTS, liveColor, glowColor, barrelColor, MAT };
})();
if (typeof module !== 'undefined') module.exports = TankGfx;
