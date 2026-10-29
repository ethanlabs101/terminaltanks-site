"""Ammunition. An AmmoType is a look (projectile, trail, blast) and optional mechanics (bounce, split, cluster, drill,
...; see battle/shots.py). AMMOS = standard + the Tournament ammo; SHOP_AMMOS are sold in tiers; mission, ticket
and ancient ammo are earned. Keys are saved: never rename one."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AmmoType:
    key: str
    name: str
    blurb: str
    proj: str       # projectile look
    trail: str      # tracer look
    boom: str       # explosion look
    mech: tuple = ()  # gameplay mechanics as (key, value) pairs - see plan_shot(); empty = a plain shell

    @property
    def mechanics(self) -> dict:
        return dict(self.mech)


AMMOS: tuple[AmmoType, ...] = (          # first five: starters; then one per Tournament level, in level order
    AmmoType("standard", "STANDARD", "Reliable high-explosive shell.", "shell", "plain", "classic"),
    AmmoType("tracer", "TRACER", "Dashed tracer streak, ray flash.", "streak", "dash", "rays"),
    AmmoType("plasma", "PLASMA", "Pulsing energy orb, ringed blast.", "orb", "glow", "ring"),
    AmmoType("flak", "FLAK", "Crackling sparks, clustered bursts.", "spark", "sparks", "cluster"),
    AmmoType("comet", "COMET", "Blazing head, long ember tail.", "comet", "embers", "embers"),
    AmmoType("venom", "VENOM", "Dripping toxin, lingering gas cloud.", "drip", "drip", "cloud"),
    AmmoType("starburst", "STARBURST", "Twinkling star, radiant ray burst.", "star", "twinkle", "starrays"),
    AmmoType("void", "VOID", "Dark core that implodes, then blasts.", "void", "mist", "implode"),
    AmmoType("inferno", "INFERNO", "Living flame, rising fire plume.", "flame", "fire", "fire"),
    AmmoType("pulse", "PULSE", "Rippling ring-wave, triple shockwave.", "ring", "ripple", "shock"),
    AmmoType("cryo", "CRYO", "Ice shard trailing frost, shattering blast.", "shard", "frost", "shatter"),
    AmmoType("nova", "NOVA", "A blinding solar orb and a white-hot flare.", "sun", "solar", "nova"),
    AmmoType("shrapnel", "SHRAPNEL", "Splintering shards, clustered blast.", "streak", "sparks", "cluster"),
    AmmoType("blight", "BLIGHT", "Creeping rot and a choking cloud.", "drip", "mist", "cloud"),
    AmmoType("siege", "SIEGE", "Heavy slug, ember wake, shockwave.", "shell", "embers", "shock"),
    AmmoType("cyclone", "CYCLONE", "Spinning ring on a rippling wake.", "ring", "ripple", "rays"),
    AmmoType("crystal", "CRYSTAL", "Faceted shard, twinkling dust.", "shard", "twinkle", "starrays"),
    AmmoType("echo", "ECHO", "Ringing orb, dashed afterimage.", "orb", "dash", "ring"),
    AmmoType("wraith", "WRAITH", "Ghost core, frost wake, shattering burst.", "void", "frost", "shatter"),
    AmmoType("barrage", "BARRAGE", "Blazing comet, sparking wake, solar burst.", "comet", "sparks", "nova"),
    AmmoType("wrath", "WRATH", "Roaring flame, lava trail, molten crater.", "flame", "lava", "magma"),
    AmmoType("zenith", "ZENITH", "Radiant star, solar wake, blinding nova.", "star", "solar", "nova"),
    AmmoType("magma", "MAGMA", "Molten blob, dripping lava, erupting crater.", "lava", "lava", "magma"),
    AmmoType("thunder", "THUNDER", "Crackling storm orb, forking lightning blast.", "bolt", "arc", "thunder"),
    AmmoType("aurora", "AURORA", "Prismatic shell, shimmering blast.", "prism", "prism", "prism"),
)
SECRET_AMMOS: tuple[AmmoType, ...] = (
    AmmoType("glyph", "GLYPH", "Cycling ASCII character, raining code.", "glyph", "code", "code"),
    AmmoType("blessing", "MARTYR'S BLESSING", "The Martyr's last power. Land a direct hit and time fractures, stars multiply and the battlefield is judged.",
             "blessing", "blessing", "blessing"),        # no `mech`: its power is the ONE-SHOT KILL handled in BattleScene (see BlessingFX)
)
BLESSING_KEY = "blessing"
_SHOP_BASE_AMMOS: tuple[AmmoType, ...] = (
    AmmoType("blazer", "BLAZER", "A plain comet with a clean blast.", "comet", "plain", "classic"),
    AmmoType("dasher", "DASHER", "Dashed streak, clustered bursts.", "streak", "dash", "cluster"),
    AmmoType("fizz", "FIZZ", "Fizzing spark, twinkling wake.", "spark", "twinkle", "rays"),
    AmmoType("slag", "SLAG", "Dripping slag, ember burst.", "drip", "embers", "embers"),
    AmmoType("needle", "NEEDLE", "A thin streak that bursts into stars.", "streak", "plain", "starrays"),
    AmmoType("ripple", "RIPPLE", "Glowing ring and a ringed blast.", "ring", "glow", "ring"),
    AmmoType("cinder", "CINDER", "Living flame that sheds embers.", "flame", "embers", "embers"),
    AmmoType("frostbite", "FROSTBITE", "Ice shard, frost wake, chilling cloud.", "shard", "frost", "cloud"),
    AmmoType("photon", "PHOTON", "Pulsing orb on a solar wake.", "orb", "solar", "rays"),
    AmmoType("toxin", "TOXIN", "Dripping poison, imploding gas.", "drip", "mist", "implode"),
    AmmoType("stormfront", "STORMFRONT", "Crackling bolt, rippling wake, forked blast.", "bolt", "ripple", "thunder"),
    AmmoType("quasar", "QUASAR", "A tiny sun trailing stardust.", "sun", "twinkle", "starrays"),
    AmmoType("abyss", "ABYSS", "A black hole that detonates in light.", "void", "mist", "nova"),
    AmmoType("molten", "MOLTEN", "Lava blob, fire wake, fire plume.", "lava", "fire", "fire"),
    AmmoType("glacial", "GLACIAL", "Prismatic shard, shattering burst.", "shard", "prism", "shatter"),
    AmmoType("helix", "HELIX", "Twin prismatic orbs spiralling in flight.", "helix", "prism", "prism"),
    AmmoType("eclipse", "ECLIPSE", "A dark core with a blazing corona.", "void", "solar", "nova"),
    AmmoType("bloom", "BLOOM", "A prismatic star that opens like a flower.", "star", "prism", "bloom"),
    AmmoType("nebula", "NEBULA", "Spiralling orbs shedding stardust.", "helix", "twinkle", "starrays"),
    AmmoType("supernova", "SUPERNOVA", "A miniature sun that blooms on impact.", "sun", "prism", "bloom"),
)
MISSION_AMMOS: tuple[AmmoType, ...] = (
    AmmoType("bandit", "BANDIT", "Dashed rounds with clustered bursts.", "comet", "dash", "cluster"),
    AmmoType("salvo", "SALVO", "Heavy shell, sparking wake, shockwave.", "shell", "sparks", "shock"),
    AmmoType("hailstorm", "HAILSTORM", "Crackling spark, rippling wake, forked blast.", "spark", "ripple", "thunder"),
    AmmoType("meltdown", "MELTDOWN", "Molten core, solar wake, erupting crater.", "lava", "solar", "magma"),
    AmmoType("oblivion", "OBLIVION", "A prismatic void that implodes.", "void", "prism", "implode"),
    AmmoType("xenon", "XENON", "A caged star of alien plasma: orbiting ions, a comet of sparks, a crystalline bloom of rings. The Grand Prize.", "xenon", "xenon", "xenon"),
)
def _ammos(rows: list) -> tuple:
    return tuple(AmmoType(k, n, b, p, t, bm, tuple(m)) for k, n, b, p, t, bm, m in rows)


_A = lambda *r: r
_NEW_AMMOS = (
    _ammos([  # cheap: one clear quirk each
        _A("lob", "LOB", "Slow, floaty lob: wide blast, loves a tailwind.", "orb", "glow", "ring", (("g", 0.7), ("wind", 1.4), ("radius", 1.1))),
        _A("slug", "SLUG", "Flat, fast, wind-proof slug with a small blast.", "streak", "dash", "classic", (("g", 1.45), ("wind", 0.4), ("speed", 1.1), ("radius", 0.85))),
        _A("skipper", "SKIPPER", "Skips once off the ground before it blows.", "shell", "plain", "classic", (("bounce", 1), ("br", 0.5), ("radius", 0.9))),
        _A("twister", "TWISTER", "Corkscrews through the air.", "spark", "twinkle", "rays", (("wob", (3.0, 8.0)), ("radius", 0.95))),
        _A("pebbles", "PEBBLES", "A small blast, then three bomblets.", "shell", "sparks", "cluster", (("cluster", 3), ("cspace", 4.5), ("cr", 0.5), ("radius", 0.6))),
        _A("dud", "DUD", "A tiny pop... then the real blast.", "comet", "plain", "embers", (("fuse", 0.8), ("fr", 1.35), ("radius", 0.5))),
        _A("mudball", "MUDBALL", "Builds a mound of earth instead of digging.", "drip", "drip", "cloud", (("terrain", "mound"), ("dmg", 0), ("radius", 1.1))),
        _A("borer", "BORER", "Drills a narrow, deep shaft.", "streak", "sparks", "shatter", (("terrain", "trench"), ("radius", 0.9))),
        _A("scatter", "SCATTER", "Splits in two at the top of its arc.", "star", "twinkle", "starrays", (("apex", ("split", 2, 0.5)), ("subr", 0.85))),
        _A("breeze", "BREEZE", "Ignores the wind completely.", "ring", "ripple", "ring", (("wind", 0.0), ("radius", 0.95)))]),
    _ammos([  # mid
        _A("zigzag", "ZIGZAG", "A wild zigzag that is hard to read.", "spark", "arc", "thunder", (("wob", (6.0, 12.0)), ("radius", 1.0))),
        _A("triskip", "TRI-SKIP", "Three skips, three chances.", "shell", "dash", "shock", (("bounce", 3), ("br", 0.4), ("radius", 0.9))),
        _A("rainmaker", "RAINMAKER", "Rains four shells from the apex.", "drip", "mist", "cloud", (("apex", ("split", 4, 0.7)), ("subr", 0.6))),
        _A("fireworks", "FIREWORKS", "Bursts into six at the top of the arc.", "star", "twinkle", "starrays", (("apex", ("split", 6, 1.0)), ("subr", 0.5))),
        _A("walker", "WALKER", "A line of blasts marching forward.", "lava", "lava", "magma", (("chain", 4), ("cstep", 7.0), ("cr", 0.6), ("radius", 0.7))),
        _A("timecharge", "TIME CHARGE", "Small pop, then a delayed big blast.", "comet", "solar", "nova", (("fuse", 1.2), ("fr", 1.8), ("radius", 0.45))),
        _A("rockslide", "ROCKSLIDE", "Bomblets spread across the ground.", "shell", "embers", "cluster", (("cluster", 5), ("cspace", 6.0), ("cr", 0.6), ("radius", 0.7))),
        _A("fortify", "FORTIFY", "Raises a defensive hill, harms nobody.", "orb", "glow", "ring", (("terrain", "mound"), ("dmg", 0), ("radius", 1.3))),
        _A("tunneler", "TUNNELER", "Digs a deep trench.", "streak", "frost", "shatter", (("terrain", "trench"), ("radius", 1.2))),
        _A("glasser", "GLASSER", "Melts the ground perfectly flat.", "sun", "solar", "nova", (("terrain", "glass"), ("radius", 1.0)))]),
    _ammos([  # pro
        _A("warpshell", "WARP SHELL", "Teleports forward at the top of its arc.", "void", "mist", "implode", (("apex", ("jump", 28.0)),)),
        _A("gravmine", "GRAV MINE", "Pulls nearby tanks toward the blast.", "void", "mist", "implode", (("pull", 7.0), ("radius", 1.1))),
        _A("hailfall", "HAILFALL", "Eight shards fall from above.", "shard", "frost", "shatter", (("apex", ("split", 8, 1.2)), ("subr", 0.5))),
        _A("ricochet", "RICOCHET", "Four ricochets before the finale.", "bolt", "arc", "thunder", (("bounce", 4), ("br", 0.5), ("radius", 1.0))),
        _A("tremor", "TREMOR", "A ground-shaking line of blasts.", "lava", "embers", "magma", (("chain", 6), ("cstep", 6.5), ("cr", 0.65), ("radius", 0.8))),
        _A("detonator", "DETONATOR", "Bomblets, then a delayed blast.", "comet", "sparks", "cluster", (("cluster", 7), ("cspace", 4.0), ("cr", 0.5), ("fuse", 0.9), ("fr", 1.5), ("radius", 0.7))),
        _A("colossus", "COLOSSUS", "A huge, heavy, slow shell.", "shell", "embers", "fire", (("radius", 1.9), ("g", 1.25), ("speed", 0.9))),
        _A("phantomorb", "PHANTOM ORB", "A wind-proof orb that wanders.", "orb", "mist", "implode", (("wob", (7.0, 7.0)), ("wind", 0.0), ("radius", 1.2))),
        _A("meteor", "METEOR", "Plunges steeply and hits hard.", "sun", "fire", "fire", (("g", 1.8), ("speed", 1.15), ("radius", 1.5))),
        _A("sunder", "SUNDER", "A wide blast that hurts every tank in reach.", "prism", "prism", "prism", (("multi", 1), ("radius", 1.7)))]),
    _ammos([  # master
        _A("vortex", "VORTEX", "Drags tanks in, then detonates.", "void", "mist", "implode", (("pull", 10.0), ("radius", 1.6), ("fuse", 0.7), ("fr", 2.2))),
        _A("skyfall", "SKYFALL", "Ten shells rain from the apex.", "star", "twinkle", "starrays", (("apex", ("split", 10, 1.3)), ("subr", 0.55))),
        _A("wormhole", "WORMHOLE", "Warps far ahead and lands as a cluster.", "ring", "ripple", "cluster", (("apex", ("jump", 45.0)), ("cluster", 3), ("cr", 0.6))),
        _A("chainreact", "CHAIN REACTION", "A long chain of blasts.", "bolt", "arc", "thunder", (("chain", 8), ("cstep", 6.0), ("cr", 0.7))),
        _A("faultline", "FAULT LINE", "Splits the ground open and runs on.", "lava", "lava", "magma", (("terrain", "trench"), ("radius", 1.6), ("chain", 5), ("cstep", 8.0), ("cr", 0.6))),
        _A("mirrorshot", "MIRROR", "Bounces five times.", "prism", "prism", "prism", (("bounce", 5), ("br", 0.6), ("radius", 1.2))),
        _A("overkill", "OVERKILL", "An enormous multi-target blast.", "sun", "solar", "nova", (("radius", 2.1), ("multi", 1), ("g", 1.1))),
        _A("cataclysm", "CATACLYSM", "Bomblets, then a world-ending blast.", "flame", "fire", "fire", (("fuse", 1.5), ("fr", 2.6), ("cluster", 4), ("radius", 0.8))),
        _A("prismrain", "PRISM RAIN", "Seven prismatic shells from above.", "prism", "prism", "prism", (("apex", ("split", 7, 0.9)), ("subr", 0.75))),
        _A("maelstrom", "MAELSTROM", "A swirling storm that drags tanks about.", "helix", "prism", "bloom", (("wob", (9.0, 6.0)), ("pull", 6.0), ("radius", 1.4)))]),
)
# Premium: each of these is a different algorithm, not a bigger number.
_PREMIUM_AMMOS = _ammos([
    _A("eventhorizon", "EVENT HORIZON", "Drags everything in, then collapses.", "void", "mist", "implode", (("pull", 14.0), ("radius", 2.0), ("fuse", 1.0), ("fr", 2.6), ("multi", 1))),
    _A("phaseshift", "PHASE SHIFT", "Blinks across the field and carpet-bombs.", "phase", "alien", "alien", (("apex", ("jump", 60.0)), ("cluster", 5), ("cspace", 5.0), ("cr", 0.6))),
    _A("armageddon", "ARMAGEDDON", "Twelve shells from the sky.", "sun", "fire", "nova", (("apex", ("split", 12, 1.6)), ("subr", 0.7))),
    _A("tectonic", "TECTONIC FURY", "A fissure that races across the land.", "lava", "lava", "magma", (("terrain", "trench"), ("radius", 1.8), ("chain", 10), ("cstep", 9.0), ("cr", 0.75))),
    _A("quantumecho", "QUANTUM ECHO", "Six impossible bounces, then a cluster.", "helix", "prism", "bloom", (("bounce", 6), ("br", 0.6), ("radius", 1.0), ("cluster", 4))),
    # --- premium II ----------------------------------------------------------------------------------------------------
    _A("anglerlure", "ANGLER'S LURE", "A glowing lure that bends toward the nearest enemy at the top of its arc.", "lure", "biolume", "biolume",
       (("seek", 0.5), ("radius", 1.1))),
    _A("foxfire", "FOXFIRE", "Bursts into nine spirit wisps that curl down toward your foe.", "foxfire", "foxfire", "foxfire",
       (("apex", ("split", 9, 1.1)), ("seek", 0.16), ("subr", 0.4))),
    _A("hardlight", "HARDLIGHT LANCE", "A near-straight beam that ignores wind and pierces deep into the ground.", "lance", "hardlight", "hardlight",
       (("g", 0.22), ("wind", 0.0), ("speed", 1.2), ("pierce", 3), ("pstep", 5.0), ("radius", 0.9))),
    _A("paradox", "PARADOX", "At the top of its arc a mirror twin splits off across the centre line.", "paradox", "paradox", "paradox",
       (("apex", ("mirror",)), ("radius", 1.1))),
    _A("atomicbreath", "ATOMIC BREATH", "A roaring blast that hurls every tank in reach away from it.", "atomic", "atomic", "atomic",
       (("push", 12.0), ("radius", 1.7), ("multi", 1))),
    _A("sporebloom", "SPORE BLOOM", "Grows a mushroom mound, then bursts it into six spore bombs.", "spore", "spores", "spore",
       (("terrain", "mound"), ("radius", 1.1), ("cluster", 6), ("cspace", 6.5), ("cr", 0.55), ("cdelay", 1.1))),
    _A("burrower", "BURROWER", "Dives into the sand and erupts beneath the first enemy ahead.", "worm", "sand", "eruption",
       (("burrow", 30.0), ("radius", 1.3))),
    _A("serpent", "SERPENT", "Lands, then slithers up to three hops toward the nearest enemy.", "serpent", "feathers", "jade",
       (("slither", 3), ("radius", 0.9))),
    _A("constellation", "CONSTELLATION", "Calls five stars down in a ring around the impact.", "astro", "constellation", "zodiac",
       (("stars", 5), ("radius", 0.9))),
    _A("broadside", "BROADSIDE", "A ghost galleon's volley: three cannonballs at once - short, true, long.", "cannonball", "ghostfire", "ghostfire",
       (("volley", 3), ("radius", 0.8))),
])
SHOP_AMMOS: tuple[AmmoType, ...] = (_SHOP_BASE_AMMOS[0:5] + _NEW_AMMOS[0] + _SHOP_BASE_AMMOS[5:10] + _NEW_AMMOS[1]
                                    + _SHOP_BASE_AMMOS[10:15] + _NEW_AMMOS[2] + _SHOP_BASE_AMMOS[15:20] + _NEW_AMMOS[3] + _PREMIUM_AMMOS)
TICKET_AMMOS: tuple[AmmoType, ...] = _ammos([
    _A("arcstorm", "ARC STORM", "A chain of lightning blasts.", "bolt", "arc", "thunder", (("chain", 6), ("cstep", 7.0), ("cr", 0.65), ("radius", 0.9))),
    _A("gavel", "GAVEL", "A small tap... then the verdict.", "comet", "solar", "nova", (("fuse", 1.0), ("fr", 2.0), ("radius", 0.6))),
    _A("coldfront", "COLD FRONT", "Six shards fall from the sky.", "shard", "frost", "shatter", (("apex", ("split", 6, 0.8)), ("subr", 0.65))),
    _A("sunburst", "SUNBURST", "A wide solar blast with bomblets.", "sun", "solar", "nova", (("radius", 1.5), ("multi", 1), ("cluster", 4), ("cr", 0.55))),
    _A("undertow", "UNDERTOW", "Drags tanks toward the blast.", "void", "mist", "implode", (("pull", 9.0), ("radius", 1.4))),
    _A("duneshot", "DUNE SHOT", "Skips across the sand, then scatters.", "shell", "embers", "cluster", (("bounce", 3), ("br", 0.45), ("cluster", 3))),
    _A("plague", "PLAGUE", "Spreading bomblets, then a cloud.", "drip", "mist", "cloud", (("cluster", 6), ("cr", 0.6), ("fuse", 0.9), ("fr", 1.6), ("radius", 0.6))),
    _A("umbra", "UMBRA", "Splits in the dark, then collapses.", "void", "mist", "implode", (("apex", ("split", 5, 0.8)), ("subr", 0.7), ("fuse", 0.8))),
    _A("starshower", "STARSHOWER", "Nine stars rain from the apex.", "star", "twinkle", "starrays", (("apex", ("split", 9, 1.1)), ("subr", 0.6))),
    _A("dragonfire", "DRAGONFIRE", "A river of flame along the ground.", "flame", "fire", "fire", (("chain", 5), ("cstep", 8.0), ("cr", 0.7), ("radius", 1.2))),
])
ANCIENT_AMMOS: tuple[AmmoType, ...] = _ammos([
    _A("sunfall", "SUNFALL", "A relic of light: a wide golden blast with falling stars.", "relic", "runes", "sigil",
       ((("radius", 1.5), ("apex", ("split", 4, 0.9)), ("subr", 0.7)))),
    _A("totality", "TOTALITY", "A watching eye that swallows light, then collapses.", "eye", "aeon", "eclipse",
       (("pull", 10.0), ("radius", 1.6), ("fuse", 0.8), ("fr", 1.8))),
    _A("tempest_a", "TEMPEST", "Wind and tide: chains of crashing waves.", "runes", "tides", "tidal",
       (("chain", 5), ("cstep", 7.5), ("cr", 0.7), ("radius", 1.0), ("wob", (3.0, 5.0)))),
    _A("cinderfall", "CINDERFALL", "A burning hexagram that rains molten stone.", "sigil", "cinders", "cinderstorm",
       (("cluster", 6), ("cr", 0.6), ("radius", 1.2), ("terrain", "mound"))),
    _A("timerift", "TIME RIFT", "Skips through time, then snaps back as a blast.", "sandglass", "chrono", "rewind",
       (("apex", ("jump", 26.0)), ("fuse", 0.9), ("fr", 1.9), ("radius", 1.1))),
])
ALL_AMMOS = AMMOS + SHOP_AMMOS + MISSION_AMMOS + TICKET_AMMOS + SECRET_AMMOS + ANCIENT_AMMOS
assert len(AMMOS) == 25 and AMMOS[-1].key == "aurora"
assert len({a.key for a in ALL_AMMOS}) == len(ALL_AMMOS)
AMMO_BY_KEY = {a.key: a for a in ALL_AMMOS}
DEFAULT_AMMO = AMMOS[0]
