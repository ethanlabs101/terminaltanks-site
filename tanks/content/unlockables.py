"""The unlock registry: every unlockable id in the game, listed once (the unlock-everything cheat grants them all)."""
from __future__ import annotations

from dataclasses import dataclass

from tanks.content.ammo import AMMOS, ANCIENT_AMMOS, MISSION_AMMOS, SECRET_AMMOS, SHOP_AMMOS, TICKET_AMMOS
from tanks.content.homes import HOME_ORDER
from tanks.content.maps import SPECIAL_MAPS
from tanks.content.missions import MISSIONS
from tanks.content.paints import ANIMATED_PAINTS
from tanks.content.tanks import (
    ANCIENT_DESIGNS, BASE_KITS, DESIGNS, MISSION_DESIGNS, SECRET_DESIGNS, SHOP_DESIGNS, TICKET_DESIGNS
)
from tanks.content.tournament import TOURNAMENT


# ---------------------------------------------------------------------------
# Unlock registry. Everything that can be unlocked is listed here once; the 'iamethanlabs101' cheat simply
# grants every entry, so adding a future unlockable is: register it below (one line) and give it a rule in
# SaveData.is_unlocked if it isn't earned through a Tournament level's reward_ids() or bought in the shop.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Unlockable:
    uid: str        # "tank:<key>" | "ammo:<key>" | "map:<key>" | "level:<n>" | "theme:<name>" | "rgb:<hull|shell>" | ...
    kind: str       # tank | ammo | map | level | theme | feature
    label: str


UNLOCKABLES: list[Unlockable] = []


def register_unlockable(uid: str, kind: str, label: str) -> None:
    if all(u.uid != uid for u in UNLOCKABLES):
        UNLOCKABLES.append(Unlockable(uid, kind, label))


def unlockables() -> tuple[Unlockable, ...]:
    return tuple(UNLOCKABLES)


def _register_default_unlockables() -> None:
    for d in DESIGNS[BASE_KITS:] + SHOP_DESIGNS + MISSION_DESIGNS + TICKET_DESIGNS + SECRET_DESIGNS + ANCIENT_DESIGNS:
        register_unlockable(f"tank:{d.key}", "tank", d.name)
    for a in AMMOS[BASE_KITS:] + SHOP_AMMOS + MISSION_AMMOS + TICKET_AMMOS + SECRET_AMMOS + ANCIENT_AMMOS:
        register_unlockable(f"ammo:{a.key}", "ammo", a.name)
    for m in MISSIONS[1:]:                          # mission 1 is always open
        register_unlockable(f"mission:{m.number}", "mission", f"MISSION {m.number}")
    for m in SPECIAL_MAPS:
        register_unlockable(f"map:{m.key}", "map", m.name)
    for lv in TOURNAMENT[1:]:                       # level 1 is always open
        register_unlockable(f"level:{lv.number}", "level", f"LEVEL {lv.number}")
    register_unlockable("master_difficulty", "feature", "MASTER DIFFICULTY")
    for k in HOME_ORDER[1:]:
        register_unlockable(f"theme:{k.lower()}", "theme", f"{k} HOME SCREEN")
    register_unlockable("rgb:hull", "feature", "RGB HULL COLOR")
    register_unlockable("rgb:shell", "feature", "RGB SHELL COLOR")
    for p in ANIMATED_PAINTS[1:]:                   # RGB is unlocked by rgb:hull / rgb:shell above
        register_unlockable(f"paint:{p.name.lower()}", "feature", f"{p.name} PAINT / AMMO COLOR")


_register_default_unlockables()
