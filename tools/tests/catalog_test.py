"""Catalog: matches catalog.json, every entry has a picture, paints play as video, filters and the lightbox work."""
import sys, time, json
from playwright.sync_api import sync_playwright
from pw_common import BASE
S = "/tmp/claude-0/-home-claude/11bf1376-f4ec-5c96-955d-8e63870b06ca/scratchpad/"
ok = True
def check(c, label):
    global ok
    ok &= bool(c); print(("PASS " if c else "FAIL ") + label)
cat = json.load(open("/home/claude/site/catalog.json"))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    bad = []; pg.on("response", lambda r: bad.append(r.url) if r.status >= 400 else None)
    pg.goto(BASE + "catalog.html"); pg.wait_for_selector(".item")
    check(pg.locator(".item").count() == len(cat), f"all {len(cat)} entries listed")
    check(pg.locator(".item.has-shot").count() == len(cat), f"every entry has a picture ({pg.locator('.item.has-shot').count()})")
    pg.click("#kinds [data-k=paint]"); time.sleep(2.5)
    n = pg.locator(".item").count(); vids = pg.locator("video.thumb").count()
    playing = pg.evaluate("() => [...document.querySelectorAll('video.thumb')].filter((v) => !v.paused && v.currentTime > 0).length")
    check(n == 13 and vids == 13, f"paints: {n} entries, {vids} videos")
    check(playing >= 6, f"animated paint previews playing on screen: {playing}")
    pg.screenshot(path=S + "cat1.png")
    pg.locator(".item.has-shot").first.click(); time.sleep(1.5)
    check(pg.evaluate("() => { const v = document.getElementById('lbv'); return !v.hidden && !v.paused; }"), "lightbox plays the clip")
    pg.keyboard.press("Escape")
    pg.click("#kinds [data-k=boss]"); time.sleep(0.4)
    check(pg.locator(".item").count() == sum(1 for e in cat if e["k"] == "boss"), "bosses filter")
    pg.click("#kinds [data-k=all]"); pg.click("#hows [data-k='The Martyr']"); time.sleep(0.3)
    check(pg.locator(".item").count() == sum(1 for e in cat if e["h"].startswith("The Martyr")), "Martyr source filter " + str(pg.locator(".item").count()))
    pg.fill("#q", "blessing"); time.sleep(0.3); pg.screenshot(path=S + "cat2.png")
    check("MARTYR'S BLESSING" in pg.text_content("#items"), "Martyr's Blessing is in the catalog")
    pg.fill("#q", ""); pg.click("#hows [data-k=all]")
    # scroll the whole page so every lazy image loads, then look for broken ones
    for y in range(0, 60000, 1500):
        pg.evaluate(f"window.scrollTo(0,{y})"); time.sleep(0.05)
    time.sleep(1.5)
    broken = pg.evaluate("() => [...document.querySelectorAll('img.thumb')].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src)")
    check(not broken and not bad, f"no broken pictures {broken[:3]} {bad[:3]}")
    check(not errs, f"no page errors {errs[:2]}")
    b.close()
print("CATALOG TEST", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
