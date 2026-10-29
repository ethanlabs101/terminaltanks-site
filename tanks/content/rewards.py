"""The economy: coins and Tournament credits paid for matches and levels, and how a reward id is named on screen."""
from __future__ import annotations

from dataclasses import dataclass

from tanks.content.ammo import AMMO_BY_KEY
from tanks.content.homes import HOME_THEMES
from tanks.content.maps import SPECIAL_MAP_BY_KEY
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.content.tournament import TournamentLevel
from tanks.settings import Difficulty


# ---------------------------------------------------------------------------
# Economy. Two currencies: COINS (everything) and TOURNAMENT CREDITS (Tournament only, needed for Master-tier gear).
# Tweak the numbers here; shop prices are set by tier_price() in tanks/content/shop.py. Cheat codes never touch
# the wallet - the only way to earn is to play.
#   TTT + $$$$   first clear of a big boss (levels 18-20)       T + $$   big boss, later clears
#   T + $$$      first clear of any other level                 $$       other levels, later clears
#   $            single-player win (x difficulty)               $.5      any loss (level failed / match lost)
# ---------------------------------------------------------------------------
COIN_HALF, COIN_LITTLE, COIN_SOME, COIN_DECENT, COIN_LOTS = 15, 40, 120, 250, 1000
CREDITS_SOME, CREDITS_LOTS = 6, 30
SP_WIN_MULT = {Difficulty.EASY: 1.0, Difficulty.NORMAL: 1.25, Difficulty.HARD: 1.5, Difficulty.MASTER: 2.0}


@dataclass(frozen=True)
class Payout:
    coins: int = 0
    credits: int = 0

    def text(self) -> str:
        return f"+{self.coins} ◉" + (f"   +{self.credits} ◈" if self.credits else "")


def tournament_payout(level: TournamentLevel, won: bool, first: bool) -> Payout:
    if not won:
        return Payout(COIN_HALF)
    if level.is_final:
        return Payout(COIN_LOTS, CREDITS_LOTS) if first else Payout(COIN_SOME * 2, CREDITS_SOME)
    return Payout(COIN_DECENT, CREDITS_SOME) if first else Payout(COIN_SOME, 2 if level.number > 10 else 1)    # replays now pay credits too


SP_WIN_CREDITS = {Difficulty.EASY: 0, Difficulty.NORMAL: 0, Difficulty.HARD: 2, Difficulty.MASTER: 4}


def match_payout(won: bool, difficulty: Difficulty) -> Payout:
    return Payout(int(COIN_LITTLE * SP_WIN_MULT[difficulty]), SP_WIN_CREDITS[difficulty]) if won else Payout(COIN_HALF)


def reward_label(uid: str) -> tuple:
    kind, _, key = uid.partition(":")
    if kind == "tank":
        return "TANK", DESIGN_BY_KEY[key].name
    if kind == "ammo":
        return "AMMO", AMMO_BY_KEY[key].name
    if kind == "map":
        return "MAP", SPECIAL_MAP_BY_KEY[key].name
    if kind == "theme":
        return "SCREEN", HOME_THEMES[key.upper()].name if key.upper() in HOME_THEMES else key.upper()
    return kind.upper(), key.upper()
