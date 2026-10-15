#!/usr/bin/env python3
"""Renders the whole soundtrack for the Jukebox page with the game's own synthesizer.

    python3 tools/render_music.py            # render songs whose audio is missing or out of date
    python3 tools/render_music.py --all      # render every song again
    python3 tools/render_music.py --only boss_master
    python3 tools/render_music.py --jobs 4

The game composes and synthesizes every song in Python at run time (terminaltanks.py: compose(), NoteBank, Mixer). This
script drives the same Mixer the game's own `--export-music` option uses, one song at a time with looping off, and then:
  music/<id>.mp3          the song, loudness-normalised (EBU R128, -16 LUFS) and encoded as VBR MP3 at the game's 22,050 Hz
  music/covers/<id>.png   the song's cover art (song_cover), drawn by the game at 48 x 48 and scaled 4x
  music/discs/<id>.png    the record inside the sleeve (disc_px), as the jukebox's turntable shows it
  music/index.json        a signature per song so unchanged songs are skipped next time
Needs ffmpeg with libmp3lame."""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ttgame  # noqa: E402

ROOT = ttgame.ROOT
OUT = ROOT / "music"
ARGS = sys.argv[1:]
TARGET_LUFS = -16.0


def slug(sid: str) -> str:
    import re
    return re.sub(r"[^a-z0-9_]+", "-", sid.lower()).strip("-")


def _render_one(sid: str) -> tuple[str, str, float]:
    tt = ttgame.load(ttgame.game_arg(ARGS))
    from PIL import Image
    s = slug(sid)
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "song.wav"
        mx = tt.Mixer(cache=False)
        mx.load_song(sid)
        mx.command(f"music {sid} 0.05")
        mx.command("loop 0")
        total = tt.song_of(sid).total + tt.AU_SR                    # the song plus one second of reverb tail
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(tt.AU_SR)
            for _ in range(total // tt.AU_CHUNK):
                w.writeframes(mx.render())
        # two-pass loudness normalisation so every track plays at the same level
        meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af",
                               f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                              capture_output=True, text=True).stderr
        j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
        af = (f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
              f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,"
              f"afade=t=out:st={max(0.0, total / tt.AU_SR - 1.2):.2f}:d=1.2")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-af", af, "-ar", str(tt.AU_SR),
                        "-c:a", "libmp3lame", "-q:a", "5", "-metadata", f"title={tt.SONGS[sid].name.title()}",
                        "-metadata", "artist=Terminal Tanks", "-metadata", "album=Terminal Tanks Soundtrack",
                        "-metadata", f"comment={sid}", str(OUT / f"{s}.mp3")], check=True)
    g = tt.song_cover(sid, 48)
    im = Image.new("RGB", (48, 48))
    im.putdata([tuple(c) for row in g for c in row])
    im.resize((192, 192), Image.NEAREST).save(OUT / "covers" / f"{s}.png", optimize=True)
    n = 96                                                         # the record, pressed once at rest (the page spins it)
    disc = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    px = disc.load()
    h = n / 2
    for y in range(n):
        for x in range(n):
            dx, dy = (x + 0.5 - h) / h, (y + 0.5 - h) / h
            d = math.hypot(dx, dy)
            if d <= 1.0:
                c = tt.disc_px(sid, d, math.atan2(dy, dx), 0.0, False)
                px[x, y] = (c[0], c[1], c[2], 255 if d < 0.985 else 140)
    disc.save(OUT / "discs" / f"{s}.png", optimize=True)
    return sid, tt._song_sig(sid), round(tt.song_of(sid).total / tt.AU_SR, 1)


def main() -> int:
    tt = ttgame.load(ttgame.game_arg(ARGS))
    for d in (OUT, OUT / "covers", OUT / "discs"):
        d.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / "index.json"
    idx = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    only = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else ""
    jobs = int(ARGS[ARGS.index("--jobs") + 1]) if "--jobs" in ARGS else max(1, mp.cpu_count())
    todo = []
    for sid in tt.SONGS:
        if only and only not in sid:
            continue
        s = slug(sid)
        fresh = idx.get(sid) == tt._song_sig(sid) and all((OUT / p).exists() for p in (f"{s}.mp3", f"covers/{s}.png", f"discs/{s}.png"))
        if "--all" in ARGS or not fresh:
            todo.append(sid)
    print(f"{len(todo)} of {len(tt.SONGS)} songs to render with {jobs} worker(s)", flush=True)
    with mp.Pool(jobs) as pool:
        for i, (sid, sig, secs) in enumerate(pool.imap_unordered(_render_one, todo), 1):
            idx[sid] = sig
            print(f"{i:3d}/{len(todo)}  {sid:<28} {secs:6.1f}s", flush=True)
            idx_path.write_text(json.dumps(dict(sorted(idx.items())), indent=0))
    stale = [p for p in OUT.glob("*.mp3") if p.stem not in {slug(s) for s in tt.SONGS}]
    for p in stale:
        print("removing audio for a song the game no longer has:", p.name)
        p.unlink()
    idx = {k: v for k, v in idx.items() if k in tt.SONGS}
    idx_path.write_text(json.dumps(dict(sorted(idx.items())), indent=0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
