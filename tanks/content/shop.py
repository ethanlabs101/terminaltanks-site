"""The shop. Its pages are built from the content lists: the n-th item of a page lands in tier n // 15 (prices rise
inside each tier, see tier_price); anything past the fourth tier is premium. Extras (RGB, paints, the Terminal
Ticket, the Time Machine) are listed by hand at the end."""
from __future__ import annotations

from dataclasses import dataclass

from tanks.content.ammo import SHOP_AMMOS
from tanks.content.homes import HOME_THEMES, SHOP_THEMES
from tanks.content.maps import SHOP_MAPS
from tanks.content.tanks import SHOP_DESIGNS


# ---------------------------------------------------------------------------
# Shop catalogue: five pages, four tiers (cheap / mid / pro / master-tier). Master-tier gear costs coins AND credits.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ShopItem:
    uid: str
    page: int           # 0 tanks, 1 ammo, 2 main screens, 3 maps, 4 extras
    tier: int           # 0 cheap, 1 mid, 2 pro, 3 master-tier
    name: str
    blurb: str
    coins: int
    credits: int = 0


SHOP_PAGES = ("TANKS", "AMMO", "MAIN SCREEN", "MAPS", "EXTRAS")
TIER_COLORS = ((170, 205, 175), (120, 190, 255), (255, 165, 90), (255, 206, 100), (255, 70, 140))   # tier 4 = premium
TIER_SIZE = 15                                         # items per ordinary tier; anything after tier 3 is the premium tier
_TIER_RANGE = ((50, 150), (150, 450), (300, 900), (600, 1600))          # cheapest..dearest coin price inside each tier
PREMIUM_COINS = tuple(3000 + 400 * j for j in range(15))          # 3,000 .. 8,600 coins
PREMIUM_CREDITS = tuple(15 + 2 * j for j in range(15))            # 15 .. 43 credits
RGB_PRICE = (800, 8)
PRISMATIC_PRICE = (20000, 120)        # ultra expensive: the Prismatic King's refracting crystal as paint for ANY tank and shell
VOID_PRICE = (14000, 80)             # the Singularity's void as paint for ANY tank and shell
MOLTEN_PRICE = (12000, 70)
AURORA_PRICE = (15000, 85)
CIRCUIT_PRICE = (16000, 95)
CHROME_PRICE = (18000, 105)
OCEAN_PRICE = (13000, 75)
SYNTHWAVE_PRICE = (17000, 100)
TOXIC_PRICE = (11000, 65)
GILDED_PRICE = (19000, 110)
TICKET_PRICE = (3000, 25)
MARTYR_PRICE = (15000, 90)


def tier_of(index: int) -> tuple:
    """(tier, position-in-tier) of the n-th item of a shop page: 15 per ordinary tier, then the premium tier."""
    tier = min(index // TIER_SIZE, 4)
    return tier, index - tier * TIER_SIZE


def tier_price(tier: int, j: int) -> tuple:
    """(coins, credits) for item j of a tier. Only master-tier (3) and premium (4) gear costs credits."""
    if tier >= 4:
        return PREMIUM_COINS[min(j, len(PREMIUM_COINS) - 1)], PREMIUM_CREDITS[min(j, len(PREMIUM_CREDITS) - 1)]
    lo, hi = _TIER_RANGE[tier]
    return int(round((lo + (hi - lo) * j / (TIER_SIZE - 1)) / 5) * 5), (3 + j if tier == 3 else 0)


def _build_shop() -> tuple[ShopItem, ...]:
    items: list[ShopItem] = []

    def grid(page: int, rows: list) -> None:          # rows: [(uid, name, blurb)] in tier order
        for i, (uid, name, blurb) in enumerate(rows):
            tier, j = tier_of(i)
            items.append(ShopItem(uid, page, tier, name, blurb, *tier_price(tier, j)))
    grid(0, [(f"tank:{d.key}", d.name, d.blurb) for d in SHOP_DESIGNS])
    grid(1, [(f"ammo:{a.key}", a.name, a.blurb) for a in SHOP_AMMOS])
    grid(2, [(f"theme:{k.lower()}", HOME_THEMES[k].name, HOME_THEMES[k].blurb) for k in SHOP_THEMES])
    grid(3, [(f"map:{m.key}", m.name, m.description) for m in SHOP_MAPS])
    items.append(ShopItem("rgb:hull", 4, 3, "RGB HULL", "Your hull cycles through the whole rainbow.", *RGB_PRICE))
    items.append(ShopItem("rgb:shell", 4, 3, "RGB SHELL", "Your shells, trails and blasts cycle through the rainbow.", *RGB_PRICE))
    items.append(ShopItem("paint:prismatic", 4, 4, "PRISMATIC PAINT", "Paint ANY tank (and shells) in the Prismatic King's living crystal: "
                          "every facet splits the light.", *PRISMATIC_PRICE))
    items.append(ShopItem("paint:void", 4, 4, "VOID PAINT", "Paint ANY tank (and shells) in the Singularity's void: a hull that eats the light.", *VOID_PRICE))
    items.append(ShopItem("paint:molten", 4, 4, "MOLTEN PAINT", "Paint ANY tank (and shells) in cooling lava: black crust over glowing, "
                          "crawling cracks.", *MOLTEN_PRICE))
    items.append(ShopItem("paint:aurora", 4, 4, "AURORA PAINT", "Paint ANY tank (and shells) in the northern lights: green and violet "
                          "curtains over a night sky.", *AURORA_PRICE))
    items.append(ShopItem("paint:circuit", 4, 4, "CIRCUIT PAINT", "Paint ANY tank (and shells) as a live circuit board: signals race "
                          "along the traces.", *CIRCUIT_PRICE))
    items.append(ShopItem("paint:chrome", 4, 4, "CHROME PAINT", "Paint ANY tank (and shells) in liquid mirror metal, with a highlight "
                          "that slides along the hull.", *CHROME_PRICE))
    items.append(ShopItem("paint:ocean", 4, 4, "OCEAN PAINT", "Paint ANY tank (and shells) in deep water: sunlight caustics ripple "
                          "across the hull.", *OCEAN_PRICE))
    items.append(ShopItem("paint:synthwave", 4, 4, "SYNTHWAVE PAINT", "Paint ANY tank (and shells) in outrun neon: a magenta sunset over a "
                          "scrolling grid.", *SYNTHWAVE_PRICE))
    items.append(ShopItem("paint:toxic", 4, 4, "TOXIC PAINT", "Paint ANY tank (and shells) in radioactive ooze: glowing slime drips "
                          "and bubbles over a black hull.", *TOXIC_PRICE))
    items.append(ShopItem("paint:gilded", 4, 4, "GILDED PAINT", "Paint ANY tank (and shells) in gold leaf: engraved scrollwork and a glint "
                          "that sweeps across.", *GILDED_PRICE))
    items.append(ShopItem("ticket", 4, 4, "TERMINAL TICKET", "Summons a random boss from the vault. Win to claim its tank, ammo, map and "
                          "main screen. Each boss appears once.", *TICKET_PRICE))
    items.append(ShopItem("timemachine", 4, 4, "MARTYR'S TIME MACHINE", "An ancient artifact that wakes only when every vault boss has fallen. "
                          "Something inside is waiting for you.", *MARTYR_PRICE))
    return tuple(items)


SHOP_ITEMS: tuple[ShopItem, ...] = _build_shop()
SHOP_BY_UID = {i.uid: i for i in SHOP_ITEMS}
assert len(SHOP_BY_UID) == len(SHOP_ITEMS)
assert all(sum(1 for i in SHOP_ITEMS if i.page == p and i.tier < 4) == 4 * TIER_SIZE for p in range(4))   # tiers 0-3 full on every grid page
assert all((i.credits > 0) == (i.tier >= 3) for i in SHOP_ITEMS)         # exactly the master-tier and premium gear costs credits
