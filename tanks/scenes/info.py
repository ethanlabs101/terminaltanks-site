"""HOW TO PLAY and LINKS."""
from __future__ import annotations

import textwrap

from tanks.colors import GOLD, Palette
from tanks.config import IS_WEB
from tanks.scenes.base import BackdropScene
from tanks.scenes.main_menu import MenuScene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import draw_keycaps, panel


class HowToScene(BackdropScene):
    page = 0
    AMMO_LINES = [
        ("WHAT IT IS", Palette.AMBER),
        ("Ammo marked ✦ in pilot setup has a real effect: it can bounce, split in flight, drop cluster bomblets, chain blasts, change gravity, speed, wind pull or blast size, and more. Plain ammo (STANDARD, TRACER, PLASMA...) only changes how shots look.", Palette.TEXT),
        ("WHEN IT WORKS", Palette.AMBER),
        ("Single Player: on by default - switch it ON/OFF in the Single Player rules. Two Player / LAN: when SPECIAL AMMO is ON in the match rules (the host decides in LAN). Terminal Tickets: always.", Palette.TEXT),
        ("WHEN IT DOES NOT", Palette.AMBER),
        ("Tournament and Missions: always off, so boss fights stay fair. Two Player / LAN with SPECIAL AMMO OFF. The 3-damage SPECIAL ATTACK (X) also skips the ammo's effect. SPECIAL ATTACK itself is a rule toggle in Single Player, Two Player and LAN.", Palette.TEXT),
        ("HOW YOU CAN TELL", Palette.AMBER),
        ("When it is off, the match banner says SPECIAL AMMO OFF and a note pops up over your tank on your first shot. The AI follows the same rules.", Palette.TEXT),
    ]

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK or (self.page == 1 and ev.action in (Action.CONFIRM, Action.FIRE)):
            self.app.goto(MenuScene(self.app))
        elif self.page == 0 and (ev.action in (Action.CONFIRM, Action.FIRE, Action.RIGHT) or ev.confirm):
            self.page = 1
        elif ev.action is Action.LEFT:
            self.page = 0

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        if self.page == 1:
            x, y = panel(screen, 76, 24, "HOW TO PLAY  ·  SPECIAL AMMO")
            row = y + 2
            for t_, c in self.AMMO_LINES:
                for ln in textwrap.wrap(t_, 66):
                    screen.text(x + 4, row, ln, c, Palette.PANEL)
                    row += 1
            screen.center(y + 22, "[ ◄ ] PAGE 1     [ ENTER ] BACK", Palette.PRIMARY_DIM, Palette.PANEL, x, 76)
            return
        x, y = panel(screen, 76, 24, "HOW TO PLAY")
        lines = [
            ('OBJECTIVE', Palette.AMBER),
            ('Destroy the enemy tank; every hit costs a heart. Terrain breaks.', Palette.TEXT),
            ('CONTROLS', Palette.AMBER),
            ('A / D  or  ◄ ►   rotate barrel (hold SHIFT for big steps)', Palette.TEXT),
            ('W / S  or  ▲ ▼   firing power        SPACE / ENTER   fire', Palette.TEXT),
            ('ESC / P   pause        SHIFT+A/D in pilot setup jumps 5 kits', Palette.TEXT),
            ('TIPS', Palette.AMBER),
            ('WIND pushes every shell: read the arrows. The guide ignores wind.', Palette.TEXT),
            ('A blast right beside a tank still counts as a hit.', Palette.TEXT),
            ('TWO PLAYER / LAN', Palette.AMBER),
            ('Pick BEST OF or FIRST TO n rounds and your hearts. LAN: one hosts,', Palette.TEXT),
            ("one joins on the same network; the host's rules apply.", Palette.TEXT),
            ('TOURNAMENT', Palette.AMBER),
            ('Twenty levels, each opened by the one before. Beat a boss to unlock', Palette.TEXT),
            ('its exact tank + ammo. Usually 2 strikes; some levels bend the rules.', Palette.TEXT),
            ('MISSIONS', Palette.AMBER),
            ('50 missions open after the Master: marathons, 2v1, UFOs and rushes.', Palette.TEXT),
            ('First clears pay coins and credits. Co-op: local, LAN or an AI wingman.', Palette.TEXT),
            ('SHOP', Palette.AMBER),
            ('Spend coins (◉) and tournament credits (◈) on kits, maps and screens.', Palette.TEXT),
        ]
        for i, (s, c) in enumerate(lines):
            screen.text(x + 4, y + 2 + i, s, c, Palette.PANEL)
        screen.center(y + 22, "[ ENTER / ► ] NEXT: SPECIAL AMMO     [ ESC ] BACK", Palette.PRIMARY_DIM, Palette.PANEL, x, 76)


class LinksScene(BackdropScene):
    """Where to find the source, the website and the other storefronts."""
    LINKS = (("SOURCE CODE", "github.com/ethanlabs101/TerminalTanks", True),
             ("WEBSITE REPO", "github.com/ethanlabs101/terminaltanks-site", True),
             ("WEBSITE", "ethanlabs101.github.io/terminaltanks-site", True),
             ("DS PORT", "github.com/ethanlabs101/TerminalTanks-DS", True),
             ("ALL PROJECTS", "github.com/ethanlabs101", True),
             ("ITCH.IO", "COMING SOON", False),
             ("STEAM", "COMING SOON", False))

    def __init__(self, app) -> None:
        super().__init__(app)
        self.row, self.msg, self.msg_t = 0, "", 0.0

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK:
            self.app.goto(MenuScene(self.app))
        elif ev.action is Action.UP:
            self.row = (self.row - 1) % len(self.LINKS)
        elif ev.action is Action.DOWN:
            self.row = (self.row + 1) % len(self.LINKS)
        elif ev.confirm:
            _, url, live = self.LINKS[self.row]
            if not live:
                self.msg, self.msg_t = "NOT LIVE YET - CHECK BACK SOON", 2.5
                return
            try:
                if IS_WEB:
                    import js                                    # Pyodide: let the page open the tab
                    js.window.open("https://" + url, "_blank")
                    ok = True
                else:
                    import webbrowser
                    ok = webbrowser.open("https://" + url)
            except Exception:
                ok = False
            self.msg, self.msg_t = ("OPENED IN YOUR BROWSER" if ok else "COULD NOT OPEN A BROWSER - TYPE THE ADDRESS"), 2.5

    def update(self, dt: float) -> None:
        super().update(dt)
        self.msg_t = max(0.0, self.msg_t - dt)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        w, h = 72, 23
        x, y = panel(screen, w, h, "TERMINAL TANKS  ·  FIND US")
        screen.center(y + 2, "Free, open source and built by one developer.", Palette.TEXT, Palette.PANEL, x, w)
        screen.center(y + 3, "Play it, read it, fork it, share it.", Palette.MUTED, Palette.PANEL, x, w)
        for i, (lab, url, live) in enumerate(self.LINKS):
            ry, sel = y + 5 + i * 2, i == self.row
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            screen.fill(x + 2, ry, w - 4, 1, bg)
            screen.text(x + 4, ry, lab, Palette.WHITE if sel else Palette.MUTED, bg)
            screen.text(x + 20, ry, url, (GOLD if sel else Palette.PRIMARY) if live else Palette.AMBER, bg)
        screen.center(y + 20, self.msg if self.msg_t > 0 else "More games from ethanlabs101 are on the way.",
                      Palette.OK if self.msg_t > 0 and "OPENED" in self.msg else (Palette.AMBER if self.msg_t > 0 else Palette.MUTED), Palette.PANEL, x, w)
        draw_keycaps(screen, x + 14, y + 21, (("W/S", "SELECT"), ("ENTER", "OPEN"), ("ESC", "BACK")), Palette.PANEL)
