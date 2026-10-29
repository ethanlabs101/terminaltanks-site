"""Audio output: the sinks (the sounddevice or pyaudio library when installed, Windows waveOut, or a player
program fed through a pipe - paplay, pw-cat, aplay, play or ffplay - or a raw file for tests) and the helper process
(`terminaltanks.py --audio-server`) that runs the mixer so audio can never stall rendering."""
from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import traceback

from tanks.audio.mixer import AU_CHUNK, Mixer, audio_dir
from tanks.audio.synth import AU_SR


# ---- OS output sinks ---------------------------------------------------------------------------------------------------
class _PipeSink:
    def __init__(self, cmd) -> None:
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def write(self, b: bytes) -> None:
        self.p.stdin.write(b)
        self.p.stdin.flush()

    def close(self) -> None:
        try:
            self.p.stdin.close()
            self.p.terminate()
        except Exception:
            pass


class _FileSink:
    """Writes raw PCM to a file in real time (for testing without speakers: TT_AUDIO_SINK=file:/path)."""

    def __init__(self, path: str) -> None:
        self.f = open(path, "wb")
        self.t0, self.n = time.monotonic(), 0

    def write(self, b: bytes) -> None:
        self.f.write(b)
        self.n += AU_CHUNK
        ahead = self.n / AU_SR - (time.monotonic() - self.t0)
        if ahead > 0.02:
            time.sleep(ahead)

    def close(self) -> None:
        self.f.close()


class _LibSink:
    def __init__(self, kind: str) -> None:
        if kind == "sounddevice":
            import sounddevice as sd                       # type: ignore
            self.s = sd.RawOutputStream(samplerate=AU_SR, channels=2, dtype="int16", blocksize=AU_CHUNK)
            self.s.start()
        else:
            import pyaudio                                 # type: ignore
            self.pa = pyaudio.PyAudio()
            self.s = self.pa.open(format=pyaudio.paInt16, channels=2, rate=AU_SR, output=True, frames_per_buffer=AU_CHUNK)

    def write(self, b: bytes) -> None:
        self.s.write(b)

    def close(self) -> None:
        try:
            self.s.stop_stream() if hasattr(self.s, "stop_stream") else self.s.stop()
        except Exception:
            pass


class _WinSink:
    """Windows waveOut ring buffer via ctypes (no packages needed)."""

    def __init__(self) -> None:
        import ctypes
        self.ct = ctypes
        winmm = ctypes.windll.winmm

        class FMT(ctypes.Structure):
            _fields_ = [("tag", ctypes.c_ushort), ("ch", ctypes.c_ushort), ("sr", ctypes.c_ulong), ("avg", ctypes.c_ulong),
                        ("al", ctypes.c_ushort), ("bits", ctypes.c_ushort), ("cb", ctypes.c_ushort)]

        class HDR(ctypes.Structure):
            _fields_ = [("data", ctypes.c_void_p), ("len", ctypes.c_ulong), ("rec", ctypes.c_ulong), ("user", ctypes.c_void_p),
                        ("flags", ctypes.c_ulong), ("loops", ctypes.c_ulong), ("next", ctypes.c_void_p), ("res", ctypes.c_void_p)]

        fmt = FMT(1, 2, AU_SR, AU_SR * 4, 4, 16, 0)
        self.h = ctypes.c_void_p()
        if winmm.waveOutOpen(ctypes.byref(self.h), 0xFFFFFFFF, ctypes.byref(fmt), 0, 0, 0):
            raise OSError("waveOutOpen failed")
        self.winmm, self.i = winmm, 0
        self.bufs = [ctypes.create_string_buffer(AU_CHUNK * 4) for _ in range(6)]
        self.hdrs = []
        for b in self.bufs:
            hd = HDR(ctypes.cast(b, ctypes.c_void_p), AU_CHUNK * 4, 0, None, 0, 0, None, None)
            winmm.waveOutPrepareHeader(self.h, ctypes.byref(hd), ctypes.sizeof(hd))
            hd.flags |= 1
            self.hdrs.append(hd)

    def write(self, b: bytes) -> None:
        hd, buf = self.hdrs[self.i], self.bufs[self.i]
        t0 = time.monotonic()
        while not (hd.flags & 1) and time.monotonic() - t0 < 0.5:
            time.sleep(0.002)
        self.ct.memmove(buf, b, len(b))
        hd.flags &= ~1
        self.winmm.waveOutWrite(self.h, self.ct.byref(hd), self.ct.sizeof(hd))
        self.i = (self.i + 1) % len(self.bufs)

    def close(self) -> None:
        try:
            self.winmm.waveOutReset(self.h)
            self.winmm.waveOutClose(self.h)
        except Exception:
            pass


def _module_ok(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def find_audio_backend():
    """(label, factory) for the best available output, or None."""
    env = os.environ.get("TT_AUDIO_SINK", "")
    if env == "none":
        return None
    if env.startswith("file:"):
        return ("FILE", lambda: _FileSink(env[5:]))
    if _module_ok("sounddevice"):
        return ("SOUNDDEVICE", lambda: _LibSink("sounddevice"))
    if _module_ok("pyaudio"):
        return ("PYAUDIO", lambda: _LibSink("pyaudio"))
    if os.name == "nt":
        return ("WINDOWS", _WinSink)
    rate = str(AU_SR)
    for label, exe, cmd in (("PULSEAUDIO", "paplay", ["paplay", "--raw", f"--rate={rate}", "--format=s16le", "--channels=2", "--latency-msec=60"]),
                            ("PIPEWIRE", "pw-cat", ["pw-cat", "--playback", "--raw", "--rate", rate, "--channels", "2", "--format", "s16", "--latency", "60ms", "-"]),
                            ("ALSA", "aplay", ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", rate, "-c", "2", "--buffer-time=80000"]),
                            ("SOX", "play", ["play", "-q", "-V0", "-t", "raw", "-r", rate, "-e", "signed", "-b", "16", "-c", "2", "-"]),
                            ("FFPLAY", "ffplay", ["ffplay", "-nodisp", "-loglevel", "quiet", "-fflags", "nobuffer", "-f", "s16le", "-ar", rate, "-ac", "2", "-i", "-"])):
        if shutil.which(exe):
            return (label, (lambda c=cmd: _PipeSink(c)))
    return None


def audio_server(cache: bool = True) -> int:
    """Helper-process entry: read commands on stdin, sequence + mix, stream PCM to the OS, report status on stdout."""
    sys.setswitchinterval(0.002)
    be = find_audio_backend()
    if be is None:
        return 3
    mixer = Mixer(cache)
    mixer.status = True
    cmds: "queue.Queue[str]" = queue.Queue()

    def reader() -> None:
        for line in sys.stdin:
            cmds.put(line)
        mixer.running = False

    def loader() -> None:
        try:
            for nm in ("ui_move", "ui_select", "ui_back", "ui_tab", "ui_error", "ui_type", "ui_toggle"):
                mixer.request("sfx:" + nm, 3)                   # queued behind the first song, so music starts first
            while mixer.running:
                try:
                    _, _, item = mixer.pq.get(timeout=0.2)
                except queue.Empty:
                    continue
                mixer.load(item)
        except Exception:
            try:
                audio_dir().mkdir(parents=True, exist_ok=True)
                with open(audio_dir() / "server.log", "a") as f:
                    f.write(traceback.format_exc())
            except OSError:
                pass

    threading.Thread(target=reader, daemon=True).start()
    threading.Thread(target=loader, daemon=True).start()
    try:
        sink = be[1]()
    except Exception:
        return 4
    try:
        while mixer.running:
            while True:
                try:
                    mixer.command(cmds.get_nowait())
                except queue.Empty:
                    break
            sink.write(mixer.render())
            if mixer.outbox:
                lines, mixer.outbox = mixer.outbox, []
                sys.stdout.write("\n".join(lines) + "\n")
                sys.stdout.flush()
    except (BrokenPipeError, OSError, KeyboardInterrupt):
        pass
    finally:
        try:
            sink.close()
        except Exception:
            pass
    return 0
