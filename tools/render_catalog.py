#!/usr/bin/env python3
"""Draws every catalog picture with the game's own rendering code (terminaltanks.py), so the site always shows exactly
what the game draws.

    python3 tools/render_catalog.py               # render whatever is missing, then rebuild shots/manifest.json
    python3 tools/render_catalog.py --all         # re-render everything
    python3 tools/render_catalog.py --only paint  # one kind: tank ammo map theme paint boss feature
    python3 tools/render_catalog.py --check       # list missing pictures, exit 1 if any

Still pictures are PNG. Animated paints (and the Martyr's Blessing) are also written as a looping MP4 plus a small GIF, with
the first frame kept as a PNG poster, because their whole point is the movement. Needs Pillow; MP4/GIF need ffmpeg."""
from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ttgame  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = ttgame.ROOT
SHOTS = ROOT / "shots"
ARGS = sys.argv[1:]
ALL = "--all" in ARGS
ONLY = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else ""
CHECK = "--check" in ARGS
FPS = 30
tt = ttgame.load(ttgame.game_arg(ARGS))


# ---------------------------------------------------------------------------------------------------------------------------
# canvases -> images
# ---------------------------------------------------------------------------------------------------------------------------
def canvas_image(cv, scale: int) -> Image.Image:
    im = Image.new("RGB", (cv.w, cv.h))
    im.putdata([tuple(c) for row in cv.rows for c in row])
    return im.resize((cv.w * scale, cv.h * scale), Image.NEAREST)


FONT_PATHS = ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "DejaVuSansMono.ttf")
_font = None


def font():
    global _font
    if _font is None:
        for p in FONT_PATHS:
            try:
                _font = ImageFont.truetype(p, 10)
                break
            except OSError:
                continue
        else:
            _font = ImageFont.load_default()
    return _font


def screen_image(screen, cw: int = 6, ch: int = 12) -> Image.Image:
    """Paints a game Screen the way play.html's canvas renderer does: half-block pixels, block elements, then text."""
    im = Image.new("RGB", (screen.cols * cw, screen.rows * ch))
    dr = ImageDraw.Draw(im)
    f = font()
    for y, row in enumerate(screen.back):
        for x, (c, fg, bg) in enumerate(row):
            x0, y0 = x * cw, y * ch
            dr.rectangle((x0, y0, x0 + cw - 1, y0 + ch - 1), fill=tuple(bg))
            if c in (" ", ""):
                continue
            o = ord(c)
            if c == "▀":
                dr.rectangle((x0, y0, x0 + cw - 1, y0 + ch // 2 - 1), fill=tuple(fg))
            elif c == "▄":
                dr.rectangle((x0, y0 + ch // 2, x0 + cw - 1, y0 + ch - 1), fill=tuple(fg))
            elif c == "█":
                dr.rectangle((x0, y0, x0 + cw - 1, y0 + ch - 1), fill=tuple(fg))
            elif 0x2581 <= o <= 0x2587:
                h = round(ch * (o - 0x2580) / 8)
                dr.rectangle((x0, y0 + ch - h, x0 + cw - 1, y0 + ch - 1), fill=tuple(fg))
            elif 0x2591 <= o <= 0x2593:
                dr.rectangle((x0, y0, x0 + cw - 1, y0 + ch - 1), fill=tt.mix(tuple(bg), tuple(fg), (o - 0x2590) * 0.25))
            else:
                dr.text((x0 + cw / 2, y0 + ch * 0.78), c, fill=tuple(fg), font=f, anchor="ms")
    return im


def save_png(im: Image.Image, name: str) -> str:
    im.save(SHOTS / name, optimize=True)
    return name


def save_anim(frames: list, stem: str, fps: int = FPS) -> dict:
    """frames: PIL images. Writes <stem>.webm (VP9) and <stem>.mp4 (H.264) for the page, <stem>.gif (15 fps) and the poster <stem>.png."""
    out = {"poster": save_png(frames[0], stem + ".png")}
    if not shutil.which("ffmpeg"):
        print("  (ffmpeg missing: only the poster was written)")
        return out
    with tempfile.TemporaryDirectory() as td:
        for i, im in enumerate(frames):
            im.save(f"{td}/f{i:04d}.png")
        w, h = frames[0].size
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", f"{td}/f%04d.png",
                        "-vf", f"scale={w - w % 2}:{h - h % 2}:flags=neighbor", "-c:v", "libx264", "-preset", "veryslow", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(SHOTS / (stem + ".mp4"))], check=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", f"{td}/f%04d.png",
                        "-vf", f"scale={w - w % 2}:{h - h % 2}:flags=neighbor", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-row-mt", "1",
                        "-pix_fmt", "yuv420p", "-an", str(SHOTS / (stem + ".webm"))], check=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", f"{td}/f%04d.png",
                        "-vf", "fps=15,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none",
                        "-loop", "0", str(SHOTS / (stem + ".gif"))], check=True)
    out["mp4"], out["webm"], out["gif"] = stem + ".mp4", stem + ".webm", stem + ".gif"
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# scenes
# ---------------------------------------------------------------------------------------------------------------------------
SETTINGS = tt.Settings()
CYAN, ORANGE, YELLOW = tt.COLOR_BY_NAME["CYAN"], tt.COLOR_BY_NAME["ORANGE"], tt.COLOR_BY_NAME["YELLOW"]


def range_sky(w: int, h: int, ground: int = 4):
    """The plain test range the existing catalog pictures use: a night gradient and a slate strip of ground."""
    cv = tt.PixelCanvas(w, h)
    for y in range(h):
        cv.rows[y] = [tt.mix((16, 30, 44), (6, 10, 18), y / (h - 1))] * w
    for x in range(w):
        for y in range(ground):
            cv.plot(x, y, (62, 94, 110) if y == ground - 1 else (30, 44, 56))
    return cv


def tank_picture(design, body=CYAN, seed: int = 7, angle: float = 35, w: int = 36, h: int = 28, x: float = 14, t_end: float = 2.0, facing: int = 1):
    """A tank on the range at scale 2 (36 x 28 pixels, shown 8x), with its ambient particles already in the air."""
    ps = tt.ParticleSystem(600)
    fx = tt.EffectsFactory(ps, SETTINGS, random.Random(seed))
    t, dt = 0.0, 1 / FPS
    while t < t_end:
        fx.ambient(design, x, 4, tt.live_color(body, t), dt)
        ps.update(dt)
        t += dt
    cv = range_sky(w, h)
    ps.draw(cv)
    tt.draw_tank(cv, x, 4, facing, angle, body, scale=2, design=design, t=t)
    ps.draw(cv)
    return canvas_image(cv, 8)


def ufo_picture(mother: bool):
    """The alien saucer at its battle size (the Mothership with its two drones), drawn by the game's draw_ufo."""
    w, h = (72, 36) if mother else (36, 28)
    cv = range_sky(w, h)
    if mother:
        tt.draw_ufo(cv, tt._fake_tank(0, (120, 255, 190), 36.0, 10.0, -1, kind="ufo", scale=4.0, hover=0, hp=24, max_hp=24, shield=1), 1.3)
        for k, (x, col) in enumerate(((12.0, (200, 140, 255)), (60.0, (140, 200, 255)))):
            tt.draw_ufo(cv, tt._fake_tank(k + 1, col, x, 17.0, -1, kind="ufo", scale=2.0, hover=0, hp=3, max_hp=3), 1.3 + k)
        return canvas_image(cv, 8)
    tt.draw_ufo(cv, tt._fake_tank(0, (90, 230, 160), 18.0, 10.0, -1, kind="ufo", scale=3.0, hover=0, hp=5, max_hp=5), 1.3)
    return canvas_image(cv, 8)


def ammo_picture(ammo, shot=YELLOW, seed: int = 3):
    """One shell in flight while the previous one detonates: 112 x 40 pixels, shown 5x."""
    w, h, gy = 112, 40, 4
    ps = tt.ParticleSystem(900)
    fx = tt.EffectsFactory(ps, SETTINGS, random.Random(seed))
    x0, y0, x1, y1 = 6.0, 9.0, 88.0, float(gy)
    k = 40.0

    def at(u):
        return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + k * u * (1 - u)
    explosions, t, n, dt = [], 0.0, 0, 1 / FPS
    flight = 1.2
    launches = (0.0, 0.6 * flight)                     # the second shell is on its way down while the first one detonates
    snap = flight + 0.18
    landed = False
    while t < snap:
        for t0 in launches:
            if t0 <= t < t0 + flight:
                x, y = at((t - t0) / flight)
                n += 1
                fx.trail(x, y, tt.live_color(shot, t), ammo, n, t)
        if t >= flight and not landed:
            landed = True
            explosions.append(tt.Explosion(x1, y1, 4.5, tt.live_color(shot, t), 0.8, ammo.boom))
            fx.impact(x1, y1, tt.live_color(shot, t), (92, 84, 70), 0.6, ammo)
        ps.update(dt)
        for e in explosions:
            e.update(dt)
        t += dt
    cv = range_sky(w, h, gy)
    u = (t - launches[1]) / flight
    x, y = at(u)
    x2, y2 = at(min(1.0, u + 0.02))
    ps.draw(cv)
    for e in explosions:
        if not e.done:
            e.draw(cv)
    tt.draw_projectile(cv, x, y, x2 - x + 1e-3, y2 - y, shot, ammo, t)
    return canvas_image(cv, 5)


def map_picture(m):
    cv = tt.render_map_preview({}, m, 150, 78, 1.5, [(tt.DEFAULT_DESIGN, CYAN), (tt.DEFAULT_DESIGN, ORANGE)])
    return canvas_image(cv, 5)


def theme_picture(key: str):
    """The home screen's backdrop exactly as the title screen draws it, on a 100 x 30 terminal, without the menu."""
    screen = tt.Screen(None, tt.ColorMode.TRUE)
    screen.resize(100, 30)
    if key in tt.HOME_THEMES:
        bd = tt.ThemeBackdrop(tt.HOME_THEMES[key])
    elif key == "MASTER":
        bd = tt.MasterBackdrop(SETTINGS)
    elif key == "SECRET":
        bd = tt.SecretBackdrop(SETTINGS)
    else:
        bd = tt.AmbientBackdrop()
    if hasattr(bd, "ensure"):
        bd.ensure(100, 30)
    t, dt = 0.0, 1 / FPS
    while t < 4.4:
        bd.update(dt)
        t += dt
    screen.clear()
    bd.draw(screen, t)
    return screen_image(screen)


def stage_frames(design, body, ammo, shot, w: int = 56, h: int = 26, scale: int = 6, mapdef=None):
    """One full PreviewStage loop (the shop / gift-scene range: the tank aims, fires and the shell lands)."""
    st = tt.PreviewStage(SETTINGS, w, h, 2)
    if mapdef is not None:
        st.set_map(mapdef)
    st.set_kit(design, body, ammo, shot, 0.0)
    dt = 1 / FPS
    for _ in range(int(st.PERIOD * FPS)):          # one warm-up loop so smoke and embers are already drifting
        st.update(dt)
    frames = []
    for _ in range(int(st.PERIOD * FPS)):
        st.update(dt)
        frames.append(canvas_image(st.render(), scale))
    return frames


def art_picture(fn, scale: int = 10, t: float = 1.2):
    return canvas_image(fn(t), scale)


# ---------------------------------------------------------------------------------------------------------------------------
def main() -> int:
    cat = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    man_path = SHOTS / "manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    anim = manifest.pop("@anim", {})
    todo, missing = [], []
    for e in cat:
        uid, k = e["u"], e["k"]
        if ONLY and k != ONLY:
            continue
        have = manifest.get(uid)
        broken = have and (not (SHOTS / have).exists() or Image.open(SHOTS / have).convert("L").getextrema()[1] < 24)   # e.g. all-black placeholders
        needs_anim = e.get("an") and uid not in anim
        if ALL or not have or broken or needs_anim:
            (missing if CHECK else todo).append(e)
    if CHECK:
        for e in missing:
            print("missing", e["u"])
        return 1 if missing else 0
    designs, ammos = tt.DESIGN_BY_KEY, tt.AMMO_BY_KEY
    maps = {m.key: m for m in list(tt.MAPS) + list(tt.SPECIAL_MAPS)}
    paint_rgb = dict(tt.ANIM_PAINTS)
    missions = {m.number: m for m in tt.MISSIONS}
    for i, e in enumerate(todo):
        uid, k, kid = e["u"], e["k"], e["u"].split(":", 1)[-1]
        print(f"{i + 1}/{len(todo)} {uid}", flush=True)
        if k == "tank":
            manifest[uid] = save_png(tank_picture(designs[kid]), f"tank-{kid}.png")
        elif k == "ammo":
            shot = (255, 226, 120) if kid == tt.BLESSING_KEY else YELLOW
            manifest[uid] = save_png(ammo_picture(ammos[kid], shot), f"ammo-{kid}.png")
            if kid == tt.BLESSING_KEY:                       # the Blessing is shown the way the game hands it over
                a = save_anim(stage_frames(designs["a_martyr"], tt.ASTRAL, ammos[kid], (255, 226, 120)), "ammo-blessing-gift")
                anim[uid] = a
        elif k == "map":
            manifest[uid] = save_png(map_picture(maps[kid]), f"map-{kid}.png")
        elif k == "theme":
            manifest[uid] = save_png(theme_picture(kid.upper()), f"theme-{kid}.png")
        elif k == "paint":
            name = "RGB" if uid.startswith("rgb:") else kid.upper()
            col = paint_rgb[name]
            if uid == "rgb:shell":
                fr = stage_frames(tt.DEFAULT_DESIGN, CYAN, tt.DEFAULT_AMMO, tt.RAINBOW)
            else:
                fr = stage_frames(tt.DEFAULT_DESIGN, col, tt.DEFAULT_AMMO, col)
            stem = "paint-" + (uid.replace(":", "-") if uid.startswith("rgb:") else kid)
            a = save_anim(fr, stem)
            manifest[uid], anim[uid] = a["poster"], a
        elif k == "boss":
            if uid in ("boss:ufo", "boss:mission50"):
                manifest[uid] = save_png(ufo_picture(uid == "boss:mission50"), f"boss-{uid.split(':')[1]}.png")
            else:
                d = designs[e["tk"]]
                col = tt.COLOR_BY_NAME.get(e.get("col", ""), tt.ASTRAL if e["tk"] == "a_martyr" else (d.paint or ORANGE))
                manifest[uid] = save_png(tank_picture(d, col, angle=130, x=21, facing=-1), f"boss-{uid.split(':')[1]}.png")
        elif k in ("feature", "workshop"):
            sv = tt.SaveData(None)
            if uid == "master_difficulty":
                manifest[uid] = save_png(theme_picture("MASTER"), "feature-master_difficulty.png")
            elif uid == "x:ticket":
                manifest[uid] = save_png(art_picture(lambda t: tt.ticket_art(sv, t)), "feature-ticket.png")
            elif uid == "x:timemachine":
                manifest[uid] = save_png(art_picture(lambda t: tt.martyr_art(sv, t)), "feature-timemachine.png")
            elif uid == "x:special":
                a = save_anim(stage_frames(designs["bulwark"], ORANGE, ammos["plasma"], YELLOW), "feature-special")
                manifest[uid], anim[uid] = a["poster"], a
            elif uid == "x:hover":
                rec = {"id": "hoverdemo", "name": "HOVER", "parts": {"turret": "dome", "hull": "plate", "track": "round", "barrel": "rail",
                                                                     "glow": "pulse", "ambient": "sparkle", "accent": "CYAN"}, "hover": True}
                d = tt.design_from_custom(rec)
                manifest[uid] = save_png(tank_picture(d, tt.COLOR_BY_NAME["PURPLE"]), "feature-hover.png")
            elif uid == "x:workshop":
                rec = {"id": "wsdemo", "name": "WORKSHOP", "parts": {"turret": "twin", "hull": "wide", "track": "tread", "barrel": "double",
                                                                     "glow": "blink", "ambient": "sparks", "accent": "YELLOW"}}
                manifest[uid] = save_png(tank_picture(tt.design_from_custom(rec), tt.COLOR_BY_NAME["GREEN"]), "feature-workshop.png")
            elif uid == "x:parts":
                manifest[uid] = save_png(parts_sheet(), "feature-parts.png")
    known = {e["u"] for e in cat}
    manifest = {k: v for k, v in sorted(manifest.items()) if k in known and (SHOTS / v).exists()}    # stale entries go
    anim = {k: v for k, v in anim.items() if k in known}
    manifest["@anim"] = dict(sorted(anim.items()))
    man_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"done: {len(todo)} pictures; manifest has {len(manifest) - 1} entries")
    return 0


def parts_sheet():
    """A strip of turrets on the range: a glimpse of the Workshop's parts bin."""
    w, h = 100, 28
    cv = range_sky(w, h)
    turrets = list(tt._TURRETS)[::max(1, len(tt._TURRETS) // 6)][:6]
    cols = ("CYAN", "ORANGE", "GREEN", "MAGENTA", "YELLOW", "BLUE")
    for i, tu in enumerate(turrets):
        d = tt.design_from_custom({"id": f"p{i}", "parts": {"turret": tu, "hull": list(tt._HULLS)[i * 3 % len(tt._HULLS)],
                                                            "track": list(tt._TRACKS)[i * 2 % len(tt._TRACKS)], "barrel": list(tt.BARRELS)[i * 4 % len(tt.BARRELS)],
                                                            "glow": "pulse", "ambient": "none", "accent": "WHITE"}})
        tt.draw_tank(cv, 8 + i * 16.5, 4, 1, 40, tt.COLOR_BY_NAME[cols[i]], scale=1, design=d, t=0.9)
    return canvas_image(cv, 6)


if __name__ == "__main__":
    sys.exit(main())
