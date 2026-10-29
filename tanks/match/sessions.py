"""Sessions: one match from first round to result. MatchSession is a plain match; MissionSession, TicketSession,
TournamentSession and PracticeSession change the players, the win rules, the music and where the game goes next."""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Optional, TYPE_CHECKING

from tanks.audio.director import TOURNAMENT_SONGS, map_song
from tanks.colors import RGB
from tanks.config import MAX_HP, ROUNDS_TO_WIN
from tanks.content.ammo import AMMOS
from tanks.content.maps import MAPS, MapDefinition, SPECIAL_MAP_BY_KEY
from tanks.content.missions import Mission, mission_payout
from tanks.content.paints import COLOR_BY_NAME, COLOR_CHOICES, color_index
from tanks.content.rewards import COIN_HALF, Payout, match_payout, tournament_payout
from tanks.content.tanks import BASE_KITS, DESIGNS, DESIGN_BY_KEY
from tanks.content.tickets import TICKET_BOSS_BY_KEY, TICKET_PLAYER_HP, TICKET_WIN_COINS, TICKET_WIN_CREDITS, TicketBoss
from tanks.content.tournament import TOURNAMENT, TournamentLevel
from tanks.save import Loadout
from tanks.scenes.base import Scene
from tanks.scenes.battle import BattleScene
from tanks.scenes.main_menu import MenuScene
from tanks.scenes.results import MatchResultScene, TicketResultScene
from tanks.scenes.shop import ShopScene
from tanks.scenes.tournament import TournamentResultScene, TournamentScene
from tanks.scenes.tutorial import PracticeScene, TutorialScene
from tanks.settings import Difficulty

if TYPE_CHECKING:
    from tanks.app import Application


@dataclass(frozen=True)
class PlayerSetup:
    name: str
    label: str
    tank_color: RGB
    shot_color: RGB
    is_ai: bool
    design: str = "ranger"
    ammo: str = "standard"
    hp: int = MAX_HP
    team: int = -1               # -1: its own team (plain 1v1); otherwise tanks sharing a team fight together
    owner: int = 0               # LAN owner (0 = host machine)
    diff: Optional[Difficulty] = None    # per-tank AI difficulty (defaults to the match's)
    prec: float = 1.0
    kind: str = ""               # "ufo" for the big saucer enemies
    scale: float = 1.0
    hover: float = 0.0
    shield: int = 0
    guard: bool = False


@dataclass
class MatchConfig:
    players: list
    single: bool
    difficulty: Difficulty
    mode: str = "single"
    ai_precision: float = 1.0
    target: int = ROUNDS_TO_WIN  # rounds a side must win to take the match
    label: str = ""              # e.g. "BEST OF 5" / "FIRST TO 3"
    net: object = None           # a NetLink when this match is played over LAN
    my_owner: int = 0            # which LAN seat this machine plays (0 host, 1 client)
    world_size: Optional[tuple] = None   # LAN: fixed battlefield size shared by both machines
    ai_seed: int = 0
    special_wait: int = 2        # forfeited turns needed to bank the special attack
    pick_maps: bool = False      # the loser (single player: you) picks the next battlefield every round
    ammo_fx: bool = True         # special-ammo mechanics on/off (single player: on; tournament/missions: off; two player/LAN: rule)
    special: bool = False        # two-player / LAN: the forfeit-two-turns-for-a-3-damage special attack is enabled
    blessing: bool = False       # MARTYR'S BLESSING may be fired (Single/Two Player/LAN rules only; never Tournament, Missions, Tickets or the Martyr)


class MatchSession:
    """A best-of-three match. Tournament runs subclass this and swap the scoring rules."""

    exit_label = "MAIN MENU"

    def __init__(self, config: MatchConfig, first_map: Optional[MapDefinition], seed: Optional[int]) -> None:
        self.config = config
        self.rng = random.Random(seed)
        self.wins = [0, 0]
        self.round_no = 1
        self.played: list[MapDefinition] = []
        self.current_map = first_map or self._pick_map()
        self.played.append(self.current_map)

    def _pick_map(self) -> MapDefinition:
        pool = [m for m in MAPS if m not in self.played] or list(MAPS)
        return self.rng.choice(pool)

    @property
    def starting_player(self) -> int:
        return (self.round_no - 1 + getattr(self, "first_offset", 0)) % 2     # first_offset: set by the rock-paper-scissors winner

    def round_seed(self) -> int:
        return self.rng.randrange(1 << 30)

    def record_round(self, winner: int) -> None:
        self.wins[winner] += 1

    @property
    def over(self) -> bool:
        return max(self.wins) >= self.config.target

    @property
    def champion(self) -> int:
        return 0 if self.wins[0] > self.wins[1] else 1

    def team_players(self, team: int) -> list:
        return [p for i, p in enumerate(self.config.players) if (p.team if p.team >= 0 else i) == team]

    def team_name(self, team: int) -> str:
        return " + ".join(p.name for p in self.team_players(team)) or f"TEAM {team + 1}"

    pending_map: Optional[MapDefinition] = None          # the battlefield the round's loser picked

    def on_turn_start(self, scene, tank) -> None:        # hook: boss sessions change a tank's ammo here
        pass

    def dmg_mult(self, tank) -> int:                     # hook: boss fights scale damage (huge health pools)
        return 1

    def interlude(self, app):                            # hook: a scene to show between rounds (cinematics)
        return None


    def song(self) -> str:                               # hook: the battle music (boss fights, missions and story pick their own)
        return map_song(self.current_map)

    def advance(self) -> None:
        self.round_no += 1
        self.current_map = self._pick_map()                  # always drawn, so both LAN machines keep their rngs in step
        if self.pending_map is not None:
            self.current_map, self.pending_map = self.pending_map, None
        self.played.append(self.current_map)

    # -- presentation hooks (overridden by tournament runs) -------------------
    def hud_wins(self, i: int) -> str:
        need = self.config.target
        if need > 5:
            return f"WINS {self.wins[i]}/{need}"
        return "WINS " + " ".join("●" if k < self.wins[i] else "○" for k in range(need))

    def hud_title(self) -> str:
        return f"ROUND {self.round_no}  ·  {self.current_map.name}"

    def banner_title(self) -> str:
        return f"ROUND {self.round_no}"

    def round_summary(self, winner: int) -> dict:
        names = [self.team_name(0), self.team_name(1)]
        return {"title": f"ROUND {self.round_no} COMPLETE", "headline": f"{names[winner]} WINS THE ROUND",
                "score": f"{self.wins[0]}   —   {self.wins[1]}", "sub": f"{names[0]}  vs  {names[1]}",
                "next": "MATCH DECIDED" if self.over else f"NEXT: ROUND {self.round_no + 1} - NEW BATTLEFIELD"}

    def banner_note(self) -> str:
        return ""

    payout: Optional[Payout] = None        # set once the match is over and paid out (single player only)
    paid = False
    wind_override: Optional[float] = None  # a Tournament rule can pin the wind (GALE FORCE)

    def commit(self, app: "Application") -> None:
        """Called after every round; pays out once when a single-player match ends (two-player earns nothing)."""
        if self.over and not self.paid and self.config.mode == "single":
            self.paid = True
            self.payout = match_payout(self.champion == 0, self.config.difficulty)
            app.save.earn(self.payout)

    def finish_scene(self, app: "Application") -> "Scene":
        return MatchResultScene(app, self)

    def exit_scene(self, app: "Application") -> "Scene":
        return MenuScene(app)

    def restart(self, app: "Application") -> None:
        app.start_match(self.config, self.played[0] if not app.settings.random_maps else None, self.wind_override, rps=False)


def mission_foe(rng: random.Random, diff: Difficulty, prec: float, avoid: set, name: str, hp: int) -> PlayerSetup:
    """A random AI opponent built only from the starter kits, so it never depends on what a player has unlocked
    (LAN machines must build exactly the same opponent from the same seed)."""
    colors = [n for n, _ in COLOR_CHOICES if n not in avoid]
    return PlayerSetup(name, "AI", COLOR_BY_NAME[rng.choice(colors)], COLOR_BY_NAME[rng.choice(colors)], True,
                       rng.choice(DESIGNS[:BASE_KITS]).key, rng.choice(AMMOS[:BASE_KITS]).key, hp, team=1, diff=diff, prec=prec)


def ufo_setup(name: str, hp: int, diff: Difficulty, prec: float, scale: float = 3.0, color: RGB = (90, 230, 160),
              guard: bool = False) -> PlayerSetup:
    return PlayerSetup(name, "UFO", color, (170, 255, 200), True, "ranger", "xenon", hp, team=1, diff=diff, prec=prec, kind="ufo",
                       scale=scale, hover=4.0 * scale + 2.0, guard=guard)


class MissionSession(MatchSession):
    """One run at a mission. Marathons and boss rushes are several stages; the session swaps the opposition between them."""
    exit_label = "MISSIONS"

    def __init__(self, mission: Mission, config: MatchConfig, seed: Optional[int], humans: list, restart_kw: Optional[dict] = None) -> None:
        self.mission, self.humans = mission, humans
        self.stage, self.stage_cleared = 0, False
        self.committed, self.first_clear = False, False
        self.restart_kw = restart_kw
        super().__init__(config, None, seed)
        config.players = self.stage_players(0)

    # -- stages --------------------------------------------------------------
    @property
    def stage_target(self) -> int:
        m = self.mission
        return 2 if m.kind == "marathon" else m.target

    @property
    def fail_target(self) -> int:
        m = self.mission
        return 2 if m.kind == "marathon" else m.fail_at

    def stage_diff(self) -> Difficulty:
        m = self.mission
        order = (Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD, Difficulty.MASTER)
        if m.kind == "marathon" and m.stages > 1:
            a, b = order.index(m.diff), order.index(m.diff_end)
            return order[a + (b - a) * self.stage // (m.stages - 1)] if a != b else m.diff
        return m.diff

    def stage_players(self, stage: int) -> list:
        m, rng = self.mission, random.Random(self.rng.randrange(1 << 30))
        avoid = {n for n, c in COLOR_CHOICES if any(c == h.tank_color for h in self.humans)}
        foes: list = []
        if m.kind == "marathon":
            foes = [mission_foe(rng, self.stage_diff(), m.prec, avoid, f"RIVAL {stage + 1}", 3)]
        elif m.kind == "rush":
            lv = TOURNAMENT[m.levels[stage] - 1]
            foes = [replace(boss_setup(lv, color_index(next((n for n, c in COLOR_CHOICES if c == self.humans[0].tank_color), "CYAN"))),
                            team=1, hp=3, diff=lv.difficulty, prec=lv.precision)]
        elif m.kind == "mother":
            foes = [ufo_setup("MOTHERSHIP", m.ufo_hp, m.diff, m.prec * 1.2, 4.0, (120, 255, 190), guard=True),
                    ufo_setup("DRONE A", m.enemy_hp, m.diff, m.prec * 1.5, 2.0, (200, 140, 255)),
                    ufo_setup("DRONE B", m.enemy_hp, m.diff, m.prec * 1.5, 2.0, (140, 200, 255))]
        elif m.kind == "ufo" or (m.kind == "coop" and m.coop_ufo):
            foes = [ufo_setup(m.name.replace("UFO: ", ""), m.ufo_hp, m.diff, m.prec * 1.4)]
        else:
            foes = [mission_foe(rng, m.diff, m.prec * 1.3, avoid, f"ENEMY {k + 1}", m.enemy_hp) for k in range(m.enemies)]
        return list(self.humans) + foes

    def _pick_map(self) -> MapDefinition:
        m = self.mission
        key = m.map_key
        if m.kind == "rush":
            lv = TOURNAMENT[m.levels[min(self.stage, len(m.levels) - 1)] - 1]
            key = lv.map_key
        return SPECIAL_MAP_BY_KEY[key] if key else super()._pick_map()

    # -- scoring -------------------------------------------------------------
    def record_round(self, winner: int) -> None:
        self.wins[winner] += 1
        if winner == 0 and self.wins[0] >= self.stage_target and self.stage < self.mission.stages - 1:
            self.stage_cleared = True

    def advance(self) -> None:
        if self.stage_cleared:
            self.stage, self.wins, self.stage_cleared = self.stage + 1, [0, 0], False
            self.config.players = self.stage_players(self.stage)
        super().advance()

    @property
    def completed(self) -> bool:
        return self.stage == self.mission.stages - 1 and self.wins[0] >= self.stage_target

    @property
    def failed(self) -> bool:
        return self.wins[1] >= self.fail_target and not self.completed

    @property
    def over(self) -> bool:
        return self.completed or self.failed

    @property
    def champion(self) -> int:
        return 0 if self.completed else 1

    def hud_wins(self, i: int) -> str:
        m = self.mission
        if i == 1:
            return f"LOST {self.wins[1]}/{self.fail_target}"
        if m.kind == "rush":
            return f"BOSS {self.stage + 1}/{m.stages}  ·  {m.stages - self.stage - 1} AFTER THIS"
        pre = f"MATCH {self.stage + 1}/{m.stages}  " if m.stages > 1 else ""
        return f"{pre}WINS {self.wins[0]}/{self.stage_target}"

    def hud_title(self) -> str:
        return f"MISSION {self.mission.number}  ·  {self.mission.type_name}  ·  {self.current_map.name}"

    def banner_title(self) -> str:
        m = self.mission
        if m.stages > 1:
            return f"{'MATCH' if m.kind == 'marathon' else 'BOSS'} {self.stage + 1} OF {m.stages}"
        return f"MISSION {m.number} - ROUND {self.round_no}"

    def banner_note(self) -> str:
        m = self.mission
        if m.kind == "mother" and self.round_no == 1:
            return "THE MOTHERSHIP IS SHIELDED - DESTROY THE DRONES FIRST"
        if m.kind in ("marathon", "rush"):
            foe = self.config.players[-1]
            return f"VS {foe.name}" + (f"  ·  {self.stage_diff().value}" if m.kind == "marathon" else "")
        if self.wins[1] and self.wins[1] >= self.fail_target - 1:
            return "FINAL WARNING - ONE MORE LOST ROUND FAILS THE MISSION"
        return ""

    def song(self) -> str:
        m = self.mission
        if m.kind == "coop" and m.coop_ufo:
            return "saucer_attack"
        return {"ufo": "saucer_attack", "mother": "mothership", "rush": "boss_rush", "coop": "squad_up", "2v1": "squad_up"}.get(m.kind) \
            or map_song(self.current_map)

    def round_summary(self, winner: int) -> dict:
        m = self.mission
        if self.completed:
            nxt = "MISSION COMPLETE!"
        elif self.failed:
            nxt = "MISSION FAILED"
        elif self.stage_cleared:
            left = m.stages - self.stage - 1
            nxt = f"{'MATCH' if m.kind == 'marathon' else 'BOSS'} WON - {left} {'MORE' if m.kind == 'marathon' else 'BOSS' + ('ES' if left != 1 else '') + ' LEFT IN THE GAUNTLET'}".replace("MORE", "MORE TO GO")
        elif winner == 0:
            nxt = f"{self.stage_target - self.wins[0]} MORE TO GO"
        else:
            nxt = f"ROUND LOST - {self.fail_target - self.wins[1]} MORE FAILS THE MISSION"
        if m.kind == "rush":
            beaten = self.stage + (1 if (self.stage_cleared or self.completed) else 0)
            score = f"BOSSES BEATEN {beaten}/{m.stages}  ·  {m.stages - beaten} LEFT"
        elif m.kind == "marathon":
            score = f"MATCH {self.stage + 1}/{m.stages}  ·  ROUNDS {self.wins[0]}-{self.wins[1]}"
        else:
            score = f"{self.wins[0]}/{self.stage_target}  ·  LOST {self.wins[1]}/{self.fail_target}"
        return {"title": f"MISSION {m.number} - ROUND {self.round_no}",
                "headline": "YOUR TEAM WINS THE ROUND" if winner == 0 else "THE ENEMY WINS THE ROUND",
                "score": score, "sub": m.objective, "next": nxt}

    # -- results -------------------------------------------------------------
    def commit(self, app: "Application") -> None:
        if self.over and not self.committed:
            self.committed = True
            n, save = self.mission.number, app.save
            host = self.config.net is None or self.config.my_owner == 0
            if self.completed:
                self.first_clear = n not in save.mission_paid
                if host:
                    save.complete_mission(n)                 # progression counts only on the host's save
                else:                                        # LAN guest: gets the coins and the kit, not the progression step
                    save.mission_paid.add(n)
                    if self.first_clear:
                        for uid in self.mission.rewards:
                            save.grant(uid)
            self.payout = mission_payout(self.mission, self.completed, self.first_clear)
            save.earn(self.payout)

    def finish_scene(self, app: "Application") -> "Scene":
        from tanks.scenes.missions import MissionResultScene
        return MissionResultScene(app, self)

    def exit_scene(self, app: "Application") -> "Scene":
        from tanks.scenes.missions import MissionsScene
        return MissionsScene(app, self.mission.number)

    def restart(self, app: "Application") -> None:
        build_mission_session(app, self.mission, **(self.restart_kw or {"loadouts": [app.save.loadout(0)]}))


def humans_for(app, mission: Mission, loadouts: list, wingman: bool = False, guest: Optional[Loadout] = None) -> list:
    """The player-controlled (and wingman) tanks for a mission. Co-op always has two seats on team 0."""
    hp = mission.hp
    mk = lambda lo, name, label, owner=0, col=None: PlayerSetup(name, label, COLOR_BY_NAME[col or lo.tank_color],
                                                                 COLOR_BY_NAME[lo.shot_color], False, lo.tank, lo.ammo, hp, team=0,
                                                                 owner=owner)
    first = mk(loadouts[0], "PLAYER 1" if mission.is_coop else "PLAYER", "P1" if mission.is_coop else "YOU")
    if not mission.is_coop:
        return [first]
    if guest is not None or len(loadouts) > 1:
        lo2 = guest or loadouts[1]
        col = lo2.tank_color
        if col == loadouts[0].tank_color:
            col = COLOR_CHOICES[(color_index(col) + 12) % len(COLOR_CHOICES)][0]
        return [first, mk(lo2, "PLAYER 2", "P2", 1 if guest is not None else 0, col)]
    col = COLOR_CHOICES[(color_index(loadouts[0].tank_color) + 12) % len(COLOR_CHOICES)][0]       # AI wingman
    wing = PlayerSetup("WINGMAN", "AI", COLOR_BY_NAME[col], (200, 255, 200), True, "gemini", "standard", hp, team=0,
                       diff=Difficulty.NORMAL, prec=1.0)
    return [first, wing]


def build_mission_session(app, mission: Mission, loadouts: list, wingman: bool = False, guest: Optional[Loadout] = None, net=None,
                          my_owner: int = 0, world: Optional[tuple] = None, seed: Optional[int] = None, humans: Optional[list] = None,
                          go: bool = True) -> MissionSession:
    humans = humans if humans is not None else humans_for(app, mission, loadouts, wingman, guest)
    cfg = MatchConfig(list(humans), False, mission.diff, "mission", target=mission.target, ammo_fx=False, net=net, my_owner=my_owner, world_size=world)
    seed = app.rng.randrange(1 << 30) if seed is None else seed
    kw = {"loadouts": loadouts, "wingman": wingman, "guest": guest}
    s = MissionSession(mission, cfg, seed, humans, restart_kw=kw if net is None else None)
    if go:
        app.goto(BattleScene(app, s))
    return s


class TicketSession(MatchSession):
    """A Terminal Ticket boss fight: first to two rounds against one vault boss. Losing keeps the ticket active."""
    exit_label = "SHOP"

    def __init__(self, boss: TicketBoss, config: MatchConfig, seed: Optional[int]) -> None:
        self.boss, self.committed, self.first_clear = boss, False, True
        super().__init__(config, None, seed)

    def _pick_map(self) -> MapDefinition:
        return SPECIAL_MAP_BY_KEY[self.boss.map_key]

    @property
    def completed(self) -> bool:
        return self.wins[0] >= 2

    @property
    def failed(self) -> bool:
        return self.wins[1] >= 2

    @property
    def over(self) -> bool:
        return self.completed or self.failed

    @property
    def champion(self) -> int:
        return 0 if self.completed else 1

    def hud_wins(self, i: int) -> str:
        return f"WINS {self.wins[0]}/2" if i == 0 else f"LOST {self.wins[1]}/2"

    def hud_title(self) -> str:
        return f"TERMINAL TICKET  ·  {self.boss.name}  ·  {self.current_map.name}"

    def banner_title(self) -> str:
        return f"{self.boss.name} - ROUND {self.round_no}"

    def banner_note(self) -> str:
        return self.boss.taunt if self.round_no == 1 else ""

    def song(self) -> str:
        return "t_" + self.boss.key

    def round_summary(self, winner: int) -> dict:
        nxt = ("BOSS DEFEATED!" if self.completed else "TICKET BATTLE LOST - TRY AGAIN, THE TICKET IS KEPT" if self.failed
               else f"{2 - self.wins[0]} MORE TO GO" if winner == 0 else "ROUND LOST - ONE MORE FAILS THE BATTLE")
        return {"title": f"{self.boss.name} - ROUND {self.round_no}", "headline": "YOU WIN THE ROUND" if winner == 0 else f"{self.boss.name} WINS THE ROUND",
                "score": f"{self.wins[0]}/2  ·  LOST {self.wins[1]}/2", "sub": "WIN TWO ROUNDS", "next": nxt}

    def commit(self, app: "Application") -> None:
        if self.over and not self.committed:
            self.committed = True
            save = app.save
            if self.completed:
                save.tickets_won.add(self.boss.key)
                save.ticket_active = ""
                for uid in self.boss.reward_ids():
                    save.grant(uid)
                self.payout = Payout(TICKET_WIN_COINS, TICKET_WIN_CREDITS)
            else:
                self.payout = Payout(COIN_HALF)
            save.earn(self.payout)

    def finish_scene(self, app: "Application") -> "Scene":
        return TicketResultScene(app, self)

    def exit_scene(self, app: "Application") -> "Scene":
        return ShopScene(app, 4)

    def restart(self, app: "Application") -> None:
        start_ticket(app, self.boss.key)


def start_ticket(app, key: str) -> None:
    if not key or not app.save.tickets_open():               # nothing drawn / still sealed: never open a vault encounter
        app.goto(ShopScene(app, 4))
        return
    boss = TICKET_BOSS_BY_KEY.get(key)
    if boss is None:                                         # an unknown id in a save: clear it rather than getting stuck
        app.save.ticket_active = ""
        app.save.flush()
        app.goto(ShopScene(app, 4))
        return
    lo = app.save.loadout(0)
    me = PlayerSetup("PLAYER", "YOU", COLOR_BY_NAME[lo.tank_color], COLOR_BY_NAME[lo.shot_color], False, lo.tank, lo.ammo,
                     TICKET_PLAYER_HP, team=0)
    foe = PlayerSetup(boss.name, "BOSS", DESIGN_BY_KEY[boss.tank].accent, (255, 255, 255), True, boss.tank, boss.ammo, boss.hp, team=1,
                      diff=Difficulty.MASTER, prec=boss.prec)
    cfg = MatchConfig([me, foe], False, Difficulty.MASTER, "ticket", target=2)
    app.goto(BattleScene(app, TicketSession(boss, cfg, app.rng.randrange(1 << 30))))


class TournamentSession(MatchSession):
    """One run at a tournament level: win `level.wins` rounds against the boss under the level's rule."""

    exit_label = "TOURNAMENT"

    def __init__(self, level: TournamentLevel, config: MatchConfig, seed: Optional[int]) -> None:
        self.level = level
        self.first_clear = False
        self.committed = False
        super().__init__(config, None, seed)

    @property
    def wind_override(self) -> Optional[float]:
        return self.level.wind_override

    def _pick_map(self) -> MapDefinition:
        return SPECIAL_MAP_BY_KEY[self.level.map_key] if self.level.map_key else super()._pick_map()

    @property
    def strikes(self) -> int:
        s = self.level.strikes_allowed
        return 0 if s is None else min(self.wins[1], s)

    def banner_note(self) -> str:
        lv, bw = self.level, self.wins[1]
        s = lv.strikes_allowed
        if s and bw >= s:
            return "FINAL WARNING - ONE MORE LOSS FAILS THE LEVEL"
        if s and bw:
            return f"{bw} OF {s} STRIKES USED"
        if lv.rule and self.round_no == 1:
            return f"{lv.rule_tag}: {lv.rule_text}"
        if lv.consecutive and bw:
            return f"STREAK BROKEN {bw}X - BACK TO ZERO"
        return ""

    def record_round(self, winner: int) -> None:
        self.wins[winner] += 1
        if winner == 1 and self.level.consecutive:
            self.wins[0] = 0                     # a loss breaks the streak

    @property
    def completed(self) -> bool:
        return self.wins[0] >= self.level.wins

    @property
    def failed(self) -> bool:
        f = self.level.fail_at
        return f is not None and self.wins[1] >= f and not self.completed

    @property
    def over(self) -> bool:
        return self.completed or self.failed

    @property
    def champion(self) -> int:
        return 0 if self.completed else 1

    def hud_wins(self, i: int) -> str:
        lv, need = self.level, self.level.wins
        if i == 1:
            if lv.fail_at is None:
                return f"BOSS WINS {self.wins[1]}"
            if lv.fail_at == 1:
                return "NO LOSSES ALLOWED"
            s = self.strikes
            return f"BOSS {self.wins[1]}/{lv.fail_at}  STRIKES {'■' * s}{'□' * (lv.strikes_allowed - s)}"
        pips = ("●" * self.wins[0] + "○" * (need - self.wins[0])) if need <= 5 else f"{self.wins[0]}"
        return f"{'STREAK' if lv.consecutive else 'WINS'} {pips} {self.wins[0]}/{need}"

    def hud_title(self) -> str:
        tag = f"  ·  {self.level.rule_tag}" if self.level.rule else ""
        return f"LEVEL {self.level.number}  ·  ROUND {self.round_no}  ·  {self.current_map.name}{tag}"

    def banner_title(self) -> str:
        return f"LEVEL {self.level.number} - ROUND {self.round_no}"

    def song(self) -> str:
        return TOURNAMENT_SONGS[min(len(TOURNAMENT_SONGS), max(1, self.level.number)) - 1]

    def round_summary(self, winner: int) -> dict:
        lv, need = self.level, self.level.wins
        bw, f = self.wins[1], lv.fail_at
        if self.completed:
            nxt = "LEVEL CLEARED!"
        elif self.failed:
            nxt = "LEVEL FAILED - YOU LOST A ROUND" if f == 1 else f"LEVEL FAILED - {lv.boss} WON {f} ROUNDS"
        elif winner == 0:
            nxt = f"{need - self.wins[0]} MORE TO GO"
        elif lv.consecutive:
            nxt = "STREAK BROKEN - BACK TO ZERO"
        elif bw >= lv.strikes_allowed:
            nxt = f"STRIKE {lv.strikes_allowed} OF {lv.strikes_allowed} - ONE MORE LOSS FAILS THE LEVEL"
        else:
            nxt = f"STRIKE {bw} OF {lv.strikes_allowed} - WARNING"
        boss_score = f"{bw}/{f}" if f else f"{bw}"
        return {"title": f"LEVEL {lv.number} - ROUND {self.round_no}",
                "headline": "YOU WIN THE ROUND" if winner == 0 else f"{lv.boss} WINS THE ROUND",
                "score": f"{self.wins[0]}/{need}  ·  BOSS {boss_score}", "sub": lv.objective, "next": nxt}

    def commit(self, app: "Application") -> None:
        if self.over and not self.committed:
            self.committed = True
            if self.completed:
                self.first_clear = app.save.complete_level(self.level.number)
                if self.first_clear and self.level.number == len(TOURNAMENT):
                    app.settings.home_mode = "MASTER"      # reveal the Master home screen right away
                    app.apply_settings()
            self.payout = tournament_payout(self.level, self.completed, self.first_clear)
            app.save.earn(self.payout)

    def finish_scene(self, app: "Application") -> "Scene":
        return TournamentResultScene(app, self)

    def exit_scene(self, app: "Application") -> "Scene":
        return TournamentScene(app, self.level.number)

    def restart(self, app: "Application") -> None:
        app.start_tournament(self.level, self.config)


def boss_setup(level: TournamentLevel, player_color: int) -> PlayerSetup:
    bi = color_index(level.boss_color)
    if bi == player_color:
        bi = (bi + 5) % len(COLOR_CHOICES)
    return PlayerSetup(level.boss, "BOSS", COLOR_CHOICES[bi][1], COLOR_BY_NAME[level.boss_shot], True, level.tank, level.ammo)


class PracticeSession(MatchSession):
    exit_label = "THE TUTORIAL"

    def __init__(self, config: MatchConfig, mapdef, seed, lesson: int, adv: Optional[int]) -> None:
        super().__init__(config, mapdef, seed)
        self.lesson, self.adv = lesson, adv

    def song(self) -> str:
        return "tutorial"

    def exit_scene(self, app: "Application") -> "Scene":
        return TutorialScene(app, adv=self.adv is not None)

    def restart(self, app: "Application") -> None:
        app.goto(PracticeScene(app, self.lesson, self.adv))
