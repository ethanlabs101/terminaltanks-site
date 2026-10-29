"""Workshop (custom) tanks: the record format stored in saves, how a record becomes a TankDesign, which parts a
player owns, and the fee and slot limits."""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from tanks.art.barrels import BARRELS
from tanks.art.tanks import AMBIENT_KINDS, GLOW_STYLES
from tanks.content.ammo import ALL_AMMOS, SECRET_AMMOS
from tanks.content.homes import HOME_ORDER
from tanks.content.maps import MAPS, SPECIAL_MAPS
from tanks.content.paints import COLOR_BY_NAME, COLOR_CHOICES
from tanks.content.tanks import (
    ALL_DESIGNS, BASE_KITS, DESIGNS, DESIGN_BY_KEY, HULLS, SECRET_DESIGNS, TRACKS, TURRETS, TankDesign
)

if TYPE_CHECKING:
    from tanks.save import SaveData


# ---------------------------------------------------------------------------
# Custom tanks. Stored as self-describing records with STABLE component ids (never array indexes) and a format version, so a
# saved tank still resolves after the game gains new components, tanks or reorders its lists. Anything that has gone missing
# falls back to a sensible default for that slot instead of corrupting the save, and unknown extra fields are preserved.
# ---------------------------------------------------------------------------
CUSTOM_FMT = 1
CUSTOM_TANK_FEE = 2500
HOVER_COINS, HOVER_CREDITS = 2500, 0           # HOVER doubles a custom tank's price (2,500 -> 5,000); opens after the Mothership
CUSTOM_TANK_MAX = 24
CUSTOM_SLOTS = ("turret", "hull", "track", "barrel", "glow", "ambient", "accent")
CUSTOM_FALLBACK = {"turret": "dome", "hull": "plain", "track": "std", "barrel": "single", "glow": "none", "ambient": "none", "accent": "WHITE"}
FREE_PARTS = {"turret": {"dome", "box", "twin", "wide", "pillbox"}, "hull": {"plain", "plate", "ramp", "wide", "hex"},
              "track": {"std", "full", "round", "tread"}, "barrel": {"single", "double", "heavy"},
              "glow": {"none", "pulse", "blink"}, "ambient": {"none", "sparks", "mist"}}
CUSTOM_DESIGNS: dict[str, TankDesign] = {}        # runtime registry: key "custom:<id>" (also mirrored into DESIGN_BY_KEY)


def component_tables() -> dict:
    """Every component id by slot: the single registry the workshop, the cheat screen and the validators all read."""
    return {"turret": list(TURRETS), "hull": list(HULLS), "track": list(TRACKS), "barrel": list(BARRELS),
            "glow": list(GLOW_STYLES), "ambient": list(AMBIENT_KINDS), "accent": [n for n, _ in COLOR_CHOICES]}


def design_from_custom(rec: dict) -> TankDesign:
    """Builds a TankDesign from a stored record, repairing anything that no longer exists."""
    tables, p = component_tables(), (rec.get("parts") if isinstance(rec.get("parts"), dict) else {})
    pick = lambda slot: p.get(slot) if p.get(slot) in tables[slot] else CUSTOM_FALLBACK[slot]
    t, h, k = pick("turret"), pick("hull"), pick("track")
    amb = "+".join(a for a in str(p.get("ambient", "none")).split("+") if a in AMBIENT_KINDS) or "none"
    name = "".join(c for c in str(rec.get("name", "CUSTOM")).upper() if c.isalnum() or c in " -")[:14].strip() or "CUSTOM"
    lore = str(rec.get("lore", ""))[:60] or "A tank of your own design."
    return TankDesign(f"custom:{rec.get('id', 'x')}", name, lore, TURRETS[t] + HULLS[h] + TRACKS[k], barrel=pick("barrel"),
                      glow=pick("glow"), ambient=amb, accent=COLOR_BY_NAME.get(p.get("accent"), (236, 242, 250)), parts=(t, h, k),
                      hover=3.0 if rec.get("hover") else 0.0)


def register_custom(rec: dict) -> Optional[TankDesign]:
    if not isinstance(rec, dict) or not isinstance(rec.get("id"), str):
        return None
    d = design_from_custom(rec)
    CUSTOM_DESIGNS[d.key] = d
    DESIGN_BY_KEY[d.key] = d
    return d


def custom_designs(save: "SaveData") -> tuple:
    return tuple(d for d in (register_custom(r) for r in save.custom_tanks) if d is not None)


def workshop_components(save: "SaveData") -> dict:
    """What the player may use in the workshop: the free starter set plus every component of every tank they own."""
    have = {s: set(FREE_PARTS.get(s, ())) for s in CUSTOM_SLOTS}
    owned = save.unlocked_tanks()
    for d in ALL_DESIGNS:
        if d.key not in owned and d.key not in {x.key for x in DESIGNS[:BASE_KITS]}:
            continue
        for slot, cid in zip(("turret", "hull", "track"), d.parts):
            have[slot].add(cid)
        have["barrel"].add(d.barrel)
        have["glow"].add(d.glow)
        have["ambient"].update(d.ambient.split("+"))
    have["accent"] = {n for n, _ in COLOR_CHOICES}
    tables = component_tables()
    return {s: [c for c in tables[s] if c in have[s]] for s in CUSTOM_SLOTS}


def component_counts(save: "SaveData") -> tuple:
    """(unlocked, total) component counts, derived live from the registries."""
    have, tables = workshop_components(save), component_tables()
    return sum(len(have[s]) for s in CUSTOM_SLOTS if s != "accent"), sum(len(tables[s]) for s in CUSTOM_SLOTS if s != "accent")


def content_counts(save: "SaveData") -> list:
    """Every (label, owned, total) row the cheat screen shows - all computed from the current registries."""
    tanks, ammo = save.unlocked_tanks(), save.unlocked_ammo()
    official_t = [d for d in ALL_DESIGNS if d.key not in {x.key for x in SECRET_DESIGNS}]
    official_a = [a for a in ALL_AMMOS if a.key not in {x.key for x in SECRET_AMMOS}]
    comps = component_counts(save)
    return [("TANKS", sum(d.key in tanks for d in official_t), len(official_t)), ("AMMO", sum(a.key in ammo for a in official_a), len(official_a)),
            ("MAPS", len(MAPS) + len(save.unlocked_maps()), len(MAPS) + len(SPECIAL_MAPS)),
            ("SCREENS", len(save.home_modes()), len(HOME_ORDER)), ("PARTS", comps[0], comps[1]),
            ("CUSTOM", len(save.custom_tanks), CUSTOM_TANK_MAX)]
