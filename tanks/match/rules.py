"""Match rules for Two Player and LAN: rounds, health, wind, maps, Blessing and special ammo."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tanks.colors import clamp
from tanks.content.maps import MapDefinition, all_maps
from tanks.settings import Settings


ROUND_PRESETS = (3, 5, 7, 10, 0)          # 0 = custom
HP_PRESETS = (1, 3, 5, 7, 10, 0)


WIND_MODES = (("OFF", (0.0, 0.0)), ("REGULAR", (0.0, 6.0)), ("LOW", (0.0, 2.0)), ("MEDIUM", (2.0, 4.0)),
              ("HIGH", (4.0, 6.0)), ("CRAZY", (6.0, 12.0)))       # per-match WIND bands: (min, max) strength


@dataclass
class Rules:
    """Two Player / LAN match rules: BEST OF or FIRST TO n rounds, hearts, the battlefield, wind and the special attack."""
    fmt: str = "best"                     # "best" | "first"
    n_idx: int = 0
    n_custom: int = 4
    hp_idx: int = 1
    hp_custom: int = 4
    map_key: str = ""                     # "" = random battlefield
    wind: int = 1                         # index into WIND_MODES (0 OFF, 1 REGULAR, 2 LOW, 3 MEDIUM, 4 HIGH, 5 CRAZY)
    special: bool = False
    ammo_fx: bool = True                  # special ammo effects ON/OFF
    pick_maps: bool = True                # choose the battlefield every round (loser picks) instead of a random one
    blessing: bool = False                # MARTYR'S BLESSING allowed in this mode (independent of `ammo_fx`; needs the unlock)

    @property
    def n(self) -> int:
        return ROUND_PRESETS[self.n_idx] or self.n_custom

    @property
    def hp(self) -> int:
        return HP_PRESETS[self.hp_idx] or self.hp_custom

    @property
    def target(self) -> int:
        """Rounds one side must win. Best of n: more than half (best of 10 = first to 6, so a tie can never survive)."""
        return self.n // 2 + 1 if self.fmt == "best" else self.n

    @property
    def label(self) -> str:
        return f"{'BEST OF' if self.fmt == 'best' else 'FIRST TO'} {self.n}"

    @property
    def mapdef(self) -> Optional[MapDefinition]:
        return all_maps().get(self.map_key)

    def wind_value(self, settings: "Settings") -> tuple:
        """(min, max) wind strength for this match, from its WIND band."""
        return WIND_MODES[int(clamp(self.wind, 0, len(WIND_MODES) - 1))][1]

    def summary(self) -> str:
        m = self.mapdef.name if self.mapdef else "RANDOM MAP"
        return f"{self.label} · {self.hp} HP · {m} · WIND {WIND_MODES[self.wind][0]}" + (" · SPECIAL" if self.special else "") + ("" if self.ammo_fx else " · AMMO FX OFF") + (" · BLESSING" if self.blessing else "")

    def dump(self) -> str:
        return f"{self.fmt},{self.n_idx},{self.n_custom},{self.hp_idx},{self.hp_custom},{self.map_key},{int(self.wind)},{int(self.special)},{int(self.ammo_fx)},{int(self.pick_maps)},{int(self.blessing)}"

    @classmethod
    def load(cls, text: str) -> "Rules":
        try:
            parts = text.split(",")
            f, a, b, c, d = parts[:5]                         # older saves only had the first five fields
            r = cls(f if f in ("best", "first") else "best", int(a), int(b), int(c), int(d))
            if len(parts) >= 8:
                r.map_key, r.special = parts[5], parts[7] == "1"
                r.wind = int(parts[6]) if parts[6].isdigit() and int(parts[6]) < len(WIND_MODES) else 1    # old saves: "1" = REGULAR, "0" = OFF
            if len(parts) >= 9:
                r.ammo_fx = parts[8] == "1"
            if len(parts) >= 10:
                r.pick_maps = parts[9] == "1"
            if len(parts) >= 11:
                r.blessing = parts[10] == "1"
            if not (0 <= r.n_idx < len(ROUND_PRESETS) and 0 <= r.hp_idx < len(HP_PRESETS)):
                raise ValueError
            r.n_custom, r.hp_custom = int(clamp(r.n_custom, 1, 25)), int(clamp(r.hp_custom, 1, 50))
            if r.map_key and r.map_key not in all_maps():
                r.map_key = ""
            return r
        except ValueError:
            return cls()
