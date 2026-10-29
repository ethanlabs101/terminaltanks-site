"""The note bank: the instruments, the pre-rendered notes of one song, and song_of() (a composed, cached Song)."""
from __future__ import annotations

import pickle
import zlib
from array import array

from tanks.audio.composer import Song, compose
from tanks.audio.synth import au_drum, au_echo, au_inst_table, au_tail, mtof
from tanks.content.songs import SONGS


_AU_INST = None
AU_A16 = 18000


def au_instruments() -> dict:
    global _AU_INST
    if _AU_INST is None:
        _AU_INST = au_inst_table()
    return _AU_INST


class NoteBank:
    """Pre-rendered notes for one song; the sequencer fires them on the beat grid."""

    def __init__(self, spb: float, echo: float = 0.0) -> None:
        self.spb, self.echo, self.notes = spb, echo, {}

    def make(self, key) -> array:
        if key[0] == "drum":
            buf, sc = au_drum(key[1]), 1.0
        else:
            name, m, steps = key
            base = name.split("+")[0]
            fn, sc = au_instruments().get(base, au_instruments()["pad"])
            buf = fn(mtof(m), max(0.05, steps * self.spb), 1.0)
            if name.endswith("+e") and self.echo:
                buf = au_echo(buf, self.echo * 4 * self.spb, ((1, .34), (2, .16), (3, .07)), lp=0.5)
        buf = au_tail(buf)
        return array("h", [int(max(-1.0, min(1.0, v * sc)) * AU_A16) for v in buf])

    def dump(self) -> bytes:
        return zlib.compress(pickle.dumps({k: v.tobytes() for k, v in self.notes.items()}), 3)

    def load(self, blob: bytes) -> None:
        for k, b in pickle.loads(zlib.decompress(blob)).items():
            a = array("h")
            a.frombytes(b)
            self.notes[k] = a


_au_songs: dict = {}


def song_of(sid: str) -> "Song":
    s = _au_songs.get(sid)
    if s is None:
        spec = SONGS[sid]
        s = _au_songs[sid] = compose(spec)
        if spec.get("echo"):                                        # lead gets the style's echo baked in
            s.events = [(t, st, ((k[0] + "+e",) + k[1:]) if st == "lead" else k, v, p) for t, st, k, v, p in s.events]
            s.keys = {e[2] for e in s.events}
    return s
