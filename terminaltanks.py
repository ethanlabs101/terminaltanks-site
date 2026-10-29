#!/usr/bin/env python3
"""Terminal Tanks - turn-based artillery for the terminal.

Credit: ethanlabs101 - https://github.com/ethanlabs101

Run:   python3 terminaltanks.py          (python3 terminaltanks.py --help for options)
Needs: Python 3.10+, a UTF-8 terminal of at least 96x28 (100x30 recommended). No third-party packages.

The game itself is the `tanks` package next to this file. The browser version imports this module and drives the
game through the web_* functions (see tanks/web.py).
"""
import sys

from tanks.app import main
from tanks.web import WEB_API, web_feed, web_frames, web_redraw, web_resize

__all__ = ["main", "WEB_API", "web_feed", "web_frames", "web_redraw", "web_resize"]

if __name__ == "__main__":
    sys.exit(main())
