#!/usr/bin/env python3
"""Records the DS page's hero clip from the real ROM: a single-player battle where a shot is fired from the touch screen,
through the shot's flight and impact, saved as ds/ds-fire.webm / .mp4 / .png.

The game draws 30 new pictures a second, so the clip keeps those (no motion lost) at 30 fps. It is laid out for the
drawn DS on the page: top screen, a GAP-pixel band (the distance between the two screens on a real DS Lite, in screen
pixels), then the touch screen. The page shows it through two screen-shaped windows, so one video drives both screens.

    python3 tools/ds/capture_clip.py ROM DSSHOT OUTDIR [--secs 7]

Uses the same emulator driver and screen checks as capture.py."""
import subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture import DS, title_logo, press_a, menu_list, boxed_screens, fire_ready
from PIL import Image, ImageChops

GAP = 114          # 20.4 mm between the screens of a DS Lite, at 256 px per 61 mm screen width


def main() -> int:
    rom, binary, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    secs = float(sys.argv[sys.argv.index("--secs") + 1]) if "--secs" in sys.argv else 7.0
    for attempt in range(6):
        ds = DS(rom, binary)
        try:
            ds.run(300); ds.wait_for(title_logo); ds.wait_for(press_a)
            ds.press("A", after=10); ds.wait_for(menu_list, step=10)
            ds.press("A", after=10); ds.run(120); ds.wait_for(boxed_screens)
            ds.press("A", after=150); ds.press("UP", after=20); ds.press("A", after=60)
            ready = None
            for _ in range(6):
                try:
                    ready = ds.wait_for(fire_ready, step=30, limit=600); break
                except RuntimeError:
                    ds.press("A", after=30)
            if ready is None:
                raise RuntimeError("the battle did not start")
        except RuntimeError as e:
            print(f"  attempt {attempt + 1}: {e}; trying again"); ds.close(); continue
        frames = []
        def grab(n):
            for _ in range(n):
                ds.run(1); frames.append(ds.image())
        grab(30)                                                           # a moment of aiming first
        for _ in range(3):                                                 # a little more power, pressed on camera
            ds.cmd("press UP"); grab(6); ds.cmd("release UP"); grab(4)
        ds.cmd("touch 198 73"); grab(12); ds.cmd("untouch")               # FIRE, with the stylus
        grab(int(secs * 60) - len(frames))
        ds.close()
        break
    else:
        print("could not reach a battle"); return 1
    # keep every other frame, on whichever phase carries the game's new pictures
    diff = lambda a, b: ImageChops.difference(a, b).getbbox() is not None
    phase = max((0, 1), key=lambda p: sum(diff(frames[i], frames[i - 1]) for i in range(p + 2, len(frames), 2)))
    frames = frames[phase::2]
    def layout(im):
        out = Image.new("RGB", (256, 192 * 2 + GAP), (0, 0, 0))
        out.paste(im.crop((0, 0, 256, 192)), (0, 0)); out.paste(im.crop((0, 192, 256, 384)), (0, 192 + GAP))
        return out
    frames = [layout(im) for im in frames]
    with tempfile.TemporaryDirectory() as td:
        for i, im in enumerate(frames):
            im.save(f"{td}/f{i:04d}.png")
        w, h = 512, (192 * 2 + GAP) * 2
        src = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-i", f"{td}/f%04d.png", "-vf", f"scale={w}:{h}:flags=neighbor"]
        subprocess.run(src + ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-row-mt", "1", "-pix_fmt", "yuv420p", str(out / "ds-fire.webm")], check=True)
        subprocess.run(src + ["-c:v", "libx264", "-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out / "ds-fire.mp4")], check=True)
        frames[0].resize((w, h), Image.NEAREST).save(out / "ds-fire.png", optimize=True)
    print(f"ds-fire: {len(frames)} frames ({len(frames) / 30:.1f} s at 30 fps), {512} x {(192 * 2 + GAP) * 2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
