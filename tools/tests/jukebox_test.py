"""Jukebox: list loads, search/filter/sort work, a track plays, the analyser hears it, seek/next/mute work."""
import sys, time, json
from playwright.sync_api import sync_playwright
from pw_common import BASE
SHOT = "/tmp/claude-0/-home-claude/11bf1376-f4ec-5c96-955d-8e63870b06ca/scratchpad/"
ok, notes = True, []
def check(c, label):
    global ok
    ok &= bool(c); print(("PASS " if c else "FAIL ") + label)
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(BASE + "jukebox.html")
    pg.wait_for_selector(".trk")
    n = pg.locator(".trk").count()
    check(n == 277, f"library lists every song ({n})")
    pg.fill("#q", "martyr"); time.sleep(0.3)
    check(0 < pg.locator(".trk").count() < 20, f"search 'martyr' -> {pg.locator('.trk').count()} tracks")
    pg.fill("#q", ""); pg.click("[data-g=tbos]"); time.sleep(0.2)
    check(pg.locator(".trk").count() == 20, "Tournament boss filter shows 20")
    pg.click("[data-g=all]"); pg.check("#hand"); time.sleep(0.2)
    check(pg.locator(".trk").count() == 103, f"hand-written only -> {pg.locator('.trk').count()}")
    pg.uncheck("#hand"); pg.select_option("#sort", "bpm"); time.sleep(0.2)
    bpms = pg.eval_on_selector_all(".trk .tb", "els => els.slice(0, 5).map(e => parseInt(e.textContent))")
    check(bpms == sorted(bpms, reverse=True), f"sort by tempo {bpms}")
    pg.select_option("#sort", "game")
    pg.locator(".trk").nth(0).click()
    time.sleep(3)
    st = pg.evaluate("() => { const a = document.getElementById('audio'); return { paused: a.paused, t: a.currentTime, src: a.currentSrc, d: a.duration }; }")
    check(not st["paused"] and st["t"] > 0.5, f"track plays {json.dumps(st)}")
    lvl = pg.evaluate("""() => new Promise((res) => { let best = 0, n = 0; const tick = () => {
        const c = document.getElementById('viz'), g = c.getContext('2d'), d = g.getImageData(0, 0, c.width, c.height).data; let lit = 0;
        for (let i = 0; i < d.length; i += 16) if (d[i] + d[i + 1] + d[i + 2] > 300) lit++; best = Math.max(best, lit); if (++n < 30) requestAnimationFrame(tick); else res(best); }; tick(); })""")
    check(lvl > 50, f"equalizer reacts to the music (lit pixels {lvl})")
    pg.screenshot(path=SHOT + "jb1.png")
    pg.evaluate("() => { const s = document.getElementById('seek'); s.value = 500; s.dispatchEvent(new Event('input')); s.dispatchEvent(new Event('change')); }")
    time.sleep(1)
    st2 = pg.evaluate("() => document.getElementById('audio').currentTime / document.getElementById('audio').duration")
    check(0.45 < st2 < 0.6, f"seek to middle ({st2:.2f})")
    t0 = pg.text_content("#np-title"); pg.click("#next"); time.sleep(1.5)
    check(pg.text_content("#np-title") != t0, "next track: " + pg.text_content("#np-title"))
    pg.click("#mute"); time.sleep(0.3)
    check(pg.get_attribute("#mute", "aria-pressed") == "true", "mute toggles")
    pg.click("#play"); time.sleep(0.5)
    check(pg.evaluate("() => document.getElementById('audio').paused"), "pause works")
    check(not errs, "no page errors " + str(errs[:3]))
    m = b.new_page(**p.devices["iPhone 13"])
    m.goto(BASE + "jukebox.html#song=boss_master"); m.wait_for_selector(".trk"); time.sleep(1)
    check(m.text_content("#np-title").startswith("THE MASTER") or "MASTER" in m.text_content("#np-title"), "deep link selects " + m.text_content("#np-title"))
    w = m.evaluate("() => document.documentElement.scrollWidth <= 391 && window.innerWidth <= 391")
    check(w, "no horizontal scroll on a phone")
    m.screenshot(path=SHOT + "jb2.png", full_page=False)
    b.close()
print("JUKEBOX TEST", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
