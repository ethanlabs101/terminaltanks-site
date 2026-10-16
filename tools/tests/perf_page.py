"""How busy a page keeps the browser's main thread: share of wall time spent running tasks, with the CPU slowed (default 4x).
    python3 tools/tests/perf_page.py jukebox.html [--cpu N] [--play]     (--play starts the first song first)"""
import sys, time, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from pw_common import BASE

page_name = next((a for a in sys.argv[1:] if a.endswith(".html")), "jukebox.html")
cpu = float(sys.argv[sys.argv.index("--cpu") + 1]) if "--cpu" in sys.argv else 4.0
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page()
    cdp = ctx.new_cdp_session(pg)
    pg.goto(BASE + page_name); pg.wait_for_load_state("networkidle"); time.sleep(1)
    if "--play" in sys.argv:
        pg.click("#play"); time.sleep(3)
    cdp.send("Performance.enable")
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu})
    m0 = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    t0 = time.time(); time.sleep(10); wall = time.time() - t0
    m1 = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    busy = (m1["TaskDuration"] - m0["TaskDuration"]) / wall
    out = {"page": page_name, "cpu": cpu, "main_thread_busy": f"{busy * 100:.0f}%",
           "script": round(m1["ScriptDuration"] - m0["ScriptDuration"], 2), "layout": round(m1["LayoutDuration"] - m0["LayoutDuration"], 2),
           "style": round(m1["RecalcStyleDuration"] - m0["RecalcStyleDuration"], 2)}
    if "--play" in sys.argv:
        out["audio"] = pg.evaluate("() => { const a = document.getElementById('audio'); return { t: a.currentTime, paused: a.paused, rs: a.readyState }; }")
    print(json.dumps(out))
    b.close()
