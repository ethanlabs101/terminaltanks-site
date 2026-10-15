"""Loads terminaltanks.py as a module so the site tools can read its real content registries.

Every generator in tools/ goes through load(), so the website is always built from the same game file that play.html runs
(the repository's ./terminaltanks.py unless --game points somewhere else)."""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent          # the website folder
DEFAULT_GAME = ROOT / "terminaltanks.py"


def load(path: str | os.PathLike | None = None, name: str = "terminaltanks"):
    """Imports the game file and returns the module. Audio is forced off so nothing tries to open a sound device."""
    os.environ.setdefault("TT_NOAUDIO", "1")
    os.environ.setdefault("TT_AUDIO_SINK", "none")
    p = pathlib.Path(path or DEFAULT_GAME).resolve()
    if name in sys.modules and getattr(sys.modules[name], "__file__", None) == str(p):
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                                      # dataclasses look the module up while it executes
    spec.loader.exec_module(mod)
    return mod


def game_arg(argv: list[str]) -> str | None:
    """`--game PATH` from a tool's command line (None = the site's own terminaltanks.py)."""
    if "--game" in argv:
        i = argv.index("--game")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None
