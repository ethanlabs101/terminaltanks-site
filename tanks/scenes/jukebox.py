"""The JUKEBOX (every unlocked song, analyser, EQ) and the Blessing gift screen."""
from __future__ import annotations

import math
from typing import Optional

from tanks.audio.director import JUKEBOX_GROUPS, jukebox_unlocked, song_group
from tanks.colors import GOLD, Palette, clamp, gradient, mix
from tanks.content.ammo import AMMO_BY_KEY, BLESSING_KEY
from tanks.content.paints import ASTRAL
from tanks.content.songs import SONGS
from tanks.content.tanks import DEFAULT_DESIGN, DESIGN_BY_KEY
from tanks.scenes.base import BackdropScene
from tanks.scenes.main_menu import MenuScene
from tanks.scenes.martyr import MartyrFinaleScene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.preview import PreviewStage
from tanks.ui.widgets import draw_keycaps, wrap_center


class JukeboxScene(BackdropScene):
    """Every song you have unlocked: play anything, watch the analyser, shape it with a 3-band EQ."""
    BANDS = ("BASS", "MID", "TREBLE")

    def __init__(self, app) -> None:
        super().__init__(app)
        self.rows = []
        for title, grp in JUKEBOX_GROUPS:
            ids = [s for s in SONGS if song_group(s) == grp]
            got = [s for s in ids if jukebox_unlocked(app, s)]
            self.rows.append(("hdr", title, len(got), len(ids)))
            self.rows += [("song", s) for s in got]
        self.sel = next((i for i, r in enumerate(self.rows) if r[0] == "song"), 0)
        self.playing: Optional[str] = None
        self.band, self.loop_one = 0, True
        self.bars = [0.0] * 16
        try:
            self.eq = [float(x) for x in app.save.settings.get("eq", "0,0,0").split(",")][:3]
        except ValueError:
            self.eq = [0.0, 0.0, 0.0]

    def music(self):
        return (self.playing, "menu") if self.playing else None

    def _songs(self) -> list:
        return [r[1] for r in self.rows if r[0] == "song"]

    def handle(self, ev: InputEvent) -> None:
        a = self.app.audio
        if ev.action is Action.BACK:
            a.loop(True)
            self.app.goto(MenuScene(self.app))
        elif ev.action in (Action.UP, Action.DOWN):
            d = -1 if ev.action is Action.UP else 1
            for _ in range(10 if ev.coarse else 1):                 # SHIFT jumps ten songs
                for _ in range(len(self.rows)):
                    self.sel = (self.sel + d) % len(self.rows)
                    if self.rows[self.sel][0] == "song":
                        break
            if self.rows and self.rows[self.sel][0] == "song":
                a.prep(["song:" + self.rows[self.sel][1]])
        elif ev.raw == "TAB":                                      # the first song of the next group
            hdrs = [i for i, r in enumerate(self.rows) if r[0] == "hdr"]
            nxt = next((h for h in hdrs if h > self.sel), hdrs[0] if hdrs else 0)
            for i in range(nxt, len(self.rows)):
                if self.rows[i][0] == "song":
                    self.sel = i
                    break
        elif ev.action in (Action.LEFT, Action.RIGHT):
            self.eq[self.band] = clamp(self.eq[self.band] + (-2 if ev.action is Action.LEFT else 2), -12, 12)
            a.eq(*self.eq)
            self.app.save.settings["eq"] = ",".join(f"{x:g}" for x in self.eq)
        elif ev.raw in ("e", "E"):
            self.band = (self.band + 1) % 3
        elif ev.raw in ("r", "R"):
            self.eq = [0.0, 0.0, 0.0]
            a.eq(0, 0, 0)
            self.app.save.settings["eq"] = "0,0,0"
        elif ev.raw in ("l", "L"):
            self.loop_one = not self.loop_one
            a.loop(self.loop_one)
        elif ev.confirm and self.rows and self.rows[self.sel][0] == "song":
            self.playing = self.rows[self.sel][1]
            a.loop(self.loop_one)

    def update(self, dt: float) -> None:
        super().update(dt)
        a = self.app.audio
        spec = getattr(a, "spec", "0" * 16)
        for i in range(16):
            v = int(spec[i]) if i < len(spec) and spec[i].isdigit() else 0
            self.bars[i] += (v - self.bars[i]) * min(1.0, dt * (14 if v > self.bars[i] else 5))
        if self.playing and not self.loop_one and getattr(a, "ended", None) == self.playing:
            a.ended = None
            songs = self._songs()
            self.playing = songs[(songs.index(self.playing) + 1) % len(songs)] if self.playing in songs else None

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        a = self.app.audio
        W, H = min(100, screen.cols - 2), min(28, screen.rows - 1)
        LW = W - 54                                                 # the song list gets whatever the NOW PLAYING panel leaves
        x, y = (screen.cols - W) // 2, max(0, (screen.rows - H) // 2)
        screen.box(x, y, LW, H, "double", Palette.LINE, Palette.PANEL, "JUKEBOX")
        top = max(0, min(self.sel - (H - 6) // 2, len(self.rows) - (H - 4)))
        for k, r in enumerate(self.rows[top:top + H - 4]):
            ry, i = y + 2 + k, top + k
            if r[0] == "hdr":
                screen.text(x + 2, ry, f"{r[1]}  {r[2]}/{r[3]}", GOLD, Palette.PANEL)
                continue
            sel = i == self.sel
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            screen.fill(x + 2, ry, LW - 4, 1, bg)
            mark = "♪ " if r[1] == self.playing else ("▶ " if sel else "  ")
            name = SONGS[r[1]].name
            if len(name) > LW - 7:                                    # never cut mid-word: drop whole trailing words
                name = name[:LW - 8].rsplit(" ", 1)[0] + "…"
            screen.text(x + 3, ry, mark + name, GOLD if r[1] == self.playing else Palette.WHITE if sel else Palette.TEXT, bg)
        if len(self.rows) > H - 4:                                 # scroll position
            track = H - 4
            pos = int((track - 1) * top / max(1, len(self.rows) - (H - 4)))
            for k in range(track):
                screen.put(x + LW - 2, y + 2 + k, "█" if k == pos else "│", GOLD if k == pos else Palette.LINE, Palette.PANEL)
        px = x + LW + 1
        screen.box(px, y, 53, H, "double", Palette.LINE, Palette.PANEL, "NOW PLAYING")
        cur = self.playing or getattr(a, "now_sid", None)
        if not a.on:
            wrap_center(screen, y + 9, f"Audio is off ({a.label}). Turn AUDIO on in Settings - music needs a sound device.", 47, Palette.AMBER, Palette.PANEL, px, 53, 2)
        if cur in SONGS:
            sp = SONGS[cur]
            screen.center(y + 2, sp.name, GOLD, Palette.PANEL, px, 53)
            wrap_center(screen, y + 3, sp.desc, 47, Palette.MUTED, Palette.PANEL, px, 53, 2)
            meter = {"44": "4/4", "34": "3/4", "68": "6/8", "78": "7/8", "54": "5/4"}.get(sp.meter, sp.meter)
            screen.center(y + 5, f"{sp.bpm} BPM  ·  {meter}  ·  {sp.style.upper()}", Palette.TEXT, Palette.PANEL, px, 53)
            pos, dur = getattr(a, "pos", 0), max(1, getattr(a, "dur", 0))
            bw = 40
            n = int(bw * clamp(pos / dur, 0, 1)) if a.on else 0
            screen.text(px + 4, y + 7, "█" * n + "░" * (bw - n), Palette.PRIMARY, Palette.PANEL)
            screen.text(px + 45, y + 7, f"{pos // 60}:{pos % 60:02d}", Palette.MUTED, Palette.PANEL)
        # the analyser: 16 bands, 10 rows tall
        base = y + 19
        for i, v in enumerate(self.bars):
            h = int(round(v))
            for r in range(9):
                on = r < h
                col = gradient(((0.0, (60, 220, 160)), (0.55, (255, 214, 90)), (1.0, (255, 80, 90))), r / 8) if on else (32, 36, 52)
                screen.text(px + 4 + i * 3, base - r, "▆▆", col, Palette.PANEL)
        screen.text(px + 4, base + 1, "55Hz" + " " * 36 + "10kHz", Palette.MUTED, Palette.PANEL)
        for i, nm in enumerate(self.BANDS):                        # the EQ
            bx = px + 4 + i * 16
            sel = i == self.band
            screen.text(bx, y + 22, ("▶" if sel else " ") + nm, GOLD if sel else Palette.TEXT, Palette.PANEL)
            v = self.eq[i]
            pos_ = int((v + 12) / 24 * 12)
            screen.text(bx, y + 23, "".join("●" if k == pos_ else "─" for k in range(13)), GOLD if sel else Palette.MUTED, Palette.PANEL)
            screen.text(bx + 4, y + 24, f"{v:+.0f} dB", Palette.WHITE if sel else Palette.MUTED, Palette.PANEL)
        screen.text(px + 4, y + 25, "LOOP ONE SONG" if self.loop_one else "AUTO-PLAY NEXT", Palette.PRIMARY, Palette.PANEL)
        ky = y + H if y + H < screen.rows else y + H - 1              # under the panels when there is a free row
        draw_keycaps(screen, x + 2, ky, (("▲▼", "SONG"), ("TAB", "GROUP"), ("ENTER", "PLAY"), ("◄►", "EQ"), ("E", "BAND"), ("R", "FLAT"),
                                         ("L", "LOOP"), ("ESC", "BACK")), Palette.PANEL if ky < y + H else None)


class BlessingGiftScene(BackdropScene):
    """After the finale's rewards: the Martyr's last power, handed down as a single shell."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.t = 0.0
        self.stage = PreviewStage(app.settings, 46, 26, 2)
        self.stage.set_kit(DESIGN_BY_KEY.get("a_martyr", DEFAULT_DESIGN), ASTRAL, AMMO_BY_KEY[BLESSING_KEY], (255, 226, 120), 0.0)

    def enter(self) -> None:
        self.app.sfx("bless_grant", 1.0)

    def music(self):
        return ("the_blessing", "story")

    def handle(self, ev: InputEvent) -> None:
        if self.t > 1.0 and (ev.confirm or ev.action in (Action.CONFIRM, Action.BACK)):
            self.app.goto(MartyrFinaleScene(self.app))

    def update(self, dt: float) -> None:
        super().update(dt)
        self.t += dt
        self.stage.update(dt)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        t = self.t
        W, H = 72, 26
        x, y = (screen.cols - W) // 2, max(0, (screen.rows - H) // 2)
        screen.box(x, y, W, H, "double", GOLD, Palette.PANEL, "A GIFT ACROSS TEN THOUSAND YEARS")
        screen.blit(self.stage.render(), x + (W - 46) // 2, y + 1)
        title = "M A R T Y R ' S   B L E S S I N G"
        screen.center(y + 15, title, mix((176, 120, 255), GOLD, 0.5 + 0.5 * math.sin(t * 3)), Palette.PANEL, x, W)
        lines = ("What remained of the Martyr's power could not follow him into rest.",
                 "It has been sealed into a single shell of gold and starlight: MARTYR'S BLESSING.",
                 "Land one direct hit and nothing left standing in your way will stay standing.",
                 "Enable it in the rules of Single Player, Two Player or LAN.")
        for k, ln in enumerate(lines):
            if t > 0.6 + k * 0.7:
                wrap_center(screen, y + 17 + k * 2, ln, W - 6, Palette.WHITE if k < 3 else Palette.MUTED, Palette.PANEL, x, W, 2)
        if t > 3.5:
            screen.center(y + H - 2, "[ ENTER ]", Palette.PRIMARY if int(t * 2) % 2 == 0 else Palette.MUTED, Palette.PANEL, x, W)
