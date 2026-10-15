"""Makes realistic test saves with the game's own SaveData code (never touches a real save): a desktop save.json and a
browser backup with two profiles, an extra file and fields from 'the future' that must survive editing."""
import base64, json, os, sys, pathlib, random, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ttgame
tt = ttgame.load()
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tt-test-saves"); out.mkdir(parents=True, exist_ok=True)
random.seed(4)


def rich(path, coins):
    sv = tt.SaveData(path)
    for n in range(1, 8):
        sv.complete_level(n)
    sv.earn(tt.Payout(200000, 500))
    for uid in ("tank:badger", "ammo:fizz", "theme:neon", "map:the-maw", "paint:molten"):
        assert sv.buy(tt.SHOP_BY_UID[uid]) == "", uid
    parts = {"turret": "dome", "hull": "plain", "track": "std", "barrel": "single", "glow": "pulse", "ambient": "sparks", "accent": "GOLD"}
    assert sv.create_custom(parts, "TESTER", "Built by the round-trip test.") == "", sv.create_custom(parts, "TESTER", "x")
    sv.tickets_won = {"volt"}; sv.ticket_active = "regent"
    sv.martyr_open, sv.martyr_paid, sv.martyr_phase, sv.martyr_seen = True, True, 1, True
    sv.story = {"first_battle", "master"}; sv.playtime = 4321.5
    sv.settings = {"AI DIFFICULTY": "HARD", "MUSIC VOLUME": "60%", "eq": "2,0,-2", "heard": "main_theme,green_hills", "rules": "x"}
    sv.loadouts[0].tank, sv.loadouts[0].tank_color = "badger", "MOLTEN"
    sv.coins = coins
    sv.flush()
    d = json.loads(path.read_text())
    d["future_field"] = {"from": "a newer game", "keep": [1, 2, 3]}           # unknown fields must survive
    d["custom_tanks"][0]["decal"] = "skull"                                    # and unknown fields inside custom tanks
    d["custom_tanks"][0]["name"] = "TÉSTER"                                    # non-ASCII text must survive base64
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return d


plain = rich(out / "save.json", 777)
home = out / "home" / ".config" / "terminaltanks"; home.mkdir(parents=True, exist_ok=True)
rich(home / "save.json", 1111)
p2 = tt.SaveData(home / "save_profile2.json"); p2.complete_level(1); p2.earn(tt.Payout(50, 0)); p2.flush()
(home / "profiles.json").write_text(json.dumps({"active": "1", "profiles": [{"id": "1", "name": "ETHAN", "file": "save.json"}, {"id": "2", "name": "GÄST", "file": "save_profile2.json"}]}, ensure_ascii=False), encoding="utf-8")
(out / "home" / "notes.txt").write_text("not a save, must be kept\n")
files = []
for f in sorted((out / "home").rglob("*")):
    if f.is_file():
        files.append({"path": str(f.relative_to(out / "home")), "b64": base64.b64encode(f.read_bytes()).decode()})
(out / "backup.json").write_text(json.dumps({"app": "TerminalTanks", "format": 1, "exported": "2026-10-14T00:00:00Z", "files": files}, indent=2))
(out / "bad-notjson.json").write_text("this is { not json")
(out / "bad-array.json").write_text("[1, 2, 3]")
(out / "bad-otherapp.json").write_text(json.dumps({"app": "SomethingElse", "format": 1, "files": []}))
(out / "bad-path.json").write_text(json.dumps({"app": "TerminalTanks", "format": 1, "files": [{"path": "../../etc/passwd", "b64": "eA=="}]}))
(out / "bad-nosave.json").write_text(json.dumps({"app": "TerminalTanks", "format": 1, "files": [{"path": "notes.txt", "b64": "eA=="}]}))
(out / "bad-random.json").write_text(json.dumps({"hello": "world"}))
print("wrote test saves to", out)
