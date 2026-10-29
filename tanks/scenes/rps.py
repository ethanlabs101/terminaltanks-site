"""Rock-paper-scissors: decides who shoots first in Two Player and LAN."""
from __future__ import annotations

import math
from typing import Optional

from tanks.colors import GOLD, Palette, RGB, clamp, ease_out, mix, shade
from tanks.content.paints import live_color
from tanks.match.sessions import MatchSession
from tanks.scenes.base import BackdropScene
from tanks.scenes.battle import BattleScene
from tanks.scenes.main_menu import MenuScene
from tanks.screen import PixelCanvas, Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.widgets import draw_keycaps, panel


RPS_NAMES = ("ROCK", "PAPER", "SCISSORS")


def _hp_ell(cv, cx: float, cy: float, rx: float, ry: float, col: RGB, y_shade: float = 0.0) -> None:
    for dx in range(-int(rx) - 1, int(rx) + 2):
        for dy in range(-int(ry) - 1, int(ry) + 2):
            if (dx / max(0.5, rx)) ** 2 + (dy / max(0.5, ry)) ** 2 <= 1.0:
                cv.plot(int(cx + dx), int(cy + dy), shade(col, 1.0 - y_shade * (0.5 - dy / (2 * max(0.5, ry)))))


def _hp_cap(cv, x0: float, y0: float, x1: float, y1: float, w: float, col: RGB, y_shade: float = 0.0) -> None:
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(n + 1):
        u = i / n
        _hp_ell(cv, x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, w / 2, w / 2, col, y_shade)


def hand_sprite(kind: int, skin: RGB, sleeve: RGB, bob: float = 0.0, mirror: bool = False) -> "PixelCanvas":
    """A 32x36 pixel-art hand (0 rock, 1 paper, 2 scissors), outlined and lit from above, wearing a coloured cuff.
    Drawn twice (a dark expanded pass, then the skin) so every shape gets a clean outline."""
    W, H = 32, 36
    cv = PixelCanvas(W, H, (0, 0, 0))
    ol = (46, 26, 24)

    def parts(grow: float, col: RGB, sh: float) -> None:
        g = grow
        if kind == 0:                                                       # ROCK: a clenched fist
            _hp_ell(cv, 16, 13, 9 + g, 7.5 + g, col, sh)
            for i in range(4):
                _hp_ell(cv, 9.6 + i * 4.3, 19.2, 2.7 + g, 3.4 + g, col, sh)
            _hp_cap(cv, 7, 11, 15, 14.5, 4.6 + 2 * g, col, sh)               # the thumb across the front
        elif kind == 1:                                                     # PAPER: a flat open hand, fingers fanned
            _hp_ell(cv, 16, 12, 8.2 + g, 6.6 + g, col, sh)
            for i, ang in enumerate((-13, -4, 5, 14)):
                a = math.radians(ang)
                ln = (14, 16, 15.5, 12)[i]
                bx = 11 + i * 3.3
                _hp_cap(cv, bx, 16, bx + math.sin(a) * ln, 16 + math.cos(a) * ln, 3.3 + 2 * g, col, sh)
            _hp_cap(cv, 8, 10, 2.5, 19, 3.8 + 2 * g, col, sh)                # thumb out to the side
        else:                                                               # SCISSORS: index + middle in a V, the rest curled
            _hp_ell(cv, 16, 11, 8.2 + g, 6.2 + g, col, sh)
            _hp_cap(cv, 12, 15, 6.5, 31, 3.6 + 2 * g, col, sh)
            _hp_cap(cv, 19, 15, 25, 31, 3.6 + 2 * g, col, sh)
            for cx_ in (11.5, 16.5):
                _hp_ell(cv, cx_, 14.5, 2.7 + g, 2.5 + g, col, sh)            # ring + little finger folded down
            _hp_cap(cv, 8, 10, 15, 13, 4.0 + 2 * g, col, sh)
    parts(1.0, ol, 0.0)
    # sleeve / cuff (outlined)
    for x in range(8, 25):
        for y in range(0, 7):
            cv.plot(x, y, ol)
    for x in range(9, 24):
        for y in range(1, 6):
            cv.plot(x, y, shade(sleeve, 0.7 + 0.3 * (y / 5)))
    for x in range(9, 24):
        cv.plot(x, 6, mix(sleeve, (255, 255, 255), 0.45))
    parts(0.0, skin, 0.45)
    # knuckle / finger lines for a hand-drawn feel
    if kind == 0:
        for i in range(3):
            for y in range(16, 19):
                cv.plot(int(11.9 + i * 4.3), y, shade(skin, 0.62))
    elif kind == 1:
        for i in range(3):
            cv.plot(int(13.6 + i * 3.3), 18, shade(skin, 0.6))
    if mirror:
        cv.rows = [row[::-1] for row in cv.rows]
    return cv


def blit_sprite(dst: "PixelCanvas", src: "PixelCanvas", x: int, y: int, flip_y: bool = False) -> None:
    """Copies every non-black pixel of src onto dst at (x, y) (both y-up)."""
    for sy in range(src.h):
        for sx in range(src.w):
            c = src.rows[src.h - 1 - sy][sx]
            if c != (0, 0, 0):
                dst.plot(x + sx, y + sy, c)


class RPSScene(BackdropScene):
    """Local: players pick one after the other (the other looks away). LAN: both pick on their own machine; picks travel as
    {"t":"rps","c":n} and the winner's choice as {"t":"rpsfirst","p":seat}. Ties repeat. Sets session.first_offset, then battle."""

    def __init__(self, app, session: "MatchSession", seat: Optional[int] = None) -> None:
        super().__init__(app)
        self.s, self.seat, self.net = session, seat, session.config.net
        self.picks: list = [None, None]
        self.stage, self.turn, self.sel, self.t, self.winner, self.note = "pick", 0, 0, 0.0, None, ""
        self.cpu = session.config.mode == "single"      # vs the computer: seat 1 is the CPU and picks at random
        if self.cpu:
            self.names = ["YOU", "CPU"]
        else:
            pl = [p for p in session.config.players if not p.is_ai][:2]
            self.names = [(p.name or f"PLAYER {i + 1}")[:14] for i, p in enumerate(pl)] + ["PLAYER 1", "PLAYER 2"][len(pl):]
        self.choice = 0                                 # FIRST (0) / SECOND (1)

    @staticmethod
    def beats(a: int, b: int) -> bool:
        return (a - b) % 3 == 1

    def _finish(self, first_seat: int) -> None:
        self.s.first_offset = first_seat % 2
        self.app.goto(BattleScene(self.app, self.s))

    def _both(self) -> None:
        a, b = self.picks
        self.stage, self.t = "count", 0.0                 # both hands shake: ROCK... PAPER... SCISSORS... SHOOT!
        self.winner = None if a == b else (0 if self.beats(a, b) else 1)

    def update(self, dt: float) -> None:
        from tanks.scenes.lan import NetNoticeScene
        super().update(dt)
        self.t += dt
        if self.net is not None:
            self.net.pump()
            if self.net.take("quit") or self.net.dead:
                self.net.close()
                self.app.goto(NetNoticeScene(self.app, "OPPONENT LEFT", "The other player left the match."))
                return
            peer = 1 - self.seat
            m = self.net.peek("rps")
            if m is not None and self.picks[peer] is None and isinstance(m.get("c"), int):
                self.net.drop(m)
                self.picks[peer] = int(m["c"]) % 3
                if self.picks[self.seat] is not None:
                    self._both()
            f = self.net.peek("rpsfirst")
            if f is not None and self.stage == "wait":
                self.net.drop(f)
                self._finish(int(f.get("p", 0)))
                return
        if self.stage == "cpufirst" and self.t > 1.6:
            self._finish(1)
            return
        if self.stage == "count":
            beat = min(3, int(self.t / 0.6))
            if beat != getattr(self, "_beat", -1):
                self._beat = beat
                self.app.sfx("rps_shake" if beat < 3 else "rps_reveal", 0.9)
        else:
            self._beat = -1
        if self.stage == "count" and self.t > 2.3:
            self.stage, self.t = "reveal", 0.0
        elif self.stage == "reveal" and self.t > 2.0:
            if self.winner is None:
                self.picks, self.stage, self.turn, self.note = [None, None], "pick", 0, "TIE! PICK AGAIN"
            elif self.cpu and self.winner == 1:
                self.stage, self.t = "cpufirst", 0.0                  # the computer won: it shoots first
            elif self.net is None:
                self.stage = "choose"
            else:
                self.stage = "choose" if self.winner == self.seat else "wait"

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK and self.net is None:
            self.app.goto(MenuScene(self.app))
            return
        if ev.action in (Action.LEFT, Action.RIGHT, Action.UP, Action.DOWN):
            d = -1 if ev.action in (Action.LEFT, Action.UP) else 1
            if self.stage == "pick":
                self.sel = (self.sel + d) % 3
            elif self.stage == "choose":
                self.choice = 1 - self.choice
        elif ev.raw in ("1", "2", "3") and self.stage == "pick":
            self.sel = int(ev.raw) - 1
        elif ev.confirm:
            if self.stage == "pick":
                if self.net is not None:
                    if self.picks[self.seat] is None:
                        self.picks[self.seat] = self.sel
                        self.net.send({"t": "rps", "c": self.sel})
                        if self.picks[1 - self.seat] is not None:
                            self._both()
                elif self.cpu:
                    self.picks = [self.sel, self.app.rng.randrange(3)]
                    self._both()
                else:
                    self.picks[self.turn] = self.sel
                    if self.turn == 0:
                        self.turn, self.sel = 1, 0
                    else:
                        self._both()
                self.note = ""
            elif self.stage == "choose":
                w = self.winner
                first_seat = w if self.choice == 0 else 1 - w
                if self.net is not None:
                    self.net.send({"t": "rpsfirst", "p": first_seat})
                self._finish(first_seat)

    SKINS = ((244, 204, 170), (176, 118, 84))

    def _hands(self, screen: Screen, x: int, y: int, kinds: tuple, bobs: tuple, glow: Optional[int] = None) -> None:
        """Two pixel-art hands facing each other, half-block rendered into the panel."""
        W_PX, H_PX = 84, 38
        cv = PixelCanvas(W_PX, H_PX, (0, 0, 0))
        cols = [live_color(p.tank_color, self.app.time) for p in self.s.config.players if not p.is_ai][:2]
        cols += [(90, 200, 255), (255, 150, 90)][len(cols):]
        for k in range(2):
            sp = hand_sprite(kinds[k], self.SKINS[k], cols[k], mirror=bool(k))
            hx = 6 if k == 0 else W_PX - 6 - sp.w
            blit_sprite(cv, sp, hx, int(bobs[k]))
        top = y
        for r in range(H_PX // 2):
            for c in range(W_PX):
                a_, b_ = cv.rows[2 * r][c], cv.rows[2 * r + 1][c]
                if a_ == (0, 0, 0) and b_ == (0, 0, 0):
                    continue
                bgc = Palette.PANEL
                screen.put(x + c, top + r, "▀", bgc if a_ == (0, 0, 0) else a_, bgc if b_ == (0, 0, 0) else b_)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        W, H = 92, 26
        x, y = panel(screen, W, H, "WHO SHOOTS FIRST?")
        me = self.seat
        gx = x + (W - 84) // 2                                        # the hands' stage, centred
        if self.stage == "pick":
            who = (f"{self.names[me]}: CHOOSE YOUR HAND" if me is not None else "CHOOSE YOUR HAND  (the CPU picks at random)" if self.cpu
                   else f"{self.names[self.turn]}: CHOOSE  (the other player look away!)")
            screen.center(y + 1, who, GOLD, Palette.PANEL, x, W)
            locked = self.net is not None and self.picks[me] is not None
            for i in range(3):
                bx = x + 10 + i * 27
                sel = i == self.sel and not locked
                sp = hand_sprite(i, self.SKINS[(me if me is not None else self.turn) % 2], (90, 200, 255) if (me or self.turn) == 0 else (255, 150, 90))
                cv = PixelCanvas(32, 36, (0, 0, 0))
                blit_sprite(cv, sp, 0, 3 if sel and int(self.app.time * 4) % 2 else 0)
                for r in range(18):
                    for c in range(32):
                        a_, b_ = cv.rows[2 * r][c], cv.rows[2 * r + 1][c]
                        if a_ == (0, 0, 0) and b_ == (0, 0, 0):
                            continue
                        dim = 1.0 if (sel or locked is False) else 0.55
                        screen.put(bx + c - 2, y + 4 + r, "▀", shade(Palette.PANEL, 1) if a_ == (0, 0, 0) else shade(a_, dim if sel else 0.6),
                                   Palette.PANEL if b_ == (0, 0, 0) else shade(b_, dim if sel else 0.6))
                screen.center(y + 22, "", Palette.PANEL, Palette.PANEL, x, W) if False else None
                screen.text(bx + 8 - len(RPS_NAMES[i]) // 2 + 3, y + 21, ("▶ " if sel else "  ") + RPS_NAMES[i], Palette.WHITE if sel else Palette.MUTED, Palette.PANEL)
            if locked:
                screen.center(y + 23, "LOCKED IN - WAITING FOR THE OTHER PLAYER...", Palette.MUTED, Palette.PANEL, x, W)
            elif self.note:
                screen.center(y + 23, self.note, Palette.AMBER, Palette.PANEL, x, W)
            draw_keycaps(screen, x + 22, y + H - 2, (("◄ ►", "CHOOSE"), ("ENTER", "LOCK IN"), ("1 2 3", "QUICK PICK")), Palette.PANEL)
        elif self.stage == "count":
            beat = int(self.t / 0.5)
            word = ("ROCK...", "PAPER...", "SCISSORS...", "SHOOT!", "SHOOT!")[min(4, beat)]
            bobs = tuple(max(0, 14 * abs(math.sin(self.t * math.pi / 0.5)) - 2) if beat < 3 else 0 for _ in range(2))
            self._hands(screen, gx, y + 4, (0, 0), bobs)
            screen.center(y + 22, word, GOLD if beat >= 3 else Palette.WHITE, Palette.PANEL, x, W)
            names = f"{self.names[0]}     vs     {self.names[1]}"
            screen.center(y + 1, names, Palette.AMBER, Palette.PANEL, x, W)
        elif self.stage == "reveal":
            a, b = self.picks
            self._hands(screen, gx, y + 4, (a, b), (4 * ease_out(clamp(self.t / 0.2, 0, 1)),) * 2, self.winner)
            screen.center(y + 1, f"{self.names[0]}     vs     {self.names[1]}", Palette.AMBER, Palette.PANEL, x, W)
            if self.t < 0.12:
                screen.tint(x, y, W, H, (255, 255, 255), 0.5 * (1 - self.t / 0.12))
            screen.center(y + 21, f"{RPS_NAMES[a]}   vs   {RPS_NAMES[b]}", Palette.WHITE, Palette.PANEL, x, W)
            screen.center(y + 23, "IT'S A TIE!" if self.winner is None else f"{self.names[self.winner]} {'WIN' if self.names[self.winner] == 'YOU' else 'WINS'}!", Palette.OK if self.winner is not None else Palette.AMBER, Palette.PANEL, x, W)
        elif self.stage == "choose":
            screen.center(y + 3, f"{self.names[self.winner]} WON", GOLD, Palette.PANEL, x, W)
            screen.center(y + 5, "CHOOSE WHO SHOOTS FIRST", Palette.WHITE, Palette.PANEL, x, W)
            for i, lab in enumerate(("GO FIRST", "GO SECOND")):
                sel = i == self.choice
                screen.fill(x + 30, y + 9 + i * 4, 32, 3, Palette.PANEL_HI if sel else Palette.PANEL)
                screen.center(y + 10 + i * 4, ("▶ " if sel else "  ") + lab + (" ◀" if sel else "  "), GOLD if sel else Palette.TEXT, Palette.PANEL_HI if sel else Palette.PANEL, x + 30, 32)
            draw_keycaps(screen, x + 28, y + H - 2, (("◄ ►", "CHOOSE"), ("ENTER", "CONFIRM")), Palette.PANEL)
        elif self.stage == "cpufirst":
            screen.center(y + 10, "THE CPU WINS - IT SHOOTS FIRST", Palette.AMBER, Palette.PANEL, x, W)
        else:
            screen.center(y + 10, f"{self.names[self.winner]} WON - CHOOSING WHO GOES FIRST...", Palette.AMBER, Palette.PANEL, x, W)
