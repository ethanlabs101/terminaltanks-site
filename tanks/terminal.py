"""Terminal input and output. TerminalIO owns a real terminal (alternate screen, raw keys, guaranteed restore on
exit, Windows and POSIX); WebTerminalIO is the same interface for the browser, where the page owns the screen.
InputManager turns raw keys into Actions."""
from __future__ import annotations

import atexit
import os
import re
import select
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional

from tanks.config import IS_WEB

if os.name == "nt":
    import msvcrt
elif not IS_WEB:
    import termios
    import tty


class TerminalError(RuntimeError):
    pass


class TerminalIO:
    """Owns the raw terminal: alternate screen, cbreak input, guaranteed restore."""

    ENTER = "\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[2J\x1b[H"
    LEAVE = "\x1b[0m\x1b[?7h\x1b[?25h\x1b[?1049l"
    CSI_KEYS = {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}

    def __init__(self) -> None:
        self._active = False
        self._fd = -1
        self._saved = None
        self._buffer = ""
        self.redraw_requested = False
        self._out = getattr(sys.stdout, "buffer", None)
        self._bg0: Optional[str] = None      # the terminal's own background colour (its OSC 11 answer), restored on exit
        self._margin: Optional[tuple] = None  # the colour the game gave the window margin

    def __enter__(self) -> "TerminalIO":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise TerminalError("TerminalTanks needs an interactive terminal.")
        if os.name == "nt":
            self._start_windows()
        else:
            self._start_posix()
        self._active = True
        atexit.register(self.stop)
        self.write(self.ENTER)

    def _start_posix(self) -> None:
        self._fd = sys.stdin.fileno()
        self._saved = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        self._query_background()
        signal.signal(signal.SIGTERM, self._terminate)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._terminate)
        if hasattr(signal, "SIGTSTP"):
            signal.signal(signal.SIGTSTP, self._on_suspend)
            signal.signal(signal.SIGCONT, self._on_resume)

    def _start_windows(self) -> None:
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            kernel.SetConsoleOutputCP(65001)
            handle = kernel.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel.GetConsoleMode(handle, ctypes.byref(mode))
            kernel.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass

    def _query_background(self) -> None:
        """Asks the terminal for its background colour (OSC 11). Only a terminal that answers gets its window margin
        recoloured by set_margin(), so its own colour can always be put back."""
        self.write("\x1b]11;?\x07")
        reply, end = "", time.monotonic() + 0.3
        while time.monotonic() < end and not reply.endswith(("\x07", "\x1b\\")):
            if select.select([self._fd], [], [], 0.05)[0]:
                reply += os.read(self._fd, 256).decode("utf-8", "replace")
        m = re.search(r"\x1b\]11;(rgb:[0-9a-fA-F/]+)(?:\x07|\x1b\\)", reply)
        if m:
            self._bg0, reply = m.group(1), reply[:m.start()] + reply[m.end():]
        self._buffer += reply                # anything typed meanwhile is still a key press

    def set_margin(self, rgb: tuple) -> None:
        """Colours the window's margin (the pixels left over around the character grid) to match the game."""
        if self._bg0 is not None and rgb != self._margin:
            self._margin = rgb
            self.write("\x1b]11;#%02x%02x%02x\x07" % rgb)

    def _restore_margin(self) -> None:
        if self._margin is not None:
            self._margin = None
            self.write(f"\x1b]11;{self._bg0}\x07")

    @staticmethod
    def _terminate(signum, frame) -> None:
        raise SystemExit(128 + signum)

    def _on_suspend(self, signum, frame) -> None:
        self._restore_margin()
        self.write(self.LEAVE)
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTSTP)

    def _on_resume(self, signum, frame) -> None:
        signal.signal(signal.SIGTSTP, self._on_suspend)
        tty.setcbreak(self._fd)
        self.write(self.ENTER)
        self.redraw_requested = True

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self._restore_margin()
        self.write(self.LEAVE)
        if os.name != "nt" and self._saved is not None:
            try:
                termios.tcsetattr(self._fd, termios.TCSAFLUSH, self._saved)
            except termios.error:
                pass

    def write(self, text: str) -> None:
        if self._out is None:
            return
        try:
            self._out.write(text.encode("utf-8", "replace"))
            self._out.flush()
        except (BrokenPipeError, OSError):
            pass

    def size(self) -> tuple[int, int]:
        sz = shutil.get_terminal_size((80, 24))
        return sz.columns, sz.lines

    # -- keyboard ------------------------------------------------------------
    @staticmethod
    def _map_char(ch: str) -> Optional[str]:
        if ch in "\r\n":
            return "ENTER"
        if ch == " ":
            return "SPACE"
        if ch in "\x7f\x08":
            return "BACKSPACE"
        if ch == "\t":
            return "TAB"
        return ch if ch >= " " else None

    def read_keys(self) -> list[str]:
        if os.name == "nt":
            return self._read_windows()
        chunks = []
        while select.select([self._fd], [], [], 0)[0]:
            data = os.read(self._fd, 4096)
            if not data:
                raise SystemExit(0)
            chunks.append(data)
        if chunks:
            self._buffer += b"".join(chunks).decode("utf-8", "ignore")
        return self._parse_buffer()

    def _parse_buffer(self) -> list[str]:
        keys: list[str] = []
        s, i, n = self._buffer, 0, len(self._buffer)
        while i < n:
            ch = s[i]
            if ch == "\x1b":
                if i + 1 >= n:
                    keys.append("ESC")
                    i += 1
                    continue
                if s[i + 1] in "[O":
                    j = i + 2
                    while j < n and not ("@" <= s[j] <= "~"):
                        j += 1
                    if j >= n:
                        break
                    name = self.CSI_KEYS.get(s[j])
                    if name:
                        keys.append(("SHIFT+" if ";2" in s[i + 2:j] else "") + name)
                    i = j + 1
                    continue
                keys.append("ESC")
                i += 1
                continue
            key = self._map_char(ch)
            if key:
                keys.append(key)
            i += 1
        self._buffer = s[i:]
        return keys

    def _read_windows(self) -> list[str]:
        keys: list[str] = []
        table = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                name = table.get(msvcrt.getwch())
                if name:
                    keys.append(name)
            elif ch == "\x03":
                raise KeyboardInterrupt
            elif ch == "\x1b":
                keys.append("ESC")
            else:
                key = self._map_char(ch)
                if key:
                    keys.append(key)
        return keys


class WebTerminalIO(TerminalIO):
    """TerminalIO for the browser: cells out via callbacks, keys and size pushed in by the page."""
    cell_output = True

    def __init__(self, present: Callable, bell: Optional[Callable[[], None]] = None, size: tuple[int, int] = (110, 31)) -> None:
        super().__init__()
        self._present, self._bell = present, bell
        self._size = (max(1, int(size[0])), max(1, int(size[1])))

    def start(self) -> None:
        self._active = True

    def stop(self) -> None:
        self._active = False

    def write(self, text: str) -> None:
        if "\a" in text and self._bell is not None:      # the game's optional sound setting rings the terminal bell
            self._bell()

    def present(self, cols: int, rows: int, full: bool, data: bytes) -> None:
        self._present(cols, rows, full, data)

    def size(self) -> tuple[int, int]:
        return self._size

    def resize(self, cols: int, rows: int) -> None:
        self._size = (max(1, int(cols)), max(1, int(rows)))

    def push_keys(self, data: str) -> None:
        """Raw input as a terminal would send it (letters, \\r, \\x1b[A, \\x1b[1;2C ...)."""
        self._buffer += data

    def read_keys(self) -> list[str]:
        return self._parse_buffer()


class Action(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    CONFIRM = auto()
    FIRE = auto()
    BACK = auto()
    PAUSE = auto()
    OTHER = auto()


@dataclass(frozen=True)
class InputEvent:
    action: Action
    coarse: bool = False
    raw: str = ""

    @property
    def confirm(self) -> bool:
        return self.action in (Action.CONFIRM, Action.FIRE)


_BINDINGS = {
    "UP": Action.UP, "w": Action.UP, "DOWN": Action.DOWN, "s": Action.DOWN,
    "LEFT": Action.LEFT, "a": Action.LEFT, "RIGHT": Action.RIGHT, "d": Action.RIGHT,
    "ENTER": Action.CONFIRM, "SPACE": Action.FIRE, "ESC": Action.BACK, "p": Action.PAUSE,
}


class InputManager:
    """Turns raw key names into game actions; letters honour Shift as 'coarse'."""

    def __init__(self, term) -> None:
        self.term = term

    def poll(self) -> list[InputEvent]:
        events = []
        for raw in self.term.read_keys():
            coarse = raw.startswith("SHIFT+") or (len(raw) == 1 and raw.isupper())
            name = raw[6:] if raw.startswith("SHIFT+") else raw
            action = _BINDINGS.get(name if len(name) > 1 else name.lower(), Action.OTHER)
            events.append(InputEvent(action, coarse, raw))
        return events
