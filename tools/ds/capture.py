#!/usr/bin/env python3
"""Takes real screenshots of Terminal Tanks DS by playing the actual ROM in a headless DS emulator.

    python3 tools/ds/capture.py ROM DSSHOT OUTDIR

DSSHOT is tools/ds/dsshot.cpp compiled against the NooDS core (see that file for the one-line build). The script drives the
emulator interactively: it waits until the screen shows what it expects (the title logo, the touch-screen FIRE button...)
before pressing anything, because the game's timing changes from run to run (it seeds from the DS clock). Pictures are
256 x 384: the DS's two screens, top above bottom, exactly as the hardware draws them."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


class DS:
    def __init__(self, rom: str, binary: str) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.p = subprocess.Popen([str(Path(binary).resolve()), str(Path(rom).resolve()), "-", self.tmp.name],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.frame = 0
        self.n = 0

    def cmd(self, line: str) -> None:
        self.p.stdin.write(line + "\n"); self.p.stdin.flush()
        self.frame = int(self.p.stdout.readline().split()[1])

    def run(self, n: int) -> None:
        self.cmd(f"run {n}")

    def press(self, key: str, after: int = 30, hold: int = 6) -> None:
        self.cmd(f"press {key}"); self.run(hold); self.cmd(f"release {key}"); self.run(after)

    def tap(self, x: int, y: int, after: int = 30, hold: int = 12) -> None:
        self.cmd(f"touch {x} {y}"); self.run(hold); self.cmd("untouch"); self.run(after)

    def image(self) -> Image.Image:
        self.n += 1
        name = f"cap{self.n}"
        self.cmd(f"shot {name}")
        return Image.open(Path(self.tmp.name) / f"{name}.ppm").convert("RGB")

    def wait_for(self, test, step: int = 20, limit: int = 3000) -> Image.Image:
        for _ in range(limit // step):
            im = self.image()
            if test(im):
                return im
            self.run(step)
        raise RuntimeError(f"timed out at frame {self.frame}")

    def close(self) -> None:
        try:
            self.cmd("quit")
        except Exception:
            pass
        self.p.wait(timeout=10)
        self.tmp.cleanup()


def count(im: Image.Image, box, fn) -> int:
    return sum(1 for px in im.crop(box).get_flattened_data() if fn(px)) if hasattr(im, 'get_flattened_data') else sum(1 for px in im.crop(box).getdata() if fn(px))


# what the screens look like at each step (coordinates are in the 256 x 384 two-screen picture)
def title_logo(im):            # the cyan TERMINAL TANKS logo on the top screen, and no boot text
    return count(im, (20, 25, 236, 110), lambda p: p[1] > 190 and p[2] > 190 and p[0] < 170) > 1500
def press_a(im):               # "[ PRESS A ]" is drawn under the logo once the title is ready
    return count(im, (90, 250, 170, 268), lambda p: p[0] > 200 and p[1] > 200 and p[2] > 200) > 20
def menu_list(im):             # the bright, selected SINGLE PLAYER row of the main menu
    return count(im, (60, 205, 200, 218), lambda p: p[0] > 220 and p[1] > 220 and p[2] > 220) > 30
def boxed_screens(im):         # rules / setup screens: the double-line frame on both screens
    return count(im, (0, 0, 256, 6), lambda p: p[2] > 120 and p[1] > 90 and p[0] < 120) > 60
def fire_ready(im):            # the red FIRE button on the touch screen is lit when it is your turn to aim
    return count(im, (152, 219 + 0, 244, 312), lambda p: p[0] > 180 and p[1] < 90 and p[2] < 90) > 150


def make_clip(frames, stem: Path) -> None:
    """A short looping clip (WebM, MP4 and GIF) of real frames, shown 2x with crisp pixels."""
    import shutil
    if not shutil.which("ffmpeg"):
        return
    with tempfile.TemporaryDirectory() as td:
        for i, im in enumerate(frames):
            im.save(f"{td}/f{i:04d}.png")
        src = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-i", f"{td}/f%04d.png", "-vf", "scale=512:768:flags=neighbor"]
        subprocess.run(src[:-2] + ["-vf", "scale=512:768:flags=neighbor", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30", "-pix_fmt", "yuv420p", f"{stem}.webm"], check=True)
        subprocess.run(src + ["-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", f"{stem}.mp4"], check=True)
        frames[0].save(f"{stem}.png", optimize=True)


def main() -> int:
    rom, binary, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    save = lambda im, name: (im.save(out / f"{name}.png", optimize=True), print("captured", name))

    # 1. boot, title, menu, rules, pilot setup, a single-player battle (fired from the touch screen). The battlefield is random,
    #    and now and then the emulator stalls while one is generated, so a run that never reaches the battle is simply retried.
    for attempt in range(6):
        ds = DS(rom, binary)
        try:
            boot = ds.wait_for(lambda im: count(im, (0, 0, 256, 30), lambda p: p[1] > 150) > 200, step=10)
            ds.run(300)
            ds.wait_for(title_logo)
            title = ds.wait_for(press_a)
            ds.press("A", after=10)
            menu = ds.wait_for(menu_list, step=10)
            ds.press("A", after=10)
            ds.run(120); rules = ds.wait_for(boxed_screens)
            ds.press("A", after=150); setup = ds.image()
            ds.press("UP", after=20); ds.press("A", after=60)
            im = None
            for _ in range(6):                           # past the pilot setup and the round banner, until FIRE lights up
                try:
                    im = ds.wait_for(fire_ready, step=30, limit=600)
                    break
                except RuntimeError:
                    ds.press("A", after=30)
            if im is None:
                raise RuntimeError("the battle did not start")
        except RuntimeError as e:
            print(f"  attempt {attempt + 1}: {e}; trying again")
            ds.close()
            continue
        for im_, nm in ((boot, "ds-boot"), (title, "ds-title"), (menu, "ds-menu"), (rules, "ds-rules"), (setup, "ds-setup")):
            save(im_, nm)
        ds.run(40)
        save(ds.image(), "ds-battle")
        ds.press("UP", after=4); ds.press("UP", after=4); ds.press("UP", after=4)      # a little more power
        ds.tap(198, 73, after=12)                                                      # FIRE, with the stylus (touch-screen coordinates)
        if fire_ready(ds.image()):                                                    # still aiming: fire with the A button instead
            print("  (the tap did not fire; using A)")
            ds.press("A", after=12)
        clip = []
        for i in range(90):                                                           # the shot in flight, every 2nd frame
            ds.run(2); clip.append(ds.image())
        for i, k in enumerate((8, 20, 34, 50, 70, 89)):
            save(clip[k], f"ds-shot{i}")
        make_clip(clip, out / "ds-fire")
        for i in range(6):
            ds.run(150); save(ds.image(), f"ds-turn{i}")
        ds.close()
        break

    # 2. menu screens: shop, tournament, how to play, links
    for name, downs in (("ds-tournament", 3), ("ds-shop", 5), ("ds-howto", 7), ("ds-links", 12)):
        ds = DS(rom, binary)
        ds.run(300); ds.wait_for(title_logo); ds.wait_for(press_a)
        ds.press("A", after=10); ds.wait_for(menu_list, step=10); ds.run(30)
        for _ in range(downs):
            ds.press("DOWN", after=36, hold=8)
        ds.run(30); ds.press("A", after=220, hold=8)
        save(ds.image(), name)
        if name == "ds-shop":
            ds.press("R", after=60); save(ds.image(), "ds-shop2")
            ds.press("R", after=60); save(ds.image(), "ds-shop3")
        ds.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
