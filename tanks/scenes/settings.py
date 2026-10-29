"""The SETTINGS and CHEAT CODES screens."""
from __future__ import annotations

from tanks.colors import Palette
from tanks.content.cheats import redeem_cheat
from tanks.content.custom import content_counts
from tanks.content.missions import MISSIONS
from tanks.content.tickets import TICKET_BOSS_BY_KEY
from tanks.content.tournament import TOURNAMENT
from tanks.scenes.base import BackdropScene
from tanks.scenes.main_menu import MenuScene
from tanks.screen import Screen
from tanks.settings import Difficulty, SETTING_ROWS
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import draw_keycaps, panel


class SettingsScene(BackdropScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.index = 0

    def _choices(self, row) -> tuple:
        save = self.app.save
        if row[1] == "difficulty" and not save.master_unlocked:
            return tuple(c for c in row[2] if c[1] is not Difficulty.MASTER)
        if row[1] == "home_mode":
            return tuple(c for c in row[2] if c[1] in save.home_modes())
        return row[2]

    def _choice_index(self, row) -> int:
        cur = getattr(self.app.settings, row[1])
        return next((i for i, (_, v) in enumerate(self._choices(row)) if v == cur), 0)

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK:
            self.app.goto(MenuScene(self.app))
        elif ev.action is Action.UP:
            self.index = (self.index - 1) % len(SETTING_ROWS)
        elif ev.action is Action.DOWN:
            self.index = (self.index + 1) % len(SETTING_ROWS)
        elif ev.action in (Action.LEFT, Action.RIGHT, Action.CONFIRM, Action.FIRE):
            row = SETTING_ROWS[self.index]
            step = -1 if ev.action is Action.LEFT else 1
            choices = self._choices(row)
            i = (self._choice_index(row) + step) % len(choices)
            setattr(self.app.settings, row[1], choices[i][1])
            self.app.apply_settings()

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        step = 2 if screen.rows >= len(SETTING_ROWS) * 2 + 10 else 1
        h = len(SETTING_ROWS) * step + 6
        x, y = panel(screen, 64, h, "SETTINGS")
        for i, row in enumerate(SETTING_ROWS):
            ry = y + 2 + i * step
            sel = i == self.index
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            screen.fill(x + 2, ry, 60, 1, bg)
            screen.text(x + 4, ry, row[0], Palette.WHITE if sel else Palette.MUTED, bg)
            val = self._choices(row)[self._choice_index(row)][0]
            s = f"◄ {val} ►" if sel else val
            screen.text(x + 60 - len(s), ry, s, Palette.PRIMARY if sel else Palette.TEXT, bg)
        row = SETTING_ROWS[self.index]
        desc = row[3]
        if not self.app.save.master_unlocked and row[1] in ("difficulty", "home_mode"):
            desc = "MASTER unlocks after Tournament Level 10"
        screen.center(y + h - 3, desc, Palette.MUTED, Palette.PANEL, x, 64)
        screen.center(y + h - 2, "ESC  BACK", Palette.PRIMARY_DIM, Palette.PANEL, x, 64)


class CheatScene(BackdropScene):
    """Type a code, press ENTER. Codes live in CHEATS; the status block shows what is unlocked without spoiling the codes."""
    MAX_LEN = 24

    def __init__(self, app) -> None:
        super().__init__(app)
        self.text, self.msg, self.msg_ok, self.msg_t = "", "", True, 0.0

    def handle(self, ev: InputEvent) -> None:
        raw = ev.raw
        if raw == "BACKSPACE":
            self.text = self.text[:-1]
        elif ev.action is Action.BACK:
            self.app.goto(MenuScene(self.app))
        elif ev.action is Action.CONFIRM:
            if self.text:
                self.msg_ok, self.msg = redeem_cheat(self.app, self.text)
                self.msg_t, self.text = 5.0, ""
        elif len(raw) == 1 and raw.isalnum() and len(self.text) < self.MAX_LEN:
            self.text += raw.lower()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.msg_t = max(0.0, self.msg_t - dt)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        save, t = self.app.save, self.app.time
        x, y = panel(screen, 64, 24, "CHEAT CODES")
        screen.center(y + 2, "ENTER A CODE", Palette.AMBER, Palette.PANEL, x, 64)
        screen.box(x + 8, y + 3, 48, 3, "single", Palette.LINE, Palette.PANEL_HI)
        cursor = "█" if int(t * 2) % 2 == 0 else " "
        screen.text(x + 10, y + 4, (self.text + cursor)[-44:], Palette.WHITE, Palette.PANEL_HI)
        if self.msg_t > 0:
            screen.center(y + 7, self.msg, Palette.OK if self.msg_ok else Palette.DANGER, Palette.PANEL, x, 64)
        n_levels = sum(save.level_unlocked(l.number) for l in TOURNAMENT)
        lines = [(lab, f"{have}/{total}") for lab, have, total in content_counts(save)] + [
            ("LEVELS", f"{n_levels}/{len(TOURNAMENT)} OPEN  ·  {len(save.completed)}/{len(TOURNAMENT)} CLEARED"),
            ("MISSION", f"{sum(save.mission_unlocked(m.number) for m in MISSIONS)}/{len(MISSIONS)} OPEN  ·  {len(save.mission_completed)}/{len(MISSIONS)} CLEARED"),
            ("TICKETS", f"{len(save.tickets_won & set(TICKET_BOSS_BY_KEY))}/{len(TICKET_BOSS_BY_KEY)} BOSSES"),
            ("MASTER", "DIFFICULTY UNLOCKED" if save.master_unlocked else "DIFFICULTY LOCKED")]
        for k, (lab, val) in enumerate(lines):
            screen.text(x + 12, y + 9 + k, f"{lab:<8}", Palette.MUTED, Palette.PANEL)
            screen.text(x + 21, y + 9 + k, val, Palette.TEXT, Palette.PANEL)
        draw_keycaps(screen, x + 10, y + 21, (("ENTER", "REDEEM"), ("BKSP", "DELETE"), ("ESC", "BACK")), Palette.PANEL)
