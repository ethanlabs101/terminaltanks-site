"""The Martyr's three-phase duel session and how it starts."""
from __future__ import annotations

from dataclasses import replace
from typing import Optional, TYPE_CHECKING

from tanks.audio.director import MARTYR_SONGS
from tanks.content.ammo import AMMOS, ANCIENT_AMMOS, BLESSING_KEY, TICKET_AMMOS
from tanks.content.maps import ANCIENT_MAPS, MapDefinition
from tanks.content.martyr import (
    ELEMENTS, MAGE_AMMO, MARTYR_MAGE_HP, MARTYR_MAGE_MULT, MARTYR_PHASES, MARTYR_PLAYER_HP_BY_PHASE, MARTYR_PLAYER_MULT,
    MARTYR_PREC, MARTYR_REWARD_IDS, MARTYR_TAUNT, MARTYR_WIN_COINS, PHASE_ELEMENTS
)
from tanks.content.paints import COLOR_BY_NAME
from tanks.content.rewards import Payout
from tanks.content.story import MARTYR_BETWEEN, MARTYR_INTRO, MARTYR_OUTRO, MARTYR_PHASE0
from tanks.content.tanks import BASE_KITS
from tanks.match.sessions import MatchConfig, MatchSession, PlayerSetup
from tanks.scenes.base import Scene
from tanks.scenes.battle import BattleScene
from tanks.scenes.martyr import MartyrRewardsScene
from tanks.scenes.shop import ShopScene
from tanks.scenes.story import CinematicScene, whisper
from tanks.settings import Difficulty
from tanks.ui.hud import FloatText

if TYPE_CHECKING:
    from tanks.app import Application


def start_martyr(app, intro: bool = False, replay: bool = False) -> None:
    save = app.save
    ph = 0 if replay else min(2, save.martyr_phase)
    lo = save.loadout(0)
    me = PlayerSetup("PLAYER", "YOU", COLOR_BY_NAME[lo.tank_color], COLOR_BY_NAME[lo.shot_color], False, lo.tank, lo.ammo, MARTYR_PLAYER_HP_BY_PHASE[ph], team=0)
    mage = PlayerSetup("THE MARTYR", "MAGE", (190, 150, 255), (255, 240, 170), True, "a_martyr", "timerift", MARTYR_MAGE_HP[ph], team=1,
                       diff=Difficulty.MASTER, prec=MARTYR_PREC[ph])
    cfg = MatchConfig([me, mage], False, Difficulty.MASTER, "martyr", target=3, ammo_fx=True, special=True, special_wait=1)
    sess = MartyrSession(cfg, app.rng.randrange(1 << 30), ph, replay)

    def go():
        save.martyr_seen = True
        save.flush()
        app.goto(BattleScene(app, sess))
    pages = (MARTYR_INTRO if not save.martyr_seen else []) + (MARTYR_BETWEEN[ph] if ph > 0 else MARTYR_PHASE0)
    if not replay and not save.martyr_seen:
        whisper(app, "hoarders", lambda: app.goto(CinematicScene(app, pages, go)))     # saves that finished the vaults earlier still hear it
    else:
        app.goto(CinematicScene(app, pages, go))


class MartyrSession(MatchSession):
    """Three escalating phases against the Martyr. Losing a phase repeats it; clearing one is saved."""
    exit_label = "SHOP"

    def __init__(self, config: MatchConfig, seed: Optional[int], phase: int = 0, replay: bool = False) -> None:
        self.phase_i, self.won_phase, self.committed, self.replay = phase, False, False, replay
        super().__init__(config, None, seed)
        self.wins[0] = phase
        self._set_mage()

    def _set_mage(self) -> None:
        p = min(self.phase_i, 2)
        self.config.players[0] = replace(self.config.players[0], hp=MARTYR_PLAYER_HP_BY_PHASE[p])
        self.config.players[1] = replace(self.config.players[1], hp=MARTYR_MAGE_HP[p], prec=MARTYR_PREC[p])

    def _pick_map(self) -> MapDefinition:
        return ANCIENT_MAPS[min(self.phase_i, 2)]

    @property
    def completed(self) -> bool:
        return self.wins[0] >= 3

    @property
    def failed(self) -> bool:
        return False

    @property
    def over(self) -> bool:
        return self.completed

    @property
    def champion(self) -> int:
        return 0

    def record_round(self, winner: int) -> None:
        self.won_phase = winner == 0
        if winner == 0:
            self.wins[0] += 1

    def advance(self) -> None:
        self.round_no += 1
        if self.won_phase:
            self.phase_i = min(2, self.phase_i + 1)
        self._set_mage()
        self.current_map = self._pick_map()
        self.played.append(self.current_map)

    def interlude(self, app):
        if not self.won_phase:
            return None
        return CinematicScene(app, MARTYR_BETWEEN[self.phase_i], lambda: app.goto(BattleScene(app, self)))

    def on_turn_start(self, scene, tank) -> None:
        if tank.index != 1:
            return
        el = scene.srng.choice(PHASE_ELEMENTS[min(self.phase_i, 2)])
        a = MAGE_AMMO[(el, min(self.phase_i, 2))]
        name = ELEMENTS[el][0]
        if scene.srng.random() < 0.7:                               # most turns he draws from EVERY special ammo there is
            pool = [x for x in AMMOS[BASE_KITS:] + TICKET_AMMOS + ANCIENT_AMMOS if x.key != BLESSING_KEY]
            a = scene.srng.choice(pool)
            name = a.name
        tank.ammo, tank.shot_color = a, ELEMENTS[el][4]
        scene.floaters.append(FloatText(tank.x, tank.y + tank.height + 14, name + "!", ELEMENTS[el][4]))

    def dmg_mult(self, tank) -> int:
        return MARTYR_PLAYER_MULT if tank.index == 0 else MARTYR_MAGE_MULT[min(self.phase_i, 2)]

    def hud_wins(self, i: int) -> str:
        return f"PHASE {min(3, self.phase_i + 1)}/3" if i == 0 else "THE MARTYR"

    def hud_title(self) -> str:
        return f"MARTYR'S TIME MACHINE  ·  {MARTYR_PHASES[min(self.phase_i, 2)]}  ·  {self.current_map.name}"

    def banner_title(self) -> str:
        return MARTYR_PHASES[min(self.phase_i, 2)]

    def banner_note(self) -> str:
        return MARTYR_TAUNT[min(self.phase_i, 2)]

    def song(self) -> str:
        return MARTYR_SONGS[min(self.phase_i, 2)]

    def round_summary(self, winner: int) -> dict:
        nxt = ("THE MARTYR FALLS." if self.completed else f"NEXT: {MARTYR_PHASES[min(self.phase_i + 1, 2)]}" if winner == 0
               else "YOU FALL - THE PHASE IS REPEATED. YOUR PROGRESS IS SAVED.")
        return {"title": MARTYR_PHASES[min(self.phase_i, 2)], "headline": "PHASE CLEARED" if winner == 0 else "THE MARTYR PREVAILS",
                "score": f"PHASES CLEARED {self.wins[0]}/3",
                "sub": "ESCALATING: HIS POWER GROWS EACH PHASE" if winner == 0 else "TIP: USE SPECIAL AMMO - TRY ARMAGEDDON IN THE SHOP", "next": nxt}

    def commit(self, app: "Application") -> None:
        save = app.save
        if self.won_phase and not self.completed and not self.replay:
            save.martyr_phase = max(save.martyr_phase, self.wins[0])
            save.flush()
        if self.completed and not self.committed:
            self.committed = True
            if not self.replay:
                save.martyr_won, save.martyr_phase = True, 3
                for uid in MARTYR_REWARD_IDS:
                    save.grant(uid)
                self.payout = Payout(MARTYR_WIN_COINS)
                save.earn(self.payout)
                app.settings.home_mode = "ETERNAL"            # the masterpiece is waiting on the main screen
                app.apply_settings()
            save.flush()

    def finish_scene(self, app: "Application") -> "Scene":
        if self.replay:
            return ShopScene(app, 4)
        return CinematicScene(app, MARTYR_OUTRO, lambda: app.goto(MartyrRewardsScene(app)))

    def exit_scene(self, app: "Application") -> "Scene":
        return ShopScene(app, 4)

    def restart(self, app: "Application") -> None:
        start_martyr(app, replay=self.replay)
