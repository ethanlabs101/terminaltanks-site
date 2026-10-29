#!/usr/bin/env python3
"""Builds downloads/terminaltanks.zip (the desktop download) from the site's game (terminaltanks.py and, since 2.0.0, the
tanks/ package next to it) and writes downloads/info.json.
    python3 tools/release/build_download.py
The zip is reproducible: fixed timestamps and order, so rebuilding an unchanged game gives an identical file."""
import hashlib, json, re, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
game = (ROOT / "terminaltanks.py").read_bytes()
pkg = sorted(p for p in (ROOT / "tanks").rglob("*.py")) if (ROOT / "tanks").is_dir() else []
version_src = (ROOT / "tanks" / "__init__.py").read_bytes() if pkg else game
version = re.search(rb'^__version__\s*=\s*["\']([^"\']+)', version_src, re.M).group(1).decode()
out = ROOT / "downloads" / "terminaltanks.zip"
files = [("README.txt", (HERE / "README.txt").read_text().replace("{VERSION}", version).encode(), 0o644),
         ("terminaltanks.py", game, 0o644), ("play.sh", (HERE / "play.sh").read_bytes(), 0o755), ("play.bat", (HERE / "play.bat").read_bytes(), 0o644)]
files += [(p.relative_to(ROOT).as_posix(), p.read_bytes(), 0o644) for p in pkg]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data, mode in files:
        zi = zipfile.ZipInfo("TerminalTanks/" + name, date_time=(2026, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = (0o100000 | mode) << 16
        z.writestr(zi, data)
data = out.read_bytes()
info = {"version": version, "file": "downloads/terminaltanks.zip", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
(ROOT / "downloads" / "info.json").write_text(json.dumps(info, indent=2) + "\n")
for legacy in ("terminaltanks.zip", "info.json"):            # older links pointed at copies in the site root: keep them current
    if (ROOT / legacy).exists():
        (ROOT / legacy).write_bytes((ROOT / "downloads" / legacy).read_bytes())
print(json.dumps(info))
