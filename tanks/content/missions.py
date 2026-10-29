"""The 50 missions (five acts): marathons, 2-vs-1, UFO hunts, co-op, boss rushes and the Mothership, with their
rewards and payouts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from tanks.content.ammo import MISSION_AMMOS
from tanks.content.homes import MISSION_THEMES
from tanks.content.maps import MISSION_MAPS
from tanks.content.rewards import COIN_HALF, Payout, tournament_payout
from tanks.content.tanks import MISSION_DESIGNS
from tanks.content.tournament import TournamentLevel
from tanks.settings import Difficulty


# ---------------------------------------------------------------------------
# Missions: 50 numbered challenges, each unlocked by clearing the one before (like the Tournament, but with variety).
#   marathon  win N matches in a row (losing any match fails it)        2v1    you against two AI tanks
#   ufo       one huge hovering saucer with a big health pool             coop   two players (local, LAN or + AI wingman)
#   rush      beat a string of Tournament bosses, one round each          mother the final saucer fleet (Grand Prize)
# Coins only (never credits). First clear pays much more than repeats; every 5th mission also hands out kit rewards.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Mission:
    number: int
    name: str
    kind: str                    # marathon | 2v1 | ufo | coop | rush | mother
    diff: Difficulty
    diff_end: Difficulty         # marathons ramp from diff to diff_end
    stages: int                  # matches (marathon) / bosses (rush) / 1
    target: int                  # rounds to win per stage
    fail_at: int                 # enemy round wins in a stage that fail the mission
    hp: int                      # hearts each human starts with
    enemies: int = 1
    enemy_hp: int = 3
    ufo_hp: int = 0
    prec: float = 1.0
    levels: tuple = ()           # rush: Tournament level numbers
    coop_ufo: bool = False
    map_key: Optional[str] = None
    blurb: str = ""
    rewards: tuple = ()

    @property
    def is_coop(self) -> bool:
        return self.kind == "coop"

    @property
    def type_name(self) -> str:
        return {"marathon": "MARATHON", "2v1": "2 vs 1", "ufo": "UFO ASSAULT", "coop": "CO-OP", "rush": "BOSS RUSH",
                "mother": "MOTHERSHIP"}[self.kind]

    @property
    def objective(self) -> str:
        k = self.kind
        if k == "marathon":
            return f"WIN {self.stages} MATCHES IN A ROW"
        if k == "rush":
            return f"BEAT {self.stages} BOSSES, NO LOSSES"
        if k == "mother":
            return "DESTROY THE MOTHERSHIP FLEET"
        if k == "coop":
            return "TEAM UP: " + ("DOWN THE SAUCER" if self.coop_ufo else "BEAT BOTH TANKS") + f" ({self.target} RDS)"
        if k == "ufo":
            return f"DOWN THE SAUCER ({self.target} {'RD' if self.target == 1 else 'RDS'})"
        return f"BEAT BOTH TANKS - WIN {self.target} ROUNDS"

    @property
    def rule_text(self) -> str:
        k = self.kind
        if k == "marathon":
            return "LOSE ONE MATCH AND IT'S OVER"
        if k == "rush":
            return "LOSE ONE ROUND AND IT'S OVER"
        return f"{self.fail_at} LOST ROUNDS FAIL IT  ·  {self.hp} HEARTS"

    @property
    def first_coins(self) -> int:
        base = 80 + 6 * self.number
        if self.kind == "rush":
            base = int(base * 1.5)
        if self.kind == "mother":
            base += 1000
        return base

    @property
    def repeat_coins(self) -> int:
        return int(self.first_coins * 0.5)

    @property
    def first_credits(self) -> int:
        return 25 if self.kind == "mother" else 6 if self.kind == "rush" else 2


MISSION_REWARDS = {
    5: ("tank:wardog", "ammo:bandit"), 10: ("map:bunker-line", "theme:outpost"), 15: ("tank:spitfire", "ammo:salvo"),
    20: ("map:radar-hill", "theme:radar"), 25: ("tank:blitz", "ammo:hailstorm"), 30: ("map:shelled-field", "theme:warzone"),
    35: ("tank:judge", "ammo:meltdown"), 40: ("map:space-elevator", "theme:orbital"),
    45: ("tank:hydra", "ammo:oblivion", "map:asteroid-field", "theme:deepspace"),
    50: ("tank:ufo", "ammo:xenon", "map:mothership", "theme:invasion"),
}
_MARATHONS = {1: 3, 5: 3, 6: 3, 11: 3, 16: 4, 20: 4, 21: 4, 26: 5, 30: 5, 31: 5, 36: 6, 41: 7, 46: 10}
_RUSH = {40: tuple(range(1, 8)), 45: tuple(range(8, 15)), 47: tuple(range(1, 21))}
_UFO_NAMES = ("SCOUT", "DRONE", "SKIMMER", "HUNTER", "REAPER", "WARSHIP", "DESTROYER", "CRUISER", "DREADNOUGHT", "LEVIATHAN", "OVERMIND",
              "ARCHON")
_MARA_NAMES = ("WARM-UP RUN", "ROAD TO NOWHERE", "LONG HAUL", "IRON LEGS", "UNBROKEN", "ENDURANCE", "THE GRIND", "NO BRAKES", "STREAKER",
               "LAST MILE", "THE LONG ROAD", "FULL DISTANCE", "ULTRA")
_OUT_NAMES = ("OUTNUMBERED", "TWO ON ONE", "PINCER", "CROSSFIRE", "THE AMBUSH", "SURROUNDED", "DOUBLE TROUBLE", "NO ESCAPE", "BAD ODDS",
              "LAST STAND")
_COOP_NAMES = ("BUDDY SYSTEM", "TAG TEAM", "SIDE BY SIDE", "BACK TO BACK", "DUAL STRIKE", "WINGMEN", "IN SYNC", "TWIN FIRE", "ONE TEAM",
               "SHOULDER TO SHOULDER", "BROTHERS IN ARMS")
_UFO_HP = (8, 10, 12, 13, 14, 15, 14, 16, 18, 20, 22, 24)          # saucer health by UFO mission, Scout .. Archon (2-round fights from Destroyer)
_COOP_UFO_HP = {34: 24, 39: 30, 44: 40, 49: 45}                    # co-op saucers: two shooters, so about 1.5-2x the solo saucer nearby


def _build_missions() -> tuple:
    out, counts = [], {"marathon": 0, "2v1": 0, "ufo": 0, "coop": 0}
    ufo_ranks = [n for n in range(1, 50) if (n % 5 == 3 or n in (15, 35)) and n not in _RUSH]
    tiers = (Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD)

    def tier(n: int) -> Difficulty:
        return tiers[0 if n <= 8 else 1 if n <= 18 else 2]

    for n in range(1, 51):
        prec = round(1.45 - 0.75 * (n - 1) / 49, 2)
        d = tier(n)
        rewards = MISSION_REWARDS.get(n, ())
        if n == 50:
            m = Mission(n, "THE MOTHERSHIP", "mother", Difficulty.HARD, Difficulty.HARD, 1, 1, 3, 9, 3, 4, 30, 0.8,
                        map_key="mothership", blurb="The alien flagship and its two drones. Everything you have learned, at once.")
        elif n in _RUSH:
            lv = _RUSH[n]
            m = Mission(n, {40: "BOSS RUSH I", 45: "BOSS RUSH II", 47: "THE GAUNTLET"}[n], "rush", Difficulty.HARD, Difficulty.MASTER,
                        len(lv), 1, 1, 4, levels=lv,
                        blurb="Every boss in a row, one round each, no healing. One loss ends the run." if n != 47 else
                        "All twenty Tournament bosses, back to back. The end-game test.")
        elif n in _MARATHONS:
            i = counts["marathon"] = counts["marathon"] + 1
            end = tiers[min(2, tiers.index(d) + 1)]
            m = Mission(n, _MARA_NAMES[(i - 1) % len(_MARA_NAMES)], "marathon", d, end, _MARATHONS[n], 2, 2, 3, prec=prec,
                        blurb=f"{_MARATHONS[n]} matches against fresh opponents. A lost match ends the marathon.")
        elif n in ufo_ranks:
            rk = ufo_ranks.index(n)
            counts["ufo"] += 1
            m = Mission(n, f"UFO: {_UFO_NAMES[rk % len(_UFO_NAMES)]}", "ufo", Difficulty.NORMAL if rk < 3 else Difficulty.HARD,
                        Difficulty.HARD, 1, 1 if rk < 6 else 2, 2 if rk < 6 else 3, 6 if rk < 4 else 7 if rk < 8 else 9, 1, 3,
                        _UFO_HP[min(rk, len(_UFO_HP) - 1)], prec, map_key="space-elevator" if rk >= 6 else None,
                        blurb="A huge saucer hovers above the field: shields, hops and three-shot volleys. Direct hits count double.")
        elif n % 5 == 4 or n in (25,):
            i = counts["coop"] = counts["coop"] + 1
            ufo = n >= 34
            m = Mission(n, _COOP_NAMES[(i - 1) % len(_COOP_NAMES)], "coop", d, d, 1, 2, 3, 5 if not ufo else 7, 2, 4,
                        _COOP_UFO_HP.get(n, 10 + (n - 34)) if ufo else 0, prec, coop_ufo=ufo,
                        blurb="Two players, one team. Play local, over LAN, or bring an AI wingman.")
        else:
            i = counts["2v1"] = counts["2v1"] + 1
            m = Mission(n, _OUT_NAMES[(i - 1) % len(_OUT_NAMES)], "2v1", d, d, 1, 2, 3, 6, 2, 3,
                        prec=prec, blurb="Two AI tanks hunt you. Pick them off one at a time.")
        out.append(replace(m, rewards=rewards))
    return tuple(out)


MISSIONS: tuple = _build_missions()
assert len(MISSIONS) == 50 and all(m.number == i + 1 for i, m in enumerate(MISSIONS))
assert MISSIONS[-1].kind == "mother" and all(m.diff is not Difficulty.MASTER or m.kind == "rush" for m in MISSIONS)
assert {"marathon", "2v1", "ufo", "coop", "rush", "mother"} == {m.kind for m in MISSIONS}
assert all(uid.split(":")[1] in {*(d.key for d in MISSION_DESIGNS), *(a.key for a in MISSION_AMMOS), *(x.key for x in MISSION_MAPS),
                                 *(k.lower() for k in MISSION_THEMES)} for r in MISSION_REWARDS.values() for uid in r)


def payout_state(level: TournamentLevel, cleared: bool) -> tuple:
    """(label, Payout) for the single reward that applies to a level right now: first clear until cleared, then replay."""
    return ("REPLAY", tournament_payout(level, True, False)) if cleared else ("FIRST CLEAR", tournament_payout(level, True, True))


def mission_payout(m: Mission, won: bool, first: bool) -> Payout:
    if not won:
        return Payout(COIN_HALF)
    return Payout(m.first_coins, m.first_credits) if first else Payout(m.repeat_coins)    # first clears also pay a few credits
