"""Save Forge round trip with real saves: import -> (edit) -> export -> reimport, checked with the game's own SaveData.load.
Also checks that damaged or foreign files are refused without changing anything, and (with --e2e) that an exported backup
imports into the browser game and shows the edited wallet."""
import base64, json, pathlib, subprocess, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from pw_common import BASE, route_pyodide
import ttgame
tt = ttgame.load()
SV = pathlib.Path(tempfile.mkdtemp(prefix="tt-forge-"))
subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("make_test_saves.py")), str(SV)], check=True)
ok = True
def check(c, label):
    global ok
    ok &= bool(c); print(("PASS " if c else "FAIL ") + label, flush=True)
strip = lambda d: {k: v for k, v in d.items() if k != "unlocked"}


def load_game(doc_or_text):
    p = SV / ("tmp-%d.json" % time.time_ns())
    p.write_text(doc_or_text if isinstance(doc_or_text, str) else json.dumps(doc_or_text), encoding="utf-8")
    return tt.SaveData.load(p)


def same_progress(a, b):
    return (a.completed, a.mission_completed, a.granted, a.coins, a.credits, a.tickets_won, a.ticket_active, a.custom_tanks, a.settings,
            a.martyr_won, a.martyr_paid, a.martyr_phase, a.martyr_open, a.story, round(a.playtime, 1), [vars(l) for l in a.loadouts]) == \
           (b.completed, b.mission_completed, b.granted, b.coins, b.credits, b.tickets_won, b.ticket_active, b.custom_tanks, b.settings,
            b.martyr_won, b.martyr_paid, b.martyr_phase, b.martyr_open, b.story, round(b.playtime, 1), [vars(l) for l in b.loadouts])


with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(accept_downloads=True)
    pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: (errs.append("dialog: " + d.message), d.dismiss()))
    pg.goto(BASE + "save-forge.html"); pg.wait_for_selector("#groups input")

    def upload(path):
        pg.evaluate("() => { document.getElementById('loaded').textContent = '...'; }")
        pg.set_input_files("#load", str(path))
        pg.wait_for_function("(n) => document.getElementById('loaded').textContent.includes(n)", arg=pathlib.Path(path).name, timeout=10000)
        time.sleep(0.2)

    def download(btn):
        with pg.expect_download() as dl:
            pg.click(btn)
        path = SV / ("out-%d-%s" % (time.time_ns(), dl.value.suggested_filename))
        dl.value.save_as(path)
        return path

    # 1. a desktop save.json, untouched: exactly the same progress comes back out
    orig = json.loads((SV / "save.json").read_text(encoding="utf-8"))
    upload(SV / "save.json")
    check("Loaded save.json" in pg.text_content("#loaded"), "plain save loads: " + pg.text_content("#loaded")[:80])
    check("No problems found" in pg.text_content("#inspect"), "inspection finds no problems")
    out = json.loads(download("#plain").read_text(encoding="utf-8"))
    check(strip(out) == strip(orig), "untouched save.json comes back identical (except the summary the game rewrites)")
    check(same_progress(load_game(out), load_game(orig)), "the game reads identical progress from it")

    # 2. a browser backup with two profiles: edit profile 2, everything else byte-identical
    bk = json.loads((SV / "backup.json").read_text())
    upload(SV / "backup.json")
    check(not pg.is_hidden("#profrow"), "profile picker appears for a two-profile backup")
    opts = pg.eval_on_selector_all("#prof option", "o => o.map(x => x.textContent)")
    check(len(opts) == 2 and "GÄST" in opts[1], f"profiles listed by name {opts}")
    pg.select_option("#prof", "1"); time.sleep(0.3)
    pg.fill("#coins", "123456"); pg.fill("#lv", "20")
    pg.check("#groups input[value='paint:molten']"); pg.check("#m-won"); time.sleep(0.2)
    nb = json.loads(download("#make").read_text(encoding="utf-8"))
    byp = {f["path"]: f["b64"] for f in nb["files"]}
    orig_files = {f["path"]: f["b64"] for f in bk["files"]}
    check(set(byp) == set(orig_files), "every file of the backup is still there")
    check(all(byp[k] == v for k, v in orig_files.items() if not k.endswith("save_profile2.json")), "profile 1, profiles.json and other files are byte-identical")
    p2 = json.loads(base64.b64decode(byp[".config/terminaltanks/save_profile2.json"]).decode("utf-8"))
    g = load_game(p2)
    check(g.coins == 123456, f"edited coins read by the game ({g.coins})")
    check(g.completed == set(range(1, 21)), "edited Tournament progress read by the game")
    check(g.is_unlocked("paint:molten") and g.martyr_won and g.blessing_unlocked() and "blessing" in g.unlocked_ammo(), "paint, Martyr defeat and Martyr's Blessing read by the game")
    check(all(g.is_unlocked(u) for u in tt.MARTYR_REWARD_IDS), "the Martyr's relics are all unlocked")

    # 3. edit profile 1 of the original backup: unknown fields and custom tanks survive, non-ASCII text intact
    upload(SV / "backup.json"); pg.select_option("#prof", "0"); time.sleep(0.2); pg.fill("#credits", "999")
    nb1 = json.loads(download("#make").read_text(encoding="utf-8"))
    d1 = json.loads(base64.b64decode({f["path"]: f["b64"] for f in nb1["files"]}[".config/terminaltanks/save.json"]).decode("utf-8"))
    o1 = json.loads((SV / "home/.config/terminaltanks/save.json").read_text(encoding="utf-8"))
    check(d1["future_field"] == o1["future_field"], "an unknown top-level field survives")
    check(d1["custom_tanks"] == o1["custom_tanks"] and d1["custom_tanks"][0]["name"] == "TÉSTER", "custom tanks survive verbatim (unknown fields, non-ASCII names)")
    check({k: v for k, v in strip(d1).items() if k != "wallet"} == {k: v for k, v in strip(o1).items() if k != "wallet"} and d1["wallet"]["credits"] == 999, "only the edited field changed")

    # 4. reimport the exported backup and export again without edits: stable
    p = SV / "reimport.json"; p.write_text(json.dumps(nb), encoding="utf-8")
    upload(p); pg.select_option("#prof", "1"); time.sleep(0.2)
    again = json.loads(download("#make").read_text(encoding="utf-8"))
    a2 = {f["path"]: f["b64"] for f in again["files"]}
    check(a2 == byp, "reimport + export without edits gives the same files")

    # 5. damaged and foreign files are refused and change nothing
    upload(SV / "save.json")
    before = pg.input_value("#coins")
    for bad, why in (("bad-notjson.json", "not valid JSON"), ("bad-array.json", "not a TerminalTanks save"), ("bad-otherapp.json", "different app"),
                     ("bad-path.json", "unsafe file path"), ("bad-nosave.json", "no save file"), ("bad-random.json", "does not look like")):
        upload(SV / bad)
        msg = pg.text_content("#loaded")
        check(why in msg and "still editing" in msg and pg.input_value("#coins") == before, f"{bad} refused: {msg[:90]}")
    check(not errs, f"no page errors or alerts {errs[:2]}")

    # 6. (optional) the exported backup imports into the browser game
    if "--e2e" in sys.argv:
        upload(SV / "save.json"); pg.fill("#coins", "424242")
        e2e = download("#make")
        ctx2 = br.new_context(); route_pyodide(ctx2); g2 = ctx2.new_page()
        g2.on("dialog", lambda d: d.accept())
        g2.goto(BASE + "play.html"); g2.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=120000)
        g2.click("#b-save"); g2.set_input_files("#f-import", str(e2e))
        g2.wait_for_function("document.getElementById('chip').textContent === 'BOOTING'", timeout=30000)
        g2.wait_for_function("document.getElementById('chip').textContent === 'ONLINE'", timeout=90000); time.sleep(3)
        for _ in range(4):
            g2.keyboard.press("Enter"); time.sleep(1.5)
        scr = g2.evaluate("() => window.__term.plain()")
        check("424242" in scr.replace(",", "") , "the browser game shows the edited wallet after importing the backup")
        g2.screenshot(path="/tmp/claude-0/-home-claude/11bf1376-f4ec-5c96-955d-8e63870b06ca/scratchpad/forge-e2e.png")
    br.close()
print("FORGE TEST", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
