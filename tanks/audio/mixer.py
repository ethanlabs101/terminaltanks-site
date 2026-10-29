"""The real-time mixer: song players with stem moods, effects, ducking, EQ, the spectrum for the analyser and the
note-bank cache on disk."""
from __future__ import annotations

import bisect
import math
import os
import queue
import sys
import threading
import time
import zlib
from array import array
from pathlib import Path
from typing import Optional

from tanks.audio.composer import STEMS, STEM_GAIN, STYLES
from tanks.audio.notebank import NoteBank, song_of
from tanks.audio.sfx import SFX_DUCK, sfx_build
from tanks.audio.synth import AU_SR, AU_TAU, au_finish
from tanks.colors import clamp
from tanks.content.songs import SONGS
from tanks.save import default_save_path


AU_CHUNK = 512
AUDIO_VER = "tt1"
AU_MUSIC_K = 1.0 / 32768
AU_PUMP = [math.exp(-j / (0.05 * AU_SR)) for j in range(int(0.22 * AU_SR))]
SPEC_BANDS = [55 * 2 ** (k * 0.52) for k in range(16)]          # 55 Hz .. ~10 kHz, log spaced (the jukebox analyser)


def audio_dir() -> Path:
    base = os.environ.get("TT_AUDIO_DIR")
    if base:
        return Path(base)
    try:
        return default_save_path().parent / "audio" / AUDIO_VER
    except Exception:
        return Path.home() / ".terminaltanks_audio" / AUDIO_VER


AU_CACHE_BANKS, AU_CACHE_BYTES = 48, 240 * 1024 * 1024     # the note-bank cache keeps the most recently played songs only


def _prune_bank_cache(keep: Path) -> None:
    """Old versions of a song and the least recently played banks are deleted so the cache never grows without bound."""
    try:
        files = sorted(keep.parent.glob("bank_*.z"), key=lambda p: p.stat().st_mtime, reverse=True)
        stem = keep.name.rsplit("_", 1)[0]
        total, kept = 0, 0
        for p in files:
            if p != keep and p.name.rsplit("_", 1)[0] == stem:
                p.unlink()
                continue
            total += p.stat().st_size
            kept += 1
            if p != keep and (kept > AU_CACHE_BANKS or total > AU_CACHE_BYTES):
                p.unlink()
    except OSError:
        pass


def _song_sig(sid: str) -> str:
    sp = SONGS[sid]
    return "%08x" % (zlib.crc32(repr((sp.bpm, sp.root, sp.scale, sp.meter, sp.style, sp.prog, sp.mel, sp.form, sorted(sp.kw.items()),
                                      STYLES[sp.style])).encode()) & 0xffffffff)


class SongPlayer:
    """Sequences one song: fires note samples on its beat grid; stem gains follow the mood; loops past the intro."""

    def __init__(self, sid, song, bank, mood, fade) -> None:
        self.sid, self.song, self.bank, self.mood = sid, song, bank, mood
        self.pos, self.i = 0, 0
        self.g, self.t, self.fade = 0.0, 1.0, fade
        self.voices: list = []
        self.sg: dict = {}
        self.since = 10 ** 9
        self.pump = SONGS[sid].get("pump", 0.0) or 0.0

    def restart(self) -> None:
        start = self.song.secs.get("A", 0)                           # loop back past the intro, not to silence
        self.pos, self.i = start, bisect.bisect_left(self.song.times, start)

    def render(self, mx: "Mixer", n: int, L: list, R: list) -> None:
        song = self.song
        self.g += (self.t - self.g) * min(1.0, n / AU_SR / max(0.15, self.fade) * 3)
        tg = mx.stem_targets(self.mood)
        for nm in STEMS:
            c = self.sg.get(nm, tg.get(nm, 1.0))
            self.sg[nm] = c + (tg.get(nm, 0.0) - c) * 0.08
        end, ev, times, ko = self.pos + n, song.events, song.times, None
        while self.i < len(ev) and times[self.i] < end:
            t, stem, key, vel, pan = ev[self.i]
            self.i += 1
            gs = self.sg[stem]
            if gs < 0.02:
                continue
            arr = self.bank.notes.get(key)
            if arr is None:
                continue
            gain, off = vel * gs * STEM_GAIN[stem], max(0, t - self.pos)
            self.voices.append([arr, 0, gain * (1 - max(0.0, pan) * 0.7), gain * (1 + min(0.0, pan) * 0.7), off, stem != "drums"])
            if stem == "drums" and key[1].startswith("kick") and ko is None:
                ko = off
        if len(self.voices) > 48:                                     # polyphony cap: oldest long notes go first
            self.voices = self.voices[-48:]
        dg = self.g * mx.vol["mus"] * mx.vol["m"] * mx.dk * AU_MUSIC_K
        Ld, Rd, Lm, Rm = [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n
        for v in self.voices[:]:
            arr, idx, gl, gr, off, mel = v
            seg = arr[idx:idx + n - off]
            m_ = len(seg)
            if m_ == 0:
                self.voices.remove(v)
                continue
            bl, br = (Lm, Rm) if mel else (Ld, Rd)
            a, b = gl * dg, gr * dg
            bl[off:off + m_] = [x + s * a for x, s in zip(bl[off:off + m_], seg)]
            br[off:off + m_] = [x + s * b for x, s in zip(br[off:off + m_], seg)]
            v[1], v[4] = idx + m_, 0
            if v[1] >= len(arr):
                self.voices.remove(v)
        if self.pump > 0 and (ko is not None or self.since < len(AU_PUMP)):
            env = [1.0] * n
            s0, k0 = (ko, 0) if ko is not None else (0, self.since)
            for i in range(s0, n):
                k = k0 + i - s0
                if k >= len(AU_PUMP):
                    break
                env[i] = 1 - self.pump * AU_PUMP[k]
            Lm = [x * e for x, e in zip(Lm, env)]
            Rm = [x * e for x, e in zip(Rm, env)]
        self.since = (n - ko) if ko is not None else self.since + n
        L[:] = [a + b + c for a, b, c in zip(L, Ld, Lm)]
        R[:] = [a + b + c for a, b, c in zip(R, Rd, Rm)]
        self.pos = end


class Mixer:
    """Music players + sound effects -> stereo int16 chunks. Owns the EQ, the auto-level and the spectrum analyser."""

    def __init__(self, cache: bool = True) -> None:
        self.cache = cache
        self.voices: list = []
        self.players: list = []
        self.ready: dict = {}
        self.sfx: dict = {}
        self.lru: list = []
        self.pq: "queue.PriorityQueue" = queue.PriorityQueue()
        self.partial: dict = {}                                     # sid -> (bank, keys still to render, cache path)
        self.req: dict = {}
        self._cnt = 0
        self.vol = {"m": 0.85, "mus": 0.7, "sfx": 0.9}
        self.eq = (0.0, 0.0, 0.0)
        self._eqs = [0.0] * 4
        self.mood = "menu"
        self.want: Optional[tuple] = None
        self.pending_sfx: list = []
        self.duck, self.dk = 0.0, 1.0
        self.agc = 1.0
        self.loop = True
        self.status, self.outbox, self._lastsec, self._nspec = False, [], -1, 0
        self.running = True
        self.lock = threading.Lock()

    # -- loading (runs on the loader thread)
    def request(self, item: str, prio: int = 5) -> None:
        """item: 'song:<sid>' or 'sfx:<name>'. A more urgent request jumps the queue."""
        if (item.startswith("song:") and item[5:] in self.ready) or (item.startswith("sfx:") and item[4:] in self.sfx):
            return
        if prio < self.req.get(item, 10 ** 6):
            self.req[item] = prio
            self._cnt += 1
            self.pq.put((prio, self._cnt, item))

    def load(self, item: str) -> None:
        if item.startswith("song:"):
            self.load_song(item[5:])
        elif item.startswith("fill:"):
            self._fill(item[5:])
        elif item.startswith("sfx:"):
            self.load_sfx(item[4:])

    def _fill_prio(self, sid: str) -> int:
        """The song you are hearing fills first; prefetched songs fill only when nothing more urgent is waiting."""
        playing = any(p.sid == sid for p in self.players) or (self.want is not None and self.want[0] == sid)
        return 1 if playing else 4

    def _fill(self, sid: str) -> None:
        """Render the next slice of a song that is already playing (or ready), then requeue the rest. Slices are short, so a
        new song request always jumps ahead and starts within a fraction of a second."""
        job = self.partial.get(sid)
        if job is None:
            return
        bank, keys, path = job
        t0 = time.monotonic()
        while keys and time.monotonic() - t0 < 0.06:
            k = keys.pop(0)
            if k not in bank.notes:
                bank.notes[k] = bank.make(k)
        if keys:
            self._cnt += 1
            self.pq.put((self._fill_prio(sid), self._cnt, "fill:" + sid))
            return
        self.partial.pop(sid, None)
        if self.cache and path is not None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(bank.dump())
                os.replace(tmp, path)
                _prune_bank_cache(path)
            except OSError:
                pass

    def load_sfx(self, name: str) -> None:
        if name in self.sfx:
            return
        path = audio_dir() / ("sfx_" + name.replace(":", "_") + ".pcm")
        arr = array("h")
        try:
            if self.cache and path.exists():
                arr.frombytes(zlib.decompress(path.read_bytes()))
        except Exception:
            arr = array("h")
        if not arr:
            arr = array("h", [int(max(-1.0, min(1.0, v)) * 30000) for v in au_finish(sfx_build(name))])
            if self.cache:
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(zlib.compress(arr.tobytes(), 3))
                except OSError:
                    pass
        self.sfx[name] = arr

    def load_song(self, sid: str) -> None:
        if sid in self.ready or sid not in SONGS:
            return
        song = song_of(sid)
        spec = SONGS[sid]
        bank = NoteBank(song.spb, spec.get("echo", 0.0) or 0.0)
        path = audio_dir() / f"bank_{sid}_{_song_sig(sid)}.z"
        if self.cache and path.exists():
            try:
                bank.load(path.read_bytes())
                os.utime(path)                                  # recently played: keep it in the cache
            except Exception:
                bank.notes.clear()
        order, seen = [], set()                                     # every note, in the order the song first needs it
        for e in song.events:
            if e[2] not in seen:
                seen.add(e[2])
                order.append(e[2])
        first = {e[2] for e in song.events if e[0] < AU_SR * 1.5}  # the opening 1.5 seconds: enough to start at once
        missing = [k for k in order if k not in bank.notes]
        for k in [k for k in missing if k in first]:
            bank.notes[k] = bank.make(k)
        rest = [k for k in missing if k not in first]
        if rest:
            self.partial[sid] = (bank, rest, path)
            self._cnt += 1
            self.pq.put((self._fill_prio(sid), self._cnt, "fill:" + sid))
        elif missing and self.cache:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(bank.dump())
                os.replace(tmp, path)
                _prune_bank_cache(path)
            except OSError:
                pass
        with self.lock:
            self.ready[sid] = (song, bank)
            self.lru.append(sid)
            keep = {p.sid for p in self.players} | ({self.want[0]} if self.want else set())
            while len(self.ready) > 10:
                old = next((s for s in self.lru if s not in keep and s != sid), None)
                if old is None:
                    break
                self.lru.remove(old)
                self.ready.pop(old, None)
                self.partial.pop(old, None)
                self.req.pop("song:" + old, None)
        if self.status:
            self.outbox.append(f"ready {sid}")

    def stem_targets(self, mood: str) -> dict:
        if mood == "story":
            return {"drums": .45, "bass": .8, "harm": .9, "pad": 1.0, "lead": .85, "counter": .8}
        if mood == "result":
            return {"drums": .3, "bass": .7, "harm": .9, "pad": 1.0, "lead": .6, "counter": .6}
        return {"drums": 1.0, "bass": 1.0, "harm": 1.0, "pad": 1.0, "lead": 1.0, "counter": 1.0}

    # -- commands from the game
    def command(self, line: str) -> None:
        p = line.split()
        if not p:
            return
        c = p[0]
        try:
            if c == "sfx":
                name, vol, pan = p[1], float(p[2]), float(p[3])
                rate = float(p[4]) if len(p) > 4 else 1.0
                a = self.sfx.get(name)
                if a is None:
                    self.request("sfx:" + name, 0)
                    self.pending_sfx.append((time.monotonic(), name, vol, pan, rate))
                elif len(self.voices) < 32:
                    self.voices.append([a, 0.0, vol, pan, rate])
                    if name in SFX_DUCK:
                        self.duck = 1.0
            elif c == "music":
                sid, fade = p[1], float(p[2]) if len(p) > 2 else 1.5
                if sid in ("none", "-"):
                    for pl in self.players:
                        pl.t, pl.fade = 0.0, fade
                    self.want = None
                    return
                cur = self.players[-1] if self.players else None
                if cur and cur.sid == sid and cur.t == 1.0:
                    return
                self.want = (sid, fade)
                self.request("song:" + sid, 0)
                if sid in self.partial:
                    self._cnt += 1
                    self.pq.put((1, self._cnt, "fill:" + sid))
            elif c == "mood":
                self.mood = p[1]
                for pl in self.players:
                    pl.mood = p[1]
            elif c == "vol":
                self.vol = dict(zip(("m", "mus", "sfx"), map(float, p[1:4])))
            elif c == "eq":
                self.eq = tuple(float(x) for x in p[1:4])
            elif c == "loop":
                self.loop = p[1] == "1"
            elif c == "prep":
                for it in p[1:]:
                    self.request(it, 2)
            elif c == "quit":
                self.running = False
        except (IndexError, ValueError, KeyError):
            pass

    def _start(self, sid: str, fade: float) -> None:
        song, bank = self.ready[sid]
        for pl in self.players:
            pl.t, pl.fade = 0.0, min(fade, 0.35)
        self.players.append(SongPlayer(sid, song, bank, self.mood, min(fade, 0.06)))
        if len(self.players) > 2:
            self.players = self.players[-2:]
        if self.status:
            self.outbox.append(f"now {sid} {int(song.total / AU_SR)}")

    def _apply_eq(self, buf: list, ch: int) -> list:
        """3-band EQ (BASS < 250 Hz < MID < 3 kHz < TREBLE), each band -12..+12 dB."""
        gb, gm, gt = (10 ** (x / 20) for x in self.eq)
        a1, a2 = 1 - math.exp(-AU_TAU * 250 / AU_SR), 1 - math.exp(-AU_TAU * 3000 / AU_SR)
        y1, y2 = self._eqs[2 * ch], self._eqs[2 * ch + 1]
        out = [0.0] * len(buf)
        for i, x in enumerate(buf):
            y1 += a1 * (x - y1)
            y2 += a2 * (x - y2)
            out[i] = gb * y1 + gm * (y2 - y1) + gt * (x - y2)
        self._eqs[2 * ch], self._eqs[2 * ch + 1] = y1, y2
        return out

    def _spectrum(self, mono: list) -> str:
        n = len(mono)
        out = []
        for f in SPEC_BANDS:
            w = AU_TAU * f / AU_SR
            c = 2 * math.cos(w)
            s1 = s2 = 0.0
            for x in mono[::2] if f < 1500 else mono:
                s0 = x + c * s1 - s2
                s2, s1 = s1, s0
            mag = math.sqrt(max(0.0, s1 * s1 + s2 * s2 - c * s1 * s2)) / (n / (2 if f < 1500 else 1))
            out.append(str(int(max(0, min(9, 9 + 20 * math.log10(mag + 1e-6) / 6)))))
        return "".join(out)

    def render(self) -> bytes:
        n = AU_CHUNK
        L, R = [0.0] * n, [0.0] * n
        v = self.vol
        self.duck = max(0.0, self.duck - n / AU_SR * 1.2)
        self.dk = 1.0 - 0.45 * self.duck
        with self.lock:
            if self.want and self.want[0] in self.ready:
                sid, fade = self.want
                self.want = None
                self._start(sid, fade)
            for pl in self.players[:]:
                pl.render(self, n, L, R)
                if pl.t == 1.0 and pl.pos >= pl.song.total:
                    if self.loop:
                        pl.restart()
                    else:
                        pl.t = 0.0
                        if self.status:
                            self.outbox.append(f"ended {pl.sid}")
                if pl.t == 0.0 and pl.g < 0.01:
                    self.players.remove(pl)
        if self.players:
            ms = sum(x * x for x in L[::8]) / (n // 8)                     # auto-level the music to about -18 dBFS
            rms = math.sqrt(ms)
            if rms > 1e-4:
                want = clamp(0.11 / rms, 0.4, 2.4)
                self.agc += (want - self.agc) * (0.02 if want < self.agc else 0.006)
            L = [x * self.agc for x in L]
            R = [x * self.agc for x in R]
            if any(abs(x) > 0.05 for x in self.eq):
                L, R = self._apply_eq(L, 0), self._apply_eq(R, 1)
        now = time.monotonic()
        if self.pending_sfx:
            keep = []
            for t0, name, vol, pan, rate in self.pending_sfx:
                if name in self.sfx:
                    self.voices.append([self.sfx[name], 0.0, vol, pan, rate])
                elif now - t0 < 0.6:
                    keep.append((t0, name, vol, pan, rate))
            self.pending_sfx = keep
        for vc in self.voices[:]:
            arr, pos, vol, pan, rate = vc
            ip = int(pos)
            if ip >= len(arr):
                self.voices.remove(vc)
                continue
            if rate == 1.0:
                seg, step = arr[ip:ip + n], n
            else:
                step = n * rate
                seg = [arr[int(ip + k * rate)] for k in range(n) if ip + k * rate < len(arr)]
            g = vol * v["sfx"] * v["m"] * (1 / 32768) * 1.1
            gl, gr = g * (1 - max(0.0, pan) * .85), g * (1 + min(0.0, pan) * .85)
            m_ = len(seg)
            L[:m_] = [x + s * gl for x, s in zip(L[:m_], seg)]
            R[:m_] = [x + s * gr for x, s in zip(R[:m_], seg)]
            vc[1] = pos + step
        if self.status:
            self._nspec += 1
            if self._nspec % 4 == 0:
                self.outbox.append("spec " + self._spectrum([(a + b) * 0.5 for a, b in zip(L, R)]))
            if self.players:
                pl = self.players[-1]
                sec = int(pl.pos / AU_SR)
                if sec != self._lastsec:
                    self._lastsec = sec
                    self.outbox.append(f"pos {pl.sid} {sec} {int(pl.song.total / AU_SR)}")
        out = array("h", bytes(n * 4))
        tanh = math.tanh
        out[0::2] = array("h", [int(30000 * tanh(x * 1.15)) for x in L])
        out[1::2] = array("h", [int(30000 * tanh(x * 1.15)) for x in R])
        if sys.byteorder == "big":
            out.byteswap()
        return out.tobytes()
