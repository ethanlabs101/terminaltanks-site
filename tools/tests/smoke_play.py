import sys, time
from playwright.sync_api import sync_playwright
from pw_common import BASE, route_pyodide
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    route_pyodide(ctx)
    pg = ctx.new_page()
    logs = []
    pg.on("console", lambda m: logs.append(m.type + ": " + m.text))
    pg.on("pageerror", lambda e: logs.append("PAGEERROR " + str(e)))
    pg.goto(BASE + "play.html" + (sys.argv[1] if len(sys.argv) > 1 else ""))
    t0 = time.time()
    while time.time() - t0 < 120:
        chip = pg.text_content("#chip")
        if chip in ("ONLINE", "OFFLINE", "CRASHED"):
            break
        time.sleep(1)
    print("chip", chip, "after", round(time.time() - t0), "s")
    time.sleep(6)
    pg.screenshot(path=sys.argv[2] if len(sys.argv) > 2 else "/tmp/claude-0/-home-claude/11bf1376-f4ec-5c96-955d-8e63870b06ca/scratchpad/play.png")
    print("\n".join(logs[-30:]))
    b.close()
