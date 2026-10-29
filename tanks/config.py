"""Fixed numbers the whole game shares: frame rate, minimum terminal size, field limits, tank geometry and the
shell physics."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


GAME_DIR = Path(__file__).resolve().parent.parent      # the folder that holds terminaltanks.py and tanks/

IS_WEB = sys.platform in ("emscripten", "wasi")      # running in a browser (Pyodide): see tanks/web.py

FPS = 30
MIN_SIZE = (96, 28)
RECOMMENDED_SIZE = (100, 30)
MAX_FIELD_COLS = 180
MAX_FIELD_ROWS = 40
HUD_TOP_ROWS = 3
HUD_BOTTOM_ROWS = 3
MAX_HP = 3
ROUNDS_TO_WIN = 2
GLASS_HP = 2                           # Glass Cannon levels: your tank has only this many hearts
BOSS_MAX_WINS = 3                      # a Tournament level is lost when the boss wins this many rounds (earlier boss wins are strikes)
LAN_PORT, BEACON_PORT = 47474, 47475   # LAN: TCP game port and UDP discovery port
FINAL_BOSSES = 3                       # the last three Tournament levels are the "big bosses" (Master AI, richer rewards)

PAIR_CACHE_MAX = 6000                  # cap for the screen's colour-escape cache (see Screen.flush)

TANK_W, TANK_H = 11, 6
PIVOT_H = 4.5
BARREL_LEN = 7.5
COARSE_STEP = 5


@dataclass(frozen=True)
class PhysicsConfig:
    gravity: float = 32.0          # px / s^2
    range_factor: float = 1.16     # full-power 45deg shot covers this many field widths
    power_curve: float = 1.0       # speed = max_speed * (power/100) ** curve
    min_power: float = 10.0
    max_power: float = 100.0
    projectile_radius: float = 0.9
    substep: float = 0.6           # max px travelled between collision probes
    blast_radius: float = 5.5
    splash_reach: float = 2.5
    fall_speed: float = 45.0


PHYS = PhysicsConfig()
