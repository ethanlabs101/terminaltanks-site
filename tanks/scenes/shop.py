"""The SHOP: tiers, previews, buying, and the Terminal Ticket and Time Machine entries."""
from __future__ import annotations

import math
import random
import textwrap

from tanks.art.bosses import martyr_art, ticket_art
from tanks.art.scenery import MOTE_STYLES, Scenery
from tanks.art.tanks import draw_tank
from tanks.battle.terrain import Terrain
from tanks.colors import GOLD, Palette, RGB, clamp, gradient, hsv
from tanks.content.ammo import AMMO_BY_KEY
from tanks.content.homes import HOME_THEMES, HomeTheme
from tanks.content.maps import MapDefinition, SPECIAL_MAP_BY_KEY
from tanks.content.paints import COLOR_BY_NAME, PAINT_BY_KEY, RAINBOW, rainbow
from tanks.content.shop import SHOP_ITEMS, SHOP_PAGES, ShopItem, TIER_COLORS
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.content.tickets import TICKET_BOSS_BY_KEY
from tanks.scenes.base import BackdropScene
from tanks.scenes.main_menu import MenuScene
from tanks.screen import PixelCanvas, Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.preview import PreviewStage
from tanks.ui.widgets import draw_keycaps


def theme_preview(th: HomeTheme, t: float, hull: RGB, w: int = 34, h: int = 20) -> PixelCanvas:
    """Miniature of a home screen for the shop: sky, stars, ridge, ground, hero tank and (for Eclipse) the black sun."""
    cv = PixelCanvas(w, h, (0, 0, 0))
    for py in range(h):
        col = gradient(th.sky, clamp(1 - py / (h - 1), 0, 1))
        cv.rows[py] = [col] * w
    if th.stars:
        for k in range(26):
            sx, sy = (k * 37) % w, (k * 11) % int(h * 0.55)
            cv.blendf(sx, h - 1 - sy, (255, 255, 255), 0.35 + 0.45 * math.sin(t * 2 + k))
    if th.corona:
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                d = math.hypot(dx, dy)
                if d <= 4.5:
                    cv.plot(24 + dx, 13 + dy, (2, 1, 8)) if 0 <= 24 + dx < w and 0 <= 13 + dy < h else None
                elif d <= 7:
                    cv.blendf(24 + dx, 13 + dy, hsv((math.atan2(dy, dx) / math.tau + t * 0.1) % 1, 0.55, 1.0), 0.8 * (1 - (d - 4.5) / 2.5))
    style = MOTE_STYLES.get(th.fx)
    if style:
        for k in range(14):
            mx = (k * 53 + math.sin(t + k) * 2) % w
            my = (k * 29 + t * abs(style[1]) * 0.6 * (1 if style[1] < 0 else -1)) % h
            cv.blendf(mx, my, style[2][k % 3], 0.85)
    for x in range(w):
        rh = int(3 + 2 * math.sin(x * 0.3) + math.sin(x * 0.7))
        for y in range(rh + 3):
            cv.plot(x, y, th.far)
        for y in range(3):
            cv.plot(x, y, th.ground if y < 2 else th.ground_top)
    draw_tank(cv, 8.0, 3, 1, 40, hull, design=DESIGN_BY_KEY[th.hero], t=t)
    return cv


class ShopScene(BackdropScene):
    """Spend coins (and credits on master-tier gear). Five pages; tier rows; live preview; ENTER twice to buy."""
    CW, GAP, W = 10, 1, 94

    def music(self):
        return ("shop_jingle", "menu")

    def __init__(self, app, page: int = 0) -> None:
        super().__init__(app)
        self.page = page
        self.pos = {p: (0, 0) for p in range(len(SHOP_PAGES))}
        self.scroll: dict = {}
        self.pending = False
        self.msg, self.msg_ok, self.msg_t = "", True, 0.0
        self.stage = PreviewStage(app.settings, 34, 20, 1)
        self.maps: dict = {}

    # -- data ----------------------------------------------------------------
    def grid(self) -> list:
        """Rows of up to five items; a row never mixes tiers, so each row has exactly one colour."""
        its = [i for i in SHOP_ITEMS if i.page == self.page]
        rows: list = []
        if self.page == 4:                                     # EXTRAS: RGB / super paints / vault, each group on its own rows
            groups: dict = {}
            for i in its:
                groups.setdefault("rgb" if i.uid.startswith("rgb:") else "paint" if i.uid.startswith("paint:") else "vault", []).append(i)
            for g in ("rgb", "paint", "vault"):
                gi = groups.get(g, [])
                rows += [gi[k:k + 5] for k in range(0, len(gi), 5)]
            return rows
        for t in sorted({i.tier for i in its}):
            tier_items = [i for i in its if i.tier == t]
            rows += [tier_items[k:k + 5] for k in range(0, len(tier_items), 5)]
        return rows

    def _view_rows(self, screen_rows: int) -> tuple:
        """(panel height, rows visible at once) for this terminal; the grid scrolls when there are more rows than that."""
        ph = max(21, min(41, screen_rows - 8))
        return ph, max(1, (ph - 3) // 4)

    def _fit(self, vis: int) -> None:
        r = min(self.pos[self.page][0], len(self.grid()) - 1)
        top = self.scroll.get(self.page, 0)
        if r < top:
            top = r
        elif r >= top + vis:
            top = r - vis + 1
        self.scroll[self.page] = max(0, min(top, max(0, len(self.grid()) - vis)))

    @property
    def item(self) -> ShopItem:
        g = self.grid()
        r, c = self.pos[self.page]
        r = min(r, len(g) - 1)
        return g[r][min(c, len(g[r]) - 1)]

    def _go_page(self, p: int) -> None:
        self.page, self.pending = p % len(SHOP_PAGES), False

    def handle(self, ev: InputEvent) -> None:
        g = self.grid()
        r, c = self.pos[self.page]
        if ev.action is Action.BACK:
            if self.pending:
                self.pending = False
            else:
                self.app.goto(MenuScene(self.app))
            return
        if len(ev.raw) == 1 and ev.raw in "12345":
            self._go_page(int(ev.raw) - 1)
            return
        if ev.raw == "TAB":
            self._go_page(self.page + 1)
            return
        if ev.action in (Action.LEFT, Action.RIGHT, Action.UP, Action.DOWN):
            self.pending = False
            if ev.action is Action.LEFT:
                c = max(0, c - 1)
            elif ev.action is Action.RIGHT:
                c = min(len(g[r]) - 1, c + 1)
            else:
                jump = self._view_rows(self.app.screen.rows)[1] if ev.coarse else 1      # SHIFT+W/S pages through the rows
                r = max(0, r - jump) if ev.action is Action.UP else min(len(g) - 1, r + jump)
            self.pos[self.page] = (r, min(c, len(g[r]) - 1))
            self._fit(self._view_rows(self.app.screen.rows)[1])
            return
        if ev.confirm and self.item.uid == "ticket":
            self._ticket()
            return
        if ev.confirm and self.item.uid == "timemachine":
            self._martyr()
            return
        if ev.confirm:
            it, save = self.item, self.app.save
            if save.is_unlocked(it.uid):
                self.msg, self.msg_ok, self.msg_t = "YOU ALREADY OWN THIS", False, 2.0
            elif save.shortfall(it):
                self.pending = False
                self.msg, self.msg_ok, self.msg_t = save.shortfall(it), False, 2.5
            elif not self.pending:
                self.pending = True
            else:
                why = save.buy(it)
                self.pending = False
                self.msg, self.msg_ok, self.msg_t = (why, False, 2.5) if why else (f"PURCHASED: {it.name}", True, 3.0)
                if not why:
                    self.app._wallet_flash = 1.4

    def _martyr(self) -> None:
        from tanks.match.martyr import start_martyr
        save, it = self.app.save, self.item
        if save.martyr_won:
            self.msg, self.msg_ok, self.msg_t = "THE MARTYR RESTS. REPLAY THE DUEL? PRESS ENTER AGAIN", True, 2.5
            if self.pending:
                self.pending = False
                start_martyr(self.app, replay=True)
            else:
                self.pending = True
        elif not save.martyr_available():
            self.msg, self.msg_ok, self.msg_t = "DEFEAT ALL 10 VAULT BOSSES FIRST", False, 2.5
        elif save.martyr_paid:
            start_martyr(self.app)
        elif save.shortfall(it):
            self.pending = False
            self.msg, self.msg_ok, self.msg_t = save.shortfall(it), False, 2.5
        elif not self.pending:
            self.pending = True
        else:
            self.pending = False
            self.app._wallet_flash = 1.4
            if save.buy_martyr(it):
                start_martyr(self.app, intro=True)

    def _ticket(self) -> None:
        from tanks.match.sessions import start_ticket
        save, it = self.app.save, self.item
        if not save.tickets_open():
            self.pending = False
            self.msg, self.msg_ok, self.msg_t = "SEALED - BEAT THE MASTER AND THE FINAL MISSION", False, 3.0
        elif save.tickets_sold_out():
            self.msg, self.msg_ok, self.msg_t = "SOLD OUT - EVERY BOSS IS DEFEATED", False, 2.5
        elif save.ticket_active:                              # a drawn boss is waiting: no new charge
            start_ticket(self.app, save.ticket_active)
        elif save.shortfall(it):
            self.pending = False
            self.msg, self.msg_ok, self.msg_t = save.shortfall(it), False, 2.5
        elif not self.pending:
            self.pending = True
        else:
            self.pending = False
            self.app._wallet_flash = 1.4
            start_ticket(self.app, save.buy_ticket(it))

    def update(self, dt: float) -> None:
        super().update(dt)
        self.stage.update(dt)
        self.msg_t = max(0.0, self.msg_t - dt)

    # -- preview -------------------------------------------------------------
    def _map_preview(self, m: MapDefinition) -> PixelCanvas:
        if m.key not in self.maps:
            rng = random.Random(1)
            terrain = Terrain(34, 20, m, rng)
            tanks = []
            for i in range(2):
                x = int(m.spawns[i] * 34)
                terrain.flatten(x + 0.5, 10)
                tanks.append(x + 0.5)
            scen = Scenery(34, 20, m.theme, rng)
            scen.apply_terrain(terrain)
            self.maps[m.key] = (scen, terrain, tanks)
        scen, terrain, tanks = self.maps[m.key]
        t, cv = self.app.time, scen.canvas()
        scen.draw_stars(cv, t)
        scen.draw_aurora(cv, t)
        scen.draw_fx(cv, t)
        for i, x in enumerate(tanks):
            draw_tank(cv, x, terrain.support_height(x), 1 if i == 0 else -1, 50 if i == 0 else 130, (230, 190, 90) if i == 0 else (90, 190, 230),
                      t=t)
        return cv

    def _preview(self, it: ShopItem) -> PixelCanvas:
        """Previews always use the game's first tank, first ammo and default colours - never the player's loadout - so an
        RGB shell is not hidden by an RGB-coloured current setup, and every ammo is judged on the same stage."""
        design, ammo = DESIGN_BY_KEY["ranger"], AMMO_BY_KEY["standard"]
        hull, shot = COLOR_BY_NAME["CYAN"], COLOR_BY_NAME["YELLOW"]
        kind, _, key = it.uid.partition(":")
        if it.uid == "ticket":
            return ticket_art(self.app.save, self.app.time)
        if it.uid == "timemachine":
            return martyr_art(self.app.save, self.app.time)
        if kind == "map":
            return self._map_preview(SPECIAL_MAP_BY_KEY[key])
        if kind == "theme":
            return theme_preview(HOME_THEMES[key.upper()], self.app.time, hull)
        if kind == "tank":
            design = DESIGN_BY_KEY[key]
        elif kind == "ammo":
            ammo = AMMO_BY_KEY[key]
        elif kind == "paint":
            hull = shot = PAINT_BY_KEY[key]
        elif key == "hull":
            hull = RAINBOW
        elif key == "shell":
            shot = RAINBOW
        self.stage.set_kit(design, hull, ammo, shot, 0.0)
        return self.stage.render()

    # -- drawing -------------------------------------------------------------
    def _price(self, it: ShopItem) -> str:
        c = f"{it.coins // 1000}K" if it.coins >= 10000 and it.coins % 1000 == 0 else f"{it.coins}"
        return f"{c}◉" + (f" {it.credits}◈" if it.credits else "")

    _BREAKS = {"GRAVEDIGGER": ("GRAVE-", "DIGGER"), "DOOMBRINGER": ("DOOM-", "BRINGER"), "EVISCERATOR": ("EVISCER-", "ATOR"),
               "SINGULARITY": ("SINGU-", "LARITY"), "STORMBRINGER": ("STORM-", "BRINGER"), "CONSTELLATION": ("CONSTEL-", "LATION"),
               "THUNDERHEAD": ("THUNDER-", "HEAD"), "SHATTERLINE": ("SHATTER-", "LINE"), "MARTYR'S TIME MACHINE": ("TIME", "MACHINE")}

    @staticmethod
    def _tile_lines(name: str, w: int) -> list:
        """A tile name on at most two lines: whole words where they fit, a syllable break only for a word longer than the tile."""
        if name in ShopScene._BREAKS:
            return list(ShopScene._BREAKS[name])
        words, lines = name.split(), [""]
        for wd in words:
            while len(wd) > w:                                    # one very long word: hyphenate it
                room = w - len(lines[-1]) - (1 if lines[-1] else 0)
                if room >= 4:
                    cut = room - 1
                    lines[-1] = (lines[-1] + " " if lines[-1] else "") + wd[:cut] + "-"
                    wd = wd[cut:]
                lines.append("")
            if not lines[-1]:
                lines[-1] = wd
            elif len(lines[-1]) + 1 + len(wd) <= w:
                lines[-1] += " " + wd
            else:
                lines.append(wd)
        lines = [ln for ln in lines if ln]
        if len(lines) > 2:
            lines = [lines[0], " ".join(lines[1:])]
            if len(lines[1]) > w:
                lines[1] = lines[1][:w - 1] + "…"
        return lines

    KIND = {"tank": "TANK", "ammo": "AMMO", "map": "MAP", "theme": "MAIN SCREEN", "rgb": "EXTRA", "paint": "EXTRA", "ticket": "TICKET", "timemachine": "ARTIFACT"}

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        save, t, W = self.app.save, self.app.time, self.W
        ph, vis = self._view_rows(screen.rows)
        x0, y0 = (screen.cols - W) // 2, max(1, (screen.rows - ph - 3) // 2)
        screen.text(x0 + 1, y0, "S H O P", GOLD)
        tx = x0 + 14
        for i, name in enumerate(SHOP_PAGES):
            lab = f" {i + 1} {name} "
            sel = i == self.page
            screen.text(tx, y0, lab, Palette.INK if sel else Palette.MUTED, GOLD if sel else Palette.PANEL)
            tx += len(lab) + 1
        screen.fill(x0, y0 + 1, W, 1, Palette.BG, "─", Palette.LINE)
        grid = self.grid()
        self._fit(vis)
        top = self.scroll.get(self.page, 0)
        sel_r, sel_c = self.pos[self.page]
        sel_r = min(sel_r, len(grid) - 1)
        title = SHOP_PAGES[self.page] + (f"  ·  ROW {sel_r + 1}/{len(grid)}" if len(grid) > vis else "")
        screen.box(x0, y0 + 2, 57, ph, "double", Palette.LINE, Palette.PANEL, title)
        for k in range(vis):                                  # the visible window of rows; tier colour alone marks the tier
            r = top + k
            if r >= len(grid):
                break
            row, gy = grid[r], y0 + 4 + k * 4
            col = TIER_COLORS[row[0].tier]
            for dy in (0, 1, 2):
                bar = rainbow(t + r * 0.1 + dy * 0.05) if row[0].tier >= 4 else col      # the premium rows shimmer
                screen.put(x0 + 1, gy + dy, "▌", bar, Palette.PANEL)
            for c, it in enumerate(row):
                x = x0 + 2 + c * (self.CW + self.GAP)
                sel = (r, c) == (sel_r, sel_c)
                owned = save.is_unlocked(it.uid)
                bg = Palette.PANEL_HI if sel else Palette.PANEL
                screen.fill(x, gy, self.CW, 3, bg)
                for li, ln in enumerate(self._tile_lines(it.name, self.CW)):
                    screen.text(x, gy + li, ln, Palette.WHITE if sel else (Palette.OK if owned else col), bg)
                if it.uid == "ticket":
                    price, pc = (("SOLD OUT", Palette.MUTED) if owned else ("SEALED", Palette.MUTED) if not save.tickets_open()
                                 else (("RESUME" if save.ticket_active else self._price(it)), Palette.AMBER))
                elif it.uid == "timemachine":
                    price, pc = (("✓ BEATEN", Palette.OK) if owned else ("LOCKED", Palette.MUTED) if not save.martyr_available()
                                 else (("RESUME", Palette.AMBER) if save.martyr_paid else (self._price(it), Palette.AMBER)))
                elif owned:
                    price, pc = "✓ OWNED", Palette.OK
                else:
                    price = self._price(it)
                    pc = Palette.AMBER if not save.shortfall(it) else (200, 90, 90)
                screen.text(x, gy + 2, price, pc, bg)
                if sel:
                    screen.put(x - 1, gy, "▸", GOLD, Palette.PANEL)
        if len(grid) > vis:                                   # scroll bar
            track = ph - 3
            thumb = max(1, track * vis // len(grid))
            pos = (track - thumb) * top // max(1, len(grid) - vis)
            for k in range(track):
                screen.put(x0 + 56, y0 + 3 + k, "█" if pos <= k < pos + thumb else "│", GOLD if pos <= k < pos + thumb else Palette.LINE, Palette.PANEL)
            if top > 0:
                screen.put(x0 + 56, y0 + 2, "▲", GOLD, Palette.PANEL)
            if top + vis < len(grid):
                screen.put(x0 + 56, y0 + 2 + ph - 1, "▼", GOLD, Palette.PANEL)
        # detail panel (works for the selected item even when its row is scrolled out of view)
        it = self.item
        px, py = x0 + 58, y0 + 2
        col = TIER_COLORS[it.tier]
        owned = save.is_unlocked(it.uid)
        screen.box(px, py, 36, 21, "double", rainbow(t) if it.tier >= 4 else col, Palette.PANEL, "ITEM")
        screen.blit(self._preview(it), px + 1, py + 1)
        screen.center(py + 11, it.name, Palette.WHITE, Palette.PANEL, px, 36)
        screen.center(py + 12, self.KIND[it.uid.split(":")[0]] + ("  ·  PREMIUM" if it.tier >= 4 else ""), col, Palette.PANEL, px, 36)
        for k, line in enumerate(textwrap.wrap(it.blurb, 32)[:4]):
            screen.center(py + 13 + k, line, Palette.TEXT, Palette.PANEL, px, 36)
        if it.uid == "ticket":
            sub = "SOLD OUT" if owned else "SEALED: BEAT THE MASTER + FINAL MISSION" if not save.tickets_open() else (f"ACTIVE BOSS: {TICKET_BOSS_BY_KEY[save.ticket_active].name}" if save.ticket_active
                                          else f"PRICE  {it.coins} ◉  {it.credits} ◈")
            screen.center(py + 17, sub, Palette.OK if owned else GOLD, Palette.PANEL, px, 36)
        elif it.uid == "timemachine":
            sub = ("DUEL COMPLETE" if owned else "DEFEAT ALL 10 VAULT BOSSES TO UNLOCK" if not save.martyr_available()
                   else f"PHASE {save.martyr_phase + 1}/3 - RESUME" if save.martyr_paid else f"PRICE  {it.coins:,} ◉  {it.credits} ◈")
            screen.center(py + 17, sub, Palette.OK if owned else GOLD if save.martyr_available() else Palette.MUTED, Palette.PANEL, px, 36)
        else:
            screen.center(py + 17, "OWNED" if owned else f"PRICE  {it.coins} ◉" + (f"  {it.credits} ◈" if it.credits else ""),
                          Palette.OK if owned else GOLD, Palette.PANEL, px, 36)
        if self.msg_t > 0:
            screen.center(py + 19, self.msg, Palette.OK if self.msg_ok else Palette.DANGER, Palette.PANEL, px, 36)
        elif it.uid == "timemachine":
            if self.pending and int(t * 3) % 2 == 0:
                screen.center(py + 19, "ENTER AGAIN TO CONTINUE  ·  ESC CANCEL", Palette.AMBER, Palette.PANEL, px, 36)
            elif not self.pending:
                screen.center(py + 19, "[ENTER] " + ("REPLAY" if owned else "RESUME" if save.martyr_paid else "BUY"), Palette.PRIMARY, Palette.PANEL, px, 36)
        elif it.uid == "ticket" and not owned and not save.tickets_open():
            screen.center(py + 19, "[ENTER] WHY IS IT SEALED?", Palette.MUTED, Palette.PANEL, px, 36)
        elif it.uid == "ticket" and not owned:
            n = len(save.tickets_won & set(TICKET_BOSS_BY_KEY))
            if self.pending and int(t * 3) % 2 == 0:
                screen.center(py + 19, "ENTER AGAIN TO BUY  ·  ESC CANCEL", Palette.AMBER, Palette.PANEL, px, 36)
            elif not self.pending:
                screen.center(py + 19, f"[ENTER] {'RESUME FIGHT' if save.ticket_active else 'BUY'}   {n}/{len(TICKET_BOSS_BY_KEY)} BEATEN",
                              Palette.PRIMARY, Palette.PANEL, px, 36)
        elif owned:
            hint = {"tank": "PICK IT IN PILOT SETUP", "ammo": "PICK IT IN PILOT SETUP", "map": "PICK IT IN BATTLEFIELD",
                    "theme": "SET IT IN SETTINGS OR PRESS H", "rgb": "PICK IT IN PILOT SETUP", "paint": "PICK IT IN PILOT SETUP OR THE WORKSHOP", "ticket": "ALL BOSSES DEFEATED"}[it.uid.split(":")[0]]
            screen.center(py + 19, hint, Palette.MUTED, Palette.PANEL, px, 36)
        elif self.pending:
            if int(t * 3) % 2 == 0:
                screen.center(py + 19, "ENTER AGAIN TO BUY  ·  ESC CANCEL", Palette.AMBER, Palette.PANEL, px, 36)
        else:
            why = save.shortfall(it)
            screen.center(py + 19, why if why else "[ENTER] BUY", (200, 90, 90) if why else Palette.PRIMARY, Palette.PANEL, px, 36)
        draw_keycaps(screen, x0 + 2, y0 + ph + 2, (("1-5", "PAGE"), ("TAB", "NEXT"), ("WASD", "SELECT"), ("SHIFT+W/S", "PAGE UP/DN"), ("ENTER", "BUY"), ("ESC", "BACK")))
