"""After the Martyr: the rewards and the finale screens."""
from __future__ import annotations

from tanks.art.backdrops import ThemeBackdrop, draw_theme_logo
from tanks.colors import GOLD, Palette
from tanks.content.ammo import ANCIENT_AMMOS
from tanks.content.homes import HOME_THEMES
from tanks.content.maps import ANCIENT_MAPS
from tanks.content.paints import ASTRAL, astral
from tanks.content.tanks import ANCIENT_DESIGNS
from tanks.scenes.base import BackdropScene, Scene
from tanks.scenes.main_menu import MenuScene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.preview import PreviewStage
from tanks.ui.widgets import wrap_center


class MartyrRewardsScene(BackdropScene):
    """Everything the Martyr leaves behind."""

    def music(self):
        return ("the_blessing", "story")

    def __init__(self, app) -> None:
        super().__init__(app)
        self.stage = PreviewStage(app.settings, 46, 26, 2)

    def handle(self, ev: InputEvent) -> None:
        from tanks.scenes.jukebox import BlessingGiftScene
        if ev.confirm or ev.action in (Action.CONFIRM, Action.BACK):
            self.app.goto(BlessingGiftScene(self.app))

    def update(self, dt: float) -> None:
        super().update(dt)
        self.stage.update(dt)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        t = self.app.time
        W, H = 94, 26
        x, y = (screen.cols - W) // 2, max(0, (screen.rows - H) // 2)
        screen.box(x, y, 44, H, "double", GOLD, Palette.PANEL, "THE MARTYR'S LEGACY")
        rows = ([("ANCIENT ARTIFACT TANKS", GOLD)] + [(f"  ✦ {d.name}", Palette.WHITE) for d in ANCIENT_DESIGNS]
                + [("ANCIENT ARTIFACT AMMO", GOLD)] + [(f"  ✦ {a.name}", Palette.WHITE) for a in ANCIENT_AMMOS]
                + [("BATTLEFIELDS", GOLD)] + [(f"  ✦ {m.name}", m.accent) for m in ANCIENT_MAPS]
                + [("COLOR", GOLD), ("  ✦ ASTRAL PAINT & AMMO COLOR", astral(t))])
        for k, (txt, c) in enumerate(rows[:20]):
            screen.text(x + 3, y + 2 + k, txt, c, Palette.PANEL)
        screen.text(x + 3, y + 2 + len(rows[:20]), "6 HOME SCREENS - ONE PER ANCIENT TANK", Palette.AMBER, Palette.PANEL)
        screen.text(x + 3, y + 3 + len(rows[:20]), "★ ULTIMATE AMMO: MARTYR'S BLESSING", astral(t), Palette.PANEL)
        screen.center(y + H - 2, "[ ENTER ]", Palette.PRIMARY if int(t * 2) % 2 == 0 else Palette.MUTED, Palette.PANEL, x, 44)
        px = x + 45
        screen.box(px, y, 49, H, "double", GOLD, Palette.PANEL, "RELICS")
        i = int(t / 2.5)
        d, a = ANCIENT_DESIGNS[i % len(ANCIENT_DESIGNS)], ANCIENT_AMMOS[i % len(ANCIENT_AMMOS)]
        self.stage.set_kit(d, ASTRAL, a, ASTRAL, 0.0)
        screen.blit(self.stage.render(), px + 1, y + 1)
        screen.center(y + 15, d.name, GOLD, Palette.PANEL, px, 49)
        wrap_center(screen, y + 16, d.blurb, 44, Palette.TEXT, Palette.PANEL, px, 49, 2)
        screen.center(y + 19, f"+ {a.name}", Palette.PRIMARY, Palette.PANEL, px, 49)
        wrap_center(screen, y + 20, a.blurb, 44, Palette.MUTED, Palette.PANEL, px, 49, 2)


class MartyrFinaleScene(Scene):
    """The 'you did it' screen: the ETERNAL home screen, shown in full."""

    def music(self):
        return ("the_blessing", "story")

    def __init__(self, app) -> None:
        super().__init__(app)
        self.bd = ThemeBackdrop(HOME_THEMES["ETERNAL"])

    def handle(self, ev: InputEvent) -> None:
        if ev.confirm or ev.action in (Action.CONFIRM, Action.BACK):
            self.app.goto(MenuScene(self.app))

    def draw(self, screen: Screen) -> None:
        t, th = self.app.time, HOME_THEMES["ETERNAL"]
        cols, rows = screen.cols, screen.rows
        self.bd.ensure(cols, rows)
        self.bd.draw(screen, t)
        y = draw_theme_logo(screen, 2, t, rows >= 34, th)
        lines = [("THE LAST SEAL IS OPEN.", GOLD), ("THE HOURGLASS TURNS FOR YOU NOW.", (255, 244, 214)), ("", (255, 255, 255)),
                 ("10 VAULTS  ·  3 PHASES  ·  1 LEGEND", th.accent), ("", (255, 255, 255)),
                 ("A new home screen waits for you every time you return.", Palette.MUTED)]
        bx, bw = (cols - 60) // 2, 60
        screen.box(bx, y + 1, bw, len(lines) + 4, "double", GOLD, Palette.BG, "")
        for k, (txt, c) in enumerate(lines):
            screen.center(y + 3 + k, txt, c, Palette.BG, bx, bw)
        if int(t * 2) % 2 == 0:
            screen.center(y + 4 + len(lines), "[ ENTER ]", Palette.PRIMARY, Palette.BG, bx, bw)
