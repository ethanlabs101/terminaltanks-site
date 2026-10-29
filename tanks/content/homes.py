"""Home screens. HOME_ORDER is the cycle order of every home screen; HomeTheme is a screen's sky, ground, logo
colours, weather, mascot tank and scenery layers (drawn by art/home_layers.py). The CLASSIC, MASTER and SECRET
screens are drawn by art/backdrops.py."""
from __future__ import annotations

from dataclasses import dataclass, replace

from tanks.colors import RGB, mix


SHOP_THEMES = ('SUNSET', 'MEADOW', 'DESERT', 'HARBOR', 'AUTUMN', 'DAWN', 'PRAIRIE', 'HARVEST', 'LAKESIDE', 'CAMPFIRE', 'TWILIGHT', 'FOGBANK', 'SPRING', 'MARKET', 'MONSOON', 'ARCTIC', 'JUNGLE', 'NEON', 'DEEPSEA', 'STORMFRONT', 'SYNTHWAVE', 'TOKYO', 'PYRAMIDS', 'TUNDRA', 'CANYONS', 'LAGOON', 'THUNDERHEAD', 'STEAMTOWN', 'ORBITRING', 'BAMBOO', 'MOLTEN', 'CRYSTALCAVE', 'BLOODMOON', 'EMERALD', 'GOLDENDUNES', 'NIGHTCITY', 'LAVAFALLS', 'VAPORWAVE', 'DEADSEA', 'SKYFORT', 'CYBERPUNK', 'MAELSTROM', 'ICEPALACE', 'SOLARSTORM', 'GHOSTTOWN', 'ECLIPSE', 'VOIDRIFT', 'SOLARCROWN', 'STARFALL', 'CELESTIAL', 'QUASAR', 'GALAXY', 'NEBULAR', 'HYPERGATE', 'BLACKHOLE', 'AURORAKING', 'CRYSTALPEAK', 'DRAGONSKY', 'CELESTIA', 'ASTRALSEA',
               'GLASSDESERT', 'LANTERNFEST', 'WORLDTREE', 'SKYWHALE', 'SHATTERLINE',
               'BIOLUME', 'SPIRITSHRINE', 'HOLOCITY', 'TESSERACT', 'KAIJUBAY', 'SHROOMGROVE', 'WORMSEA', 'JADETEMPLE', 'ORRERY', 'GHOSTARMADA')
MISSION_THEMES = ('OUTPOST', 'RADAR', 'WARZONE', 'ORBITAL', 'DEEPSPACE', 'INVASION')
TICKET_THEMES = ('VOLTCITY', 'CLOCKWORKS', 'FROSTCATHEDRAL', 'SUNTEMPLE', 'SUNKENCITY', 'PYRAMIDPLAIN', 'CHEMWORKS', 'GOTHICKEEP', 'ORBITALCITY', 'PAGODAPEAK')
ANCIENT_THEMES = ('EMBERSANCTUM', 'TEMPESTSPIRES', 'ASTRALRIFT', 'SOLARIS', 'CHRONOS', 'ETERNAL')
HOME_ORDER = ("CLASSIC",) + SHOP_THEMES + MISSION_THEMES + TICKET_THEMES + ANCIENT_THEMES + ("MASTER", "SECRET")   # every home screen, in cycle order


# ---------------------------------------------------------------------------
# Home screens that can be bought (the Master and Secret screens are earned / cheat-only).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class HomeTheme:
    key: str
    name: str
    blurb: str
    sky: tuple              # gradient stops, horizon (0) -> zenith (1)
    far: RGB                # distant ridge
    ground: RGB
    ground_top: RGB
    accent: RGB             # frame / highlight colour
    logo_a: RGB             # logo gradient, top -> bottom
    logo_b: RGB
    fx: str                 # drifting-particle layer (key of MOTE_STYLES) or ""
    hero: str               # tank design shown firing on the title screen
    hero_ammo: str
    stars: bool = True
    aurora: bool = False
    corona: bool = False
    layers: tuple = ()      # scenery layers drawn by ThemeBackdrop: see LAYER_DRAWERS in art/home_layers.py (moon, sun, city, mountains, grid, ...)


def _hx(key: str, name: str, blurb: str, sky4: tuple, far: RGB, ground: RGB, accent: RGB, fx: str, hero: str, ammo: str,
        layers: tuple, stars: bool = True, aurora: bool = False, corona: bool = False) -> HomeTheme:
    """Compact HomeTheme: derives the ground-top colour and the logo gradient from the accent."""
    return HomeTheme(key, name, blurb, tuple(zip((0, 0.28, 0.62, 1), sky4)), far, ground, mix(ground, accent, 0.55), accent,
                     mix(accent, (255, 255, 255), 0.65), accent, fx, hero, ammo, stars, aurora, corona, layers)


def _ht(key: str, name: str, blurb: str, sky4: tuple, far: RGB, ground: RGB, top: RGB, accent: RGB, la: RGB, lb: RGB, fx: str,
        hero: str, ammo: str, stars: bool = True, aurora: bool = False, corona: bool = False) -> HomeTheme:
    sky = tuple(zip((0, 0.28, 0.62, 1), sky4))
    return HomeTheme(key, name, blurb, sky, far, ground, top, accent, la, lb, fx, hero, ammo, stars, aurora, corona)


HOME_THEMES: dict[str, HomeTheme] = {t.key: t for t in (
    # --- shop, row 1 (cheap) ---------------------------------------------------------------------------------
    _ht("SUNSET", "SUNSET RIDGE", "A warm dusk with drifting fireflies.", ((255, 170, 100), (230, 100, 110), (90, 40, 110), (14, 10, 40)),
        (70, 36, 84), (30, 16, 34), (150, 100, 70), (255, 170, 110), (255, 225, 160), (230, 110, 90), "fireflies", "ranger", "blazer"),
    _ht("MEADOW", "MEADOW MORN", "Green hills under a soft morning haze.", ((200, 240, 200), (120, 200, 180), (40, 90, 130), (10, 20, 50)),
        (40, 90, 70), (24, 50, 34), (110, 170, 90), (150, 235, 150), (230, 255, 200), (90, 200, 120), "fireflies", "mule", "blazer"),
    _ht("DESERT", "DESERT NOON", "Hot sand and drifting dust.", ((255, 210, 140), (240, 150, 90), (120, 70, 90), (20, 14, 40)),
        (120, 70, 60), (80, 50, 36), (210, 160, 100), (255, 200, 120), (255, 240, 190), (220, 140, 70), "ash", "scout", "dasher", False),
    _ht("HARBOR", "BLUE HARBOR", "Dusk over still water.", ((255, 200, 170), (150, 160, 200), (50, 70, 130), (8, 12, 40)),
        (40, 56, 100), (20, 30, 56), (110, 140, 190), (150, 190, 255), (225, 240, 255), (100, 150, 230), "", "badger", "fizz"),
    _ht("AUTUMN", "AUTUMN LEAVES", "Amber light and falling ash.", ((255, 190, 110), (200, 110, 70), (80, 40, 60), (16, 8, 30)),
        (80, 40, 40), (40, 24, 24), (170, 100, 50), (255, 170, 80), (255, 230, 170), (210, 100, 50), "ash", "pioneer", "slag"),
    # --- shop, row 2 (mid) -----------------------------------------------------------------------------------
    _ht("ARCTIC", "ARCTIC NIGHT", "Falling snow under a freezing sky.", ((190, 230, 255), (100, 160, 220), (30, 56, 120), (6, 10, 36)),
        (40, 62, 104), (30, 48, 80), (190, 215, 235), (150, 220, 255), (230, 250, 255), (90, 170, 230), "snow", "glacier", "cryo"),
    _ht("JUNGLE", "JUNGLE CANOPY", "Humid green dusk full of fireflies.", ((190, 255, 170), (80, 190, 120), (20, 70, 80), (4, 16, 24)),
        (20, 70, 60), (10, 36, 30), (70, 150, 80), (120, 255, 150), (230, 255, 190), (60, 200, 110), "fireflies", "mantis", "toxin"),
    _ht("NEON", "NEON CITY", "A synthwave skyline in violet and pink.", ((255, 120, 200), (160, 60, 200), (50, 20, 110), (6, 4, 28)),
        (40, 20, 80), (14, 10, 34), (200, 60, 220), (255, 100, 230), (255, 230, 255), (220, 70, 230), "stardust", "warhound", "photon"),
    _ht("DEEPSEA", "DEEP SEA", "Cold currents and drifting plankton.", ((120, 230, 255), (40, 140, 200), (10, 50, 110), (2, 6, 30)),
        (10, 50, 100), (6, 24, 56), (60, 140, 190), (90, 220, 255), (210, 250, 255), (40, 170, 230), "snow", "leviathan", "ripple"),
    _ht("STORMFRONT", "STORM FRONT", "A bruised sky about to break.", ((190, 200, 220), (100, 110, 150), (36, 40, 70), (6, 6, 20)),
        (46, 50, 80), (22, 24, 40), (120, 130, 170), (170, 190, 255), (235, 240, 255), (120, 140, 230), "ash", "centurion", "ripple", False),
    # --- shop, row 3 (pro) -----------------------------------------------------------------------------------
    _ht("MOLTEN", "MOLTEN CORE", "A furnace sky raining embers.", ((255, 140, 50), (200, 50, 30), (70, 16, 24), (10, 2, 8)),
        (60, 16, 20), (24, 10, 12), (190, 70, 30), (255, 140, 60), (255, 240, 160), (220, 70, 30), "embers", "behemoth", "molten", False),
    _ht("CRYSTALCAVE", "CRYSTAL CAVE", "A violet aurora over glittering stone.", ((220, 180, 255), (140, 100, 220), (50, 30, 120), (6, 4, 30)),
        (60, 40, 120), (24, 16, 56), (180, 140, 255), (200, 160, 255), (245, 230, 255), (150, 100, 255), "stardust", "nightshade", "glacial",
        True, True),
    _ht("BLOODMOON", "BLOOD MOON", "A crimson night and drifting ash.", ((255, 120, 110), (190, 40, 60), (60, 10, 40), (8, 2, 14)),
        (50, 10, 30), (20, 6, 14), (150, 30, 50), (255, 90, 100), (255, 220, 200), (210, 40, 60), "ash", "reaper", "molten"),
    _ht("EMERALD", "EMERALD AURORA", "Green ribbons over snowy hills.", ((160, 255, 210), (40, 170, 150), (10, 60, 90), (2, 8, 26)),
        (10, 60, 80), (6, 26, 40), (60, 170, 150), (100, 255, 200), (220, 255, 240), (40, 220, 170), "snow", "banshee", "frostbite", True, True),
    _ht("GOLDENDUNES", "GOLDEN DUNES", "Sunset-lit dunes and rising embers.", ((255, 230, 150), (255, 150, 70), (120, 50, 70), (16, 6, 24)),
        (90, 40, 50), (30, 14, 20), (220, 140, 60), (255, 190, 90), (255, 245, 200), (240, 140, 50), "embers", "behemoth", "cinder"),
    # --- shop, row 4 (master tier) ---------------------------------------------------------------------------
    _ht("ECLIPSE", "TOTAL ECLIPSE", "A black sun, a prismatic corona and a river of stars.",
        ((255, 200, 120), (150, 60, 160), (40, 16, 90), (2, 2, 16)), (30, 14, 56), (10, 6, 20), (190, 150, 230), (210, 170, 255),
        (255, 236, 170), (190, 120, 255), "stardust", "emperor", "helix", True, True, True),
    _ht("VOIDRIFT", "VOID RIFT", "A tear in space, ringed by violet fire.", ((120, 60, 200), (50, 20, 120), (14, 6, 50), (0, 0, 10)),
        (20, 10, 50), (6, 4, 16), (120, 80, 220), (170, 120, 255), (230, 210, 255), (130, 70, 255), "stardust", "eternal", "eclipse",
        True, True, True),
    _ht("SOLARCROWN", "SOLAR CROWN", "A burning corona over a scorched world.", ((255, 250, 200), (255, 190, 90), (210, 80, 60), (30, 6, 30)),
        (110, 40, 40), (34, 10, 20), (255, 200, 90), (255, 220, 120), (255, 252, 220), (255, 170, 60), "embers", "celestial", "supernova",
        True, False, True),
    _ht("STARFALL", "STARFALL", "A river of stars falling through aurora.", ((150, 200, 255), (70, 90, 200), (20, 20, 100), (2, 2, 24)),
        (24, 24, 90), (8, 8, 36), (120, 160, 255), (160, 200, 255), (235, 245, 255), (100, 140, 255), "stardust", "dynasty", "nebula",
        True, True),
    _ht("CELESTIAL", "CELESTIAL GATE", "A gate of light beyond the clouds.", ((255, 230, 255), (220, 150, 255), (90, 50, 160), (8, 4, 36)),
        (70, 40, 130), (24, 14, 52), (240, 200, 255), (250, 200, 255), (255, 245, 255), (230, 140, 255), "fireflies", "overlord", "bloom",
        True, True, True),
    # --- new shop screens: each pairs a palette with scenery LAYERS so they differ in structure, not just colour ---------
    _hx("DAWN", "FIRST LIGHT", "A low sun over blue mountains.", ((255, 220, 160), (250, 160, 150), (110, 110, 170), (20, 24, 64)), (70, 80, 130), (28, 34, 60), (255, 190, 130), "", "scout", "slug", ("sun", "mountains")),
    _hx("PRAIRIE", "OPEN PRAIRIE", "Pine ridge and a warm evening sun.", ((255, 230, 170), (255, 180, 110), (130, 90, 120), (24, 20, 52)), (60, 70, 70), (26, 34, 30), (255, 200, 120), "fireflies", "mule", "lob", ("sun", "trees")),
    _hx("HARVEST", "HARVEST MOON", "A huge orange moon over dark pines.", ((255, 190, 100), (190, 100, 70), (70, 36, 60), (10, 8, 28)), (50, 30, 44), (20, 14, 22), (255, 160, 70), "ash", "badger", "dud", ("moon", "trees")),
    _hx("LAKESIDE", "QUIET LAKESIDE", "Still water below a mountain range.", ((190, 225, 255), (120, 170, 220), (50, 90, 150), (8, 16, 44)), (50, 80, 120), (18, 34, 60), (140, 200, 255), "", "turtle", "breeze", ("mountains", "ocean")),
    _hx("CAMPFIRE", "CAMPFIRE NIGHT", "Embers rising into a starry dark.", ((60, 50, 90), (40, 30, 70), (20, 16, 44), (4, 4, 18)), (24, 20, 40), (12, 10, 22), (255, 150, 60), "embers", "pioneer", "pebbles", ("trees", "moon")),
    _hx("TWILIGHT", "TWILIGHT TOWN", "A small town as the lights come on.", ((255, 170, 150), (190, 110, 150), (80, 60, 130), (12, 12, 44)), (50, 40, 80), (20, 18, 40), (255, 180, 160), "", "pebble", "skipper", ("moon", "city")),
    _hx("FOGBANK", "FOGBANK", "Rain through grey mist.", ((170, 180, 190), (120, 130, 150), (60, 70, 96), (14, 18, 32)), (70, 80, 100), (30, 36, 50), (190, 210, 230), "", "rusty", "twister", ("rain", "mountains"), False),
    _hx("SPRING", "SPRING MEADOW", "Green hills and a pale sun.", ((235, 250, 220), (170, 220, 190), (80, 150, 170), (20, 50, 90)), (60, 110, 90), (24, 52, 40), (170, 240, 150), "fireflies", "hopper", "borer", ("sun", "trees")),
    _hx("MARKET", "NIGHT MARKET", "Glowing windows in a crowded old town.", ((255, 200, 120), (180, 110, 110), (70, 50, 100), (10, 8, 32)), (60, 40, 70), (24, 18, 34), (255, 210, 110), "", "spud", "scatter", ("city", "moon")),
    _hx("MONSOON", "MONSOON", "Warm rain over a dark sea.", ((120, 150, 170), (70, 100, 130), (30, 50, 84), (6, 10, 28)), (30, 50, 80), (12, 22, 44), (130, 200, 240), "", "crate", "mudball", ("rain", "ocean"), False),
    _hx("SYNTHWAVE", "SYNTHWAVE", "A perspective grid under a striped sun.", ((255, 120, 190), (180, 60, 190), (60, 20, 120), (8, 4, 30)), (50, 20, 90), (14, 8, 34), (255, 90, 220), "", "outrider", "zigzag", ("sun", "grid")),
    _hx("TOKYO", "NEON RAIN", "A rain-soaked megacity.", ((90, 60, 150), (60, 36, 120), (30, 20, 80), (6, 4, 26)), (30, 24, 70), (12, 10, 30), (255, 110, 200), "", "marauder", "triskip", ("city", "rain")),
    _hx("PYRAMIDS", "PYRAMIDS", "Golden pyramids at dusk.", ((255, 220, 140), (250, 160, 90), (150, 80, 90), (24, 14, 44)), (110, 70, 60), (44, 28, 30), (255, 200, 110), "ash", "sandstorm", "rainmaker", ("sun", "pyramids"), False),
    _hx("TUNDRA", "TUNDRA", "Snow driven across pale mountains.", ((220, 235, 250), (160, 190, 225), (80, 110, 170), (14, 24, 56)), (110, 140, 180), (60, 80, 110), (190, 225, 255), "snow", "barracuda", "fireworks", ("mountains",)),
    _hx("CANYONS", "RED CANYONS", "Layered rock under a hot sun.", ((255, 210, 150), (240, 130, 90), (140, 60, 80), (24, 12, 40)), (130, 60, 56), (46, 24, 26), (255, 150, 90), "ash", "raider", "walker", ("sun", "mountains"), False),
    _hx("LAGOON", "MOON LAGOON", "A silver moon over a glassy lagoon.", ((150, 210, 235), (90, 150, 200), (30, 70, 130), (4, 10, 36)), (30, 60, 100), (10, 22, 46), (160, 230, 250), "fireflies", "stingray", "timecharge", ("moon", "ocean")),
    _hx("THUNDERHEAD", "THUNDERHEAD", "Lightning inside a boiling storm.", ((120, 120, 150), (70, 70, 110), (30, 30, 66), (6, 6, 22)), (36, 36, 70), (14, 14, 32), (200, 210, 255), "", "trident", "rockslide", ("lightning", "rain"), False),
    _hx("STEAMTOWN", "STEAMTOWN", "Smoking chimneys under a copper sky.", ((230, 170, 110), (170, 110, 90), (80, 56, 70), (14, 10, 26)), (66, 46, 54), (24, 18, 22), (255, 180, 100), "ash", "redoubt", "fortify", ("city",), False),
    _hx("ORBITRING", "RINGED WORLD", "A banded planet hangs overhead.", ((90, 100, 190), (50, 60, 140), (24, 24, 80), (4, 4, 24)), (30, 34, 90), (10, 12, 36), (150, 180, 255), "stardust", "harpoon", "tunneler", ("planet",)),
    _hx("BAMBOO", "BAMBOO RAIN", "Green stalks and soft rain.", ((190, 235, 200), (110, 190, 160), (40, 110, 110), (6, 24, 44)), (40, 90, 80), (14, 40, 34), (150, 240, 170), "", "cobra", "glasser", ("trees", "rain"), False),
    _hx("NIGHTCITY", "NIGHT CITY", "Towers, rain and a moon behind the clouds.", ((90, 70, 130), (50, 40, 100), (24, 20, 66), (4, 4, 22)), (30, 26, 64), (10, 10, 26), (170, 150, 255), "", "tempestor", "warpshell", ("moon", "city", "rain")),
    _hx("LAVAFALLS", "LAVA FALLS", "Burning peaks and a rain of embers.", ((255, 150, 60), (200, 60, 30), (80, 20, 24), (12, 2, 8)), (70, 20, 20), (24, 8, 10), (255, 130, 50), "embers", "hellcat", "tremor", ("mountains",), False),
    _hx("VAPORWAVE", "VAPORWAVE", "A pastel sun and a drifting planet.", ((255, 190, 230), (200, 140, 240), (110, 90, 200), (20, 20, 70)), (90, 70, 160), (24, 20, 56), (255, 150, 230), "", "typhoon", "gravmine", ("sun", "grid", "planet")),
    _hx("DEADSEA", "DEAD SEA", "A pale moon on black water.", ((120, 140, 170), (70, 90, 130), (30, 40, 80), (4, 6, 22)), (30, 40, 70), (8, 12, 28), (170, 200, 235), "ash", "gravedigger", "hailfall", ("moon", "ocean")),
    _hx("SKYFORT", "SKY FORTRESS", "A needle tower above the clouds.", ((200, 220, 255), (130, 160, 230), (60, 80, 160), (8, 12, 48)), (60, 80, 140), (22, 30, 60), (190, 220, 255), "snow", "warmaster", "ricochet", ("tower", "comet")),
    _hx("CYBERPUNK", "CYBERPUNK", "Glitching skyline in acid rain.", ((120, 255, 200), (50, 180, 170), (20, 70, 110), (2, 8, 28)), (20, 70, 90), (6, 22, 34), (80, 255, 200), "", "shatterer", "detonator", ("city", "rain", "glitch"), True, True),
    _hx("MAELSTROM", "MAELSTROM", "Black water lit by lightning.", ((90, 110, 140), (50, 70, 110), (20, 34, 70), (4, 6, 22)), (24, 34, 66), (8, 12, 30), (160, 200, 255), "", "stormrider", "colossus", ("ocean", "lightning", "rain"), False),
    _hx("ICEPALACE", "ICE PALACE", "A spire of ice under green aurora.", ((190, 250, 235), (100, 200, 200), (30, 100, 140), (4, 14, 48)), (40, 100, 130), (14, 36, 56), (160, 255, 230), "snow", "ironclad", "phantomorb", ("tower", "mountains"), True, True),
    _hx("SOLARSTORM", "SOLAR STORM", "A giant sun and crackling bolts.", ((255, 250, 190), (255, 190, 90), (210, 90, 60), (40, 10, 30)), (130, 50, 40), (36, 12, 20), (255, 220, 120), "embers", "bloodhound", "meteor", ("sun", "lightning")),
    _hx("GHOSTTOWN", "GHOST TOWN", "Empty windows under a cold moon.", ((150, 160, 190), (90, 100, 140), (40, 46, 84), (6, 8, 28)), (40, 46, 80), (12, 14, 30), (190, 205, 240), "ash", "sandshark", "sunder", ("moon", "city"), True),
    _hx("QUASAR", "QUASAR", "A ringed world and a cosmic jet.", ((200, 160, 255), (120, 80, 220), (50, 30, 140), (4, 2, 28)), (50, 36, 120), (12, 8, 40), (190, 150, 255), "stardust", "ascendant", "vortex", ("planet", "comet"), True, True, True),
    _hx("GALAXY", "SPIRAL GALAXY", "Comets crossing a violet galaxy.", ((130, 140, 255), (80, 70, 200), (36, 30, 120), (2, 2, 24)), (36, 34, 110), (10, 10, 40), (170, 180, 255), "stardust", "seraphim", "skyfall", ("planet", "comet"), True, True),
    _hx("NEBULAR", "NEBULA SEA", "Pink and teal clouds in deep space.", ((255, 160, 220), (160, 90, 210), (50, 70, 170), (2, 4, 30)), (50, 60, 150), (12, 14, 50), (255, 160, 230), "stardust", "doombringer", "wormhole", ("comet",), True, True),
    _hx("HYPERGATE", "HYPERGATE", "A tower of light and a streaming grid.", ((120, 255, 255), (50, 160, 220), (20, 60, 150), (2, 6, 34)), (24, 60, 130), (6, 14, 40), (120, 240, 255), "stardust", "starforge", "chainreact", ("tower", "grid", "comet"), True, True),
    _hx("BLACKHOLE", "EVENT HORIZON", "A black sun ringed in fire.", ((255, 200, 120), (180, 70, 90), (60, 24, 100), (2, 2, 18)), (30, 14, 56), (8, 6, 20), (255, 180, 120), "stardust", "arcanist", "faultline", ("planet", "comet"), True, True, True),
    _hx("AURORAKING", "AURORA KING", "Great ribbons over snowy peaks.", ((140, 255, 190), (60, 190, 170), (20, 90, 150), (2, 8, 40)), (24, 80, 120), (8, 24, 46), (130, 255, 190), "snow", "voidwalker", "mirrorshot", ("mountains", "comet"), True, True),
    _hx("CRYSTALPEAK", "CRYSTAL PEAK", "Glittering peaks and floating stars.", ((220, 190, 255), (150, 120, 240), (60, 50, 160), (6, 4, 36)), (60, 50, 150), (16, 14, 52), (210, 180, 255), "stardust", "sunbreaker", "overkill", ("mountains", "moon"), True, True),
    _hx("DRAGONSKY", "DRAGON SKY", "A storm over burning mountains.", ((255, 150, 110), (190, 70, 90), (70, 30, 100), (8, 4, 30)), (70, 28, 80), (20, 10, 34), (255, 150, 120), "embers", "templar", "cataclysm", ("mountains", "lightning"), True, True),
    _hx("CELESTIA", "CELESTIA", "A golden gate beyond the clouds.", ((255, 245, 200), (255, 200, 140), (200, 130, 190), (30, 20, 80)), (130, 90, 170), (40, 28, 70), (255, 230, 150), "fireflies", "monolith", "prismrain", ("tower", "sun", "comet"), True, True, True),
    _hx("ASTRALSEA", "ASTRAL SEA", "A starlit sea beneath ribbons of light.", ((140, 200, 255), (80, 130, 230), (30, 60, 160), (2, 6, 40)), (30, 60, 140), (8, 16, 50), (150, 210, 255), "stardust", "phoenix", "maelstrom", ("ocean", "comet", "planet"), True, True),
    # --- terminal ticket rewards ---------------------------------------------------------------------------------
    _hx("VOLTCITY", "VOLT CITY", "A storm over a city of towers.", ((90, 110, 190), (50, 60, 150), (24, 24, 90), (4, 4, 30)), (30, 34, 90), (10, 10, 36), (150, 210, 255), "", "voltsovereign", "arcstorm", ("city", "lightning", "rain")),
    _hx("CLOCKWORKS", "CLOCKWORKS", "A giant tower ticking over a copper town.", ((255, 220, 150), (210, 150, 90), (110, 76, 70), (20, 14, 30)), (90, 66, 60), (30, 22, 26), (255, 215, 120), "", "magistrate", "gavel", ("city", "tower")),
    _hx("FROSTCATHEDRAL", "FROST CATHEDRAL", "An ice cathedral beneath green aurora.", ((190, 250, 235), (100, 200, 210), (30, 100, 150), (4, 14, 50)), (40, 100, 140), (14, 36, 60), (160, 255, 235), "snow", "regent", "coldfront", ("tower", "mountains"), True, True),
    _hx("SUNTEMPLE", "SUN TEMPLE", "A temple at sunset.", ((255, 230, 150), (255, 160, 90), (200, 80, 90), (30, 12, 40)), (120, 56, 56), (36, 16, 24), (255, 210, 100), "embers", "solarch", "sunburst", ("sun", "pyramids")),
    _hx("SUNKENCITY", "SUNKEN CITY", "Drowned towers in black water.", ((120, 190, 220), (60, 120, 170), (20, 60, 120), (2, 8, 36)), (24, 60, 110), (8, 18, 44), (110, 210, 255), "fireflies", "abyssal", "undertow", ("city", "ocean")),
    _hx("PYRAMIDPLAIN", "PYRAMID PLAIN", "Pyramids and a huge moon.", ((255, 220, 160), (230, 150, 100), (130, 80, 110), (20, 14, 44)), (110, 70, 70), (40, 26, 34), (255, 215, 130), "ash", "pharaoh", "duneshot", ("moon", "pyramids")),
    _hx("CHEMWORKS", "CHEMICAL WORKS", "Smokestacks in acid rain.", ((170, 220, 120), (110, 160, 100), (50, 80, 80), (8, 18, 30)), (50, 80, 60), (18, 28, 24), (170, 255, 100), "ash", "baron", "plague", ("city", "rain"), False),
    _hx("GOTHICKEEP", "GOTHIC KEEP", "A castle against a stormy moon.", ((150, 130, 190), (90, 70, 150), (40, 30, 90), (6, 4, 30)), (40, 30, 80), (12, 10, 30), (190, 160, 255), "", "shadowlord", "umbra", ("city", "moon", "lightning")),
    _hx("ORBITALCITY", "ORBITAL CITY", "A space-station city and a distant world.", ((140, 200, 255), (70, 120, 230), (30, 50, 150), (2, 4, 36)), (30, 50, 140), (8, 14, 46), (150, 210, 255), "stardust", "overseer", "starshower", ("planet", "tower", "comet"), True, True),
    _hx("PAGODAPEAK", "PAGODA PEAK", "Pagodas above the clouds.", ((255, 200, 190), (210, 140, 160), (100, 80, 140), (14, 12, 44)), (80, 66, 120), (24, 20, 46), (255, 190, 170), "snow", "warlord", "dragonfire", ("mountains", "trees", "moon")),
    # --- mission rewards ---------------------------------------------------------------------------------------
    _ht("OUTPOST", "FORWARD OUTPOST", "A lonely radio mast on a cold ridge.", ((200, 215, 225), (110, 130, 150), (40, 54, 70), (8, 12, 22)),
        (44, 56, 70), (24, 32, 42), (130, 150, 160), (170, 210, 230), (235, 245, 250), (110, 160, 190), "ash", "wardog", "bandit"),
    _ht("RADAR", "RADAR STATION", "Green sweeps across a dark horizon.", ((120, 255, 150), (40, 160, 90), (10, 60, 50), (2, 10, 14)),
        (12, 56, 44), (6, 26, 22), (60, 170, 110), (100, 255, 150), (220, 255, 230), (40, 200, 110), "fireflies", "spitfire", "salvo"),
    _ht("WARZONE", "WARZONE", "Burning horizon, smoke and sparks.", ((255, 170, 90), (190, 70, 40), (60, 24, 24), (10, 6, 10)),
        (50, 24, 22), (22, 12, 12), (150, 80, 50), (255, 150, 80), (255, 235, 190), (210, 80, 40), "embers", "blitz", "hailstorm", False),
    _ht("ORBITAL", "ORBITAL RING", "A station ring above a blue world.", ((140, 200, 255), (60, 110, 220), (20, 30, 110), (2, 2, 20)),
        (30, 44, 100), (10, 14, 44), (130, 180, 255), (150, 210, 255), (230, 245, 255), (90, 150, 255), "stardust", "judge", "meltdown",
        True, False, True),
    _ht("DEEPSPACE", "DEEP SPACE", "A violet nebula and a million stars.", ((200, 150, 255), (110, 60, 190), (36, 20, 100), (2, 2, 18)),
        (40, 24, 90), (12, 8, 36), (170, 130, 255), (200, 160, 255), (245, 230, 255), (150, 100, 255), "stardust", "hydra", "oblivion",
        True, True),
    _ht("INVASION", "ALIEN INVASION", "Saucers over the horizon, green fire in the sky.",
        ((150, 255, 170), (50, 190, 110), (24, 70, 100), (2, 8, 20)), (16, 50, 60), (6, 20, 28), (80, 220, 140), (120, 255, 170),
        (230, 255, 220), (60, 220, 150), "stardust", "ufo", "xenon", True, True, True),
)}
HOME_THEMES.update({t.key: t for t in (
    _hx("GLASSDESERT", "GLASS DESERT", "Twin suns over dunes of fused glass.", ((255, 214, 150), (255, 140, 112), (96, 44, 130), (14, 6, 40)), (112, 62, 104), (36, 22, 48),
        (150, 236, 246), "stardust", "prismatic_king", "prismrain", ("twinsuns",), True),
    _hx("LANTERNFEST", "LANTERN FEST", "A night festival: a thousand lanterns rising.", ((255, 190, 120), (214, 84, 70), (70, 24, 56), (8, 6, 30)), (64, 24, 44), (28, 14, 22),
        (255, 190, 100), "fireflies", "phoenix", "cataclysm", ("lanterns",), True),
    _hx("WORLDTREE", "WORLDTREE", "A colossal tree whose veins glow with starlight.", ((150, 255, 220), (60, 190, 150), (14, 70, 70), (2, 12, 24)), (10, 54, 56), (8, 24, 28),
        (120, 250, 180), "fireflies", "stormbringer", "maelstrom", ("worldtree",), True, True),
    _hx("SKYWHALE", "SKY WHALE", "A sky-whale as big as a moon drifts through the stars.", ((190, 220, 255), (70, 120, 200), (20, 44, 100), (2, 6, 24)), (16, 40, 92), (8, 14, 36),
        (170, 220, 255), "stardust", "singularity", "eventhorizon", ("whale",), True, True),
    _hx("SHATTERLINE", "SHATTERLINE", "A fractured sky of drifting, prismatic glass.", ((255, 230, 255), (180, 120, 255), (70, 34, 140), (8, 2, 24)), (56, 28, 104), (16, 8, 40),
        (226, 190, 255), "stardust", "chronos", "quantumecho", ("shards",), True, True),
    # --- premium II ---------------------------------------------------------------------------------------------------
    _hx("BIOLUME", "BIOLUME TRENCH", "The deep sea: jellyfish lanterns drifting up through the dark.", ((20, 70, 110), (10, 40, 80), (4, 18, 48), (2, 6, 20)),
        (6, 16, 30), (4, 10, 20), (120, 255, 235), "", "luminary", "anglerlure", ("abyss",), False),
    _hx("SPIRITSHRINE", "SPIRIT SHRINE", "Torii gates climb to a moonlit shrine. Foxfire drifts between them.", ((120, 70, 140), (70, 40, 110), (30, 20, 70), (8, 6, 30)),
        (26, 16, 40), (16, 10, 24), (150, 200, 255), "", "kitsune", "foxfire", ("shrine",), True),
    _hx("HOLOCITY", "HOLO CITY", "Rain, neon and holograms over a city that never sleeps.", ((170, 60, 140), (90, 30, 110), (36, 14, 70), (10, 6, 30)),
        (8, 6, 18), (6, 4, 14), (90, 240, 255), "", "holoronin", "hardlight", ("holocity",), False),
    _hx("TESSERACT", "THE TESSERACT", "A hypercube turning through dimensions you cannot see.", ((90, 30, 140), (40, 16, 90), (14, 6, 44), (2, 2, 14)),
        (20, 8, 40), (12, 4, 26), (200, 160, 255), "stardust", "tesseract", "paradox", ("hyper",), True),
    _hx("KAIJUBAY", "KAIJU BAY", "A storm, a harbour city and something enormous wading ashore.", ((120, 128, 150), (78, 88, 112), (40, 46, 68), (14, 16, 28)),
        (12, 14, 20), (8, 10, 14), (130, 205, 255), "", "kaiju", "atomicbreath", ("kaiju",), False),
    _hx("SHROOMGROVE", "GLOWSHROOM GROVE", "Giant glowing mushrooms breathing spores into the night.", ((40, 80, 90), (24, 50, 70), (14, 24, 50), (4, 8, 24)),
        (14, 26, 30), (8, 16, 18), (130, 255, 200), "fireflies", "sporeking", "sporebloom", ("shrooms",), True),
    _hx("WORMSEA", "THE DEEP DESERT", "Three moons over endless dunes. Something vast moves beneath.", ((240, 170, 110), (170, 90, 90), (70, 40, 80), (14, 10, 34)),
        (90, 56, 40), (60, 36, 26), (255, 170, 80), "", "sandwyrm", "burrower", ("wormsea",), True),
    _hx("JADETEMPLE", "JADE TEMPLE", "A feathered serpent circles a pyramid in the jungle.", ((255, 200, 130), (230, 140, 90), (110, 90, 120), (30, 30, 70)),
        (20, 50, 34), (14, 34, 24), (120, 255, 170), "", "quetzal", "serpent", ("jadetemple",), False),
    _hx("ORRERY", "THE ORRERY", "A brass astrolabe the size of the sky, turning the stars.", ((50, 50, 110), (28, 30, 80), (12, 14, 48), (2, 4, 20)),
        (16, 18, 40), (10, 10, 26), (255, 226, 150), "", "zodiac", "constellation", ("orrery",), True),
    _hx("GHOSTARMADA", "GHOST ARMADA", "Spectral galleons sail a sea of cloud under a green moon.", ((60, 110, 100), (30, 64, 70), (12, 30, 40), (2, 8, 16)),
        (18, 36, 38), (10, 22, 24), (120, 255, 170), "", "wraithship", "broadside", ("armada",), True),

    replace(_ht("EMBERSANCTUM", "EMBER SANCTUM", "A volcanic temple above a river of fire.", ((255, 170, 70), (220, 70, 24), (90, 20, 16), (14, 4, 8)),
                (60, 14, 12), (22, 8, 8), (255, 120, 40), (255, 150, 60), (255, 236, 170), (255, 110, 40), "inferno", "a_emberheart", "cinderfall"),
            layers=("volcano",)),
    replace(_ht("TEMPESTSPIRES", "TEMPEST SPIRES", "Floating isles in a world-ending storm.", ((150, 230, 250), (40, 130, 170), (14, 50, 90), (2, 10, 24)),
                (14, 40, 70), (6, 18, 30), (110, 200, 230), (120, 232, 255), (230, 252, 255), (80, 190, 240), "tempest", "a_tempest", "tempest_a",
                True, True), layers=("isles", "rain", "lightning")),
    replace(_ht("ASTRALRIFT", "ASTRAL RIFT", "A ring of light and dark at the end of time.", ((255, 226, 160), (150, 90, 230), (40, 16, 100), (2, 0, 14)),
                (36, 20, 80), (8, 4, 26), (255, 226, 150), (214, 170, 255), (255, 248, 214), (170, 120, 255), "rift", "a_umbral", "totality",
                True, True, True), layers=("riftring",)),
    replace(_ht("SOLARIS", "SOLARIS", "A sun that never sets over a sea of gold.", ((255, 248, 210), (255, 196, 90), (200, 110, 40), (40, 16, 10)),
                (120, 60, 24), (30, 14, 8), (255, 210, 90), (255, 226, 130), (255, 252, 226), (255, 190, 70), "stardust", "a_solaris", "sunfall",
                True, False, True), layers=("sunburst",)),
    replace(_ht("CHRONOS", "CHRONOS", "Time itself, caught in an hourglass of gold.", ((255, 236, 190), (190, 130, 60), (70, 40, 40), (8, 4, 10)),
                (70, 40, 30), (16, 10, 8), (226, 176, 70), (255, 236, 176), (255, 250, 232), (230, 170, 70), "stardust", "a_chronos", "timerift",
                True, False, True), layers=("hourglass",)),
    replace(_ht("ETERNAL", "ETERNAL", "The legend's own sanctum. The universe is safe. Because of you.", ((255, 250, 230), (255, 206, 110), (120, 70, 190), (4, 2, 20)),
                (70, 40, 120), (14, 8, 30), (255, 226, 150), (255, 230, 150), (255, 255, 244), (255, 200, 90), "rift", "a_martyr", "timerift",
                True, True, False), layers=("sanctum",)),
)})
assert set(HOME_ORDER) == {"CLASSIC", "MASTER", "SECRET"} | set(HOME_THEMES) and len(HOME_ORDER) == len(set(HOME_ORDER))
