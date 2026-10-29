"""Loads the game so the site tools can read its real content registries.

Every generator in tools/ goes through load(), so the website is always built from the same game that play.html runs
(the repository's ./terminaltanks.py unless --game points somewhere else).

Since 2.0.0 the game is a package: terminaltanks.py is a small entry point and everything else lives in tanks/. load()
then returns one flat namespace holding every name the package defines (each taken from the module that defines it),
so the tools can keep reading `tt.SONGS`, `tt.draw_tank`, `tt.SaveData` and so on wherever those live. A single-file
game (1.x) is loaded as it always was."""
from __future__ import annotations

import ast
import importlib
import importlib.util
import os
import pathlib
import pkgutil
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent          # the website folder
DEFAULT_GAME = ROOT / "terminaltanks.py"

# names the tools used before 2.0.0 renamed them (2.0.0 made these helpers public)
OLD_NAMES = {"_flick": "flicker", "_ELEM": "ELEMENTS", "_PHASE_ELEMS": "PHASE_ELEMENTS", "_MOTE_STYLES": "MOTE_STYLES",
             "_to_256": "to_256", "_nearest16": "nearest16", "_parse_cli": "parse_cli", "_reset_progress": "reset_progress",
             "_NOTE_NAMES": "NOTE_NAMES", "_SCALE_NAMES": "SCALE_NAMES", "_DIGITS": "DIGITS", "_au_inst_table": "au_inst_table",
             "_UNLOCKABLES": "UNLOCKABLES", "_family_of": "family_of", "_TURRETS": "TURRETS", "_HULLS": "HULLS", "_TRACKS": "TRACKS"}


def _top_level_names(path: pathlib.Path) -> set[str]:
    """Names a module assigns, defines or declares at its top level (not the ones it only imports)."""
    out = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        out.add(n.id)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and isinstance(node.target, ast.Name):
            out.add(node.target.id)
    return out


def _flat(entry: types.ModuleType, pkg_name: str) -> types.ModuleType:
    pkg = importlib.import_module(pkg_name)
    ns = types.ModuleType(entry.__name__, entry.__doc__)
    owner: dict[str, str] = {}
    modules = [pkg] + [importlib.import_module(m.name) for m in pkgutil.walk_packages(pkg.__path__, pkg_name + ".")]
    for m in modules:
        for name in sorted(_top_level_names(pathlib.Path(m.__file__))):
            if hasattr(m, name) and name not in owner:
                setattr(ns, name, getattr(m, name))
                owner[name] = m.__name__
    for k, v in vars(entry).items():
        if not k.startswith("__"):
            setattr(ns, k, v)
    for old, new in OLD_NAMES.items():
        if hasattr(ns, new) and not hasattr(ns, old):
            setattr(ns, old, getattr(ns, new))
    ns.__file__ = entry.__file__
    ns.__version__ = getattr(pkg, "__version__", "")
    ns.__package_modules__ = modules
    ns.__owner__ = owner                     # which module each name came from (handy when a tool needs a module)
    return ns


def load(path: str | os.PathLike | None = None, name: str = "terminaltanks"):
    """Imports the game and returns it as one module-like namespace. Audio is forced off so nothing opens a sound
    device."""
    os.environ.setdefault("TT_NOAUDIO", "1")
    os.environ.setdefault("TT_AUDIO_SINK", "none")
    p = pathlib.Path(path or DEFAULT_GAME).resolve()
    if name in sys.modules and getattr(sys.modules[name], "__file__", None) == str(p):
        return sys.modules[name]
    pkg_dir = p.parent / "tanks"
    if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
        if str(p.parent) not in sys.path:
            sys.path.insert(0, str(p.parent))
        spec = importlib.util.spec_from_file_location(name + "_entry", p)
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        mod = _flat(entry, "tanks")
        sys.modules[name] = mod
        return mod
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
