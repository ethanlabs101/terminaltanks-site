#!/usr/bin/env python3
"""Renders the whole soundtrack with the game's own audio engine, exactly as the desktop game plays it.

    python3 tools/render_music.py            # render songs whose audio is missing or out of date
    python3 tools/render_music.py --all      # render every song again
    python3 tools/render_music.py --only boss_master
    python3 tools/render_music.py --jobs 4

The desktop game plays music through its helper process: Mixer + SongPlayer (terminaltanks.py), which sequence the song,
auto-level it and soft-clip the output, at the game's default volumes, 22,050 Hz stereo. This script drives that same
Mixer with looping on, exactly as a song plays in the game, and keeps:
  music/<slug>.mp3         the first pass, from the start to the moment the desktop loops it (the end of the 512-sample
                           block in which the song ends). Nothing else is done to the sound: no loudness normalisation.
  music/loop/<slug>.mp3    the first seconds of the second pass: after the loop, notes still ringing from the end of the
                           song carry on over the start of section A. The play page plays these, then carries on in the
                           first file, so the loop is as seamless as on the desktop.
  music/story/...          the same two files in the "story" mood (softer drums, bass and lead), for the songs the game
                           plays in story scenes.
  music/covers, discs      the cover art and the record (song_cover, disc_px)
  music/index.json         signature + exact sample counts, so unchanged songs are skipped and the page can line up
                           the files to the sample.
Encoded as MP3 (LAME VBR V0) at the game's own sample rate. Needs ffmpeg with libmp3lame."""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ttgame  # noqa: E402

ROOT = ttgame.ROOT
OUT = ROOT / "music"
ARGS = sys.argv[1:]


def slug(sid: str) -> str:
    import re
    return re.sub(r"[^a-z0-9_]+", "-", sid.lower()).strip("-")


STORY = ("whisper", "time_machine", "the_blessing", "martyr_ember", "martyr_tempest", "martyr_astral")   # songs the game plays in mood "story"


def _encode(tt, pcm: bytes, dst: Path, title: str, sid: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(tt.AU_SR), "-ac", "2", "-i", "-",
                    "-c:a", "libmp3lame", "-q:a", "0", "-metadata", f"title={title}", "-metadata", "artist=Terminal Tanks",
                    "-metadata", "album=Terminal Tanks Soundtrack", "-metadata", f"comment={sid}", str(dst)], input=pcm, check=True)


def _passes(tt, sid: str, mood: str) -> tuple[bytes, bytes, dict]:
    """The first pass, and the loop file, exactly as the desktop game plays the song (same engine, same defaults).

    The desktop loops at block boundaries: the first pass ends at the end of the 512-sample block in which the song ends
    (`n` samples); every later pass starts at section A (`a`) and lasts `p` samples, also a whole number of blocks.
    The loop file holds the first `ln` samples of the second pass (notes still ringing from the end of the song carry on
    over the start of section A) and the second pass's last block (`lb` samples). In between, the second pass is sample
    for sample the first pass from a + ln on, so the page plays that part from the first file. Each piece in the loop
    file is padded with `pad` samples of the real audio around it: MP3 is least exact at the edges of what it encodes,
    so the edges land in padding the page never plays. Layout: pad | seam | pad | last block | pad."""
    mx = tt.Mixer(cache=False)
    mx.load_song(sid)
    while mx.partial:                                            # every note rendered before playback starts
        mx._fill(next(iter(mx.partial)))
    mx.command(f"mood {mood}")
    mx.command(f"music {sid} 0.05")
    mx.command("loop 1")
    song, bank = mx.ready[sid]
    k = tt.AU_CHUNK
    a = song.secs.get("A", 0)
    n = -(-song.total // k) * k                                  # first pass: up to the end of the block where the song ends
    p = -(-(song.total - a) // k) * k                            # every later pass: from A, a whole number of blocks
    ring = max((len(x) for x in bank.notes.values()), default=0) + k
    ln = min(-(-ring // k) * k, 8 * tt.AU_SR, p - k)             # the seam: as long as the longest note can still ring
    pad = 2048
    out = bytearray()
    while len(out) < (n + p + pad) * 4:
        out += mx.render()
    seg = lambda s0, s1: bytes(out[s0 * 4:s1 * 4])
    first = seg(0, n)
    loop = seg(n - pad, n + ln + pad) + seg(n + p - k - pad, n + p + pad)
    return first, loop, {"n": n, "a": a, "p": p, "ln": ln, "lb": k, "pad": pad}


def _render_one(sid: str) -> tuple[str, str, float, dict]:
    tt = ttgame.load(ttgame.game_arg(ARGS))
    from PIL import Image
    s = slug(sid)
    title = tt.SONGS[sid].name.title()
    a, b, info = _passes(tt, sid, "menu")
    _encode(tt, a, OUT / f"{s}.mp3", title, sid)
    _encode(tt, b, OUT / "loop" / f"{s}.mp3", title + " (loop)", sid)
    if sid in STORY:
        a, b, _ = _passes(tt, sid, "story")
        _encode(tt, a, OUT / "story" / f"{s}.mp3", title, sid)
        _encode(tt, b, OUT / "story" / "loop" / f"{s}.mp3", title + " (loop)", sid)
        info["story"] = True
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
    return sid, tt._song_sig(sid), round(tt.song_of(sid).total / tt.AU_SR, 1), info


def main() -> int:
    tt = ttgame.load(ttgame.game_arg(ARGS))
    for d in (OUT, OUT / "covers", OUT / "discs", OUT / "loop"):
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
        fresh = isinstance(idx.get(sid), dict) and idx[sid].get("sig") == tt._song_sig(sid) and "pad" in idx[sid] and \
            all((OUT / p).exists() for p in (f"{s}.mp3", f"loop/{s}.mp3", f"covers/{s}.png", f"discs/{s}.png"))
        if "--all" in ARGS or not fresh:
            todo.append(sid)
    print(f"{len(todo)} of {len(tt.SONGS)} songs to render with {jobs} worker(s)", flush=True)
    with mp.Pool(jobs) as pool:
        for i, (sid, sig, secs, info) in enumerate(pool.imap_unordered(_render_one, todo), 1):
            idx[sid] = dict(sig=sig, **info)
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
