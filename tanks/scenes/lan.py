"""LAN screens: match rules, host, join, and network notices."""
from __future__ import annotations

import textwrap
from dataclasses import replace
from typing import Callable, Optional

from tanks import __version__
from tanks.colors import GOLD, Palette, clamp
from tanks.config import LAN_PORT
from tanks.content.ammo import AMMO_BY_KEY, BLESSING_KEY, DEFAULT_AMMO
from tanks.content.maps import MAPS, all_maps
from tanks.content.missions import MISSIONS
from tanks.content.paints import COLOR_BY_NAME
from tanks.content.tanks import DESIGNS, DESIGN_BY_KEY
from tanks.match.lan import lan_players, loadout_from_json, loadout_json, player_from_json, player_to_json
from tanks.match.rules import HP_PRESETS, ROUND_PRESETS, Rules, WIND_MODES
from tanks.match.sessions import MatchConfig, MatchSession, build_mission_session
from tanks.net import Connector, LanBrowser, LanHost, NetLink, field_size, local_ips
from tanks.save import Loadout
from tanks.scenes.base import BackdropScene
from tanks.scenes.battle import BattleScene
from tanks.scenes.main_menu import MenuScene
from tanks.scenes.rps import RPSScene
from tanks.scenes.setup import SetupScene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import MenuList, draw_keycaps, panel, render_map_preview, wrap_center


class RulesScene(BackdropScene):
    """Pick BEST OF / FIRST TO, rounds, hearts, the battlefield (live terrain scan), WIND, SPECIAL AMMO and the special attack. Remembered."""

    def __init__(self, app, title: str, on_done: Callable, kind: str = "two") -> None:
        super().__init__(app)
        self.title, self.on_done, self.kind = title, on_done, kind
        self.rkey = "rules_single" if kind == "single" else "rules_lan" if kind == "lan" else "rules"
        old = app.save.settings.get(self.rkey)
        self.rules = Rules.load(old if old is not None else app.save.settings.get("rules", "") if kind == "lan" else "")
        if old is None and kind == "lan":
            self.rules.blessing = False                      # LAN used to share the two-player entry: never inherit its Blessing choice
        if not app.save.blessing_unlocked():
            self.rules.blessing = False
        self.row = 0
        self.maps = [None] + list(MAPS) + app.save.unlocked_maps()           # None = RANDOM
        self.cache: dict = {}

    def keys(self) -> list:
        r = self.rules
        k = ["fmt", "n"] + (["n_custom"] if ROUND_PRESETS[r.n_idx] == 0 else [])
        k += ["hp"] + (["hp_custom"] if HP_PRESETS[r.hp_idx] == 0 else [])
        return k + ["map", "next", "wind", "ammo", "blessing", "special", "go"]

    def _map_index(self) -> int:
        return next((i for i, m in enumerate(self.maps) if m is not None and m.key == self.rules.map_key), 0)

    def handle(self, ev: InputEvent) -> None:
        keys, r = self.keys(), self.rules
        self.row = min(self.row, len(keys) - 1)
        if ev.action is Action.BACK:
            self.app.goto(LanMenuScene(self.app) if self.kind == "lan" else MenuScene(self.app))
        elif ev.action is Action.UP:
            self.row = (self.row - 1) % len(keys)
        elif ev.action is Action.DOWN:
            self.row = (self.row + 1) % len(keys)
        elif ev.action in (Action.LEFT, Action.RIGHT):
            d, k = (-1 if ev.action is Action.LEFT else 1), keys[self.row]
            step = d * (5 if ev.coarse else 1)
            if k == "fmt":
                r.fmt = "first" if r.fmt == "best" else "best"
            elif k == "n":
                r.n_idx = (r.n_idx + d) % len(ROUND_PRESETS)
            elif k == "hp":
                r.hp_idx = (r.hp_idx + d) % len(HP_PRESETS)
            elif k == "n_custom":
                r.n_custom = int(clamp(r.n_custom + step, 1, 25))
            elif k == "hp_custom":
                r.hp_custom = int(clamp(r.hp_custom + step, 1, 50))
            elif k == "map":
                m = self.maps[(self._map_index() + step) % len(self.maps)]
                r.map_key = m.key if m else ""
            elif k == "next":
                r.pick_maps = not r.pick_maps
            elif k == "wind":
                r.wind = (r.wind + d) % len(WIND_MODES)
            elif k == "ammo":
                r.ammo_fx = not r.ammo_fx
            elif k == "blessing":
                r.blessing = (not r.blessing) and self.app.save.blessing_unlocked()      # locked: stays OFF
            elif k == "special":
                r.special = not r.special
        elif ev.confirm:
            r.blessing = r.blessing and self.app.save.blessing_unlocked()
            self.app.save.settings[self.rkey] = r.dump()
            self.app.save.flush()
            self.on_done(r)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        r, keys, t = self.rules, self.keys(), self.app.time
        self.row = min(self.row, len(keys) - 1)
        PW, VW = 50, 44
        sp = 2 if 9 + len(keys) * 2 <= screen.rows - 1 else 1
        H = max(22, 9 + len(keys) * sp)
        x, y = (screen.cols - (PW + 1 + VW)) // 2, max(0, (screen.rows - H) // 2)
        screen.box(x, y, PW, H, "double", Palette.LINE, Palette.PANEL, self.title)
        names = {"fmt": "FORMAT", "n": "ROUNDS", "n_custom": "  CUSTOM ROUNDS", "hp": "HEALTH", "hp_custom": "  CUSTOM HEALTH",
                 "map": "BATTLEFIELD", "next": "LATER ROUNDS", "wind": "WIND", "ammo": "SPECIAL AMMO", "blessing": "MARTYR'S BLESSING", "special": "SPECIAL ATTACK", "go": "CONTINUE"}
        mp = self.maps[self._map_index()]
        for i, k in enumerate(keys):
            ry, sel = y + 2 + i * sp, i == self.row
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            screen.fill(x + 2, ry, PW - 4, 1, bg)
            screen.text(x + 4, ry, names[k], Palette.WHITE if sel else Palette.MUTED, bg)
            val = {"fmt": "BEST OF" if r.fmt == "best" else "FIRST TO", "n": str(r.n) if ROUND_PRESETS[r.n_idx] else "CUSTOM",
                   "n_custom": str(r.n_custom), "hp": str(r.hp) if HP_PRESETS[r.hp_idx] else "CUSTOM",
                   "hp_custom": str(r.hp_custom), "map": (f"{self._map_index():03d}/{len(self.maps) - 1} {mp.name}" if mp else "RANDOM"),
                   "next": ("PICK EACH ROUND" if r.pick_maps else "RANDOM"), "wind": WIND_MODES[r.wind][0],
                   "ammo": "ON" if r.ammo_fx else "OFF", "special": "ON" if r.special else "OFF", "go": "▶",
                   "blessing": ("LOCKED" if not self.app.save.blessing_unlocked() else "ON" if r.blessing else "OFF")}[k]
            val = f"◄ {val[:25]} ►" if sel and k != "go" else val[:29]
            screen.text(x + PW - 4 - len(val), ry, val, GOLD if sel else Palette.TEXT, bg)
        screen.center(y + H - 6, f"{r.label}  ·  {r.hp} {'HEART' if r.hp == 1 else 'HEARTS'} EACH  ·  WIND {WIND_MODES[r.wind][0]}",
                      Palette.AMBER, Palette.PANEL, x, PW)
        extra = ("SPECIAL: X banks a turn. Two banked = 3 damage" if r.special
                 else f"A side wins the match with {r.target} round wins")
        screen.center(y + H - 5, extra[:PW - 2], Palette.MUTED, Palette.PANEL, x, PW)
        if keys[self.row] == "ammo":
            tip = ("ON: ✦ ammo really works (bounce, split, cluster, gravity, wind)."
                   if r.ammo_fx else "OFF: every ammo only changes looks - no special-ammo edge.")
            for k, ln in enumerate(textwrap.wrap(tip, PW - 6)[:2]):
                screen.center(y + H - 4 + k, ln, Palette.PRIMARY, Palette.PANEL, x, PW)
        elif keys[self.row] == "blessing":
            tip = ("Defeat the Martyr to inherit this ultimate ammo." if not self.app.save.blessing_unlocked()
                   else "ON: the BLESSING may be loaded - one direct hit erases every foe." if r.blessing
                   else "OFF: MARTYR'S BLESSING cannot be selected or fired in this mode.")
            for k, ln in enumerate(textwrap.wrap(tip, PW - 6)[:2]):
                screen.center(y + H - 4 + k, ln, GOLD, Palette.PANEL, x, PW)
        else:
            screen.center(y + H - 4, "SPECIAL AMMO ON: effects active" if r.ammo_fx else "SPECIAL AMMO OFF: all ammo is cosmetic",
                          Palette.PRIMARY if r.ammo_fx else Palette.MUTED, Palette.PANEL, x, PW)
        draw_keycaps(screen, x + 3, y + H - 2, (("W/S", "ROW"), ("A/D", "CHANGE"), ("SHIFT", "x5"), ("ENTER", "OK")), Palette.PANEL)
        # live terrain scan
        vx = x + PW + 1
        screen.box(vx, y, VW, H, "double", Palette.LINE, Palette.PANEL, "TERRAIN SCAN")
        m = mp or MAPS[int(t / 1.2) % len(MAPS)]
        pl = []
        for i in range(2):
            lo = self.app.save.loadout(i)
            pl.append((DESIGN_BY_KEY.get(lo.tank, DESIGNS[0]), COLOR_BY_NAME[lo.tank_color]))
        screen.blit(render_map_preview(self.cache, m, VW - 4, 24, t, pl), vx + 2, y + 2)
        screen.center(y + 14, (f"{self._map_index():03d}/{len(self.maps) - 1}  " if mp else "") + (m.name if mp else "RANDOM"),
                      m.accent if (mp and m.special) else Palette.AMBER, Palette.PANEL, vx, VW)
        desc = m.description if mp else "A fresh battlefield every round."
        n = wrap_center(screen, y + 15, desc, VW - 4, Palette.TEXT, Palette.PANEL, vx, VW, 3)
        if mp:
            dots = lambda k: "●" * k + "○" * (3 - k)
            screen.center(y + 15 + n + 1, f"COVER {dots(m.cover)}     RELIEF {dots(m.relief)}", Palette.PRIMARY, Palette.PANEL, vx, VW)
        screen.center(y + H - 2, "Opening map only - later rounds rotate", Palette.MUTED, Palette.PANEL, vx, VW)


class NetNoticeScene(BackdropScene):
    show_wallet = True

    def __init__(self, app, title: str, text: str) -> None:
        super().__init__(app)
        self.title, self.text = title, text

    def handle(self, ev: InputEvent) -> None:
        if ev.confirm or ev.action is Action.BACK:
            self.app.goto(MenuScene(self.app))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        x, y = panel(screen, 56, 10, self.title, fg=Palette.DANGER)
        for k, line in enumerate(textwrap.wrap(self.text, 50)[:4]):
            screen.center(y + 2 + k, line, Palette.TEXT, Palette.PANEL, x, 56)
        if int(self.app.time * 2) % 2 == 0:
            screen.center(y + 7, "[ ENTER ]", Palette.PRIMARY, Palette.PANEL, x, 56)


class LanMenuScene(BackdropScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.menu = MenuList(["HOST A GAME", "JOIN A GAME", "PILOT SETUP", "BACK"])

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK:
            self.app.goto(MenuScene(self.app))
            return
        c = self.menu.handle(ev)
        app = self.app
        if c == 0:
            app.goto(RulesScene(app, "LAN MATCH RULES", lambda r: app.goto(LanHostScene(app, r)), kind="lan"))
        elif c == 1:
            app.goto(LanJoinScene(app))
        elif c == 2:
            app.goto(SetupScene(app, "lan", done=lambda _: app.goto(LanMenuScene(app)), pages=1))
        elif c == 3:
            app.goto(MenuScene(app))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        x, y = panel(screen, 56, 14, "LAN PLAY")
        screen.center(y + 2, "Play a friend on the same network.", Palette.TEXT, Palette.PANEL, x, 56)
        screen.center(y + 3, "One hosts, one joins - same rules as Two Player.", Palette.MUTED, Palette.PANEL, x, 56)
        self.menu.draw(screen, screen.cols // 2, y + 6, self.app.time, gap=1, width=26)
        screen.center(y + 11, "Your PLAYER 1 loadout is the one you bring.", Palette.MUTED, Palette.PANEL, x, 56)


class LanHostScene(BackdropScene):
    """Waiting room: shows the address, the rules and the guest; ENTER starts once someone has joined.
    `launch` (optional) builds the match for non-versus games such as co-op missions: launch(app, link, guest_lo) -> None."""

    def __init__(self, app, rules: Optional[Rules], launch: Optional[Callable] = None, title: str = "HOSTING A LAN GAME") -> None:
        super().__init__(app)
        self.rules, self.launch, self.title = rules, launch, title
        self.link: Optional[NetLink] = None
        self.guest: Optional[Loadout] = None
        self.guest_term = None
        self.err = ""
        self.ips = local_ips()
        try:
            self.host: Optional[LanHost] = LanHost("TERMINAL TANKS")
        except OSError as e:
            self.host, self.err = None, str(e)

    def exit(self) -> None:
        if self.host:
            self.host.close()

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.host and self.link is None:
            self.link = self.host.poll(dt)
        if self.link is not None:
            self.link.pump()
            for m in self.link.take("hello"):
                self.guest = loadout_from_json(m.get("lo", {}), self.app.save, 1)
                self.guest_term = tuple(m.get("term", (80, 24)))
                self.link.send({"t": "welcome", "rules": self.rules.summary() if self.rules else self.title})
            if self.link.dead:
                self.link, self.guest = None, None

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK:
            if self.link:
                self.link.send({"t": "quit"})
                self.link.close()
            self.app.goto(LanMenuScene(self.app))
        elif ev.confirm and self.link and self.guest:
            self._start()

    def _start(self) -> None:
        app, link = self.app, self.link
        self.link = None
        if self.launch:
            self.launch(app, link, self.guest, self.guest_term)
            return
        r, s = self.rules, app.save
        players = lan_players(s.loadout(0), self.guest, r.hp)
        bless = bool(r.blessing and s.blessing_unlocked())              # host-authoritative: the host's save and rules decide
        if not bless:
            players = [replace(p, ammo=DEFAULT_AMMO.key) if p.ammo == BLESSING_KEY else p for p in players]
        mine = field_size(app.screen.cols, app.screen.rows)
        world = (min(mine[0], self.guest_term[0]), min(mine[1], self.guest_term[1]))
        seed = app.rng.randrange(1 << 30)
        wind = r.wind_value(app.settings)
        cfg = MatchConfig(players, False, app.settings.difficulty, "lan", target=r.target, label=r.label, net=link, my_owner=0,
                          world_size=world, special=r.special, ammo_fx=r.ammo_fx, pick_maps=r.pick_maps, blessing=bless)
        link.send({"t": "start", "kind": "versus", "players": [player_to_json(p) for p in players], "target": r.target,
                   "label": r.label, "seed": seed, "world": list(world), "wind": wind, "map": r.map_key, "special": r.special, "ammo_fx": r.ammo_fx, "pick": r.pick_maps, "blessing": bless})
        session = MatchSession(cfg, r.mapdef, seed)
        session.wind_override = wind
        app.goto(RPSScene(app, session, 0))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        x, y = panel(screen, 60, 17, self.title)
        if self.err:
            screen.center(y + 4, "Could not open a LAN port:", Palette.DANGER, Palette.PANEL, x, 60)
            screen.center(y + 5, self.err[:50], Palette.MUTED, Palette.PANEL, x, 60)
            return
        screen.center(y + 2, "TELL YOUR FRIEND TO JOIN:", Palette.MUTED, Palette.PANEL, x, 60)
        for k, ip in enumerate(self.ips[:2]):
            screen.center(y + 3 + k, f"{ip}:{self.host.port}", GOLD, Palette.PANEL, x, 60)
        screen.center(y + 6, "(or pick this game from their JOIN list)", Palette.MUTED, Palette.PANEL, x, 60)
        if self.rules:
            screen.center(y + 8, f"{self.rules.label}  ·  {self.rules.hp} HEARTS EACH", Palette.AMBER, Palette.PANEL, x, 60)
        if self.guest:
            screen.center(y + 10, "PLAYER 2 CONNECTED", Palette.OK, Palette.PANEL, x, 60)
            screen.center(y + 11, f"{DESIGN_BY_KEY[self.guest.tank].name} + {AMMO_BY_KEY[self.guest.ammo].name}", Palette.TEXT, Palette.PANEL, x, 60)
            if int(self.app.time * 2) % 2 == 0:
                screen.center(y + 13, "[ ENTER ] START", Palette.PRIMARY, Palette.PANEL, x, 60)
        else:
            dots = "." * (int(self.app.time * 2) % 4)
            screen.center(y + 10, f"WAITING FOR PLAYER 2{dots}", Palette.AMBER, Palette.PANEL, x, 60)
        screen.center(y + 15, "ESC  CANCEL", Palette.MUTED, Palette.PANEL, x, 60)


class LanJoinScene(BackdropScene):
    """Lists games found on the network (or type an IP address), connects, then waits for the host to start."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.browser = LanBrowser()
        self.found: list = []
        self.index = 0
        self.text = ""
        self.conn: Optional[Connector] = None
        self.link: Optional[NetLink] = None
        self.msg = ""
        self.rules_text = ""

    def exit(self) -> None:
        self.browser.close()

    def _connect(self, ip: str, port: int) -> None:
        self.conn, self.msg = Connector(ip, port), ""

    def handle(self, ev: InputEvent) -> None:
        raw = ev.raw
        if ev.action is Action.BACK:
            if self.link:
                self.link.send({"t": "quit"})
                self.link.close()
            self.app.goto(LanMenuScene(self.app))
        elif self.link or self.conn:
            return
        elif raw == "BACKSPACE":
            self.text = self.text[:-1]
        elif len(raw) == 1 and (raw.isdigit() or raw in ".:") and len(self.text) < 21:
            self.text += raw
        elif ev.action is Action.UP:
            self.index = max(0, self.index - 1)
        elif ev.action is Action.DOWN:
            self.index = min(max(0, len(self.found) - 1), self.index + 1)
        elif ev.confirm:
            if self.text:
                host, _, port = self.text.partition(":")
                self._connect(host, int(port) if port.isdigit() else LAN_PORT)
            elif self.found:
                (ip, port), _ = self.found[min(self.index, len(self.found) - 1)]
                self._connect(ip, port)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.found = self.browser.poll()
        if self.conn and not self.link:
            link = self.conn.poll()
            if link:
                self.link, self.conn = link, None
                lo = self.app.save.loadout(0)
                s = self.app.screen
                link.send({"t": "hello", "lo": loadout_json(lo), "term": list(field_size(s.cols, s.rows)), "ver": __version__})
            elif self.conn.error:
                self.msg, self.conn = f"COULD NOT CONNECT: {self.conn.error.upper()}", None
        if self.link:
            self.link.pump()
            for m in self.link.take("welcome"):
                self.rules_text = str(m.get("rules", ""))
            if self.link.take("quit") or self.link.dead:
                self.msg, self.link = "THE HOST CLOSED THE GAME", None
            for m in (self.link.take("start") if self.link else []):
                self._begin(m)

    def _begin(self, m: dict) -> None:
        app, link = self.app, self.link
        players = [player_from_json(p) for p in m["players"]]
        if m.get("kind") == "mission":
            mission = MISSIONS[int(m["n"]) - 1]
            sess = build_mission_session(app, mission, [], net=link, my_owner=1, world=tuple(m["world"]), seed=int(m["seed"]),
                                         humans=players, go=False)
            sess.wind_override = tuple(m["wind"]) if isinstance(m["wind"], list) else float(m["wind"])
            app.goto(BattleScene(app, sess))
            return
        world = tuple(m["world"])
        cfg = MatchConfig(players, False, app.settings.difficulty, "lan", target=int(m["target"]), label=str(m["label"]), net=link,
                          my_owner=1, world_size=world, special=bool(m.get("special", False)), ammo_fx=bool(m.get("ammo_fx", True)), pick_maps=bool(m.get("pick", False)),
                          blessing=bool(m.get("blessing", False)))
        session = MatchSession(cfg, all_maps().get(str(m.get("map", ""))), int(m["seed"]))
        session.wind_override = tuple(m["wind"]) if isinstance(m["wind"], list) else float(m["wind"])
        app.goto(RPSScene(app, session, 1))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        x, y = panel(screen, 60, 18, "JOIN A LAN GAME")
        if self.link:
            screen.center(y + 6, "CONNECTED", Palette.OK, Palette.PANEL, x, 60)
            if self.rules_text:
                screen.center(y + 8, self.rules_text, Palette.AMBER, Palette.PANEL, x, 60)
            dots = "." * (int(self.app.time * 2) % 4)
            screen.center(y + 10, f"WAITING FOR THE HOST TO START{dots}", Palette.TEXT, Palette.PANEL, x, 60)
            screen.center(y + 15, "ESC  LEAVE", Palette.MUTED, Palette.PANEL, x, 60)
            return
        screen.text(x + 4, y + 2, "GAMES ON YOUR NETWORK", Palette.AMBER, Palette.PANEL)
        if not self.found:
            screen.text(x + 4, y + 4, "searching..." if int(self.app.time * 2) % 2 else "searching", Palette.MUTED, Palette.PANEL)
        for i, ((ip, port), info) in enumerate(self.found[:5]):
            sel = i == self.index and not self.text
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            screen.fill(x + 3, y + 4 + i, 54, 1, bg)
            screen.text(x + 4, y + 4 + i, f"{'▸ ' if sel else '  '}{info['name']:<16} {ip}:{port}", Palette.WHITE if sel else Palette.TEXT, bg)
        screen.text(x + 4, y + 10, "OR TYPE AN ADDRESS", Palette.MUTED, Palette.PANEL)
        screen.box(x + 4, y + 11, 40, 3, "single", Palette.LINE, Palette.PANEL_HI)
        cursor = "█" if int(self.app.time * 2) % 2 == 0 else " "
        screen.text(x + 6, y + 12, self.text + cursor, Palette.WHITE, Palette.PANEL_HI)
        if self.conn:
            screen.center(y + 15, "CONNECTING...", Palette.AMBER, Palette.PANEL, x, 60)
        elif self.msg:
            screen.center(y + 15, self.msg[:54], Palette.DANGER, Palette.PANEL, x, 60)
        else:
            screen.center(y + 15, "W/S PICK   ENTER JOIN   ESC BACK", Palette.MUTED, Palette.PANEL, x, 60)
