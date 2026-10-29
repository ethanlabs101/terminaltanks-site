#!/usr/bin/env python3
"""Writes terminaltanks.json: every module of the tanks/ package, so play.html fetches them all at once instead of
discovering them import by import ("complete": true tells it nothing else is needed).
    python3 tools/release/game_manifest.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "tanks").rglob("*.py"))
(ROOT / "terminaltanks.json").write_text(json.dumps({"complete": True, "files": files}, indent=1) + "\n")
print(f"terminaltanks.json: {len(files)} files")
