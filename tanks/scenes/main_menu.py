"""The main menu: the hub that opens every mode and screen."""
from __future__ import annotations

import copy

from tanks.art.backdrops import (
    draw_master_logo, draw_master_menu, draw_secret_logo, draw_secret_menu, draw_theme_logo, draw_theme_menu
)
from tanks.colors import Palette
from tanks.config import IS_WEB
from tanks.content.homes import HOME_THEMES
from tanks.net import WEB_LAN_TEXT
from tanks.profiles import fmt_playtime
from tanks.scenes.title import HomeScene, TitleScene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import MenuList, draw_keycaps, draw_logo


class MenuScene(HomeScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.menu = MenuList(["SINGLE PLAYER", "TWO PLAYER", "LAN PLAY", "TOURNAMENT", "MISSIONS", "SHOP", "WORKSHOP", "HOW TO PLAY", "TUTORIAL", "JUKEBOX", "PROFILES", "SETTINGS", "CHEAT CODES", "LINKS", "QUIT"])

    def handle(self, ev: InputEvent) -> None:
        from tanks.scenes.info import HowToScene, LinksScene
        from tanks.scenes.jukebox import JukeboxScene
        from tanks.scenes.lan import LanMenuScene, NetNoticeScene, RulesScene
        from tanks.scenes.missions import MissionsScene
        from tanks.scenes.profiles import ProfilesScene
        from tanks.scenes.settings import CheatScene, SettingsScene
        from tanks.scenes.setup import SetupScene
        from tanks.scenes.shop import ShopScene
        from tanks.scenes.studio import WorkshopScene
        from tanks.scenes.tournament import TournamentScene
        from tanks.scenes.tutorial import TutorialScene
        if ev.raw in ("h", "H", "TAB"):
            self.toggle_home()
            return
        if ev.action is Action.BACK:
            self.app.goto(TitleScene(self.app))
            return
        choice = self.menu.handle(ev)
        if choice is None:
            return
        app, label = self.app, self.menu.items[choice]
        if label == "SINGLE PLAYER":
            def single_next(r):
                sc = SetupScene(app, "single", rules=r)
                sc.back = RulesScene(app, "SINGLE PLAYER RULES", single_next, kind="single")
                app.goto(sc)
            app.goto(RulesScene(app, "SINGLE PLAYER RULES", single_next, kind="single"))
        elif label == "TWO PLAYER":
            app.goto(RulesScene(app, "TWO PLAYER RULES", lambda r: app.goto(SetupScene(app, "two", rules=r)), kind="two"))
        elif label == "LAN PLAY":
            if IS_WEB:
                app.goto(NetNoticeScene(app, "LAN DISABLED ON WEB", WEB_LAN_TEXT))
            else:
                app.goto(LanMenuScene(app))
        elif label == "TOURNAMENT":
            app.goto(TournamentScene(app))
        elif label == "MISSIONS":
            if app.save.missions_open():
                app.goto(MissionsScene(app))
            else:
                app.goto(NetNoticeScene(app, "MISSIONS LOCKED", "Missions open once you defeat the Master in Tournament mode (Level 20). "
                                                                "Your Tournament progress is on the TOURNAMENT screen."))
        elif label == "SHOP":
            app.goto(ShopScene(app))
        elif label == "WORKSHOP":
            if app.save.workshop_open():
                app.goto(WorkshopScene(app))
            else:
                app.goto(NetNoticeScene(app, "WORKSHOP LOCKED", "The Tank Workshop opens once you defeat Level 5 in Tournament mode."))
        elif label == "TUTORIAL":
            app.goto(TutorialScene(app))
        elif label == "PROFILES":
            app.goto(ProfilesScene(app))
        elif label == "JUKEBOX":
            app.goto(JukeboxScene(app))
        elif label == "HOW TO PLAY":
            app.goto(HowToScene(app))
        elif label == "SETTINGS":
            app.goto(SettingsScene(app))
        elif label == "CHEAT CODES":
            app.goto(CheatScene(app))
        elif label == "LINKS":
            app.goto(LinksScene(app))
        elif label == "QUIT":
            app.running = False

    def _view(self, screen: Screen, y0: int, gap: int):
        """The menu may have more entries than a short terminal has rows: show a window that follows the selection."""
        items, idx = self.menu.items, self.menu.index
        fit = max(5, (screen.rows - 4 - y0) // gap)
        if len(items) <= fit:
            return self.menu
        start = max(0, min(idx - fit // 2, len(items) - fit))
        view = copy.copy(self.menu)
        view.items = list(items[start:start + fit])
        view.index = idx - start
        return view

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        t = self.app.time
        tall = screen.rows >= len(self.menu.items) + 23        # the full TANKS logo whenever the whole menu still fits under it
        if self.theme == "MASTER":
            y = draw_master_logo(screen, 0, t, tall)
            gap = 2 if y + 4 + len(self.menu.items) * 2 <= screen.rows - 3 else 1
            draw_master_menu(screen, self._view(screen, y + 2, gap), screen.cols // 2, y + 2, t, gap)
        elif self.theme == "SECRET":
            y = draw_secret_logo(screen, 0, t, tall)
            gap = 2 if y + 4 + len(self.menu.items) * 2 <= screen.rows - 3 else 1
            draw_secret_menu(screen, self._view(screen, y + 2, gap), screen.cols // 2, y + 2, t, gap)
        elif self.theme in HOME_THEMES:
            th = HOME_THEMES[self.theme]
            y = draw_theme_logo(screen, 1, t, tall, th)
            gap = 2 if y + 4 + len(self.menu.items) * 2 <= screen.rows - 3 else 1
            draw_theme_menu(screen, self._view(screen, y + 2, gap), screen.cols // 2, y + 2, t, th, gap)
        else:
            y = draw_logo(screen, 2, t, compact=not tall)
            screen.center(y, "SELECT MISSION", Palette.PRIMARY_DIM)
            gap = 2 if screen.rows >= 32 and y + 4 + len(self.menu.items) * 2 <= screen.rows - 3 else 1
            self.menu.draw(screen, screen.cols // 2, y + 2, t, gap=gap) if False else self._view(screen, y + 2, gap).draw(screen, screen.cols // 2, y + 2, t, gap=gap)
        draw_keycaps(screen, screen.cols // 2 - 22, screen.rows - 3, (("W/S", "NAVIGATE"), ("ENTER", "SELECT"), ("ESC", "BACK")))
        self.draw_footer(screen, screen.rows - 2)
        pt = int(self.app.save.playtime)
        pn = next((p["name"] for p in self.app.profiles.profiles if p["id"] == self.app.profiles.active), "")
        screen.text(2, screen.rows - 1, f"{pn}  ·  PLAYTIME {fmt_playtime(pt)}", Palette.MUTED)
