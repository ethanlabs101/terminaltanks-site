"""Records demo.webm / demo.mp4 for the home page: the real game running on play.html, a two-player match where both
sides trade a few shots. The clip is cropped to the game's canvas and scaled to 1200 x 630 (the size of preview.png).
    python3 tools/tests/record_demo.py          (site served on TT_BASE, ffmpeg installed)"""
import pathlib, re, shutil, subprocess, sys, tempfile, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pw_common import BASE, route_pyodide
ROOT = pathlib.Path(__file__).resolve().parents[2]


def screen(pg):
    return pg.evaluate("() => window.__term.plain()")


def press(pg, key, n=1, wait=0.35):
    for _ in range(n):
        pg.keyboard.press(key); time.sleep(wait)


AIMING = "() => ((window.__gs && window.__gs.raw) || '').split(':')[2] === '1'"   # a local player is aiming (any rules)


def wait_mine(pg, t=20):
    t0 = time.time()
    while time.time() - t0 < t:
        if pg.evaluate(AIMING):
            return True
        time.sleep(0.2)
    return False


tmp = pathlib.Path(tempfile.mkdtemp())
with sync_playwright() as p:
    b = p.chromium.launch()
    vp = {"width": 1280, "height": 760}
    ctx = b.new_context(viewport=vp)
    route_pyodide(ctx)
    pg = ctx.new_page()
    t_open = time.time()
    pg.goto(BASE + "play.html")
    pg.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=120000)
    for _ in range(6):
        press(pg, "Enter", wait=1.5)
        if re.search("SELECT MISSION", screen(pg)):
            break
    time.sleep(1)
    press(pg, "ArrowDown", wait=0.6); press(pg, "Enter", wait=2.5)     # TWO PLAYER -> rules
    press(pg, "ArrowUp", 1); press(pg, "Enter", wait=1.2)              # GO
    for i in range(30):
        if pg.evaluate("() => (window.__gs && window.__gs.raw) || ''").startswith("battle"):
            break
        s = screen(pg)
        if "SHOOTS FIRST" in s and "PLAYER 2" in s and i % 2:
            press(pg, "ArrowRight", wait=0.3)
        press(pg, "Enter", wait=1.2)
    # record the game's own canvas, in the page, in real time (the round intro included)
    pg.evaluate("""() => { const c = document.querySelector('canvas'); window.__rec = { chunks: [] };
        const r = new MediaRecorder(c.captureStream(30), { mimeType: 'video/webm;codecs=vp9', videoBitsPerSecond: 12e6 });
        r.ondataavailable = (e) => { if (e.data.size) window.__rec.chunks.push(e.data); }; r.start(1000); window.__rec.r = r; }""")
    t_start = time.time()
    wait_mine(pg, 90)
    T_SKIP = max(0.0, time.time() - t_start - 2.5)
    print(f"  first turn after {time.time() - t_start:.1f}s", flush=True)
    plans = [(3, 2), (-2, 4), (1, 5), (-1, 6)]                            # (aim steps, power steps) per turn: varied, deterministic
    for aim, power in plans:
        if not wait_mine(pg, 60):
            break
        time.sleep(0.6)
        press(pg, "ArrowRight" if aim > 0 else "ArrowLeft", abs(aim), wait=0.15)
        press(pg, "ArrowUp", power, wait=0.15)
        time.sleep(0.4)
        press(pg, "Space", wait=0.2)
        print(f"  fired at {time.time() - t_start:.1f}s", pg.evaluate("() => window.__gs && window.__gs.raw"), flush=True)
        t0 = time.time()
        while time.time() - t0 < 15 and pg.evaluate(AIMING):
            time.sleep(0.2)                                               # the shot is away once the turn is no longer 'aiming'
        time.sleep(3.5)
    b64 = pg.evaluate("""() => new Promise((ok) => { const r = window.__rec.r; r.onstop = () => { const fr = new FileReader();
        fr.onload = () => ok(fr.result.split(',')[1]); fr.readAsDataURL(new Blob(window.__rec.chunks, { type: 'video/webm' })); }; r.stop(); })""")
    ctx.close(); b.close()

import base64
vid = tmp / "raw.webm"; vid.write_bytes(base64.b64decode(b64))
info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(vid)], capture_output=True, text=True).stdout.strip()
dur = 30.0
vf = "scale=1200:630:force_original_aspect_ratio=decrease:flags=neighbor,pad=1200:630:(ow-iw)/2:(oh-ih)/2:color=0x05090f,fps=30"
ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{T_SKIP:.2f}", "-t", f"{dur:.2f}", "-i", str(vid), "-vf", vf, "-an"]
subprocess.run(ff + ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "34", "-row-mt", "1", str(ROOT / "demo.webm")], check=True)
subprocess.run(ff + ["-c:v", "libx264", "-crf", "24", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(ROOT / "demo.mp4")], check=True)
shutil.rmtree(tmp, ignore_errors=True)
print("wrote demo.webm / demo.mp4 from", info, "s of canvas video, skipping", round(T_SKIP, 1))
