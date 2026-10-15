#!/usr/bin/env python3
"""Build shots/manifest.json from the screenshots in this folder.

Name each screenshot after the item id with ":" replaced by "-", for example:
    tank-hornet.png   ammo-venom.png   map-the-maw.png   theme-neon.png   rgb-hull.png   master_difficulty.png
Pictures drawn by tools/render_catalog.py are listed automatically; use this script only after adding hand-made files.
Animated previews (MP4/GIF, under the "@anim" key) are kept as they are.
Run from anywhere:  python3 shots/make_manifest.py
List every expected file name:  python3 shots/make_manifest.py --list
"""
import json, sys
from pathlib import Path

here = Path(__file__).resolve().parent
KINDS = ("tank", "ammo", "map", "theme", "rgb", "paint", "boss", "feature")
EXT = {".png", ".jpg", ".jpeg", ".webp", ".avif"}


def uid_for(stem: str) -> str:
    kind, _, rest = stem.partition("-")
    return f"{kind}:{rest}" if kind in KINDS and rest else stem


if "--list" in sys.argv:
    for item in json.loads((here.parent / "catalog.json").read_text()):
        print(item["u"].replace(":", "-") + ".png")
    raise SystemExit

old = json.loads((here / "manifest.json").read_text()) if (here / "manifest.json").exists() else {}
anim = old.pop("@anim", {})
posters = {f for a in anim.values() for f in a.values()}
known = {i["u"] for i in json.loads((here.parent / "catalog.json").read_text())}
manifest = dict(old)
manifest.update({uid_for(p.stem): p.name for p in sorted(here.iterdir()) if p.suffix.lower() in EXT and p.name not in posters and uid_for(p.stem) not in old and uid_for(p.stem) in known})
known = {i["u"] for i in json.loads((here.parent / "catalog.json").read_text())}
for u in sorted(set(manifest) - known - {"@anim"}):
    print(f"warning: {manifest[u]} does not match any catalog item")
manifest["@anim"] = anim
(here / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
print(f"{len(manifest)} screenshots listed in shots/manifest.json")
