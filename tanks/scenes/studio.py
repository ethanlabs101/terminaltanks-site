"""The TANK STUDIO (preview any tank anywhere; nothing is saved) and the WORKSHOP (build custom tanks)."""
from __future__ import annotations

import textwrap
from typing import Callable

from tanks.colors import GOLD, Palette, clamp
from tanks.content.ammo import AMMOS, AMMO_BY_KEY, ANCIENT_AMMOS, DEFAULT_AMMO
from tanks.content.custom import (
    CUSTOM_FALLBACK, CUSTOM_SLOTS, CUSTOM_TANK_FEE, CUSTOM_TANK_MAX, HOVER_COINS, HOVER_CREDITS, design_from_custom,
    workshop_components
)
from tanks.content.maps import all_maps
from tanks.content.paints import COLOR_BY_NAME, PAINTS, live_color, paint_index
from tanks.content.tanks import TankDesign
from tanks.scenes.base import BackdropScene
from tanks.scenes.main_menu import MenuScene
from tanks.screen import Screen
from tanks.terminal import Action, InputEvent
from tanks.ui.preview import PreviewStage
from tanks.ui.widgets import draw_keycaps, wrap_center


class StudioScene(BackdropScene):
    """TANK STUDIO (preview only): pick a real battlefield, a paint, an ammo and a shell colour and watch the tank fire on a loop."""
    ROWS = ("map", "paint", "ammo", "shot", "back")
    SW, SH = 46, 44                                        # preview pixels: 46 x 22 terminal rows

    def music(self):
        return ("workshop", "menu")

    def __init__(self, app, design: "TankDesign", body_name: str, back: Callable) -> None:
        super().__init__(app)
        self.design, self.back = design, back
        self.row, self.msg, self.msg_ok = 0, "", True
        self.maps = list(all_maps().values())
        self.ammos = [a for a in AMMOS + ANCIENT_AMMOS if a.key in app.save.unlocked_ammo()] or [DEFAULT_AMMO]
        lo = app.save.loadout(0)
        self.mi = 0
        self.ai = next((i for i, a in enumerate(self.ammos) if a.key == lo.ammo), 0)
        self.pi, self.si = paint_index(body_name), paint_index(lo.shot_color)
        self.stage = PreviewStage(app.settings, self.SW, self.SH, 2)
        self._map_applied = None

    def _apply(self, stage: "PreviewStage") -> None:
        if self._map_applied is not self.maps[self.mi] or stage is not self.stage:
            stage.set_map(self.maps[self.mi])
            if stage is self.stage:
                self._map_applied = self.maps[self.mi]
        stage.set_kit(self.design, PAINTS[self.pi][1], self.ammos[self.ai], PAINTS[self.si][1], 0.0)

    def handle(self, ev: InputEvent) -> None:
        key = self.ROWS[self.row]
        if ev.action is Action.BACK:
            self.app.goto(self.back())
        elif ev.action is Action.UP:
            self.row = (self.row - 1) % len(self.ROWS)
        elif ev.action is Action.DOWN:
            self.row = (self.row + 1) % len(self.ROWS)
        elif ev.action in (Action.LEFT, Action.RIGHT):
            d = (-1 if ev.action is Action.LEFT else 1) * (5 if ev.coarse else 1)
            if key == "map":
                self.mi = (self.mi + d) % len(self.maps)
            elif key == "paint":
                self.pi = (self.pi + d) % len(PAINTS)
            elif key == "ammo":
                self.ai = (self.ai + d) % len(self.ammos)
            elif key == "shot":
                self.si = (self.si + d) % len(PAINTS)
        elif ev.confirm and key == "back":
            self.app.goto(self.back())

    def update(self, dt: float) -> None:
        super().update(dt)
        self.stage.update(dt)

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        H = 26
        x, y = (screen.cols - 96) // 2, max(0, (screen.rows - H) // 2)
        screen.box(x, y, 44, H, "double", Palette.LINE, Palette.PANEL, "TANK STUDIO")
        sv, t = self.app.save, self.app.time
        pn, sn = PAINTS[self.pi][0], PAINTS[self.si][0]
        lock = lambda n: "" if sv.paint_ok(n, True) else "  (LOCKED)"
        vals = {"map": self.maps[self.mi].name, "paint": pn + lock(pn), "ammo": self.ammos[self.ai].name, "shot": sn + lock(sn),
                "back": "◄  BACK"}
        labels = {"map": "BATTLEFIELD", "paint": "TANK PAINT", "ammo": "AMMO", "shot": "SHELL COLOR", "back": ""}
        for i, key in enumerate(self.ROWS):
            ry, sel = y + 2 + i * 2, i == self.row
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            screen.fill(x + 2, ry, 40, 1, bg)
            screen.text(x + 3, ry, labels[key], Palette.WHITE if sel else Palette.MUTED, bg)
            v = f"◄ {vals[key]} ►" if key in ("map", "paint", "ammo", "shot") and sel else vals[key]
            screen.text(x + 41 - len(v), ry, v[:30], GOLD if sel else Palette.TEXT, bg)
            if key in ("paint", "shot"):
                col = live_color(PAINTS[self.pi if key == "paint" else self.si][1], t)
                screen.text(x + 3, ry + 1, "█" * 8, col, Palette.PANEL)
        pr = y + 15
        tip = ("Paints marked LOCKED are preview-only until you own them." if (not sv.paint_ok(pn, True) or not sv.paint_ok(sn, False))
               else "Preview your tank on any battlefield with any paint, ammo and shell colour. Nothing is saved.")
        wrap_center(screen, pr, tip, 40, Palette.MUTED, Palette.PANEL, x, 44, 4)
        draw_keycaps(screen, x + 3, y + H - 2, (("▲▼", "ROW"), ("◄►", "CHANGE"), ("ENTER", "DO"), ("ESC", "BACK")), Palette.PANEL)
        px = x + 45
        screen.box(px, y, 50, H, "double", Palette.LINE, Palette.PANEL, "LIVE PREVIEW")
        self._apply(self.stage)
        screen.blit(self.stage.render(), px + 2, y + 1)
        screen.center(y + 23, self.design.name, Palette.WHITE, Palette.PANEL, px, 50)
        screen.center(y + 24, f"{self.ammos[self.ai].name}  ·  {self.maps[self.mi].name}"[:46], Palette.MUTED, Palette.PANEL, px, 50)


class WorkshopScene(BackdropScene):
    """Tank Workshop: combine unlocked components, name the tank, write its lore, preview it and build it for a fee."""
    ROWS = ("load", "turret", "hull", "track", "barrel", "glow", "ambient", "accent", "color", "hover", "name", "lore", "build", "equip", "delete")
    LABEL = {"load": "TANK", "turret": "TURRET", "hull": "HULL", "track": "TRACKS", "barrel": "BARREL", "glow": "GLOW", "ambient": "AMBIENT",
             "accent": "ACCENT", "color": "COLOR", "hover": "HOVER", "name": "NAME", "lore": "LORE", "build": "BUILD", "equip": "EQUIP", "delete": "DELETE"}

    def music(self):
        return ("workshop", "menu")

    def __init__(self, app) -> None:
        super().__init__(app)
        self.row, self.msg, self.msg_ok, self.msg_t = 0, "", True, 0.0
        self.stage = PreviewStage(app.settings, 46, 26, 2)
        self.load = 0                                   # 0 = a new design, n = saved tank n
        self.confirm_delete = False
        self.draft = {"parts": dict(CUSTOM_FALLBACK), "name": "MY TANK", "lore": "Built in the workshop.", "hover": False}
        self.opts = workshop_components(app.save)
        self.pcolor = paint_index(app.save.loadout(0).tank_color)        # preview body colour (applied to Player 1 on EQUIP)

    def _toggle_hover(self) -> None:
        if self.app.save.hover_open() or self.draft["hover"]:
            self.draft["hover"] = not self.draft["hover"]
        else:
            self.msg_ok, self.msg, self.msg_t = False, "HOVER OPENS AFTER YOU DEFEAT THE MOTHERSHIP", 2.5

    def _saved(self) -> list:
        return self.app.save.custom_tanks

    def _sync_draft(self) -> None:
        if self.load > 0 and self.load <= len(self._saved()):
            rec = self._saved()[self.load - 1]
            self.draft = {"parts": dict(CUSTOM_FALLBACK, **{k: v for k, v in (rec.get("parts") or {}).items() if k in CUSTOM_SLOTS}),
                          "name": str(rec.get("name", "")), "lore": str(rec.get("lore", "")), "hover": bool(rec.get("hover"))}

    def _design(self) -> TankDesign:
        return design_from_custom({"id": "preview", "name": self.draft["name"] or "CUSTOM", "lore": self.draft["lore"], "parts": self.draft["parts"],
                                   "hover": self.draft["hover"]})

    def _cycle(self, slot: str, d: int) -> None:
        opts = self.opts[slot]
        cur = self.draft["parts"].get(slot, CUSTOM_FALLBACK[slot])
        self.draft["parts"][slot] = opts[(opts.index(cur) + d) % len(opts)] if cur in opts else opts[0]

    def handle(self, ev: InputEvent) -> None:
        key, raw, save = self.ROWS[self.row], ev.raw, self.app.save
        if raw in ("g", "G") and key not in ("name", "lore"):                         # TANK STUDIO: preview booth
            self.app.goto(StudioScene(self.app, self._design(), PAINTS[self.pcolor][0], lambda: WorkshopScene(self.app)))
            return
        if ev.action is Action.BACK:
            self.confirm_delete = False if self.confirm_delete else self.confirm_delete
            if not self.confirm_delete:
                self.app.goto(MenuScene(self.app))
            return
        if key in ("name", "lore") and len(raw) == 1 and raw.isprintable():       # typing: letters never navigate here
            cap = 14 if key == "name" else 60
            if len(self.draft[key]) < cap and (raw.isalnum() or raw in " -.,!'"):
                self.draft[key] += raw.upper() if key == "name" else raw
            return
        if key in ("name", "lore") and raw == "SPACE":
            if len(self.draft[key]) < (14 if key == "name" else 60):
                self.draft[key] += " "
            return
        if raw == "BACKSPACE" and key in ("name", "lore"):
            self.draft[key] = self.draft[key][:-1]
            return
        if ev.action is Action.UP:
            self.row, self.confirm_delete = (self.row - 1) % len(self.ROWS), False
        elif ev.action is Action.DOWN:
            self.row, self.confirm_delete = (self.row + 1) % len(self.ROWS), False
        elif ev.action in (Action.LEFT, Action.RIGHT):
            d = -1 if ev.action is Action.LEFT else 1
            if key == "load":
                self.load = (self.load + d) % (len(self._saved()) + 1)
                self._sync_draft()
            elif key == "color":
                self.pcolor = (self.pcolor + d * (4 if ev.coarse else 1)) % len(PAINTS)
            elif key in self.opts:
                self._cycle(key, d * (5 if ev.coarse else 1))
            elif key == "hover":
                self._toggle_hover()
        elif ev.confirm:
            if key == "hover":
                self._toggle_hover()
            elif key == "build":
                hv = self.draft["hover"]
                why = save.create_custom(self.draft["parts"], self.draft["name"].strip() or "CUSTOM", self.draft["lore"].strip(), hv)
                paid = f"-{CUSTOM_TANK_FEE + (HOVER_COINS if hv else 0):,} COINS" + (f", -{HOVER_CREDITS} CREDITS" if hv and HOVER_CREDITS else "")
                self.msg_ok, self.msg, self.msg_t = (not why), why or f"BUILT: {(self.draft['name'].strip() or 'CUSTOM')}  ({paid})", 3.0
                if not why:
                    self.load = len(save.custom_tanks)
                    self.app._wallet_flash = 1.4
            elif key == "equip" and self.load > 0:
                save.loadouts[0].tank = f"custom:{self._saved()[self.load - 1]['id']}"
                if save.paint_ok(PAINTS[self.pcolor][0], True):
                    save.loadouts[0].tank_color = PAINTS[self.pcolor][0]
                save.flush()
                self.msg_ok, self.msg, self.msg_t = True, "EQUIPPED AS YOUR PLAYER 1 TANK", 2.5
            elif key == "equip":
                self.msg_ok, self.msg, self.msg_t = False, "BUILD IT FIRST - THEN EQUIP", 2.5
            elif key == "delete" and self.load > 0:
                if not self.confirm_delete:
                    self.confirm_delete = True
                    self.msg_ok, self.msg, self.msg_t = False, "ENTER AGAIN TO DELETE FOR GOOD", 3.0
                else:
                    save.delete_custom(self._saved()[self.load - 1]["id"])
                    self.load, self.confirm_delete = 0, False
                    self.msg_ok, self.msg, self.msg_t = True, "TANK DELETED", 2.0
            elif key == "delete":
                self.msg_ok, self.msg, self.msg_t = False, "NOTHING SAVED TO DELETE", 2.0

    def update(self, dt: float) -> None:
        super().update(dt)
        self.stage.update(dt)
        self.msg_t = max(0.0, self.msg_t - dt)

    HELP = ("HOW IT WORKS: you only get parts from tanks you own - every tank you unlock adds its parts. Mix parts, name it, "
            "add lore, BUILD for {fee:,} coins. HOVER (a floating tank, after the Mothership): +{hc:,} coins{hr}.")

    def draw(self, screen: Screen) -> None:
        super().draw(screen)
        save, t = self.app.save, self.app.time
        W, H = 93, 26
        x, y = (screen.cols - W) // 2, max(0, (screen.rows - H) // 2)
        screen.box(x, y, 44, H, "double", Palette.LINE, Palette.PANEL, "TANK WORKSHOP")
        for i, key in enumerate(self.ROWS):
            ry, sel = y + 2 + i, i == self.row
            bg = Palette.PANEL_HI if sel else Palette.PANEL
            screen.fill(x + 2, ry, 40, 1, bg)
            screen.text(x + 3, ry, f"{self.LABEL[key]:<8}", Palette.WHITE if sel else Palette.MUTED, bg)
            if key == "load":
                val = "NEW DESIGN" if self.load == 0 else f"{self.load}/{len(self._saved())}  {self._saved()[self.load - 1].get('name', '')[:14]}"
            elif key in self.opts:
                val = self.draft["parts"].get(key, "-").upper().replace("_", " ")
            elif key == "hover":
                val = ("ON" if self.draft["hover"] else "OFF") if self.app.save.hover_open() else "LOCKED - BEAT THE MOTHERSHIP"
            elif key == "color":
                nm, cc = PAINTS[self.pcolor]
                val = nm + ("" if self.app.save.paint_ok(nm, True) else " (LOCKED)")
                screen.text(x + 12, ry, "████", live_color(cc, self.app.time), bg)
            elif key == "name":
                val = self.draft["name"] + ("█" if sel and int(t * 2) % 2 == 0 else "")
            elif key == "lore":
                val = (self.draft["lore"] + ("█" if sel and int(t * 2) % 2 == 0 else ""))[-26:]
            elif key == "build":
                val = f"▶ {CUSTOM_TANK_FEE + (HOVER_COINS if self.draft['hover'] else 0):,} COINS" + (f" +{HOVER_CREDITS}CR" if self.draft["hover"] else "")
            elif key == "equip":
                val = "▶ USE AS P1"
            else:
                val = "▶ REMOVE" if not self.confirm_delete else "▶ SURE?"
            val = f"◄ {val} ►" if sel and key in ("load", "hover", "color") + tuple(self.opts) else val
            screen.text(x + 41 - len(val), ry, val[:30], GOLD if sel else Palette.TEXT, bg)
        my = y + 3 + len(self.ROWS)
        if self.msg_t > 0:
            wrap_center(screen, my, self.msg, 40, Palette.OK if self.msg_ok else Palette.DANGER, Palette.PANEL, x, 44, 2)
        else:
            screen.center(my, f"{len(save.custom_tanks)}/{CUSTOM_TANK_MAX} SAVED", Palette.MUTED, Palette.PANEL, x, 44)
        for k, ln in enumerate(textwrap.wrap(self.HELP.format(fee=CUSTOM_TANK_FEE, hc=HOVER_COINS, hr=f" and +{HOVER_CREDITS} credits" if HOVER_CREDITS else ""), 40)[:4]):
            screen.text(x + 2, my + 1 + k, ln, Palette.MUTED, Palette.PANEL)
        draw_keycaps(screen, x + 3, y + H - 2, (("▲▼", "ROW"), ("◄►", "PART"), ("ENTER", "DO"), ("ESC", "BACK")), Palette.PANEL)
        # preview
        px = x + 45
        screen.box(px, y, 48, H, "double", Palette.LINE, Palette.PANEL, "PREVIEW  ·  [G] STUDIO")
        d = self._design()
        lo = save.loadout(0)
        self.stage.set_kit(d, PAINTS[self.pcolor][1], AMMO_BY_KEY[lo.ammo], COLOR_BY_NAME[lo.shot_color], 0.0)
        screen.blit(self.stage.render(), px + 1, y + 1)
        screen.center(y + 14, d.name, Palette.WHITE, Palette.PANEL, px, 48)
        wrap_center(screen, y + 15, d.blurb, 44, Palette.TEXT, Palette.PANEL, px, 48, 2)
        amb = d.ambient.upper().split("+")
        line = f"{d.barrel.upper()}  ·  {d.glow.upper()}  ·  {'+'.join(amb)}"
        while len(line) > 44 and len(amb) > 1:                     # list as many aura parts as fit, then count the rest
            amb = amb[:-1]
            line = f"{d.barrel.upper()}  ·  {d.glow.upper()}  ·  {'+'.join(amb)} +{len(d.ambient.split('+')) - len(amb)}"
        screen.center(y + 17, line, Palette.MUTED, Palette.PANEL, px, 48)
        screen.center(y + 18, f"YOU HAVE {save.coins:,} ◉  {save.credits} CR", GOLD if save.coins >= CUSTOM_TANK_FEE else Palette.DANGER, Palette.PANEL, px, 48)
        # browsable list of every custom tank
        saved = self._saved()
        screen.text(px + 2, y + 19, f"MY TANKS  {len(saved)}/{CUSTOM_TANK_MAX}", Palette.AMBER, Palette.PANEL)
        hint = "◄► ON TANK ROW TO BROWSE"
        screen.text(px + 46 - len(hint), y + 19, hint, Palette.MUTED, Palette.PANEL)
        total, vis = len(saved) + 1, 5
        top = int(clamp(self.load - vis // 2, 0, max(0, total - vis)))
        equipped = save.loadouts[0].tank
        for r in range(vis):
            i = top + r
            if i >= total:
                break
            cur = i == self.load
            bg = Palette.PANEL_HI if cur else Palette.PANEL
            screen.fill(px + 2, y + 20 + r, 44, 1, bg)
            if i == 0:
                label = "+ NEW DESIGN"
            else:
                rec = saved[i - 1]
                label = f"{i:02d} {str(rec.get('name', ''))[:22]}" + ("  ★ EQUIPPED" if equipped == f"custom:{rec['id']}" else "")
            screen.text(px + 3, y + 20 + r, ("▶ " if cur else "  ") + label, Palette.WHITE if cur else Palette.TEXT, bg)
        if top > 0:
            screen.put(px + 45, y + 20, "▲", Palette.PRIMARY_DIM, Palette.PANEL)
        if top + vis < total:
            screen.put(px + 45, y + 24, "▼", Palette.PRIMARY_DIM, Palette.PANEL)
