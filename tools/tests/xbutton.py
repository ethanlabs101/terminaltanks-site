"""Drives the browser game into a Two Player match with SPECIAL on and checks the X button: hidden outside matches,
live on the human's aiming turn, one press = one charge (same as the X key), and the charge pips the game draws update."""
import sys, time, re
from playwright.sync_api import sync_playwright
from pw_common import BASE, route_pyodide
SHOT = "/tmp/claude-0/-home-claude/11bf1376-f4ec-5c96-955d-8e63870b06ca/scratchpad/"
mobile = "--mobile" in sys.argv


def screen(pg):
    return pg.evaluate("() => window.__term.plain()")


def press(pg, key, n=1, wait=0.35):
    for _ in range(n):
        pg.keyboard.press(key)
        time.sleep(wait)


def wait_text(pg, pat, timeout=25):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if re.search(pat, screen(pg)):
            return True
        time.sleep(0.3)
    return False


ok = True
with sync_playwright() as p:
    b = p.chromium.launch()
    kw = dict(viewport={"width": 1280, "height": 800})
    if mobile:
        kw = dict(p.devices["Pixel 7"]); kw["viewport"] = {"width": 915, "height": 412}
    ctx = b.new_context(**kw)
    route_pyodide(ctx)
    pg = ctx.new_page()
    pg.goto(BASE + "play.html")
    pg.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=120000)
    xb = pg.locator("#pad-x") if mobile else pg.locator("#b-x")
    print("X hidden on title:", pg.locator("#b-x").is_hidden())
    for _ in range(6):                                            # skip the boot screen and the title
        press(pg, "Enter", wait=1.5)
        if wait_text(pg, "SELECT MISSION", 2):
            break
    time.sleep(1)
    press(pg, "ArrowDown", wait=0.6); press(pg, "Enter", wait=2.5)          # TWO PLAYER -> rules
    wait_text(pg, "RULES")

    press(pg, "ArrowUp", 2)                                       # rows wrap: GO <- SPECIAL
    txt = screen(pg)
    row = [ln for ln in txt.splitlines() if "SPECIAL" in ln and "AMMO" not in ln]
    print("special row before:", row[:1])
    if row and "OFF" in row[0]:
        press(pg, "ArrowRight")
    print("special row after:", [ln for ln in screen(pg).splitlines() if "SPECIAL" in ln and "AMMO" not in ln][:1])
    press(pg, "ArrowDown"); press(pg, "Enter", wait=1.2)            # GO -> pilot setup
    pg.screenshot(path=SHOT + "x1.png")
    scene = ""
    for i in range(30):
        scene = pg.evaluate("() => (window.__gs && window.__gs.raw) || ''")
        if scene.startswith("battle"):
            break
        s = screen(pg)
        if "SHOOTS FIRST" in s and "PLAYER 2" in s and i % 2:
            press(pg, "ArrowRight", wait=0.3)                     # player 2 picks something different, so nobody ties
        press(pg, "Enter", wait=1.2)
    print("reached:", scene, "after", i, "steps")
    for _ in range(40):                                           # wait until it is a human's turn to aim
        if pg.evaluate("() => window.__gs && window.__gs.mine"):
            break
        time.sleep(0.25)
    time.sleep(2)
    pg.screenshot(path=SHOT + "x2.png")
    vis = xb.is_visible()
    dis = xb.get_attribute("aria-disabled")
    print("X visible in match:", vis, "disabled:", dis)
    ok &= vis and dis == "false"
    time.sleep(3)
    hud0 = screen(pg).splitlines()[0]
    turn0 = [l for l in screen(pg).splitlines() if "TURN" in l][:1]
    if mobile:
        xb.tap()
    else:
        xb.click()
    time.sleep(2.5)
    hud1 = screen(pg).splitlines()[0]
    turn1 = [l for l in screen(pg).splitlines() if "TURN" in l][:1]
    print("HUD before:", hud0.strip()); print("HUD after: ", hud1.strip())
    print("turn before:", [t.strip() for t in turn0], "after:", [t.strip() for t in turn1])
    charged = "\u2726" in hud1.split("PLAYER 2")[0] and "\u2726" not in hud0.split("PLAYER 2")[0]
    print("player 1 banked a charge:", charged)
    pg.screenshot(path=SHOT + "x3.png")
    ok &= charged
    # a second, rapid press must not double-charge: it is player 2's turn now, so press X twice quickly as player 2
    for _ in range(40):
        if pg.evaluate("() => window.__gs && window.__gs.mine"):
            break
        time.sleep(0.25)
    if mobile:
        xb.tap(); xb.tap()
    else:
        xb.click(); xb.click()
    time.sleep(2.5)
    hud2 = screen(pg).splitlines()[0]
    p2 = hud2.split("PLAYER 2")[0][-12:] + "|" + hud2.split("PLAYER 2")[0][:0]
    right = hud2[hud2.index("PLAYER 2") - 12:hud2.index("PLAYER 2")]
    print("HUD after double press:", hud2.strip())
    ok &= right.count("\u2726") == 1
    print("player 2 got exactly one charge from a double press:", right.count("\u2726") == 1)
    b.close()
print("X BUTTON TEST", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
