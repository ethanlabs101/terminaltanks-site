"""Small widgets: the big pixel logo, health and bars, menus, keycaps, panels, map previews and the wallet."""
from __future__ import annotations

import math
import random
import textwrap
from typing import Optional, Sequence

from tanks.art.scenery import Scenery
from tanks.art.tanks import draw_tank
from tanks.battle.tank import Tank
from tanks.battle.terrain import Terrain
from tanks.colors import GOLD, Palette, RGB, clamp, gradient, mix
from tanks.config import MAX_HP
from tanks.content.maps import MapDefinition
from tanks.save import SaveData
from tanks.screen import PixelCanvas, Screen
from tanks.terminal import Action, InputEvent


_GLYPHS = {
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    "M": ["███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "K": ["██╗  ██╗", "██║ ██╔╝", "█████╔╝ ", "██╔═██╗ ", "██║  ██╗", "╚═╝  ╚═╝"],
    "S": ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"],
}
DIGITS = {
    "0": ("███", "█ █", "█ █", "█ █", "███"), "1": (" █ ", "██ ", " █ ", " █ ", "███"),
    "2": ("███", "  █", "███", "█  ", "███"), "3": ("███", "  █", "███", "  █", "███"),
}


def big_word(word: str) -> list[str]:
    rows = [""] * 6
    for ch in word:
        g = _GLYPHS[ch]
        w = max(len(r) for r in g)
        for i in range(6):
            rows[i] += g[i].ljust(w)
    return rows


def draw_logo(screen: Screen, y: int, t: float, compact: bool) -> int:
    """Draws the gradient logo with a travelling shimmer. Returns the next free row."""
    words = [big_word("TERMINAL")] if compact else [big_word("TERMINAL"), big_word("TANKS")]
    shimmer = (t * 42) % 140 - 30
    for wi, rows in enumerate(words):
        width = len(rows[0])
        x0 = (screen.cols - width) // 2
        for r, line in enumerate(rows):
            top = mix((150, 255, 235), (50, 150, 235), (r + wi * 6) / 11)
            for i, ch in enumerate(line):
                if ch == " ":
                    continue
                if ch == "█":
                    b = max(0.0, 1 - abs(i + r * 2 + wi * 14 - shimmer) / 9)
                    screen.put(x0 + i, y, ch, mix(top, (255, 255, 255), b * 0.75), Palette.BG)
                else:
                    screen.put(x0 + i, y, ch, (30, 76, 100), Palette.BG)
            y += 1
        y += 0 if wi else 1
    if compact:
        screen.center(y, "▀▄▀  T  A  N  K  S  ▀▄▀", Palette.AMBER)
        y += 1
    return y


def draw_hp(screen: Screen, x: int, y: int, t: Tank, bg: RGB, right: bool = False) -> int:
    """Hearts for small health pools, a bar plus number for big ones. Returns the width drawn."""
    if t.max_hp <= 10:
        w = t.max_hp * 2 - 1
        x0 = x - w + 1 if right else x
        for k in range(t.max_hp):
            screen.put(x0 + k * 2, y, "♥" if k < t.hp else "♡", Palette.HEART if k < t.hp else Palette.HEART_OFF, bg)
        return w
    n = 0 if t.hp <= 0 else max(1, min(10, math.ceil(10 * t.hp / t.max_hp)))
    label = f" {max(t.hp, 0)}/{t.max_hp}"
    w = 10 + len(label)
    x0 = x - w + 1 if right else x
    for k in range(10):
        screen.put(x0 + k, y, "█" if k < n else "░", Palette.HEART if k < n else Palette.HEART_OFF, bg)
    screen.text(x0 + 10, y, label, Palette.TEXT, bg)
    return w


def hearts(hp: int, spaced: bool = True, total: int = MAX_HP) -> str:
    if total > 10:
        return f"♥{max(hp, 0)}/{total}"
    sep = " " if spaced else ""
    return sep.join("♥" if i < hp else "♡" for i in range(total))


def draw_bar(screen: Screen, x: int, y: int, w: int, frac: float) -> None:
    frac = clamp(frac, 0, 1)
    full = frac * w
    for i in range(w):
        if i + 1 <= full:
            ch, col = "█", gradient(((0, Palette.OK), (0.6, Palette.AMBER), (1, Palette.DANGER)), i / max(1, w - 1))
        elif i < full:
            ch, col = "▌", gradient(((0, Palette.OK), (0.6, Palette.AMBER), (1, Palette.DANGER)), i / max(1, w - 1))
        else:
            ch, col = "░", (52, 66, 78)
        screen.put(x + i, y, ch, col, Palette.PANEL)


class MenuList:
    def __init__(self, items: Sequence[str]) -> None:
        self.items, self.index = list(items), 0

    def handle(self, ev: InputEvent) -> Optional[int]:
        if ev.action is Action.UP:
            self.index = (self.index - 1) % len(self.items)
        elif ev.action is Action.DOWN:
            self.index = (self.index + 1) % len(self.items)
        elif ev.confirm:
            return self.index
        return None

    def draw(self, screen: Screen, cx: int, y: int, t: float, gap: int = 1, width: int = 30) -> None:
        for i, label in enumerate(self.items):
            row = y + i * gap
            x0 = cx - width // 2
            if i == self.index:
                pulse = 0.5 + 0.5 * math.sin(t * 6)
                screen.fill(x0, row, width, 1, Palette.PANEL_HI)
                screen.center(row, label, Palette.WHITE, Palette.PANEL_HI, x0, width)
                arrow = mix(Palette.PRIMARY_DIM, Palette.PRIMARY, pulse)
                screen.put(x0 + 1, row, "▶", arrow, Palette.PANEL_HI)
                screen.put(x0 + width - 2, row, "◀", arrow, Palette.PANEL_HI)
            else:
                screen.center(row, label, Palette.MUTED, None, x0, width)


def draw_keycaps(screen: Screen, x: int, y: int, pairs: Sequence[tuple[str, str]], bg: Optional[RGB] = None) -> None:
    for key, desc in pairs:
        screen.text(x, y, key, Palette.AMBER, bg)
        x += len(key) + 1
        screen.text(x, y, desc, Palette.MUTED, bg)
        x += len(desc) + 3


def panel(screen: Screen, w: int, h: int, title: str, y: Optional[int] = None, fg: RGB = Palette.LINE) -> tuple[int, int]:
    x = (screen.cols - w) // 2
    y = (screen.rows - h) // 2 if y is None else y
    screen.box(x, y, w, h, "double", fg, Palette.PANEL, title)
    return x, y


def wrap_center(screen: Screen, y: int, text: str, width: int, fg: RGB, bg: Optional[RGB], x: int, w: int, lines: int = 2) -> int:
    """Centred, word-wrapped text that never gets cut mid-word. Returns rows used."""
    parts = textwrap.wrap(text, width) or [""]
    if len(parts) > lines:
        parts = parts[:lines]
        parts[-1] = parts[-1][:max(0, width - 1)].rstrip() + "…"
    for k, ln in enumerate(parts):
        screen.center(y + k, ln, fg, bg, x, w)
    return len(parts)


def render_map_preview(cache: dict, mapdef: MapDefinition, w: int, h: int, t: float, tanks: list) -> PixelCanvas:
    """Terrain scan used by the rules screens. tanks = [(design, colour), (design, colour)]."""
    key = (mapdef.key, w, h)
    if key not in cache:
        rng = random.Random(1)
        terrain = Terrain(w, h, mapdef, rng)
        xs = []
        for i in range(2):
            x = int(mapdef.spawns[i] * w)
            terrain.flatten(x + 0.5, 10)
            xs.append(x + 0.5)
        scen = Scenery(w, h, mapdef.theme, rng)
        scen.apply_terrain(terrain)
        cache[key] = (scen, terrain, xs)
    scen, terrain, xs = cache[key]
    cv = scen.canvas()
    scen.draw_stars(cv, t)
    scen.draw_aurora(cv, t)
    scen.draw_fx(cv, t)
    for i, x in enumerate(xs):
        d, col = tanks[i]
        draw_tank(cv, x, terrain.support_height(x), 1 if i == 0 else -1, 50 if i == 0 else 130, col, design=d, t=t)
    return cv


def wallet_text(save: "SaveData") -> str:
    return f"◉ {save.coins:,}   ◈ {save.credits:,}"


def draw_wallet(screen: Screen, save: "SaveData", flash: float = 0.0) -> None:
    """Coins (◉) and Tournament Credits (◈) in the top-right corner of every screen."""
    text = wallet_text(save)
    x = screen.cols - len(text) - 3
    bg = mix((16, 24, 34), (60, 52, 20), clamp(flash, 0, 1))
    screen.fill(x - 1, 0, len(text) + 3, 1, bg)
    coin, _, cred = text.partition("   ")
    screen.text(x, 0, coin, GOLD, bg)
    screen.text(x + len(coin) + 3, 0, cred, (140, 225, 255), bg)
