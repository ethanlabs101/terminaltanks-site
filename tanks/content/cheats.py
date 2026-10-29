"""Cheat codes and what they do. Cheats never touch the wallet."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tanks.content.tournament import TOURNAMENT

if TYPE_CHECKING:
    from tanks.app import Application


# ---------------------------------------------------------------------------
# Cheat codes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Cheat:
    code: str
    grants: tuple = ()          # unlockable ids this code hands out
    everything: bool = False    # True: grant every registered unlockable
    activate_theme: str = ""    # home screen to switch to once unlocked
    text: str = ""              # message when something new was unlocked


LEVEL_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
               "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty")
assert len(LEVEL_WORDS) == len(TOURNAMENT)
CHEATS: dict[str, Cheat] = {}


def _register_cheats() -> None:
    def add(c: Cheat) -> None:
        CHEATS[c.code] = c
    add(Cheat("asciieasteregg", ("tank:asciibot", "ammo:glyph"), text="EASTER EGG UNLOCKED: ASCIIBOT TANK + GLYPH AMMO"))
    add(Cheat("iamethanlabs101", everything=True))
    add(Cheat("unlocktimemachine", text="MARTYR'S TIME MACHINE UNLOCKED"))
    add(Cheat("notasecrettheme", ("theme:secret",), activate_theme="SECRET", text="SECRET HOME SCREEN UNLOCKED AND ACTIVATED"))
    for n, word in enumerate(LEVEL_WORDS, 1):       # each level code opens that one level only
        add(Cheat(f"unlocklevel{word}", (f"level:{n}",)))


_register_cheats()


def redeem_cheat(app: "Application", code: str) -> tuple[bool, str]:
    """Runs a cheat code. Returns (success, message). Cheats unlock content only - never coins or credits."""
    cheat = CHEATS.get("".join(code.lower().split()))
    if cheat is None:
        return False, "UNKNOWN CODE"
    save = app.save
    if cheat.code == "unlocktimemachine":                 # opens the Time Machine in the shop and skips its price (no currency given)
        if save.martyr_open and save.martyr_paid:
            return True, "THE TIME MACHINE IS ALREADY UNLOCKED"
        save.martyr_open = save.martyr_paid = True
        save.flush()
        return True, "TIME MACHINE UNLOCKED - FIND IT IN THE SHOP (EXTRAS) AND PRESS ENTER"
    if cheat.everything:
        n = save.grant_all()
        return True, f"ALL UNLOCKABLES GRANTED - {n} NEW" if n else "EVERYTHING IS ALREADY UNLOCKED"
    if cheat.code.startswith("unlocklevel"):
        n = int(cheat.grants[0][6:])
        if save.level_unlocked(n):
            return True, f"LEVEL {n} IS ALREADY OPEN"
        save.grant(cheat.grants[0])
        save.flush()
        return True, f"LEVEL {n} OPENED - CLEAR IT TO EARN ITS REWARDS"
    new = [g for g in cheat.grants if save.grant(g)]
    if not new:
        return True, "ALREADY UNLOCKED"
    if cheat.activate_theme:
        app.settings.home_mode = cheat.activate_theme
        app.apply_settings()
    else:
        save.flush()
    return True, cheat.text or "UNLOCKED"
