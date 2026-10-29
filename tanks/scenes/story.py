"""Cutscenes: the full-screen cinematic and one-time story whispers."""
from __future__ import annotations

import math
import random
import textwrap
from typing import Callable

from tanks.art.bosses import draw_artifact, draw_mage
from tanks.art.tanks import draw_tank
from tanks.audio.director import MARTYR_SONGS
from tanks.colors import GOLD, Palette, mix
from tanks.content.maps import ANCIENT_MAPS
from tanks.content.paints import COLOR_BY_NAME
from tanks.content.story import MARTYR, STORY_LINES
from tanks.content.tanks import DESIGNS, DESIGN_BY_KEY
from tanks.scenes.base import Scene
from tanks.screen import PixelCanvas, Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import render_map_preview


def whisper(app, key: str, nxt: Callable) -> None:
    """Plays a story whisper once (a short CinematicScene), then continues with `nxt`. Already heard / unknown key: just `nxt`."""
    if key in STORY_LINES and app.save.hear(key):
        app.goto(CinematicScene(app, [("A VOICE", ln, "voice", False) for ln in STORY_LINES[key]], nxt))
    else:
        nxt()


def cinematic_song(pages) -> tuple:
    who = {p[0] for p in pages}
    stages = {p[2] for p in pages}
    if "win" in stages:
        return ("the_blessing", "story")
    for st in stages:
        if st.startswith("map") and st[3:4].isdigit():                    # the Martyr speaks before a fight: that phase's theme, held back
            return (MARTYR_SONGS[min(2, int(st[3]))], "story")
    if MARTYR in who:
        return ("time_machine", "story")
    return ("whisper", "story")


class CinematicScene(Scene):
    """Full-screen cutscene: animated art above, typed dialogue below. ENTER advances, ESC skips."""

    def music(self):
        return cinematic_song(self.pages)

    def __init__(self, app, pages: list, on_done: Callable) -> None:
        super().__init__(app)
        self.pages, self.on_done, self.i, self.age, self.done = pages, on_done, 0, 0.0, False
        self.cache: dict = {}
        self.stars = [(random.Random(i * 7 + 5).uniform(0, 1), random.Random(i * 13 + 1).uniform(0, 1), i * 0.7) for i in range(90)]

    def _finish(self) -> None:
        if not self.done:
            self.done = True
            self.on_done()

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK:
            self._finish()
        elif ev.confirm or ev.action in (Action.CONFIRM, Action.FIRE):
            text = self.pages[self.i][1]
            if self.age * 45 < len(text):
                self.age = len(text) / 45 + 0.01
            elif self.i + 1 >= len(self.pages):
                self._finish()
            else:
                self.i, self.age = self.i + 1, 0.0

    def update(self, dt: float) -> None:
        self.age += dt
        if getattr(self, "_snd_page", -1) != self.i and self.i < len(self.pages):
            self._snd_page = self.i
            _, _, stage, flash = self.pages[self.i]
            if self.i:
                self.app.sfx("ui_page", 0.6)
            if stage == "voice":
                self.app.sfx("whisper", 0.8)
            elif stage == "awake":
                self.app.sfx("time_machine", 1.0)
            if flash:
                self.app.sfx("cine_hit", 0.9)

    def draw(self, screen: Screen) -> None:
        cols, rows = screen.cols, screen.rows
        screen.fill(0, 0, cols, rows, (3, 2, 10))
        who, text, stage, flash = self.pages[min(self.i, len(self.pages) - 1)]
        t, W, H = self.app.time, cols, max(8, (rows - 10) * 2)
        if stage.startswith("map"):
            tank = (DESIGN_BY_KEY.get(self.app.save.loadout(0).tank, DESIGNS[0]), COLOR_BY_NAME[self.app.save.loadout(0).tank_color])
            cv = render_map_preview(self.cache, ANCIENT_MAPS[int(stage[3])], W, H, t, [tank, (DESIGN_BY_KEY["a_martyr"], (190, 150, 255))])
        else:
            cv = PixelCanvas(W, H, (0, 0, 0))
            for py in range(H):
                cv.rows[py] = [mix((4, 2, 14), (60, 24, 96) if stage != "win" else (110, 70, 40), py / max(1, H - 1))] * W
            for sx, sy, ph in self.stars:
                cv.blendf(sx * W, sy * H, (255, 255, 255), 0.3 + 0.5 * (0.5 + 0.5 * math.sin(t * 2 + ph)))
            sc = H / 28
            if stage in ("artifact", "awake"):
                draw_artifact(cv, W / 2, H / 2, sc * 1.5, t)
                if stage == "awake":
                    for k in range(14):
                        a = k * math.tau / 14 + t * 0.3
                        for j in range(int(H * 0.5)):
                            cv.blendf(W / 2 + math.cos(a) * j * 1.6, H / 2 + math.sin(a) * j, (255, 226, 150), 0.25 * min(1, self.age / 2) * (1 - j / (H * 0.5)))
            elif stage == "voice":                                         # an unseen speaker: only the stars and the gradient
                pass
            elif stage == "mage":
                draw_artifact(cv, W * 0.28, H * 0.42, sc * 1.0, t)
                draw_mage(cv, W * 0.62, H * 0.08, max(1.0, H * 0.78 / 32), t, min(1.0, 0.25 + self.age / 3))
            elif stage == "duel":
                for x in range(W):
                    for y in range(max(1, int(H * 0.1))):
                        cv.plot(x, y, (24, 14, 44))
                lo = self.app.save.loadout(0)
                draw_tank(cv, W * 0.25, H * 0.1, 1, 40, COLOR_BY_NAME[lo.tank_color], scale=2, design=DESIGN_BY_KEY.get(lo.tank, DESIGNS[0]), t=t)
                draw_mage(cv, W * 0.7, H * 0.1, max(1.0, H * 0.78 / 32), t, 1.0)
            else:                                                          # win: the Martyr dissolves into sand and light
                draw_artifact(cv, W * 0.3, H * 0.42, sc, t)
                draw_mage(cv, W * 0.62, H * 0.08, max(1.0, H * 0.78 / 32), t, max(0.0, 1 - self.age / 6) * 0.9 if self.i >= 1 else 0.9)
                rng = random.Random(int(t * 5))
                for _ in range(40):
                    cv.blendf(W * 0.62 + rng.uniform(-12, 12), H * 0.12 + ((t * 9 + rng.uniform(0, H)) % (H * 0.8)), (255, 226, 150), 0.7)
        if flash and self.age < 0.6:
            for row in cv.rows:
                for x in range(len(row)):
                    row[x] = mix(row[x], (255, 255, 255), (1 - self.age / 0.6) * 0.9)
        screen.blit(cv, 0, 0)
        bw = min(cols - 4, 92)
        bx, by = (cols - bw) // 2, rows - 9
        screen.box(bx, by, bw, 8, "double", Palette.LINE, Palette.PANEL, "")
        col = GOLD if who == MARTYR else Palette.MUTED
        screen.text(bx + 3, by, f" {who} ", col, Palette.PANEL)
        shown = text[:int(self.age * 45)]
        shown_left = len(shown)
        for k, ln in enumerate(textwrap.wrap(text, bw - 8)[:5]):
            screen.text(bx + 3, by + 2 + k, ln[:max(0, shown_left)], Palette.WHITE, Palette.PANEL)
            shown_left -= len(ln) + 1
        if self.age * 45 >= len(text) and int(t * 2) % 2 == 0:
            screen.text(bx + bw - 12, by + 6, "▼ ENTER", Palette.PRIMARY, Palette.PANEL)
        screen.text(bx + 3, by + 7, f"{self.i + 1}/{len(self.pages)}   ESC SKIP", Palette.MUTED, Palette.PANEL)
