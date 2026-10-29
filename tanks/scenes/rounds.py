"""Between rounds: the next-map picker, waiting for the LAN partner and the round result."""
from __future__ import annotations

from tanks.colors import Palette, clamp
from tanks.content.maps import MAPS, all_maps
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.match.sessions import MatchSession
from tanks.scenes.base import BackdropScene, Scene
from tanks.scenes.battle import BattleScene, ConfirmLeaveScene
from tanks.scenes.lan import NetNoticeScene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import panel, render_map_preview, wrap_center


class RoundMapScene(BackdropScene):
    """After a round the loser picks the next battlefield: numbered list + live terrain scan. LAN: sent to the opponent."""
    VISIBLE = 17

    def __init__(self, app, session: MatchSession, picker: int) -> None:
        super().__init__(app)
        self.session, self.picker, self.cache = session, picker, {}
        self.maps = [None] + list(MAPS) + app.save.unlocked_maps()          # None = RANDOM
        self.index = 0

    def handle(self, ev: InputEvent) -> None:
        n = len(self.maps)
        if ev.action is Action.UP:
            self.index = (self.index - 1) % n
        elif ev.action is Action.DOWN:
            self.index = (self.index + 1) % n
        elif ev.action is Action.LEFT:
            self.index = max(0, self.index - 8)
        elif ev.action is Action.RIGHT:
            self.index = min(n - 1, self.index + 8)
        elif ev.confirm:
            m = self.maps[self.index]
            net = self.session.config.net
            if net is not None:
                net.send({"t": "map", "key": m.key if m else ""})
            self.session.pending_map = m
            self.session.advance()
            self.app.goto(BattleScene(self.app, self.session))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        s = self.session
        who = s.team_name(self.picker) if s.config.mode != "single" else "YOU"
        n = len(self.maps)
        x, y = (screen.cols - 88) // 2, max(0, (screen.rows - 24) // 2)
        screen.box(x, y, 34, 24, "double", Palette.LINE, Palette.PANEL, "NEXT BATTLEFIELD")
        screen.center(y + 1, f"{who[:20]} PICK{'S' if who != 'YOU' else ''}", Palette.AMBER, Palette.PANEL, x, 34)
        top = int(clamp(self.index - self.VISIBLE // 2, 0, max(0, n - self.VISIBLE)))
        for row in range(min(self.VISIBLE, n)):
            i = top + row
            sel, m = i == self.index, self.maps[i]
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            name = "RANDOM" if m is None else (f"{i:03d} {m.name}" if not m.special else f"{i:03d} ★ {m.name}")
            col = Palette.WHITE if sel else (m.accent if (m and m.special) else Palette.AMBER if m is None else Palette.MUTED)
            screen.fill(x + 2, y + 3 + row, 30, 1, bg)
            screen.text(x + 3, y + 3 + row, ("▶ " if sel else "  ") + name[:27], col, bg)
        if top > 0:
            screen.put(x + 31, y + 3, "▲", Palette.PRIMARY_DIM, Palette.PANEL)
        if top + self.VISIBLE < n:
            screen.put(x + 31, y + 2 + self.VISIBLE, "▼", Palette.PRIMARY_DIM, Palette.PANEL)
        screen.center(y + 21, f"{self.index:03d}/{n - 1}  ·  A/D PAGE  ·  ENTER PICK", Palette.MUTED, Palette.PANEL, x, 34)
        px = x + 36
        screen.box(px, y, 52, 24, "double", Palette.LINE, Palette.PANEL, "TERRAIN SCAN")
        m = self.maps[self.index] or MAPS[int(self.app.time / 1.2) % len(MAPS)]
        pl = [(DESIGN_BY_KEY[p.design], p.tank_color) for p in s.config.players[:2]]
        screen.blit(render_map_preview(self.cache, m, 46, 24, self.app.time, pl), px + 3, y + 2)
        screen.center(y + 15, (f"{self.index:03d}/{n - 1}  " if self.index else "") + (m.name if self.index else "RANDOM"),
                      m.accent if (self.index and m.special) else Palette.AMBER, Palette.PANEL, px, 52)
        wrap_center(screen, y + 16, m.description if self.index else "A fresh battlefield.", 48, Palette.TEXT, Palette.PANEL, px, 52, 3)
        if self.index:
            dots = lambda k: "●" * k + "○" * (3 - k)
            screen.center(y + 20, f"COVER {dots(m.cover)}     RELIEF {dots(m.relief)}", Palette.PRIMARY, Palette.PANEL, px, 52)


class RoundMapWaitScene(BackdropScene):
    """LAN: the other player lost the round and is choosing the next battlefield."""

    def __init__(self, app, session: MatchSession, picker: int) -> None:
        super().__init__(app)
        self.session, self.picker, self.net = session, picker, session.config.net

    def update(self, dt: float) -> None:
        super().update(dt)
        self.net.pump()
        if self.net.take("quit") or self.net.dead:
            self.net.close()
            self.app.goto(NetNoticeScene(self.app, "OPPONENT LEFT", "The other player left the match."))
            return
        msgs = self.net.take("map")
        if msgs:
            self.session.pending_map = all_maps().get(str(msgs[-1].get("key", "")))
            self.session.advance()
            self.app.goto(BattleScene(self.app, self.session))

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK:
            self.app.push(ConfirmLeaveScene(self.app, self.session))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        x, y = panel(screen, 52, 9, "NEXT BATTLEFIELD")
        screen.center(y + 3, f"{self.session.team_name(self.picker)} IS CHOOSING THE NEXT MAP", Palette.AMBER, Palette.PANEL, x, 52)
        dots = "." * (1 + int(self.app.time * 2) % 3)
        screen.center(y + 5, "WAITING" + dots, Palette.MUTED, Palette.PANEL, x, 52)


class RoundResultScene(Scene):
    overlay = True

    def music(self):
        return (self.app.last_battle_song, "result") if self.app.last_battle_song else None

    def __init__(self, app, battle: BattleScene) -> None:
        super().__init__(app)
        self.battle = battle
        self.session = battle.session
        try:
            won = 1 - battle.doomed.team
            mine = {t.team for t in battle.world.tanks if battle._control(t) == "local"}
            good = len(mine) != 1 or won in mine
            app.sfx(("match_" if self.session.over else "round_") + ("win" if good else "lose"), 1.0)
        except Exception:
            pass

        self.net = battle.session.config.net
        self.ready_me = self.ready_peer = self.moved = False

    def _proceed(self) -> None:
        if self.moved:
            return
        self.moved = True
        if self.session.over:
            self.app.goto(self.session.finish_scene(self.app))
            return
        s, cfg = self.session, self.session.config
        if cfg.pick_maps and type(s) is MatchSession and cfg.mode in ("single", "two", "lan"):
            loser = self.battle.doomed.team
            if cfg.mode == "lan":
                if loser == cfg.my_owner:
                    self.app.goto(RoundMapScene(self.app, s, loser))
                else:
                    self.app.goto(RoundMapWaitScene(self.app, s, loser))
                return
            if cfg.mode in ("two", "single") or loser == 0:
                self.app.goto(RoundMapScene(self.app, s, loser))
                return
        s.advance()
        self.app.goto(s.interlude(self.app) or BattleScene(self.app, s))

    def update(self, dt: float) -> None:
        if self.net is not None:
            self.net.pump()
            if self.net.take("quit") or self.net.dead:
                self.net.close()
                self.app.goto(NetNoticeScene(self.app, "OPPONENT LEFT", "The other player left the match."))
                return
            if self.net.take("ready"):
                self.ready_peer = True
            if self.ready_me and self.ready_peer:
                self._proceed()

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK and self.session.config.mode in ("two", "lan"):
            self.app.push(ConfirmLeaveScene(self.app, self.session))
            return
        if ev.action is Action.CONFIRM or ev.action is Action.FIRE:
            if self.net is None:
                self._proceed()
            elif not self.ready_me:
                self.ready_me = True
                self.net.send({"t": "ready"})

    def draw(self, screen: Screen) -> None:
        screen.dim(0.5)
        s = self.session
        winner = 1 - self.battle.doomed.team
        info = s.round_summary(winner)
        pl = (s.team_players(winner) or s.config.players)[0]
        x, y = panel(screen, 52, 13, info["title"], fg=pl.tank_color)
        screen.center(y + 2, info["headline"], pl.tank_color, Palette.PANEL, x, 52)
        screen.center(y + 4, info["score"], Palette.WHITE, Palette.PANEL, x, 52)
        screen.center(y + 5, info["sub"], Palette.MUTED, Palette.PANEL, x, 52)
        screen.center(y + 8, info["next"], Palette.AMBER if s.over else Palette.TEXT, Palette.PANEL, x, 52)
        if self.net is not None and self.ready_me and not self.ready_peer:
            screen.center(y + 10, "WAITING FOR THE OTHER PLAYER...", Palette.AMBER, Palette.PANEL, x, 52)
        elif int(self.app.time * 2) % 2 == 0:
            screen.center(y + 10, "[ ENTER ]", Palette.PRIMARY, Palette.PANEL, x, 52)
