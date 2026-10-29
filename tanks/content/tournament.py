"""The 20 Tournament levels: boss, kit, map, rule (streak, glass cannon, ...), difficulty and aim precision."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tanks.config import BOSS_MAX_WINS, FINAL_BOSSES, GLASS_HP, MAX_HP
from tanks.content.ammo import AMMOS
from tanks.content.maps import MASTER_MAP, SPECIAL_MAP_BY_KEY
from tanks.content.tanks import BASE_KITS, DESIGNS
from tanks.settings import Difficulty


@dataclass(frozen=True)
class TournamentLevel:
    """One boss fight. `rule` selects the win/loss condition:
        ""          standard: the boss may win twice (two strikes); its third round win fails the level
        "streak"    win `wins` rounds IN A ROW - a boss round win resets the streak (no strikes, unlimited tries)
        "flawless"  win `wins` rounds without losing a single one - the first boss round win fails the level
        "onestrike" the boss may win once; its second round win fails the level
        "glass"     standard strikes, but your tank has only two hearts
        "gale"      standard strikes, but the wind is stuck at its strongest
    The last FINAL_BOSSES levels never use a rule."""
    number: int
    name: str
    boss: str
    difficulty: Difficulty
    wins: int                  # rounds the player must win
    tank: str                  # boss kit == the reward kit
    ammo: str
    boss_color: str
    boss_shot: str
    blurb: str
    map_key: Optional[str] = None       # a reward map the level is fought on (looked up in SPECIAL_MAP_BY_KEY)
    precision: float = 1.0              # AI aim-noise multiplier: <1 = sharper, >1 = sloppier (fine ramp inside a difficulty)
    rule: str = ""
    extra_rewards: tuple = ()           # unlockable ids beyond the kit (+ map) this level hands out

    # -- rules ---------------------------------------------------------------
    @property
    def consecutive(self) -> bool:
        return self.rule == "streak"

    @property
    def fail_at(self) -> Optional[int]:
        """Boss round wins that fail the level (None = it can never be failed, only retried within the run)."""
        return {"streak": None, "flawless": 1, "onestrike": 2}.get(self.rule, BOSS_MAX_WINS)

    @property
    def strikes_allowed(self) -> Optional[int]:
        return None if self.fail_at is None else self.fail_at - 1

    @property
    def player_hp(self) -> int:
        return GLASS_HP if self.rule == "glass" else MAX_HP

    @property
    def wind_override(self) -> Optional[float]:
        return 10.0 if self.rule == "gale" else None

    @property
    def is_final(self) -> bool:
        return self.number > len(TOURNAMENT) - FINAL_BOSSES

    @property
    def rule_tag(self) -> str:
        return {"": "STANDARD", "streak": "BACK TO BACK", "flawless": "FLAWLESS", "onestrike": "ONE STRIKE",
                "glass": "GLASS CANNON", "gale": "GALE FORCE"}[self.rule]

    @property
    def rule_text(self) -> str:
        return {"": "2 STRIKES - BOSS WIN #3 FAILS IT",
                "streak": "NO STRIKES - A LOSS RESETS STREAK",
                "flawless": "NO STRIKES - 1 LOST ROUND FAILS",
                "onestrike": "1 STRIKE - BOSS WIN #2 FAILS IT",
                "glass": f"{GLASS_HP} HEARTS - BOSS WIN #3 FAILS IT",
                "gale": "WIND LOCKED AT MAX - 2 STRIKES"}[self.rule]

    @property
    def objective(self) -> str:
        if self.rule == "streak":
            return f"WIN {self.wins} ROUNDS IN A ROW"
        if self.rule == "flawless":
            return f"WIN {self.wins} ROUNDS, LOSE NONE"
        return f"WIN {self.wins} ROUNDS"

    def reward_ids(self) -> tuple:
        """Every unlockable id earned by clearing this level: its exact boss tank + ammo, its map, any extras."""
        ids = [f"tank:{self.tank}", f"ammo:{self.ammo}"]
        if self.map_key:
            ids.append(f"map:{self.map_key}")
        return tuple(ids) + tuple(self.extra_rewards)


# Twenty levels in four acts. Level N unlocks exactly one new tank + one new ammo type (kit number 5+N) and its boss
# fights with that very kit. Levels 1-17 climb Easy -> Normal -> Hard with a per-level `precision` ramp; some of them use
# a special win condition (`rule`). Levels 18-20 are the three big bosses: Master AI, standard rules only, each on its
# own reward map; 18 and 19 are shorter fights, 20 is the longest, on the Citadel, and the only one that unlocks the
# Master difficulty and Master home screen.
TOURNAMENT: tuple[TournamentLevel, ...] = (
    TournamentLevel(1, "BOOT CAMP", "STINGER", Difficulty.EASY, 3, "hornet", "venom", "YELLOW", "LIME",
                    "Land three rounds back to back.", rule="streak"),
    TournamentLevel(2, "PROVING GROUND", "WARDEN", Difficulty.NORMAL, 3, "titan", "starburst", "STEEL", "SKY",
                    "A patient gunner who learns fast.", precision=1.25),
    TournamentLevel(3, "GHOST FRONT", "SPECTER", Difficulty.NORMAL, 4, "phantom", "void", "VIOLET", "PURPLE",
                    "Quiet, steady and hard to shake.", precision=1.05),
    TournamentLevel(4, "IRON GAUNTLET", "COLOSSUS", Difficulty.NORMAL, 4, "juggernaut", "inferno", "CRIMSON", "ORANGE",
                    "A siege engine that never blinks.", precision=0.9),
    TournamentLevel(5, "STEEL SENTRY", "SENTINEL", Difficulty.HARD, 4, "sentinel", "pulse", "TEAL", "AQUA",
                    "Two hearts. Spend them wisely.", precision=1.4, rule="glass"),
    TournamentLevel(6, "DEEP FREEZE", "GLACIER", Difficulty.HARD, 5, "glacier", "cryo", "SKY", "WHITE",
                    "Cold, exact and in no hurry.", precision=1.3),
    TournamentLevel(7, "SOLAR FLARE", "HELIOS", Difficulty.HARD, 5, "helios", "nova", "ORANGE", "YELLOW",
                    "Hot hands, hotter shells.", precision=1.2),
    TournamentLevel(8, "DUST BOWL", "RATTLER", Difficulty.HARD, 3, "rattler", "shrapnel", "SAND", "COPPER",
                    "Win clean: lose a single round and it is over.", precision=1.25, rule="flawless"),
    TournamentLevel(9, "TOXIC MARSH", "MIASMA", Difficulty.HARD, 5, "miasma", "blight", "LIME", "GREEN",
                    "It gets in everywhere.", precision=1.1),
    TournamentLevel(10, "STONE WALL", "BASTION", Difficulty.HARD, 5, "bastion", "siege", "OLIVE", "SAND",
                    "A fortress that fires back.", precision=1.05),
    TournamentLevel(11, "WIND TUNNEL", "ZEPHYR", Difficulty.HARD, 5, "zephyr", "cyclone", "AQUA", "WHITE",
                    "The wind never drops. Read it or lose.", precision=1.15, rule="gale"),
    TournamentLevel(12, "CRYSTAL DEPTHS", "GEODE", Difficulty.HARD, 6, "geode", "crystal", "VIOLET", "PINK",
                    "Every facet is a firing line.", precision=0.95),
    TournamentLevel(13, "HALL OF MIRRORS", "MIRAGE", Difficulty.HARD, 6, "mirage", "echo", "PINK", "MAGENTA",
                    "Is that the real tank?", precision=0.9),
    TournamentLevel(14, "GRAVEYARD SHIFT", "REVENANT", Difficulty.HARD, 5, "revenant", "wraith", "OBSIDIAN", "CYAN",
                    "It only needs two wins.", precision=1.05, rule="onestrike"),
    TournamentLevel(15, "SKY RAID", "CORSAIR", Difficulty.HARD, 6, "corsair", "barrage", "COBALT", "SKY",
                    "Fast, loud and accurate.", precision=0.8),
    TournamentLevel(16, "BLOOD MOON", "TYRANT", Difficulty.HARD, 4, "tyrant", "wrath", "CRIMSON", "GOLD",
                    "Four in a row. Blink and it resets.", precision=0.85, rule="streak"),
    TournamentLevel(17, "THE GATEKEEPER", "ARCHON", Difficulty.HARD, 6, "archon", "zenith", "GOLD", "WHITE",
                    "The last guard on the Master's road.", precision=0.65),
    TournamentLevel(18, "THE FORGE", "OBSIDIAN", Difficulty.MASTER, 5, "obsidian", "magma", "OBSIDIAN", "ORANGE",
                    "Master-grade fire control in a lava foundry.", map_key="forge", precision=0.95),
    TournamentLevel(19, "STORM SPIRE", "TEMPEST", Difficulty.MASTER, 6, "tempest", "thunder", "BLUE", "CYAN",
                    "Lightning overhead, a Master across the gap.", map_key="spire", precision=0.88),
    TournamentLevel(20, "MASTER'S CITADEL", "THE MASTER", Difficulty.MASTER, 8, "sovereign", "aurora", "GOLD", "WHITE",
                    "The final duel, on ground few have seen.", map_key="citadel", precision=0.78,
                    extra_rewards=("master_difficulty", "theme:master")),
)
assert len(TOURNAMENT) == 20 and TOURNAMENT[-1].map_key == MASTER_MAP.key
assert all(l.number == i + 1 for i, l in enumerate(TOURNAMENT))
# the progression contract: level N unlocks kit number BASE_KITS+N (exactly one tank + one ammo) and its boss uses it
assert all(l.tank == DESIGNS[BASE_KITS + l.number - 1].key and l.ammo == AMMOS[BASE_KITS + l.number - 1].key for l in TOURNAMENT)
assert all(l.map_key in SPECIAL_MAP_BY_KEY for l in TOURNAMENT if l.map_key)
assert all(l.rule == "" for l in TOURNAMENT[-FINAL_BOSSES:]) and sum(1 for l in TOURNAMENT if l.rule) >= 5
assert all(l.rule != "streak" or l.difficulty is not Difficulty.MASTER for l in TOURNAMENT)
