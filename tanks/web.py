"""The browser entry points (Pyodide). The page imports terminaltanks.py, calls web_frames() and then drives one frame
per tick; keys and the grid size are pushed in with web_feed() / web_resize(). The game hands the page structured
cell updates instead of ANSI text. Everything else is the same code the terminal runs."""
from __future__ import annotations

import sys
import traceback
from typing import Callable, Optional, Sequence

from tanks.app import Application, parse_cli, reset_progress
from tanks.terminal import WebTerminalIO


WEB_API = 2

_web_term: Optional[WebTerminalIO] = None


def web_feed(data: str) -> None:
    """Page -> game: keystrokes."""
    if _web_term is not None:
        _web_term.push_keys(data)


def web_resize(cols: int, rows: int) -> None:
    """Page -> game: the drawing grid changed size."""
    if _web_term is not None:
        _web_term.resize(cols, rows)


def web_redraw() -> None:
    """Page -> game: repaint every cell (tab visible again, canvas was recreated, ...)."""
    if _web_term is not None:
        _web_term.redraw_requested = True


def web_frames(argv: Optional[Sequence[str]] = None, present: Optional[Callable] = None,
               bell: Optional[Callable[[], None]] = None, size: tuple[int, int] = (110, 31)):
    """Generator entry point for the browser: one iteration per frame, so the page paces the game (it never blocks the
    tab). The exit code is the generator's return value."""
    global _web_term
    args, mode, save_path = parse_cli(argv)
    if args.reset_progress:
        return reset_progress(save_path)
    term = _web_term = WebTerminalIO(present, bell, size)
    try:
        with term:
            yield from Application(term, args.seed, mode, save_path).frames()
    except GeneratorExit:
        raise
    except Exception:
        traceback.print_exc()
        print("\nTerminalTanks crashed.", file=sys.stderr)
        return 1
    finally:
        _web_term = None
    return 0
