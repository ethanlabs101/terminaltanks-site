#!/usr/bin/env python3
"""Pre-computes each song's spectrum for the visualisers: music/spec/<slug>.bin, read by the Jukebox's analyser and the
play page (the game's now-playing bars). The music itself then plays through the browser's plain media player, with no
Web Audio graph in the way, which is what keeps it from crackling and dropping out on slower computers.

    python3 tools/render_spectrum.py [--only TEXT] [--jobs N]

File format: b"TTS1", fps (u8), bands (u8), then one row of `bands` bytes per frame. Each byte is the loudest bin in a band
(32 log-spaced bands from 55 Hz to 10 kHz, the game's own range), on the same 0-255 dB scale and with the same smoothing
as a browser AnalyserNode (fftSize 2048, smoothing 0.72), so the bars look like a live analyser's."""
from __future__ import annotations

import json, os, subprocess, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SR, FPS, BANDS, N = 22050, 16, 32, 2048
SMOOTH, DB_MIN, DB_MAX = 0.72, -100.0, -30.0


def edges() -> np.ndarray:
    f = 55 * (10000 / 55) ** (np.arange(BANDS + 1) / BANDS)
    i = np.floor(f / (SR / 2) * (N // 2)).astype(int)
    for k in range(1, len(i)):                                   # every band gets at least one bin
        i[k] = max(i[k], i[k - 1] + 1)
    return i


def render(mp3: str) -> tuple[str, int]:
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ROOT / mp3), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, dtype=np.float32)
    hop = SR / FPS
    frames = int(len(x) / hop) + 1
    win = np.blackman(N).astype(np.float32)                      # the window an AnalyserNode uses
    e = edges()
    prev = np.zeros(N // 2, dtype=np.float32)
    out = bytearray(b"TTS1" + bytes([FPS, BANDS]))
    for f in range(frames):
        c = int(f * hop)
        seg = x[max(0, c - N):c]
        if len(seg) < N:
            seg = np.concatenate([np.zeros(N - len(seg), dtype=np.float32), seg])
        mag = np.abs(np.fft.rfft(seg * win))[:N // 2] / N
        prev = SMOOTH * prev + (1 - SMOOTH) * mag
        db = 20 * np.log10(np.maximum(prev, 1e-12))
        byte = np.clip((db - DB_MIN) / (DB_MAX - DB_MIN) * 255, 0, 255)
        out += bytes(int(byte[e[k]:e[k + 1]].max()) for k in range(BANDS))
    dst = ROOT / mp3.replace("music/", "music/spec/").replace(".mp3", ".bin")
    dst.write_bytes(bytes(out))
    return mp3, len(out)


def main() -> int:
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else (os.cpu_count() or 2)
    songs = json.loads((ROOT / "data/music.json").read_text())["songs"]
    todo = [s["a"] for s in songs if only in s["id"] or only in s["a"]]
    (ROOT / "music/spec").mkdir(parents=True, exist_ok=True)
    total = 0
    with Pool(jobs) as pool:
        for i, (mp3, n) in enumerate(pool.imap_unordered(render, todo), 1):
            total += n
            if i % 25 == 0 or i == len(todo):
                print(f"{i}/{len(todo)}  {total / 1e6:.1f} MB", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
