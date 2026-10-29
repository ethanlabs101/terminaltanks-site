"""Scene and BackdropScene: the base classes every screen builds on."""
from __future__ import annotations

from typing import TYPE_CHECKING

from tanks.screen import Screen
from tanks.terminal import InputEvent

if TYPE_CHECKING:
    from tanks.app import Application


class Scene:
    overlay = False
    ambient = False
    show_wallet = True

    def __init__(self, app: "Application") -> None:
        self.app = app

    def enter(self) -> None: ...
    def exit(self) -> None: ...
    def handle(self, ev: InputEvent) -> None: ...
    def update(self, dt: float) -> None: ...
    def update_ambient(self, dt: float) -> None: ...
    def draw(self, screen: Screen) -> None: ...


class BackdropScene(Scene):
    home = False

    def backdrop(self):
        return self.app.home_backdrop() if self.home else self.app.backdrop

    def update(self, dt: float) -> None:
        self.backdrop().update(dt)

    def draw(self, screen: Screen) -> None:
        self.backdrop().draw(screen, self.app.time)
