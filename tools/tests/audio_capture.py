"""Records what the browser game actually outputs (PCM tapped from the page's master gain) to a WAV for inspection."""
import sys, time, json, wave, struct, base64
from playwright.sync_api import sync_playwright
from pw_common import BASE, route_pyodide
out = sys.argv[1] if len(sys.argv) > 1 else "capture.wav"
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(); route_pyodide(ctx)
    pg = ctx.new_page()
    pg.goto(BASE + "play.html")
    pg.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=120000)
    pg.keyboard.press("Enter")
    pg.wait_for_function("window.__audio && window.__audio.ctx && window.__audio.ctx.state === 'running'", timeout=20000)
    pg.evaluate("""() => { const a = window.__audio; window.__cap = [];
        const sp = a.ctx.createScriptProcessor(4096, 2, 2); a.out.connect(sp); sp.connect(a.ctx.destination);
        sp.onaudioprocess = (e) => { window.__cap.push(Array.from(e.inputBuffer.getChannelData(0))); }; window.__sp = sp; }""")
    time.sleep(12)
    data = pg.evaluate("() => { const d = window.__cap.flat(); return { sr: window.__audio.ctx.sampleRate, d: d.map((x) => Math.round(Math.max(-1, Math.min(1, x)) * 32767)) }; }")
    b.close()
w = wave.open(out, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(data["sr"]); w.writeframes(struct.pack("<%dh" % len(data["d"]), *[int(x or 0) for x in data["d"]])); w.close()
print("wrote", out, len(data["d"]) / data["sr"], "s")
