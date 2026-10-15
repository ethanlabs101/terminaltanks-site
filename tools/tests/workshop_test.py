"""Workshop: every part has a tile, paints and HOVER draw, build sheet and share link round-trip."""
import sys, time, json
from playwright.sync_api import sync_playwright
from pw_common import BASE
S = "/tmp/claude-0/-home-claude/11bf1376-f4ec-5c96-955d-8e63870b06ca/scratchpad/"
ok = True
def check(c, label):
    global ok
    ok &= bool(c); print(("PASS " if c else "FAIL ") + label)
P = json.load(open("/home/claude/site/data/parts.json"))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1000})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "workshop.html"); pg.wait_for_selector(".part")
    for slot in ["turret", "hull", "track", "barrel", "glow", "ambient", "accent"]:
        pg.click(f"#slots [data-s={slot}]"); time.sleep(0.4)
        check(pg.locator(".part").count() == len(P[slot]), f"{slot}: {pg.locator('.part').count()} tiles")
    pg.click("#slots [data-s=turret]"); pg.click(".part[data-id=martyrhood]"); time.sleep(0.2)
    pg.click("#slots [data-s=ambient]"); pg.click(".part[data-id=tails]"); time.sleep(0.2)
    pg.select_option("#hc", "GILDED"); pg.check("#hov"); time.sleep(0.8)
    lit = pg.evaluate("() => { const c = document.getElementById('pv'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] > 150 && d[i + 1] > 110 && d[i + 2] < 120) n++; return n; }")
    check(lit > 10, f"gilded paint draws gold pixels ({lit})")
    check("5,000" in pg.text_content("#fee"), "fee includes HOVER: " + pg.text_content("#fee"))
    url = pg.url
    pg.screenshot(path=S + "ws1.png")
    pg2 = b.new_page(); pg2.goto(url); pg2.wait_for_selector(".part"); time.sleep(0.5)
    check(pg2.input_value("#hc") == "GILDED" and pg2.is_checked("#hov"), "share link restores paint and HOVER")
    check("MARTYRHOOD" in pg2.text_content("#sheet"), "share link restores parts")
    check(not errs, f"no page errors {errs[:2]}")
    b.close()
print("WORKSHOP TEST", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
