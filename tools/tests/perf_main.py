"""How busy play.html keeps the page's main thread (drawing the game, sound) on the home screen, CPU slowed 4x.
    python3 tools/tests/perf_main.py [--cpu N] [--secs S]"""
import sys, time, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from pw_common import BASE, route_pyodide
cpu = float(sys.argv[sys.argv.index("--cpu") + 1]) if "--cpu" in sys.argv else 4.0
secs = float(sys.argv[sys.argv.index("--secs") + 1]) if "--secs" in sys.argv else 10.0
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1280, "height": 760}); route_pyodide(ctx); pg = ctx.new_page()
    cdp = ctx.new_cdp_session(pg)
    pg.goto(BASE + "play.html"); pg.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=180000)
    pg.mouse.click(640, 400); time.sleep(2); pg.keyboard.press("Enter"); time.sleep(6)       # past boot, on the title with music
    cdp.send("Performance.enable"); cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu})
    g = lambda: {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    m0 = g(); t0 = time.time(); time.sleep(secs); m1 = g(); wall = time.time() - t0
    d = {k: round(m1[k] - m0[k], 2) for k in ("TaskDuration", "ScriptDuration", "LayoutDuration", "RecalcStyleDuration")}
    print(json.dumps({"main_thread_busy": f"{d['TaskDuration'] / wall * 100:.0f}%", **d}))
    b.close()
