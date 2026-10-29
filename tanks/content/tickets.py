"""Terminal Tickets: the ten Ancient Hoarders a ticket can summon, each guarding a unique tank, ammo, map and home screen."""
from __future__ import annotations

from dataclasses import dataclass

from tanks.content.ammo import AMMO_BY_KEY
from tanks.content.homes import HOME_THEMES
from tanks.content.maps import SPECIAL_MAP_BY_KEY
from tanks.content.tanks import DESIGN_BY_KEY


# ---------------------------------------------------------------------------
# Terminal Tickets: ten vault bosses. A ticket draws one that has not been beaten yet; beating it grants its tank, ammo, map
# and main screen. Beaten bosses leave the pool; with all ten beaten the ticket is sold out.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TicketBoss:
    key: str
    name: str
    tank: str
    ammo: str
    map_key: str
    theme: str
    hp: int
    prec: float
    taunt: str

    def reward_ids(self) -> tuple:
        return (f"tank:{self.tank}", f"ammo:{self.ammo}", f"map:{self.map_key}", f"theme:{self.theme.lower()}")


TICKET_BOSSES: tuple = (
    TicketBoss("volt", "VOLT SOVEREIGN", "voltsovereign", "arcstorm", "neon-skyline", "VOLTCITY", 9, 0.95, "THE CITY RUNS ON MY LIGHTNING."),
    TicketBoss("magistrate", "IRON MAGISTRATE", "magistrate", "gavel", "clock-plaza", "CLOCKWORKS", 9, 0.9, "YOUR TIME IS UP."),
    TicketBoss("regent", "GLACIER REGENT", "regent", "coldfront", "frozen-cathedral", "FROSTCATHEDRAL", 9, 0.9, "KNEEL IN THE COLD."),
    TicketBoss("solar", "SOLAR ARCHON", "solarch", "sunburst", "sun-temple", "SUNTEMPLE", 10, 0.88, "THE SUN ANSWERS TO ME."),
    TicketBoss("abyssal", "ABYSS LEVIATHAN", "abyssal", "undertow", "sunken-metropolis", "SUNKENCITY", 10, 0.88, "THE DEEP WILL TAKE YOU."),
    TicketBoss("pharaoh", "SAND PHARAOH", "pharaoh", "duneshot", "pyramid-plain", "PYRAMIDPLAIN", 10, 0.85, "THE DESERT KEEPS ITS DEAD."),
    TicketBoss("baron", "TOXIC BARON", "baron", "plague", "chemical-works", "CHEMWORKS", 11, 0.85, "BREATHE DEEP."),
    TicketBoss("shadow", "SHADOW EMPEROR", "shadowlord", "umbra", "gothic-keep", "GOTHICKEEP", 11, 0.82, "THE DARK IS MY THRONE."),
    TicketBoss("overseer", "COSMIC OVERSEER", "overseer", "starshower", "orbital-city", "ORBITALCITY", 12, 0.8, "I SEE EVERY SHOT."),
    TicketBoss("warlord", "DRAGON WARLORD", "warlord", "dragonfire", "pagoda-peak", "PAGODAPEAK", 12, 0.78, "BURN, ALL OF YOU."),
)
TICKET_BOSS_BY_KEY = {b.key: b for b in TICKET_BOSSES}
assert len(TICKET_BOSSES) == 10 and all(b.tank in DESIGN_BY_KEY and b.ammo in AMMO_BY_KEY and b.map_key in SPECIAL_MAP_BY_KEY
                                        and b.theme in HOME_THEMES for b in TICKET_BOSSES)
TICKET_PLAYER_HP, TICKET_WIN_COINS, TICKET_WIN_CREDITS = 6, 2000, 10
