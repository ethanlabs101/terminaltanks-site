"""The Application: the scene stack with fades, the frame loop, music and sound routing, the wallet chime and the
NOW PLAYING card. Also the command line (parse_cli) and main()."""
from __future__ import annotations

import argparse
import random
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from tanks import CREDIT_NAME, CREDIT_URL, __version__
from tanks.art.backdrops import AmbientBackdrop, MasterBackdrop, SecretBackdrop, ThemeBackdrop
from tanks.audio.clients import NullAudio, make_audio
from tanks.audio.director import HOME_SONG
from tanks.audio.export import export_music
from tanks.audio.output import audio_server
from tanks.colors import ColorMode, Palette, clamp
from tanks.config import FPS, MIN_SIZE, RECOMMENDED_SIZE
from tanks.content.homes import HOME_ORDER, HOME_THEMES
from tanks.content.maps import MapDefinition
from tanks.content.paints import COLOR_BY_NAME, color_index
from tanks.content.songs import SONGS
from tanks.content.tournament import TournamentLevel
from tanks.match.sessions import MatchConfig, MatchSession, PlayerSetup, TournamentSession, boss_setup
from tanks.profiles import ProfileBook
from tanks.save import SaveData, default_save_path
from tanks.scenes.base import Scene
from tanks.scenes.battle import BattleScene
from tanks.scenes.jukebox import JukeboxScene
from tanks.scenes.main_menu import MenuScene
from tanks.scenes.rps import RPSScene
from tanks.scenes.story import CinematicScene, whisper
from tanks.scenes.title import BootScene
from tanks.screen import Screen
from tanks.settings import Feedback, Settings
from tanks.terminal import Action, InputEvent, InputManager, TerminalError, TerminalIO
from tanks.ui.hud import Phase
from tanks.ui.now_playing import NowPlaying
from tanks.ui.widgets import draw_wallet


@dataclass
class Transition:
    scene: Scene
    phase: str = "out"
    t: float = 0.0
    OUT = 0.22
    IN = 0.30

    @property
    def progress(self) -> float:
        return clamp(self.t / (self.OUT if self.phase == "out" else self.IN), 0, 1)


class Application:
    def __init__(self, term, seed: Optional[int] = None, color_mode: ColorMode = ColorMode.AUTO,
                 save_path: Optional[Path] = None) -> None:
        self.term = term
        self.input = InputManager(term)
        self.profiles = ProfileBook(save_path)
        self.save = SaveData.load(self.profiles.active_path() if save_path is not None else None)
        self.settings = Settings()
        self.save.apply_settings(self.settings)
        if color_mode is not ColorMode.AUTO:
            self.settings.color_mode = color_mode
        self.screen = Screen(term, self.settings.color_mode)
        self.feedback = Feedback(term, self.settings)
        self.audio = make_audio(term, self.settings)
        self.now_playing = NowPlaying()
        self._sync_audio()
        self.last_battle_song: Optional[str] = None
        self._sfx_t: dict = {}
        self._wallet_seen = (self.save.coins, len(self.save.granted))
        self.backdrop = AmbientBackdrop()
        self.master_backdrop = MasterBackdrop(self.settings)
        self.secret_backdrop = SecretBackdrop(self.settings)
        self.theme_backdrops: dict = {}
        self.rng = random.Random(seed)
        self.stack: list[Scene] = []
        self.transition: Optional[Transition] = None
        self.time = 0.0
        self.running = True

    # -- scene management ----------------------------------------------------
    def _swap(self, scene: Scene) -> None:
        for s in self.stack:
            s.exit()
        self.stack = [scene]
        scene.enter()

    def goto(self, scene: Scene, fade: bool = True) -> None:
        if not self.stack or not fade:
            self._swap(scene)
        elif self.transition is None:
            self.transition = Transition(scene)

    def push(self, scene: Scene) -> None:
        self.stack.append(scene)
        scene.enter()

    def pop(self) -> None:
        if len(self.stack) > 1:
            self.stack.pop().exit()

    def start_match(self, cfg: MatchConfig, mapdef: Optional[MapDefinition], wind: Optional[float] = None, rps: bool = True) -> None:
        session = MatchSession(cfg, mapdef, self.rng.randrange(1 << 30))
        session.wind_override = wind
        if rps and cfg.mode in ("two", "single") and cfg.net is None:      # who shoots first is decided by rock-paper-scissors
            self.goto(RPSScene(self, session))
        else:
            self.goto(BattleScene(self, session))

    def start_tournament(self, level: TournamentLevel, cfg: Optional[MatchConfig] = None) -> None:
        if cfg is None:
            lo = self.save.loadout(0)
            me = PlayerSetup("PLAYER", "YOU", COLOR_BY_NAME[lo.tank_color], COLOR_BY_NAME[lo.shot_color], False, lo.tank, lo.ammo,
                             level.player_hp)
            cfg = MatchConfig([me, boss_setup(level, color_index(lo.tank_color))], True, level.difficulty, "tournament", level.precision, ammo_fx=False)
        go = lambda: self.goto(BattleScene(self, TournamentSession(level, cfg, self.rng.randrange(1 << 30))))
        if level.number == 1:
            whisper(self, "first_battle", go)
        else:
            go()

    def home_theme(self) -> str:
        mode = self.settings.home_mode
        return mode if mode in self.save.home_modes() else "CLASSIC"

    def home_backdrop(self):
        mode = self.home_theme()
        if mode in HOME_THEMES:
            if mode not in self.theme_backdrops:
                self.theme_backdrops[mode] = ThemeBackdrop(HOME_THEMES[mode])
            return self.theme_backdrops[mode]
        return {"MASTER": self.master_backdrop, "SECRET": self.secret_backdrop}.get(mode, self.backdrop)

    def switch_profile(self, pid: str) -> None:
        """Save the current profile, load another into the same running game, return to the main menu."""
        self.save.flush()
        path = self.profiles.path_of(pid)
        if path is None:
            return
        self.profiles.active = pid
        self.profiles.write()
        self.save = SaveData.load(path)
        self.settings = Settings() if False else self.settings
        self.save.apply_settings(self.settings)
        self.screen.set_mode(self.settings.color_mode)
        self.goto(MenuScene(self))

    def profiles_delete(self, pid: str) -> None:
        was_active = self.profiles.active == pid
        if self.profiles.delete(pid) and was_active:
            self.save = SaveData.load(self.profiles.active_path())
            self.save.apply_settings(self.settings)

    def _sync_audio(self) -> None:
        """Start/stop the engine to match the AUDIO setting and push the volumes and EQ."""
        want = getattr(self.settings, "audio", 2) == 2
        if want and not self.audio.on:
            self.audio = make_audio(self.term, self.settings)
        elif not want and self.audio.on:
            self.audio.stop()
            self.audio = NullAudio()
        self.audio.volumes(0.9, self.settings.music_vol, self.settings.sfx_vol)
        try:
            self.audio.eq(*[float(x) for x in self.save.settings.get("eq", "0,0,0").split(",")][:3])
        except (ValueError, TypeError):
            pass
        if hasattr(self.audio, "_music"):
            self.audio._music = None                         # re-send the current song after a restart

    def sfx(self, name: str, vol: float = 1.0, pan: float = 0.0, rate: float = 1.0, gap: float = 0.0) -> None:
        """Play a sound effect (optionally at most once per `gap` seconds)."""
        if gap:
            last = self._sfx_t.get(name, -9.0)
            if self.time - last < gap:
                return
            self._sfx_t[name] = self.time
        self.audio.sfx(name, vol, pan, rate)

    def _direct_music(self) -> None:
        """Pick the song for whatever is on screen (top-most scene that has an opinion, else the home screen's song)."""
        sid, mood = None, None
        for s in reversed(self.stack):
            f = getattr(s, "music", None)
            r = f() if f else None
            if r:
                sid, mood = r
                break
        if sid is None:
            sid, mood = HOME_SONG.get(self.home_theme(), "main_theme"), "menu"
        if sid not in SONGS:
            sid = "main_theme"
        if mood in ("battle",):
            self.last_battle_song = sid
        if sid != getattr(self, "_np_last", None):
            self._np_last = sid
            top = self.stack[-1] if self.stack else None
            if self.audio.on and self.settings.song_popup and not isinstance(top, JukeboxScene):
                self.now_playing.show(sid)
        self.audio.music(sid)
        self.audio.mood(mood or "menu")
        top = self.stack[-1] if self.stack else None
        pkey = (type(top).__name__, self.home_theme())
        if pkey != getattr(self, "_prefetch_key", None):           # warm up what is likely to play next
            self._prefetch_key = pkey
            owned = [k for k in HOME_ORDER if k in self.save.home_modes()]
            cur = self.home_theme()
            want = ["shop_jingle", "workshop"]
            if cur in owned and len(owned) > 1:
                i = owned.index(cur)
                want += [HOME_SONG.get(owned[(i + 1) % len(owned)]), HOME_SONG.get(owned[i - 1])]
            want += list(getattr(top, "prefetch_songs", lambda: [])())
            self.audio.prep(["song:" + s for s in want if s in SONGS and s != sid])
        heard = self.save.settings.get("heard", "")
        if ("," + sid + ",") not in ("," + heard + ","):
            self.save.settings["heard"] = (heard + "," + sid).strip(",")

    def _ui_sound(self, ev: InputEvent) -> None:
        top = self.stack[-1] if self.stack else None
        if isinstance(top, BattleScene):
            if top.phase is Phase.AIMING and top._control(top.current) == "local":
                if ev.action in (Action.LEFT, Action.RIGHT):
                    self.sfx("aim_tick", 0.6, gap=0.035)
                elif ev.action in (Action.UP, Action.DOWN):
                    self.sfx("power_tick", 0.6, gap=0.035)
            return
        if isinstance(top, CinematicScene):
            return
        if ev.action in (Action.UP, Action.DOWN):
            self.sfx("ui_move", 0.7, gap=0.03)
        elif ev.action in (Action.LEFT, Action.RIGHT):
            self.sfx("ui_tab", 0.7, gap=0.03)
        elif ev.action in (Action.CONFIRM, Action.FIRE):
            self.sfx("ui_select", 0.8, gap=0.05)
        elif ev.action is Action.BACK:
            self.sfx("ui_back", 0.8, gap=0.05)
        elif len(ev.raw) == 1 and ev.raw.isalnum():
            self.sfx("ui_type", 0.5, gap=0.02)

    def apply_settings(self) -> None:
        self._sync_audio()
        self.screen.set_mode(self.settings.color_mode)
        self.save.capture_settings(self.settings)
        self.save.flush()

    # -- frame ---------------------------------------------------------------
    def step(self, dt: float) -> None:
        screen = self.screen
        cols, rows = self.term.size()
        if (cols, rows) != (screen.cols, screen.rows):
            screen.resize(cols, rows)
        if getattr(self.term, "redraw_requested", False):
            screen.force_redraw()
            self.term.redraw_requested = False
        events = self.input.poll()
        self.time += dt
        self.save.playtime += min(dt, 0.5)                       # playtime counter (capped so a stalled frame never inflates it)
        self._pt_flush = getattr(self, "_pt_flush", 0.0) + dt
        if self._pt_flush >= 60.0:
            self._pt_flush = 0.0
            self.save.flush()
        screen.clear()
        if cols < MIN_SIZE[0] or rows < MIN_SIZE[1]:
            self._draw_too_small(cols, rows)
            screen.flush()
            return
        tr = self.transition
        if tr:
            tr.t += dt
            if tr.phase == "out" and tr.progress >= 1:
                self._swap(tr.scene)
                tr.phase, tr.t = "in", 0.0
            elif tr.phase == "in" and tr.progress >= 1:
                self.transition = tr = None
        elif events:
            for ev in events:
                if self.transition is not None:
                    break
                self._ui_sound(ev)
                self.stack[-1].handle(ev)
        if self.stack:
            coins, got = self.save.coins, len(self.save.granted)        # wallet / unlock chimes
            if coins < self._wallet_seen[0]:
                self.sfx("ui_buy", 0.9, gap=0.3)
            elif coins > self._wallet_seen[0] + 0:
                self.sfx("payout", 0.8, gap=0.6)
            if got > self._wallet_seen[1]:
                self.sfx("ui_unlock", 0.9, gap=0.8)
            self._wallet_seen = (coins, got)
            self._direct_music()
            self.audio.tick()
            self.stack[-1].update(dt)
            for s in self.stack[:-1]:
                if s.ambient:
                    s.update_ambient(dt)
            base = len(self.stack) - 1
            while base > 0 and self.stack[base].overlay:
                base -= 1
            for s in self.stack[base:]:
                s.draw(screen)
            if self.stack[base].show_wallet and not (tr and tr.phase == "out" and tr.progress > 0.9):
                self._wallet_flash = max(0.0, getattr(self, "_wallet_flash", 0.0) - dt)
                draw_wallet(screen, self.save, self._wallet_flash)
            lay = getattr(self.stack[-1], "layout", None)
            ny = (lay.fy + 1) if lay is not None and hasattr(lay, "fy") else 1
            if getattr(self.stack[-1], "coach", False):                # tutorial coach box open: the card sits under it
                ny += getattr(self.stack[-1], "coach_h", 0) + 1
            self.now_playing.draw(screen, dt, getattr(self.audio, "spec", ""), self.time, ny)
        tr = self.transition
        if tr:
            p = tr.progress
            if tr.phase == "out":
                fac = [clamp(1 - (p * 1.6 - r / rows * 0.6), 0, 1) for r in range(rows)]
            else:
                fac = [clamp(p * 1.6 - r / rows * 0.6, 0, 1) for r in range(rows)]
            screen.fade_rows(fac)
        screen.flush()

    def _draw_too_small(self, cols: int, rows: int) -> None:
        s = self.screen
        lines = ["TerminalTanks requires a larger terminal window.", "",
                 f"Current: {cols}x{rows}", f"Recommended: {RECOMMENDED_SIZE[0]}x{RECOMMENDED_SIZE[1]}"]
        y = max(0, rows // 2 - 2)
        for i, line in enumerate(lines):
            s.center(y + i, line[:cols], Palette.AMBER if i == 0 else Palette.TEXT if i else Palette.TEXT)

    def frames(self):
        """Yields once per rendered frame. run() paces it with sleep(); the web backend lets the browser pace it."""
        self._swap(BootScene(self))
        last = time.perf_counter()
        while self.running:
            start = time.perf_counter()
            dt = min(start - last, 0.1)
            last = start
            self.step(dt)
            yield

    def run(self) -> None:
        frame = 1.0 / FPS
        began = time.perf_counter()
        for _ in self.frames():
            spare = frame - (time.perf_counter() - began)
            if spare > 0:
                time.sleep(spare)
            began = time.perf_counter()


def parse_cli(argv: Optional[Sequence[str]]):
    parser = argparse.ArgumentParser(prog="terminaltanks", description="Turn-based tank artillery for the terminal.",
                                     epilog=f"Created by {CREDIT_NAME} - https://{CREDIT_URL}")
    parser.add_argument("--color", choices=("auto", "truecolor", "256", "16"), default="auto", help="force a colour mode")
    parser.add_argument("--seed", type=int, default=None, help="seed maps and AI for reproducible matches")
    parser.add_argument("--save-file", default=None, help="progress file (default: per-user config directory)")
    parser.add_argument("--reset-progress", action="store_true", help="delete saved tournament progress and unlocks, then exit")
    parser.add_argument("--export-music", metavar="DIR", default=None, help="render the whole soundtrack and every sound effect to WAV files, then exit")
    parser.add_argument("--only", metavar="TEXT", default="", help="with --export-music: only songs whose id, name or group contains TEXT "
                                                                   "(e.g. martyr, t_, boss, map_, home_)")
    parser.add_argument("--audio-server", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=f"TerminalTanks {__version__} by {CREDIT_NAME} (https://{CREDIT_URL})")
    args = parser.parse_args(argv)
    mode = {"auto": ColorMode.AUTO, "truecolor": ColorMode.TRUE, "256": ColorMode.ANSI256, "16": ColorMode.ANSI16}[args.color]
    save_path = Path(args.save_file).expanduser() if args.save_file else default_save_path()
    return args, mode, save_path


def reset_progress(save_path: Path) -> int:
    try:
        save_path.unlink()
        print(f"Progress reset ({save_path}).")
    except FileNotFoundError:
        print("No saved progress found.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, mode, save_path = parse_cli(argv)
    if args.audio_server:
        return audio_server()
    if args.export_music:
        return export_music(args.export_music, args.only)
    if args.reset_progress:
        return reset_progress(save_path)
    app = None
    try:
        with TerminalIO() as term:
            app = Application(term, args.seed, mode, save_path)
            app.run()
    except KeyboardInterrupt:
        pass
    except TerminalError as exc:
        print(exc, file=sys.stderr)
        return 1
    except Exception:
        traceback.print_exc()
        print("\nTerminalTanks crashed; your terminal has been restored.", file=sys.stderr)
        return 1
    finally:
        if app is not None:
            app.audio.stop()
    return 0
