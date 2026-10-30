"""The itch.io build, tested the way itch.io serves it: unpacked on its own origin, shown inside an iframe on a third
origin, with the songs streamed cross-origin from "the website" (a second local server that sends the same CORS header
GitHub Pages does). Checks the game boots, music and effects play, the analyser gets data, saves persist across a
reload, and nothing errors. Starts and stops its own servers.
    python3 tools/release/build_itch.py --music-base http://127.0.0.1:8791/ && python3 tools/tests/itch_build.py"""
import functools, http.server, sys, tempfile, threading, time, zipfile, pathlib, json
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pw_common import route_pyodide

ROOT = pathlib.Path(__file__).resolve().parents[2]
GAME, SITE, HOST = 8790, 8791, 8792


class Quiet(http.server.SimpleHTTPRequestHandler):
    cors = False

    def end_headers(self):
        if self.cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, *a):
        pass


class Cors(Quiet):
    cors = True


def serve(port, root, handler):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(handler, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


tmp = pathlib.Path(tempfile.mkdtemp())
game_dir, host_dir = tmp / "game", tmp / "host"
host_dir.mkdir()
with zipfile.ZipFile(ROOT / "downloads" / "terminaltanks-itch.zip") as z:
    z.extractall(game_dir)
(host_dir / "index.html").write_text(
    f'<!doctype html><body style="margin:0;background:#222"><iframe id="g" src="http://127.0.0.1:{GAME}/index.html" '
    'width="1100" height="740" allow="autoplay; fullscreen *; gamepad" allowfullscreen style="border:0"></iframe></body>')
servers = [serve(GAME, game_dir, Quiet), serve(SITE, ROOT, Cors), serve(HOST, host_dir, Quiet)]

ok, errs = True, []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1180, "height": 800})
        route_pyodide(ctx)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{HOST}/index.html")
        fr = pg.frame_locator("#g")
        frame = next(f for f in pg.frames if f.url.startswith(f"http://127.0.0.1:{GAME}/"))
        frame.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=120000)
        print("boots inside the iframe:", frame.text_content("#ver"))
        pg.wait_for_timeout(2000)
        fr.locator("#terminal").click()
        pg.keyboard.press("Enter")
        st, peak = None, 0
        for i in range(40):
            pg.wait_for_timeout(500)
            st = frame.evaluate("""() => { const a = window.__audio; if (!a || !a.ctx) return null;
                const sp = a.spectrum(), peak = sp ? Math.max(...sp.split('').map(Number)) * 28 : 0;
                return { music: a.mctx.state, song: a.cur ? a.cur.sid : '', pos: +a.position()[0].toFixed(2), pack: !!a.pack, peak, errors: a.errors }; }""")
            if st:
                peak = max(peak, st["peak"])
            if st and st["song"] and st["peak"] > 40 and i > 6:
                break
        t1 = frame.evaluate("() => window.__audio.position()[0]"); pg.wait_for_timeout(1500)
        t2 = frame.evaluate("() => window.__audio.position()[0]")
        music_ok = bool(st) and st["music"] == "running" and st["song"] and t2 - t1 > 1.0 and st["pack"] and peak > 40 and st["errors"] == 0
        print("music streamed from the site:", json.dumps(st), f"position {t1:.1f} -> {t2:.1f} s", "PASS" if music_ok else "FAIL")
        ok &= music_ok
        site_link = frame.get_attribute("a.btn[title^='The TerminalTanks website']", "target")
        print("Site button opens a new tab:", site_link == "_blank")
        ok &= site_link == "_blank"
        # progress survives a reload (IndexedDB inside the iframe): the game writes its save on the main menu
        pg.keyboard.press("Enter"); pg.wait_for_timeout(3000)
        before = frame.evaluate("() => document.getElementById('b-save') && document.getElementById('b-save').textContent")
        pg.reload()
        frame = next(f for f in pg.frames if f.url.startswith(f"http://127.0.0.1:{GAME}/"))
        frame.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=120000)
        print("reloads and boots again: True")
        b.close()
finally:
    for s in servers:
        s.shutdown()
print("errors:", errs[:10])
ok &= not errs
print("ITCH BUILD TEST", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
