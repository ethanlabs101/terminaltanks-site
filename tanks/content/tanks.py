"""Tank designs. A design is an 11x6 pixel mask, usually composed from a turret, hull and track (TURRETS / HULLS /
TRACKS), plus a barrel, glow, ambient particles and accent colour. DESIGNS = 5 starters + the 20 Tournament tanks;
SHOP_DESIGNS are sold in tiers of 15 then premium; mission, ticket and ancient designs are earned. Keys are saved:
never rename one."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tanks.colors import RGB
from tanks.config import TANK_H, TANK_W


@dataclass(frozen=True)
class TankDesign:
    key: str
    name: str
    blurb: str
    mask: tuple
    barrel: str = "single"      # a key of BARRELS
    glow: str = "none"          # animation of 'l' pixels: a key of GLOW_STYLES
    ambient: str = "none"       # particle flavour(s): keys of AMBIENT_KINDS joined with '+', e.g. "fire+smoke"
    accent: RGB = (236, 242, 250)
    paint: Optional[RGB] = None  # intrinsic body colour: when set the design looks the same whatever hull colour is picked
    parts: tuple = ()           # (turret, hull, track) component ids when the mask was composed from components
    hover: float = 0.0          # >0: the tank floats this many pixels above the ground (shadow, bob and thruster are drawn)


TURRETS = {
    "dome": ("...ttttt...", "..ttttttt.."), "box": ("..ttttttt..", ".ttttttttt."), "twin": ("..tt.t.tt..", ".ttttttttt."),
    "spike": ("a...ttt...a", ".a.ttttt.a."), "wide": (".ttttttttt.", "ttttttttttt"), "crown": ("a.a.ttt.a.a", ".attttttta."),
    "needle": ("....ttt....", "...ttttt..."), "visor": ("..ttttttt..", ".tlllllllt."), "coil": ("..a.ttt.a..", "..attltta.."),
}
HULLS = {
    "plain": (".hhhhhhhhg.", "hhhhhhhhhhh"), "plate": ("hhhhhhhhhhg", "hdhhhdhhhdh"), "core": (".hhhhhhhhg.", "hhhllllhhhh"),
    "stripe": (".hdhdhdhdhg", "hdhdhdhdhdh"), "wedge": ("..hhhhhhhgg", ".hhhhhhhhh."), "armor": ("hhhhhhhhhhg", "dhhhlhhhdhh"),
    "jewel": (".hhhhhhhhg.", "hallhhhllah"), "vent": ("hhhhhhhhhhg", "hlhlhlhlhlh"), "slab": ("hhhhhhhhhhg", "hhhhdhdhhhh"),
    "royal": (".hhhhhhhhg.", "hallllllhah"),
}
TRACKS = {
    "std": ("kwkwkwkwkwk", ".kkkkkkkkk."), "full": ("kwkwkwkwkwk", "kkkkkkkkkkk"), "round": (".kwkwkwkwk.", "..kkkkkkk.."),
    "spike": ("kdkwkwkwkdk", "kkkkkkkkkkk"), "heavy": ("kkwkkwkkwkk", "kkkkkkkkkkk"),
}


TURRETS.update({
    "antenna": ("....t.t....", "..ttttttt.."), "mushroom": (".tttttttt..", "...ttttt..."), "stair": ("......ttt..", "..ttttttt.."),
    "split": ("..tt...tt..", "..tt.t.tt.."), "pillbox": ("..ttttttt..", "..ttttttt.."), "ridge": ("...t.t.t...", ".ttttttttt."),
    "helm": ("...ttttt...", ".tttlllttt."), "radar": ("..t.ttt.t..", "...ttttt..."), "fin": ("a.........a", ".attttttta."),
    "orb": ("...ttttt...", "..tlllllt.."), "horns": ("t.........t", ".tt.ttt.tt."), "dish": (".t.......t.", "..ttttttt.."),
    "sail": ("......t....", "..tttttt..."), "rear": ("..ttt......", "..tttttttt."), "bubble": ("....ttt....", "...ttttt..."),
    "tower": ("...ttttt...", "...ttttt..."),
    # premium vocabulary: crystal (p/q), furnace flame (f/e), void (v), storm (b), clockwork gold (y)
    "crystal": ("....ppp....", "..pqpppqp.."), "shard": ("....q......", "..pppqppp.."), "furnace": ("a..f.f.f..a", "..tteeett.."),
    "inferno": ("f.f.fff.f.f", ".ttteeettt."), "singularity": ("...vvvvv...", "..vvhvhvv.."), "tesla": ("b....b....b", ".tbttttttbt"),
    "clock": ("...yyyyy...", "..yttyttyy."),
})
HULLS.update({
    "ramp": ("...hhhhhhgg", ".hhhhhhhhhh"), "wide": ("hhhhhhhhhhg", "hhhhhhhhhhh"), "hex": ("..hhhhhhhg.", ".hhhhhhhhhh"),
    "ribbed": (".hhhhhhhhg.", "hdhdhdhdhdh"), "boat": ("hhhhhhhhhgg", ".hhhhhhhhh."), "bunker": ("hhhhhhhhhhg", "hddhhhhhddh"),
    "lattice": (".hdhhdhhdhg", "hhdhhdhhdhh"), "keel": (".hhhhhhhhg.", "..hhhhhhh.."), "domehull": ("..hhhhhhhg.", "hhhhhhhhhhh"),
    "saddle": ("hh.hhhhh.hg", "hhhhhhhhhhh"), "spined": ("ahahahahahg", "hhhhhhhhhhh"), "glowband": ("hhhhhhhhhhg", "hlllllllllh"),
    "cradle": (".h.hhhhh.hg", "hhhhhhhhhhh"),
    "crystal_h": ("..ppqpppp.g", ".ppppqpppp."), "forge_h": ("hheehheehhg", "heeeheeehhh"), "event_h": (".vvvhhhvvg.", "vvhvvvvhvvv"),
    "storm_h": ("hhhbhhhbhhg", "hbhhhbhhhbh"), "chrono_h": ("hhyhhhhyhhg", "hyhhhhhhyhh"),
})
TRACKS.update({
    "tread": ("kkkkkkkkkkk", "kwkwkwkwkwk"), "stilts": (".k.......k.", "kk.......kk"), "skids": ("kk.......kk", ".kkkkkkkkk."),
    "wheels": (".kk.kk.kk..", ".kk.kk.kk.."), "spiked": ("kdkdkdkdkdk", "kkkkkkkkkkk"), "pods": ("..kk...kk..", ".kkkk.kkkk."),
    "lowtread": (".kkkkkkkkk.", "kwkwkwkwkwk"), "hoverpad": ("..k.....k..", ".kkk...kkk."),
    "crystal_t": ("..pq...qp..", ".pppqpqppp."), "ember_t": ("kekekekekek", "kkkkkkkkkkk"), "void_t": ("..vv...vv..", ".vvvv.vvvv."),
    "arc_t": ("kbkwkwkbkwk", "kkkkkkkkkkk"), "gold_t": ("kykwkwkwkyk", "kkkkkkkkkkk"),
})
assert all(len(r) == 11 for part in (TURRETS, HULLS, TRACKS) for rows in part.values() for r in rows) \
    and all(len(rows) == 2 for part in (TURRETS, HULLS, TRACKS) for rows in part.values())
# Premium components are only offered by the workshop once a tank that uses them is owned (see workshop_components()).
PREMIUM_PARTS = frozenset({"crystal", "shard", "furnace", "inferno", "singularity", "tesla", "clock", "crystal_h", "forge_h", "event_h",
                           "storm_h", "chrono_h", "crystal_t", "ember_t", "void_t", "arc_t", "gold_t"})


def _tank(key: str, name: str, blurb: str, parts: str, barrel: str, glow: str, ambient: str, accent: RGB,
          paint: Optional[RGB] = None, hover: float = 0.0) -> TankDesign:
    """parts = 'turret/hull/track' component ids from the tables above."""
    t, h, k = parts.split("/")
    return TankDesign(key, name, blurb, TURRETS[t] + HULLS[h] + TRACKS[k], barrel=barrel, glow=glow, ambient=ambient,
                      accent=accent, parts=(t, h, k), paint=paint, hover=hover)


def _tanks(rows: list) -> tuple:
    return tuple(_tank(*r[:8], **(r[8] if len(r) > 8 else {})) for r in rows)


DESIGNS: tuple[TankDesign, ...] = (
    TankDesign("ranger", "RANGER", "Balanced dome-turret all-rounder.",
               ("...ttttt...", "..ttttttt..", ".hhhhhhhhg.", "hhhhhhhhhhh", "kwkwkwkwkwk", ".kkkkkkkkk.")),
    TankDesign("bulwark", "BULWARK", "Boxy plated hull with a heavy gun.",
               ("..ttttttt..", ".tttdtdttt.", "hhhhhhhhhhg", "hdhhhdhhhdh", "kwkwkwkwkwk", "kkkkkkkkkkk"),
               barrel="heavy", accent=(255, 210, 90)),
    TankDesign("viper", "VIPER", "Low wedge hull with blinking sensors.",
               ("....ttt....", "..ttltltt..", "..hhhhhhhgg", ".hhhhhhhhh.", "kwkwkwkwkw.", ".kkkkkkkkk."),
               barrel="rail", glow="blink", accent=(140, 255, 230)),
    TankDesign("gemini", "GEMINI", "Twin cupolas and a split barrel.",
               ("..tt.t.tt..", ".ttttttttt.", ".hhhhhhhhg.", "hhhhhhhhhhh", "kwkwkwkwkwk", ".kkkkkkkkk."),
               barrel="double"),
    TankDesign("crawler", "CRAWLER", "Round-bellied hull on small wheels.",
               ("....ttt....", "..ttttttt..", ".ttttttttt.", "hhhhhhhhhhg", ".kwkwkwkwk.", "..kkkkkkk..")),
    TankDesign("hornet", "HORNET", "Warning stripes and a spark-spitting hull.",
               ("...ttttt...", "..tttdttt..", ".hdhdhdhdhg", "hdhdhdhdhdh", "kwkwkwkwkwk", ".kkkkkkkkk."),
               ambient="sparks"),
    TankDesign("titan", "TITAN", "Armoured giant with a pulsing core.",
               (".ttttttttt.", "tttdtltdttt", "hhhhhhhhhhg", "hdddhhhdddh", "kkwkkwkkwkk", "kkkkkkkkkkk"),
               barrel="heavy", glow="pulse", accent=(120, 200, 255)),
    TankDesign("phantom", "PHANTOM", "Angular stealth hull trailing violet mist.",
               ("....ttt....", "...ttttt...", ".dhhhhhhhg.", "dhhllllhhhh", "kdkdkdkdkdk", ".kkkkkkkkk."),
               barrel="rail", glow="pulse", ambient="mist", accent=(200, 140, 255)),
    TankDesign("juggernaut", "JUGGERNAUT", "Siege hull with a roaring exhaust.",
               ("..ttttttt..", ".ttttatttt.", "hhhhhhhhhhg", "lhhhhhhhhhh", "kwkwkwkwkwk", "kkkkkkkkkkk"),
               barrel="heavy", glow="flame", ambient="embers", accent=(255, 160, 60)),
    # --- Tournament levels 5-9: each one a step up in presence ------------------------------------------------
    TankDesign("sentinel", "SENTINEL", "Shield-plated guardian with a scanning visor.",
               ("..ttttttt..", ".tddtltddt.", "hhhhhhhhhhg", "hllllllllhh", "kwkwkwkwkwk", "kkkkkkkkkkk"),
               barrel="heavy", glow="scan", accent=(120, 255, 190)),
    TankDesign("glacier", "GLACIER", "Spiked ice armour shedding frost.",
               ("....ttt....", "..tttattt..", ".hhhhhhhhg.", "ahalhhhlaha", "kwkwkwkwkwk", ".kkkkkkkkk."),
               barrel="rail", glow="pulse", ambient="frost", accent=(170, 225, 255)),
    TankDesign("helios", "HELIOS", "A crowned solar hull burning with plasma.",
               ("a.a.ttt.a.a", ".attlltta..", ".hhhhhhhhg.", "hhllllllhhh", "kwkwkwkwkwk", "kkkkkkkkkkk"),
               barrel="double", glow="plasma", ambient="flare", accent=(255, 214, 90)),
    # --- Tournament levels 8-17: ten more steps up in presence ---------------------------------------------------
    _tank("rattler", "RATTLER", "Dusty desert wedge that spits sparks.", "wide/stripe/full", "heavy", "none", "sparks", (240, 200, 90)),
    _tank("miasma", "MIASMA", "Toxic hull trailing green mist.", "dome/vent/round", "rail", "blink", "mist", (140, 255, 100)),
    _tank("bastion", "BASTION", "A walking fortress of slab armour.", "box/armor/spike", "heavy", "pulse", "none", (210, 190, 150)),
    _tank("zephyr", "ZEPHYR", "Needle-nosed sprinter that rides the wind.", "needle/wedge/std", "rail", "scan", "frost", (170, 230, 255)),
    _tank("geode", "GEODE", "Crystal-spiked shell with a glowing heart.", "spike/core/round", "double", "pulse", "flare", (200, 140, 255)),
    _tank("mirage", "MIRAGE", "A shimmering hull that never sits still.", "twin/jewel/std", "double", "plasma", "mist", (255, 170, 210)),
    _tank("revenant", "REVENANT", "Ghost-iron war machine with a lava heart.", "visor/vent/spike", "heavy", "lava", "embers", (255, 120, 60)),
    _tank("corsair", "CORSAIR", "Raider with a crackling storm cannon.", "coil/plate/full", "double", "storm", "static", (120, 200, 255)),
    _tank("tyrant", "TYRANT", "Crowned siege lord, furnace-lit.", "crown/slab/heavy", "heavy", "flame", "embers", (255, 150, 50)),
    _tank("archon", "ARCHON", "Gleaming champion with a triple plasma gun.", "crown/core/spike", "triple", "plasma", "flare", (255, 230, 160)),
    # --- Tournament levels 18-20: the Master's road --------------------------------------------------------------
    TankDesign("obsidian", "OBSIDIAN", "Black glass hull split by molten cracks.",
               ("a...ttt...a", ".a.ttdtt.a.", "hdhhhhhhhhg", "dlhdlhhldhd", "kdkwkdkwkdk", "kkkkkkkkkkk"),
               barrel="heavy", glow="lava", ambient="embers", accent=(255, 96, 36)),
    TankDesign("tempest", "TEMPEST", "Storm-crowned coil tank with a triple barrel.",
               ("a....t....a", "a.tttltttt.", "hhhhhhhhhhg", "hlhlhlhlhlh", "kdkwkwkwkdk", "kkkkkkkkkkk"),
               barrel="triple", glow="storm", ambient="static", accent=(150, 222, 255)),
    # --- Tournament level 20: the Master's tank (prism barrel, crown, sparkle) --------------------------------
    TankDesign("sovereign", "SOVEREIGN", "The Master's crowned war machine.",
               ("..a.ttt.a..", "..attltta..", ".hhhhhhhhg.", "hallhhhllah", "kwkwkwkwkwk", ".kkkkkkkkk."),
               barrel="prism", glow="prism", ambient="sparkle", accent=(255, 214, 110)),
)
# Secret kits: never part of the Tournament, hidden until a cheat code unlocks them.
SECRET_DESIGNS: tuple[TankDesign, ...] = (
    TankDesign("asciibot", "ASCIIBOT", "A retro monitor on treads, running on pure code.",
               (".ttttttttt.", ".tlltlttlt.", ".hhhhhhhhg.", "hdhdhdhdhdh", "kwkwkwkwkwk", ".kkkkkkkkk."),
               barrel="single", glow="matrix", ambient="bits", accent=(80, 255, 120)),
)
# Shop kits: bought with coins (and credits at the top tier). 5 cheap, 5 mid, 5 pro, 3 sovereign-level.
_SHOP_BASE_DESIGNS: tuple[TankDesign, ...] = (
    _tank("scout", "SCOUT", "Light wedge built for quick shots.", "needle/wedge/tread", "single", "none", "none", (200, 225, 240)),
    _tank("mule", "MULE", "Stubby, stubborn workhorse.", "box/plain/full", "single", "none", "none", (230, 200, 140)),
    _tank("badger", "BADGER", "Low-slung and hard to shift.", "dome/stripe/round", "single", "none", "none", (210, 170, 120)),
    _tank("turtle", "TURTLE", "Domed shell on tiny wheels.", "dome/plain/round", "single", "none", "none", (150, 220, 150)),
    _tank("pioneer", "PIONEER", "Open-frame frontier tank.", "twin/slab/std", "single", "none", "none", (220, 190, 160)),
    _tank("raider", "RAIDER", "Striped raider with a spark exhaust.", "wide/stripe/std", "double", "none", "sparks", (255, 180, 80)),
    _tank("centurion", "CENTURION", "Plated legionnaire, blinking visor.", "box/plate/spike", "heavy", "blink", "none", (230, 210, 120)),
    _tank("warhound", "WARHOUND", "Fast hunter with a rail gun.", "needle/vent/full", "rail", "blink", "none", (120, 255, 200)),
    _tank("mantis", "MANTIS", "Green praying-mantis hull.", "spike/wedge/round", "rail", "pulse", "mist", (150, 255, 120)),
    _tank("paladin", "PALADIN", "Gilded defender with a pulsing core.", "dome/armor/std", "heavy", "pulse", "none", (255, 230, 140)),
    _tank("reaper", "REAPER", "Dark scythe-armed hunter.", "spike/armor/spike", "rail", "lava", "embers", (255, 80, 60)),
    _tank("leviathan", "LEVIATHAN", "Deep-sea hull glowing from within.", "wide/core/heavy", "heavy", "pulse", "mist", (80, 200, 255)),
    _tank("banshee", "BANSHEE", "Shrieking storm-wing tank.", "coil/wedge/std", "triple", "storm", "static", (180, 220, 255)),
    _tank("behemoth", "BEHEMOTH", "Colossal slab with a blazing core.", "box/slab/heavy", "heavy", "flame", "embers", (255, 140, 40)),
    _tank("nightshade", "NIGHTSHADE", "Violet stealth hull, glowing visor.", "visor/jewel/round", "rail", "plasma", "mist", (200, 120, 255)),
    _tank("emperor", "EMPEROR", "Crowned war engine with a prism gun.", "crown/royal/heavy", "prism", "prism", "sparkle", (255, 214, 110)),
    _tank("celestial", "CELESTIAL", "Star-forged hull wreathed in solar fire.", "coil/jewel/spike", "triple", "plasma", "flare", (255, 220, 120)),
    _tank("eternal", "ETERNAL", "Void-crowned titan lit by lightning.", "crown/armor/heavy", "prism", "storm", "static", (190, 160, 255)),
    _tank("dynasty", "DYNASTY", "A gilded throne on treads, sparkling.", "coil/royal/heavy", "triple", "prism", "sparkle", (255, 200, 120)),
    _tank("overlord", "OVERLORD", "Jewelled horned tyrant, plasma-lit.", "spike/jewel/heavy", "prism", "plasma", "flare", (255, 150, 220)),
)
# Mission-mode rewards (6 tanks, 6 ammo, 6 maps and 6 home screens; the last of each is the alien Grand Prize set).
MISSION_DESIGNS: tuple[TankDesign, ...] = (
    _tank("wardog", "WARDOG", "Battle-scarred hound with a heavy cannon.", "box/plate/heavy", "heavy", "none", "sparks", (180, 200, 150)),
    _tank("spitfire", "SPITFIRE", "Quick-firing wedge with a scanning visor.", "visor/wedge/std", "double", "scan", "none", (150, 255, 190)),
    _tank("blitz", "BLITZ", "Storm-lit raider with a triple cannon.", "coil/vent/full", "triple", "blink", "static", (255, 220, 120)),
    _tank("judge", "JUDGE", "A crowned slab of unforgiving armour.", "crown/armor/spike", "rail", "pulse", "flare", (230, 200, 255)),
    _tank("hydra", "HYDRA", "Many-headed plasma tank trailing mist.", "twin/jewel/heavy", "triple", "plasma", "mist", (120, 255, 150)),
    TankDesign("ufo", "U.F.O.", "An alien saucer on hover pods. The Grand Prize.",
               ("....lll....", "...tllllt..", ".hhhhhhhhg.", "hahahahahah", ".kk.kkk.kk.", "..k.....k.."),
               barrel="single", glow="plasma", ambient="mist", accent=(120, 255, 170), hover=3.0),
)
_N = lambda *r: r
_NEW_TANKS = (
    _tanks([  # cheap
        _N("pebble", "PEBBLE", "A smooth little river-stone of a tank.", "dome/ribbed/tread", "single", "none", "none", (190, 200, 205)),
        _N("rusty", "RUSTY", "Patched bunker on low treads.", "pillbox/bunker/lowtread", "howitzer", "none", "none", (200, 140, 90)),
        _N("hopper", "HOPPER", "Spindly antenna tank on wheels.", "antenna/boat/wheels", "single", "none", "none", (170, 220, 170)),
        _N("spud", "SPUD", "Round, wide and unbothered.", "bubble/wide/full", "single", "none", "none", (220, 200, 140)),
        _N("crate", "CRATE", "A box on pods. It works.", "pillbox/slab/pods", "single", "none", "none", (190, 170, 130)),
        _N("skiff", "SKIFF", "Sail-turret skimmer on skids.", "sail/keel/skids", "needle", "none", "none", (150, 200, 235)),
        _N("grunt", "GRUNT", "Rear-set gun on a ramped hull.", "rear/ramp/std", "howitzer", "none", "none", (160, 190, 140)),
        _N("tinker", "TINKER", "Radar-topped hex hull on spiked treads.", "radar/hex/spiked", "single", "none", "none", (210, 190, 120)),
        _N("drifter", "DRIFTER", "Mushroom cap over a saddle hull.", "mushroom/saddle/round", "single", "none", "none", (200, 170, 210)),
        _N("bucket", "BUCKET", "Bulbous cradle with a double barrel.", "bubble/cradle/heavy", "double", "none", "none", (180, 190, 200))]),
    _tanks([  # mid
        _N("stingray", "STINGRAY", "Dish-crowned keel gliding on pods.", "dish/keel/pods", "sniper", "scan", "bubbles", (100, 200, 230)),
        _N("marauder", "MARAUDER", "Horned hex hull bristling with barrels.", "horns/hex/spiked", "quad", "blink", "sparks", (235, 150, 90)),
        _N("harpoon", "HARPOON", "Helmeted lowtread with a very long gun.", "helm/glowband/lowtread", "sniper", "scan", "none", (120, 230, 200)),
        _N("trident", "TRIDENT", "A three-pronged gun on a bunker.", "split/bunker/tread", "triple", "pulse", "none", (110, 210, 230)),
        _N("redoubt", "REDOUBT", "A tower on a ribbed fortress hull.", "tower/ribbed/heavy", "howitzer", "pulse", "none", (210, 200, 170)),
        _N("sandstorm", "SANDSTORM", "Gritty ridge-top hull shedding dust.", "ridge/ramp/spiked", "gatling", "none", "embers", (230, 190, 110)),
        _N("cobra", "COBRA", "A hooded orb striking from a keel.", "orb/keel/hoverpad", "coil", "toxic", "mist", (140, 240, 110)),
        _N("barracuda", "BARRACUDA", "Finned predator with a needle gun.", "fin/boat/skids", "needle", "ice", "frost", (150, 220, 255)),
        _N("outrider", "OUTRIDER", "Radar scout on long stilts.", "radar/domehull/stilts", "sniper", "neon", "none", (240, 110, 220)),
        _N("brigadier", "BRIGADIER", "Stair-stepped command tank in gold.", "stair/lattice/lowtread", "heavy", "gold", "none", (235, 215, 130))]),
    _tanks([  # pro
        _N("typhoon", "TYPHOON", "A storm-cell turret on a glowing band.", "antenna/glowband/hoverpad", "bolt", "storm", "static", (130, 190, 255)),
        _N("hellcat", "HELLCAT", "Horned, ember-plated predator.", "horns/armor/spiked", "flame", "ember", "embers", (255, 110, 60)),
        _N("warmaster", "WARMASTER", "A quad-barrel siege lord.", "helm/bunker/heavy", "quad", "pulse", "sparks", (220, 190, 120)),
        _N("gravedigger", "GRAVEDIGGER", "Black spined hull, void-lit.", "ridge/spined/stilts", "void", "void", "void", (150, 100, 230)),
        _N("shatterer", "SHATTERER", "Crystal-cold hull crowned with ice.", "fin/hex/pods", "needle", "ice", "frost", (190, 235, 255)),
        _N("stormrider", "STORMRIDER", "A wide-bodied cannon on skids, crackling.", "radar/wide/skids", "gatling", "storm", "lightning", (110, 200, 255)),
        _N("ironclad", "IRONCLAD", "A tower of armour with a gold heart.", "tower/armor/heavy", "howitzer", "gold", "none", (200, 200, 215)),
        _N("bloodhound", "BLOODHOUND", "A fast red hunter trailing embers.", "rear/ramp/hoverpad", "sniper", "ember", "embers", (230, 70, 70)),
        _N("sandshark", "SANDSHARK", "A finned burrower with a toxic glow.", "fin/keel/spiked", "coil", "toxic", "petals", (220, 190, 100)),
        _N("tempestor", "TEMPESTOR", "An orb-topped war engine in neon.", "orb/lattice/heavy", "bolt", "neon", "orbit", (255, 90, 220))]),
    _tanks([  # master tier
        _N("ascendant", "ASCENDANT", "A rising gold spire over a glowing band.", "helm/glowband/hoverpad", "crystal", "gold", "orbit", (255, 225, 130)),
        _N("seraphim", "SERAPHIM", "A winged, haloed hull, bright and ethereal.", "fin/domehull/pods", "bolt", "refract", "sparkle", (255, 250, 200)),
        _N("doombringer", "DOOMBRINGER", "A spiked dread on burning treads.", "horns/armor/lowtread", "flame", "ember", "burn", (255, 80, 50)),
        _N("starforge", "STARFORGE", "A star-crowned forge of living gold.", "orb/royal/heavy", "coil", "gold", "sparkle+flare", (255, 200, 100)),
        _N("arcanist", "ARCANIST", "A mystic hull orbited by motes.", "coil/jewel/hoverpad", "void", "neon", "orbit", (200, 120, 255)),
        _N("voidwalker", "VOIDWALKER", "A black glass stalker leaking dark.", "ridge/lattice/stilts", "void", "void", "void+smoke", (160, 110, 240)),
        _N("sunbreaker", "SUNBREAKER", "A radiant dome of solar plasma.", "crown/glowband/heavy", "flame", "plasma", "fire+flare", (255, 190, 70)),
        _N("templar", "TEMPLAR", "A gilded tower-fortress with a halo.", "tower/royal/heavy", "heavy", "gold", "sparkle+orbit", (255, 235, 150)),
        _N("monolith", "MONOLITH", "A slab of glowing stone and static.", "pillbox/slab/heavy", "howitzer", "storm", "static+orbit", (180, 200, 230)),
        _N("phoenix", "PHOENIX", "A bird of fire on a gilded frame.", "fin/jewel/hoverpad", "flame", "ember", "fire+embers", (255, 160, 50))]),
)
# --- Premium vocabulary II (uppercase material letters, see MATERIALS in tanks/art/materials.py):
#   J abyss hide  U biolume   F foxfire   X spirit fur   H hologram   K hardlight steel   Q hyper-wire   Z hyper-void
#   R kaiju scale N atomic    M fungus cap S spore glow  W worm ring  O worm maw        E jade         P quetzal plume
#   C star chart  G gold line B ghost wood L ghostfire
TURRETS.update({
    "anglerlure": ("...U.......", "..JJJJJJ..."), "foxears": (".X......X..", "XXXXFXXXXX."), "kabuto": ("..K.HHH.K..", ".HHHHHHHHH."),
    "cube": ("...QQQQQ...", "...QZZZQ..."), "dorsal": ("N..N..N..N.", "RRNRRNRRNRR"), "cap": (".MMMMMMMMM.", "MMMMMMMMMMM"),
    "maw": ("O.O.O.O.O..", "WWOOOOOOWW."), "plume": ("P.P.PPP.P.P", ".PEEEEEEEP."), "astrolabe": ("..G.CCC.G..", ".GCCCCCCCG."),
    "masts": ("..B..B..B..", "BBBBBBBBBB."),
})
HULLS.update({
    "abyss_h": ("JJUJJJJUJJg", "JJJJlllJJJJ"), "kitsune_h": ("XXFXXXXFXXg", "XXXXlllXXXX"), "holo_h": ("HHHHKHHHHHg", "HKHHlllHHKH"),
    "tess_h": ("QZZZZlZZZZQ", "QQZZQQQZZQQ"), "kaiju_h": ("RRRRRRRRRlg", "RRlRRRRRlRR"), "stem_h": ("..hhShhhhg.", ".hhhhlhhhh."),
    "wyrm_h": ("WWWWWWWWWWg", "WkWWkWWkWWW"), "jade_h": ("EEyEEEEyEEg", "EEEElllEEEE"), "zodiac_h": ("CCGCClCCGCg", "CGCCCGCCCGC"),
    "galleon_h": ("BBBBBBBBBBg", "BLBLBLBLBLB"),
})
TRACKS.update({
    "abyss_t": ("kUkJkJkUkJk", ".kkkkkkkkk."), "spirit_t": ("F.F.F.F.F.F", ".F.F.F.F.F."), "holo_t": ("kHkHkHkHkHk", "kkkkkkkkkkk"),
    "phase_t": ("..Q.....Q..", ".QQQ...QQQ."), "claw_t": ("RkRkRkRkRkR", "kRkkkkkkkRk"), "root_t": (".k.k.k.k.k.", "kkSkkkkkSkk"),
    "burrow_t": ("WWWWWWWWWWW", ".W.W.W.W.W."), "serpent_t": ("EkEkEkEkEkE", ".kkkkkkkkk."), "orbit_t": ("..C.....C..", ".CCC...CCC."),
    "keel_t": (".BBBBBBBBB.", "..LLLLLLL.."),
})
assert all(len(r) == 11 for part in (TURRETS, HULLS, TRACKS) for rows in part.values() for r in rows) \
    and all(len(rows) == 2 for part in (TURRETS, HULLS, TRACKS) for rows in part.values())
PREMIUM_PARTS = PREMIUM_PARTS | {"anglerlure", "foxears", "kabuto", "cube", "dorsal", "cap", "maw", "plume", "astrolabe", "masts",
                                 "abyss_h", "kitsune_h", "holo_h", "tess_h", "kaiju_h", "stem_h", "wyrm_h", "jade_h", "zodiac_h", "galleon_h",
                                 "abyss_t", "spirit_t", "holo_t", "phase_t", "claw_t", "root_t", "burrow_t", "serpent_t", "orbit_t", "keel_t"}
# The premium tier: intrinsic designs built from the premium component set (crystal, furnace, void, storm, clockwork).
_PREMIUM_TANKS = _tanks([
    _N("prismatic_king", "PRISMATIC KING", "Grown from a single crystal: every facet splits the light.", "crystal/crystal_h/crystal_t", "crystal",
       "refract", "prism+sparkle", (255, 255, 255), {"paint": (206, 220, 246)}),
    _N("eviscerator", "EVISCERATOR", "Furnace-hearted and permanently ablaze, smoke pouring off white-hot armour.", "inferno/forge_h/ember_t",
       "flame", "ember", "burn", (255, 150, 40), {"paint": (205, 26, 26)}),
    _N("singularity", "SINGULARITY", "A collapsed star in tank form; light bends around the hull.", "singularity/event_h/void_t", "void", "void",
       "void+orbit", (170, 110, 255), {"paint": (34, 22, 70), "hover": 3.0}),
    _N("stormbringer", "STORMBRINGER", "Tesla spires and arc-wreathed tracks.", "tesla/storm_h/arc_t", "bolt", "storm", "lightning+static",
       (160, 220, 255), {"paint": (52, 72, 128)}),
    _N("chronos", "CHRONOS", "A clockwork of gold that never stops turning.", "clock/chrono_h/gold_t", "coil", "gold", "orbit+sparkle",
       (255, 230, 140), {"paint": (150, 112, 40)}),
    # --- premium II: ten new legends, each with its own materials, gun, glow and aura ---------------------------------
    _N("luminary", "LUMINARY", "An abyssal angler. A living lure glows over a hide of cold deep water.", "anglerlure/abyss_h/abyss_t",
       "lure", "biolume", "lure+bubbles", (120, 255, 235), {"paint": (14, 34, 66)}),
    _N("kitsune", "KITSUNE", "A nine-tailed fox spirit floating on blue foxfire.", "foxears/kitsune_h/spirit_t", "spirit", "foxfire",
       "tails+foxfire", (150, 205, 255), {"paint": (236, 232, 246), "hover": 2.5}),
    _N("holoronin", "HOLO RONIN", "A masterless samurai woven from hard light. It glitches when it moves.", "kabuto/holo_h/holo_t", "katana",
       "hologlitch", "scanlines+bits", (90, 240, 255), {"paint": (20, 30, 64)}),
    _N("tesseract", "TESSERACT", "A four-dimensional cube folded into a tank. Do not stare at it.", "cube/tess_h/phase_t", "tesseract", "phase",
       "hypercube", (190, 150, 255), {"paint": (10, 8, 30), "hover": 4.0}),
    _N("kaiju", "KAIJU", "An atomic monster in armour. Its dorsal plates glow before it roars.", "dorsal/kaiju_h/claw_t", "atomic", "atomic",
       "radiation", (130, 205, 255), {"paint": (40, 58, 50)}),
    _N("sporeking", "SPOREKING", "A walking mushroom grove that breathes glowing spores.", "cap/stem_h/root_t", "fungal", "spore", "spores",
       (130, 255, 200), {"paint": (214, 204, 184)}),
    _N("sandwyrm", "SANDWYRM", "A great worm of the deep desert, ringed and ravenous.", "maw/wyrm_h/burrow_t", "wyrm", "maw", "sand+embers",
       (255, 170, 80), {"paint": (176, 128, 72)}),
    _N("quetzal", "QUETZAL", "A feathered serpent of jade and gold, crowned in plumes.", "plume/jade_h/serpent_t", "serpent", "jade",
       "feathers+glyphs", (120, 255, 170), {"paint": (28, 108, 80)}),
    _N("zodiac", "ZODIAC", "An astrolabe of brass and starlight that reads your fortune.", "astrolabe/zodiac_h/orbit_t", "astrolabe", "zodiac",
       "constellation+sparkle", (255, 226, 150), {"paint": (16, 22, 64), "hover": 3.0}),
    _N("wraithship", "WRAITHSHIP", "A ghost galleon sailing on its own fog, cannons lit with green fire.", "masts/galleon_h/keel_t",
       "broadside", "ghost", "sails+ghostfire+mist", (120, 255, 170), {"paint": (38, 58, 62), "hover": 3.0}),
])
SHOP_DESIGNS: tuple[TankDesign, ...] = (_SHOP_BASE_DESIGNS[0:5] + _NEW_TANKS[0] + _SHOP_BASE_DESIGNS[5:10] + _NEW_TANKS[1]
                                        + _SHOP_BASE_DESIGNS[10:15] + _NEW_TANKS[2] + _SHOP_BASE_DESIGNS[15:20] + _NEW_TANKS[3] + _PREMIUM_TANKS)
# Terminal Ticket bosses: ten unique premium-class tanks (intrinsic paint), reward-only.
TICKET_DESIGNS: tuple[TankDesign, ...] = _tanks([
    _N("voltsovereign", "VOLT SOVEREIGN", "A throne of arcing coils.", "tesla/glowband/hoverpad", "bolt", "storm", "lightning+static", (150, 210, 255), {"paint": (40, 60, 150)}),
    _N("magistrate", "IRON MAGISTRATE", "A clockwork judge in grey iron and gold.", "clock/ribbed/lowtread", "coil", "gold", "orbit+sparkle", (255, 220, 120), {"paint": (110, 104, 96)}),
    _N("regent", "GLACIER REGENT", "A frozen spire-tank breathing frost.", "shard/hex/pods", "needle", "ice", "frost+orbit", (200, 240, 255), {"paint": (170, 215, 245)}),
    _N("solarch", "SOLAR ARCHON", "A blazing gold tower-tank.", "tower/royal/spiked", "flame", "gold", "fire+flare+sparkle", (255, 220, 100), {"paint": (230, 170, 50)}),
    _N("abyssal", "ABYSS LEVIATHAN", "A deep-sea horror leaking bubbles and dark.", "wide/hex/hoverpad", "howitzer", "void", "bubbles+void", (100, 200, 255), {"paint": (20, 70, 110), "hover": 2.0}),
    _N("pharaoh", "SAND PHARAOH", "A gilded sun-priest on silent skids.", "dish/spined/skids", "sniper", "gold", "sparkle+embers", (255, 230, 150), {"paint": (205, 170, 70)}),
    _N("baron", "TOXIC BARON", "A noxious war-machine venting green smoke.", "stair/ribbed/lowtread", "quad", "toxic", "smoke+mist", (170, 255, 90), {"paint": (80, 130, 40)}),
    _N("shadowlord", "SHADOW EMPEROR", "A horned silhouette swallowing the light.", "horns/lattice/stilts", "void", "void", "void+smoke", (170, 120, 255), {"paint": (30, 24, 46)}),
    _N("overseer", "COSMIC OVERSEER", "A watching orb on a hovering throne.", "orb/jewel/hoverpad", "crystal", "refract", "orbit+prism", (200, 190, 255), {"paint": (60, 60, 140), "hover": 3.0}),
    _N("warlord", "DRAGON WARLORD", "A scaled, fire-breathing conqueror.", "furnace/slab/spiked", "flame", "ember", "fire+smoke", (255, 160, 60), {"paint": (170, 40, 30)}),
])
# --- Ancient Artifact vocabulary: o solar flame, r rune gold, s starlight, n nightglass, m aether, z chrono ------------------
TURRETS.update({
    "sunhalo": ("..o.ooo.o..", ".ooosssooo."), "eclipsecrown": ("n.n.nnn.n.n", ".nnnsssnnn."), "tempestfan": ("m.m..m..m.m", ".mmmmmmmmm."),
    "emberspire": ("..f.fff.f..", ".efffffffe."), "hourglass": ("..zzzzzzz..", "...zszsz..."),
})
HULLS.update({
    "sunplate": ("hoosshsso.g", "hsohhhhhosh"), "nightwing": ("nnhhnnnhhng", "nsnnhhhnnsn"), "stormdeck": ("hmhmhmhmhmg", "hmmmhhhmmmh"),
    "magmaslab": ("hefehfehefg", "heeefhfeeeh"), "chronocase": ("hzzhhzhhzzg", "zshzzhzzhsz"),
})
TRACKS.update({
    "sunrunner": ("ororororor.", ".oooooooo.."), "voidskids": ("n.nn...nn.n", ".nsnn.nnsn."), "galetreads": (".mm.mm.mm..", "mmmmmmmmmmm"),
    "cinder_t": ("kekfkekfkek", ".kkkkkkkkk."), "sand_t": ("..zz...zz..", ".zzszzzszz."),
})
assert all(len(r) == 11 for part in (TURRETS, HULLS, TRACKS) for rows in part.values() for r in rows) \
    and all(len(rows) == 2 for part in (TURRETS, HULLS, TRACKS) for rows in part.values())
TURRETS["martyrhood"] = ("...nnnnn...", "..nnrsrnn..")
HULLS["martyrrobe"] = ("nnrnnnnnrng", "nrnnsnnsnrn")
TRACKS["martyrstaff"] = ("r.rr.rr.rr.", ".rssrrrrss.")
assert all(len(r) == 11 for p in ("martyrhood", "martyrrobe", "martyrstaff") for part in (TURRETS, HULLS, TRACKS) if p in part for r in part[p])
PREMIUM_PARTS = PREMIUM_PARTS | {"martyrhood", "martyrrobe", "martyrstaff", "sunhalo", "eclipsecrown", "tempestfan", "emberspire", "hourglass", "sunplate", "nightwing", "stormdeck",
                                 "magmaslab", "chronocase", "sunrunner", "voidskids", "galetreads", "cinder_t", "sand_t"}
ANCIENT_DESIGNS: tuple[TankDesign, ...] = (
    _tank("a_solaris", "ANCIENT SOLARIS", "Sunforged war-relic crowned in living light.", "sunhalo/sunplate/sunrunner", "sunlance", "plasma",
          "halo+flare+sparkle", (255, 226, 130), paint=(226, 176, 60), hover=3.0),
    _tank("a_umbral", "ANCIENT UMBRAL", "A shard of the first night, wearing a crown of stars.", "eclipsecrown/nightwing/voidskids", "umbra", "aeon",
          "riftmotes+void", (196, 146, 255), paint=(16, 10, 34), hover=3.0),
    _tank("a_tempest", "ANCIENT TEMPEST", "Storm and tide bound into one hovering fortress.", "tempestfan/stormdeck/galetreads", "gale", "storm",
          "glyphs+static+bubbles", (120, 232, 255), paint=(30, 92, 134), hover=3.0),
    _tank("a_emberheart", "ANCIENT EMBERHEART", "Mountain and fire: a furnace that never went out.", "emberspire/magmaslab/cinder_t", "magmacannon", "lava",
          "fire+embers+glyphs", (255, 146, 56), paint=(92, 32, 22), hover=2.0),
    _tank("a_chronos", "ANCIENT CHRONOS", "The hourglass itself. Time bends around its hull.", "hourglass/chronocase/sand_t", "ancient", "aeon",
          "halo+orbit+glyphs", (255, 236, 176), paint=(150, 108, 48), hover=4.0),
    _tank("a_martyr", "THE MARTYR", "The legend's own war-tank: robes of night and a crown of stars.", "martyrhood/martyrrobe/martyrstaff", "ancient", "aeon",
          "halo+riftmotes+glyphs", (255, 226, 150), paint=(20, 12, 44), hover=4.0),
)
ALL_DESIGNS = DESIGNS + SHOP_DESIGNS + MISSION_DESIGNS + TICKET_DESIGNS + SECRET_DESIGNS + ANCIENT_DESIGNS
assert all(len(d.mask) == TANK_H and all(len(r) == TANK_W for r in d.mask) for d in ALL_DESIGNS)
assert len(DESIGNS) == 25 and DESIGNS[-1].key == "sovereign"          # 5 starters + 20 Tournament unlocks
assert len({d.key for d in ALL_DESIGNS}) == len(ALL_DESIGNS)
DESIGN_BY_KEY = {d.key: d for d in ALL_DESIGNS}
DEFAULT_DESIGN = DESIGNS[0]
BASE_KITS = 5     # the first five designs / ammo types are available from the start
