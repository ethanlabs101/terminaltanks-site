"""Special-ammo mechanics. A shot is planned once, at fire time, as flights (arcs) that end in impact events; bounce,
split, cluster, burrow, pierce, seek, chain, volley and the rest are all built from those two pieces. Also the Martyr's Blessing finale."""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Callable, Optional, TYPE_CHECKING

from tanks.battle.physics import Impact, ImpactKind, Launch, Projectile, TraceResult
from tanks.battle.tank import Tank
from tanks.battle.world import BattleWorld
from tanks.colors import RGB, clamp, ease_out, gradient, mix, shade
from tanks.screen import Screen

if TYPE_CHECKING:
    from tanks.ui.hud import Layout


# ============================================================================
# Ammo mechanics. A shot is planned once, at fire time, as a list of FLIGHTS (arcs) that end in impact EVENTS. Everything
# is computed on the fixed physics grid from the world state, so LAN machines plan the very same shot.
#   mech keys (all optional)      g, wind, speed : scale gravity / wind pull / muzzle speed
#   wob=(amp, freq) corkscrew     bounce=n, br   : skip off the ground n times (small blasts), radius br
#   radius=r  dmg=n               apex=("split", n, spread) | ("jump", dist)   : act at the top of the arc
#   cluster=n, cspace, cr         chain=n, cstep : bomblets / a walking line of blasts after the main impact
#   fuse=seconds, fr              terrain="blast"|"mound"|"trench"|"glass"       pull=px : drag tanks toward the impact
#   multi=1 : the blast can hurt every tank in reach
# ============================================================================
@dataclass
class Ev:
    x: float
    y: float
    kind: "ImpactKind"
    tank: int = -1
    radius: float = 1.0
    dmg: int = 1
    mode: str = "blast"          # blast | mound | trench | glass | fx
    delay: float = 0.0
    first: bool = False
    pull: float = 0.0
    multi: bool = False
    big: bool = False            # the special attack: bigger visuals everywhere


SPECIAL_DMG, SPECIAL_RADIUS = 3, 2.0


@dataclass
class FlightSpec:
    launch: Launch
    trace: TraceResult
    delay: float
    events: list = field(default_factory=list)


def make_ammo_launch(w: "BattleWorld", tank: Tank, angle: float, power: float, wind: Optional[float] = None,
                     special: bool = False) -> Launch:
    M = {} if (special or not getattr(w, "ammo_fx", True)) else tank.ammo.mechanics
    L = w.physics.make_launch(tank.launch_origin(angle), angle, power, gravity=w.physics.cfg.gravity * M.get("g", 1.0),
                              wind=(w.wind if wind is None else wind) * M.get("wind", 1.0))
    if M.get("speed", 1.0) != 1.0:
        L = replace(L, vx=L.vx * M["speed"], vy=L.vy * M["speed"])
    if "wob" in M:
        L = replace(L, wa=M["wob"][0], wf=M["wob"][1])
    return L


def _nearest_foe(w: "BattleWorld", tank: Tank, x: float, ahead: float = 0.0, reach: float = 1e9) -> Optional[Tank]:
    """The closest living enemy to world-x `x` (optionally only those up to `reach` px in direction `ahead`)."""
    best = None
    for t in w.tanks:
        if not t.alive or t.team == tank.team:
            continue
        dx = t.x - x
        if ahead and not (0 < dx * ahead <= reach):
            continue
        if best is None or abs(dx) < abs(best.x - x):
            best = t
    return best


def _reaim(w: "BattleWorld", tank: Tank, L: Launch, x: float, y: float, vx: float, vy: float, k: float) -> Launch:
    """SEEK: from (x, y) with velocity (vx, vy), bend the horizontal speed `k` of the way toward the nearest enemy."""
    foe = _nearest_foe(w, tank, x)
    sub = replace(L, x0=x, y0=y, vx=vx, vy=vy, wa=0.0)
    if foe is None or k <= 0:
        return sub
    ty = foe.y + foe.height * 0.5
    g = max(1e-3, L.g)
    disc = vy * vy + 2 * g * (y - ty)
    if disc <= 0:
        return sub
    tf = (vy + math.sqrt(disc)) / g                                   # time to fall to the target's height
    want = (foe.x - x - 0.5 * L.ax * tf * tf) / max(0.05, tf)
    tf_land = tf
    shift = clamp(k, 0, 1) * (want - vx) * tf_land                # how far the landing point moves...
    shift = clamp(shift, -18.0, 18.0)                            # ...but a lure only bends so far
    return replace(sub, vx=vx + shift / max(0.05, tf_land))


def plan_shot(w: "BattleWorld", tank: Tank, special: bool = False) -> list:
    """A special attack is a plain arc ending in one huge 3-damage blast (the ammo's own looks, scaled up)."""
    M, phys = ({} if (special or not getattr(w, "ammo_fx", True)) else tank.ammo.mechanics), w.physics
    L = make_ammo_launch(w, tank, tank.angle, tank.power, special=special)
    probe = lambda: w.owner_probe(tank.index)
    tr = phys.trace(L, probe(), 0.02, 0.0, 12.0)
    flights: list = []
    W = w.width

    def main_ev(imp: Impact, first: bool, radius: float, mode: Optional[str] = None) -> Ev:
        if special:
            return Ev(imp.x, imp.y, imp.kind, imp.tank, SPECIAL_RADIUS, SPECIAL_DMG, "blast", 0.0, first, 0.0, False, True)
        return Ev(imp.x, imp.y, imp.kind, imp.tank, radius, int(M.get("dmg", 1)), mode or M.get("terrain", "blast"), 0.0, first,
                  float(M.get("pull", 0.0)) - float(M.get("push", 0.0)), bool(M.get("multi", 0)))

    def finale(imp: Impact, first: bool, vx: float, vy: float = -1.0) -> list:
        evs = [main_ev(imp, first, M.get("radius", 1.0))]
        if imp.kind is ImpactKind.OUT:
            return evs
        if M.get("cluster"):
            n, sp, cd = int(M["cluster"]), float(M.get("cspace", 5.5)), float(M.get("cdelay", 0.09))
            for k in range(n):
                bx = clamp(imp.x + (k - (n - 1) / 2) * sp, 2, W - 3)
                evs.append(Ev(bx, w.terrain.height_at(bx) + 1.0, ImpactKind.TERRAIN, -1, M.get("cr", 0.55), 1, "blast", (cd if k == 0 else 0.09) + 0.07 * k))
        if M.get("chain"):
            n, st = int(M["chain"]), float(M.get("cstep", 7.0))
            d = 1.0 if vx >= 0 else -1.0
            for k in range(1, n + 1):
                bx = clamp(imp.x + d * k * st, 2, W - 3)
                evs.append(Ev(bx, w.terrain.height_at(bx) + 1.0, ImpactKind.TERRAIN, -1, M.get("cr", 0.6), 1, "blast", 0.1))
        if M.get("pierce"):                                          # HARDLIGHT: the lance keeps going, carving a shaft
            sp = math.hypot(vx, vy) or 1.0
            ux, uy, st = vx / sp, vy / sp, float(M.get("pstep", 4.5))
            for k in range(1, int(M["pierce"]) + 1):
                px_, py_ = clamp(imp.x + ux * st * k, 2, W - 3), max(1.0, imp.y + uy * st * k)
                evs.append(Ev(px_, py_, ImpactKind.TERRAIN, -1, 0.55, 1 if k == int(M["pierce"]) else 0, "blast", 0.05))
        if M.get("fuse"):
            evs.append(Ev(imp.x, imp.y, ImpactKind.TERRAIN, -1, M.get("fr", 1.5), int(M.get("dmg", 1)), "blast", float(M["fuse"])))
        return evs

    def after_landing(imp: Impact, t_land: float, vx: float) -> None:
        """Follow-up flights that start where the shell came down (BURROWER, SERPENT, CONSTELLATION)."""
        if special or imp.kind is ImpactKind.OUT:
            return
        if M.get("burrow") and imp.kind is ImpactKind.TERRAIN:       # the worm tunnels just under the surface toward the first foe ahead
            d = 1.0 if vx >= 0 else -1.0
            reach = float(M["burrow"])
            foe = _nearest_foe(w, tank, imp.x, d, reach)
            ex = foe.x if foe is not None else clamp(imp.x + d * reach, 3, W - 4)
            dist = abs(ex - imp.x)
            if dist >= 2:
                y0 = w.terrain.height_at(imp.x) - 2.5
                speed = 34.0
                sub = Launch(imp.x, y0, d * speed, 0.0, 0.0)
                ty = w.terrain.height_at(ex) + 1.0
                kind, ti = (ImpactKind.TANK, foe.index) if foe is not None else (ImpactKind.TERRAIN, -1)
                erupt = Ev(ex, ty, kind, ti, M.get("radius", 1.3), int(M.get("dmg", 1)), "blast", 0.0, False)
                flights.append(FlightSpec(sub, TraceResult(Impact(ex, y0, ImpactKind.OUT), [], dist / speed), t_land + 0.25, [erupt]))
        if M.get("slither") and imp.kind is ImpactKind.TERRAIN:      # hops that steer toward the nearest enemy
            x, y, t0 = imp.x, imp.y, t_land
            for k in range(int(M["slither"])):
                foe = _nearest_foe(w, tank, x)
                if foe is None or imp.kind is ImpactKind.OUT:
                    break
                dx = foe.x - x
                hop = clamp(abs(dx), 4.0, 16.0)
                vy0 = 26.0
                tf = 2 * vy0 / max(1e-3, L.g)
                sub = Launch(x, y + 1.5, math.copysign(hop / tf, dx), vy0, L.g, 0.0)
                st = phys.trace(sub, probe(), 0.02, 0.0, 6.0)
                last = k == int(M["slither"]) - 1
                flights.append(FlightSpec(sub, st, t0 + 0.12, [main_ev(st.impact, False, M.get("radius", 0.9) if last else 0.55)]))
                t0 += 0.12 + st.time
                x, y = st.impact.x, st.impact.y
                if st.impact.kind is not ImpactKind.TERRAIN:
                    break
        if M.get("stars"):                                           # a pentagon of stars falls from the top of the sky
            n = int(M["stars"])
            for k in range(n):
                ang = math.pi / 2 + k * math.tau / n
                sx = clamp(imp.x + math.cos(ang) * 15.0, 3, W - 4)
                top = w.height + 4.0
                sub = Launch(sx + 4.0, top, -4.0, -48.0, L.g, 0.0)
                st = phys.trace(sub, probe(), 0.02, 0.0, 8.0)
                flights.append(FlightSpec(sub, st, t_land + 0.3 + 0.14 * k, [main_ev(st.impact, False, 0.65, "blast")]))

    apex = M.get("apex")
    t_ap = L.vy / L.g if L.g > 0 else 0.0
    if apex and 0.35 < t_ap < tr.time - 0.2:
        ax, ay = L.at(t_ap)
        vxa, vya = L.vx + L.ax * t_ap, L.vy - L.g * t_ap
        if apex[0] == "mirror":                                      # PARADOX: the shell flies on; its twin falls across the centre line
            vxi, vyi = L.vx + L.ax * tr.time, L.vy - L.g * tr.time
            flights.append(FlightSpec(L, tr, 0.0, finale(tr.impact, True, vxi, vyi)))
            mx = clamp(W - ax, 4, W - 5)
            twin = replace(L, x0=mx, y0=ay, vx=-vxa, vy=vya, ax=-L.ax, wa=0.0)
            st = phys.trace(twin, probe(), 0.02, 0.0, 12.0)
            flights.append(FlightSpec(twin, TraceResult(Impact(mx, ay, ImpactKind.OUT), [], 0.0), t_ap, [Ev(mx, ay, ImpactKind.OUT, -1, 0.5, 0, "fx")]))
            flights.append(FlightSpec(twin, st, t_ap + 0.02, [main_ev(st.impact, False, M.get("radius", 1.0))]))
            return flights
        portal = [Ev(ax, ay, ImpactKind.OUT, -1, 0.5, 0, "fx")] if apex[0] == "jump" else []
        flights.append(FlightSpec(L, TraceResult(Impact(ax, ay, ImpactKind.OUT), [], t_ap), 0.0, portal))
        if apex[0] == "split":
            n, spread = int(apex[1]), float(apex[2])
            for k in range(n):
                f = (k - (n - 1) / 2) / max(1.0, (n - 1) / 2)
                sub = replace(L, x0=ax + f * 1.5, y0=ay, vx=vxa * (1 + spread * f) + f * spread * 6, vy=vya + 1.0 - abs(f) * 3.0, wa=0.0)
                if M.get("seek"):
                    sub = _reaim(w, tank, sub, sub.x0, sub.y0, sub.vx, sub.vy, float(M["seek"]))
                st = phys.trace(sub, probe(), 0.02, 0.0, 12.0)
                flights.append(FlightSpec(sub, st, t_ap + 0.04 * k, [main_ev(st.impact, k == 0, M.get("subr", 0.6), "blast")]))
            return flights
        dirx = 1.0 if vxa >= 0 else -1.0
        nx = clamp(ax + dirx * float(apex[1]), 4, W - 5)
        sub = replace(L, x0=nx, y0=ay, vx=vxa, vy=vya, wa=0.0)
        st = phys.trace(sub, probe(), 0.02, 0.0, 12.0)
        flights.append(FlightSpec(sub, TraceResult(Impact(nx, ay, ImpactKind.OUT), [], 0.0), t_ap + 0.1,
                                  [Ev(nx, ay, ImpactKind.OUT, -1, 0.5, 0, "fx")]))
        flights.append(FlightSpec(sub, st, t_ap + 0.12, finale(st.impact, True, vxa)))
        return flights
    if M.get("seek") and 0.35 < t_ap < tr.time - 0.2:              # ANGLER'S LURE: at the top of the arc the lure turns toward its prey
        ax, ay = L.at(t_ap)
        vxa, vya = L.vx + L.ax * t_ap, L.vy - L.g * t_ap
        flights.append(FlightSpec(L, TraceResult(Impact(ax, ay, ImpactKind.OUT), [], t_ap), 0.0, [Ev(ax, ay, ImpactKind.OUT, -1, 0.35, 0, "fx")]))
        sub = _reaim(w, tank, L, ax, ay, vxa, vya, float(M["seek"]))
        st = phys.trace(sub, probe(), 0.02, 0.0, 12.0)
        flights.append(FlightSpec(sub, st, t_ap, finale(st.impact, True, sub.vx, -1.0)))
        after_landing(st.impact, t_ap + st.time, sub.vx)
        return flights
    if M.get("volley"):                                              # BROADSIDE: short, true and long, fired together
        n = int(M["volley"])
        for k in range(n):
            f = (k - (n - 1) / 2) * 0.085
            sub = replace(L, vx=L.vx * (1 + f), vy=L.vy * (1 + f))
            st = phys.trace(sub, probe(), 0.02, 0.0, 12.0)
            flights.append(FlightSpec(sub, st, 0.11 * k, [main_ev(st.impact, k == (n - 1) // 2, M.get("radius", 0.8))]))
        return flights
    bounces, cur, st, tcum = int(M.get("bounce", 0)), L, tr, 0.0
    for b in range(bounces + 1):
        imp = st.impact
        vxi, vyi = cur.vx + cur.ax * st.time, cur.vy - cur.g * st.time
        last = b == bounces or imp.kind is not ImpactKind.TERRAIN or vyi > -4
        if last and M.get("burrow") and imp.kind is ImpactKind.TERRAIN and not special:
            evs = [Ev(imp.x, imp.y, imp.kind, imp.tank, 0.5, int(M.get("dmg", 1)), "trench", 0.0, b == 0)]       # the worm's entry hole
        else:
            evs = finale(imp, b == 0, vxi, vyi) if last else [Ev(imp.x, imp.y, ImpactKind.TERRAIN, -1, M.get("br", 0.4), 1, "blast", 0.0, b == 0)]
        flights.append(FlightSpec(cur, st, tcum, evs))
        tcum += st.time
        if last:
            after_landing(imp, tcum, vxi)
            break
        cur = replace(cur, x0=imp.x, y0=imp.y + 1.5, vx=vxi * 0.82, vy=-vyi * 0.55)
        st = phys.trace(cur, probe(), 0.02, 0.0, 12.0)
    return flights


class BlessingFX:
    """MARTYR'S BLESSING, a four-act spectacle drawn on terminal cells (no raw output, nothing to restore):
      I   THE CLOCK  - an enormous Roman-numeral dial opens around the impact; hands sweep, rings turn.
      II  THE SUN    - 24 stars (12 that duplicate into 24) spiral in from the dial and fuse into a swelling golden sun.
      III THE JUDGMENT - the sun cracks; a reticle marks each victim, then a column of light falls on it. Tanks are struck first,
                         then pillars sweep outward across half the battlefield, each one carving a real crater.
      IV  THE FINALE - the dial implodes into the centre and a colossal white nova erases what is left.
    Everything is bounded (<=12 numerals, 4 rings, 24 stars, <=MAXT pillars) and `full=False` (SCREEN EFFECTS off) keeps the same
    gameplay beats on a short, calm timeline. Gameplay (kills, craters) is applied by BattleScene from the events below."""
    ROMAN = ("XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI")
    GOLDC, VIOLET, PURPLE, WHITEC = (255, 214, 90), (176, 120, 255), (104, 46, 180), (255, 255, 255)
    CHAIN_N, MAXT = 12, 14

    def __init__(self, wx: float, wy: float, targets: list, full: bool = True, wipes: tuple = ()) -> None:
        self.wx, self.wy, self.full, self.t = wx, wy, full, 0.0
        self.targets = list(targets)[:self.MAXT]                     # (world x, world y, tank index or None): victims first
        self.wipes = list(wipes)[:16]                                # (world x, world y): the final firewall's craters across the whole field
        if full:
            self.T_SUN, self.T_BANG, self.first, self.gap, self.tel, tail = 1.6, 3.0, 0.7, 0.1, 0.6, 2.6
        else:
            self.T_SUN, self.T_BANG, self.first, self.gap, self.tel, tail = 99.0, 0.4, 0.2, 0.04, 0.2, 0.5
        self.arrive = [self.T_BANG + self.first + self.gap * i for i in range(len(self.targets))]
        self.T_CONV = (max(self.arrive) if self.arrive else self.T_BANG) + 0.45        # the finale (the nuke) starts here
        self.wipe_t = [self.T_CONV + 0.05 + abs(x - wx) / (55.0 if full else 400.0) for x, _ in self.wipes]
        self.T_END = max([self.T_CONV + tail] + [w_ + 0.7 for w_ in self.wipe_t])
        self.skipped, self._fired = False, set()

    def skip(self) -> None:
        """Jump to the end. Every hit and the finale still resolve (the scene applies them instantly, without the spectacle)."""
        self.skipped = True
        self.t = max(self.t, self.T_END)

    def events(self) -> list:
        keys = [("bang", self.T_BANG)] + [(f"hit{i}", a) for i, a in enumerate(self.arrive)] + [("finale", self.T_CONV)] \
            + [(f"wipe{i}", w_) for i, w_ in enumerate(self.wipe_t)]
        out = []
        for key, when in keys:
            if key not in self._fired and self.t >= when:
                self._fired.add(key)
                if not self.skipped or key.startswith(("hit", "wipe")) or key == "finale":
                    out.append(key)
        return out

    @staticmethod
    def _c(v: int, lo: int, hi: int) -> int:
        return (lo + hi) // 2 if lo > hi else max(lo, min(hi, v))

    def draw(self, screen: "Screen", L: "Layout", cell_of: Callable) -> None:
        t, full = self.t, self.full
        ry = max(3, min(L.frows // 2 - 1, 12))
        rx = max(6, min(ry * 2 + 2, L.fcols // 2 - 3))
        ix, iy = cell_of(self.wx, self.wy)
        cx = self._c(ix, L.fx + rx + 2, L.fx + L.fcols - rx - 3)
        cy = self._c(iy, L.fy + ry + 1, L.fy + L.frows - ry - 2)
        compact = L.fcols < 46 or L.frows < 16                      # narrow/short terminals: four numerals instead of twelve
        x0, y0, x1, y1 = L.fx, L.fy, L.fx + L.fcols, L.fy + L.frows
        G, V, P, W = self.GOLDC, self.VIOLET, self.PURPLE, self.WHITEC

        def put(x: int, y: int, ch: str, col: RGB) -> None:
            if x0 <= x < x1 and y0 <= y < y1:
                screen.put(x, y, ch, col)

        def text(x: int, y: int, s: str, col: RGB) -> None:
            for j, ch in enumerate(s):
                put(x + j, y, ch, col)

        def ellipse(px: int, py: int, ax: float, ay: float, fade: float, hot: RGB) -> None:      # filled glowing blob
            for dy in range(-int(ay) - 1, int(ay) + 2):
                for dx in range(-int(ax) - 1, int(ax) + 2):
                    d = math.hypot(dx / max(0.5, ax), dy / max(0.5, ay))
                    if d <= 1.0:
                        put(px + dx, py + dy, "█▓▒░"[min(3, int(d * 4))], mix(gradient(((0.0, W), (0.35, hot), (0.75, V), (1.0, P)), d), P, 0.8 * (1 - fade)))

        def ring(px: int, py: int, ax: float, ay: float, n: int, col: RGB, fade: float, glyphs: str = "○◦") -> None:
            for j in range(n):
                a = j * math.tau / n
                put(px + int(round(math.cos(a) * ax)), py + int(round(math.sin(a) * ay)), glyphs[j % len(glyphs)], shade(col, fade))

        conv = clamp((t - self.T_CONV) / max(0.01, self.T_END - self.T_CONV), 0, 1) if full else 0.0
        k = ease_out(clamp(t / 1.0, 0, 1)) * (1 - conv * conv)
        screen.tint(x0, y0, L.fcols, L.frows, (46, 12, 104), 0.40 * clamp(t / 0.8, 0, 1) * (1 - 0.6 * conv))

        # I - the clock: two turning rings, 12 numerals (4 on small screens), sweeping hands
        for ri, (f, col, ch, dr) in enumerate(((1.0, G, "·", 1), (0.86, V, "•", -1), (0.62, G, "·", 1), (0.3, P, "◦", -1))):
            n = int(clamp(math.tau * rx * f * 0.9, 24, 140))
            for j in range(n):
                a = j * math.tau / n + dr * t * (0.35 + 0.2 * ri)
                mark = "✧" if j % 10 == 0 else ch
                put(cx + int(round(math.sin(a) * rx * f * k)), cy - int(round(math.cos(a) * ry * f * k)), mark,
                    shade(col, 0.55 + 0.45 * math.sin(t * 5 + j * 0.7) ** 2) if mark == ch else W)
        for i, rn in enumerate(self.ROMAN):
            if (compact and i % 3) or t < 0.25 + i * 0.06:
                continue
            a = i * math.tau / 12 + t * 0.18
            lit = (int(t * 3) % 12) == i and conv == 0
            text(cx + int(round(math.sin(a) * rx * 0.93 * k)) - len(rn) // 2, cy - int(round(math.cos(a) * ry * 0.93 * k)), rn, W if lit else G)
        for length, spd, col in ((0.55, 2.4, G), (0.82, 0.8, W)):
            ha = t * spd * (1 - conv)
            for s in range(1, 13):
                f = s / 12 * length * k
                put(cx + int(round(math.sin(ha) * rx * f)), cy - int(round(math.cos(ha) * ry * f)), "•" if s % 3 else "◦", col)
        if rx >= 8 and L.frows >= 10:
            title = "M A R T Y R ' S   B L E S S I N G"
            if len(title) > L.fcols - 2:
                title = "MARTYR'S BLESSING"[:max(0, L.fcols - 2)]
            text(x0 + (L.fcols - len(title)) // 2, y0 + 1, title, mix(P, G, 0.5 + 0.5 * math.sin(t * 6)))
            if t >= self.T_BANG and conv < 1 and L.frows >= 14:
                sub = "TIME RECEIVES ITS FINAL JUDGMENT"[:max(0, L.fcols - 2)]
                text(x0 + (L.fcols - len(sub)) // 2, y0 + 2, sub, W)

        # II - the sun: one clean spiral of stars (12, then 24 after the duplication) winds into a swelling golden sun
        if full and self.T_SUN <= t < self.T_BANG:
            u_all = clamp((t - self.T_SUN) / (self.T_BANG - self.T_SUN), 0, 1)
            twin = 2 if t >= self.T_SUN + 0.6 else 1
            for j in range(12 * twin):
                u = clamp(u_all * 1.15 - (j % 12) * 0.02, 0, 1)
                ang = (j % 12) * math.tau / 12 + (math.pi / 12 if j >= 12 else 0) + u * 5.5
                r = (1 - u) ** 1.4
                put(cx + int(round(math.cos(ang) * rx * 0.95 * r)), cy + int(round(math.sin(ang) * ry * 0.95 * r)),
                    "✦" if j < 12 else "✧", G if j < 12 else W)
            sr = ease_out(u_all)
            ellipse(cx, cy, rx * 0.34 * sr, ry * 0.34 * sr, 1.0, G)
        # III - the judgment
        if full and t >= self.T_BANG:
            b = t - self.T_BANG
            if b < 0.9:                                                          # the crack: flash, flare, shock ring
                ellipse(cx, cy, rx * 0.34 * (1 - b / 0.9) + 1, ry * 0.34 * (1 - b / 0.9) + 1, 1 - b / 0.9, W)
                rs = ease_out(clamp(b / 0.7, 0, 1))
                ring(cx, cy, rx * 1.05 * rs, ry * 1.05 * rs, 64, mix(W, G, b / 0.9), 1 - b / 0.9)
                for j in range(8):
                    a = j * math.pi / 4
                    for s in range(2, int(2 + 8 * rs)):
                        put(cx + int(round(math.cos(a) * s * 2)), cy - int(round(math.sin(a) * s)), "✦" if s == int(7 * rs) else "·", G if j % 2 else W)
            for j in range(40):                                                          # shooting stars fly out of the clock in every direction
                age = t - (self.T_BANG + 0.12 * j)
                if 0 <= age < 1.0:
                    a = j * 2.399 + 0.4                                                  # golden-angle spread: even coverage, never a clump
                    spd = 34 + (j % 5) * 9
                    for tr in range(7):
                        a2 = max(0.0, age - tr * 0.025)
                        put(int(round(cx + math.cos(a) * spd * a2 * 1.7)), int(round(cy + math.sin(a) * spd * a2 * 0.55 - a2 * a2 * 10)),
                            "✦" if tr == 0 else "·", shade(G if j % 3 else W if j % 3 == 0 else V, 1 - tr * 0.13))
            top = y0 + 3
            for i, (tgt, arr) in enumerate(zip(self.targets, self.arrive)):
                ex, ey = cell_of(tgt[0], tgt[1])
                ex, ey = int(clamp(ex, x0 + 2, x1 - 3)), int(clamp(ey, y0 + 4, y1 - 2))
                vic = tgt[2] is not None
                age = t - arr
                if -self.tel <= age < -0.12:                                         # the reticle contracts onto the victim
                    p = 1 - (age + self.tel) / (self.tel - 0.12)
                    rr = 2 + (1 - p) * 7
                    ring(ex, ey, rr * 2, rr * 0.7, 16, G if int(t * 12) % 2 else W, 0.5 + 0.5 * p)
                    put(ex, ey, "✛", W)
                if -0.12 <= age < 0.45:                                              # the pillar of light
                    drop = clamp((age + 0.12) / 0.12, 0, 1)
                    head = int(top + (ey - top) * drop)
                    wide = 2 if vic else 1
                    fade = 1.0 if age < 0.12 else clamp(1 - (age - 0.12) / 0.33, 0, 1)
                    for yy in range(top, head + 1):
                        put(ex, yy, "┃", shade(W, 0.5 + 0.5 * fade))
                        for sdx in range(1, wide + 1):
                            c = mix(G, V, (sdx - 1) / max(1, wide))
                            put(ex - sdx, yy, "│" if sdx == 1 else "╎", shade(c, 0.35 + 0.5 * fade))
                            put(ex + sdx, yy, "│" if sdx == 1 else "╎", shade(c, 0.35 + 0.5 * fade))
                    put(ex, head, "▼", W)
                if 0 <= age < 0.9:                                                   # the strike: twin shock rings, rising sparks
                    sw = (2 + age * (22 if vic else 15)) * ease_out(clamp(age / 0.5, 0, 1) + 0.2)
                    ring(ex, ey, sw, sw * 0.4, 24, G, 1 - age / 0.9)
                    if vic and age > 0.08:
                        ring(ex, ey, sw * 0.62, sw * 0.25, 16, V, 1 - age / 0.9, "◦•")
                    for j in range(6 if vic else 4):
                        a = j * math.pi / (3 if vic else 2) + 0.3
                        put(ex + int(round(math.cos(a) * age * 11)), ey - int(round(abs(math.sin(a)) * age * 9 - age * age * 12)), "✦", W if j % 2 else G)
        # IV - the finale, a nuclear end of the world: the dial implodes, white-out, a rising mushroom cloud and a firewall racing
        #      across the whole field (each wall-front crater is a real one: see the wipe events)
        if full and t >= self.T_CONV:
            f = t - self.T_CONV
            if conv > 0:
                for j in range(24):
                    a = j * math.tau / 24
                    put(cx + int(round(math.sin(a) * rx * (1 - conv))), cy - int(round(math.cos(a) * ry * (1 - conv))), "✦", W)
            base = min(y1 - 2, cy + ry + 2)                                        # the ground the cloud grows from
            if f < 0.5:                                                            # white-out fireball
                ellipse(cx, base, rx * (0.6 + 2.2 * f), ry * (0.5 + 1.6 * f), 1 - f / 0.5 * 0.4, W)
            p = ease_out(clamp(f / 2.2, 0, 1))
            fade = 1 - clamp((f - 2.0) / 1.2, 0, 1)
            top_y = int(base - (base - (y0 + 4)) * 0.8 * p)
            if f > 0.15 and fade > 0:
                for yy in range(top_y, base + 1):                                  # the stem: hot at the core, rolling smoke at the edges
                    sw = max(2, int(2 + (1 - (yy - top_y) / max(1, base - top_y)) * 2 + (yy - top_y) / max(1, base - top_y) * 5))
                    for dx in range(-sw, sw + 1):
                        u = abs(dx) / max(1, sw)
                        put(cx + dx, yy, "█▓▒░"[min(3, int(u * 4))], shade(gradient(((0, (255, 226, 150)), (0.5, (255, 110, 30)), (1, (120, 28, 18))), u), 0.5 + 0.5 * fade))
                cap_rx, cap_ry = rx * 1.25 * p + 4, ry * 0.95 * p + 2                  # the cap: a boiling mushroom of fire
                for dy in range(-int(cap_ry) - 1, int(cap_ry) + 2):
                    for dx in range(-int(cap_rx) - 1, int(cap_rx) + 2):
                        d = math.hypot(dx / cap_rx, dy / cap_ry + 0.25 * math.sin(dx * 0.4 + t * 6) * 0.3)
                        if d <= 1.0:
                            put(cx + dx, top_y + dy, "█▓▒░"[min(3, int(d * 4))],
                                shade(gradient(((0, (255, 240, 190)), (0.3, (255, 130, 36)), (0.7, (210, 48, 20)), (1, (60, 18, 30))), d), 0.4 + 0.6 * fade))
            for sgn in (-1, 1):                                                   # the firewall sweeping the whole field
                wx_ = cx + sgn * int(f * 55)
                if x0 <= wx_ < x1 and f < 2.5:
                    for yy in range(y0 + 2, y1 - 1):
                        k_ = (yy * 7 + int(t * 20)) % 5
                        for th_ in range(7):                                         # a wall of fire: white-hot front, cooling trail behind it
                            put(wx_ - sgn * th_, yy - (th_ + k_) % 2, "█▓▓▒▒░░"[th_],
                                shade(mix((255, 245, 200), (190, 50, 20), th_ / 6), 0.55 + 0.45 * ((k_ + th_) % 3) / 2))
        if t > self.T_END - 0.3:                                                    # cosmic flash marks the end
            screen.tint(x0, y0, L.fcols, L.frows, W, clamp((t - (self.T_END - 0.3)) / 0.3, 0, 1) * 0.85)


class LiveFlight:
    """A flight currently animating on screen."""
    def __init__(self, spec: FlightSpec, owner: int) -> None:
        self.spec, self.delay = spec, spec.delay
        self.proj = Projectile(spec.launch, owner, lambda x, y: None)
        self.last = (spec.launch.x0, spec.launch.y0)
        self.n = 0
