"""Computer opponents for Single Player: the CPU's kit and the special ammo it may draw."""
from __future__ import annotations

import random
from typing import Optional

from tanks.content.ammo import AMMO_BY_KEY, ANCIENT_AMMOS, BLESSING_KEY, DEFAULT_AMMO, SECRET_AMMOS, TICKET_AMMOS
from tanks.content.paints import COLOR_BY_NAME, COLOR_CHOICES, color_index
from tanks.content.tanks import BASE_KITS, DESIGNS
from tanks.content.tournament import TOURNAMENT
from tanks.match.sessions import PlayerSetup
from tanks.save import SaveData
from tanks.settings import Difficulty


def is_special_ammo(key: str) -> bool:
    """'Special' = an ammo with real effects (the ✦ ones). Cosmetic-only ammo counts as regular."""
    a = AMMO_BY_KEY.get(key)
    return bool(a is not None and a.mechanics)


def cpu_ammo_pool(save: SaveData, player_ammo: str, ammo_fx: bool) -> Optional[list]:
    """Single Player: the CPU mirrors you. You on a special ammo (with SPECIAL AMMO on) -> it always draws a special ammo;
    otherwise -> None, meaning a plain standard shell. Vault, secret, Ancient and the Blessing are never handed to the CPU."""
    if not (ammo_fx and is_special_ammo(player_ammo)):
        return None
    banned = {BLESSING_KEY} | {a.key for a in ANCIENT_AMMOS + TICKET_AMMOS + SECRET_AMMOS}
    pool = sorted(k for k in save.unlocked_ammo() if k not in banned and is_special_ammo(k))
    return pool or sorted(k for k, a in AMMO_BY_KEY.items() if k not in banned and a.mechanics)    # MUST be special even if you own few


def pick_ai_kit(save: SaveData, rng: random.Random, difficulty: Difficulty, player_color: int, ammo_pool: Optional[list] = None) -> PlayerSetup:
    """Opponent for a normal Single Player match. Master difficulty always fields the Master kit."""
    if difficulty is Difficulty.MASTER:
        lv = TOURNAMENT[-1]
        body, shot, design, ammo = lv.boss_color, lv.boss_shot, lv.tank, lv.ammo
        ammo = rng.choice(ammo_pool) if ammo_pool else DEFAULT_AMMO.key          # the Master kit still mirrors your ammo choice
    else:
        design = rng.choice(DESIGNS[:BASE_KITS]).key
        ammo = rng.choice(ammo_pool) if ammo_pool else DEFAULT_AMMO.key
        body = rng.choice([n for n, _ in COLOR_CHOICES])
        shot = rng.choice([n for n, _ in COLOR_CHOICES])
    bi = color_index(body)
    if bi == player_color:
        bi = (bi + 5) % len(COLOR_CHOICES)
    return PlayerSetup("AI", "CPU", COLOR_CHOICES[bi][1], COLOR_BY_NAME[shot], True, design, ammo)
