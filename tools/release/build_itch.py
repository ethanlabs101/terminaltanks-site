#!/usr/bin/env python3
"""Builds downloads/terminaltanks-itch.zip: the browser game as an itch.io HTML5 upload.
    python3 tools/release/build_itch.py [--music-base URL]

The zip holds play.html as index.html, the game (terminaltanks.py, terminaltanks.json, tanks/), the effects pack and the
song list. itch.io takes at most 1,000 files and 500 MB per HTML5 game, and the music/ folder alone is ~1,400 files, so
the songs stream from the website instead (--music-base, the live site by default; GitHub Pages allows that). Links that
lead off the game open in a new tab, because on itch.io the game runs inside an iframe. Reproducible: rebuilding an
unchanged site gives an identical zip."""
import hashlib, json, re, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = "https://ethanlabs101.github.io/terminaltanks-site/"
music = sys.argv[sys.argv.index("--music-base") + 1] if "--music-base" in sys.argv else SITE
if not music.endswith("/"):
    music += "/"

page = (ROOT / "play.html").read_text(encoding="utf-8")
page = page.replace('<meta charset="utf-8">', f'<meta charset="utf-8">\n<meta name="tt-music-base" content="{music}">', 1)
page, n = re.subn(r'<a class="btn" href="home\.html" title="Back to the TerminalTanks site"',
                  f'<a class="btn" href="{SITE}home.html" target="_blank" rel="noopener" title="The TerminalTanks website (new tab)"',
                  page, count=1)
assert n == 1, "play.html: the Site button was not found"

files = [("index.html", page.encode("utf-8"))]
for rel in ["terminaltanks.py", "terminaltanks.json", "audio/sfx.mp3", "audio/sfx.json", "data/music.json"]:
    files.append((rel, (ROOT / rel).read_bytes()))
manifest = json.loads((ROOT / "terminaltanks.json").read_text())["files"]
files += [(rel, (ROOT / rel).read_bytes()) for rel in manifest]

assert len(files) <= 1000, f"{len(files)} files: itch.io allows 1,000"
out = ROOT / "downloads" / "terminaltanks-itch.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in files:
        zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o100644 << 16
        z.writestr(zi, data)
data = out.read_bytes()
total = sum(len(d) for _, d in files)
print(json.dumps({"file": str(out.relative_to(ROOT)), "files": len(files), "unpacked_mb": round(total / 1e6, 2),
                  "zip_mb": round(len(data) / 1e6, 2), "music_from": music, "sha256": hashlib.sha256(data).hexdigest()}))
