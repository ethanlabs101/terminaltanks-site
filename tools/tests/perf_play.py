"""Measures how hard the browser game works: frame time and frame rate reported by the game worker, on the title screen
and in a battle, with the CPU slowed down (default 4x) to stand in for an older computer.
    python3 tools/tests/perf_play.py [page.html] [--cpu N]"""
import sys, time, re, json, statistics, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from pw_common import BASE, route_pyodide

page_name = next((a for a in sys.argv[1:] if a.endswith(".html")), "play.html")
cpu = float(sys.argv[sys.argv.index("--cpu") + 1]) if "--cpu" in sys.argv else 4.0
HOOK = """(() => { window.__stats = []; const W = window.Worker;
  window.Worker = function (...a) { const w = new W(...a);
    w.addEventListener('message', (e) => { const m = e.data; if (m && m.t === 'stats') window.__stats.push({ at: performance.now(), fps: m.fps, avg: m.avg, max: m.max, pending: m.pending }); });
    return w; }; window.Worker.prototype = W.prototype; })();"""


def screen(pg):
    return pg.evaluate("() => window.__term ? window.__term.plain() : ''")


def press(pg, key, n=1, wait=0.35):
    for _ in range(n):
        pg.keyboard.press(key); time.sleep(wait)


def window_stats(pg, secs):
    t0 = pg.evaluate("performance.now()"); time.sleep(secs)
    s = [x for x in pg.evaluate("window.__stats") if x["at"] > t0]
    if not s:
        return {"n": 0}
    return {"fps": round(statistics.mean(x["fps"] for x in s), 1), "frame_ms": round(statistics.mean(x["avg"] for x in s), 1),
            "worst_ms": round(max(x["max"] for x in s), 1)}


with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1280, "height": 760})
    route_pyodide(ctx); ctx.add_init_script(HOOK)
    pg = ctx.new_page()
    cdp = ctx.new_cdp_session(pg)
    pg.goto(BASE + page_name)
    pg.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=180000)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu})
    pg.mouse.click(640, 400)                                  # a user gesture, so sound can start
    time.sleep(4)
    res = {"page": page_name, "cpu_slowdown": cpu, "title": window_stats(pg, 8)}
    for _ in range(6):
        press(pg, "Enter", wait=1.5)
        if "SELECT MISSION" in screen(pg):
            break
    time.sleep(1)
    press(pg, "ArrowDown", wait=0.6); press(pg, "Enter", wait=2.5); press(pg, "ArrowUp"); press(pg, "Enter", wait=1.2)
    for i in range(40):
        s = screen(pg)
        if re.search(r"PLAYER [12] TURN", s):
            break
        if "SHOOTS FIRST" in s and "PLAYER 2" in s and i % 2:
            press(pg, "ArrowRight", wait=0.3)
        press(pg, "Enter", wait=1.2)
    time.sleep(6)
    res["battle_idle"] = window_stats(pg, 8)
    t0 = pg.evaluate("performance.now()")
    for _ in range(2):
        press(pg, "ArrowUp", 3, 0.1); press(pg, "Space", wait=0.2); time.sleep(5)
    s = [x for x in pg.evaluate("window.__stats") if x["at"] > t0]
    res["battle_shots"] = {"fps": round(statistics.mean(x["fps"] for x in s), 1), "frame_ms": round(statistics.mean(x["avg"] for x in s), 1),
                           "worst_ms": round(max(x["max"] for x in s), 1)} if s else {"n": 0}
    print(json.dumps(res))
    b.close()
