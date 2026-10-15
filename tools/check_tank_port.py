#!/usr/bin/env python3
"""Checks that tank.js (the website's port of the game's tank renderer) draws every tank exactly like terminaltanks.py.

    python3 tools/check_tank_port.py           # every design, several moments in time, every paint
Needs node. Draws each case with the game's draw_tank and with tank.js and compares the pixels (particles are random, so
only the deterministic parts are compared: hull, materials, glows, barrels, overlays and paints). A difference of one
colour step is allowed, because JavaScript and Python round the last bit of sin() differently now and then."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ttgame  # noqa: E402

ROOT = ttgame.ROOT
NODE = r"""
const fs = require('fs'), T = require(process.argv[2]), R = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')), cases = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
const byKey = Object.fromEntries(R.designs.map((d) => [d.key, d]));
const out = cases.map((c) => {
  const d = byKey[c.key], cv = new T.Px(40, 30, [0, 0, 0]);
  T.drawTank(R, cv, 16, 5, c.facing, c.angle, c.body, 2, { mask: d.mask, barrel: d.barrel, glow: d.glow, ambient: d.ambient, accent: d.accent, paint: d.paint, hover: d.hover }, c.t);
  return cv.rows;
});
fs.writeFileSync(process.argv[5], JSON.stringify(out));
"""


def main() -> int:
    tt = ttgame.load(ttgame.game_arg(sys.argv))
    paints = {n: c for n, c in tt.ANIM_PAINTS if n != "RGB"}
    cases = []
    for d in tt.ALL_DESIGNS:
        for t in (0.0, 0.73, 2.4, 5.9):
            cases.append({"key": d.key, "t": t, "angle": 35 + t * 10, "facing": 1 if t < 3 else -1, "body": list(tt.COLOR_BY_NAME["CYAN"])})
    for i, name in enumerate(paints):                                   # every paint on a few hull shapes
        for key in ("ranger", "bulwark", "hornet", "a_martyr"):
            cases.append({"key": key, "t": 1.3 + i * 0.37, "angle": 40, "facing": 1, "body": name})
    with tempfile.TemporaryDirectory() as td:
        js, cj, oj = Path(td, "run.js"), Path(td, "cases.json"), Path(td, "out.json")
        js.write_text(NODE)
        cj.write_text(json.dumps(cases))
        subprocess.run(["node", str(js), str(ROOT / "tank.js"), str(ROOT / "data/render.json"), str(cj), str(oj)], check=True)
        got = json.loads(oj.read_text())
    bad, worst = [], 0
    for c, rows in zip(cases, got):
        d = tt.DESIGN_BY_KEY[c["key"]]
        cv = tt.PixelCanvas(40, 30, (0, 0, 0))
        body = paints[c["body"]] if isinstance(c["body"], str) else tuple(c["body"])
        tt.draw_tank(cv, 16, 5, c["facing"], c["angle"], body, scale=2, design=d, t=c["t"])
        diff = 0
        for py_row, js_row in zip(cv.rows, rows):
            for a, b in zip(py_row, js_row):
                dd = max(abs(a[i] - b[i]) for i in range(3))
                worst = max(worst, dd)
                if dd > 1:
                    diff += 1
        if diff:
            bad.append((c["key"], c["t"], c["body"] if isinstance(c["body"], str) else "", diff))
    print(f"{len(cases)} cases, {len(bad)} with differences, largest channel difference {worst}")
    for b in bad[:40]:
        print("  differs:", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
