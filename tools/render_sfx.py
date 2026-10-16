#!/usr/bin/env python3
"""Renders every sound effect the game can make into one file for the browser: audio/sfx.mp3 plus audio/sfx.json (where
each effect starts and how long it is). The play page loads it once and plays slices of it, so the game never has to
synthesise sound in Python while you play (that is what made the browser version slow).

    python3 tools/render_sfx.py [--game PATH] [--jobs N]

The effects come from the game's own recipes (sfx_build + au_finish, exactly what its audio engine plays): every named
effect, plus the firing and impact sound of every ammo type."""
from __future__ import annotations

import json, os, subprocess, sys, tempfile
from array import array
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ttgame

ROOT = Path(__file__).resolve().parents[1]
GAP = 0.2            # seconds of silence after each effect (room for the MP3 decoder's slop)
MARK_AT = 0.1        # a single click at this time lets the page measure the decoder's start delay exactly
tt = None


def _init(game):
    global tt
    tt = ttgame.load(game)


def _render(name: str):
    return name, list(tt.au_finish(tt.sfx_build(name)))


def main() -> int:
    game = ttgame.game_arg(sys.argv)
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else (os.cpu_count() or 2)
    t = ttgame.load(game)
    sr = t.AU_SR
    names = sorted(t.SFX_RECIPES) + [f"fire:{k}" for k in sorted(t.AMMO_BY_KEY)] + [f"hit:{k}" for k in sorted(t.AMMO_BY_KEY)]
    print(f"rendering {len(names)} sound effects with {jobs} workers...", flush=True)
    with Pool(jobs, initializer=_init, initargs=(game,)) as pool:
        done = dict(pool.imap_unordered(_render, names, chunksize=4))
    pcm = array("f", [0.0] * int(sr * MARK_AT))
    pcm.append(0.9)                                                    # the marker
    pcm.extend([0.0] * int(sr * GAP))
    index = {}
    for n in names:
        data = done[n]
        start = len(pcm)
        pcm.extend(max(-1.0, min(1.0, float(x))) for x in data)
        index[n] = [round(start / sr, 5), round(len(data) / sr, 5)]
        pcm.extend([0.0] * int(sr * GAP))
    out = ROOT / "audio"; out.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".f32", delete=False) as f:
        f.write(pcm.tobytes()); raw = f.name
    try:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", raw,
                        "-c:a", "libmp3lame", "-q:a", "4", str(out / "sfx.mp3")], check=True)
    finally:
        os.unlink(raw)
    meta = {"version": t.__version__, "sr": sr, "mark": MARK_AT, "sfx": index}
    (out / "sfx.json").write_text(json.dumps(meta, separators=(",", ":")) + "\n")
    print(f"audio/sfx.mp3: {len(names)} effects, {len(pcm) / sr:.0f} s, {(out / 'sfx.mp3').stat().st_size / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
