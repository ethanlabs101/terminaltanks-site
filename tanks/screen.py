"""The two drawing surfaces. PixelCanvas is a free-form pixel buffer drawn with half-block characters (two pixels
per cell); Screen is the cell grid every scene draws into, flushed as minimal ANSI updates (terminal) or as
packed cell records (browser)."""
from __future__ import annotations

import struct
from typing import Optional, Sequence

from tanks.colors import ColorMode, Palette, RGB, clamp, mix, nearest16, resolve_color_mode, shade, to_256
from tanks.config import PAIR_CACHE_MAX


_CELL = struct.Struct("<HHI6B")             # one changed cell for the browser renderer


class PixelCanvas:
    """Square-ish pixel grid (two pixels per terminal row); y grows upward."""
    __slots__ = ("w", "h", "rows")

    def __init__(self, w: int, h: int, fill: RGB = (0, 0, 0), rows=None) -> None:
        self.w, self.h = w, h
        self.rows = rows if rows is not None else [[fill] * w for _ in range(h)]

    def copy(self) -> "PixelCanvas":
        return PixelCanvas(self.w, self.h, rows=[r[:] for r in self.rows])

    def plot(self, x: int, y: int, c: RGB) -> None:
        py = self.h - 1 - y
        if 0 <= x < self.w and 0 <= py < self.h:
            self.rows[py][x] = c

    def blend(self, x: int, y: int, c: RGB, a: float) -> None:
        py = self.h - 1 - y
        if 0 <= x < self.w and 0 <= py < self.h and a > 0.02:
            row = self.rows[py]
            row[x] = mix(row[x], c, a)

    def plotf(self, x: float, y: float, c: RGB) -> None:
        self.plot(int(x // 1), int(y // 1), c)

    def blendf(self, x: float, y: float, c: RGB, a: float) -> None:
        self.blend(int(x // 1), int(y // 1), c, a)


Cell = tuple[str, RGB, RGB]
BOX_STYLES = {"double": "╔╗╚╝═║", "single": "┌┐└┘─│", "round": "╭╮╰╯─│", "heavy": "┏┓┗┛━┃"}


def _shift_row(row: list, dx: int) -> list:
    if dx > 0:
        return [row[0]] * dx + row[:-dx]
    if dx < 0:
        return row[-dx:] + [row[-1]] * (-dx)
    return row


class Screen:
    """Double-buffered cell grid with diffed truecolor/256/16-colour output."""

    def __init__(self, term, mode: ColorMode) -> None:
        self.term = term
        self.cols = self.rows = 0
        self.back: list[list[Cell]] = []
        self._front: Optional[list[list]] = None
        self._pairs: dict = {}
        self.mode = ColorMode.TRUE
        self.set_mode(mode)

    def set_mode(self, mode: ColorMode) -> None:
        self.mode = resolve_color_mode(mode)
        self._pairs.clear()
        self._front = None

    def resize(self, cols: int, rows: int) -> None:
        self.cols, self.rows = cols, rows
        self._front = None
        self.clear()

    def force_redraw(self) -> None:
        self._front = None

    def clear(self, color: RGB = Palette.BG) -> None:
        blank: Cell = (" ", color, color)
        self.back = [[blank] * self.cols for _ in range(self.rows)]

    # -- drawing -------------------------------------------------------------
    def put(self, x: int, y: int, ch: str, fg: RGB, bg: Optional[RGB] = None) -> None:
        if 0 <= x < self.cols and 0 <= y < self.rows:
            if bg is None:
                old = self.back[y][x]
                bg = mix(old[1], old[2], 0.5) if old[0] == "▀" else old[2]
            self.back[y][x] = (ch, fg, bg)

    def text(self, x: int, y: int, s: str, fg: RGB, bg: Optional[RGB] = None) -> None:
        for i, ch in enumerate(s):
            if ch != " " or bg is not None:
                self.put(x + i, y, ch, fg, bg)

    def center(self, y: int, s: str, fg: RGB, bg: Optional[RGB] = None,
               x0: int = 0, width: Optional[int] = None) -> None:
        width = self.cols if width is None else width
        self.text(x0 + (width - len(s)) // 2, y, s, fg, bg)

    def fill(self, x: int, y: int, w: int, h: int, bg: RGB, ch: str = " ", fg: RGB = Palette.TEXT) -> None:
        cell: Cell = (ch, fg, bg)
        for yy in range(max(0, y), min(self.rows, y + h)):
            x0, x1 = max(0, x), min(self.cols, x + w)
            if x1 > x0:
                self.back[yy][x0:x1] = [cell] * (x1 - x0)

    def box(self, x: int, y: int, w: int, h: int, style: str = "double",
            fg: RGB = Palette.LINE, bg: RGB = Palette.PANEL, title: str = "",
            title_fg: RGB = Palette.PRIMARY) -> None:
        tl, tr, bl, br, hz, vt = BOX_STYLES[style]
        self.fill(x, y, w, h, bg)
        for i in range(1, w - 1):
            self.put(x + i, y, hz, fg, bg)
            self.put(x + i, y + h - 1, hz, fg, bg)
        for j in range(1, h - 1):
            self.put(x, y + j, vt, fg, bg)
            self.put(x + w - 1, y + j, vt, fg, bg)
        for (cx, cy, ch) in ((x, y, tl), (x + w - 1, y, tr), (x, y + h - 1, bl), (x + w - 1, y + h - 1, br)):
            self.put(cx, cy, ch, fg, bg)
        if title:
            label = f" {title} "
            self.text(x + (w - len(label)) // 2, y, label, title_fg, bg)

    def blit(self, canvas: PixelCanvas, x: int, y: int, shift: tuple[int, int] = (0, 0)) -> None:
        dx, dy = shift
        rows, h = canvas.rows, canvas.h
        for r in range(h // 2):
            if dx == 0 and dy == 0:
                top, bot = rows[2 * r], rows[2 * r + 1]
            else:
                ty = int(clamp(2 * r - dy, 0, h - 1))
                by = int(clamp(2 * r + 1 - dy, 0, h - 1))
                top, bot = _shift_row(rows[ty], dx), _shift_row(rows[by], dx)
            if 0 <= y + r < self.rows:
                self.back[y + r][x:x + canvas.w] = [("▀", t, b) for t, b in zip(top, bot)]

    def tint(self, x: int, y: int, w: int, h: int, color: RGB, a: float) -> None:
        for yy in range(max(0, y), min(self.rows, y + h)):
            row = self.back[yy]
            for xx in range(max(0, x), min(self.cols, x + w)):
                ch, fg, bg = row[xx]
                row[xx] = (ch, mix(fg, color, a), mix(bg, color, a))

    def dim(self, k: float) -> None:
        for row in self.back:
            row[:] = [(ch, shade(fg, k), shade(bg, k)) for ch, fg, bg in row]

    def fade_rows(self, factors: Sequence[float]) -> None:
        for y, row in enumerate(self.back):
            k = factors[y]
            if k < 0.999:
                row[:] = [(ch, shade(fg, k), shade(bg, k)) for ch, fg, bg in row]

    # -- output --------------------------------------------------------------
    def _encode(self, fg: RGB, bg: RGB) -> str:
        m = self.mode
        if m is ColorMode.TRUE:
            return f"\x1b[38;2;{fg[0]};{fg[1]};{fg[2]};48;2;{bg[0]};{bg[1]};{bg[2]}m"
        if m is ColorMode.ANSI256:
            return f"\x1b[38;5;{to_256(fg)};48;5;{to_256(bg)}m"
        f, b = nearest16(fg), nearest16(bg)
        return f"\x1b[{30 + f if f < 8 else 82 + f};{40 + b if b < 8 else 92 + b}m"

    def _flush_cells(self) -> None:
        """Browser renderer: send only the changed cells as fixed-size records (x, y, codepoint, fg rgb, bg rgb)
        instead of ANSI text; the page paints them on a canvas."""
        full = self._front is None
        if full:
            self._front = [[None] * self.cols for _ in range(self.rows)]
        pack, recs = _CELL.pack, []
        for y in range(self.rows):
            brow, frow = self.back[y], self._front[y]
            if brow == frow:
                continue
            for x in range(self.cols):
                cell = brow[x]
                if cell != frow[x]:
                    ch, fg, bg = cell
                    try:
                        recs.append(pack(x, y, ord(ch[:1] or " "), fg[0], fg[1], fg[2], bg[0], bg[1], bg[2]))
                    except struct.error:                                   # a colour channel out of range: clamp it
                        c = [max(0, min(255, int(v))) for v in (*fg, *bg)]
                        recs.append(pack(x, y, ord(ch[:1] or " "), *c))
            self._front[y] = brow[:]
        if recs or full:
            self.term.present(self.cols, self.rows, full, b"".join(recs))

    def flush(self) -> None:
        if getattr(self.term, "cell_output", False):
            return self._flush_cells()
        if self._front is None:
            self._front = [[None] * self.cols for _ in range(self.rows)]
        out: list[str] = []
        last_pair = None
        cur_x = cur_y = -1
        for y in range(self.rows):
            brow, frow = self.back[y], self._front[y]
            if brow == frow:
                continue
            for x in range(self.cols):
                cell = brow[x]
                if cell == frow[x]:
                    continue
                if cur_y != y or cur_x != x:
                    out.append(f"\x1b[{y + 1};{x + 1}H")
                pair = (cell[1], cell[2])
                if pair != last_pair:
                    seq = self._pairs.get(pair)
                    if seq is None:
                        if len(self._pairs) >= PAIR_CACHE_MAX:     # animated skies mint endless new colours;
                            self._pairs.clear()                    # an unbounded cache here was a slow memory leak
                        seq = self._pairs[pair] = self._encode(*pair)
                    out.append(seq)
                    last_pair = pair
                out.append(cell[0])
                cur_x, cur_y = x + 1, y
            self._front[y] = brow[:]
        if out:
            self.term.write("".join(out))
        if self.rows and self.cols:
            self.term.set_margin(self.back[-1][-1][2])        # the window margin takes the colour of the bottom-right corner
