#!/usr/bin/env python3
"""Records the DS page's hero clip from the real ROM: a single-player battle where a shot is fired from the touch screen,
every DS frame (60 a second) through the shot's flight and impact, saved as ds/ds-fire.webm / .mp4 / .png.

    python3 tools/ds/capture_clip.py ROM DSSHOT OUTDIR [--secs 7]

Uses the same emulator driver and screen checks as capture.py."""
import subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture import DS, title_logo, press_a, menu_list, boxed_screens, fire_ready


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
    with tempfile.TemporaryDirectory() as td:
        for i, im in enumerate(frames):
            im.save(f"{td}/f{i:04d}.png")
        src = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "60", "-i", f"{td}/f%04d.png", "-vf", "scale=512:768:flags=neighbor"]
        subprocess.run(src + ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30", "-row-mt", "1", "-pix_fmt", "yuv420p", str(out / "ds-fire.webm")], check=True)
        subprocess.run(src + ["-c:v", "libx264", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out / "ds-fire.mp4")], check=True)
        frames[0].save(out / "ds-fire.png", optimize=True)
    print(f"ds-fire: {len(frames)} frames ({len(frames) / 60:.1f} s at 60 fps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
