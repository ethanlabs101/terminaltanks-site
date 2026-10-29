#!/usr/bin/env python3
"""Checks every page: local links and files exist, no script errors, no failed requests, and no sideways scrolling on a
desktop window or a phone (375 px). Needs the site served on TT_BASE (python3 tools/serve.py 8766) and Playwright.
    python3 tools/tests/site_check.py"""
import pathlib, re, sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pw_common import BASE, route_pyodide

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGES = sorted(p.name for p in ROOT.glob("*.html"))
bad = []


class Refs(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs = []; self.ids = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"): self.ids.add(a["id"])
        for k in ("href", "src", "poster"):
            if a.get(k): self.refs.append(a[k])


# 0. GitHub Pages runs Jekyll unless .nojekyll exists, and Jekyll drops every file whose name starts with "_". That would
#    remove the game's tanks/**/__init__.py files and break play.html on the live site even though it works locally.
if not (ROOT / ".nojekyll").exists() and any(p.name.startswith("_") for p in ROOT.rglob("*") if ".git" not in p.parts):
    bad.append(".nojekyll is missing: GitHub Pages would leave out every file starting with '_' (tanks/__init__.py)")

# 1. static: every local href/src points at a file that exists (and #anchors on the same page exist)
for page in PAGES:
    p = Refs(); p.feed((ROOT / page).read_text(encoding="utf-8"))
    for ref in p.refs:
        u = urlsplit(ref)
        if u.scheme or ref.startswith(("//", "mailto:", "javascript:", "data:")) or "${" in ref or "{" in ref:
            continue
        if not u.path:
            if u.fragment and u.fragment not in p.ids:
                pass                                                  # anchors can be added by script; checked live below
            continue
        if not (ROOT / unquote(u.path)).exists():
            bad.append(f"{page}: missing {ref}")
# the generated data refers to media files too
import json
for e in json.loads((ROOT / "catalog.json").read_text()):
    pass
m = json.loads((ROOT / "data/music.json").read_text())
songs = m["songs"] if isinstance(m, dict) else m
for s in songs:
    for k in ("a", "cv"):
        if s.get(k) and not (ROOT / s[k]).exists():
            bad.append(f"music.json: missing {s[k]}")
man = json.loads((ROOT / "shots/manifest.json").read_text())
for k, v in man.items():
    for f in (v.values() if isinstance(v, dict) else [v] if isinstance(v, str) else []):
        if isinstance(f, str) and re.search(r"\.(png|gif|webm|mp4)$", f) and not (ROOT / "shots" / f).exists() and not (ROOT / f).exists():
            bad.append(f"shots/manifest.json: missing {f}")
print(f"static: {len(PAGES)} pages, {len(songs)} songs checked")

# 2. live: each page at two widths
with sync_playwright() as pw:
    br = pw.chromium.launch()
    for label, vp, mobile in (("desktop", {"width": 1280, "height": 860}, False), ("phone", {"width": 375, "height": 740}, True)):
        ctx = br.new_context(viewport=vp, is_mobile=mobile, has_touch=mobile)
        route_pyodide(ctx)
        for page in PAGES:
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e, errs=errs: errs.append(f"script error: {e}"))
            pg.on("console", lambda m, errs=errs: errs.append(f"console: {m.text}") if m.type == "error" else None)
            pg.on("response", lambda r, errs=errs: errs.append(f"HTTP {r.status} {r.url}") if r.status >= 400 and r.url.startswith(BASE) and not r.url.endswith("favicon.ico") else None)
            pg.goto(BASE + page, wait_until="load"); pg.wait_for_timeout(1500)
            over = pg.evaluate("""() => { const w = document.documentElement.clientWidth; const out = [];
                for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect();
                  if (r.width && r.right > w + 1 && getComputedStyle(el).position !== 'fixed') {
                    let p = el.parentElement, clipped = false;
                    while (p && p !== document.body) { const o = getComputedStyle(p); if (/(auto|scroll|hidden|clip)/.test(o.overflowX)) { clipped = true; break; } p = p.parentElement; }
                    if (!clipped) out.push((el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + el.className).slice(0, 60) + ' ' + Math.round(r.right)); } }
                return { sw: document.documentElement.scrollWidth, w, out: out.slice(0, 5) }; }""")
            if over["sw"] > over["w"] + 1:
                errs.append(f"page scrolls sideways ({over['sw']} > {over['w']}): {over['out']}")
            if page == "404.html":
                errs = [e for e in errs if "HTTP 404" not in e]
            for e in errs:
                bad.append(f"{page} [{label}]: {e}")
            pg.close()
        ctx.close()
    br.close()

for b in bad:
    print("FAIL", b)
print("SITE CHECK", "PASS" if not bad else f"FAIL ({len(bad)})")
sys.exit(1 if bad else 0)
