"""Match setup (players, tanks, colours, ammo, AI) and the map picker."""
from __future__ import annotations

import random
import textwrap
from dataclasses import replace
from typing import Callable, Optional

from tanks.art.scenery import Scenery
from tanks.art.tanks import draw_tank
from tanks.battle.terrain import Terrain
from tanks.colors import GOLD, Palette, clamp, shade
from tanks.config import MAX_HP
from tanks.content.ammo import AMMOS, AMMO_BY_KEY, ANCIENT_AMMOS, MISSION_AMMOS, SECRET_AMMOS, SHOP_AMMOS, TICKET_AMMOS
from tanks.content.custom import custom_designs
from tanks.content.maps import MAPS, MapDefinition
from tanks.content.missions import MISSIONS
from tanks.content.paints import ANIM_PAINTS, COLOR_BY_NAME, COLOR_CHOICES, PAINT_UNLOCK, color_index, live_color
from tanks.content.shop import SHOP_BY_UID
from tanks.content.tanks import (
    ANCIENT_DESIGNS, DESIGNS, DESIGN_BY_KEY, MISSION_DESIGNS, SECRET_DESIGNS, SHOP_DESIGNS, TICKET_DESIGNS
)
from tanks.content.tickets import TICKET_BOSSES
from tanks.content.tournament import TOURNAMENT, TournamentLevel
from tanks.match.opponents import cpu_ammo_pool, pick_ai_kit
from tanks.match.rules import Rules
from tanks.match.sessions import MatchConfig, PlayerSetup, boss_setup
from tanks.save import Loadout
from tanks.scenes.base import BackdropScene, Scene
from tanks.scenes.main_menu import MenuScene
from tanks.scenes.tournament import TournamentScene
from tanks.screen import PixelCanvas, Screen
from tanks.settings import Difficulty
from tanks.terminal import Action, InputEvent
from tanks.ui.preview import PreviewStage
from tanks.ui.widgets import draw_keycaps


def draw_swatches(screen: Screen, x: int, y: int, idx: int, taken: Optional[int] = None, anim: tuple = (),
                  cur: str = "", t: float = 0.0) -> None:
    """24 colours as a 12x2 grid, then one compact swatch for each animated paint you own (RGB, ASTRAL, PRISMATIC, VOID,
    MOLTEN, CHROME, AURORA, CIRCUIT); the selection is framed in white and named in the row's own label."""
    step = 4 if len(anim) * 4 - 1 <= 36 else 3                  # ten owned paints still fit the 36-column grid
    for i, (name, col) in enumerate(anim):
        sx = x + i * step
        c = live_color(col, t + i * 0.37)
        if name == cur:
            screen.put(sx, y + 2, "▐", Palette.WHITE, Palette.PANEL)
            screen.put(sx + 1, y + 2, "█", c, Palette.PANEL)
            screen.put(sx + 2, y + 2, "▌", Palette.WHITE, Palette.PANEL)
        else:
            screen.text(sx, y + 2, "███", c, Palette.PANEL)
    if anim and len(anim) * step + 8 <= 36:
        screen.text(x + len(anim) * step, y + 2, "ANIMATED", Palette.MUTED, Palette.PANEL)
    for k, (_, col) in enumerate(COLOR_CHOICES):
        sx, sy = x + (k % 12) * 3, y + k // 12
        if k == idx:
            screen.put(sx, sy, "▐", Palette.WHITE, Palette.PANEL)
            screen.put(sx + 1, sy, "█", col, Palette.PANEL)
            screen.put(sx + 2, sy, "▌", Palette.WHITE, Palette.PANEL)
        elif k == taken:
            screen.text(sx, sy, "╳╳╳", shade(col, 0.35), Palette.PANEL)
        else:
            screen.text(sx, sy, "███", col, Palette.PANEL)


def unlock_hint(kind: str, key: str) -> str:
    for lv in TOURNAMENT:
        if (kind == "tank" and lv.tank == key) or (kind == "ammo" and lv.ammo == key):
            return f"LOCKED - CLEAR TOURNAMENT LEVEL {lv.number}"
    for m in MISSIONS:
        if f"{kind}:{key}" in m.rewards:
            return f"LOCKED - CLEAR MISSION {m.number}"
    if any(f"{kind}:{key}" in b.reward_ids() for b in TICKET_BOSSES):
        return "LOCKED - WIN IT FROM A TERMINAL TICKET"
    item = SHOP_BY_UID.get(f"{kind}:{key}")
    if item:
        return f"LOCKED - SHOP: {item.coins} COINS" + (f" + {item.credits} CREDITS" if item.credits else "")
    return "LOCKED"


class SetupScene(BackdropScene):
    """Loadout screen: tank design, hull colour, ammo, shell colour (+ difficulty) with a live preview.
    Modes: 'single', 'two' (two pages) and 'tournament' (one page, then straight into the run)."""

    def __init__(self, app, mode: str = "single", level: Optional[TournamentLevel] = None, rules: "Optional[Rules]" = None,
                 done: Optional[Callable] = None, pages: Optional[int] = None) -> None:
        super().__init__(app)
        self.mode, self.level, self.rules, self.done = mode, level, rules, done
        self.back: Optional[Scene] = None
        self.pages = pages or (2 if mode == "two" else 1)
        self.page = 0
        self.row = 0
        self.sel = [Loadout(**vars(app.save.loadout(i))) for i in range(2)]
        self.msg, self.msg_t = "", 0.0
        self.stage = PreviewStage(app.settings, 46, 26, 2)

    # -- rows ----------------------------------------------------------------
    def rows(self) -> list[str]:
        r = ["TANK", "HULL COLOR", "AMMO", "SHELL COLOR"]
        if self.mode == "single" and self.page == 0:
            r.append("AI DIFFICULTY")
        return r + ["CONFIRM"]

    def _cur(self) -> Loadout:
        return self.sel[self.page]

    def _locked(self, lo: Loadout) -> str:
        if lo.tank not in self.app.save.unlocked_tanks():
            return unlock_hint("tank", lo.tank)
        if lo.ammo not in self.app.save.unlocked_ammo():
            return unlock_hint("ammo", lo.ammo)
        return ""

    def _kits(self, name: str) -> tuple:
        """Every Tournament kit (locked ones are shown as locked) plus any secret kit that has been unlocked."""
        if name == "TANK":
            return (DESIGNS + SHOP_DESIGNS + MISSION_DESIGNS + TICKET_DESIGNS + ANCIENT_DESIGNS + custom_designs(self.app.save)
                    + tuple(d for d in SECRET_DESIGNS if d.key in self.app.save.unlocked_tanks()))
        return AMMOS + SHOP_AMMOS + MISSION_AMMOS + TICKET_AMMOS + ANCIENT_AMMOS + tuple(a for a in SECRET_AMMOS if a.key in self.app.save.unlocked_ammo())

    def _cycle_kit(self, items: tuple, attr: str, d: int) -> None:
        lo = self._cur()
        i = next(k for k, it in enumerate(items) if it.key == getattr(lo, attr))
        setattr(lo, attr, items[(i + d) % len(items)].key)

    def _color_names(self, attr: str) -> list:
        names = [n for n, _ in COLOR_CHOICES]
        if self.app.save.is_unlocked("rgb:hull" if attr == "tank_color" else "rgb:shell"):
            names.append("RGB")
        for nm, _ in ANIM_PAINTS[1:]:
            if self.app.save.is_unlocked(PAINT_UNLOCK[nm][0]):
                names.append(nm)
        return names

    def _cycle_color(self, attr: str, d: int) -> None:
        lo = self._cur()
        names = self._color_names(attr)
        cur = getattr(lo, attr)
        i = names.index(cur) if cur in names else 0
        other = self.sel[0].tank_color if (attr == "tank_color" and self.page == 1) else None
        for _ in range(len(names)):
            i = (i + d) % len(names)
            if names[i] != other:
                break
        setattr(lo, attr, names[i])

    def handle(self, ev: InputEvent) -> None:
        rows = self.rows()
        if ev.action is Action.BACK:
            if self.page > 0:
                self.page -= 1
                self.row = 0
            else:
                self.app.goto(TournamentScene(self.app, self.level.number) if self.mode == "tournament" else
                              self.back or MenuScene(self.app))
        elif ev.action is Action.UP:
            self.row = (self.row - 1) % len(rows)
        elif ev.action is Action.DOWN:
            self.row = (self.row + 1) % len(rows)
        elif ev.action in (Action.LEFT, Action.RIGHT):
            d = -1 if ev.action is Action.LEFT else 1
            name = rows[self.row]
            if name in ("TANK", "AMMO") and getattr(ev, "coarse", False):
                d *= 5                                   # SHIFT + A/D jumps five kits (there are a lot now)
            if name == "TANK":
                self._cycle_kit(self._kits("TANK"), "tank", d)
            elif name == "AMMO":
                self._cycle_kit(self._kits("AMMO"), "ammo", d)
            elif name == "HULL COLOR":
                self._cycle_color("tank_color", d)
            elif name == "SHELL COLOR":
                self._cycle_color("shot_color", d)
            elif name == "AI DIFFICULTY":
                order = [x for x in Difficulty if x is not Difficulty.MASTER or self.app.save.master_unlocked]
                s = self.app.settings
                s.difficulty = order[(order.index(s.difficulty) + d) % len(order)]
                self.app.apply_settings()
        elif ev.confirm:
            if rows[self.row] == "CONFIRM" or ev.action is Action.CONFIRM:
                lock = self._locked(self._cur())
                if lock:
                    self.msg, self.msg_t = lock, 2.5
                    self.row = 0
                elif self.page + 1 < self.pages:
                    self.page += 1
                    self.row = 0
                else:
                    self._finish()
            else:
                self.row = (self.row + 1) % len(rows)

    def _finish(self) -> None:
        app = self.app
        for i in range(self.pages):
            app.save.loadouts[i] = Loadout(**vars(self.sel[i]))
        app.save.flush()
        if self.mode in ("lan", "mission"):                  # these flows decide the match themselves
            self.done([Loadout(**vars(l)) for l in self.sel[:self.pages]])
            return
        mk = lambda i, name, label, ai=False: PlayerSetup(
            name, label, COLOR_BY_NAME[self.sel[i].tank_color], COLOR_BY_NAME[self.sel[i].shot_color], ai,
            self.sel[i].tank, self.sel[i].ammo,
            self.level.player_hp if (self.mode == "tournament" and i == 0) else (self.rules.hp if self.rules else MAX_HP))
        pcol = color_index(self.sel[0].tank_color)
        if self.mode == "tournament":
            cfg = MatchConfig([mk(0, "PLAYER", "YOU"), boss_setup(self.level, pcol)], True, self.level.difficulty, "tournament",
                              self.level.precision, ammo_fx=False)
            app.start_tournament(self.level, cfg)
            return
        if self.mode == "single":
            diff = app.settings.difficulty
            r = self.rules or Rules()
            me_setup = mk(0, "PLAYER", "YOU")
            players = [me_setup, replace(pick_ai_kit(app.save, app.rng, diff, pcol, cpu_ammo_pool(app.save, me_setup.ammo, r.ammo_fx)), hp=r.hp)]
            cfg = MatchConfig(players, True, diff, "single", target=r.target, label=r.label, ammo_fx=r.ammo_fx, special=r.special, pick_maps=r.pick_maps,
                              blessing=r.blessing and app.save.blessing_unlocked())
            app.start_match(cfg, r.mapdef, r.wind_value(app.settings))        # the rules screen already chose map + wind
            return
        else:
            r = self.rules or Rules()
            cfg = MatchConfig([mk(0, "PLAYER 1", "P1"), mk(1, "PLAYER 2", "P2")], False, app.settings.difficulty, "two",
                              target=r.target, label=r.label, special=r.special, ammo_fx=r.ammo_fx, pick_maps=r.pick_maps,
                              blessing=r.blessing and app.save.blessing_unlocked())
            app.start_match(cfg, r.mapdef, r.wind_value(app.settings))          # the rules screen already chose map + wind
            return
        if app.settings.random_maps:
            app.start_match(cfg, None)
        else:
            app.goto(MapSelectScene(app, cfg))

    def update(self, dt: float) -> None:
        super().update(dt)
        self.stage.update(dt)
        self.msg_t = max(0.0, self.msg_t - dt)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        total_w = 92
        x, y = (screen.cols - total_w) // 2, (screen.rows - 24) // 2
        lo = self._cur()
        title = ("PILOT SETUP" if self.mode in ("single", "lan") or (self.mode == "mission" and self.pages == 1)
                 else f"PLAYER {self.page + 1} SETUP" if self.mode in ("two", "mission") else f"LEVEL {self.level.number} LOADOUT")
        screen.box(x, y, 44, 24, "double", Palette.LINE, Palette.PANEL, title)
        rows = self.rows()
        other = color_index(self.sel[0].tank_color) if self.page == 1 else None
        design, ammo = DESIGN_BY_KEY[lo.tank], AMMO_BY_KEY[lo.ammo]
        ry = y + 2
        for i, name in enumerate(rows):
            sel = i == self.row
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            screen.fill(x + 2, ry, 40, 1, bg)
            screen.text(x + 3, ry, name, Palette.WHITE if sel else Palette.MUTED, bg)
            if name in ("TANK", "AMMO"):
                kit = design if name == "TANK" else ammo
                items = self._kits(name)
                pos = next((k for k, it in enumerate(items) if it.key == kit.key), 0) + 1
                bad = (kit.key not in (self.app.save.unlocked_tanks() if name == "TANK" else self.app.save.unlocked_ammo()))
                label = f"{pos}/{len(items)} {kit.name}" + (" ✦" if getattr(kit, "mech", ()) else "") + (" [LOCKED]" if bad else "")
                label = f"◄ {label} ►" if sel else label
                screen.text(x + 41 - len(label), ry, label, Palette.DANGER if bad else Palette.AMBER, bg)
                hint = unlock_hint("tank" if name == "TANK" else "ammo", kit.key) if bad else kit.blurb
                for k2, ln in enumerate(textwrap.wrap(hint, 39)[:3]):
                    screen.text(x + 3, ry + 1 + k2, ln, Palette.DANGER if bad else Palette.MUTED, Palette.PANEL)
                ry += 4
            elif name in ("HULL COLOR", "SHELL COLOR"):
                cur = lo.tank_color if name == "HULL COLOR" else lo.shot_color
                idx = color_index(cur, -1)
                label = f"◄ {cur} ►" if sel else cur
                screen.text(x + 41 - len(label), ry, label, live_color(COLOR_BY_NAME[cur], self.app.time), bg)
                owned = tuple((n, c) for n, c in ANIM_PAINTS if self.app.save.paint_ok(n, name == "HULL COLOR"))
                draw_swatches(screen, x + 3, ry + 1, idx, other if name == "HULL COLOR" else None, owned, cur, self.app.time)
                ry += 4
            elif name == "AI DIFFICULTY":
                d = self.app.settings.difficulty.value
                screen.text(x + 41 - len(d) - 4, ry, f"◄ {d} ►" if sel else f"  {d}  ", GOLD if d == "MASTER" else Palette.AMBER, bg)
                ry += 2
            else:
                last = self.page + 1 == self.pages
                text = ("[ START RUN ]" if self.mode == "tournament" else "[ READY ]") if last else "[ NEXT PLAYER ]"
                screen.center(ry, text, Palette.PRIMARY if sel else Palette.MUTED, bg, x + 2, 40)
        draw_keycaps(screen, x + 2, y + 22, (("W/S", "ROW"), ("A/D", "PICK"), ("SHIFT", "x5"), ("ENTER", "OK")), Palette.PANEL)
        px = x + 46
        screen.box(px, y, 48, 24, "double", Palette.LINE, Palette.PANEL, "LIVE PREVIEW")
        lock = self._locked(lo)
        self.stage.set_kit(design, COLOR_BY_NAME[lo.tank_color], ammo, COLOR_BY_NAME[lo.shot_color], 0.45 if lock else 0.0)
        screen.blit(self.stage.render(), px + 1, y + 2)
        screen.center(y + 16, f"{design.name}  +  {ammo.name}", Palette.TEXT, Palette.PANEL, px, 48)
        screen.center(y + 17, f"{lo.tank_color} HULL  /  {lo.shot_color} SHELL", Palette.MUTED, Palette.PANEL, px, 48)
        if self.mode == "tournament":
            lv = self.level
            screen.center(y + 19, f"VS {lv.boss}  ·  {lv.difficulty.value} AI", GOLD if lv.difficulty is Difficulty.MASTER else Palette.AMBER, Palette.PANEL, px, 48)
            screen.center(y + 20, lv.objective, Palette.TEXT, Palette.PANEL, px, 48)
            screen.center(y + 21, lv.rule_text, GOLD if lv.rule else Palette.MUTED, Palette.PANEL, px, 48)
            screen.center(y + 18, "SPECIAL AMMO IS OFF IN TOURNAMENT", Palette.MUTED, Palette.PANEL, px, 48)
        else:
            if self.mode == "mission":
                notes, nc = ["SPECIAL AMMO IS OFF IN MISSIONS", "Every kit is cosmetic: all ammo plays alike."], Palette.MUTED
            elif self.mode == "lan" and self.rules is None:
                notes, nc = ["✦ = ammo with a special effect", "LAN: the host's SPECIAL AMMO rule decides."], Palette.AMBER
            elif self.rules is not None and not self.rules.ammo_fx:
                notes, nc = ["SPECIAL AMMO IS OFF (match rule)", "✦ ammo plays like plain ammo this match."], Palette.MUTED
            else:
                notes, nc = ["SPECIAL AMMO IS ON  ✦ = has an effect", "Bounce, split, cluster... see HOW TO PLAY."], Palette.AMBER
            for k, nt in enumerate(notes):
                screen.center(y + 19 + k, nt, nc, Palette.PANEL, px, 48)
            if self.rules is not None and self.rules.special:
                screen.center(y + 21, "SPECIAL ATTACK: X skips a turn; after two,", GOLD, Palette.PANEL, px, 48)
                screen.center(y + 22, "your next shot deals 3 damage." if self.msg_t <= 0 else self.msg, GOLD if self.msg_t <= 0 else Palette.DANGER, Palette.PANEL, px, 48)
        if self.msg_t > 0:
            screen.center(y + 22, self.msg, Palette.DANGER, Palette.PANEL, px, 48)
        elif not (self.rules is not None and self.rules.special and self.mode != "tournament"):
            screen.center(y + 22, "ESC  BACK", Palette.MUTED, Palette.PANEL, px, 48)


class MapSelectScene(BackdropScene):
    VISIBLE = 17

    def __init__(self, app, cfg: MatchConfig) -> None:
        super().__init__(app)
        self.cfg = cfg
        self.maps = list(MAPS) + app.save.unlocked_maps()
        self.index = 0          # 0 = RANDOM, 1..N = maps
        self.cache: dict = {}

    def handle(self, ev: InputEvent) -> None:
        n = len(self.maps) + 1
        if ev.action is Action.BACK:
            self.app.goto(SetupScene(self.app, self.cfg.mode))
        elif ev.action is Action.UP:
            self.index = (self.index - 1) % n
        elif ev.action is Action.DOWN:
            self.index = (self.index + 1) % n
        elif ev.action is Action.LEFT:
            self.index = max(0, self.index - 8)
        elif ev.action is Action.RIGHT:
            self.index = min(n - 1, self.index + 8)
        elif ev.confirm:
            self.app.start_match(self.cfg, None if self.index == 0 else self.maps[self.index - 1])

    def _preview(self, mapdef: MapDefinition) -> PixelCanvas:
        if mapdef.key not in self.cache:
            rng = random.Random(1)
            terrain = Terrain(46, 26, mapdef, rng)
            tanks = []
            for i in range(2):
                x = int(mapdef.spawns[i] * 46)
                terrain.flatten(x + 0.5, 10)
                tanks.append(x + 0.5)
            scen = Scenery(46, 26, mapdef.theme, rng)
            scen.apply_terrain(terrain)
            self.cache[mapdef.key] = (scen, terrain, tanks)
        scen, terrain, tanks = self.cache[mapdef.key]
        cv = scen.canvas()
        scen.draw_stars(cv, self.app.time)
        scen.draw_aurora(cv, self.app.time)
        scen.draw_fx(cv, self.app.time)
        for i, x in enumerate(tanks):
            p = self.cfg.players[i]
            draw_tank(cv, x, terrain.support_height(x), 1 if i == 0 else -1, 50 if i == 0 else 130, p.tank_color,
                      design=DESIGN_BY_KEY[p.design], t=self.app.time)
        return cv

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        x, y = (screen.cols - 88) // 2, (screen.rows - 22) // 2
        n = len(self.maps) + 1
        screen.box(x, y, 34, 22, "double", Palette.LINE, Palette.PANEL, "BATTLEFIELD")
        top = int(clamp(self.index - self.VISIBLE // 2, 0, n - self.VISIBLE))
        for row in range(self.VISIBLE):
            i = top + row
            sel = i == self.index
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            if i == 0:
                name = "RANDOM"
            else:
                m = self.maps[i - 1]
                name = f"{i:02d} {m.name}" if not m.special else f"★  {m.name}"
            col = self.maps[i - 1].accent if (i and self.maps[i - 1].special) else Palette.AMBER if i == 0 and not sel else Palette.WHITE if sel else Palette.MUTED
            screen.fill(x + 2, y + 2 + row, 30, 1, bg)
            screen.text(x + 3, y + 2 + row, ("▶ " if sel else "  ") + name, col, bg)
        if top > 0:
            screen.put(x + 31, y + 2, "▲", Palette.PRIMARY_DIM, Palette.PANEL)
        if top + self.VISIBLE < n:
            screen.put(x + 31, y + 2 + self.VISIBLE - 1, "▼", Palette.PRIMARY_DIM, Palette.PANEL)
        screen.center(y + 20, f"{self.index}/{n - 1}  ·  A/D PAGE", Palette.MUTED, Palette.PANEL, x, 34)
        px = x + 36
        screen.box(px, y, 52, 22, "double", Palette.LINE, Palette.PANEL, "TERRAIN SCAN")
        m = self.maps[self.index - 1] if self.index else MAPS[int(self.app.time / 1.2) % len(MAPS)]
        screen.blit(self._preview(m), px + 3, y + 2)
        screen.center(y + 16, m.name if self.index else "RANDOM", m.accent if m.special else Palette.AMBER, Palette.PANEL, px, 52)
        desc = m.description if self.index else "A fresh battlefield every round."
        cut = desc.rfind(" ", 0, 48) if len(desc) > 48 else len(desc)
        screen.center(y + 17, desc[:cut], Palette.TEXT, Palette.PANEL, px, 52)
        screen.center(y + 18, desc[cut:].strip(), Palette.TEXT, Palette.PANEL, px, 52)
        if self.index:
            dots = lambda k: "●" * k + "○" * (3 - k)
            screen.center(y + 19, f"COVER {dots(m.cover)}     RELIEF {dots(m.relief)}", Palette.PRIMARY, Palette.PANEL, px, 52)
        screen.center(y + 20, "Opening map only - later rounds rotate", Palette.MUTED, Palette.PANEL, px, 52)
