"""The boot screen, the home-screen base class and the title screen."""
from __future__ import annotations

from tanks import CREDIT_NAME, CREDIT_URL, __version__
from tanks.art.backdrops import draw_master_logo, draw_secret_logo, draw_theme_logo
from tanks.colors import GOLD, Palette, clamp, mix
from tanks.content.homes import HOME_THEMES
from tanks.scenes.base import BackdropScene
from tanks.screen import Screen
from tanks.terminal import InputEvent
from tanks.ui.widgets import draw_logo


class BootScene(BackdropScene):
    show_wallet = False
    LINES = ("TERMINALTANKS // TACTICAL ARTILLERY SYSTEM", f"author: {CREDIT_NAME} ({CREDIT_URL})",
             "display link .............. online", "ballistics core ........... online",
             "terrain engine ............ online", "particle system ........... online",
             "fire-control AI ........... online", "tournament registry ....... online",
             "all systems nominal")

    def __init__(self, app) -> None:
        super().__init__(app)
        self.t = 0.0

    def handle(self, ev: InputEvent) -> None:
        self.t = max(self.t, 9.0)

    def update(self, dt: float) -> None:
        self.t += dt
        if self.t > 3.8 or (self.t >= 9.0):
            self.app.goto(TitleScene(self.app))

    def draw(self, screen: Screen) -> None:
        screen.clear(Palette.BG)
        x, y = max(2, screen.cols // 2 - 24), screen.rows // 2 - 9
        shown = int(self.t / 0.38)
        for i, line in enumerate(self.LINES[:shown]):
            head = i == 0
            screen.text(x, y + i * 2, line, Palette.PRIMARY if head else Palette.TEXT)
            if not head and i != 1:
                screen.text(x + 41, y + i * 2, "[ OK ]", Palette.OK)
        w = 40
        frac = clamp(self.t / 3.4, 0, 1)
        screen.text(x, y + 20, "LOADING", Palette.MUTED)
        for i in range(w):
            screen.put(x + 8 + i, y + 20, "█" if i < frac * w else "░", Palette.PRIMARY if i < frac * w else (36, 52, 62), Palette.BG)


class HomeScene(BackdropScene):
    """Shared behaviour of the title and main-menu scenes: switching between the unlocked home screens."""
    home = True
    THEME_COLORS = {"CLASSIC": Palette.PRIMARY_DIM, "MASTER": GOLD, "SECRET": (110, 255, 150),
                    **{k: v.accent for k, v in HOME_THEMES.items()}}

    def __init__(self, app) -> None:
        super().__init__(app)
        self.note = ""
        self.note_t = 0.0

    def toggle_home(self) -> None:
        modes = self.app.save.home_modes()
        if len(modes) < 2:
            self.note, self.note_t = "NO OTHER HOME SCREENS YET - BUY ONE IN THE SHOP", 3.0
            return
        s = self.app.settings
        s.home_mode = modes[(modes.index(self.theme) + 1) % len(modes)]
        self.app.apply_settings()
        self.app.goto(type(self)(self.app))

    @property
    def theme(self) -> str:
        return self.app.home_theme()

    @property
    def master(self) -> bool:
        return self.theme == "MASTER"

    def update(self, dt: float) -> None:
        super().update(dt)
        self.note_t = max(0.0, self.note_t - dt)

    def draw_footer(self, screen: Screen, row: int) -> None:
        if self.note_t > 0:
            screen.center(row, self.note, Palette.AMBER)
            return
        if len(self.app.save.home_modes()) > 1:
            screen.center(row, f"[H] HOME SCREEN: {self.theme}  (press H to switch)", self.THEME_COLORS[self.theme])
        else:
            screen.center(row, "[H] MORE HOME SCREENS IN THE SHOP  (Master screen: clear Level 20)", Palette.MUTED)


class TitleScene(HomeScene):
    def handle(self, ev: InputEvent) -> None:
        from tanks.scenes.main_menu import MenuScene
        if ev.raw in ("h", "H", "TAB"):
            self.toggle_home()
        elif ev.confirm:
            self.app.goto(MenuScene(self.app))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        t = self.app.time
        if self.theme == "MASTER":
            y = max(0, (screen.rows - (21 if screen.rows >= 34 else 15)) // 2)
            y = draw_master_logo(screen, y, t, screen.rows >= 34)
            if int(t * 2) % 2 == 0:
                screen.center(y + 2, "[ PRESS ENTER ]", (255, 248, 220))
        elif self.theme == "SECRET":
            y = max(0, (screen.rows - (21 if screen.rows >= 34 else 15)) // 2)
            y = draw_secret_logo(screen, y, t, screen.rows >= 34)
            if int(t * 2) % 2 == 0:
                screen.center(y + 2, "[ PRESS ENTER ]", (200, 255, 215))
        elif self.theme in HOME_THEMES:
            th = HOME_THEMES[self.theme]
            y = max(1, (screen.rows - (21 if screen.rows >= 34 else 15)) // 2)
            y = draw_theme_logo(screen, y, t, screen.rows >= 34, th)
            if int(t * 2) % 2 == 0:
                screen.center(y + 2, "[ PRESS ENTER ]", mix(th.accent, (255, 255, 255), 0.6))
        else:
            y = max(1, (screen.rows - 18) // 2)
            y = draw_logo(screen, y, t, compact=False)
            screen.center(y + 1, "T A C T I C A L   A R T I L L E R Y   S I M U L A T I O N", Palette.AMBER)
            if int(t * 2) % 2 == 0:
                screen.center(y + 4, "[ PRESS ENTER ]", Palette.WHITE)
        screen.center(screen.rows - 4, f"v{__version__}  -  pure Python, zero dependencies", Palette.MUTED)
        screen.center(screen.rows - 3, f"created by {CREDIT_NAME}  ·  {CREDIT_URL}", Palette.PRIMARY_DIM)
        self.draw_footer(screen, screen.rows - 2)
