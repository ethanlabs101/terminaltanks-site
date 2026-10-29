"""The NOW PLAYING card that slides in when the music changes."""
from __future__ import annotations

import math
import random
import re
import zlib
from typing import Optional

from tanks.art.covers import NOTE_NAMES, SCALE_NAMES, SONG_GROUP_LABEL, disc_sample, song_cover, song_disc
from tanks.audio.director import song_group
from tanks.colors import GOLD, RGB, clamp, ease_out, gradient, hsv, mix
from tanks.content.songs import SONGS
from tanks.screen import Screen


class NowPlaying:
    """Racing-game NOW PLAYING card: the song's own album cover with the record sliding out and spinning, the title decoding into place,
    an oscilloscope, a live analyser, key/tempo/style, a beat-pulsed frame, motion streaks, a landing sweep, a burning edge."""
    IN, HOLD, OUT = 0.42, 4.6, 0.45
    GROUP_HUE = {"menu": 0.53, "battle": 0.03, "tbos": 0.12, "mission": 0.36, "ticket": 0.78, "martyr": 0.14, "story": 0.70}
    GLYPHS = "▓▒░█▚▞#%&@$*+=?<>"

    def __init__(self) -> None:
        self.sid: Optional[str] = None
        self.t = 99.0

    def show(self, sid: str) -> None:
        self.sid, self.t = sid, 0.0

    @property
    def active(self) -> bool:
        return self.sid is not None and self.t < self.IN + self.HOLD + self.OUT

    def draw(self, screen: Screen, dt: float, spec: str, now: float, y0: int = 1) -> None:
        if not self.active or self.sid not in SONGS:
            return
        self.t += dt
        sid, sp, t = self.sid, SONGS[self.sid], self.t
        grp = song_group(sid)
        meter = {"44": "4/4", "34": "3/4", "68": "6/8", "78": "7/8", "54": "5/4", "98": "9/8", "128": "12/8", "58": "5/8"}.get(sp.meter, sp.meter)
        title = sp.name
        sub = f"{SONG_GROUP_LABEL.get(grp, 'MUSIC')}  ·  {sp.bpm} BPM  ·  {meter}"
        blurb = sp.desc
        for pre in ("Home screen. ", "Battlefield theme. ", "Battlefield. ", "Ticket boss. "):
            blurb = blurb.replace(pre, "")
        info = f"{NOTE_NAMES[sp.root % 12]} {SCALE_NAMES.get(sp.scale, sp.scale.upper())}  ·  {sp.style.upper()}"
        order = list(SONGS)
        track = f" TRACK {order.index(sid) + 1:03d}/{len(order)} "
        hue = (self.GROUP_HUE.get(grp, 0.5) + (zlib.crc32(sid.encode()) % 1000) / 1000 * 0.18 - 0.09) % 1.0
        scol = hsv(hue, 0.65, 1.0)
        H, LEFT, VIS = 7, 21, 8                                     # rows; art column; analyser width
        w = min(screen.cols - 2, max(56, LEFT + max(len(title), len(sub), len(info), len(blurb)) + VIS + 4))
        room = w - LEFT - VIS - 4
        if len(blurb) > room:                                       # keep whole sentences, then whole clauses
            keep = ""
            for part in re.split(r"(?<=[.!?]) ", blurb):
                if len(keep) + len(part) + 1 > room:
                    break
                keep = (keep + " " + part).strip()
            if not keep:
                first = re.split(r"(?<=[.!?]) ", blurb)[0]
                bits = first.split(", ")
                while bits and len(", ".join(bits)) + 1 > room:
                    bits.pop()
                keep = (", ".join(bits).rstrip(".") + ".") if bits else ""
            blurb = keep
        if t < self.IN:
            k = 1 - ease_out(t / self.IN)
        elif t < self.IN + self.HOLD:
            k = 0.0
        else:
            k = clamp((t - self.IN - self.HOLD) / self.OUT, 0, 1) ** 2
        x0 = screen.cols - w - 1 + int(round(k * (w + 2)))
        moving = 0.02 < k < 0.98
        beat = (now * sp.bpm / 60.0) % 1.0
        pulse = (1 - beat) ** 3
        since = t - self.IN
        flash = clamp(1 - since / 0.3, 0, 1) if since >= 0 else 0.0
        base = (10, 12, 24)
        frame = mix(mix((56, 62, 96), scol, 0.45 + 0.4 * pulse), (255, 255, 255), 0.75 * flash)
        gold = mix(GOLD, (255, 255, 255), 0.25 * pulse)
        sweep_x = (since - 0.05) * 90 if 0 <= since < 1.2 else -99    # a light sweep across the glass as it lands

        def bg_at(c: int, r: int = 0) -> RGB:
            u_ = c / max(1, w - 1)
            col = mix(base, scol, 0.24 * (1 - u_) ** 1.5)
            band = c - sweep_x + r * 2
            if -3 < band < 3:
                col = mix(col, (255, 255, 255), 0.22 * (1 - abs(band) / 3))
            return mix(col, (255, 255, 255), 0.2 * flash * (1 - u_))

        def put(x, y, ch, col, back=None):
            if 0 <= x < screen.cols and 0 <= y < screen.rows:
                screen.put(x, y, ch, col, back if back is not None else bg_at(x - x0, y - y0))
        if moving:                                                  # motion streaks trailing the slide
            for r in (1, 2, 3, 4, 5):
                for c in range(1, int(k * 18) + 2):
                    xx = x0 + w + c * 2 + (r % 2)
                    if xx < screen.cols and 0 <= y0 + r < screen.rows:
                        screen.put(xx, y0 + r, "━", mix(scol, (255, 255, 255), 0.3), screen.back[y0 + r][xx][2])
        for r in range(H):
            for c in range(w):
                put(x0 + c, y0 + r, " ", (0, 0, 0))
        for c in range(1, w - 1):
            put(x0 + c, y0, "─", frame)
            put(x0 + c, y0 + H - 1, "─", mix(frame, base, 0.5))
        for r in range(1, H - 1):
            put(x0, y0 + r, "│", frame)
            put(x0 + w - 1, y0 + r, "│", frame)
        for (cx, cy, ch) in ((0, 0, "╭"), (w - 1, 0, "╮"), (0, H - 1, "╰"), (w - 1, H - 1, "╯")):
            put(x0 + cx, y0 + cy, ch, frame)
        label = " ♫ NOW PLAYING "
        for i, ch in enumerate(label):
            put(x0 + 2 + i, y0, ch, gold if ch.strip() else frame)
        for i, ch in enumerate(track):
            put(x0 + w - 2 - len(track) + i, y0, ch, mix((150, 160, 196), scol, 0.3) if ch.strip() else frame)
        # --- the sleeve (10 x 10 px, art made for this song) with the record sliding out of it and spinning
        out = 7.0 * ease_out(clamp((since if since > 0 else 0) / 0.6, 0, 1)) if t >= self.IN else 0.0
        spin = now * 6.283 * song_disc(sid)["rpm"] / 60 * 0.25      # 33, 45 or 78, slowed to read
        rec_cx, rec_cy, R = 5.0 + out, 5.0, 4.8
        ax, ay = x0 + 2, y0 + 1
        art = song_cover(sid, 10)
        for r in range(5):
            for c in range(18):
                cols2 = []
                for sy in (0, 1):
                    px_, py_ = c + 0.5, r * 2 + sy + 0.5
                    if c < 10:                                      # sleeve in front
                        col = art[r * 2 + sy][c]
                        if c == 9:
                            col = mix(col, (0, 0, 0), 0.3)          # the sleeve's open edge, in shadow
                        cols2.append(col)
                        continue
                    d = math.hypot(px_ - rec_cx, py_ - rec_cy) / R
                    if d > 1.0:
                        cols2.append(None)
                        continue
                    acc = [0, 0, 0]                                 # 2 x 2 samples so the label and patterns stay crisp
                    for ox_, oy_ in ((-0.25, -0.25), (0.25, -0.25), (-0.25, 0.25), (0.25, 0.25)):
                        dd = math.hypot(px_ + ox_ - rec_cx, py_ + oy_ - rec_cy) / R
                        cc = disc_sample(sid, (px_ + ox_ - rec_cx) / R, (py_ + oy_ - rec_cy) / R, spin) if dd <= 1.0 else bg_at(2 + c, r + 1)
                        acc[0] += cc[0]; acc[1] += cc[1]; acc[2] += cc[2]
                    cols2.append((acc[0] // 4, acc[1] // 4, acc[2] // 4))
                top, bot = cols2
                if top is None and bot is None:
                    continue
                back = bg_at(2 + c, r + 1)
                put(ax + c, ay + r, "▀", top or back, bot or back)
        tx = x0 + LEFT
        # --- title: decodes from noise into place, then a gold shimmer travels across it
        reveal = clamp((t - 0.1) / 0.7, 0, 1)
        sh = ((t - 0.8) * 24) % (len(title) + 34) - 4
        rng = random.Random(int(now * 24))
        for i, ch in enumerate(title):
            if ch == " ":
                continue
            settled = i / max(1, len(title)) < reveal * 1.15 - 0.15
            if not settled:
                put(tx + i, y0 + 1, rng.choice(self.GLYPHS), mix(scol, (255, 255, 255), rng.random() * 0.5))
                continue
            glow = max(0.0, 1 - abs(i - sh) / 3.0)
            col = gradient(((0, (255, 255, 255)), (1, mix(scol, (255, 255, 255), 0.35))), i / max(1, len(title) - 1))
            put(tx + i, y0 + 1, ch, mix(col, gold, 0.7 * glow))
        for i, ch in enumerate(sub):
            put(tx + i, y0 + 2, ch, scol if ch == "·" else (160, 170, 204))
        for i, ch in enumerate(blurb):
            put(tx + i, y0 + 3, ch, (196, 200, 220))
        for i, ch in enumerate(info):
            put(tx + i, y0 + 5, ch, scol if ch == "·" else mix((120, 128, 160), scol, 0.25))
        # --- oscilloscope: a trace that breathes with the mix and the beat
        lvl = sum(int(c) for c in spec if c.isdigit()) / max(1, 9 * len(spec)) if spec else 0.0
        amp = 0.35 + 0.65 * max(lvl, 0.35 * (0.4 + 0.6 * pulse))
        ow = w - LEFT - VIS - 3
        for i in range(ow):
            y_ = math.sin(i * 0.55 - now * 7) * 0.6 + math.sin(i * 0.23 + now * 3.1) * 0.4
            y_ = 0.5 + 0.5 * y_ * amp
            put(tx + i, y0 + 4, "▁▂▃▄▅▆▇█"[max(0, min(7, int(y_ * 8)))], hsv((hue + i * 0.01 - now * 0.08) % 1.0, 0.55, 0.65 + 0.35 * pulse))
        # --- four-row analyser on the right
        vx = x0 + w - 2 - VIS
        for i in range(VIS):
            si = int(i * 16 / VIS)
            live = spec and any(c not in "0" for c in spec)
            v = (int(spec[si]) / 9.0) if live and si < len(spec) and spec[si].isdigit() else \
                0.2 + 0.7 * abs(math.sin(now * (2.1 + i * 0.41) + i)) * (0.5 + 0.5 * pulse)
            hgt = v * 5 * 8
            for r in range(5):
                fill = clamp(hgt - (4 - r) * 8, 0, 8)
                if fill <= 0:
                    continue
                col = gradient(((0, (60, 220, 160)), (0.6, (255, 214, 90)), (1, (255, 90, 120))), (4 - r) / 4)
                put(vx + i, y0 + 1 + r, " ▁▂▃▄▅▆▇█"[int(fill)], col)
        # --- the bottom edge burns down while the card is up
        life = clamp(1 - t / (self.IN + self.HOLD), 0, 1)
        lit = int((w - 2) * life)
        for c in range(lit):
            put(x0 + 1 + c, y0 + H - 1, "━", mix(gold, scol, c / max(1, w - 2)))
        if lit > 0:
            put(x0 + lit, y0 + H - 1, "╸", (255, 255, 255))
