"""The MISSIONS map, the co-op choice and the mission result."""
from __future__ import annotations

import math
import textwrap
from typing import Optional

from tanks.art.backdrops import prism_text
from tanks.art.projectiles import draw_ufo
from tanks.art.tanks import draw_tank
from tanks.battle.tank import Tank
from tanks.colors import GOLD, Palette, RGB, clamp, mix, shade
from tanks.config import IS_WEB
from tanks.content.missions import MISSIONS, Mission
from tanks.content.paints import COLOR_BY_NAME
from tanks.content.rewards import reward_label
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.content.tournament import TOURNAMENT
from tanks.match.lan import player_to_json
from tanks.match.sessions import MissionSession, build_mission_session, humans_for
from tanks.net import WEB_LAN_TEXT, field_size
from tanks.scenes.base import BackdropScene
from tanks.scenes.lan import LanHostScene, NetNoticeScene
from tanks.scenes.main_menu import MenuScene
from tanks.scenes.setup import SetupScene
from tanks.scenes.story import whisper
from tanks.screen import PixelCanvas, Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import MenuList, draw_keycaps, panel


M_ACTS = ((1, "ACT I", "BASIC TRAINING", (120, 225, 150)), (11, "ACT II", "THE FIELD", (255, 190, 90)),
          (21, "ACT III", "HOT ZONES", (255, 120, 100)), (31, "ACT IV", "THE ELITE", (130, 190, 255)),
          (41, "ACT V", "THE ALIEN THREAT", (120, 255, 200)))
M_TYPE_COLORS = {"marathon": (130, 225, 140), "2v1": (255, 180, 90), "ufo": (120, 255, 200), "coop": (130, 190, 255),
                 "rush": (255, 110, 100), "mother": GOLD}
M_TYPE_SHORT = {"marathon": "RUN", "2v1": "2v1", "ufo": "UFO", "coop": "CO-OP", "rush": "RUSH", "mother": "BOSS"}


def _fake_tank(i: int, color: RGB, x: float, y: float, facing: int, **kw) -> Tank:
    return Tank(i, "", "", color, (255, 255, 255), False, x, y, facing, 50.0 if facing > 0 else 130.0, **kw)


def mission_art(m: Mission, t: float, locked: bool) -> PixelCanvas:
    """The picture on a mission's roadmap card: the kind of fight it is."""
    cv = PixelCanvas(34, 16, (0, 0, 0))
    for py in range(16):
        cv.rows[py] = [mix((6, 10, 24), (30, 40, 70), py / 15)] * 34
    for x in range(34):
        for y in range(3):
            cv.plot(x, y, (40, 60, 50) if not locked else (40, 46, 52))
    dim = (70, 80, 92)
    pc = lambda c: dim if locked else c
    ally, foe = (110, 200, 235), (235, 120, 100)
    if m.kind in ("ufo", "mother") or (m.kind == "coop" and m.coop_ufo):
        big = 2.2 if m.kind == "mother" else 2.0
        u = _fake_tank(0, pc((90, 230, 160)), 25.0, 7.0, -1, kind="ufo", scale=big, hover=4.0, hp=5, max_hp=5,
                       shield=1 if m.kind != "ufo" else 0)
        draw_ufo(cv, u, t)
        if m.kind == "mother":
            for k in range(2):
                d = _fake_tank(k + 1, pc((190, 140, 255)), 8.0 + k * 9, 9.0, -1, kind="ufo", scale=1.3, hover=0, hp=1, max_hp=1)
                draw_ufo(cv, d, t + k)
        if m.is_coop:
            draw_tank(cv, 4.0, 3, 1, 55, pc(ally), t=t)
            draw_tank(cv, 11.0, 3, 1, 55, pc((235, 200, 110)), t=t)
        elif m.kind == "ufo":
            draw_tank(cv, 6.0, 3, 1, 60, pc(ally), t=t)
    elif m.kind == "marathon":
        for k in range(3):
            draw_tank(cv, 5.0 + k * 8, 3, 1, 50, pc(mix(ally, (255, 255, 255), 0.15 * k)), t=t)
        draw_tank(cv, 29.0, 3, -1, 130, pc(foe), t=t)
        cv.plotf(18, 12, pc(GOLD))
    elif m.kind == "rush":
        for k, lvn in enumerate(m.levels[:4] if len(m.levels) > 4 else m.levels):
            lv = TOURNAMENT[lvn - 1]
            draw_tank(cv, 5.0 + k * 8.5, 3, -1 if k else 1, 130, pc(COLOR_BY_NAME[lv.boss_color]), design=DESIGN_BY_KEY[lv.tank], t=t)
    else:
        draw_tank(cv, 5.0, 3, 1, 50, pc(ally), t=t)
        if m.is_coop:
            draw_tank(cv, 13.0, 3, 1, 50, pc((235, 200, 110)), t=t)
        for k in range(m.enemies):
            draw_tank(cv, 29.0 - k * 9, 3, -1, 130, pc(foe if k == 0 else (235, 170, 90)), t=t)
    return cv


class MissionsScene(BackdropScene):
    """The mission roadmap: a 50-pip progress ribbon, five cards around the selected mission and a detail panel."""
    W = 94
    CARD = ((36, 10), (14, 8), (10, 6))

    def __init__(self, app, selected: Optional[int] = None) -> None:
        super().__init__(app)
        save = app.save
        if selected is None:
            todo = [m.number for m in MISSIONS if save.mission_unlocked(m.number) and m.number not in save.mission_completed]
            selected = todo[0] if todo else len(MISSIONS)
        self.sel = selected - 1
        self.msg, self.msg_t = "", 0.0

    def handle(self, ev: InputEvent) -> None:
        n, step = len(MISSIONS), (5 if ev.coarse else 1)
        if ev.action is Action.BACK:
            self.app.goto(MenuScene(self.app))
        elif ev.action in (Action.LEFT, Action.UP):
            self.sel = max(0, self.sel - step)
        elif ev.action in (Action.RIGHT, Action.DOWN):
            self.sel = min(n - 1, self.sel + step)
        elif ev.confirm:
            m = MISSIONS[self.sel]
            if not self.app.save.mission_unlocked(m.number):
                self.msg, self.msg_t = f"MISSION {m.number} IS LOCKED - CLEAR MISSION {m.number - 1} FIRST", 2.5
            elif m.is_coop:
                self.app.goto(CoopChoiceScene(self.app, m))
            else:
                scene = SetupScene(self.app, "mission", pages=1, done=lambda los, m=m: build_mission_session(self.app, m, los))
                scene.back = MissionsScene(self.app, m.number)
                self.app.goto(scene)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.msg_t = max(0.0, self.msg_t - dt)

    def _state(self, n: int) -> str:
        s = self.app.save
        return "cleared" if n in s.mission_completed else "open" if s.mission_unlocked(n) else "locked"

    @staticmethod
    def _act(n: int) -> tuple:
        return [a for a in M_ACTS if a[0] <= n][-1]

    def _ribbon(self, screen: Screen, x0: int, y: int) -> None:
        """50 pips in two evenly spaced rows of 25 (3 columns apart); the selected one is bracketed."""
        n, t = len(MISSIONS), self.app.time
        per, stride = (n + 1) // 2, 3
        start = x0 + (self.W - per * stride) // 2 + 1
        for i, m in enumerate(MISSIONS):
            st = self._state(m.number)
            col = M_TYPE_COLORS[m.kind]
            if st == "cleared":
                ch, c = "◆", col
            elif st == "open":
                ch, c = "◇", mix(col, Palette.WHITE, 0.4 + 0.3 * math.sin(t * 4 + i))
            else:
                ch, c = "·", (70, 84, 98)
            if m.rewards and st != "locked":
                ch = "★" if st == "cleared" else "☆"
            row, k = divmod(i, per)
            px, py = start + k * stride, y + row
            if i == self.sel:
                hl = mix(col, Palette.WHITE, 0.5 + 0.4 * math.sin(t * 6))
                screen.put(px - 1, py, "[", hl)
                screen.put(px + 1, py, "]", hl)
                screen.put(px, py, ch, Palette.WHITE)
            else:
                screen.put(px, py, ch, c)
        for row, (a, b) in enumerate(((1, per), (per + 1, n))):
            screen.text(x0 + 1, y + row, f"{a:02d}", (110, 124, 138))
            screen.text(x0 + self.W - 3, y + row, f"{b:02d}", (110, 124, 138))

    def _cards(self, screen: Screen, x0: int, cy: int) -> None:
        n, t = len(MISSIONS), self.app.time
        cx = x0 + (self.W - 36) // 2
        spots = {0: cx, -1: cx - 15, 1: cx + 37, -2: cx - 26, 2: cx + 52}
        for d in (-2, 2, -1, 1, 0):
            i = self.sel + d
            if not 0 <= i < n:
                continue
            m, st = MISSIONS[i], self._state(i + 1)
            col, locked = M_TYPE_COLORS[m.kind], st == "locked"
            w, h = self.CARD[abs(d)]
            x, y = spots[d], cy + (self.CARD[0][1] - h) // 2
            edge = {"cleared": col, "open": mix(Palette.PRIMARY, (255, 255, 255), 0.25), "locked": (62, 76, 90)}[st]
            if d == 0 and st != "locked":
                edge = mix(edge, Palette.WHITE, 0.35 + 0.25 * math.sin(t * 5))
            if d == 0:
                screen.box(x, y, w, h, "double", edge, Palette.PANEL, f"MISSION {m.number}", Palette.WHITE if not locked else Palette.MUTED)
                screen.blit(mission_art(m, t, locked), x + 1, y + 1)
                badge = {"cleared": " ✓ CLEARED ", "open": " ▶ OPEN ", "locked": " ░ LOCKED "}[st]
                screen.text(x + w - len(badge) - 2, y + h - 1, badge, edge, Palette.PANEL)
                screen.text(x + 2, y + h - 1, f" {m.type_name} ", col if not locked else Palette.MUTED, Palette.PANEL)
            else:
                screen.box(x, y, w, h, "single", edge, Palette.PANEL)
                screen.center(y + 1, f"M{m.number}", Palette.TEXT if not locked else Palette.MUTED, Palette.PANEL, x, w)
                screen.center(y + 2, M_TYPE_SHORT[m.kind], shade(col, 0.45) if locked else col, Palette.PANEL, x, w)
                screen.center(y + 3, {"cleared": "✓", "open": "▶", "locked": "░"}[st], edge, Palette.PANEL, x, w)
                if abs(d) == 1:
                    for k, ln in enumerate(textwrap.wrap(m.name, w - 2)[:2]):
                        screen.center(y + 4 + k, ln, (80, 92, 104) if locked else Palette.TEXT, Palette.PANEL, x, w)
                    if m.rewards:
                        screen.center(y + 6, "★ REWARD", GOLD if not locked else (96, 86, 50), Palette.PANEL, x, w)
        if self.sel > 2:
            screen.text(x0, cy + 5, f"◂{self.sel - 2}", Palette.MUTED)
        if self.sel < n - 3:
            right = f"{n - 3 - self.sel}▸"
            screen.text(x0 + self.W - len(right), cy + 5, right, Palette.MUTED)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        save, W = self.app.save, self.W
        x0, y0 = (screen.cols - W) // 2, max(1, (screen.rows - 26) // 2)
        m = MISSIONS[self.sel]
        st, act, col = self._state(m.number), self._act(m.number), M_TYPE_COLORS[m.kind]
        screen.text(x0 + 1, y0, "M I S S I O N S", GOLD)
        title = f"{act[1]}  ·  {act[2]}"
        screen.text(x0 + (W - len(title)) // 2, y0, title, act[3])
        done = f"{len(save.mission_completed)}/{len(MISSIONS)} CLEARED"
        screen.text(x0 + W - 1 - len(done), y0, done, Palette.OK if len(save.mission_completed) == len(MISSIONS) else Palette.TEXT)
        self._ribbon(screen, x0, y0 + 1)
        self._cards(screen, x0, y0 + 4)
        py = y0 + 14
        screen.box(x0, py, W, 11, "double", mix(col, (0, 0, 0), 0.3), Palette.PANEL, f"MISSION {m.number} - {m.name}", col)
        ax = x0 + 3
        foe = {"marathon": f"{m.stages} AI RIVALS", "2v1": "2 AI TANKS", "ufo": "1 ALIEN SAUCER", "coop": "2 AI TANKS" if not m.coop_ufo else "1 ALIEN SAUCER",
               "rush": f"{m.stages} TOURNAMENT BOSSES", "mother": "MOTHERSHIP + 2 DRONES"}[m.kind]
        rows = [("TYPE", m.type_name, col), ("FOES", foe, Palette.TEXT)]
        for k, (lab, val, c) in enumerate(rows):
            screen.text(ax, py + 1 + k, f"{lab:<5}", Palette.MUTED, Palette.PANEL)
            screen.text(ax + 6, py + 1 + k, val, c, Palette.PANEL)
        goal = textwrap.wrap(m.objective, 30)[:2]
        screen.text(ax, py + 3, "GOAL", Palette.MUTED, Palette.PANEL)
        for k, ln in enumerate(goal):
            screen.text(ax + 6, py + 3 + k, ln, Palette.TEXT, Palette.PANEL)
        ai = m.diff.value if m.kind != "marathon" or m.diff is m.diff_end else f"{m.diff.value} > {m.diff_end.value}"
        screen.text(ax, py + 5, "AI", Palette.MUTED, Palette.PANEL)
        screen.text(ax + 6, py + 5, ai, Palette.AMBER, Palette.PANEL)
        for k, ln in enumerate(textwrap.wrap(m.rule_text, 34)[:2]):
            screen.text(ax, py + 6 + k, ln, GOLD, Palette.PANEL)
        status = {"cleared": ("✓ CLEARED - REPLAY ANY TIME", Palette.OK), "open": ("▶ READY", Palette.PRIMARY),
                  "locked": (f"░ LOCKED - CLEAR MISSION {m.number - 1} FIRST", Palette.MUTED)}[st]
        screen.text(ax, py + 9, status[0][:36], status[1], Palette.PANEL)
        mx = x0 + 40
        for k, line in enumerate(textwrap.wrap(m.blurb, 28)[:5]):
            screen.text(mx, py + 1 + k, line, Palette.TEXT, Palette.PANEL)
        first_left = m.number not in save.mission_paid
        screen.text(mx, py + 7, f"{'FIRST CLEAR' if first_left else 'REPLAY'}  {m.first_coins if first_left else m.repeat_coins} ◉"
                    + (f"  +{m.first_credits} ◈" if first_left else ""),
                    GOLD if first_left else Palette.MUTED, Palette.PANEL)
        if m.is_coop:
            screen.text(mx, py + 9, "LOCAL · LAN · AI WINGMAN", (130, 190, 255), Palette.PANEL)
        rx = x0 + 70
        screen.text(rx, py + 1, "GRAND PRIZE" if m.number == len(MISSIONS) else "REWARDS", GOLD, Palette.PANEL)
        earned = m.number in save.mission_completed
        for k, uid in enumerate(m.rewards[:5]):
            lab, name = reward_label(uid)
            lab = {"SCREEN": "HOME"}.get(lab, lab)
            screen.text(rx, py + 2 + k, ("✓ " if earned else "· ") + f"{lab:<5}" + name, Palette.OK if earned else Palette.TEXT, Palette.PANEL)
        if not m.rewards:
            screen.text(rx, py + 2, "· COINS ONLY", Palette.MUTED, Palette.PANEL)
        if self.msg_t > 0:
            screen.center(y0 + 25, self.msg, Palette.DANGER)
        else:
            draw_keycaps(screen, screen.cols // 2 - 28, y0 + 25,
                         (("A/D", "MISSION"), ("SHIFT", "JUMP 5"), ("ENTER", "START"), ("ESC", "BACK")))


class CoopChoiceScene(BackdropScene):
    """How to play a co-op mission: two players on this machine, hosting a LAN game, or alone with an AI wingman."""

    def __init__(self, app, mission: Mission) -> None:
        super().__init__(app)
        self.m = mission
        self.menu = MenuList(["LOCAL TWO PLAYER", "HOST OVER LAN", "SOLO + AI WINGMAN", "BACK"])

    def handle(self, ev: InputEvent) -> None:
        app, m = self.app, self.m
        if ev.action is Action.BACK:
            app.goto(MissionsScene(app, m.number))
            return
        c = self.menu.handle(ev)
        if c == 0:
            sc = SetupScene(app, "mission", pages=2, done=lambda los: build_mission_session(app, m, los))
            sc.back = CoopChoiceScene(app, m)
            app.goto(sc)
        elif c == 1 and IS_WEB:
            app.goto(NetNoticeScene(app, "LAN DISABLED ON WEB", WEB_LAN_TEXT))
        elif c == 1:
            def after(los):
                def launch(app_, link, guest, guest_term):
                    mine = field_size(app_.screen.cols, app_.screen.rows)
                    world = (min(mine[0], guest_term[0]), min(mine[1], guest_term[1]))
                    seed = app_.rng.randrange(1 << 30)
                    humans = humans_for(app_, m, los, guest=guest)
                    link.send({"t": "start", "kind": "mission", "n": m.number, "players": [player_to_json(h) for h in humans],
                               "seed": seed, "world": list(world), "wind": app_.settings.wind})
                    build_mission_session(app_, m, los, net=link, my_owner=0, world=world, seed=seed, humans=humans)
                app.goto(LanHostScene(app, None, launch, f"CO-OP MISSION {m.number}"))
            sc = SetupScene(app, "mission", pages=1, done=after)
            sc.back = CoopChoiceScene(app, m)
            app.goto(sc)
        elif c == 2:
            sc = SetupScene(app, "mission", pages=1, done=lambda los: build_mission_session(app, m, los, wingman=True))
            sc.back = CoopChoiceScene(app, m)
            app.goto(sc)
        elif c == 3:                                  # (MenuList returns None for plain navigation keys: never treat that as BACK)
            app.goto(MissionsScene(app, m.number))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        x, y = panel(screen, 60, 16, f"CO-OP MISSION {self.m.number}: {self.m.name}")
        screen.center(y + 2, self.m.objective, Palette.TEXT, Palette.PANEL, x, 60)
        self.menu.draw(screen, screen.cols // 2, y + 5, self.app.time, gap=1, width=30)
        screen.center(y + 10, "LAN: both players earn coins and the kit;", Palette.MUTED, Palette.PANEL, x, 60)
        screen.center(y + 11, "only the host's mission progress advances.", Palette.MUTED, Palette.PANEL, x, 60)
        screen.center(y + 12, "LOCAL: the one save on this machine earns it all.", Palette.MUTED, Palette.PANEL, x, 60)


class MissionResultScene(BackdropScene):
    def music(self):
        return (self.app.last_battle_song, "result") if self.app.last_battle_song else None

    def __init__(self, app, session: MissionSession) -> None:
        super().__init__(app)
        self.session, self.m, self.t = session, session.mission, 0.0

    def enter(self) -> None:
        self.app._wallet_flash = 1.6
        if self.session.completed:
            self.app.backdrop.celebrate_with([M_TYPE_COLORS[self.m.kind], GOLD, Palette.WHITE])

    def exit(self) -> None:
        self.app.backdrop.celebrate_with(None)

    def handle(self, ev: InputEvent) -> None:
        s, net = self.session, self.session.config.net
        if ev.raw in ("r", "R") and not s.completed and net is None:
            s.restart(self.app)
        elif ev.confirm:
            if net is not None:
                net.send({"t": "quit"})
                net.close()
            nxt = self.m.number + 1 if (s.completed and self.m.number < len(MISSIONS) and net is None) else self.m.number
            go = lambda: self.app.goto(MissionsScene(self.app, nxt))
            m = self.m
            if net is not None:
                go()
            elif m.kind == "mother" and s.completed:
                whisper(self.app, "mothership", go)
            elif m.kind == "ufo" or (m.kind == "coop" and m.coop_ufo):
                whisper(self.app, "alien", go)
            else:
                go()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.t += dt

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        s, m, t = self.session, self.m, self.t
        ok = s.completed
        col = M_TYPE_COLORS[m.kind]
        x, y = panel(screen, 64, 20, f"MISSION {m.number}", fg=col if ok else Palette.DANGER)
        head = "M I S S I O N   C O M P L E T E" if ok else "M I S S I O N   F A I L E D"
        if ok:
            prism_text(screen, x + (64 - len(head)) // 2, y + 2, head, t, 0.12, 0.05, 0.55, 1.0, Palette.PANEL)
        else:
            screen.center(y + 2, head, Palette.DANGER, Palette.PANEL, x, 64)
        screen.center(y + 3, m.name, col, Palette.PANEL, x, 64)
        if s.payout:
            screen.center(y + 5, ("FIRST CLEAR  " if s.first_clear else "REPLAY  " if ok else "CONSOLATION  ") + s.payout.text(), GOLD,
                          Palette.PANEL, x, 64)
        if ok and s.first_clear and m.rewards:
            screen.center(y + 7, "GRAND PRIZE UNLOCKED" if m.number == len(MISSIONS) else "UNLOCKED", GOLD if m.number == len(MISSIONS) else Palette.OK,
                          Palette.PANEL, x, 64)
            for k, uid in enumerate(m.rewards):
                a = clamp((t - 0.6 - k * 0.5) / 0.4, 0, 1)
                if a > 0:
                    lab, name = reward_label(uid)
                    screen.center(y + 9 + k, f"{lab}: {name}", mix(Palette.PANEL, GOLD, a), Palette.PANEL, x, 64)
        elif ok:
            screen.center(y + 8, "ALREADY CLEARED - NO NEW REWARDS", Palette.MUTED, Palette.PANEL, x, 64)
        else:
            screen.center(y + 8, "ONLY THIS MISSION RESTARTS", Palette.AMBER, Palette.PANEL, x, 64)
        if int(t * 2) % 2 == 0 and t > 0.6:
            text = "[ ENTER ] CONTINUE" if ok else ("[ ENTER ] MISSIONS" if s.config.net else "[ ENTER ] MISSIONS     [ R ] RETRY")
            screen.center(y + 17, text, Palette.PRIMARY, Palette.PANEL, x, 64)
