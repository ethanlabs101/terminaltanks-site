"""Result screens for Terminal Tickets and ordinary matches."""
from __future__ import annotations

from typing import TYPE_CHECKING

from tanks.art.backdrops import prism_text
from tanks.colors import GOLD, Palette, clamp, mix
from tanks.content.paints import live_color
from tanks.content.rewards import reward_label
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.content.tickets import TICKET_BOSS_BY_KEY
from tanks.scenes.base import BackdropScene
from tanks.scenes.main_menu import MenuScene
from tanks.scenes.shop import ShopScene
from tanks.scenes.story import whisper
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import DIGITS, panel

if TYPE_CHECKING:
    from tanks.match.sessions import MatchSession, TicketSession


class TicketResultScene(BackdropScene):
    def music(self):
        return (self.app.last_battle_song, "result") if self.app.last_battle_song else None

    def __init__(self, app, session: "TicketSession") -> None:
        super().__init__(app)
        self.session, self.boss, self.t = session, session.boss, 0.0

    def enter(self) -> None:
        self.app._wallet_flash = 1.6
        if self.session.completed:
            self.app.backdrop.celebrate_with([DESIGN_BY_KEY[self.boss.tank].accent, GOLD, Palette.WHITE])

    def exit(self) -> None:
        self.app.backdrop.celebrate_with(None)

    def handle(self, ev: InputEvent) -> None:
        s = self.session
        if ev.raw in ("r", "R") and not s.completed:
            s.restart(self.app)
        elif ev.confirm:
            go = lambda: self.app.goto(ShopScene(self.app, 4))
            if s.completed and self.app.save.tickets_sold_out():
                whisper(self.app, "hoarders", go)
            else:
                go()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.t += dt

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        s, b, t = self.session, self.boss, self.t
        ok = s.completed
        col = DESIGN_BY_KEY[b.tank].accent
        x, y = panel(screen, 64, 20, "TERMINAL TICKET", fg=col if ok else Palette.DANGER)
        head = "B O S S   D E F E A T E D" if ok else "T I C K E T   B A T T L E   L O S T"
        if ok:
            prism_text(screen, x + (64 - len(head)) // 2, y + 2, head, t, 0.12, 0.05, 0.55, 1.0, Palette.PANEL)
        else:
            screen.center(y + 2, head, Palette.DANGER, Palette.PANEL, x, 64)
        screen.center(y + 3, b.name, col, Palette.PANEL, x, 64)
        if s.payout:
            screen.center(y + 5, ("VICTORY  " if ok else "CONSOLATION  ") + s.payout.text(), GOLD, Palette.PANEL, x, 64)
        if ok:
            screen.center(y + 7, "CLAIMED", Palette.OK, Palette.PANEL, x, 64)
            for k, uid in enumerate(b.reward_ids()):
                a = clamp((t - 0.6 - k * 0.5) / 0.4, 0, 1)
                if a > 0:
                    lab, name = reward_label(uid)
                    screen.center(y + 9 + k, f"{lab}: {name}", mix(Palette.PANEL, GOLD, a), Palette.PANEL, x, 64)
            left = len(TICKET_BOSS_BY_KEY) - len(self.app.save.tickets_won & set(TICKET_BOSS_BY_KEY))
            screen.center(y + 14, "ALL BOSSES DEFEATED - TICKETS SOLD OUT" if left == 0 else f"{left} BOSS{'ES' if left != 1 else ''} LEFT IN THE VAULT",
                          Palette.MUTED, Palette.PANEL, x, 64)
        else:
            screen.center(y + 8, "YOUR TICKET IS KEPT", Palette.AMBER, Palette.PANEL, x, 64)
            screen.center(y + 9, "RETRY ANY TIME - IT IS NOT WASTED", Palette.MUTED, Palette.PANEL, x, 64)
        if int(t * 2) % 2 == 0 and t > 0.6:
            screen.center(y + 17, "[ ENTER ] SHOP" if ok else "[ ENTER ] SHOP     [ R ] RETRY", Palette.PRIMARY, Palette.PANEL, x, 64)


class MatchResultScene(BackdropScene):
    def music(self):
        return (self.app.last_battle_song, "result") if self.app.last_battle_song else None

    def __init__(self, app, session: MatchSession) -> None:
        super().__init__(app)
        self.session = session

    def enter(self) -> None:
        self.app._wallet_flash = 1.6
        w = self.session.champion
        pl = (self.session.team_players(w) or self.session.config.players)[0]
        self.app.backdrop.celebrate_with([pl.tank_color, pl.shot_color, Palette.WHITE])

    def exit(self) -> None:
        self.app.backdrop.celebrate_with(None)

    def handle(self, ev: InputEvent) -> None:
        if ev.action in (Action.CONFIRM, Action.FIRE):
            net = self.session.config.net
            if net is not None:
                net.send({"t": "quit"})
                net.close()
            self.app.goto(MenuScene(self.app))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        s = self.session
        w = s.champion
        pl = (s.team_players(w) or s.config.players)[0]
        x, y = panel(screen, 46, 17, "MATCH COMPLETE", fg=live_color(pl.tank_color, self.app.time))
        screen.center(y + 2, f"{s.team_name(w)} WINS"[:42], pl.tank_color, Palette.PANEL, x, 46)
        a, b = str(s.wins[0]), str(s.wins[1])
        if len(a) == 1 and len(b) == 1:
            for r in range(5):
                line = DIGITS[a][r] + ("  ———  " if r == 2 else "       ") + DIGITS[b][r]
                screen.center(y + 4 + r, line, Palette.WHITE, Palette.PANEL, x, 46)
        else:
            screen.center(y + 6, f"{a}   —   {b}", Palette.WHITE, Palette.PANEL, x, 46)
        cfg, lw = s.config, s.wins[1 - w]
        label = cfg.label or f"FIRST TO {cfg.target}"
        if cfg.net is not None:                               # LAN: each machine hears it from its own player's side
            mine = cfg.my_owner
            won = w == mine
            head, hcol = ("VICTORY!", Palette.OK) if won else ("DEFEAT", Palette.DANGER)
            cond = f"{label}: YOU {'WON' if won else 'LOST'} {s.wins[mine]} TO {s.wins[1 - mine]}"
        elif cfg.single:
            won = w == 0
            head, hcol = ("VICTORY!", Palette.AMBER) if won else ("DEFEAT", Palette.DANGER)
            cond = f"{label}: {'YOU WON' if won else 'THE AI WON'} {s.wins[0]} TO {s.wins[1]}"
        else:
            head, hcol = f"{s.team_name(w)} WINS!", Palette.AMBER
            cond = f"{label}: {s.team_name(w)} WON {s.wins[w]} TO {lw}"
        screen.center(y + 10, head[:40], hcol, Palette.PANEL, x, 46)
        screen.center(y + 11, cond[:44], Palette.TEXT, Palette.PANEL, x, 46)
        if s.payout:
            screen.center(y + 13, s.payout.text(), GOLD, Palette.PANEL, x, 46)
        elif cfg.mode in ("two", "lan"):
            screen.center(y + 13, "TWO-PLAYER AND LAN MATCHES EARN NO COINS", Palette.MUTED, Palette.PANEL, x, 46)
        if int(self.app.time * 2) % 2 == 0:
            screen.center(y + 15, "[ ENTER ]", Palette.PRIMARY, Palette.PANEL, x, 46)
