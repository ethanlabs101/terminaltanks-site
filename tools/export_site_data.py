#!/usr/bin/env python3
"""Regenerates the website's game data from terminaltanks.py.

    python3 tools/export_site_data.py [--game PATH] [--check]

Writes
  site.js            the generated TT block (unlock registry, Tournament, tickets, Martyr, counts) between its markers
  catalog.json       every tank, ammo type, map, home screen, paint, feature and boss, with where it comes from
  data/render.json   everything tank.js needs to draw any tank (masks, parts, barrels, glows, paints)
  data/parts.json    every Workshop part with how it is unlocked
  data/cheats.json   every cheat code the game accepts
  data/music.json    the soundtrack's metadata (the audio files come from tools/render_music.py)

Nothing here is typed by hand: rerun it after changing the game and commit the result. --check exits 1 if a file would
change (useful in CI to catch a stale site)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ttgame  # noqa: E402

ROOT = ttgame.ROOT
CHECK = "--check" in sys.argv
changed: list[str] = []


def write(rel: str, text: str) -> None:
    p = ROOT / rel
    old = p.read_text(encoding="utf-8") if p.exists() else None
    if old != text:
        changed.append(rel)
        if not CHECK:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")


def jdump(obj, compact: bool = True) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":") if compact else None, indent=None if compact else 1)


def money(coins: int, credits: int) -> str:
    return f"{coins:,} coins" + (f" + {credits} credits" if credits else "")


def main() -> int:
    tt = ttgame.load(ttgame.game_arg(sys.argv))
    BASE = tt.BASE_KITS
    secret_t = {d.key for d in tt.SECRET_DESIGNS}
    secret_a = {a.key for a in tt.SECRET_AMMOS}
    blessing = tt.BLESSING_KEY

    # ---- where every unlockable comes from (first match wins; the order mirrors how a player meets them) --------------
    source: dict[str, tuple[str, str, str]] = {}          # uid -> (how, cost, tier)

    def give(uid: str, how: str, cost: str = "", tier: str = "") -> None:
        source.setdefault(uid, (how, cost, tier))

    for d in tt.DESIGNS[:BASE]:
        give(f"tank:{d.key}", "Starter")
    for a in tt.AMMOS[:BASE]:
        give(f"ammo:{a.key}", "Starter")
    for m in tt.MAPS:
        give(f"map:{m.key}", "Starter")
    give("theme:classic", "Starter")
    for lv in tt.TOURNAMENT:
        for uid in lv.reward_ids():
            give(uid, f"Tournament level {lv.number}")
    for m in tt.MISSIONS:
        for uid in m.rewards:
            give(uid, f"Mission {m.number}")
    for b in tt.TICKET_BOSSES:
        for uid in b.reward_ids():
            give(uid, f"Terminal Ticket: {b.name}")
    for uid in tt.MARTYR_REWARD_IDS:
        give(uid, "The Martyr", "Defeat the Martyr in the Time Machine")
    give(f"ammo:{blessing}", "The Martyr", "Defeat the Martyr. Never sold, granted or cheated", "Legendary")
    tier_name = {3: "Master tier", 4: "Premium"}
    for it in tt.SHOP_ITEMS:
        give(it.uid, "Shop", money(it.coins, it.credits), tier_name.get(it.tier, ""))
    for c in tt.CHEATS.values():
        for uid in c.grants:
            if not uid.startswith("level:"):
                give(uid, "Cheat only")

    # ---- the catalog --------------------------------------------------------------------------------------------------
    cat: list[dict] = []

    def entry(uid: str, kind: str, name: str, blurb: str, **extra) -> None:
        how, cost, tier = source.get(uid, ("", "", ""))
        if not how:
            raise SystemExit(f"export: no source found for {uid} - teach export_site_data.py where it comes from")
        e = {"u": uid, "k": kind, "n": name, "b": blurb, "h": how, "c": cost}
        if tier:
            e["t"] = tier
        e.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
        cat.append(e)

    def ammo_tags(a) -> list[str]:
        m = a.mechanics
        tags = []
        for key, label in (("split", "splits"), ("cluster", "cluster"), ("bounce", "bounces"), ("chain", "chain blasts"), ("pull", "gravity pull"),
                           ("fuse", "delayed blast"), ("terrain", "shapes terrain"), ("wind", "wind-proof"), ("apex", "acts at the apex"),
                           ("rain", "rains shells"), ("burrow", "burrows"), ("radius", "")):
            if key in m and label:
                tags.append(label)
        return tags

    designs_all = list(tt.DESIGNS) + list(tt.SHOP_DESIGNS) + list(tt.MISSION_DESIGNS) + list(tt.TICKET_DESIGNS) + list(tt.SECRET_DESIGNS) + list(tt.ANCIENT_DESIGNS)
    for d in designs_all:
        parts = list(d.parts) + [d.barrel, d.glow] + [x for x in d.ambient.split("+") if x != "none"]
        entry(f"tank:{d.key}", "tank", d.name, d.blurb, p=" ".join(p for p in parts if p and p != "none"),
              hv=1 if d.hover else None)
    ammos_all = list(tt.AMMOS) + list(tt.SHOP_AMMOS) + list(tt.MISSION_AMMOS) + list(tt.TICKET_AMMOS) + list(tt.SECRET_AMMOS) + list(tt.ANCIENT_AMMOS)
    for a in ammos_all:
        entry(f"ammo:{a.key}", "ammo", a.name, a.blurb, fx=", ".join(ammo_tags(a)) or None)
    for m in list(tt.MAPS) + list(tt.SPECIAL_MAPS):
        entry(f"map:{m.key}", "map", m.name, m.description)
    for k in tt.HOME_ORDER:
        th = tt.HOME_THEMES.get(k)
        name = th.name if th else k
        blurb = th.blurb if th else {"CLASSIC": "The original night sky over the ridge.", "MASTER": "Aurora over the Master's Citadel, and a crowned tank firing prism shells.",
                                     "SECRET": "A terminal that has seen too much: raining code and a green ghost of a tank."}.get(k, "")
        entry(f"theme:{k.lower()}", "theme", name, blurb)
    paint_blurb = {it.uid: it.blurb for it in tt.SHOP_ITEMS}
    paint_blurb["paint:astral"] = "The Martyr's own colours: a drifting nebula with twinkling stars, on ANY tank and its shells."
    paints = []
    for name, _ in tt.ANIM_PAINTS:
        if name == "RGB":
            for uid, nm in (("rgb:hull", "RGB HULL COLOR"), ("rgb:shell", "RGB SHELL COLOR")):
                entry(uid, "paint", nm, paint_blurb[uid], an=1)
            paints.append({"n": "RGB", "hull": "rgb:hull", "shell": "rgb:shell"})
            continue
        uid = f"paint:{name.lower()}"
        entry(uid, "paint", f"{name} PAINT", paint_blurb.get(uid, ""), an=1)
        paints.append({"n": name, "hull": uid, "shell": uid})
    entry("master_difficulty", "feature", "MASTER DIFFICULTY", "The AI's sharpest setting, for Single Player once the Master falls.")

    # features that are not unlockables but are part of the game's progression: shown so the catalog tells the whole story
    def feature(uid: str, name: str, blurb: str, how: str, cost: str = "", kind: str = "feature", tier: str = "", an: int = 0) -> None:
        e = {"u": uid, "k": kind, "n": name, "b": blurb, "h": how, "c": cost}
        if an:
            e["an"] = an
        if tier:
            e["t"] = tier
        cat.append(e)

    feature("x:special", "SPECIAL ATTACK", f"Press X to give up a turn and bank a charge. After {tt.MatchConfig.__dataclass_fields__['special_wait'].default} charges your next "
            "shot is one huge 3-damage blast. Turn it on in the rules of Single Player, Two Player or LAN.", "Starter", "Match rule", an=1)
    feature("x:ticket", "TERMINAL TICKET", tt.SHOP_BY_UID["ticket"].blurb, "Shop",
            money(*tt.TICKET_PRICE) + ". Opens after the Master and the Mothership fall", tier="Premium")
    feature("x:timemachine", "MARTYR'S TIME MACHINE", tt.SHOP_BY_UID["timemachine"].blurb, "Shop",
            money(*tt.MARTYR_PRICE) + ". Opens when every vault boss has fallen", tier="Premium")
    feature("x:workshop", "THE WORKSHOP", f"Build your own tank from unlocked parts and keep up to {tt.CUSTOM_TANK_MAX} designs. "
            "Opens after Tournament level 5.", "Tournament level 5", money(tt.CUSTOM_TANK_FEE, 0) + " per saved design", kind="workshop")
    feature("x:hover", "HOVER UPGRADE", "Lift a custom tank off the ground: it floats, bobs and throws a thruster glow. Opens after the Mothership falls.",
            "Mission 50", money(tt.HOVER_COINS, tt.HOVER_CREDITS) + " on top of the design fee", kind="workshop")
    comp = tt.component_tables()
    feature("x:parts", "WORKSHOP PARTS", f"{sum(len(v) for k, v in comp.items() if k != 'accent')} parts across turrets, hulls, tracks, barrels, glows and "
            f"ambient effects, plus {len(comp['accent'])} accent colors. You may use every part of every tank you own.", "Starter", "Some free, the rest from tanks you own", kind="workshop")

    # bosses and other enemies
    for lv in tt.TOURNAMENT:
        rule = {"streak": f"Win {lv.wins} rounds in a row", "flawless": f"Win {lv.wins} rounds without losing one",
                "onestrike": "One strike only", "glass": f"Your tank has {tt.GLASS_HP} hearts", "gale": "The wind is stuck at its strongest"}.get(lv.rule, f"Win {lv.wins} rounds; the boss may win twice")
        cat.append({"u": f"boss:level{lv.number}", "k": "boss", "n": lv.boss, "b": lv.blurb, "h": f"Tournament level {lv.number}",
                    "c": f"{lv.name}. {lv.difficulty.name.title()} AI. {rule}", "tk": lv.tank, "col": lv.boss_color,
                    **({"t": "Master tier"} if lv.number > len(tt.TOURNAMENT) - tt.FINAL_BOSSES else {})})
    ufos = [m for m in tt.MISSIONS if m.kind == "ufo"]
    cat.append({"u": "boss:ufo", "k": "boss", "n": "UFO SAUCERS", "b": ufos[0].blurb + " Each mission sends a bigger one: "
                + ", ".join(m.name.replace("UFO: ", "").title() for m in ufos) + ".",
                "h": "Mission " + str(ufos[0].number), "c": "Missions " + ", ".join(str(m.number) for m in ufos)
                + f". {min(m.ufo_hp for m in ufos)} to {max(m.ufo_hp for m in ufos)} HP", "ufo": 1})
    for m in tt.MISSIONS:
        if m.kind == "mother":
            cat.append({"u": f"boss:mission{m.number}", "k": "boss", "n": "THE MOTHERSHIP", "b": m.blurb + " It is shielded until both drones are destroyed.",
                        "h": f"Mission {m.number}", "c": f"{m.ufo_hp} HP, two drones. {m.diff.name.title()} AI", "ufo": 2})
    for b in tt.TICKET_BOSSES:
        cat.append({"u": f"boss:ticket-{b.key}", "k": "boss", "n": b.name, "b": f"“{b.taunt.capitalize()}” An Ancient Hoarder sealed in a Terminal Ticket.",
                    "h": f"Terminal Ticket: {b.name}", "c": f"{b.hp} HP", "tk": b.tank, "t": "Premium"})
    cat.append({"u": "boss:martyr", "k": "boss", "n": "THE MARTYR", "b": "The legendary mage, waiting ten thousand years inside his own hourglass. Three phases: "
                + ", ".join(p.split("-")[-1].strip().title() for p in tt.MARTYR_PHASES) + ".",
                "h": "The Martyr", "c": f"{'/'.join(str(x) for x in tt.MARTYR_MAGE_HP)} HP across three phases", "tk": "a_martyr", "t": "Legendary"})

    # ---- the generated site.js block -----------------------------------------------------------------------------------
    U = tt.unlockables()
    pairs = lambda kind: [[u.uid.split(":", 1)[1], (u.label if kind != "theme" else tt.HOME_THEMES[u.uid.split(":", 1)[1].upper()].name
                                                   if u.uid.split(":", 1)[1].upper() in tt.HOME_THEMES else u.uid.split(":", 1)[1].upper())]
                          for u in U if u.kind == kind]
    tank_pairs = [p for p in pairs("tank")]
    ammo_pairs = [p for p in pairs("ammo")]
    map_pairs = [[m.key, m.name] for m in tt.SPECIAL_MAPS]
    theme_pairs = pairs("theme")
    comps = (sum(len(v) for k, v in comp.items() if k != "accent"))
    official_t = [d for d in tt.ALL_DESIGNS if d.key not in secret_t]
    official_a = [a for a in tt.ALL_AMMOS if a.key not in secret_a]
    music_count = len(tt.SONGS)
    counts = {
        "tanks": len(tt.ALL_DESIGNS), "ammo": len(tt.ALL_AMMOS), "maps": len(tt.MAPS) + len(tt.SPECIAL_MAPS), "specialMaps": len(tt.SPECIAL_MAPS),
        "screens": len(tt.HOME_ORDER), "parts": comps, "accents": len(comp["accent"]), "customMax": tt.CUSTOM_TANK_MAX,
        "unlockables": len(U), "grantable": sum(1 for u in U if u.uid != f"ammo:{blessing}"), "catalog": len(cat), "cheats": len(tt.CHEATS),
        "ticketCoins": tt.TICKET_PRICE[0], "ticketCredits": tt.TICKET_PRICE[1], "martyrCoins": tt.MARTYR_PRICE[0], "martyrCredits": tt.MARTYR_PRICE[1],
        "customFee": tt.CUSTOM_TANK_FEE, "hoverFee": tt.HOVER_COINS, "saveVersion": tt.SaveData.VERSION, "lines": sum(sum(1 for _ in open(f, encoding="utf-8"))
                                                        for f in [tt.__file__] + [m.__file__ for m in getattr(tt, "__package_modules__", [])]),
        "menuTanks": len(official_t), "menuAmmo": len(official_a), "startMaps": len(tt.MAPS), "paints": len(tt.ANIM_PAINTS), "songs": music_count,
        "profiles": tt.PROFILE_MAX, "missions": len(tt.MISSIONS), "levels": len(tt.TOURNAMENT), "bosses": sum(1 for e in cat if e["k"] == "boss"),
    }
    data = {
        "version": tt.__version__,
        "tanks": tank_pairs, "ammo": ammo_pairs, "maps": map_pairs, "themes": theme_pairs,
        "levels": [lv.name for lv in tt.TOURNAMENT], "words": list(tt.LEVEL_WORDS),
        "rewards": [list(lv.reward_ids()) for lv in tt.TOURNAMENT],
        "missionRewards": {str(m.number): list(m.rewards) for m in tt.MISSIONS if m.rewards},
        "tickets": [{"key": b.key, "name": b.name, "uids": list(b.reward_ids())} for b in tt.TICKET_BOSSES],
        "martyr": {"rewards": list(tt.MARTYR_REWARD_IDS), "blessing": f"ammo:{blessing}", "coins": tt.MARTYR_WIN_COINS},
        "paints": paints,
        "colors": [n for n, _ in tt.COLOR_CHOICES],
        "counts": counts,
        "missions": len(tt.MISSIONS),
        "base": {"tanks": [[d.key, d.name] for d in tt.DESIGNS[:BASE]], "ammo": [[a.key, a.name] for a in tt.AMMOS[:BASE]]},
        "secret": {"tanks": sorted(secret_t), "ammo": sorted(secret_a - {blessing})},
    }
    js = (ROOT / "site.js").read_text(encoding="utf-8")
    start, end = "/* BEGIN GENERATED (tools/export_site_data.py) */", "/* END GENERATED */"
    block = start + "\nconst TT_DATA = " + jdump(data) + ";\n" + end
    if start in js:
        js = js[:js.index(start)] + block + js[js.index(end) + len(end):]
    else:
        raise SystemExit("site.js has no generated-block markers")
    write("site.js", js)
    write("catalog.json", jdump(cat))

    # ---- workshop: render data and parts --------------------------------------------------------------------------------
    rgb = lambda c: list(c) if c is not None else None
    render = {
        "w": tt.TANK_W, "h": tt.TANK_H, "pivot": tt.PIVOT_H, "barrelLen": tt.BARREL_LEN,
        "turrets": {k: list(v) for k, v in tt._TURRETS.items()}, "hulls": {k: list(v) for k, v in tt._HULLS.items()},
        "tracks": {k: list(v) for k, v in tt._TRACKS.items()},
        "barrels": {k: {"offsets": list(v.offsets), "length": v.length, "style": v.style} for k, v in tt.BARRELS.items()},
        "glows": list(tt.GLOW_STYLES), "ambients": list(tt.AMBIENT_KINDS), "materials": sorted(tt.MATERIALS),
        "colors": [[n, list(c)] for n, c in tt.COLOR_CHOICES],
        "paints": [[n, n.lower()] for n, _ in tt.ANIM_PAINTS],
        "fallback": dict(tt.CUSTOM_FALLBACK), "fmt": tt.CUSTOM_FMT, "nameMax": 14, "loreMax": 60, "fee": tt.CUSTOM_TANK_FEE,
        "hoverFee": tt.HOVER_COINS, "slots": tt.CUSTOM_TANK_MAX,
        "designs": [{"key": d.key, "name": d.name, "mask": list(d.mask), "parts": list(d.parts), "barrel": d.barrel, "glow": d.glow,
                     "ambient": d.ambient, "accent": rgb(d.accent), "paint": rgb(d.paint), "hover": d.hover} for d in tt.ALL_DESIGNS],
    }
    write("data/render.json", jdump(render))

    src_of = {e["u"]: e for e in cat}
    owners: dict = {s: {} for s in tt.CUSTOM_SLOTS}
    starter = {d.key for d in tt.DESIGNS[:BASE]}
    for d in tt.ALL_DESIGNS:
        for slot, cid in list(zip(("turret", "hull", "track"), d.parts)) + [("barrel", d.barrel), ("glow", d.glow)] + [("ambient", a) for a in d.ambient.split("+")]:
            owners[slot].setdefault(cid, []).append(d)
    order = {"Starter": 0, "Tournament": 1, "Mission": 2, "Shop": 3, "Terminal": 4, "The Martyr": 5, "Cheat": 6}
    rank = lambda d: (order.get(src_of.get(f"tank:{d.key}", {"h": "Starter"})["h"].split(" ")[0] if d.key not in starter else "Starter", 9), tt.ALL_DESIGNS.index(d))
    parts_out: dict = {}
    for slot in tt.CUSTOM_SLOTS:
        rows = []
        for cid in comp[slot]:
            if slot == "accent":
                rows.append({"id": cid, "n": cid, "free": True, "tag": "Free", "rgb": list(tt.COLOR_BY_NAME[cid]), "providers": [], "more": 0})
                continue
            prov = sorted([d for d in owners[slot].get(cid, []) if d.key not in starter], key=rank)
            free = cid in tt.FREE_PARTS.get(slot, set()) or any(d.key in starter for d in owners[slot].get(cid, []))
            plist = [{"k": d.key, "n": d.name, "h": src_of[f"tank:{d.key}"]["h"], "c": src_of[f"tank:{d.key}"]["c"]} for d in prov]
            tag = "Free" if free else (plist[0]["h"] + (", " + plist[0]["c"] if plist[0]["h"] == "Shop" and plist[0]["c"] else "")) if plist else "Cheat only"
            if tag.startswith("Shop, ") and plist:
                tag = "Shop, " + plist[0]["c"]
            rows.append({"id": cid, "n": cid.upper().replace("_", " "), "free": free, "premium": cid in tt.PREMIUM_PARTS, "tag": tag,
                         "providers": plist[:3], "more": max(0, len(plist) - 3)})
        parts_out[slot] = rows
    write("data/parts.json", jdump(parts_out))
    for legacy, obj in (("render.json", render), ("parts.json", parts_out)):     # copies older pages linked to from the site root
        if (ROOT / legacy).exists():
            write(legacy, jdump(obj))

    # ---- cheats -------------------------------------------------------------------------------------------------------
    cheats = []
    for c in tt.CHEATS.values():
        cheats.append({"code": c.code, "grants": list(c.grants), "everything": c.everything, "theme": c.activate_theme, "text": c.text})
    write("data/cheats.json", jdump(cheats))

    # ---- music metadata -------------------------------------------------------------------------------------------------
    write("data/music.json", jdump(music_meta(tt), compact=True))

    for rel in changed:
        print(("would change " if CHECK else "wrote ") + rel)
    if not changed:
        print("site data is up to date")
    return 1 if (CHECK and changed) else 0


GROUP_LABEL = {"menu": "Home screens", "battle": "Battlefields", "tbos": "Tournament bosses", "mission": "Missions & aliens",
               "ticket": "Terminal Ticket bosses", "martyr": "The Martyr", "story": "Story"}


def music_slug(tt, sid: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "-", sid.lower()).strip("-")


def music_meta(tt) -> dict:
    """One record per song in the in-game jukebox, with where it plays. Audio and cover paths follow render_music.py."""
    idx = ROOT / "music" / "index.json"
    rendered = json.loads(idx.read_text()) if idx.exists() else {}
    meters = {"44": "4/4", "34": "3/4", "68": "6/8", "78": "7/8", "54": "5/4", "98": "9/8", "128": "12/8"}
    notes = tt._NOTE_NAMES
    scales = tt._SCALE_NAMES
    hand = {sid for sid in tt.SONGS if not (sid.startswith("home_") or sid.startswith("map_"))}
    all_maps = tt.all_maps()
    themes = {k: (tt.HOME_THEMES[k].name if k in tt.HOME_THEMES else k) for k in tt.HOME_ORDER}
    lv_of = {s: i + 1 for i, s in enumerate(tt.TOURNAMENT_SONGS)}
    tb = {f"t_{b.key}": b.name for b in tt.TICKET_BOSSES}
    out = []
    for i, (sid, sp) in enumerate(tt.SONGS.items()):
        grp = tt.song_group(sid)
        where = []
        for k in tt.SONG_HOMES.get(sid, ()):
            where.append("Home screen: " + themes.get(k, k))
        for k in tt.SONG_MAPS.get(sid, ()):
            if k in all_maps:
                where.append("Battlefield: " + all_maps[k].name)
        if sid in lv_of:
            where.append(f"Tournament level {lv_of[sid]}: {tt.TOURNAMENT[lv_of[sid] - 1].name}")
        if sid in tb:
            where.append("Terminal Ticket: " + tb[sid])
        if sid in tt.MARTYR_SONGS:
            where.append("The Martyr, " + tt.MARTYR_PHASES[tt.MARTYR_SONGS.index(sid)].split("-")[0].strip().title())
        extra = {"saucer_attack": "UFO missions", "mothership": "Mission 50: the Mothership", "boss_rush": "Boss Rush missions",
                 "squad_up": "Co-op and 2v1 missions", "tutorial": "Tutorial and practice", "shop_jingle": "The shop", "workshop": "The Workshop",
                 "whisper": "Story whispers", "time_machine": "The Martyr's Time Machine", "the_blessing": "Martyr's Blessing",
                 "protector": "The Eternal home screen and the ending"}
        if sid in extra and extra[sid] not in where:
            where.append(extra[sid])
        song = tt.song_of(sid)
        slug = music_slug(tt, sid)
        out.append({
            "id": sid, "n": sp.name, "g": grp, "gl": GROUP_LABEL.get(grp, grp), "d": sp.desc, "bpm": sp.bpm,
            "key": f"{notes[sp.root % 12]} {scales.get(sp.scale, sp.scale.upper()).title()}", "m": meters.get(sp.meter, sp.meter), "st": sp.style,
            "len": round(song.total / tt.AU_SR, 1), "hand": sid in hand, "w": where, "i": i + 1,
            # where the game loops it: back to section A at the end (the play page loops the MP3 there, like the game does)
            "lp": round(song.secs.get("A", 0) / tt.AU_SR, 4), "le": round(song.total / tt.AU_SR, 4),
            # exact sample layout of the rendered files (tools/render_music.py), so the play page can loop like the game
            **({"x": {k: rendered[sid][k] for k in ("n", "a", "p", "ln", "lb", "pad") if k in rendered[sid]}} if isinstance(rendered.get(sid), dict) and "n" in rendered[sid] else {}),
            **({"story": True} if isinstance(rendered.get(sid), dict) and rendered[sid].get("story") else {}),
            "a": f"music/{slug}.mp3", "cv": f"music/covers/{slug}.png",
            "disc": {k: (list(v) if isinstance(v, tuple) else v) for k, v in tt.song_disc(sid).items() if k in ("kind", "bold", "avg", "second", "label", "rpm")},
        })
    return {"version": tt.__version__, "groups": [[GROUP_LABEL[g], g] for _, g in tt.JUKEBOX_GROUPS], "songs": out}


if __name__ == "__main__":
    sys.exit(main())
