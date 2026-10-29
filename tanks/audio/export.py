"""--export-music: renders the soundtrack and every sound effect to WAV files."""
from __future__ import annotations

import time
from array import array
from pathlib import Path

from tanks.audio.director import song_group
from tanks.audio.mixer import AU_CHUNK, Mixer
from tanks.audio.notebank import song_of
from tanks.audio.sfx import SFX_RECIPES, sfx_build
from tanks.audio.synth import AU_SR, au_finish
from tanks.content.songs import SONGS


def export_music(outdir: str, only: str = "") -> int:
    """`--export-music DIR`: renders every song (and every named sound effect) to WAV files so you can audition them."""
    out = Path(outdir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    import wave
    want = [s for s in SONGS if not only or only.lower() in (s + " " + SONGS[s].name + " " + song_group(s)).lower()]
    for i, sid in enumerate(want):
        t0 = time.time()
        mx = Mixer(cache=False)
        mx.load_song(sid)
        mx.command(f"music {sid} 0.05")
        mx.command("loop 0")
        total = song_of(sid).total + AU_SR
        pcm = b"".join(mx.render() for _ in range(total // AU_CHUNK))
        nice = "".join(c if c.isalnum() or c in " -" else "_" for c in SONGS[sid].name).strip()
        with wave.open(str(out / f"{i + 1:03d} {song_group(sid)} - {nice} [{sid}].wav"), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(AU_SR)
            w.writeframes(pcm)
        print(f"{i + 1:3d}/{len(want)}  {SONGS[sid].name:<40} {song_of(sid).total / AU_SR:6.1f}s  ({time.time() - t0:.1f}s)", flush=True)
    if only and only.lower() != "sfx":
        print(f"done: {len(want)} songs in {out}")
        return 0
    sdir = out / "sfx"
    sdir.mkdir(exist_ok=True)
    for nm in SFX_RECIPES:
        with wave.open(str(sdir / f"{nm}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(AU_SR)
            w.writeframes(array("h", [int(max(-1, min(1, v)) * 30000) for v in au_finish(sfx_build(nm))]).tobytes())
    print(f"done: {len(want)} songs and {len(SFX_RECIPES)} sound effects in {out}")
    return 0
