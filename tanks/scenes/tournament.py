"""The Tournament ladder and its level result screen."""
from __future__ import annotations

import math
import textwrap
from typing import Optional, TYPE_CHECKING

from tanks.art.backdrops import prism_text
from tanks.art.tanks import draw_tank
from tanks.colors import GOLD, Palette, RGB, clamp, mix, shade
from tanks.content.ammo import AMMOS, AMMO_BY_KEY
from tanks.content.maps import SPECIAL_MAP_BY_KEY
from tanks.content.missions import payout_state
from tanks.content.paints import COLOR_BY_NAME
from tanks.content.tanks import DESIGNS, DESIGN_BY_KEY
from tanks.content.tournament import TOURNAMENT, TournamentLevel
from tanks.scenes.base import BackdropScene
from tanks.scenes.main_menu import MenuScene
from tanks.scenes.story import whisper
from tanks.screen import PixelCanvas, Screen
from tanks.settings import Difficulty
from tanks.terminal import Action, InputEvent
from tanks.ui.preview import PreviewStage
from tanks.ui.widgets import draw_keycaps, wrap_center

if TYPE_CHECKING:
    from tanks.match.sessions import TournamentSession


def reward_lines(level: TournamentLevel, compact: bool = False) -> list[tuple[str, str]]:
    """(label, name) pairs describing everything a level unlocks (compact = short labels for the roadmap panel)."""
    tank, ammo = DESIGN_BY_KEY[level.tank], AMMO_BY_KEY[level.ammo]
    if level.number == len(TOURNAMENT):
        if compact:
            return [(f"TANK {DESIGNS.index(tank) + 1}", tank.name), (f"AMMO {AMMOS.index(ammo) + 1}", ammo.name),
                    ("MAP", SPECIAL_MAP_BY_KEY[level.map_key].name.replace("THE ", "")), ("MASTER", "DIFFICULTY"), ("MASTER", "HOME SCREEN")]
        return [("MASTER TANK", tank.name), ("MASTER AMMO", ammo.name), ("MASTER MAP", SPECIAL_MAP_BY_KEY[level.map_key].name),
                ("MASTER DIFFICULTY", "SINGLE PLAYER"), ("MASTER HOME SCREEN", "TITLE + MENU")]
    out = [(f"TANK {DESIGNS.index(tank) + 1}", tank.name), (f"AMMO {AMMOS.index(ammo) + 1}", ammo.name)]
    if level.map_key:
        out.append(("MAP", SPECIAL_MAP_BY_KEY[level.map_key].name))
    return out


ACTS = ((1, "ACT I", "THE PROVING GROUNDS", (120, 225, 150)), (6, "ACT II", "THE IRON ROAD", (255, 190, 90)),
        (11, "ACT III", "THE ELITE", (130, 190, 255)), (18, "FINALE", "THE MASTER'S ROAD", GOLD))


def act_of(n: int) -> tuple:
    return [a for a in ACTS if a[0] <= n][-1]


class TournamentScene(BackdropScene):
    """The roadmap as a carousel: a progress ribbon for all 20 levels, five big cards centred on the selected level,
    and a detail panel. Each level stays locked until the one before it is cleared; cleared levels can be replayed."""
    W = 94
    CARD = ((36, 10), (14, 8), (10, 6))          # (width, height) by distance from the selection

    def __init__(self, app, selected: Optional[int] = None) -> None:
        super().__init__(app)
        save = app.save
        if selected is None:
            open_levels = [l.number for l in TOURNAMENT if save.level_unlocked(l.number) and l.number not in save.completed]
            selected = open_levels[0] if open_levels else len(TOURNAMENT)
        self.sel = selected - 1
        self.stage = PreviewStage(app.settings, 34, 16, 1)
        self.msg, self.msg_t = "", 0.0
        self.moved = 0.0

    def handle(self, ev: InputEvent) -> None:
        from tanks.scenes.setup import SetupScene
        n = len(TOURNAMENT)
        step = 5 if ev.coarse else 1
        if ev.action is Action.BACK:
            self.app.goto(MenuScene(self.app))
        elif ev.action in (Action.LEFT, Action.UP):
            self.sel, self.moved = max(0, self.sel - step), 1.0
        elif ev.action in (Action.RIGHT, Action.DOWN):
            self.sel, self.moved = min(n - 1, self.sel + step), 1.0
        elif ev.confirm:
            lv = TOURNAMENT[self.sel]
            if self.app.save.level_unlocked(lv.number):
                self.app.goto(SetupScene(self.app, "tournament", lv))
            else:
                self.msg, self.msg_t = f"LEVEL {lv.number} IS LOCKED - CLEAR LEVEL {lv.number - 1} FIRST", 2.5

    def update(self, dt: float) -> None:
        super().update(dt)
        self.stage.update(dt)
        self.msg_t = max(0.0, self.msg_t - dt)
        self.moved = max(0.0, self.moved - dt * 4)

    def _state(self, n: int) -> str:
        save = self.app.save
        return "cleared" if n in save.completed else "open" if save.level_unlocked(n) else "locked"

    @staticmethod
    def _diff_color(lv: TournamentLevel) -> RGB:
        return GOLD if lv.difficulty is Difficulty.MASTER else {Difficulty.EASY: Palette.OK, Difficulty.NORMAL: Palette.AMBER,
                                                               Difficulty.HARD: Palette.DANGER}[lv.difficulty]

    def _edge(self, st: str, act_col: RGB, selected: bool) -> RGB:
        edge = {"cleared": act_col, "open": mix(Palette.PRIMARY, (255, 255, 255), 0.25), "locked": (62, 76, 90)}[st]
        return mix(edge, Palette.WHITE, 0.35 + 0.25 * math.sin(self.app.time * 5)) if selected and st != "locked" else edge

    def _ribbon(self, screen: Screen, x0: int, y: int) -> None:
        n, t = len(TOURNAMENT), self.app.time
        px = [x0 + 3 + round(i * (self.W - 7) / (n - 1)) for i in range(n)]
        for i in range(n - 1):
            col = act_of(i + 1)[3] if (i + 1) in self.app.save.completed else (50, 62, 74)
            for x in range(px[i] + 1, px[i + 1]):
                screen.put(x, y + 1, "─" if col != (50, 62, 74) else "┄", col)
        for i, lv in enumerate(TOURNAMENT):
            st, act = self._state(lv.number), act_of(lv.number)
            final = lv.is_final
            if st == "cleared":
                ch, col = ("★" if final else "◆"), act[3]
            elif st == "open":
                ch, col = ("☆" if final else "◇"), mix(act[3], Palette.WHITE, 0.4 + 0.3 * math.sin(t * 4 + i))
            else:
                ch, col = "·", (70, 84, 98)
            sel = i == self.sel
            screen.put(px[i], y + 1, ch, Palette.WHITE if sel else col)
            if sel:
                screen.put(px[i], y, "▼", mix(act[3], Palette.WHITE, 0.5 + 0.4 * math.sin(t * 6)))
            num = str(lv.number)
            screen.text(px[i] - len(num) // 2, y + 2, num, Palette.WHITE if sel else (110, 124, 138) if st == "locked" else col)
            if lv.rule:
                screen.put(px[i], y + 3, "!", GOLD if st != "locked" else (96, 86, 50))

    def _mini(self, lv: TournamentLevel, locked: bool) -> PixelCanvas:
        cv = PixelCanvas(12, 8, Palette.PANEL)
        draw_tank(cv, 6.0, 1, 1, 45, (70, 82, 94) if locked else COLOR_BY_NAME[lv.boss_color],
                  design=DESIGN_BY_KEY[lv.tank], t=self.app.time)
        return cv

    def _cards(self, screen: Screen, x0: int, cy: int) -> None:
        n = len(TOURNAMENT)
        cx = x0 + (self.W - 36) // 2
        spots = {0: cx, -1: cx - 15, 1: cx + 37, -2: cx - 26, 2: cx + 52}
        for d in (-2, 2, -1, 1, 0):
            i = self.sel + d
            if not 0 <= i < n:
                continue
            lv, st = TOURNAMENT[i], self._state(i + 1)
            act = act_of(lv.number)
            w, h = self.CARD[abs(d)]
            x, y = spots[d], cy + (self.CARD[0][1] - h) // 2
            locked = st == "locked"
            edge = self._edge(st, act[3], d == 0)
            if d == 0:
                screen.box(x, y, w, h, "double", edge, Palette.PANEL, f"LEVEL {lv.number}", Palette.WHITE if not locked else Palette.MUTED)
                self.stage.set_kit(DESIGN_BY_KEY[lv.tank], COLOR_BY_NAME[lv.boss_color], AMMO_BY_KEY[lv.ammo],
                                   COLOR_BY_NAME[lv.boss_shot], 0.5 if locked else 0.0)
                screen.blit(self.stage.render(), x + 1, y + 1)
                badge = {"cleared": " ✓ CLEARED ", "open": " ▶ OPEN ", "locked": " ░ LOCKED "}[st]
                screen.text(x + w - len(badge) - 2, y + h - 1, badge, edge, Palette.PANEL)
                screen.text(x + 2, y + h - 1, f" {lv.boss} ", Palette.WHITE if not locked else Palette.MUTED, Palette.PANEL)
            elif abs(d) == 1:
                screen.box(x, y, w, h, "single", edge, Palette.PANEL)
                screen.center(y + 1, f"LV {lv.number}", Palette.TEXT if not locked else Palette.MUTED, Palette.PANEL, x, w)
                screen.blit(self._mini(lv, locked), x + 1, y + 2)
                screen.center(y + 6, lv.boss[:12], COLOR_BY_NAME[lv.boss_color] if not locked else (80, 92, 104), Palette.PANEL, x, w)
            else:
                screen.box(x, y, w, h, "single", edge, Palette.PANEL)
                screen.center(y + 1, f"LV {lv.number}", Palette.TEXT if not locked else Palette.MUTED, Palette.PANEL, x, w)
                dc = self._diff_color(lv)
                screen.center(y + 2, lv.difficulty.value, shade(dc, 0.45) if locked else dc, Palette.PANEL, x, w)
                screen.center(y + 3, {"cleared": "✓", "open": "▶", "locked": "░"}[st], edge, Palette.PANEL, x, w)
        mid = cy + 5
        for gx in (cx - 16, cx - 1, cx + 36, cx + 51):
            near_i = {cx - 16: self.sel - 2, cx - 1: self.sel - 1, cx + 36: self.sel, cx + 51: self.sel + 1}[gx]
            if 0 <= near_i < n - 1 or (gx == cx + 36 and near_i < n - 1):
                done = (near_i + 1) in self.app.save.completed
                screen.put(gx, mid, "━" if done else "┈", act_of(near_i + 1)[3] if done else (70, 84, 98))
        if self.sel > 2:
            screen.text(x0, mid, f"◂{self.sel - 2}", Palette.MUTED)
        if self.sel < n - 3:
            right = f"{n - 3 - self.sel}▸"
            screen.text(x0 + self.W - len(right), mid, right, Palette.MUTED)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        save, W = self.app.save, self.W
        x0, y0 = (screen.cols - W) // 2, max(1, (screen.rows - 26) // 2)
        lv = TOURNAMENT[self.sel]
        st = self._state(lv.number)
        act = act_of(lv.number)
        gold = lv.difficulty is Difficulty.MASTER
        screen.text(x0 + 1, y0, "T O U R N A M E N T", GOLD)
        title = f"{act[1]}  ·  {act[2]}"
        screen.text(x0 + (W - len(title)) // 2, y0, title, act[3])
        done = f"{len(save.completed)}/{len(TOURNAMENT)} CLEARED"
        screen.text(x0 + W - 1 - len(done), y0, done, Palette.OK if len(save.completed) == len(TOURNAMENT) else Palette.TEXT)
        self._ribbon(screen, x0, y0 + 1)
        self._cards(screen, x0, y0 + 5)
        # detail panel
        py = y0 + 16
        screen.box(x0, py, W, 9, "double", mix(act[3], (0, 0, 0), 0.25) if not gold else GOLD, Palette.PANEL,
                   f"LEVEL {lv.number} - {lv.name}", act[3])
        ax, boss_col = x0 + 3, COLOR_BY_NAME[lv.boss_color]
        rows = [("BOSS", lv.boss, boss_col), ("AI", lv.difficulty.value, self._diff_color(lv)), ("GOAL", lv.objective, Palette.TEXT),
                ("RULE", lv.rule_tag, GOLD if lv.rule else Palette.MUTED)]
        for k, (lab, val, col) in enumerate(rows):
            screen.text(ax, py + 1 + k, f"{lab:<5}", Palette.MUTED, Palette.PANEL)
            screen.text(ax + 6, py + 1 + k, val, col, Palette.PANEL)
        screen.text(ax, py + 5, lv.rule_text, GOLD if lv.rule else Palette.MUTED, Palette.PANEL)
        status = {"cleared": ("✓ CLEARED - REPLAY ANY TIME", Palette.OK), "open": ("▶ READY TO FIGHT", Palette.PRIMARY),
                  "locked": (f"░ LOCKED - CLEAR LEVEL {lv.number - 1} FIRST", Palette.MUTED)}[st]
        screen.text(ax, py + 7, status[0], status[1], Palette.PANEL)
        mx = x0 + 37
        for k, line in enumerate(textwrap.wrap(lv.blurb, 28)[:2]):
            screen.text(mx, py + 1 + k, line, Palette.TEXT, Palette.PANEL)
        tank, ammo = DESIGN_BY_KEY[lv.tank], AMMO_BY_KEY[lv.ammo]
        screen.text(mx, py + 3, f"TANK  {tank.name}", Palette.TEXT, Palette.PANEL)
        screen.text(mx, py + 4, f"AMMO  {ammo.name}", Palette.AMBER, Palette.PANEL)
        if lv.map_key:
            m = SPECIAL_MAP_BY_KEY[lv.map_key]
            screen.text(mx, py + 5, f"MAP   {m.name}", m.accent, Palette.PANEL)
        label, pay = payout_state(lv, lv.number in save.completed)
        screen.text(mx, py + 6, f"{label} {pay.coins} ◉" + (f" {pay.credits} ◈" if pay.credits else ""),
                    GOLD if label == "FIRST CLEAR" else Palette.MUTED, Palette.PANEL)
        rx = x0 + 68
        screen.text(rx, py + 1, "REWARDS", GOLD, Palette.PANEL)
        earned = lv.number in save.completed
        for k, (lab, name) in enumerate(reward_lines(lv, True)):
            screen.text(rx, py + 2 + k, ("✓ " if earned else "· ") + f"{lab:<8}" + name[:13],
                        Palette.OK if earned else (Palette.TEXT if st != "locked" else Palette.MUTED), Palette.PANEL)
        if self.msg_t > 0:
            screen.center(y0 + 25, self.msg, Palette.DANGER)
        else:
            draw_keycaps(screen, screen.cols // 2 - 28, y0 + 25,
                         (("A/D", "LEVEL"), ("SHIFT", "JUMP 5"), ("ENTER", "FIGHT / REPLAY"), ("ESC", "BACK")))


class TournamentResultScene(BackdropScene):
    """Level complete / failed screen with a staged reveal of every unlock."""

    def music(self):
        return (self.app.last_battle_song, "result") if self.app.last_battle_song else None

    def __init__(self, app, session: TournamentSession) -> None:
        super().__init__(app)
        self.session, self.level = session, session.level
        self.t = 0.0
        self.stage = PreviewStage(app.settings, 40, 26, 2)

    @property
    def fresh(self) -> bool:
        return self.session.completed and self.session.first_clear

    def enter(self) -> None:
        self.app._wallet_flash = 1.6
        if self.fresh:
            lv = self.level
            self.app.backdrop.celebrate_with([COLOR_BY_NAME[lv.boss_color], COLOR_BY_NAME[lv.boss_shot], Palette.WHITE])

    def exit(self) -> None:
        self.app.backdrop.celebrate_with(None)

    def handle(self, ev: InputEvent) -> None:
        if ev.raw in ("r", "R") and not self.session.completed:      # retry just this level, straight away
            self.session.restart(self.app)
        elif ev.action in (Action.CONFIRM, Action.FIRE):
            n = self.level.number
            nxt = n + 1 if (self.session.completed and n < len(TOURNAMENT)) else n
            go = lambda: self.app.goto(TournamentScene(self.app, nxt))
            if self.session.completed and n == len(TOURNAMENT):
                whisper(self.app, "master", go)
            else:
                go()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.t += dt
        self.stage.update(dt)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        s, lv, t = self.session, self.level, self.t
        x, y = (screen.cols - 92) // 2, (screen.rows - 24) // 2
        boss_col = COLOR_BY_NAME[lv.boss_color]
        gold = lv.difficulty is Difficulty.MASTER
        ok = s.completed
        edge = (GOLD if gold else Palette.OK) if ok else Palette.DANGER
        screen.box(x, y, 46, 24, "double", edge, Palette.PANEL, "REWARD KIT" if ok else "BOSS KIT")
        self.stage.set_kit(DESIGN_BY_KEY[lv.tank], boss_col, AMMO_BY_KEY[lv.ammo], COLOR_BY_NAME[lv.boss_shot], 0.0 if ok else 0.5)
        screen.blit(self.stage.render(), x + 3, y + 2)          # 40px canvas centred in the 44-col box
        screen.center(y + 16, f"{DESIGN_BY_KEY[lv.tank].name}  +  {AMMO_BY_KEY[lv.ammo].name}", Palette.TEXT, Palette.PANEL, x, 46)
        n1 = wrap_center(screen, y + 18, DESIGN_BY_KEY[lv.tank].blurb, 42, Palette.MUTED, Palette.PANEL, x, 46, 2)
        wrap_center(screen, y + 18 + n1, AMMO_BY_KEY[lv.ammo].blurb, 42, Palette.MUTED, Palette.PANEL, x, 46, 2)
        rx = x + 46
        screen.box(rx, y, 46, 24, "double", edge, Palette.PANEL, f"LEVEL {lv.number}")
        if ok:
            head = "L E V E L   C L E A R E D"
            prism_text(screen, rx + (46 - len(head)) // 2, y + 2, head, t, 0.12, 0.05, 0.55, 1.0, Palette.PANEL)
            screen.center(y + 4, f"{lv.boss} DEFEATED", boss_col, Palette.PANEL, rx, 46)
            screen.center(y + 5, f"{s.wins[0]} ROUNDS WON  ·  BOSS {s.wins[1]}", Palette.MUTED, Palette.PANEL, rx, 46)
            if s.payout:
                screen.center(y + 6, ("FIRST CLEAR  " if self.fresh else "REPLAY  ") + s.payout.text(), GOLD, Palette.PANEL, rx, 46)
            items = reward_lines(lv) if self.fresh else []
            if not self.fresh:
                screen.center(y + 9, "REWARDS ALREADY UNLOCKED", Palette.TEXT, Palette.PANEL, rx, 46)
            for k, (lab, name) in enumerate(items):
                a = clamp((t - 0.9 - k * 0.7) / 0.4, 0, 1)
                if a <= 0:
                    continue
                col = mix(Palette.PANEL, GOLD if gold else Palette.AMBER, a)
                suffix = "ACTIVATED" if lab == "MASTER HOME SCREEN" else "UNLOCKED"
                screen.text(rx + 4, y + 8 + k * 2, f"✓ {lab} {suffix}", mix(Palette.PANEL, Palette.OK, a), Palette.PANEL)
                screen.text(rx + 6, y + 9 + k * 2, name, col, Palette.PANEL)
            if self.fresh and lv.number == len(TOURNAMENT) and t > 4.8:
                screen.center(y + 20, "Press H on the title or menu to switch home screens", Palette.MUTED, Palette.PANEL, rx, 46)
        else:
            screen.center(y + 3, "L E V E L   F A I L E D", Palette.DANGER, Palette.PANEL, rx, 46)
            screen.center(y + 5, "YOU LOST A ROUND" if lv.fail_at == 1 else f"{lv.boss} WON {lv.fail_at} ROUNDS", boss_col, Palette.PANEL, rx, 46)
            screen.center(y + 7, f"YOU HAD {s.wins[0]}/{lv.wins} ROUND WINS", Palette.TEXT, Palette.PANEL, rx, 46)
            screen.center(y + 10, "ONLY THIS LEVEL RESTARTS", Palette.AMBER, Palette.PANEL, rx, 46)
            screen.center(y + 11, "ALL OTHER PROGRESS IS SAFE", Palette.MUTED, Palette.PANEL, rx, 46)
            if s.payout:
                screen.center(y + 14, "CONSOLATION  " + s.payout.text(), GOLD, Palette.PANEL, rx, 46)
        if int(t * 2) % 2 == 0 and t > 0.6:
            text = "[ ENTER ] CONTINUE" if ok else "[ ENTER ] ROADMAP     [ R ] RETRY LEVEL"
            screen.center(y + 22, text, Palette.PRIMARY, Palette.PANEL, rx, 46)
