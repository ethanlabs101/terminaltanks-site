"""Players and loadouts as JSON for LAN play (custom tanks travel with their full record)."""
from __future__ import annotations

from typing import Optional

from tanks.content.ammo import AMMO_BY_KEY
from tanks.content.custom import CUSTOM_DESIGNS, CUSTOM_FMT, register_custom
from tanks.content.paints import COLOR_BY_NAME, COLOR_CHOICES, color_index
from tanks.content.tanks import DESIGN_BY_KEY
from tanks.match.sessions import PlayerSetup
from tanks.save import Loadout, SaveData
from tanks.settings import Difficulty


def _custom_rec_for(key: str) -> Optional[dict]:
    d = CUSTOM_DESIGNS.get(key)
    return None if d is None else {"id": key[7:], "name": d.name, "lore": d.blurb, "fmt": CUSTOM_FMT,
                                   "parts": dict(zip(("turret", "hull", "track"), d.parts), barrel=d.barrel, glow=d.glow, ambient=d.ambient,
                                                  accent=next((n for n, c in COLOR_CHOICES if c == d.accent), "WHITE"))}


def player_to_json(p: PlayerSetup) -> dict:
    d = dict(vars(p))
    if p.design.startswith("custom:"):
        d["custom_rec"] = _custom_rec_for(p.design)
    d["tank_color"], d["shot_color"] = list(p.tank_color), list(p.shot_color)
    d["diff"] = p.diff.name if p.diff else None
    return d


def player_from_json(d: dict) -> PlayerSetup:
    d = dict(d)
    if isinstance(d.get("custom_rec"), dict):
        register_custom(d["custom_rec"])                           # the peer's own tank design, usable for this match only
    if d.get("design") not in DESIGN_BY_KEY:
        d["design"] = "ranger"
    d["tank_color"], d["shot_color"] = tuple(d["tank_color"]), tuple(d["shot_color"])
    d["diff"] = Difficulty[d["diff"]] if d.get("diff") else None
    return PlayerSetup(**{k: v for k, v in d.items() if k in PlayerSetup.__dataclass_fields__})


def loadout_json(lo: Loadout) -> dict:
    d = dict(vars(lo))
    if lo.tank.startswith("custom:"):
        d["custom_rec"] = _custom_rec_for(lo.tank)
    return d


def loadout_from_json(d: dict, save: "SaveData", owner: int) -> Loadout:
    """Accepts the peer's loadout but never trusts it blindly (unknown kits fall back to the starters)."""
    lo = Loadout()
    if isinstance(d.get("custom_rec"), dict):
        register_custom(d["custom_rec"])
    if d.get("tank") in DESIGN_BY_KEY:
        lo.tank = d["tank"]
    if d.get("ammo") in AMMO_BY_KEY:
        lo.ammo = d["ammo"]
    for f in ("tank_color", "shot_color"):
        if d.get(f) in COLOR_BY_NAME:
            setattr(lo, f, d[f])
    return lo


def lan_players(host_lo: Loadout, guest_lo: Loadout, hp: int) -> list:
    """Two human seats for a LAN versus match (the guest's hull colour is nudged if it matches the host's)."""
    gcol = guest_lo.tank_color
    if gcol == host_lo.tank_color:
        gcol = COLOR_CHOICES[(color_index(gcol) + 12) % len(COLOR_CHOICES)][0]
    mk = lambda lo, col, name, label, owner: PlayerSetup(name, label, COLOR_BY_NAME[col], COLOR_BY_NAME[lo.shot_color], False,
                                                         lo.tank, lo.ammo, hp, owner=owner)
    return [mk(host_lo, host_lo.tank_color, "PLAYER 1", "P1", 0), mk(guest_lo, gcol, "PLAYER 2", "P2", 1)]
