"""The PROFILES screen: switch, create, rename and delete save profiles."""
from __future__ import annotations

import math

from tanks.colors import GOLD, Palette, RGB, mix
from tanks.content.paints import astral, void_tint
from tanks.profiles import PROFILE_MAX, fmt_playtime
from tanks.save import SaveData
from tanks.scenes.base import BackdropScene
from tanks.scenes.main_menu import MenuScene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import draw_keycaps, panel, wrap_center


class ProfilesScene(BackdropScene):
    """ENTER = switch (or create in an empty slot) · R = rename · X = delete (press twice) · ESC = back."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.sel, self.mode, self.buf, self.msg, self.confirm = 0, "", "", "", False

    def _rows(self) -> list:
        return list(self.app.profiles.profiles) + ([None] if len(self.app.profiles.profiles) < PROFILE_MAX else [])

    def _save_of(self, p: dict) -> "SaveData":
        return self.app.save if p["id"] == self.app.profiles.active else SaveData.load(self.app.profiles.path_of(p["id"]))

    def handle(self, ev: InputEvent) -> None:
        book, rows = self.app.profiles, self._rows()
        self.sel = min(self.sel, len(rows) - 1)
        if self.mode:                                            # typing a name
            if ev.action is Action.BACK:
                self.mode = ""
            elif ev.confirm:
                if self.mode == "new":
                    pid = book.create(self.buf)
                    if pid:
                        self.app.switch_profile(pid)
                        return
                elif self.mode == "rename" and rows[self.sel]:
                    book.rename(rows[self.sel]["id"], self.buf)
                self.mode = ""
            elif ev.raw == "BACKSPACE":
                self.buf = self.buf[:-1]
            elif ev.raw == "SPACE" and len(self.buf) < 14:
                self.buf += " "
            elif len(ev.raw) == 1 and ev.raw.isprintable() and len(self.buf) < 14 and (ev.raw.isalnum() or ev.raw in "-_."):
                self.buf += ev.raw.upper()
            return
        if ev.action is Action.BACK:
            self.app.goto(MenuScene(self.app))
        elif ev.action is Action.UP:
            self.sel, self.confirm = (self.sel - 1) % len(rows), False
        elif ev.action is Action.DOWN:
            self.sel, self.confirm = (self.sel + 1) % len(rows), False
        elif ev.confirm:
            p = rows[self.sel]
            if p is None:
                self.mode, self.buf = "new", ""
            elif p["id"] != book.active:
                self.app.switch_profile(p["id"])
            else:
                self.msg = "THAT PROFILE IS ALREADY ACTIVE"
        elif ev.raw in ("r", "R") and rows[self.sel]:
            self.mode, self.buf = "rename", rows[self.sel]["name"]
        elif ev.raw in ("x", "X", "DELETE") and rows[self.sel]:
            if len(book.profiles) <= 1:
                self.msg = "YOU NEED AT LEAST ONE PROFILE"
            elif not self.confirm:
                self.confirm, self.msg = True, "PRESS X AGAIN TO DELETE THIS PROFILE AND ITS PROGRESS FOR GOOD"
            else:
                self.app.profiles_delete(rows[self.sel]["id"])
                self.confirm, self.msg, self.sel = False, "PROFILE DELETED", 0

    TIER_NAMES = ("NEW GAME", "TOURNAMENT CLEARED", "MISSIONS CLEARED", "VAULT CLEARED", "LEGEND")

    @staticmethod
    def outline_color(tier: int, i: int, t: float) -> RGB:
        """Border colour of the i-th perimeter cell: gold / pulsing green / void / astral+gold, so progress reads at a glance."""
        if tier == 1:
            return mix((190, 140, 40), (255, 222, 120), 0.5 + 0.5 * math.sin(t * 1.2 + i * 0.1))
        if tier == 2:
            return mix((14, 80, 36), (110, 255, 150), 0.5 + 0.5 * math.sin(t * 3.0 + i * 0.05))
        if tier == 3:
            return mix(void_tint(t), (10, 4, 28), 0.5 + 0.5 * math.sin(t * 1.4 + i * 0.12))
        if tier == 4:
            return (255, 214, 90) if (i + int(t * 6)) % 6 < 3 else astral(t + i * 0.03)
        return Palette.LINE

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        W, H = 84, 26
        x, y = panel(screen, W, H, "PROFILES")
        book, rows, t = self.app.profiles, self._rows(), self.app.time
        screen.center(y + 1, "Separate saves in one game. Switching saves your current profile first.", Palette.MUTED, Palette.PANEL, x, W)
        for i, p in enumerate(rows):
            sel, ry = i == self.sel, y + 3 + i * 5
            bw, bx = W - 6, x + 3
            screen.fill(bx, ry, bw, 5, Palette.PANEL_HI if sel else Palette.PANEL)
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            if p is None:
                screen.text(bx + 3, ry + 2, "+ NEW PROFILE", GOLD if sel else Palette.MUTED, bg)
                continue
            sv = self._save_of(p)
            tier, cnt = sv.progress_tier(), sv.progress_counts()
            per = [(bx + k, ry) for k in range(bw)] + [(bx + bw - 1, ry + k) for k in range(1, 5)] + [(bx + bw - 1 - k, ry + 4) for k in range(1, bw)] + [(bx, ry + 4 - k) for k in range(1, 4)]
            for n, (px, py) in enumerate(per):
                ch = "═" if py in (ry, ry + 4) else "║"
                if (px, py) == (bx, ry): ch = "╔"
                elif (px, py) == (bx + bw - 1, ry): ch = "╗"
                elif (px, py) == (bx, ry + 4): ch = "╚"
                elif (px, py) == (bx + bw - 1, ry + 4): ch = "╝"
                screen.put(px, py, ch, self.outline_color(tier, n, t), bg)
            act = p["id"] == book.active
            screen.text(bx + 3, ry + 1, ("▶ " if sel else "  ") + p["name"] + ("   ★ ACTIVE" if act else ""), GOLD if act else Palette.WHITE if sel else Palette.TEXT, bg)
            tn = self.TIER_NAMES[tier]
            screen.text(bx + bw - 3 - len(tn), ry + 1, tn, self.outline_color(tier, int(t * 10), t), bg)
            line = f"PLAYTIME {fmt_playtime(sv.playtime)}    ◉ {sv.coins:,}    ◈ {sv.credits:,}"
            screen.text(bx + 5, ry + 2, line[:bw - 8], Palette.AMBER, bg)
            c = cnt
            screen.text(bx + 5, ry + 3, f"TANKS {c['tanks'][0]}/{c['tanks'][1]}   AMMO {c['ammo'][0]}/{c['ammo'][1]}   MAPS {c['maps'][0]}/{c['maps'][1]}   SCREENS {c['screens'][0]}/{c['screens'][1]}"[:bw - 8], Palette.MUTED, bg)
        if self.mode:
            screen.fill(x + 6, y + 18, W - 12, 4, Palette.PANEL_HI)
            screen.text(x + 8, y + 18, "NAME THE NEW PROFILE:" if self.mode == "new" else "RENAME PROFILE:", Palette.AMBER, Palette.PANEL_HI)
            screen.text(x + 8, y + 19, self.buf + ("█" if int(self.app.time * 2) % 2 == 0 else " "), Palette.WHITE, Palette.PANEL_HI)
            screen.text(x + 8, y + 20, "ENTER OK   ESC CANCEL", Palette.MUTED, Palette.PANEL_HI)
        elif self.msg:
            wrap_center(screen, y + 21, self.msg, W - 8, Palette.AMBER, Palette.PANEL, x, W, 2)
        draw_keycaps(screen, x + 8, y + H - 2, (("▲▼", "CHOOSE"), ("ENTER", "SWITCH/NEW"), ("R", "RENAME"), ("X", "DELETE"), ("ESC", "BACK")), Palette.PANEL)
