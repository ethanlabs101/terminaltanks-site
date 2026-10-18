"""Boots play.html, presses Enter (a user gesture, which unlocks audio) and checks the game's sound really plays: the
song the game asked for is decoded and queued to the sample on the music context (first pass, and the loop pieces), its
position advances, effects play on the effects context, and the page hands the game a live spectrum for its analyser."""
import sys, time, json
from playwright.sync_api import sync_playwright
from pw_common import BASE, route_pyodide
ok = True
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    route_pyodide(ctx)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(BASE + "play.html")
    pg.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=120000)
    time.sleep(2)
    pg.keyboard.press("Enter")
    peak, st = 0, None
    for i in range(40):
        time.sleep(0.5)
        st = pg.evaluate("""() => { const a = window.__audio; if (!a || !a.ctx) return null;
            const sp = a.spectrum(), peak = sp ? Math.max(...sp.split('').map(Number)) * 28 : 0;
            return { state: a.ctx.state, music: a.mctx.state, rate: a.mctx.sampleRate, ops: a.ops, song: a.cur ? a.cur.sid : '', pieces: a.cur ? a.cur.srcs.length : 0,
                     pos: +a.position()[0].toFixed(2), pack: !!a.pack, effects: a.played, peak, errors: a.errors }; }""")
        if st:
            peak = max(peak, st["peak"])
        if st and st["peak"] > 40 and st["song"] and i > 6:
            break
    for _ in range(4):                                       # menu moves make effects (ui_move)
        pg.keyboard.press("ArrowDown"); time.sleep(0.4)
    time.sleep(0.5)
    st["effects"] = pg.evaluate("() => window.__audio.played")
    print(json.dumps(st))
    print("peak level heard by the analyser:", peak)
    t1 = pg.evaluate("() => window.__audio.position()[0]"); time.sleep(1.5)
    t2 = pg.evaluate("() => window.__audio.position()[0]")
    print(f"song position advanced {t1:.2f} -> {t2:.2f} s")
    ok = bool(st) and st["state"] == "running" and st["music"] == "running" and st["song"] != "" and st["pieces"] >= 1 and t2 - t1 > 1.0 and st["pack"] and st["effects"] > 0 and peak > 40 and st["errors"] == 0
    pg.screenshot(path="/tmp/claude-0/-home-claude/11bf1376-f4ec-5c96-955d-8e63870b06ca/scratchpad/audio.png")
    print("errors:", errs[:10])
    ok &= not errs
    b.close()
print("AUDIO TEST", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
