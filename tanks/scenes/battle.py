"""The battle screen: turns, aiming, firing, flights, impacts, the HUD, pause and leaving a match."""
from __future__ import annotations

import math
import random
from dataclasses import replace
from typing import Optional, TYPE_CHECKING

from tanks.art.projectiles import draw_projectile, draw_ufo
from tanks.art.tanks import draw_tank
from tanks.battle.ai import AIController, AimPlan
from tanks.battle.effects import Explosion
from tanks.battle.physics import Impact, ImpactKind, Projectile, TraceResult, advance_projectile
from tanks.battle.shots import BlessingFX, Ev, LiveFlight, make_ammo_launch, plan_shot
from tanks.battle.tank import Tank
from tanks.battle.world import BattleWorld
from tanks.colors import GOLD, Palette, clamp, ease_in_out, gradient, lerp, mix
from tanks.config import COARSE_STEP, HUD_BOTTOM_ROWS, HUD_TOP_ROWS, MAX_FIELD_COLS, MAX_FIELD_ROWS, PHYS
from tanks.content.ammo import BLESSING_KEY, DEFAULT_AMMO
from tanks.content.paints import PIXEL_PAINTS
from tanks.scenes.base import Scene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.hud import Banner, FloatText, Layout, Phase, ScreenShake
from tanks.ui.widgets import MenuList, draw_bar, draw_hp, draw_keycaps, hearts, panel, wallet_text

if TYPE_CHECKING:
    from tanks.match.sessions import MatchSession


class BattleScene(Scene):
    show_wallet = False
    ambient = True
    INTRO_TIME = 1.8

    def music(self):
        return (self.session.song(), "battle")

    def __init__(self, app, session: MatchSession) -> None:
        super().__init__(app)
        try:
            app.audio.prep(["song:" + session.song()])     # start rendering during the fade, so the fight opens on its music
        except Exception:
            pass
        self.session = session
        self.world: Optional[BattleWorld] = None
        self.phase = Phase.INTRO
        self.t = 0.0
        self.turn = 0
        self.order: list = []
        self.trace: Optional[TraceResult] = None
        self.ais: dict = {}
        self._aim_sent = None
        self._aim_timer = 0.0
        self.proj: Optional[Projectile] = None
        self.flights: list = []
        self.special_shot = False
        self.blessing_shot, self.bless, self._bless_blocked = False, None, False
        self._off: list = []
        self._fx_warned: set = set()
        self.pending: list = []
        self.ev: Optional[Ev] = None
        self.victims: list = []
        self.doomed_more: list = []
        self.shake = ScreenShake()
        self.floaters: list[FloatText] = []
        self.banner: Optional[Banner] = None
        self.flash = 0.0
        self.guide: list = []
        self.guide_key = None
        self.plan: Optional[AimPlan] = None
        self.plan_from = (0.0, 0.0)
        self.doomed: Optional[Tank] = None
        self.impact: Optional[Impact] = None
        self.flags: set = set()
        self.size = (0, 0)
        self.wiped = False
        self.finished = False
        self.layout: Optional[Layout] = None

    # -- setup ---------------------------------------------------------------
    def enter(self) -> None:
        self._build()
        cfg = self.session.config
        for t, pl in zip(self.world.tanks, cfg.players):
            if t.is_ai:
                self.ais[t.index] = AIController(pl.diff or cfg.difficulty, random.Random(self.session.rng.randrange(1 << 30)),
                                                 cfg.ai_precision * pl.prec)
        m = self.session.current_map
        wt = self._wind_text()
        sub = m.name + (f"   ·   {wt}" if wt else "")
        if not cfg.ammo_fx and any(t.ammo.mechanics for t in self.world.tanks if not t.is_ai):
            sub += "   ·   SPECIAL AMMO OFF"
        if self._bless_blocked:
            sub += "   ·   MARTYR'S BLESSING OFF HERE"
        note = self.session.banner_note()
        warn = note.startswith("FINAL")
        self.banner = Banner(self.session.banner_title(), f"{note}   ·   {sub}" if note else sub,
                             Palette.DANGER if warn else Palette.PRIMARY, self.INTRO_TIME * (1.4 if warn else 1.0))

    def _layout(self) -> Layout:
        s = self.app.screen
        fc = min(s.cols, MAX_FIELD_COLS)
        fr = max(8, min(s.rows - HUD_TOP_ROWS - HUD_BOTTOM_ROWS, MAX_FIELD_ROWS))
        if self.session.config.world_size:                  # LAN: both machines draw the same fixed-size battlefield
            fc, fr = self.session.config.world_size[0], self.session.config.world_size[1] // 2
        top = max(0, (s.rows - (fr + HUD_TOP_ROWS + HUD_BOTTOM_ROWS)) // 2)
        return Layout(s.cols, s.rows, (s.cols - fc) // 2, top + HUD_TOP_ROWS, fc, fr, top)

    def _build(self) -> None:
        self.layout = L = self._layout()
        self.size = (self.app.screen.cols, self.app.screen.rows)
        s = self.app.settings
        wo = self.session.wind_override
        if isinstance(wo, (tuple, list)):                    # a match WIND band (min, max)
            s = replace(s, wind=float(wo[1]), wind_min=float(wo[0]))
        elif wo is not None:                                 # GALE FORCE etc.: a private settings copy with the wind pinned high
            s = replace(s, wind=float(wo), wind_min=0.0)
        self.cfg_settings = s
        size = self.session.config.world_size or (L.fcols, L.frows * 2)
        seed = self.session.round_seed()
        self.world = BattleWorld(size[0], size[1], self.session.current_map, seed, self.session.config.players, s)
        self.world.ammo_fx = self.session.config.ammo_fx
        if not self.session.config.blessing:
            for i, (tk, pl) in enumerate(zip(self.world.tanks, self.session.config.players)):
                if pl.ammo == BLESSING_KEY:                              # PlayerSetup is frozen: swap in a corrected copy
                    self.session.config.players[i] = replace(pl, ammo=DEFAULT_AMMO.key)
                    tk.ammo = DEFAULT_AMMO
                    self._bless_blocked = True
        self.srng = random.Random(seed ^ 0xA11E)              # scene-level decisions every LAN machine must repeat identically
        self._make_order()

    def _check_resize(self) -> None:
        if self.size != (self.app.screen.cols, self.app.screen.rows):
            self.layout = L = self._layout()
            self.size = (self.app.screen.cols, self.app.screen.rows)
            if self.session.config.world_size is None and (L.fcols, L.frows * 2) != (self.world.width, self.world.height):
                self.world.resize(L.fcols, L.frows * 2)
                self.guide_key = None
                if self.phase in (Phase.FLIGHT, Phase.IMPACT):
                    self.proj = None
                    self._end_turn()

    # -- helpers -------------------------------------------------------------
    def _turn_text(self, i: int) -> str:
        t = self.world.tanks[i]
        if t.kind == "ufo":
            return "UFO TURN"
        if t.is_ai:
            n = sum(1 for x in self.world.tanks if x.is_ai)
            return "AI TURN" if n == 1 else f"AI {sum(1 for x in self.world.tanks[:i + 1] if x.is_ai)} TURN"
        humans = [x for x in self.world.tanks if not x.is_ai]
        if len(humans) == 1:
            return "PLAYER TURN"
        return f"PLAYER {humans.index(t) + 1} TURN"

    @property
    def current(self) -> Tank:
        return self.world.tanks[self.turn]

    def _make_order(self) -> None:
        """Turn order: teams alternate, tanks inside a team take turns in seat order."""
        tanks = self.world.tanks
        lists = [[t.index for t in tanks if t.team == tm] for tm in sorted({t.team for t in tanks})]
        start = self.session.starting_player % len(lists)
        lists = lists[start:] + lists[:start]
        self.order = [l[k] for k in range(max(map(len, lists))) for l in lists if k < len(l)]
        self.turn = self.order[0]

    def _pan(self, x: float) -> float:
        return clamp((x / max(1, self.world.width) - 0.5) * 1.2, -1.0, 1.0)

    def _prep_audio(self) -> None:
        items = ["song:" + self.session.song()]
        for t in self.world.tanks:
            items += ["sfx:fire:" + t.ammo.key, "sfx:hit:" + t.ammo.key]
        self.app.audio.prep(items + ["sfx:tank_hit", "sfx:tank_destroy", "sfx:debris", "sfx:turn_you", "sfx:turn_cpu"])

    def _control(self, t: Tank) -> str:
        """'local' = this keyboard, 'ai' = computed here, 'remote' = driven by the LAN peer's messages."""
        cfg = self.session.config
        if cfg.net is None:
            return "ai" if t.is_ai else "local"
        if t.is_ai:
            return "ai" if cfg.my_owner == 0 else "remote"
        return "local" if t.owner == cfg.my_owner else "remote"

    def _target_for(self, me: Tank) -> Tank:
        foes = [t for t in self.world.tanks if t.team != me.team and t.alive]
        return min(foes, key=lambda t: (abs(t.x - me.x), t.hp)) if foes else self.world.tanks[0]

    def _begin_turn(self, volley: bool = False) -> None:
        tank = self.current
        self.guide_key = None
        if not volley and self._turn_start(tank):
            self.banner = Banner("UFO CHARGING", "", tank.color, 0.8)
            self._end_turn()
            return
        if not volley:
            self.session.on_turn_start(self, tank)
        ready = self.session.config.special and tank.charge >= self.session.config.special_wait
        self.banner = Banner(self._turn_text(self.turn), "SPECIAL READY - FIRE FOR 3 DAMAGE!" if ready else self._wind_text(), tank.color,
                             0.9 if volley else 1.3)
        ctl = self._control(tank)
        if not volley:
            if not hasattr(self, "_audio_prepped"):
                self._audio_prepped = True
                self._prep_audio()
            self.app.sfx("turn_you" if ctl == "local" else "turn_cpu", 0.55)
            if abs(self.world.wind) > 6.0 and self.cfg_settings.wind > 0:
                self.app.sfx("wind_gust", min(1.0, abs(self.world.wind) / 10), self._pan(self.world.width * (0.8 if self.world.wind > 0 else 0.2)), gap=4)
        self._aim_sent = None
        cfg = self.session.config
        if (ctl == "ai" and cfg.mode == "single" and cfg.special and cfg.net is None and not volley and tank.index in self.ais
                and tank.kind != "ufo" and tank.charge < cfg.special_wait and self.srng.random() < 0.2):
            self._forfeit(tank, announce=False)                     # the CPU banks a charge now and then and later fires its special
            return
        if ctl == "ai" and tank.index in self.ais:
            self.plan = self.ais[tank.index].plan(tank, self._target_for(tank), self.world)
            self.plan_from = (tank.angle, tank.power)
            self.phase, self.t = Phase.AI_THINKING, 0.0
        else:
            self.phase, self.t = Phase.AIMING, 0.0

    def _turn_start(self, tank: Tank) -> bool:
        """Per-turn behaviour of special units. The saucer hops to a new spot, raises shields as it is hurt and, every few
        turns, fires a three-shot volley. Everything here runs off the shared scene rng so LAN machines stay in step."""
        if tank.kind != "ufo":
            return False
        w = self.world
        tank.turns += 1
        lo, hi = (0.52, 0.93) if tank.team == 1 else (0.07, 0.48)
        old, half = tank.x, int(tank.width / 2)
        others = [t for t in w.tanks if t is not tank and t.alive and t.kind == "ufo"]
        for _ in range(8):                               # a few tries to land clear of the other saucers
            cand = int(clamp(self.srng.uniform(lo, hi) * w.width, 12 + half, w.width - 13 - half)) + 0.5
            if all(abs(cand - o.x) >= (tank.width + o.width) / 2 + 3 for o in others):
                break
        tank.x = cand
        tank.vis_dx = old - tank.x
        self.app.sfx("ufo_hop", 0.7, self._pan(tank.x), gap=0.2)
        w.terrain.flatten(tank.x, 10)
        tank.y = float(w.terrain.support_height(tank.x)) + tank.hover
        frac = tank.hp / tank.max_hp
        thresholds = (0.66, 0.33)
        drone = tank.name.startswith("DRONE")             # Mothership fight: only the mothership ever shields
        while tank.phase < 2 and frac <= thresholds[tank.phase]:
            tank.phase += 1
            if drone:
                continue
            tank.shield = 2
            self.floaters.append(FloatText(tank.x, tank.y + tank.height + 8, "SHIELDS UP", (140, 230, 255)))
        if tank.turns % 2 == 1:                          # charging turn: the saucer only repositions - a breather for the player
            self.floaters.append(FloatText(tank.x, tank.y + tank.height + 14, "CHARGING...", (150, 255, 200)))
            return True
        period = 3 if frac > 0.5 else 2
        if (tank.turns // 2) % period == 0:
            tank.volley = 2
            self.app.sfx("ufo_volley", 0.9, self._pan(tank.x))
            self.floaters.append(FloatText(tank.x, tank.y + tank.height + 14, "VOLLEY!", Palette.DANGER))
        return False

    def _end_turn(self) -> None:
        pos = self.order.index(self.turn)
        for k in range(1, len(self.order) + 1):
            i = self.order[(pos + k) % len(self.order)]
            if self.world.tanks[i].alive:
                self.turn = i
                break
        self.world.drift_wind()
        self._begin_turn()

    def _wind_text(self) -> str:
        w, m = self.world.wind, self.cfg_settings.wind
        if m <= 0:
            return ""
        if abs(w) < 0.05:
            return "WIND CALM"
        n = 1 + int(min(abs(w) / m, 0.999) * 4)
        return f"WIND {'◄' * n if w < 0 else '►' * n} {abs(w):.1f}"

    def _fx_on(self) -> bool:
        return self.app.settings.effects

    def _fire(self, announce: bool = True) -> None:
        w, tank = self.world, self.current
        origin = tank.launch_origin()
        # The whole shot (arcs, bounces, splits, bomblets...) is decided once, on a fixed 20ms grid, so every LAN machine
        # produces the exact same events no matter its frame rate; the screen just animates the planned flights.
        if tank.ammo.key == BLESSING_KEY and not self.session.config.blessing:      # stale selection / forged loadout: never fires
            tank.ammo = DEFAULT_AMMO
        self.blessing_shot = tank.ammo.key == BLESSING_KEY
        self.special_shot = (not self.blessing_shot) and self.session.config.special and tank.charge >= self.session.config.special_wait
        if self.blessing_shot:
            self.floaters.append(FloatText(tank.x, tank.y + tank.height + 8, "MARTYR'S BLESSING!", GOLD))
        if self.special_shot:
            tank.charge = 0
            self.floaters.append(FloatText(tank.x, tank.y + tank.height + 8, "SPECIAL ATTACK!", GOLD))
            if tank.ammo.mechanics:
                self.floaters.append(FloatText(tank.x, tank.y + tank.height + 14, "AMMO EFFECT SKIPPED", Palette.MUTED))
        elif tank.ammo.mechanics and not w.ammo_fx and not tank.is_ai and tank.index not in self._fx_warned:
            self._fx_warned.add(tank.index)
            self.floaters.append(FloatText(tank.x, tank.y + tank.height + 8, "SPECIAL AMMO IS OFF HERE", Palette.MUTED))
        self.flights = [LiveFlight(s, tank.index) for s in plan_shot(w, tank, self.special_shot)]
        self.pending = []
        self.proj = self.flights[0].proj if self.flights else None
        net = self.session.config.net
        if net is not None and announce:
            net.send({"t": "fire", "i": tank.index, "a": tank.angle, "p": tank.power})
        tank.recoil = 0.2
        pan = self._pan(origin[0])
        self.app.sfx("fire:" + tank.ammo.key, 0.9, pan)
        if self.blessing_shot:
            self.app.sfx("bless_choir", 0.8, pan)
        elif self.special_shot:
            self.app.sfx("special_fire", 0.9, pan)
        w.fx.muzzle(origin[0], origin[1], tank.angle, tank.shot_color)
        if self._fx_on():
            self.shake.kick(0.9)
        self.phase, self.t = Phase.FLIGHT, 0.0

    def _advance_flights(self, sdt: float) -> None:
        for f in list(self.flights):
            if f.delay > 0:
                f.delay -= sdt
                continue
            advance_projectile(f.proj, sdt, PHYS, lambda x, y, f=f: self._flight_step(f, x, y))
            if f.proj.t >= f.spec.trace.time:
                self.flights.remove(f)
                self.pending.extend(f.spec.events)

    def _flight_step(self, f: "LiveFlight", x: float, y: float) -> None:
        if math.hypot(x - f.last[0], y - f.last[1]) >= 1.0:
            f.last = (x, y)
            f.n += 1
            for k in range(3 if self.special_shot else 1):
                self.world.fx.trail(x + (k - 1) * 1.5, y + (k - 1), self.current.shot_color, self.current.ammo, f.n + k, self.app.time)

    def _begin_blessing(self, ev: Ev) -> None:
        """A direct hit on an opposing tank: the clock opens and the judgment is planned. Every opposing tank is struck first, then
        nine pillars sweep outward across half the battlefield around the impact, each carving a real crater."""
        w, shooter = self.world, self.current
        self.proj, self.ev, self.flags = None, ev, set()
        self.impact = Impact(ev.x, ev.y, ev.kind, ev.tank)
        self.victims = [t for t in w.tanks if t.alive and t.team != shooter.team]
        self.blessing_shot, self.pending, self.flights = False, [], []
        W, n = w.width, 10
        span = W * 0.55
        c0 = clamp(ev.x - span / 2, 4, max(4, W - 4 - span))
        ground = sorted((c0 + span * (k + 0.5) / n for k in range(n)), key=lambda x: abs(x - ev.x))
        targets = [(v.x, v.y + v.height * 0.5, v.index) for v in self.victims]
        targets += [(x, float(w.terrain.heights[int(clamp(x, 0, W - 1))]), None) for x in ground if abs(x - shooter.x) >= 14]
        wipes = [(x, float(w.terrain.heights[int(x)])) for x in (4 + (W - 9) * k / 11 for k in range(12)) if abs(x - shooter.x) >= 14]
        self.bless = BlessingFX(ev.x, ev.y, targets, full=self._fx_on(), wipes=tuple(wipes))
        self._bless_ticks = 0
        self.app.sfx("bless_star", 1.0, self._pan(ev.x))
        self.phase, self.t = Phase.BLESSING, 0.0

    def _bless_kill(self, v: "Tank") -> None:
        if v.hp <= 0 and v in ([self.doomed] + self.doomed_more):
            return
        v.shield = 0
        v.hp = 0
        v.hurt = 0.6
        self.floaters.append(FloatText(v.x, v.y + v.height + 6, "JUDGED", BlessingFX.GOLDC))
        if self.doomed is None:
            self.doomed = v
        elif v is not self.doomed and v not in self.doomed_more:
            self.doomed_more.append(v)

    def _blessing_update(self, sdt: float) -> None:
        w, b, imp = self.world, self.bless, self.impact
        b.t += sdt
        R = PHYS.blast_radius
        if not b.skipped and b.t < b.T_BANG:                                 # the clock winds: one tick per beat, faster as it closes
            n = int((b.t / max(0.01, b.T_BANG)) ** 0.7 * 12)
            if n > getattr(self, "_bless_ticks", 0):
                self._bless_ticks = n
                self.app.sfx("bless_tick", 0.7, rate=1.0 + n * 0.03)
        for key in b.events():
            if key == "bang":
                self.app.sfx("bless_pillar", 1.0, self._pan(imp.x))
                w.explosions.append(Explosion(imp.x, imp.y, R * 3.0, BlessingFX.GOLDC, 1.2, "blessing"))
                self.flash = 1.0
                if self._fx_on():
                    self.shake.kick(5.0)
                self.app.feedback.emit("explosion")
            elif key.startswith("hit"):                                      # a pillar lands: real crater, real kill if it is a tank's
                i = int(key[3:])
                if i >= len(b.targets):
                    continue
                tx, ty, ti = b.targets[i]
                if not b.skipped or i == 0:
                    self.app.sfx("bless_pillar", 0.9 if ti is not None else 0.6, self._pan(tx), rate=1.0 - 0.02 * (i % 6), gap=0.03)
                w.terrain_op("blast", tx, ty, R * (1.7 if ti is not None else 2.6))
                if not b.skipped:
                    w.explosions.append(Explosion(tx, ty, R * 3.2, BlessingFX.GOLDC if i % 2 == 0 else BlessingFX.VIOLET, 1.1, "blessing"))
                    w.fx.impact(tx, ty, BlessingFX.GOLDC, w.mapdef.theme.soil, 1.8, ammo=self.current.ammo)
                    self.flash = max(self.flash, 0.25 if ti is None else 0.5)
                    if self._fx_on():
                        self.shake.kick(3.0 if ti is None else 5.0)
                if ti is not None:
                    self._bless_kill(w.tanks[ti])
            elif key == "finale":                                            # the nuke at the heart of the clock
                self.app.sfx("bless_nuke", 1.0, self._pan(imp.x))
                w.terrain_op("blast", imp.x, imp.y, R * 4.2)
                if not b.skipped:
                    w.explosions.append(Explosion(imp.x, imp.y, R * 7.5, (255, 255, 255), 2.0, "blessing"))
                    self.flash = 1.0
                    if self._fx_on():
                        self.shake.kick(11.0)
                    self.app.feedback.emit("explosion")
            elif key.startswith("wipe"):                                     # the firewall front reaches a column: the ground is gone
                i = int(key[4:])
                if i < len(b.wipes):
                    wx_, wy_ = b.wipes[i]
                    if i == 0:
                        self.app.sfx("bless_firewall", 1.0)
                    w.terrain_op("blast", wx_, wy_, R * 3.4)
                    if not b.skipped:
                        w.explosions.append(Explosion(wx_, wy_, R * 3.4, (255, 150, 60), 1.2, "blessing"))
                        if self._fx_on():
                            self.shake.kick(2.0)
        if b.t >= b.T_END:
            for v in self.victims:                                           # safety net: nobody survives the Blessing
                self._bless_kill(v)
            self.bless = None
            self.phase, self.t = Phase.SETTLE, 0.0

    def _start_event(self, ev: Ev) -> None:
        if self.blessing_shot and ev.first:
            if ev.kind is ImpactKind.TANK and ev.tank is not None and self.world.tanks[ev.tank].team != self.current.team:
                self._begin_blessing(ev)
                return
            self.blessing_shot = False                                       # a miss is just an ordinary shell: the Blessing needs a DIRECT HIT
            if ev.kind is not ImpactKind.OUT:
                self.floaters.append(FloatText(ev.x, ev.y + 8, "THE BLESSING NEEDS A DIRECT HIT", BlessingFX.GOLDC))
        w, shooter = self.world, self.current
        self.proj, self.ev, self.flags = None, ev, set()
        self.impact = Impact(ev.x, ev.y, ev.kind, ev.tank)
        victims: list = []
        reach = PHYS.splash_reach * ev.radius
        if ev.dmg > 0 and ev.kind is ImpactKind.TANK and ev.tank >= 0:
            victims = [w.tanks[ev.tank]]
        elif ev.dmg > 0 and ev.kind is ImpactKind.TERRAIN:
            near = sorted((w.distance_to_tank(t, ev.x, ev.y), t.index) for t in w.tanks if t.alive)
            victims = [w.tanks[i] for d, i in near if d <= reach][:(len(near) if ev.multi else 1)]
        self.victims = victims
        ai = self.ais.get(shooter.index)
        if ev.first and ai and shooter.is_ai and self.plan and self._control(shooter) == "ai":
            foe = self._target_for(shooter)
            ai.observe(self.plan, self.impact, foe, foe in victims)
        if ev.kind is ImpactKind.OUT and ev.mode != "fx":
            self.floaters.append(FloatText(clamp(ev.x, 6, w.width - 6), w.height - 6, "OUT OF BOUNDS", Palette.MUTED))
            self.flags |= {"boom", "burst", "carve", "damage"}
            self.t = 0.6
        else:
            self.t = -ev.delay
        self.phase = Phase.IMPACT

    def _impact_update(self, sdt: float) -> None:
        w, ev, imp = self.world, self.ev, self.impact
        self._advance_flights(sdt)
        self.t += sdt
        if self.t < 0:
            return
        shooter = self.current
        R = PHYS.blast_radius * ev.radius
        if "boom" not in self.flags:
            self.flags.add("boom")
            w.explosions.append(Explosion(imp.x, imp.y, max(2.0, R), shooter.shot_color, style=shooter.ammo.boom))
            if imp.kind is not ImpactKind.OUT:
                self.app.sfx("hit:" + shooter.ammo.key, clamp(0.55 + 0.35 * ev.radius, 0.4, 1.0) * (1.25 if ev.big else 1.0), self._pan(imp.x),
                             rate=1.0 if ev.first else 1.0 + 0.04 * (len(self.pending) % 5), gap=0.04)
                if imp.kind is ImpactKind.TERRAIN and ev.mode == "mound":
                    self.app.sfx("mound", 0.6, self._pan(imp.x), gap=0.1)
                self.shake.kick(5.0 if ev.big else 1.6 * min(1.4, ev.radius))
            self.app.feedback.emit("explosion")
        if self.t >= 0.06 and "burst" not in self.flags:
            self.flags.add("burst")
            w.fx.impact(imp.x, imp.y, shooter.shot_color, w.mapdef.theme.soil, 2.6 if ev.big else min(1.4, 0.4 + 0.6 * ev.radius), ammo=shooter.ammo)
            if ev.big:                                               # the special: two more rings of the ammo's own blast
                for k, sc in enumerate((1.5, 2.1)):
                    w.explosions.append(Explosion(imp.x, imp.y, R * sc, mix(shooter.shot_color, (255, 255, 255), 0.3 * k), style=shooter.ammo.boom))
        if self.t >= 0.28 and "carve" not in self.flags:
            self.flags.add("carve")
            if ev.mode != "fx":
                w.terrain_op(ev.mode, imp.x, imp.y, R * (0.85 if imp.kind is ImpactKind.TANK else 1.0))
            self.guide_key = None
        if self.t >= 0.42 and "damage" not in self.flags:
            self.flags.add("damage")
            direct = imp.kind is ImpactKind.TANK
            for v in self.victims:
                dmg = ev.dmg * (2 if (direct and v.scale > 1.0) else 1) * self.session.dmg_mult(shooter)   # saucers: direct hits double
                if v.shield > 0:
                    v.shield -= 1
                    dmg = 0
                self.app.sfx("shield_block" if dmg == 0 else "tank_hit", 0.9 if direct else 0.7, self._pan(v.x), gap=0.05)
                v.hp -= dmg
                v.hurt = 0.6
                txt = ("SHIELDED - KILL THE DRONES" if v.guard else "SHIELD ABSORBED") if dmg == 0 else (f"DIRECT HIT -{dmg}" if direct else f"HIT -{dmg}")
                self.floaters.append(FloatText(v.x, v.y + v.height + 6, txt, Palette.AMBER if dmg == 0 else Palette.DANGER))
                if self._fx_on():
                    self.shake.kick(2.6 if dmg else 1.0)
                if v.hp <= 0:
                    if self.doomed is None:
                        self.doomed = v
                    elif v is not self.doomed and v not in self.doomed_more:
                        self.doomed_more.append(v)
            if ev.pull > 0:                                                     # gravity well: drag tanks toward the blast
                for t in w.tanks:
                    dx = imp.x - t.x
                    if t.alive and t.kind != "ufo" and abs(dx) <= ev.pull * 2.2:
                        t.x = clamp(t.x + clamp(dx * 0.6, -ev.pull, ev.pull), 9, w.width - 10) + 0.0
                        t.y = max(t.y, float(w.terrain.support_height(t.x)) + t.hover)
            elif ev.pull < 0:                                                   # ATOMIC BREATH: the roar hurls tanks away
                P = -ev.pull
                for t in w.tanks:
                    dx = t.x - imp.x
                    if t.alive and t.kind != "ufo" and abs(dx) <= P * 2.2:
                        shove = (P * 2.2 - abs(dx)) * 0.65
                        t.x = clamp(t.x + math.copysign(min(P, shove), dx if dx else 1.0), 9, w.width - 10) + 0.0
                        t.y = max(t.y, float(w.terrain.support_height(t.x)) + t.hover)
                        t.hurt = max(t.hurt, 0.3)
        end_t = 1.0 if not (self.flights or self.pending) else 0.5
        if self.t >= end_t:
            if self.pending:
                self._start_event(self.pending.pop(0))
            elif self.flights:
                self.phase, self.t = Phase.FLIGHT, 0.0
            else:
                self.phase, self.t = Phase.SETTLE, 0.0

    def _destruction_update(self, sdt: float) -> None:
        from tanks.scenes.rounds import RoundResultScene
        w, d = self.world, self.doomed
        self.t += sdt
        if "start" not in self.flags:
            self.flags.add("start")
            self.wiped = not any(t.alive for t in w.tanks if t.team == d.team)   # round ends only when a whole team is down
            if self.wiped:
                self.session.record_round(1 - d.team)
                self.session.commit(self.app)
        if self.t < 0.8:
            d.hurt = 0.6
        if self.t >= 0.8 and "boom" not in self.flags:
            self.flags.add("boom")
            d.destroyed = True
            for o in self.doomed_more:
                o.destroyed = True
            d.hurt = 0.0
            w.explosions.append(Explosion(d.x, d.y + 3, 12, d.shot_color, 1.3, self.current.ammo.boom))
            w.fx.tank_debris(d.x, d.y + 3, d.color)
            self.app.sfx("tank_destroy", 1.0, self._pan(d.x))
            self.app.sfx("debris", 0.7, self._pan(d.x))
            w.fx.impact(d.x, d.y + 3, d.shot_color, w.mapdef.theme.soil, 1.8, self.current.ammo)
            self.flash = 1.0
            if self._fx_on():
                self.shake.kick(4.5)
            self.app.feedback.emit("destroy")
        if self.t >= 1.6 and "banner" not in self.flags:
            self.flags.add("banner")
            self.banner = Banner("TARGET DESTROYED", d.name + " IS OUT", d.color, 2.0)
        if self.wiped and self.t >= 3.4 and not self.finished:
            self.finished = True
            self.app.push(RoundResultScene(self.app, self))
        elif not self.wiped and self.t >= 2.4:
            if self.doomed_more:                           # another tank fell in the same volley
                self.doomed, self.flags, self.t = self.doomed_more.pop(0), set(), 0.0
            else:
                self.doomed, self.flags = None, set()      # a teammate fell but the team fights on
                self._end_turn()

    # -- input ---------------------------------------------------------------
    def handle(self, ev: InputEvent) -> None:
        if ev.action in (Action.BACK, Action.PAUSE):
            self.app.push(PauseScene(self.app, self))
            return
        if self.phase is Phase.BLESSING:
            if self.bless is not None and (ev.confirm or ev.action in (Action.CONFIRM, Action.FIRE)):
                self.bless.skip()                                # the kill still lands; only the spectacle is cut short
            return
        if self.phase is not Phase.AIMING or self._control(self.current) != "local":
            return
        t, step = self.current, COARSE_STEP if ev.coarse else 1
        if ev.raw in ("x", "X") and self.session.config.special:
            self._forfeit(t)
        elif ev.action is Action.LEFT:
            t.angle = clamp(t.angle + step, 2, 178)
        elif ev.action is Action.RIGHT:
            t.angle = clamp(t.angle - step, 2, 178)
        elif ev.action is Action.UP:
            t.power = clamp(t.power + step, PHYS.min_power, PHYS.max_power)
        elif ev.action is Action.DOWN:
            t.power = clamp(t.power - step, PHYS.min_power, PHYS.max_power)
        elif ev.confirm:
            self._fire()

    def _forfeit(self, tank: Tank, announce: bool = True) -> None:
        """Special attack charging: give up this turn to bank one charge (two charges make your next shot the special)."""
        need = self.session.config.special_wait
        if tank.charge >= need:
            self.floaters.append(FloatText(tank.x, tank.y + tank.height + 8, "SPECIAL ALREADY READY - FIRE!", Palette.AMBER))
            return
        tank.charge += 1
        self.app.sfx("special_charge", 0.8, self._pan(tank.x))
        self.floaters.append(FloatText(tank.x, tank.y + tank.height + 8, "SPECIAL READY!" if tank.charge >= need else f"CHARGING {tank.charge}/{need}", GOLD))
        net = self.session.config.net
        if net is not None and announce:
            net.send({"t": "skip", "i": tank.index})
        self._end_turn()

    # -- LAN -------------------------------------------------------------------
    def _net_tick(self, dt: float) -> None:
        from tanks.scenes.lan import NetNoticeScene
        net = self.session.config.net
        if net is None or self.world is None:
            return
        net.pump()
        if net.take("quit"):
            net.close()
            self.app.goto(NetNoticeScene(self.app, "OPPONENT LEFT", "The other player left the match."))
            return
        if net.dead:
            self.app.goto(NetNoticeScene(self.app, "CONNECTION LOST", "The other player disconnected."))
            return
        cur = self.current
        ctl = self._control(cur)
        if self.phase is Phase.AIMING and ctl == "local" or self.phase is Phase.AI_THINKING:
            self._aim_timer -= dt
            key = (round(cur.angle, 2), round(cur.power, 2))
            if self._aim_timer <= 0 and key != self._aim_sent:
                self._aim_timer, self._aim_sent = 0.08, key
                net.send({"t": "aim", "i": cur.index, "a": cur.angle, "p": cur.power})
        if self.phase is Phase.AIMING and ctl == "remote":
            while True:
                m = net.peek("aim", "fire", "skip")
                if m is None:
                    break
                if m.get("i") != cur.index:
                    if m["t"] == "aim":                   # a stale aim from an earlier turn: discard it
                        net.drop(m)
                        continue
                    break
                net.drop(m)
                if m["t"] == "skip":
                    self._forfeit(cur, announce=False)
                    break
                cur.angle = clamp(float(m["a"]), 2, 178)
                cur.power = clamp(float(m["p"]), PHYS.min_power, PHYS.max_power)
                if m["t"] == "fire":
                    self._fire(announce=False)
                    break

    # -- update --------------------------------------------------------------
    def update_ambient(self, dt: float) -> None:
        if self.world:
            self.world.update_effects(dt)
            self._tick_visuals(dt)

    def _tick_visuals(self, dt: float) -> None:
        self.shake.update(dt)
        self.flash = max(0.0, self.flash - dt * 2.2)
        for f in self.floaters:
            f.age += dt
        self.floaters = [f for f in self.floaters if f.age < f.life]
        if self.banner:
            self.banner.age += dt
            if self.banner.age >= self.banner.life:
                self.banner = None

    def _refresh_guards(self) -> None:
        """A guarded tank (the Mothership) keeps its shield up while any teammate lives; it drops for good once they are all down."""
        for t in self.world.tanks:
            if t.guard and t.alive:
                if any(o.alive and o is not t and o.team == t.team for o in self.world.tanks):
                    t.shield = max(t.shield, 2)
                else:
                    t.guard, t.shield = False, 0
                    self.floaters.append(FloatText(t.x, t.y + t.height + 8, "SHIELD DOWN!", (140, 230, 255)))

    def update(self, dt: float) -> None:
        self._check_resize()
        self._net_tick(dt)
        if self.world is not None:
            self._refresh_guards()
        sdt = dt * self.app.settings.anim_speed
        w = self.world
        w.update_effects(sdt)
        self._tick_visuals(dt)
        ph = self.phase
        if ph is Phase.INTRO:
            self.t += dt
            if self.t >= self.INTRO_TIME:
                self._begin_turn()
        elif ph is Phase.AI_THINKING:
            self.t += sdt
            p = self.t / self.plan.think_time
            tank = self.current
            k = ease_in_out((p - 0.3) / 0.6)
            tank.angle = lerp(self.plan_from[0], self.plan.angle, k)
            tank.power = lerp(self.plan_from[1], self.plan.power, k)
            if p >= 1:
                tank.angle, tank.power = self.plan.angle, self.plan.power
                self._fire()
        elif ph is Phase.FLIGHT:
            self._advance_flights(sdt)
            if self.pending:
                self._start_event(self.pending.pop(0))
        elif ph is Phase.IMPACT:
            self._impact_update(sdt)
        elif ph is Phase.SETTLE:
            self.t += sdt
            moving = w.settle(sdt)
            if self.t > 0.25 and not moving:
                if self.doomed:
                    pool = [self.doomed] + self.doomed_more          # an enemy goes down first if both sides lost a tank
                    foe_first = [v for v in pool if v.team != self.current.team]
                    self.doomed = (foe_first or pool)[0]
                    self.doomed_more = [v for v in pool if v is not self.doomed]
                    self.phase, self.t, self.flags = Phase.DESTRUCTION, 0.0, set()
                elif self.current.alive and self.current.volley > 0:
                    self.current.volley -= 1
                    self._begin_turn(volley=True)
                else:
                    self._end_turn()
        elif ph is Phase.DESTRUCTION:
            self._destruction_update(sdt)
        elif ph is Phase.BLESSING:
            self._blessing_update(sdt)

    # -- drawing -------------------------------------------------------------
    def _cell_of(self, x: float, y: float) -> tuple[int, int]:
        L = self.layout
        return L.fx + int(x), L.fy + (self.world.height - 1 - int(y)) // 2

    def draw(self, screen: Screen) -> None:
        if self.world is None:
            return
        L, w = self.layout, self.world
        self._off = []
        canvas = w.scenery.canvas()
        w.scenery.draw_stars(canvas, self.app.time)
        w.scenery.draw_aurora(canvas, self.app.time)
        w.scenery.draw_fx(canvas, self.app.time, self._fx_on())
        w.draw_wind(canvas)
        cur = self.current
        if self.phase is Phase.AIMING and self.app.settings.aim_guide:
            key = (cur.angle, cur.power, w.terrain.version, cur.x, cur.y)
            if key != self.guide_key:
                self.guide_key = key
                launch = make_ammo_launch(w, cur, cur.angle, cur.power, wind=0.0)
                self.guide = w.physics.trace(launch, w.owner_probe(cur.index), 0.02, 2.6, 8.0).points
            pts = self.guide[:10] if self.app.settings.aim_guide == 1 else self.guide
            for i, (x, y) in enumerate(pts):
                canvas.blendf(x, y, cur.shot_color, 0.85 * (1 - i / (len(pts) + 4)))
        for t in w.tanks:
            flash = (t.hurt / 0.6) * (0.4 + 0.4 * math.sin(self.app.time * 40)) if t.hurt > 0 else 0.0
            if t.kind == "ufo":
                draw_ufo(canvas, t, self.app.time, max(0.0, flash))
                continue
            draw_tank(canvas, t.x, t.y, t.facing, t.angle, t.hull_sentinel if (t.rgb_hull and t.hull_sentinel in PIXEL_PAINTS) else t.color, flash=max(0.0, flash), wreck=t.destroyed, recoil=t.recoil,
                      design=t.design, t=self.app.time, lift=0.0, hover=t.hover)
        w.particles.draw(canvas)
        for f in self.flights:
            if f.delay > 0 or f.spec.trace.time <= 0:
                continue
            x, y = f.proj.x, f.proj.y
            col = self.current.shot_color
            if y >= w.height:
                pr, lc = f.proj, f.proj.launch
                draw_projectile(canvas, x, w.height - 5, lc.vx, 0.0, col, self.current.ammo, self.app.time)     # the shell, kept on screen
                self._off.append((x, y - w.height))
            else:
                pr, lc = f.proj, f.proj.launch
                vx, vy = lc.vx + lc.ax * pr.t, lc.vy - lc.g * pr.t
                if self.blessing_shot:                     # temporal invocation: gold/violet halo and orbiting stars on the shell
                    tt = self.app.time
                    for k in range(30):
                        a = k / 30 * math.tau - tt * 5
                        rr = 4.5 + 1.5 * math.sin(tt * 8 + k)
                        canvas.blendf(x + math.cos(a) * rr, y + math.sin(a) * rr, (255, 214, 90) if k % 2 else (176, 120, 255), 0.7)
                    for k in range(6):
                        a = tt * 6 + k * math.tau / 6
                        canvas.blendf(x + math.cos(a) * 2.6, y + math.sin(a) * 2.6, (255, 255, 255), 0.9)
                if self.special_shot:                      # scaled-up: a pulsing halo and three orbiting copies of the ammo's shell
                    tt = self.app.time
                    for k in range(26):
                        a = k / 26 * math.tau + tt * 6
                        canvas.blendf(x + math.cos(a) * (5 + math.sin(tt * 9)), y + math.sin(a) * (5 + math.sin(tt * 9)), col, 0.55)
                    for k in range(3):
                        a = tt * 7 + k * math.tau / 3
                        draw_projectile(canvas, x + math.cos(a) * 3.2, y + math.sin(a) * 3.2, vx, vy, col, self.current.ammo, tt)
                draw_projectile(canvas, x, y, vx, vy, col, self.current.ammo, self.app.time)
        for e in w.explosions:
            e.draw(canvas)
        screen.blit(canvas, L.fx, L.fy, self.shake.offset(w.rng, self._fx_on()))
        for ox, oh in self._off:                                                  # off-screen marker: how far above the field it is
            cx = clamp(L.fx + int(ox), L.fx + 3, L.fx + L.fcols - 8)
            screen.put(cx, L.fy, "▲", Palette.WHITE)
            screen.text(cx + 1, L.fy, f"{int(oh)}", Palette.WHITE)
        if self.flash > 0 and self._fx_on():
            screen.tint(L.fx, L.fy, L.fcols, L.frows, (255, 255, 255), self.flash * 0.45)
        if self.phase is Phase.BLESSING and self.bless is not None:
            self.bless.draw(screen, L, self._cell_of)
        self._draw_labels(screen)
        self._draw_overlays(screen)
        self._draw_hud(screen)

    def _draw_labels(self, screen: Screen) -> None:
        L, w = self.layout, self.world
        for t in w.tanks:
            if t.destroyed:
                continue
            cx, cy = self._cell_of(t.x, t.y + t.height + 8)
            cy = max(L.fy, cy)
            text = f"{t.label} {hearts(t.hp, False, t.max_hp)}"
            screen.text(cx - len(text) // 2, cy, text, t.color if t.hp > 0 else Palette.MUTED)
            if t is self.current and self.phase in (Phase.AIMING, Phase.AI_THINKING) and cy > L.fy:
                bob = int(self.app.time * 3) % 2
                screen.put(cx, cy - 1 - bob + (1 if cy - 1 - bob < L.fy else 0), "▼", Palette.WHITE)

    def _draw_overlays(self, screen: Screen) -> None:
        L = self.layout
        for f in self.floaters:
            x, y = self._cell_of(f.x, f.y + f.age * 6)
            a = 1 - f.age / f.life
            s = f.text
            screen.text(x - len(s) // 2, max(L.fy, y), s, mix(Palette.BG, f.color, clamp(a * 2, 0, 1)))
        b = self.banner
        if b:
            a = clamp(min(b.age * 6, (b.life - b.age) * 4), 0, 1)
            y = L.fy + L.frows // 3
            screen.tint(L.fx, y - 1, L.fcols, 4, (0, 0, 0), 0.6 * a)
            spaced = " ".join(b.text)
            screen.center(y, spaced, mix(Palette.BG, b.color, a), None, L.fx, L.fcols)
            if b.sub:
                screen.center(y + 2, b.sub, mix(Palette.BG, Palette.TEXT, a), None, L.fx, L.fcols)

    def _state_text(self) -> str:
        p = self.phase
        dots = "." * (int(self.app.time * 3) % 4)
        if p is Phase.INTRO:
            return "DEPLOYING"
        if p is Phase.AIMING:
            return "AIMING"
        if p is Phase.AI_THINKING:
            return "AI THINKING" + dots
        if p is Phase.FLIGHT:
            return "PROJECTILE AWAY"
        if p is Phase.IMPACT:
            return "IMPACT"
        if p is Phase.SETTLE:
            return "TERRAIN SETTLING"
        if p is Phase.BLESSING:
            return "THE MARTYR'S BLESSING"
        return "TARGET DESTROYED"

    def _draw_hud(self, screen: Screen) -> None:
        from tanks.scenes.tutorial import PracticeScene
        L, s = self.layout, self.session
        top, cols = L.top, L.cols
        screen.fill(0, top, cols, 2, Palette.PANEL)
        pl = self.world.tanks
        teams = sorted({t.team for t in pl})[:2]
        left_end, right_start = 0, cols                      # how far the two name plates reach on the title row
        for side, team in enumerate(teams):
            everyone = [t for t in pl if t.team == team]
            members = everyone[:2]
            wins_text = s.hud_wins(team)
            for r, t in enumerate(members):
                row, nm = top + (r if len(members) > 1 else 0), t.name[:16]
                sw = s.config.special_wait if s.config.special else 0
                if side == 0:
                    screen.text(1, row, "▌", t.color, Palette.PANEL)
                    screen.text(3, row, nm, t.color, Palette.PANEL)
                    wd = draw_hp(screen, 4 + len(nm), row, t, Palette.PANEL)
                    if s.config.special:
                        screen.text(5 + len(nm) + wd, row, "✦" * t.charge + "·" * (s.config.special_wait - t.charge), GOLD if t.charge >= s.config.special_wait else Palette.MUTED, Palette.PANEL)
                    if row == top:
                        left_end = max(left_end, 5 + len(nm) + wd + sw)
                else:
                    x = cols - 2
                    screen.text(x, row, "▐", t.color, Palette.PANEL)
                    screen.text(x - 1 - len(nm), row, nm, t.color, Palette.PANEL)
                    wd = draw_hp(screen, x - 3 - len(nm), row, t, Palette.PANEL, True)
                    if s.config.special:
                        screen.text(x - 5 - len(nm) - wd, row, "✦" * t.charge + "·" * (s.config.special_wait - t.charge), GOLD if t.charge >= s.config.special_wait else Palette.MUTED, Palette.PANEL)
                    if row == top:
                        right_start = min(right_start, x - 4 - len(nm) - wd - sw)
            if len(members) == 1:
                if side == 0:
                    screen.text(3, top + 1, wins_text, Palette.MUTED, Palette.PANEL)
                else:
                    screen.text(cols - 2 - len(wins_text), top + 1, wins_text, Palette.MUTED, Palette.PANEL)
            else:
                pass
        parts = s.hud_title().split("  ·  ")                  # the title gives up its least important parts until it fits the gap
        gap = right_start - left_end - 2
        for cand in ["  ·  ".join(parts[:k]) for k in range(len(parts), 0, -1)] + ["  ·  ".join(parts[1:2])]:
            if cand and len(cand) <= gap:
                screen.text(left_end + 1 + (gap - len(cand)) // 2 + 1, top, cand, Palette.TEXT, Palette.PANEL)
                break
        cur = self.current
        badge = f" {self._turn_text(self.turn)} "
        state = self._state_text()
        total = len(badge) + 2 + len(state)
        bx = (cols - total) // 2
        if self.phase is Phase.DESTRUCTION:
            screen.center(top + 1, state, Palette.DANGER, Palette.PANEL)
        else:
            screen.text(bx, top + 1, badge, Palette.INK, cur.color)
            screen.text(bx + len(badge) + 2, top + 1, state, Palette.AMBER, Palette.PANEL)
        screen.fill(0, top + 2, cols, 1, Palette.BG, "─", mix(Palette.LINE, cur.color, 0.5))
        wt = wallet_text(self.app.save)                  # the wallet rides on the HUD divider, always visible in battle
        screen.text(cols - len(wt) - 3, top + 2, f" {wt} ", Palette.TEXT, Palette.BG)
        for side, team in enumerate(teams):
            if len([t for t in pl if t.team == team]) > 1:
                wtx = s.hud_wins(team)
                extra = len([t for t in pl if t.team == team]) - 2
                if extra > 0:
                    wtx += f"  +{extra} MORE"
                ww = len(wallet_text(self.app.save)) + 6
                screen.text(1 if side == 0 else cols - ww - len(wtx), top + 2, wtx, Palette.MUTED, Palette.BG)
        by = L.fy + L.frows
        screen.fill(0, by, cols, 3, Palette.PANEL)
        screen.fill(0, by, cols, 1, Palette.BG, "─", mix(Palette.LINE, cur.color, 0.5))
        x = 2
        rel = cur.rel_angle
        screen.text(x, by + 1, "ANGLE", Palette.MUTED, Palette.PANEL)
        screen.text(x + 6, by + 1, f"{rel:>3.0f}°", cur.color, Palette.PANEL)
        gx, gw = x + 12, 25
        screen.put(gx, by + 1, "├", Palette.LINE, Palette.PANEL)
        for i in range(gw):
            screen.put(gx + 1 + i, by + 1, "─", (52, 70, 82), Palette.PANEL)
        marker = int((180 - cur.angle) / 180 * (gw - 1))
        screen.put(gx + 1 + marker, by + 1, "◆", cur.color, Palette.PANEL)
        screen.put(gx + gw + 1, by + 1, "┤", Palette.LINE, Palette.PANEL)
        px = gx + gw + 5
        screen.text(px, by + 1, "POWER", Palette.MUTED, Palette.PANEL)
        draw_bar(screen, px + 6, by + 1, 20, (cur.power - PHYS.min_power) / (PHYS.max_power - PHYS.min_power))
        screen.text(px + 27, by + 1, f"{cur.power:>3.0f}%", cur.color, Palette.PANEL)
        sx = px + 34
        if sx + 8 < cols:
            screen.text(sx, by + 1, "SHELL", Palette.MUTED, Palette.PANEL)
            screen.text(sx + 6, by + 1, "●●", cur.shot_color, Palette.PANEL)
        if self.phase is Phase.AI_THINKING:
            screen.text(2, by + 2, "AI FIRE CONTROL: " + self.plan.status, Palette.AMBER, Palette.PANEL)
        else:
            caps = ([("◄►", "AIM"), ("▲▼", "POWER"), ("SHIFT", "COARSE"), ("SPACE", "FIRE")] if isinstance(self, PracticeScene)
                    else [("A/D", "AIM"), ("W/S", "POWER"), ("SHIFT", "COARSE"), ("SPACE", "FIRE")])
            if self.session.config.special:
                caps.append(("X", "CHARGE"))
            draw_keycaps(screen, 2, by + 2, tuple(caps + [("ESC", "MENU")]), Palette.PANEL)
        wmax, wind = self.cfg_settings.wind, self.world.wind
        if wmax <= 0:
            wt, wc = "WIND OFF", Palette.MUTED
        elif abs(wind) < 0.05:
            wt, wc = "WIND CALM", Palette.TEXT
        else:
            wt = self._wind_text()
            wc = gradient(((0, Palette.OK), (0.6, Palette.AMBER), (1, Palette.DANGER)), abs(wind) / wmax)
        screen.text(cols - 2 - len(wt), by + 2, wt, wc, Palette.PANEL)


class ConfirmLeaveScene(Scene):
    """'Leave this match?' - makes the consequence clear before anything is closed or discarded."""
    overlay = True
    show_wallet = False

    def __init__(self, app, session: "MatchSession") -> None:
        super().__init__(app)
        self.session = session
        self.net = session.config.net

    def handle(self, ev: InputEvent) -> None:
        if ev.action is Action.BACK or ev.raw in ("n", "N"):
            self.app.pop()
        elif ev.confirm or ev.raw in ("y", "Y"):
            if self.net is not None:                           # tell the other player, then release the socket
                self.net.send({"t": "quit"})
                self.net.close()
            self.app.save.flush()
            self.app.goto(self.session.exit_scene(self.app))

    def draw(self, screen: Screen) -> None:
        screen.dim(0.55)
        s = self.session
        x, y = panel(screen, 52, 10, "LEAVE THE MATCH?", fg=Palette.DANGER)
        line = ("The other player will be told you left." if self.net else "This match will end and its progress is lost.")
        screen.center(y + 2, line, Palette.TEXT, Palette.PANEL, x, 52)
        screen.center(y + 3, f"You return to {s.exit_label if s.exit_label != 'MENU' else 'the menu'}.", Palette.MUTED, Palette.PANEL, x, 52)
        screen.center(y + 6, "[ENTER] LEAVE      [ESC] KEEP PLAYING", Palette.AMBER, Palette.PANEL, x, 52)


class PauseScene(Scene):
    overlay = True
    show_wallet = False

    def __init__(self, app, battle: BattleScene) -> None:
        super().__init__(app)
        self.battle = battle
        self.net = battle.session.config.net
        self.menu = MenuList(["RESUME", "EXIT MATCH"] if self.net else ["RESUME", "RESTART", "EXIT MATCH"])

    def handle(self, ev: InputEvent) -> None:
        if ev.action in (Action.BACK, Action.PAUSE):
            self.app.pop()
            return
        c = self.menu.handle(ev)
        if c is None:
            return
        label = self.menu.items[c]
        if label == "RESUME":
            self.app.pop()
        elif label == "RESTART":
            self.battle.session.restart(self.app)
        else:
            self.app.push(ConfirmLeaveScene(self.app, self.battle.session))

    def draw(self, screen: Screen) -> None:
        screen.dim(0.45)
        x, y = panel(screen, 34, 9, "MATCH MENU")
        self.menu.draw(screen, screen.cols // 2, y + 3, self.app.time, gap=1, width=24)
        if self.net:
            screen.center(y + 7, "The match keeps running for the other player.", Palette.MUTED, Palette.PANEL, x, 34)
