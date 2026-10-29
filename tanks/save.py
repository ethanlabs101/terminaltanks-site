"""Progress on disk. SaveData holds everything a player earns (coins, credits, unlocks, Tournament and mission
progress, tickets, the Martyr, custom tanks, loadouts, settings, playtime) and reads/writes save.json. Older save
versions are upgraded when loaded, custom-tank records keep fields from newer versions, and every write goes to a
temporary file that then replaces save.json in one step."""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from tanks import __version__
from tanks.content.ammo import AMMOS, BLESSING_KEY
from tanks.content.custom import (
    CUSTOM_DESIGNS, CUSTOM_FMT, CUSTOM_SLOTS, CUSTOM_TANK_FEE, CUSTOM_TANK_MAX, HOVER_COINS, HOVER_CREDITS, register_custom,
    workshop_components
)
from tanks.content.homes import HOME_ORDER
from tanks.content.maps import MAPS, SPECIAL_MAPS
from tanks.content.martyr import MARTYR_REWARD_IDS
from tanks.content.missions import MISSIONS
from tanks.content.paints import COLOR_BY_NAME, PAINT_UNLOCK
from tanks.content.rewards import Payout
from tanks.content.shop import ShopItem
from tanks.content.tanks import BASE_KITS, DESIGNS
from tanks.content.tickets import TICKET_BOSS_BY_KEY
from tanks.content.tournament import TOURNAMENT
from tanks.content.unlockables import UNLOCKABLES, unlockables
from tanks.settings import Difficulty, SETTING_ROWS, Settings


def default_save_path() -> Path:
    env = os.environ.get("TERMINALTANKS_SAVE")
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "TerminalTanks"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "terminaltanks"
    return base / "save.json"


@dataclass
class Loadout:
    tank: str = "ranger"
    tank_color: str = "CYAN"
    ammo: str = "standard"
    shot_color: str = "YELLOW"


# what a version-1 save that had cleared the old (Master) Level 5 keeps: the Master rewards now live at Level 20
LEGACY_MASTER_GRANTS = ("tank:sovereign", "ammo:aurora", "map:citadel", "master_difficulty", "theme:master")
OLD_FINALS = {8: 18, 9: 19, 10: 20}         # version-2 saves had only ten levels; their last three became levels 18-20


class SaveData:
    """Progress, unlocks, wallet, loadouts and settings, stored as one small JSON file (path=None: in-memory only).

    `completed` = Tournament levels actually cleared (the chain rule applies: a level only counts if it was reachable).
    `granted`   = unlockables handed out some other way (shop purchases, cheat codes, legacy saves). A granted level is
                  only *open to play*; it is never marked cleared, and it never opens the level after it."""
    VERSION = 5

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path
        self.mission_completed: set[int] = set()   # missions cleared (chain rule applies)
        self.mission_paid: set[int] = set()        # missions whose FIRST-clear reward was already paid (also LAN co-op guests)
        self.custom_tanks: list[dict] = []         # workshop creations: stable, versioned records (see design_from_custom)
        self.tickets_won: set[str] = set()         # Terminal Ticket bosses already defeated (they leave the random pool)
        self.martyr_paid, self.martyr_phase, self.martyr_won, self.martyr_seen, self.martyr_open = False, 0, False, False, False   # the Time Machine story
        self.ticket_active: str = ""               # a drawn-but-unbeaten ticket boss: retry it freely, it is never wasted
        self.story: set[str] = set()               # one-time story whispers already heard (see STORY_LINES)
        self.playtime: float = 0.0                 # seconds spent in the game (this profile)
        self.completed: set[int] = set()
        self.granted: set[str] = set()
        self.coins = 0
        self.credits = 0
        self.loadouts = [Loadout(), Loadout("ranger", "ORANGE", "standard", "MAGENTA")]
        self.settings: dict[str, str] = {}

    # -- persistence ---------------------------------------------------------
    @classmethod
    def load(cls, path: Optional[Path]) -> "SaveData":
        data = cls(path)
        if path is None or not path.exists():
            return data
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):                       # unreadable: start fresh in memory
            return data
        if not isinstance(raw, dict):
            return data
        version = raw.get("version", 1) if isinstance(raw.get("version", 1), int) else 1
        known = {u.uid for u in UNLOCKABLES}
        given = raw.get("granted", [])
        data.granted = {g for g in given if isinstance(g, str) and g in known} if isinstance(given, list) else set()
        if version < 3:                  # cheat-opened levels 8-10 meant the old finals
            data.granted = {f"level:{OLD_FINALS[int(g[6:])]}" if g.startswith("level:") and int(g[6:]) in OLD_FINALS else g
                            for g in data.granted}
        done = raw.get("tournament_completed", [])
        if isinstance(done, list):
            done = [n for n in done if isinstance(n, int)]
            if version < 2:
                if 5 in done:           # the old Level 5 was the Master fight: keep its rewards, the new Level 5 is a fresh fight
                    data.granted |= {g for g in LEGACY_MASTER_GRANTS if g in known}
                done = [n for n in done if n != 5]
            elif version < 3:           # old 8/9/10 are now 18/19/20: keep their rewards, they must be re-earned as levels
                for old, new in OLD_FINALS.items():
                    if old in done:
                        data.granted |= {g for g in TOURNAMENT[new - 1].reward_ids() if g in known}
                done = [n for n in done if n < 8]
            ok: set[int] = set()
            for n in range(1, len(TOURNAMENT) + 1):          # a level only counts if it was reachable
                reachable = n == 1 or (n - 1) in ok or f"level:{n}" in data.granted
                if n in done and reachable:
                    ok.add(n)
            data.completed = ok
        mdone = raw.get("missions_completed", [])
        if isinstance(mdone, list):
            ok_m: set[int] = set()
            for n in range(1, len(MISSIONS) + 1):
                if n in mdone and (n == 1 or (n - 1) in ok_m or f"mission:{n}" in data.granted):
                    ok_m.add(n)
            data.mission_completed = ok_m
        ct = raw.get("custom_tanks")
        if isinstance(ct, list):
            seen: set = set()
            for rec in ct:
                if isinstance(rec, dict) and isinstance(rec.get("id"), str) and rec["id"] not in seen:
                    seen.add(rec["id"])
                    data.custom_tanks.append(rec)                  # kept verbatim: unknown fields from newer versions survive
                    register_custom(rec)
        tk = raw.get("tickets")
        if isinstance(tk, dict):
            data.tickets_won = {k for k in tk.get("won", []) if isinstance(k, str)}
            data.ticket_active = tk["active"] if isinstance(tk.get("active"), str) else ""
        if isinstance(raw.get("playtime"), (int, float)) and raw["playtime"] >= 0:
            data.playtime = float(raw["playtime"])
        sty = raw.get("story")
        if isinstance(sty, list):
            data.story = {s for s in sty if isinstance(s, str)}
        mt = raw.get("martyr")
        if isinstance(mt, dict):
            data.martyr_paid, data.martyr_won, data.martyr_seen = bool(mt.get("paid")), bool(mt.get("won")), bool(mt.get("seen"))
            data.martyr_open = bool(mt.get("open"))
            data.martyr_phase = int(mt["phase"]) if isinstance(mt.get("phase"), int) and 0 <= mt["phase"] <= 3 else 0
        if data.martyr_won:                                  # saves that beat the Martyr before new rewards existed get them now
            for uid in MARTYR_REWARD_IDS:
                data.granted.add(uid) if uid in known else None
        paid = raw.get("missions_paid", [])
        data.mission_paid = {n for n in paid if isinstance(n, int) and 1 <= n <= len(MISSIONS)} | data.mission_completed \
            if isinstance(paid, list) else set(data.mission_completed)
        wallet = raw.get("wallet")
        if isinstance(wallet, dict):
            for f in ("coins", "credits"):
                v = wallet.get(f, 0)
                setattr(data, f, max(0, v) if isinstance(v, int) else 0)
        for i, lo in enumerate((raw.get("loadouts") or [])[:2]):
            if isinstance(lo, dict):
                cur = data.loadouts[i]
                for f in ("tank", "tank_color", "ammo", "shot_color"):
                    if isinstance(lo.get(f), str):
                        setattr(cur, f, lo[f])
        st = raw.get("settings")
        if isinstance(st, dict):
            data.settings = {str(k): str(v) for k, v in st.items()}
        return data

    def flush(self) -> None:
        if self.path is None:
            return
        doc = {
            "version": self.VERSION,
            "tournament_completed": sorted(self.completed),
            "granted": sorted(self.granted),
            "missions_completed": sorted(self.mission_completed),
            "missions_paid": sorted(self.mission_paid),
            "tickets": {"won": sorted(self.tickets_won), "active": self.ticket_active},
            "story": sorted(self.story),
            "playtime": round(self.playtime, 1),
            "martyr": {"paid": self.martyr_paid, "phase": self.martyr_phase, "won": self.martyr_won, "seen": self.martyr_seen, "open": self.martyr_open},
            "custom_tanks": self.custom_tanks,
            "wallet": {"coins": self.coins, "credits": self.credits},
            "unlocked": {"tanks": sorted(self.unlocked_tanks()), "ammo": sorted(self.unlocked_ammo()),
                         "maps": [m.key for m in self.unlocked_maps()], "master_difficulty": self.master_unlocked,
                         "home_screens": self.home_modes()},
            "loadouts": [vars(l) for l in self.loadouts],
            "settings": self.settings,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:                                     # read-only or full disk: keep playing, progress stays in memory
            pass

    # -- wallet & shop -------------------------------------------------------
    def earn(self, p: Payout) -> None:
        """The only way money enters the wallet (match / Tournament results). Cheat codes never call this."""
        self.coins += max(0, p.coins)
        self.credits += max(0, p.credits)
        self.flush()

    def shortfall(self, item: ShopItem) -> str:
        if self.coins < item.coins:
            return f"NEED {item.coins - self.coins} MORE COINS"
        if self.credits < item.credits:
            return f"NEED {item.credits - self.credits} MORE CREDITS"
        return ""

    def buy(self, item: ShopItem) -> str:
        """Buys a shop item. Returns '' on success, otherwise the reason it failed."""
        if self.is_unlocked(item.uid):
            return "ALREADY OWNED"
        why = self.shortfall(item)
        if why:
            return why
        self.coins -= item.coins
        self.credits -= item.credits
        self.granted.add(item.uid)
        self.sanitize_loadouts()
        self.flush()
        return ""

    # -- unlock rules --------------------------------------------------------
    def earned(self) -> set:
        """Unlockable ids earned by clearing Tournament levels."""
        out: set = set()
        for lv in TOURNAMENT:
            if lv.number in self.completed:
                out.update(lv.reward_ids())
        for m in MISSIONS:
            if m.number in self.mission_completed:
                out.update(m.rewards)
        return out

    def tickets_sold_out(self) -> bool:
        return len(self.tickets_won & set(TICKET_BOSS_BY_KEY)) >= len(TICKET_BOSS_BY_KEY)

    def buy_ticket(self, item: "ShopItem") -> str:
        """Pays for a Terminal Ticket and draws a random boss that has not been beaten. Returns the boss key, or '' if it
        could not be bought. A drawn boss stays active until beaten, so losing never wastes a ticket."""
        if not self.tickets_open() or self.ticket_active or self.tickets_sold_out() or self.shortfall(item):
            return ""
        pool = sorted(set(TICKET_BOSS_BY_KEY) - self.tickets_won)
        self.coins -= item.coins
        self.credits -= item.credits
        self.ticket_active = random.choice(pool)
        self.flush()
        return self.ticket_active

    # -- progression gates (derived from existing state: no new unlock flag, so old saves keep exactly what they earned) ----
    def missions_open(self) -> bool:
        """Missions open once the Master (Tournament level 20) falls. Saves that already touched Missions keep them."""
        return (len(TOURNAMENT) in self.completed or bool(self.mission_completed) or bool(self.mission_paid)
                or any(g.startswith("mission:") for g in self.granted))

    def tickets_open(self) -> bool:
        """Terminal Tickets open after the Master AND the Mothership (Mission 50) are beaten. Saves already deep in the vaults keep access."""
        return ((len(TOURNAMENT) in self.completed and len(MISSIONS) in self.mission_completed) or bool(self.tickets_won)
                or bool(self.ticket_active) or self.martyr_open or self.martyr_paid or self.martyr_won)

    def progress_tier(self) -> int:
        """0 none · 1 Tournament cleared (gold) · 2 Missions cleared (green) · 3 every vault boss beaten (void) · 4 the Martyr beaten (astral + gold)."""
        if self.martyr_won:
            return 4
        if self.tickets_sold_out():
            return 3
        if len(MISSIONS) in self.mission_completed:
            return 2
        return 1 if len(TOURNAMENT) in self.completed else 0

    def progress_counts(self) -> dict:
        """{'tanks': (owned, total), 'ammo': ..., 'maps': ..., 'screens': ...} for profile cards."""
        def count(prefix: str, base: int) -> tuple:
            us = [u for u in UNLOCKABLES if u.uid.startswith(prefix)]
            return base + sum(1 for u in us if self.is_unlocked(u.uid)), base + len(us)
        return {"tanks": count("tank:", BASE_KITS), "ammo": count("ammo:", BASE_KITS), "maps": count("map:", len(MAPS)), "screens": count("theme:", 1)}

    def paint_ok(self, name: str, hull: bool) -> bool:
        """Animated paints need their unlock; the plain 24 colours are always fine."""
        need = PAINT_UNLOCK.get(name)
        return need is None or self.is_unlocked(need[0 if hull else 1])

    def hover_open(self) -> bool:
        """The Workshop HOVER upgrade opens once the Mothership (Mission 50) falls. Tanks already built with hover keep it."""
        return len(MISSIONS) in self.mission_completed

    def workshop_open(self) -> bool:
        """The Workshop opens after Tournament level 5. Saves that already built a tank (or are past level 5) keep it."""
        return 5 in self.completed or bool(self.custom_tanks) or any(n > 5 for n in self.completed)

    def blessing_unlocked(self) -> bool:
        """Martyr's Blessing is earned only by defeating the Martyr (the flag is set together with the other Martyr rewards)."""
        return self.martyr_won

    def hear(self, key: str) -> bool:
        """True exactly once per story whisper: marks it heard and saves."""
        if key in self.story:
            return False
        self.story.add(key)
        self.flush()
        return True

    def martyr_available(self) -> bool:
        return self.tickets_sold_out() or self.martyr_open

    def buy_martyr(self, item: "ShopItem") -> bool:
        if not self.martyr_available() or self.martyr_paid or self.shortfall(item):
            return False
        self.coins -= item.coins
        self.credits -= item.credits
        self.martyr_paid = True
        self.flush()
        return True

    def mission_unlocked(self, n: int) -> bool:
        return n == 1 or (n - 1) in self.mission_completed or f"mission:{n}" in self.granted

    def complete_mission(self, n: int) -> bool:
        """Records a cleared mission. Returns True if this was its first clear."""
        first = n not in self.mission_completed
        self.mission_completed.add(n)
        self.mission_paid.add(n)
        self.sanitize_loadouts()
        self.flush()
        return first

    def level_unlocked(self, n: int) -> bool:
        return n == 1 or (n - 1) in self.completed or f"level:{n}" in self.granted

    def is_unlocked(self, uid: str) -> bool:
        if uid.startswith("level:"):
            return self.level_unlocked(int(uid[6:]))
        if uid.startswith("mission:"):
            return self.mission_unlocked(int(uid[8:]))
        if uid == "ticket":                                  # "owned" means sold out
            return self.tickets_sold_out()
        if uid == "timemachine":                             # "owned" means the Martyr has been beaten
            return self.martyr_won
        if uid == "ammo:" + BLESSING_KEY:                    # only ever the Martyr's reward - never granted, bought or cheated
            return self.blessing_unlocked()
        return uid in self.granted or uid in self.earned()

    def grant(self, uid: str) -> bool:
        """Hands out one unlockable (cheat codes). True only if it was new. Never touches the wallet."""
        if uid == "ammo:" + BLESSING_KEY or uid not in {u.uid for u in UNLOCKABLES} or self.is_unlocked(uid):
            return False
        self.granted.add(uid)
        self.sanitize_loadouts()
        return True

    def grant_all(self) -> int:
        """Grants every registered unlockable (levels become open to play, none are marked cleared). No currency."""
        n = sum(self.grant(u.uid) for u in unlockables())
        self.flush()
        return n

    def _keys(self, kind: str) -> set:
        have = self.granted | self.earned()
        return {u[len(kind) + 1:] for u in have if u.startswith(kind + ":")}

    def unlocked_tanks(self) -> set:
        return {d.key for d in DESIGNS[:BASE_KITS]} | self._keys("tank") | {f"custom:{r['id']}" for r in self.custom_tanks}

    def create_custom(self, parts: dict, name: str, lore: str, hover: bool = False) -> str:
        """Builds a custom tank for CUSTOM_TANK_FEE coins (+ the HOVER upgrade if asked). Returns '' on success, else the reason."""
        if len(self.custom_tanks) >= CUSTOM_TANK_MAX:
            return "WORKSHOP FULL - DELETE A TANK FIRST"
        if hover and not self.hover_open():
            return "HOVER OPENS AFTER YOU DEFEAT THE MOTHERSHIP"
        cost, cred = CUSTOM_TANK_FEE + (HOVER_COINS if hover else 0), HOVER_CREDITS if hover else 0
        if self.coins < cost:
            return f"NEED {cost - self.coins:,} MORE COINS"
        if self.credits < cred:
            return f"NEED {cred - self.credits} MORE CREDITS FOR HOVER"
        have = workshop_components(self)
        if any(parts.get(s) not in have[s] for s in CUSTOM_SLOTS if s != "ambient") or \
                any(a not in have["ambient"] for a in parts.get("ambient", "none").split("+")):
            return "A CHOSEN PART IS NOT UNLOCKED"
        rec = {"fmt": CUSTOM_FMT, "id": "c" + "".join(random.choice("0123456789abcdef") for _ in range(10)), "name": name, "lore": lore,
               "parts": dict(parts), "created": time.strftime("%Y-%m-%d"), "game": __version__}
        if hover:
            rec["hover"] = True
        self.custom_tanks.append(rec)
        register_custom(rec)
        self.coins -= cost
        self.credits -= cred
        self.flush()
        return ""

    def delete_custom(self, cid: str) -> None:
        self.custom_tanks = [r for r in self.custom_tanks if r.get("id") != cid]
        CUSTOM_DESIGNS.pop(f"custom:{cid}", None)
        self.sanitize_loadouts()
        self.flush()

    def unlocked_ammo(self) -> set:
        out = {a.key for a in AMMOS[:BASE_KITS]} | self._keys("ammo")
        out.discard(BLESSING_KEY)
        return out | ({BLESSING_KEY} if self.blessing_unlocked() else set())

    def unlocked_maps(self) -> list:
        return [m for m in SPECIAL_MAPS if self.is_unlocked(f"map:{m.key}")]

    @property
    def master_unlocked(self) -> bool:
        return self.is_unlocked("master_difficulty")

    def home_modes(self) -> list:
        return [k for k in HOME_ORDER if k == "CLASSIC" or self.is_unlocked(f"theme:{k.lower()}")]

    def complete_level(self, n: int) -> bool:
        """Records a cleared level. Returns True if this was its first clear."""
        first = n not in self.completed
        self.completed.add(n)
        self.sanitize_loadouts()
        self.flush()
        return first

    def loadout(self, i: int) -> Loadout:
        lo = self.loadouts[i]
        if lo.tank not in self.unlocked_tanks():
            lo.tank = "ranger"
        if lo.ammo not in self.unlocked_ammo():
            lo.ammo = "standard"
        if lo.tank_color not in COLOR_BY_NAME or not self.paint_ok(lo.tank_color, True):
            lo.tank_color = "CYAN"
        if lo.shot_color not in COLOR_BY_NAME or not self.paint_ok(lo.shot_color, False):
            lo.shot_color = "YELLOW"
        return lo

    def sanitize_loadouts(self) -> None:
        for i in range(2):
            self.loadout(i)

    # -- settings ------------------------------------------------------------
    def capture_settings(self, s: Settings) -> None:
        for name, attr, choices, _ in SETTING_ROWS:
            cur = getattr(s, attr)
            label = next((l for l, v in choices if v == cur), None)
            if label is not None:
                self.settings[name] = label

    def apply_settings(self, s: Settings) -> None:
        for name, attr, choices, _ in SETTING_ROWS:
            label = self.settings.get(name)
            for l, v in choices:
                if l == label:
                    setattr(s, attr, v)
        if not self.master_unlocked and s.difficulty is Difficulty.MASTER:   # locked content can never leak in via a settings file
            s.difficulty = Difficulty.NORMAL
        if s.home_mode not in self.home_modes():
            s.home_mode = "CLASSIC"
