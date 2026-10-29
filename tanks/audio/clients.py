"""The game's handle on audio: AudioClient (desktop helper process), WebAudio (browser) and NullAudio (silent)."""
from __future__ import annotations

import bisect
import os
import subprocess
import sys
import threading
import time
from typing import Optional

from tanks.audio.composer import STEMS, STEM_GAIN
from tanks.audio.notebank import NoteBank, song_of
from tanks.audio.output import find_audio_backend
from tanks.audio.sfx import sfx_build
from tanks.audio.synth import AU_SR, au_finish
from tanks.colors import clamp
from tanks.config import GAME_DIR, IS_WEB
from tanks.content.songs import SONGS
from tanks.settings import Settings
from tanks.terminal import WebTerminalIO


class NullAudio:
    """Silent stand-in (audio off, no output device, or a headless run)."""
    on = False
    label = "OFF"
    now_sid: Optional[str] = None
    pos = dur = 0
    spec = "0" * 16
    ready: set = set()

    def start(self) -> bool:
        return False

    def sfx(self, name: str, vol: float = 1.0, pan: float = 0.0, rate: float = 1.0) -> None: ...
    def music(self, sid: Optional[str], fade: float = 1.5) -> None: ...
    def mood(self, m: str) -> None: ...
    def volumes(self, m: float, mus: float, sfx: float) -> None: ...
    def eq(self, b: float, m: float, t: float) -> None: ...
    def loop(self, on: bool) -> None: ...
    def prep(self, items) -> None: ...
    def tick(self) -> None: ...
    def stop(self) -> None: ...
    def resume(self) -> None: ...


class AudioClient(NullAudio):
    """Desktop: the game's handle to the audio helper process (`terminaltanks.py --audio-server`)."""

    def __init__(self) -> None:
        self.proc: Optional[subprocess.Popen] = None
        self.label = "OFF"
        self._music: Optional[str] = None
        self._mood: Optional[str] = None
        self.now_sid, self.pos, self.dur, self.spec, self.ended = None, 0, 0, "0" * 16, None
        self.ready = set()

    @property
    def on(self) -> bool:
        return self.proc is not None

    def start(self) -> bool:
        if self.proc:
            return True
        be = find_audio_backend()
        if be is None:
            self.label = "NO AUDIO OUTPUT FOUND"
            return False
        self.label = be[0]
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            self.proc = subprocess.Popen([sys.executable, str(GAME_DIR / "terminaltanks.py"), "--audio-server"], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0, creationflags=flags)
        except (OSError, ValueError):
            self.proc, self.label = None, "FAILED TO START"
            return False
        threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()
        return True

    def _reader(self, proc) -> None:
        try:
            for raw in iter(proc.stdout.readline, b""):
                p = raw.decode("utf-8", "ignore").split()
                if not p:
                    continue
                if p[0] == "now" and len(p) >= 3:
                    self.now_sid, self.dur, self.pos = p[1], int(p[2]), 0
                elif p[0] == "pos" and len(p) >= 4:
                    self.now_sid, self.pos, self.dur = p[1], int(p[2]), int(p[3])
                elif p[0] == "spec" and len(p) >= 2:
                    self.spec = p[1]
                elif p[0] == "ready":
                    self.ready.add(p[1])
                elif p[0] == "ended":
                    self.ended = p[1]
        except (OSError, ValueError):
            pass

    def send(self, line: str) -> None:
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write((line + "\n").encode())
            except (OSError, ValueError):
                self.proc, self.label = None, "STOPPED"

    def sfx(self, name: str, vol: float = 1.0, pan: float = 0.0, rate: float = 1.0) -> None:
        if self.proc:
            self.send(f"sfx {name} {vol:.2f} {clamp(pan, -1, 1):.2f} {rate:.3f}")

    def music(self, sid: Optional[str], fade: float = 1.5) -> None:
        if self.proc and sid != self._music:
            self._music = sid
            self.send(f"music {sid or 'none'} {fade}")

    def mood(self, m: str) -> None:
        if self.proc and m != self._mood:
            self._mood = m
            self.send(f"mood {m}")

    def volumes(self, m: float, mus: float, sfx: float) -> None:
        self.send(f"vol {m:.2f} {mus:.2f} {sfx:.2f}")

    def eq(self, b: float, m: float, t: float) -> None:
        self.send(f"eq {b:.1f} {m:.1f} {t:.1f}")

    def loop(self, on: bool) -> None:
        self.send(f"loop {int(on)}")

    def prep(self, items) -> None:
        items = list(items)
        if items:
            self.send("prep " + " ".join(items))

    def stop(self) -> None:
        if self.proc:
            self.send("quit")
            try:
                self.proc.stdin.close()
                self.proc.wait(timeout=0.8)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None


class WebAudio(NullAudio):
    """Browser (Pyodide): the same interface on the Web Audio API. Notes and effects are synthesised in Python a little
    at a time (a per-frame budget, at half rate) and scheduled sample-accurately by the browser, which also does the
    mixing, the EQ (biquad filters) and the analyser. Any failure turns audio off quietly."""
    SR_DIV = 2

    def __init__(self) -> None:
        self.label, self.ok, self.ctx = "WEB AUDIO", False, None
        self.now_sid, self.pos, self.dur, self.spec = None, 0, 0, "0" * 16
        self.ready = set()
        self._music, self._sched, self._bank, self._song, self._pending = None, 0, {}, None, []
        self._banks: dict = {}
        self._opening: set = set()
        self._started = False
        self._sfx_bufs, self._sfx_q, self._vols = {}, [], (0.85, 0.7, 0.9)
        self._t0 = 0.0
        self._looping = True

    def start(self) -> bool:
        try:
            import js                                                      # type: ignore
            from pyodide.ffi import to_js                                  # type: ignore
            self.js, self.to_js = js, to_js
            ctx = self.ctx = js.AudioContext.new()
            self.master = ctx.createGain()
            self.analyser = ctx.createAnalyser()
            self.analyser.fftSize = 512
            self.music_bus, self.sfx_bus = ctx.createGain(), ctx.createGain()
            lo, mid, hi = ctx.createBiquadFilter(), ctx.createBiquadFilter(), ctx.createBiquadFilter()
            lo.type, lo.frequency.value = "lowshelf", 250
            mid.type, mid.frequency.value, mid.Q.value = "peaking", 1000, 0.7
            hi.type, hi.frequency.value = "highshelf", 3000
            self.eqf = (lo, mid, hi)
            self.music_bus.connect(lo)
            lo.connect(mid)
            mid.connect(hi)
            hi.connect(self.master)
            self.sfx_bus.connect(self.master)
            self.master.connect(self.analyser)
            self.analyser.connect(ctx.destination)
            self.stems = {s: ctx.createGain() for s in STEMS}
            for g in self.stems.values():
                g.connect(self.music_bus)
            self.ok = True
            return True
        except Exception:
            self.ok = False
            return False

    @property
    def on(self) -> bool:
        return self.ok

    def resume(self) -> None:
        try:
            if self.ok and self.ctx.state != "running":
                self.ctx.resume()
        except Exception:
            pass

    def _buffer(self, data: list, sr: int):
        b = self.ctx.createBuffer(1, max(1, len(data)), sr)
        b.copyToChannel(self.js.Float32Array.new(self.to_js(data)), 0)
        return b

    def sfx(self, name: str, vol: float = 1.0, pan: float = 0.0, rate: float = 1.0) -> None:
        if not self.ok:
            return
        b = self._sfx_bufs.get(name)
        if b is None:
            if name not in self._sfx_q:
                self._sfx_q.append(name)
            return
        try:
            src = self.ctx.createBufferSource()
            src.buffer = b
            src.playbackRate.value = rate
            g = self.ctx.createGain()
            g.gain.value = vol
            pn = self.ctx.createStereoPanner()
            pn.pan.value = clamp(pan, -1, 1)
            src.connect(g)
            g.connect(pn)
            pn.connect(self.sfx_bus)
            src.start()
        except Exception:
            pass

    def music(self, sid: Optional[str], fade: float = 1.5) -> None:
        if not self.ok or sid == self._music:
            return
        if self._music in self._banks:                                  # remember how far the last song got
            self._banks[self._music] = (self._bank, self._pending)
        self._music = sid
        self._song, self._bank, self._pending, self._sched = None, {}, [], 0
        try:
            now = self.ctx.currentTime
            self.music_bus.gain.setTargetAtTime(0.0, now, 0.06)
        except Exception:
            pass
        if sid:
            self._song = song_of(sid)
            cached = self._banks.get(sid)
            if cached is not None:                                      # heard recently: carry on from where it got to
                self._bank, self._pending = cached[0], list(cached[1])
            else:
                order, seen = [], set()                                 # render in the order the song needs its notes
                for e in self._song.events:
                    if e[2] not in seen:
                        seen.add(e[2])
                        order.append(e[2])
                self._pending = order
                self._banks[sid] = (self._bank, self._pending)
                while len(self._banks) > 6:
                    self._banks.pop(next(iter(self._banks)))
            self._opening = {e[2] for e in self._song.events if e[0] < AU_SR * 1.5}
            self._started = False

    def volumes(self, m: float, mus: float, sfx: float) -> None:
        self._vols = (m, mus, sfx)
        try:
            self.master.gain.value, self.sfx_bus.gain.value = m, sfx
        except Exception:
            pass

    def eq(self, b: float, m: float, t: float) -> None:
        try:
            for f, v in zip(self.eqf, (b, m, t)):
                f.gain.value = v
        except Exception:
            pass

    def loop(self, on: bool) -> None:
        self._looping = on

    def tick(self) -> None:
        """Called once a frame: synthesise a little, schedule the next ~0.4 s of notes, read the analyser."""
        if not self.ok:
            return
        try:
            budget = time.perf_counter() + 0.008
            while self._sfx_q and time.perf_counter() < budget:
                nm = self._sfx_q.pop(0)
                self._sfx_bufs[nm] = self._buffer(au_finish(sfx_build(nm)), AU_SR)
            song = self._song
            if song is None:
                return
            if self._pending:                                           # keep rendering ahead of playback, a slice per frame
                bank = NoteBank(song.spb * 1.0, SONGS[song.sid].get("echo", 0.0) or 0.0)
                while self._pending and time.perf_counter() < budget:
                    k = self._pending.pop(0)
                    arr = bank.make(k)
                    self._bank[k] = self._buffer([x / 32768 for x in arr[::self.SR_DIV]], AU_SR // self.SR_DIV)
            if not self._started:                                       # start as soon as the opening is ready
                if any(k not in self._bank for k in self._opening):
                    return
                self._started = True
                self._t0, self._sched = self.ctx.currentTime + 0.05, 0
                self.music_bus.gain.setTargetAtTime(self._vols[1], self.ctx.currentTime, 0.05)
                self.now_sid, self.dur = song.sid, int(song.total / AU_SR)
            now = self.ctx.currentTime
            horizon = int((now - self._t0 + 0.4) * AU_SR)
            ev = song.events
            while self._sched < len(ev) and ev[self._sched][0] <= horizon:
                t, stem, key, vel, _ = ev[self._sched]
                self._sched += 1
                b = self._bank.get(key)
                if b is None:
                    continue
                src = self.ctx.createBufferSource()
                src.buffer = b
                g = self.ctx.createGain()
                g.gain.value = vel * STEM_GAIN[stem] * 0.55
                src.connect(g)
                g.connect(self.stems[stem])
                src.start(self._t0 + t / AU_SR)
            self.pos = int(max(0.0, now - self._t0))
            if self._sched >= len(ev) and now - self._t0 > song.total / AU_SR:
                if self._looping:
                    start = song.secs.get("A", 0)
                    self._t0 = now - start / AU_SR
                    self._sched = bisect.bisect_left(song.times, start)
            arr = self.js.Uint8Array.new(self.analyser.frequencyBinCount)
            self.analyser.getByteFrequencyData(arr)
            vals = arr.to_py()
            n = len(vals)
            self.spec = "".join(str(min(9, int(vals[min(n - 1, int(n * (2 ** (k * 0.45) - 1) / (2 ** 7.2)))] / 28))) for k in range(16))
        except Exception:
            self.ok = False

    def prep(self, items) -> None:
        for it in items:
            if it.startswith("sfx:") and it[4:] not in self._sfx_bufs and it[4:] not in self._sfx_q:
                self._sfx_q.append(it[4:])


def make_audio(term, settings: "Settings"):
    """The right audio engine for where we run: helper process (desktop), Web Audio (browser) or silence."""
    if getattr(settings, "audio", 2) != 2 or os.environ.get("TT_NOAUDIO"):
        return NullAudio()
    if IS_WEB:
        a = WebAudio()
        return a if a.start() else NullAudio()
    if isinstance(term, WebTerminalIO):                     # headless / test harness: never spawn processes
        return NullAudio()
    a = AudioClient()
    return a if a.start() else NullAudio()
