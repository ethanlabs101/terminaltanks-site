"""The tutorial: lessons and challenges in practice matches."""
from __future__ import annotations

import textwrap
from typing import Optional

from tanks.battle.physics import ImpactKind
from tanks.battle.shots import Ev
from tanks.colors import GOLD, Palette
from tanks.content.ammo import BLESSING_KEY, DEFAULT_AMMO
from tanks.content.maps import MAPS
from tanks.content.paints import COLOR_BY_NAME
from tanks.content.tournament import TOURNAMENT
from tanks.scenes.base import BackdropScene
from tanks.scenes.battle import BattleScene
from tanks.scenes.main_menu import MenuScene
from tanks.screen import Screen
from tanks.settings import Difficulty
from tanks.terminal import Action, InputEvent
from tanks.ui.hud import Phase
from tanks.ui.widgets import draw_keycaps, panel


# ---------------------------------------------------------------------------
# Interactive tutorial: a practice range (one passive, unbreakable target) + coaching panel. Reached from HOW TO PLAY (T).
# Lessons 1-4 are live practice, 5 is a rules briefing built from the game's real level/mission text, 6 is optional challenges.
# Nothing here touches the wallet, unlocks or the Tournament; the only thing saved is a "tut:N" tick in the story list.
# ---------------------------------------------------------------------------
TUT_LESSONS = (
    ("1  AIMING & POWER", "Rotate the barrel with ◄ ► (hold SHIFT for big steps), set the power with ▲ ▼, fire with SPACE or ENTER. A higher angle lobs the shell; more power sends it farther.",
     "HIT THE TARGET ONCE", "Too short? add power. Too long? lower it. Change one thing at a time."),
    ("2  WIND", "Wind pushes every shell and changes each turn. The HUD arrows show its direction and strength; the dotted aim guide ignores it.",
     "FIRE 3 SHOTS AND LAND ONE HIT", "Fire the same aim twice and compare. Aim INTO the wind to compensate."),
    ("3  AMMUNITION", "Ammo types change how a shell flies and bursts. PEBBLES makes a small blast, then three bomblets. Marked ✦ in pilot setup = real effects.",
     "LAND A HIT WITH PEBBLES", "Effects are live in Single/Two Player and LAN (SPECIAL AMMO rule); Tournament and Missions keep ammo cosmetic."),
    ("4  TERRAIN", "Every blast digs a crater and the ground falls away. Dig a lane through a hill, or undermine a tank so it drops.",
     "DIG 2 CRATERS, THEN HIT THE TARGET", "Craters change future shots: a shell now rolls into the hole. Some ammo (MUDBALL, BORER) builds or drills instead."),
)
TUT_CHALLENGES = (                 # (name, ammo, wind, shots-in-a-row needed)
    ("GALE SNIPER: 3 hits in a row in a strong wind", "standard", 10.0, 3),
    ("WIND-PROOF: SLUG ammo, 3 hits in a row", "slug", 10.0, 3),
    ("LOB SHOT: floaty LOB ammo, 2 hits in a row", "lob", 6.0, 2),
)


class PracticeScene(BattleScene):
    """Practice range. The target never fires, never dies and nobody earns anything; the coach panel explains each lesson."""

    def __init__(self, app, lesson: int, adv: Optional[int] = None) -> None:
        from tanks.match.sessions import MatchConfig, PlayerSetup, PracticeSession
        lo = app.save.loadout(0)
        ammo = lo.ammo if lo.ammo != BLESSING_KEY else DEFAULT_AMMO.key
        wind = 0.0
        if adv is not None:
            ammo, wind = TUT_CHALLENGES[adv][1], TUT_CHALLENGES[adv][2]
        elif lesson == 2:
            wind = 8.0
        elif lesson == 3:
            ammo = "pebbles"
        elif lesson != 1 and lesson != 4:
            ammo = DEFAULT_AMMO.key
        if adv is None and lesson in (1, 2, 4):
            ammo = DEFAULT_AMMO.key
        me = PlayerSetup("PLAYER", "YOU", COLOR_BY_NAME[lo.tank_color], COLOR_BY_NAME[lo.shot_color], False, "ranger" if lo.tank not in app.save.unlocked_tanks() else lo.tank,
                         ammo, 9)
        tgt = PlayerSetup("TARGET", "TGT", COLOR_BY_NAME["ORANGE"], COLOR_BY_NAME["PINK"], True, "ranger", DEFAULT_AMMO.key, 9)
        cfg = MatchConfig([me, tgt], True, Difficulty.EASY, "single", target=99, ammo_fx=True, blessing=False)
        sess = PracticeSession(cfg, MAPS[0], app.rng.randrange(1 << 30), lesson, adv)
        sess.wind_override = wind
        super().__init__(app, sess)
        self.lesson, self.adv = lesson, adv
        self.shots = self.hits = self.streak = self.craters = 0
        self.note, self.first_x, self.coach, self.done = "FIRE WHEN READY", None, True, False
        self._ver = None

    # --- turn flow: the player always shoots again; the target is restored after every shot ---
    def _begin_turn(self, volley: bool = False) -> None:
        self.turn = 0
        super()._begin_turn(volley)

    def _start_event(self, ev: Ev) -> None:
        if ev.first and ev.kind is not ImpactKind.OUT:
            self.first_x = ev.x
        super()._start_event(ev)

    def _end_turn(self) -> None:
        w = self.world
        me, tgt = w.tanks[0], w.tanks[1]
        hit = tgt.hp < tgt.max_hp
        self.shots += 1
        self.hits += int(hit)
        self.streak = self.streak + 1 if hit else 0
        ver = w.terrain.version
        if self._ver is not None and ver != self._ver:
            self.craters += 1
        self._ver = ver
        if hit:
            self.note = "DIRECT HIT!"
        elif self.first_x is None:
            self.note = "OUT OF BOUNDS - try less power"
        else:
            err = (self.first_x - tgt.x) * (1 if tgt.x >= me.x else -1)
            self.note = f"{'LONG' if err > 0 else 'SHORT'} by {abs(err):.0f} - " + ("lower the power or angle" if err > 0 else "add power")
        self.first_x = None
        me.hp, tgt.hp = me.max_hp, tgt.max_hp
        tgt.charge = me.charge = 0
        self.doomed, self.doomed_more = None, []
        w.drift_wind()
        self._begin_turn()

    # --- goals ---
    def _goal_met(self) -> bool:
        if self.adv is not None:
            return self.streak >= TUT_CHALLENGES[self.adv][3]
        return {1: self.hits >= 1, 2: self.shots >= 3 and self.hits >= 1, 3: self.hits >= 1, 4: self.craters >= 2 and self.hits >= 1}[self.lesson]

    def update(self, dt: float) -> None:
        super().update(dt)
        if not self.done and self._goal_met():
            self.done = True
            self.app.save.hear(f"tut:{self.lesson if self.adv is None else 6}")

    def handle(self, ev: InputEvent) -> None:
        if self.phase is Phase.AIMING and ev.raw in ("t", "T"):
            self.coach = not self.coach
        elif self.phase is Phase.AIMING and self.done and ev.raw in ("n", "N"):
            if self.adv is not None or self.lesson >= 4:
                self.app.goto(TutorialScene(self.app, adv=self.adv is not None))
            else:
                self.app.goto(PracticeScene(self.app, self.lesson + 1))
        else:
            super().handle(ev)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        if not self.coach or self.layout is None:
            return
        L = self.layout
        if self.adv is not None:
            name, goal, tip = "CHALLENGE", TUT_CHALLENGES[self.adv][0].upper(), "Streaks reset on a miss. Wind shifts every turn."
            body, prog = "Practice what you learned. No rewards - just bragging rights.", f"STREAK {self.streak}/{TUT_CHALLENGES[self.adv][3]}"
        else:
            name, body, goal, tip = TUT_LESSONS[self.lesson - 1]
            prog = f"SHOTS {self.shots}  HITS {self.hits}" + (f"  CRATERS {self.craters}" if self.lesson == 4 else "")
        w = min(L.fcols - 2, 74 if L.frows >= 26 else 96)       # short terminals: a wider, shallower coach box
        tw = w - 4
        lines = [(ln, Palette.WHITE) for ln in textwrap.wrap(body, tw)]
        lines += [(ln, GOLD) for ln in textwrap.wrap("GOAL: " + goal + "   " + prog, tw)]
        if self.done:
            lines += [(ln, Palette.OK) for ln in textwrap.wrap("DONE!  [N] " + ("BACK TO LESSONS" if self.adv is not None or self.lesson >= 4
                                                                                  else "NEXT LESSON") + "  ·  keep practising if you like", tw)]
        else:
            lines += [(ln, Palette.AMBER) for ln in textwrap.wrap(self.note, tw)] + [(ln, Palette.MUTED) for ln in textwrap.wrap(tip, tw)]
        h = len(lines) + 2
        self.coach_h = h
        x, y = L.fx + 1, L.fy + 1
        screen.fill(x, y, w, h, Palette.PANEL)
        screen.text(x + 2, y, f" TUTORIAL · {name} ", GOLD, Palette.PANEL)
        for k, (ln, c) in enumerate(lines):
            screen.text(x + 2, y + 1 + k, ln, c, Palette.PANEL)
        screen.text(x + w - 22, y + h - 1, " [T] HIDE  [ESC] MENU ", Palette.MUTED, Palette.PANEL)


class TutorialScene(BackdropScene):
    """Lesson picker. ESC always returns to HOW TO PLAY / the main menu - nothing here is mandatory."""

    def __init__(self, app, adv: bool = False) -> None:
        super().__init__(app)
        self.adv, self.sel, self.page5 = adv, 0, False

    def _items(self) -> list:
        if self.adv:
            return [c[0] for c in TUT_CHALLENGES] + ["BACK"]
        return [l[0] for l in TUT_LESSONS] + ["5  BOSS MECHANICS", "6  ADVANCED PRACTICE (OPTIONAL)", "BACK"]

    def handle(self, ev: InputEvent) -> None:
        items = self._items()
        if self.page5:
            if ev.confirm or ev.action is Action.BACK:
                self.page5 = False
                self.app.save.hear("tut:5")
            return
        if ev.action is Action.BACK:
            self.app.goto(TutorialScene(self.app) if self.adv else MenuScene(self.app))
        elif ev.action is Action.UP:
            self.sel = (self.sel - 1) % len(items)
        elif ev.action is Action.DOWN:
            self.sel = (self.sel + 1) % len(items)
        elif ev.confirm or ev.action in (Action.CONFIRM, Action.FIRE):
            lab = items[self.sel]
            if lab == "BACK":
                self.app.goto(TutorialScene(self.app) if self.adv else MenuScene(self.app))
            elif self.adv:
                self.app.goto(PracticeScene(self.app, 6, self.sel))
            elif self.sel < 4:
                self.app.goto(PracticeScene(self.app, self.sel + 1))
            elif self.sel == 4:
                self.page5 = True
            else:
                self.app.goto(TutorialScene(self.app, adv=True))

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        sv = self.app.save
        if self.page5:
            x, y = panel(screen, 84, 24, "TUTORIAL  ·  5  BOSS MECHANICS")
            lines = [("Some opponents break the normal rules. Read what the game tells you:", Palette.TEXT),
                     ("• The ROUND BANNER names the fight and any special rule before you fire.", Palette.TEXT),
                     ("• Floating messages explain events: SHIELD ABSORBED, SHIELDS UP, VOLLEY!, CHARGING...", Palette.TEXT),
                     ("• Saucers hop between turns, raise shields as they are hurt and fire 3-shot volleys; direct hits count double.", Palette.TEXT),
                     ("TOURNAMENT RULE TAGS (real examples from the level cards):", Palette.AMBER)]
            seen: set = set()
            for lv in TOURNAMENT:
                if lv.rule not in seen and lv.rule:
                    seen.add(lv.rule)
                    lines.append((f"  {lv.rule_tag:<13} {lv.rule_text}", GOLD))
            lines += [("  STANDARD      " + TOURNAMENT[1].rule_text, GOLD),
                      ("EXERCISE: open TOURNAMENT and read the rule line on any level card before you start it.", Palette.AMBER),
                      ("Boss kits are the kit you unlock by winning. Later bosses add their own mechanics - the banner always tells you.", Palette.TEXT)]
            row = y + 2
            for t_, c in lines:
                for ln in textwrap.wrap(t_, 76):
                    screen.text(x + 4, row, ln, c, Palette.PANEL)
                    row += 1
            screen.center(y + 22, "[ ENTER ] BACK", Palette.PRIMARY_DIM, Palette.PANEL, x, 84)
            return
        x, y = panel(screen, 70, 20, "TUTORIAL  ·  ADVANCED PRACTICE" if self.adv else "TUTORIAL")
        screen.center(y + 1, "Optional. Practice range: no rewards, nothing can be lost." if not self.adv else "Optional challenges for a keen eye.", Palette.MUTED, Palette.PANEL, x, 70)
        for i, lab in enumerate(self._items()):
            sel = i == self.sel
            done = (not self.adv and i < 6 and f"tut:{i + 1}" in sv.story) or (self.adv and i < len(TUT_CHALLENGES) and "tut:6" in sv.story and False)
            screen.text(x + 6, y + 3 + i * 2, ("▶ " if sel else "  ") + lab, GOLD if sel else Palette.TEXT, Palette.PANEL)
            if done:
                screen.text(x + 62, y + 3 + i * 2, "✓", Palette.OK, Palette.PANEL)
        draw_keycaps(screen, x + 8, y + 18, (("▲▼", "CHOOSE"), ("ENTER", "START"), ("ESC", "BACK")), Palette.PANEL)
