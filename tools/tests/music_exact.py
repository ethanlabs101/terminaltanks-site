"""Checks that the play page's music is the desktop game's music: the page's own player (SoundHost) renders a song through
three loops into an OfflineAudioContext, and the result is compared, sample for sample, with the game's audio engine
(Mixer) playing the same song. Reports the match in dB around every loop point (MP3 alone is about 23-38 dB).
    python3 tools/tests/music_exact.py [song_id]"""
import sys, time, json, pathlib
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from pw_common import BASE, route_pyodide
import ttgame

sid = next((a for a in sys.argv[1:] if not a.startswith("-")), "main_theme")
tt = ttgame.load()
song = tt.song_of(sid)
LOOPS = 3
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(); route_pyodide(ctx); pg = ctx.new_page()
    pg.goto(BASE + "play.html"); pg.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=120000)
    pg.keyboard.press("Enter"); pg.wait_for_function("window.__audio && window.__audio.mctx", timeout=30000)
    res = pg.evaluate("""async ([sid, loops]) => {
      const A = window.__audio; await A.loadIndex();
      const info = A.songs.get(sid), x = info.x, SR = 22050;
      const N = x.n + loops * x.p + SR;                             // first pass + loops + a second
      const off = new OfflineAudioContext(2, N, SR);
      const H = Object.create(A);                                   // the page's player, on an offline context
      Object.assign(H, { mctx: off, musicBus: off.createGain(), eqNode: null, cache: new Map(), cur: null, gen: 0, loop: true, mood: 'menu' });
      H.musicBus.connect(off.destination);
      H.music(sid, 0.05);
      while (!H.cur) await new Promise((r) => setTimeout(r, 50));
      for (let t = 1; t < N / SR; t += 1) off.suspend(t).then(() => { H.schedule(); off.resume(); });
      const buf = await off.startRendering();
      const t0 = Math.round(H.cur.t0 * SR);
      // around each loop point (and the seam ends), 0.2 s windows, as int16
      const pts = []; for (let k = 0; k < loops; k++) { const at = x.n + k * x.p; pts.push(at, at + x.ln, at + x.p - x.lb); }
      pts.push(Math.round(SR * 30));
      const L = buf.getChannelData(0), R = buf.getChannelData(1), W = 4410, out = {};
      for (const at of pts) { const a = [], c = []; for (let i = at - W / 2; i < at + W / 2; i++) { a.push(Math.round(L[t0 + i] * 32768)); c.push(Math.round(R[t0 + i] * 32768)); } out[at] = [a, c]; }
      return { x, t0, out };
    }""", [sid, LOOPS])
    b.close()

x = res["x"]
mx = tt.Mixer(cache=False); mx.load_song(sid)
while mx.partial:
    mx._fill(next(iter(mx.partial)))
mx.command(f"music {sid} 0.05"); mx.command("loop 1")
need = x["n"] + LOOPS * x["p"] + 22050
raw = bytearray()
while len(raw) < need * 4:
    raw += mx.render()
ref = np.frombuffer(bytes(raw[:need * 4]), dtype=np.int16).reshape(-1, 2).astype(np.float64)
snr = lambda a, b: 10 * np.log10((a ** 2).sum() / max(1e-9, ((a - b) ** 2).sum()))
worst = 99
for at, (l, r) in res["out"].items():
    at = int(at); web = np.stack([np.array(l, float), np.array(r, float)], 1)
    w = ref[at - 2205:at + 2205]
    d = snr(w, web); worst = min(worst, d)
    k = (at - x["n"]) // x["p"] if at >= x["n"] else -1
    what = "30 s into the song" if at == 22050 * 30 else ("loop point" if (at - x["n"]) % x["p"] == 0 else "seam end" if (at - x["n"]) % x["p"] == x["ln"] else "last block")
    print(f"  {what:20s} pass {k + 2 if k >= 0 else 1}: {d:5.1f} dB")
ok = worst > 15
print("MUSIC EXACT", "PASS" if ok else "FAIL", f"(worst {worst:.1f} dB)")
sys.exit(0 if ok else 1)
