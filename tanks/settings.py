"""Player settings (difficulty, wind, effects, audio, home screen...), the rows of the SETTINGS screen, and the
optional terminal-bell feedback."""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from tanks.colors import ColorMode
from tanks.content.homes import HOME_ORDER


class Difficulty(Enum):
    EASY = "EASY"
    NORMAL = "NORMAL"
    HARD = "HARD"
    MASTER = "MASTER"


@dataclass
class Settings:
    difficulty: Difficulty = Difficulty.NORMAL
    anim_speed: float = 1.0
    effects: bool = True
    trail_life: float = 0.55
    particle_density: float = 1.0
    aim_guide: int = 1
    random_maps: bool = False
    color_mode: ColorMode = ColorMode.AUTO
    sound: bool = False
    wind: float = 6.0
    home_mode: str = "CLASSIC"
    audio: int = 2                        # 2 ON (music + effects), 1 BELL only, 0 OFF
    music_vol: float = 0.7
    sfx_vol: float = 0.9
    song_popup: bool = True               # the NOW PLAYING card when the music changes
    wind_min: float = 0.0                 # lower bound of |wind| (set from a match's WIND band; the global setting leaves it at 0)


SETTING_ROWS = (
    ("AI DIFFICULTY", "difficulty", (("EASY", Difficulty.EASY), ("NORMAL", Difficulty.NORMAL), ("HARD", Difficulty.HARD), ("MASTER", Difficulty.MASTER)),
     "How well the computer solves its firing problem"),
    ("WIND", "wind", (("OFF", 0.0), ("LIGHT", 3.0), ("NORMAL", 6.0), ("STRONG", 10.0)),
     "Shifts every turn - read the arrows before you fire"),
    ("ANIMATION SPEED", "anim_speed", (("SLOW", 0.7), ("NORMAL", 1.0), ("FAST", 1.6)),
     "Speed of shells, blasts and AI decisions"),
    ("SCREEN EFFECTS", "effects", (("OFF", False), ("ON", True)), "Screen shake and blast flashes"),
    ("PROJECTILE TRAILS", "trail_life", (("OFF", 0.0), ("SHORT", 0.55), ("LONG", 1.3)), "Length of the fading tracer"),
    ("PARTICLE DENSITY", "particle_density", (("LOW", 0.45), ("MEDIUM", 1.0), ("HIGH", 1.8)), "Sparks, debris and smoke"),
    ("AIM GUIDE", "aim_guide", (("OFF", 0), ("SHORT", 1), ("FULL", 2)), "Dotted NO-WIND preview - you add the wind"),
    ("MAP SELECTION", "random_maps", (("CHOOSE", False), ("RANDOM", True)), "Pick the opening battlefield or roll the dice"),
    ("COLOR MODE", "color_mode", (("AUTO", ColorMode.AUTO), ("24-BIT", ColorMode.TRUE), ("256", ColorMode.ANSI256), ("16", ColorMode.ANSI16)),
     "Force a palette if colours look wrong"),
    ("AUDIO", "audio", (("ON", 2), ("BELL ONLY", 1), ("OFF", 0)), "Music and sound effects (needs a sound device)"),
    ("MUSIC VOLUME", "music_vol", tuple((f"{i * 10}%", i / 10) for i in range(11)), "Soundtrack level"),
    ("SFX VOLUME", "sfx_vol", tuple((f"{i * 10}%", i / 10) for i in range(11)), "Explosions, shots and menu clicks"),
    ("SONG POPUP", "song_popup", (("ON", True), ("OFF", False)), "A NOW PLAYING card slides in when the music changes"),
    ("HOME SCREEN", "home_mode", tuple((k, k) for k in HOME_ORDER), "Pick any home screen you own"),
)


class Feedback:
    """Audio-ish feedback: optional terminal bell, kept behind one small interface."""

    def __init__(self, term, settings: Settings) -> None:
        self.term, self.settings, self._last = term, settings, 0.0

    def emit(self, kind: str) -> None:
        if getattr(self.settings, "audio", 2) == 1 and kind in ("explosion", "destroy"):
            now = time.monotonic()
            if now - self._last > 0.15:
                self._last = now
                self.term.write("\a")
