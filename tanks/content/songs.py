"""The soundtrack. Each entry is its own piece: motif (A), answer (B), chord progression, mode, metre, tempo, form
and arrangement style. Durations are 16th notes; degrees are scale steps (' = octave up, , = down, # b = altered).
Songs not listed here (most home screens and battlefields) are written by audio/house_composer.py."""
from __future__ import annotations

from tanks.audio.composer import SongSpec


SONGS: dict = {}


def _S(key, name, cat, bpm, root, scale, meter, style, prog, mel, form="I A B A2 C X O", desc="", **kw) -> None:
    SONGS[key] = SongSpec(key, name, cat, bpm, root, scale, meter, style, prog, mel, form, desc, **kw)


# ---------------------------------------------------------------- home screens / menus
_S("main_theme", "TERMINAL TANKS (MAIN THEME)", "menu", 112, 50, "dor", "44", "synthwave",
   {"A": "1m 7M 4M 1m", "B": "3M 4M 1m 5m"},
   {"A": "1:4 5:4 4:2 5:2 6:4 | 5:6 4:2 3:4 2:4 | 1:4 5:4 4:2 5:2 1':4 | 7:6 6:2 5:8",
    "B": "3:4 4:4 5:8 | 6:4 5:2 4:2 3:8 | 2:4 3:4 4:4 5:4 | 2:12 r:4"}, desc="The anthem of the artillery. It plays wherever you start.")
_S("green_hills", "GREEN HILLS, LONG SHADOWS", "menu", 104, 50, "maj", "68", "jig",
   {"A": "1 4 1 5", "B": "6m 4 1 5"},
   {"A": "5:2 3:2 1:2 3:4 5:2 | 6:2 5:2 3:2 2:6 | 3:2 5:2 1':2 7:4 5:2 | 6:2 4:2 2:2 1:6",
    "B": "3':4 2':2 1':4 6:2 | 5:4 3:2 5:6 | 4:2 6:2 1':2 7:2 6:2 5:2 | 3:6 2:6"}, desc="Flute and harp over open fields.")
_S("embers_and_ale", "EMBERS AND ALE", "menu", 92, 43, "dor", "34", "waltz",
   {"A": "1m 4M 1m 5m", "B": "7M 3M 4M 5m"},
   {"A": "5:4 4:2 3:2 2:4 | 3:8 1:4 | 2:4 3:2 4:2 5:4 | 4:12",
    "B": "1':6 7:2 6:4 | 5:8 3:4 | 4:4 5:2 6:2 4:4 | 5:12"}, lead="reed", lead2="guitar", desc="A tavern waltz for the hour after battle.")
_S("mirage_road", "MIRAGE ROAD", "menu", 88, 45, "phd", "44", "desert",
   {"A": "1 2M 1 7m", "B": "4m 2M 1 1"},
   {"A": "1:2 2:2 3:4 2:2 1:2 7,:4 | 1:8 r:2 5:2 4:2 3:2 | 2:4 3:2 4:2 5:6 4:2 | 3:2 2:2 1:12",
    "B": "5:4 6:4 5:2 4:2 3:4 | 4:8 3:4 2:4 | 3:2 2:2 1:4 2:4 7,:4 | 1:16"}, desc="Heat haze, distant drums, a road with no end.")
_S("frost_lullaby", "FROST LULLABY", "menu", 84, 52, "lyd", "34", "lullaby",
   {"A": "1 2 1 5", "B": "6m 2 4# 5"},
   {"A": "3:4 5:4 4:4 | 3:6 2:2 1:4 | 2:4 3:4 5:4 | 6:12",
    "B": "1':4 7:4 6:4 | 5:8 4:4 | 3:4 4:4 5:2 3:2 | 2:12"}, desc="A music box left out in the snow.")
_S("neon_arcade", "NEON ARCADE", "menu", 118, 47, "min", "44", "synthwave",
   {"A": "1m 6M 3M 7M", "B": "4m 6M 7M 7M"},
   {"A": "1:2 3:2 5:2 1':4 7:2 5:4 | 6:4 5:2 3:2 5:8 | 1:2 3:2 5:2 1':4 3':2 2':4 | 7:8 5:8",
    "B": "4:4 6:4 1':8 | 7:4 6:2 5:2 6:8 | 4:4 6:4 7:4 2':4 | 1':16"}, lead="hollow", desc="Rain on chrome. Every sign is still on.")
_S("undertow_dub", "UNDERTOW DUB", "menu", 76, 41, "min", "44", "dub",
   {"A": "1m 4m 1m 7M", "B": "6M 7M 1m 1m"},
   {"A": "r:4 5:2 4:2 3:8 | r:4 3:2 4:2 5:4 7:4 | 1':8 7:4 5:4 | 4:8 r:8",
    "B": "3:4 4:4 5:4 3:4 | 1:16 | 7,:4 1:4 2:4 4:4 | 3:16"}, desc="The sea floor keeps its own slow time.")
_S("ash_kingdom", "ASH KINGDOM", "menu", 80, 40, "hmin", "34", "gothic",
   {"A": "1m 6M 4m 5M", "B": "6M 2d 5M 1m"},
   {"A": "1:4 2:4 3:4 | 5:8 4:4 | 3:4 2:4 7,:4 | 1:12",
    "B": "6:6 5:2 4:4 | 3:8 2:4 | 7,:4 1:4 2:4 | 5,:12"}, form="I A B C A O", desc="Cinders falling over a throne nobody sits on.")
_S("canopy", "UNDER THE CANOPY", "menu", 98, 50, "pent", "44", "eastern",
   {"A": "1 3 4 1", "B": "2 4 3 1"},
   {"A": "1:2 2:2 3:4 5:2 3:2 2:4 | 1:6 5,:2 1:8 | 3:2 4:2 5:4 1':2 5:2 4:4 | 3:16",
    "B": "5:4 4:4 3:2 2:2 1:4 | 2:8 3:8 | 5:2 1':2 5:4 4:4 3:4 | 2:8 1:8"}, harm_i="marimba", lead="flute", desc="Marimba rain under green leaves.")
_S("starlight_drift", "STARLIGHT DRIFT", "menu", 72, 45, "lyd", "54", "cosmic",
   {"A": "1 2 6m 5", "B": "4# 2 1 1"},
   {"A": "5:6 4:4 3:6 2:4 | 1:10 5,:4 1:6",
    "B": "3:4 4:4 5:6 6:6 | 5:20"}, desc="Nothing but light-years, and you in the middle of them.")
_S("ghost_waltz", "GHOST WALTZ", "menu", 96, 42, "hung", "34", "horror",
   {"A": "1m 4# 1m 5M", "B": "6M 4# 5M 1m"},
   {"A": "5:4 4:2 3:2 2:4 | 1:8 7,:4 | 1:4 3:4 5:4 | 4:12",
    "B": "6:4 5:4 4:4 | 3:8 2:4 | 7,:4 1:4 2:4 | 1:12"}, lead="music_box", desc="The dancers left. The music did not.")
_S("first_contact", "FIRST CONTACT", "menu", 90, 46, "lyd", "44", "ambient",
   {"A": "1 2 1 2", "B": "6m 5 4# 2"},
   {"A": "1':6 7:2 4:8 | 5:4 3:4 2:8 | 1':6 2':2 4':8 | 3':16",
    "B": "6:4 5:4 4:4 3:4 | 2:16 | 4:4 5:4 6:4 1':4 | 7:16"}, lead="theremin", desc="Radar dishes turn toward something that answered.")
_S("masters_throne", "THE MASTER'S THRONE", "menu", 70, 41, "min", "44", "fanfare",
   {"A": "1m 6M 7M 1m", "B": "4m 5M 6M 5M"},
   {"A": "1:8 5:4 6:4 | 5:8 4:4 3:4 | 1:4 3:4 5:4 1':4 | 7:16",
    "B": "6:4 7:4 1':8 | 2':8 1':4 7:4 | 6:4 5:4 4:4 3:4 | 5:16"}, form="I A B A2 O", desc="The crown is yours. The room is very quiet.")
_S("kernel_panic", "KERNEL PANIC", "menu", 152, 42, "phr", "78", "glitch",
   {"A": "1m 2M 1m 7m", "B": "6M 2M 4m 5d"},
   {"A": "1:1 1:1 2:2 1:2 5:2 4:2 3:4 | 1:2 2:2 3:2 5:2 7:2 1':4 | 7:1 5:1 3:2 1:2 2:2 3:2 2:4 | 1:14",
    "B": "5:2 6:2 5:2 3:2 2:2 1:4 | 2:1 3:1 5:2 2:2 3:2 6:2 5:4 | 4:2 3:2 2:2 1:2 7,:2 6,:4 | 7,:14"},
   form="I A A2 B D X C X O", desc="SECRET EDITION. A kernel, a fault, and a very fast fix.", groove_b="glitch")
_S("protector", "PROTECTOR OF THE UNIVERSE", "menu", 66, 45, "lyd", "34", "hymn",
   {"A": "1 2 6m 5", "B": "4# 2 3m 1"},
   {"A": "5:8 6:4 | 5:4 4:4 3:4 | 2:8 3:4 | 1:12",
    "B": "1':8 7:4 | 6:4 5:4 4:4 | 5:8 6:4 | 5:12"}, form="I A B A2 C X O", desc="ETERNAL EDITION. The hymn the stars kept for you.")
_S("solaris_hymn", "SOLARIS", "menu", 84, 48, "mix", "44", "fanfare",
   {"A": "1 7M 4 1", "B": "6m 7M 1 1"},
   {"A": "1:4 3:4 5:8 | 6:4 5:4 7b:8 | 1':4 7b:2 6:2 5:4 3:4 | 4:16",
    "B": "5:4 6:4 7b:4 1':4 | 2':8 1':8 | 6:4 4:4 7b:4 6:4 | 5:16"}, lead="horn", desc="The ancient sun rises one more time.")
_S("chronos_clockwork", "CHRONOS", "menu", 108, 46, "wt", "44", "clock",
   {"A": "1 2 3 1", "B": "4 5 4 1"},
   {"A": "1:2 2:2 3:2 4:2 5:4 4:4 | 3:4 2:4 1:8 | 6:2 5:2 4:2 3:2 2:4 3:4 | 1:16",
    "B": "1':4 6:4 5:4 4:4 | 3:8 4:8 | 5:2 4:2 3:2 2:2 1:4 6,:4 | 1:16"}, desc="Every gear in the universe, ticking in step.")
_S("glass_desert", "GLASS DESERT", "menu", 96, 47, "phd", "54", "desert",
   {"A": "1 2M 1 1", "B": "6M 7m 1 1"},
   {"A": "5:2 4:2 3:2 2:4 1:4 2:6 | 3:4 4:2 3:2 2:2 1:10",
    "B": "1':6 7:2 6:2 5:6 4:4 | 3:4 2:4 1:12"}, harm_i="harp", lead="flute", desc="Twin suns on dunes of fused glass.")
_S("lantern_festival", "LANTERN FESTIVAL", "menu", 100, 48, "pent", "44", "eastern",
   {"A": "1 4 3 1", "B": "2 3 4 1"},
   {"A": "3:2 5:2 1':4 5:4 3:4 | 2:2 3:2 5:4 3:8 | 3:2 5:2 1':4 2':4 1':4 | 5:16",
    "B": "1':4 2':2 1':2 5:8 | 3:4 5:4 2:8 | 3:4 2:4 1:4 5,:4 | 1:16"}, lead="erhu", desc="A thousand paper lanterns rising.")
_S("worldtree", "WORLDTREE", "menu", 78, 43, "dor", "68", "folk",
   {"A": "1m 4M 7M 1m", "B": "3M 4M 5m 1m"},
   {"A": "1:6 3:4 4:2 | 5:6 4:6 | 3:2 4:2 5:2 7:4 6:2 | 5:12",
    "B": "1':6 7:4 6:2 | 5:12 | 4:2 5:2 6:2 4:4 3:2 | 1:12"}, lead="flute", lead2="choir", desc="Starlight climbing through ancient roots.")
_S("sky_whale", "SONG OF THE SKY WHALE", "menu", 64, 41, "maj", "34", "ambient",
   {"A": "1 4 6m 5", "B": "4 5 3m 6m"},
   {"A": "5:8 6:4 | 1':12 | 7:4 6:4 5:4 | 3:12",
    "B": "4:8 5:4 | 6:12 | 5:4 4:4 3:4 | 2:12"}, lead="choir_o", lead2="theremin", desc="Something as big as a moon is singing.")
_S("shatterline", "SHATTERLINE", "menu", 124, 49, "lyd", "44", "glitch",
   {"A": "1 2 7m 1", "B": "6m 2 4# 5"},
   {"A": "5:2 1':2 7:2 5:2 4:4 5:4 | 3:4 2:4 1:8 | 5:2 1':2 2':2 3':2 2':4 1':4 | 7:16",
    "B": "4:4 5:4 6:4 7:4 | 1':16 | 6:2 5:2 4:2 3:2 2:4 3:4 | 5:16"}, lead="music_box", lead2="glasspad", desc="Floating plates of prismatic glass.")
# ---------------------------------------------------------------- story / interface
_S("whisper", "A VOICE", "story", 60, 45, "loc", "44", "horror",
   {"A": "1d 2M 1d 7m"}, {"A": "5:8 4:8 | 3:8 2:8 | 1:16 | r:16"}, form="I A C O", desc="Someone has been watching you fight.")
_S("time_machine", "THE ARCANE TIME MACHINE", "story", 63, 40, "wt", "34", "hymn",
   {"A": "1 2 3 1", "B": "4 5 4 2"},
   {"A": "1:4 2:4 3:4 | 5:8 4:4 | 3:4 2:4 1:4 | 2:12",
    "B": "5:4 6:4 7:4 | 1':12 | 7:4 6:4 5:4 | 4:12"}, form="I A B C A O", lead2="celesta", desc="The machine that kept a man alive past time.")
_S("the_blessing", "THE MARTYR'S BLESSING", "story", 72, 45, "maj", "34", "hymn",
   {"A": "1 4 5 1", "B": "6m 4 2m 5"},
   {"A": "3:4 5:4 1':4 | 7:8 5:4 | 6:4 5:4 4:4 | 3:12",
    "B": "1':6 2':2 1':4 | 6:12 | 5:4 6:4 7:4 | 1':12"}, form="I A B A2 X O", desc="The last of his power, sealed and handed down to you.")
_S("shop_jingle", "THE ARMORY", "menu", 112, 48, "mix", "44", "house",
   {"A": "1 7M 4 1", "B": "4 5 7M 1"},
   {"A": "1:2 3:2 5:2 3:2 7b:4 6:4 | 5:8 3:8 | 1:2 3:2 5:2 1':4 7b:2 6:4 | 5:16",
    "B": "4:4 6:4 1':4 6:4 | 5:16 | 4:4 6:4 7b:4 2':4 | 1':16"}, form="I A B A2 O", desc="Browse. Buy. Blow things up.")
_S("workshop", "THE WORKSHOP", "menu", 96, 45, "dor", "44", "funk",
   {"A": "1m7 4M 1m7 4M", "B": "7M 6m 5m 4M"},
   {"A": "1:2 r:2 3:2 4:2 5:4 r:4 | 7:2 5:2 4:2 3:2 1:8 | 1:2 r:2 3:2 4:2 5:4 7:4 | 1':8 r:8",
    "B": "4:4 3:4 1:4 7,:4 | 1:16 | 5:4 4:4 3:4 2:4 | 1:16"}, form="I A B A2 O", desc="Spanners, sparks and a bass line.")
_S("tutorial", "TRAINING GROUND", "battle", 104, 48, "maj", "44", "folk",
   {"A": "1 5 6m 4", "B": "4 5 1 1"},
   {"A": "1:4 3:4 5:4 3:4 | 4:4 6:4 5:8 | 3:4 5:4 1':4 6:4 | 5:16",
    "B": "4:4 5:4 6:4 7:4 | 1':16 | 6:4 5:4 4:4 2:4 | 1:16"}, desc="Aim, power, wind. Again.")
# ---------------------------------------------------------------- battlefields (map families)
_S("steel_rain", "STEEL RAIN", "battle", 132, 40, "min", "44", "metal2",
   {"A": "1m 6M 7M 1m", "B": "4m 6M 5m 7M"},
   {"A": "1:2 1:2 5:4 4:2 3:2 2:4 | 1:4 3:4 5:8 | 6:2 5:2 4:4 3:2 2:2 1:4 | 7,:8 5,:8",
    "B": "4:4 5:4 6:4 7:4 | 1':8 5:8 | 6:4 5:4 4:4 2:4 | 1:16"}, desc="Default battlefield theme: shells and guitars.")
_S("iron_valley", "IRON VALLEY", "battle", 120, 43, "dor", "44", "march",
   {"A": "1m 4M 1m 5m", "B": "7M 4M 7M 5m"},
   {"A": "1:4 1:2 2:2 3:4 4:4 | 5:8 3:8 | 4:4 4:2 5:2 6:4 5:4 | 4:8 2:8",
    "B": "7:4 6:4 5:8 | 4:4 3:4 2:8 | 3:4 4:4 5:4 6:4 | 5:16"}, desc="A valley full of tracks and drums.")
_S("hedgerow_skirmish", "HEDGEROW SKIRMISH", "battle", 136, 50, "mix", "68", "jig",
   {"A": "1 7M 1 5m", "B": "4 1 7M 1"},
   {"A": "1:2 2:2 3:2 5:2 3:2 1:2 | 7b,:2 2:2 4:2 7b:2 4:2 2:2 | 1:2 3:2 5:2 1':2 7b:2 6:2 | 5:2 3:2 2:2 1:6",
    "B": "4:2 6:2 1':2 6:2 4:2 6:2 | 5:2 3:2 1:2 3:4 5:2 | 7b:2 6:2 5:2 4:2 3:2 2:2 | 1:12"}, desc="Fiddle-fast fighting between farm walls.")
_S("sandstorm_siege", "SANDSTORM SIEGE", "battle", 126, 45, "phd", "44", "desert",
   {"A": "1 2M 1 7m", "B": "6M 7m 1 2M"},
   {"A": "1:2 2:2 3:2 4:2 5:4 4:2 3:2 | 2:4 1:4 2:8 | 3:2 4:2 5:2 6:2 5:4 4:2 3:2 | 2:2 1:2 7,:4 1:8",
    "B": "5:4 6:2 5:2 4:4 3:4 | 2:8 1:8 | 6:4 5:2 4:2 3:4 2:4 | 1:16"}, groove="desert", c_drums=True, desc="Dunes, darbukas and artillery.")
_S("frostbite_front", "FROSTBITE FRONT", "battle", 112, 44, "min", "44", "epic",
   {"A": "1m 6M 3M 7M", "B": "4m 5m 6M 7M"},
   {"A": "5:4 5:2 6:2 5:4 4:4 | 3:8 2:8 | 1:4 1:2 2:2 3:4 5:4 | 4:16",
    "B": "6:4 5:4 4:4 3:4 | 2:8 3:8 | 4:4 5:4 6:4 7:4 | 1':16"}, harm_i="celesta", desc="Ice fields, breath like smoke, guns like thunder.")
_S("magma_pressure", "MAGMA PRESSURE", "battle", 148, 38, "phr", "44", "metal",
   {"A": "1p 2p 1p 7p", "B": "6p 7p 1p 2p"},
   {"A": "1:2 2:2 1:2 3:2 1:2 4:2 3:2 2:2 | 1:16 | 5:2 4:2 3:2 2:2 3:2 2:2 1:2 7,:2 | 1:16",
    "B": "6:4 5:4 4:4 3:4 | 2:8 1:8 | 6:2 7:2 1':4 7:2 6:2 5:4 | 2:16"}, desc="The ground is melting under your treads.")
_S("tidebreaker", "TIDEBREAKER", "battle", 172, 41, "dor", "44", "dnb",
   {"A": "1m 4M 1m 3M", "B": "6d 7M 1m 1m"},
   {"A": "5:6 4:2 3:4 1:4 | 2:8 r:8 | 5:6 6:2 7:4 1':4 | 6:16",
    "B": "3':4 2':4 1':4 7:4 | 6:16 | 4:4 5:4 6:4 4:4 | 5:16"}, desc="Waves breaking on steel at 172 BPM.")
_S("orbital_barrage", "ORBITAL BARRAGE", "battle", 128, 46, "lyd", "44", "synthwave",
   {"A": "1 2 7m 5", "B": "4# 2 1 1"},
   {"A": "1':4 7:2 5:2 4:4 5:4 | 3:4 2:4 1:8 | 1':4 2':2 3':2 4':4 3':4 | 2':16",
    "B": "5:4 6:4 7:4 1':4 | 2':8 1':8 | 7:4 6:4 5:4 4:4 | 5:16"}, desc="Artillery above the atmosphere.")
_S("scrapyard_riot", "SCRAPYARD RIOT", "battle", 118, 41, "min", "44", "industrial",
   {"A": "1p 1p 6p 7p", "B": "4p 4p 6p 5p"},
   {"A": "1:2 r:2 1:2 3:2 r:2 4:2 3:4 | r:16 | 1:2 r:2 1:2 3:2 5:2 4:2 3:2 1:2 | r:16",
    "B": "6:4 5:4 4:4 3:4 | 1:16 | 6:4 7:4 1':4 7:4 | 5:16"}, desc="Rust, rivets and riot.")
_S("eye_of_the_storm", "EYE OF THE STORM", "battle", 144, 43, "min", "78", "balkan",
   {"A": "1m 7M 6M 5m", "B": "4m 7M 3M 5M"},
   {"A": "1:2 2:2 3:2 4:2 5:6 | 4:2 3:2 2:2 1:2 7,:6 | 1:2 3:2 5:2 1':2 7:6 | 6:2 5:2 4:2 3:2 2:6",
    "B": "5:4 6:4 7:6 | 1':4 7:4 6:6 | 5:2 4:2 3:2 2:2 1:6 | 7,:14"}, lead="saw", desc="Seven-eight thunder: lightning on the off-beat.")
_S("jungle_drums", "JUNGLE DRUMS", "battle", 116, 45, "mpent", "44", "eastern",
   {"A": "1 3 4 1", "B": "4 5 3 1"},
   {"A": "1:2 1:2 3:2 4:2 5:4 4:4 | 3:4 1:4 2:8 | 1:2 3:2 4:2 5:2 1':4 5:4 | 4:8 3:8",
    "B": "5:4 4:4 3:4 1:4 | 5,:16 | 1:4 3:4 4:4 5:4 | 1:16"}, harm_i="marimba", lead="reed", desc="Something is moving in the green.")
_S("graveyard_shift", "GRAVEYARD SHIFT", "battle", 100, 40, "hung", "44", "gothic",
   {"A": "1m 4# 5M 1m", "B": "6M 2d 5M 5M"},
   {"A": "1:4 3:4 4:4 5:4 | 6:8 5:8 | 4:4 3:4 2:4 7,:4 | 1:16",
    "B": "5:4 6:4 7:8 | 1':8 7:8 | 6:4 5:4 4:4 3:4 | 2:16"}, desc="Midnight, mausoleums and mortars.")
_S("cartridge_war", "CARTRIDGE WAR", "battle", 150, 48, "maj", "44", "chip",
   {"A": "1 6m 4 5", "B": "4 5 3m 6m"},
   {"A": "5:2 5:2 6:2 5:2 3:4 1:4 | 2:2 3:2 4:2 5:2 3:8 | 5:2 5:2 6:2 5:2 1':4 7:4 | 6:4 5:4 4:8",
    "B": "4:2 4:2 5:2 6:2 4:4 6:4 | 5:16 | 3:2 4:2 5:2 6:2 7:4 5:4 | 1':16"}, desc="Eight bits of pure artillery.")
_S("lantern_terraces", "LANTERN TERRACES", "battle", 128, 48, "pent", "44", "eastern",
   {"A": "1 4 3 1", "B": "4 3 2 1"},
   {"A": "1':2 5:2 3:2 5:2 1':4 2':4 | 3':8 2':8 | 1':2 2':2 3':2 5':2 3':4 2':4 | 1':16",
    "B": "5:4 3:4 2:4 1:4 | 2:8 3:8 | 5:4 1':4 5:4 3:4 | 2:16"}, groove="boom", kit="tribal", desc="Fighting up the temple steps.")
_S("worldtree_roots", "WORLDTREE ROOTS", "battle", 120, 43, "dor", "68", "jig",
   {"A": "1m 7M 4M 1m", "B": "3M 4M 5m 1m"},
   {"A": "1:4 3:2 5:4 4:2 | 3:4 2:2 1:6 | 5:4 6:2 7:4 1':2 | 7:6 5:6",
    "B": "1':6 7:2 6:2 5:2 | 4:6 3:6 | 2:2 3:2 4:2 5:2 6:2 7:2 | 1':12"}, lead="reed", desc="Roots older than any war.")
_S("whalefall", "WHALEFALL", "battle", 92, 41, "min", "44", "cosmic",
   {"A": "1m 6M 4m 5m", "B": "6M 7M 1m 1m"},
   {"A": "5:8 6:4 5:4 | 3:8 2:8 | 1:8 3:4 5:4 | 4:16",
    "B": "6:8 7:4 1':4 | 7:8 5:8 | 4:8 3:4 2:4 | 1:16"}, groove="half", kit="808", c_drums=True, desc="A battle among bleached bones.")
_S("shatterline_battle", "PRISM BREAK", "battle", 140, 49, "lyd", "44", "glitch",
   {"A": "1 2 7m 1", "B": "6m 2 4# 5"},
   {"A": "1:1 3:1 5:2 1':2 5:2 4:4 3:4 | 2:2 3:2 5:2 2:2 1:8 | 1:1 3:1 5:2 1':2 2':2 3':4 2':4 | 1':16",
    "B": "6:2 4:2 2:2 4:2 6:4 5:4 | 3:16 | 6:2 7:2 1':2 2':2 3':4 4':4 | 5':16"}, desc="Every shell refracts.")
_S("glass_dunes_battle", "FUSED SAND", "battle", 132, 47, "phd", "44", "metal2",
   {"A": "1p 2p 1p 7p", "B": "6p 7p 1p 2p"},
   {"A": "1:2 2:2 3:4 2:2 1:2 7,:4 | 1:16 | 3:2 4:2 5:4 4:2 3:2 2:4 | 1:16",
    "B": "5:4 6:4 5:4 4:4 | 3:8 2:8 | 1:4 2:4 3:4 2:4 | 1:16"}, lead="erhu", desc="Desert metal under twin suns.")
# ---------------------------------------------------------------- tournament bosses (one theme each)
_S("boss_stinger", "STINGER", "boss", 164, 47, "phr", "44", "chip",
   {"A": "1m 2M 1m 2M", "B": "6M 7m 1m 1m"},
   {"A": "1:1 2:1 1:1 2:1 1:4 5:2 4:2 3:2 2:2 | 1:1 2:1 1:1 2:1 1:4 7,:8 | 3:1 4:1 3:1 4:1 3:4 6:2 5:2 4:2 3:2 | 2:16",
    "B": "6:2 5:2 4:2 3:2 2:4 1:4 | 2:16 | 6:2 7:2 1':2 2':2 1':4 7:4 | 1':16"}, desc="Level 1. A buzz you hear before you see it.")
_S("boss_warden", "THE WARDEN", "boss", 108, 41, "min", "44", "march",
   {"A": "1m 6M 7M 1m", "B": "4m 5M 1m 1m"},
   {"A": "1:4 1:2 1:2 5:8 | 4:4 3:4 2:8 | 1:4 1:2 1:2 6:8 | 5:16",
    "B": "4:4 5:4 6:8 | 5:4 4:4 3:8 | 2:4 3:4 4:4 7,:4 | 1:16"}, desc="Level 2. Locked gates and a heavy key.")
_S("boss_specter", "SPECTER", "boss", 118, 44, "hmin", "34", "horror",
   {"A": "1m 6M 4m 5M", "B": "2d 5M 1m 1m"},
   {"A": "5:4 6:4 5:4 | 4:4 3:4 2:4 | 3:4 2:4 1:4 | 7,:12",
    "B": "1':4 7:4 6:4 | 5:12 | 4:4 3:4 2:4 | 1:12"}, groove="waltz2", lead2="choir_o", desc="Level 3. You can only see it when it fires.")
_S("boss_colossus", "COLOSSUS", "boss", 86, 36, "phr", "44", "metal",
   {"A": "1p 1p 2p 1p", "B": "6p 6p 7p 1p"},
   {"A": "1:8 2:4 1:4 | 7,:8 1:8 | 3:8 2:4 3:4 | 4:16",
    "B": "6:8 5:4 4:4 | 3:16 | 2:8 1:4 2:4 | 1:16"}, groove="half", desc="Level 4. The ground shakes when it breathes.")
_S("boss_sentinel", "SENTINEL", "boss", 128, 45, "dor", "44", "techno",
   {"A": "1m 1m 7M 4M", "B": "6d 7M 1m 1m"},
   {"A": "1:2 r:2 1:2 r:2 5:2 r:2 4:2 3:2 | 1:2 r:2 1:2 r:2 7,:4 1:4 | 3:2 r:2 3:2 r:2 6:2 r:2 5:2 4:2 | 3:16",
    "B": "5:4 4:4 3:4 2:4 | 1:16 | 7:4 6:4 5:4 4:4 | 5:16"}, desc="Level 5. Precision. Glass. Zero error.")
_S("boss_glacier", "GLACIER", "boss", 100, 44, "min", "34", "epic",
   {"A": "1m 6M 7M 3M", "B": "4m 5m 6M 5M"},
   {"A": "1:6 2:2 3:4 | 5:8 4:4 | 3:4 2:4 1:4 | 7,:12",
    "B": "6:6 5:2 4:4 | 3:8 2:4 | 1:4 2:4 3:4 | 2:12"}, groove="waltz2", harm_i="celesta", lead2="choir", desc="Level 6. A moving wall of ice.")
_S("boss_helios", "HELIOS", "boss", 132, 48, "lyd", "44", "synthwave",
   {"A": "1 2 1 2", "B": "6m 5 4# 2"},
   {"A": "1:4 3:4 5:4 4:4 | 5:8 2':8 | 1':4 7:4 5:4 3:4 | 2:16",
    "B": "6:4 7:4 1':4 2':4 | 3':16 | 2':4 1':4 7:4 6:4 | 5:16"}, desc="Level 7. Staring into a nova.")
_S("boss_rattler", "RATTLER", "boss", 138, 45, "phd", "44", "western",
   {"A": "1 1 7m 1", "B": "4m 2M 1 1"},
   {"A": "5:2 5:2 6:2 5:2 4:2 3:2 2:4 | 1:8 r:8 | 5:2 5:2 6:2 5:2 7b:4 6:4 | 5:16",
    "B": "1':4 7b:4 6:4 5:4 | 4:8 3:8 | 2:4 3:2 2:2 1:4 7,:4 | 1:16"}, desc="Level 8. One shot. Make it count.")
_S("boss_miasma", "MIASMA", "boss", 96, 40, "loc", "44", "industrial",
   {"A": "1d 2M 1d 5M", "B": "6M 2M 5M 1d"},
   {"A": "1:4 2:4 1:4 7,:4 | 1:8 r:8 | 3:4 4:4 3:4 2:4 | 5,:16",
    "B": "5:8 4:4 3:4 | 2:16 | 3:4 2:4 1:4 7,:4 | 1:16"}, groove="half", lead="theremin", desc="Level 9. Don't breathe in.")
_S("boss_bastion", "BASTION", "boss", 112, 43, "min", "44", "epic",
   {"A": "1m 4m 6M 5M", "B": "6M 7M 1m 5M"},
   {"A": "1:4 5:4 5:4 6:2 5:2 | 4:4 3:4 2:8 | 3:4 6:4 6:4 7:2 6:2 | 5:16",
    "B": "1':4 7:4 6:4 5:4 | 4:4 5:4 6:8 | 5:4 4:4 3:4 2:4 | 1:16"}, desc="Level 10. Walls that answer fire with fire.")
_S("boss_zephyr", "ZEPHYR", "boss", 160, 47, "dor", "78", "balkan",
   {"A": "1m 4M 1m 7M", "B": "3M 4M 5m 1m"},
   {"A": "5:2 6:2 5:2 4:2 3:6 | 4:2 5:2 4:2 3:2 2:6 | 3:2 4:2 5:2 7:2 1':6 | 7:2 6:2 5:2 4:2 5:6",
    "B": "1':4 7:4 6:6 | 5:4 4:4 3:6 | 2:2 3:2 4:2 5:2 6:6 | 5:14"}, lead="flute", desc="Level 11. A gale in seven-eight.")
_S("boss_geode", "GEODE", "boss", 120, 47, "lyd", "54", "glitch",
   {"A": "1 2 6m 7m", "B": "4# 5 1 1"},
   {"A": "1:2 5:2 1':2 2':2 3':4 2':2 1':2 5:4 | 4:4 5:4 3:6 2:6",
    "B": "6:2 7:2 1':2 2':2 3':6 2':6 | 1':20"}, lead="celesta", desc="Level 12. Crystal faces, every one a mirror.")
_S("boss_mirage", "MIRAGE", "boss", 92, 46, "phd", "44", "dub",
   {"A": "1 2M 1 1", "B": "4m 2M 7m 1"},
   {"A": "5:6 4:2 3:8 | r:16 | 3:6 2:2 1:8 | r:16",
    "B": "1':6 7:2 6:8 | 5:16 | 4:6 3:2 2:8 | 1:16"}, desc="Level 13. Is that it, or its echo?")
_S("boss_revenant", "REVENANT", "boss", 92, 40, "hmin", "34", "gothic",
   {"A": "1m 4m 5M 1m", "B": "6M 4m 2d 5M"},
   {"A": "1:4 3:4 5:4 | 1':8 7:4 | 6:4 5:4 4:4 | 3:12",
    "B": "5:4 6:4 7:4 | 1':12 | 7:4 6:4 5:4 | 7,:12"}, desc="Level 14. One strike is all it needs.")
_S("boss_corsair", "CORSAIR", "boss", 140, 45, "min", "68", "jig",
   {"A": "1m 7M 1m 5m", "B": "6M 7M 1m 5M"},
   {"A": "1:2 2:2 3:2 5:4 3:2 | 4:2 3:2 2:2 1:6 | 7,:2 1:2 2:2 4:4 2:2 | 3:2 2:2 7,:2 1:6",
    "B": "5:4 6:2 7:4 5:2 | 1':6 7:6 | 6:2 5:2 4:2 3:2 2:2 3:2 | 1:12"}, lead="reed", groove="jig2", desc="Level 15. Cannons, rum and a long sea shanty.")
_S("boss_tyrant", "TYRANT", "boss", 156, 38, "min", "44", "metal",
   {"A": "1p 6p 4p 5p", "B": "6p 7p 1p 1p"},
   {"A": "1:2 1:2 1:2 2:2 3:4 1:4 | 4:2 3:2 2:2 1:2 7,:8 | 1:2 1:2 1:2 2:2 3:4 5:4 | 6:4 5:4 4:8",
    "B": "1':4 7:4 6:4 5:4 | 6:8 7:8 | 1':2 2':2 1':4 7:4 6:4 | 5:16"}, desc="Level 16. Wrath with a crown on.")
_S("boss_archon", "ARCHON", "boss", 104, 46, "mix", "44", "epic",
   {"A": "1 7M 4 1", "B": "6m 7M 1 1"},
   {"A": "1:8 5:8 | 7b:4 6:4 5:8 | 1':8 7b:4 6:4 | 5:16",
    "B": "4:4 5:4 6:4 7b:4 | 1':16 | 2':8 1':4 7b:4 | 1':16"}, lead="choir", lead2="brass", desc="Level 17. The zenith answers in a choir.")
_S("boss_obsidian", "OBSIDIAN", "boss", 124, 38, "loc", "44", "industrial",
   {"A": "1p 2p 1p 5p", "B": "6p 2p 5p 1p"},
   {"A": "1:2 1:2 2:2 1:2 5:4 4:4 | 3:2 2:2 1:4 2:8 | 1:2 1:2 2:2 1:2 6:4 5:4 | 4:16",
    "B": "5:4 6:4 5:4 3:4 | 2:16 | 1:4 2:4 3:4 5:4 | 1:16"}, groove="indus", lead2="choir", desc="Level 18. The forge, and the thing it made.")
_S("boss_tempest", "TEMPEST", "boss", 174, 42, "min", "44", "dnb",
   {"A": "1m 6M 3M 7M", "B": "4m 6M 5m 5m"},
   {"A": "5:4 6:2 7:2 1':4 7:4 | 6:4 5:4 3:8 | 5:4 6:2 7:2 2':4 1':4 | 7:16",
    "B": "3':4 2':4 1':4 7:4 | 6:16 | 5:4 4:4 3:4 2:4 | 1:16"}, lead="supersaw", desc="Level 19. The spire calls the lightning.")
_S("boss_master", "THE MASTER", "boss", 116, 40, "hmin", "44", "metal2",
   {"A": "1m 6M 4m 5M", "B": "6M 7d 1m 5M"},
   {"A": "1:4 5:4 1':8 | 7:4 6:2 5:2 4:4 3:4 | 2:4 5:4 2':8 | 1':4 7:2 6:2 5:8",
    "B": "6:4 7:4 1':4 2':4 | 3':8 2':4 1':4 | 7:4 6:4 5:4 4:4 | 5:4 7,:4 1:8"},
   form="I A B A2 C D X X O", lead2="choir", counter="brass", desc="Level 20. Everything you learned, aimed back at you.")
# ---------------------------------------------------------------- missions
_S("saucer_attack", "SAUCER ATTACK", "boss", 130, 46, "wt", "44", "techno",
   {"A": "1 2 3 2", "B": "4 5 4 1"},
   {"A": "1':2 r:2 5:2 r:2 3:2 4:2 5:4 | 6:4 5:4 r:8 | 1':2 r:2 6:2 r:2 4:2 5:2 6:4 | 2':16",
    "B": "3:4 4:4 5:4 6:4 | 1':16 | 6:4 5:4 4:4 3:4 | 2:16"}, lead="theremin", desc="They hop. They shield. They fire in threes.")
_S("mothership", "THE MOTHERSHIP", "boss", 98, 38, "loc", "44", "epic",
   {"A": "1d 2M 1d 7m", "B": "6M 7m 2M 1d"},
   {"A": "1:8 2:4 1:4 | 5:8 4:8 | 1:8 2:4 3:4 | 2:16",
    "B": "6:4 5:4 4:4 3:4 | 2:8 1:8 | 7,:8 1:4 2:4 | 1:16"}, lead="choir", lead2="theremin", counter="brass", groove="boom2",
   form="I A B A2 C D X X O", desc="The flagship. Its shadow covers the whole map.")
_S("boss_rush", "BOSS RUSH", "boss", 176, 45, "min", "44", "hyper",
   {"A": "1m 6M 3M 7M", "B": "4m 5m 6M 7M"},
   {"A": "1:2 3:2 5:2 1':2 7:2 5:2 3:2 5:2 | 6:4 5:4 3:8 | 1:2 3:2 5:2 1':2 2':4 3':4 | 2':16",
    "B": "4:2 6:2 1':2 6:2 4:2 6:2 1':4 | 7:16 | 5:2 7:2 2':2 7:2 5:2 7:2 2':4 | 1':16"}, form="I A A2 B D X X O",
   desc="Every boss. One round each. No healing.")
_S("squad_up", "SQUAD UP", "battle", 122, 45, "dor", "44", "funk",
   {"A": "1m7 4M 1m7 4M", "B": "7M 1m 4M 5m"},
   {"A": "1:2 3:2 4:2 5:2 r:4 4:2 3:2 | 1:4 r:4 7,:4 1:4 | 1:2 3:2 4:2 5:2 r:4 7:2 6:2 | 5:16",
    "B": "4:4 3:4 1:8 | 7,:4 1:4 3:4 4:4 | 5:4 4:4 3:4 1:4 | 1:16"}, desc="Co-op and 2 vs 1: back to back.")
# ---------------------------------------------------------------- terminal tickets (the ten Ancient Hoarders)
_S("t_volt", "VOLT SOVEREIGN", "boss", 136, 47, "dor", "44", "techno",
   {"A": "1m 7M 4M 5m", "B": "3M 4M 1m 1m"},
   {"A": "1:1 1:1 5:2 1:1 1:1 6:2 5:2 4:2 3:4 | 2:2 3:2 5:4 3:8 | 1:1 1:1 5:2 1:1 1:1 7:2 6:2 5:2 4:4 | 5:16",
    "B": "3':4 2':4 1':4 7:4 | 1':16 | 6:4 5:4 4:4 3:4 | 1:16"}, lead="saw", desc="Ticket boss. A skyline that is one big capacitor.")
_S("t_magistrate", "IRON MAGISTRATE", "boss", 118, 43, "hmin", "44", "clock",
   {"A": "1m 4m 5M 1m", "B": "6M 2d 5M 1m"},
   {"A": "1:2 3:2 5:2 3:2 1':4 7:4 | 6:2 5:2 4:2 3:2 2:4 1:4 | 7,:2 2:2 4:2 2:2 7:4 6:4 | 5:16",
    "B": "1':4 1':2 7:2 6:4 5:4 | 4:4 3:4 2:8 | 3:2 4:2 5:2 6:2 7:4 2':4 | 1':16"}, desc="Ticket boss. ORDER. ORDER IN THE CLOCKWORK COURT.")
_S("t_regent", "GLACIER REGENT", "boss", 88, 44, "min", "34", "gothic",
   {"A": "1m 6M 3M 7M", "B": "4m 5m 1m 1m"},
   {"A": "5:8 4:4 | 3:4 2:4 1:4 | 2:8 3:4 | 5,:12",
    "B": "1':8 7:4 | 6:4 5:4 4:4 | 5:8 2:4 | 1:12"}, harm_i="celesta", lead="choir", desc="Ticket boss. A cathedral carved from one frozen breath.")
_S("t_solar", "SOLAR ARCHON", "boss", 120, 48, "lyd", "44", "fanfare",
   {"A": "1 2 1 5", "B": "6m 2 4# 5"},
   {"A": "1:4 5:4 1':8 | 7:4 4:4 5:8 | 3:4 5:4 2':8 | 1':16",
    "B": "6:4 7:4 1':4 2':4 | 3':8 2':8 | 1':4 7:4 6:4 4:4 | 5:16"}, desc="Ticket boss. The temple at the centre of the sun.")
_S("t_abyssal", "ABYSS LEVIATHAN", "boss", 84, 36, "phr", "44", "dub",
   {"A": "1m 2M 1m 7m", "B": "6M 7m 1m 2M"},
   {"A": "1:8 r:4 2:4 | 1:16 | 5,:8 r:4 7,:4 | 1:16",
    "B": "5:8 4:8 | 3:8 2:8 | 1:8 2:4 3:4 | 2:16"}, lead="choir_o", groove="half", desc="Ticket boss. The city sank. Something stayed.")
_S("t_pharaoh", "SAND PHARAOH", "boss", 112, 45, "phd", "44", "desert",
   {"A": "1 2M 1 7m", "B": "4m 3M 2M 1"},
   {"A": "1:2 2:2 3:4 4:2 3:2 2:4 | 1:4 2:2 3:2 4:8 | 5:2 6:2 5:2 4:2 3:4 2:4 | 1:16",
    "B": "1':4 7:4 6:4 5:4 | 4:2 5:2 4:2 3:2 2:8 | 3:2 2:2 1:4 7,:4 2:4 | 1:16"}, lead="reed", c_drums=True, desc="Ticket boss. A king who never stopped counting.")
_S("t_baron", "TOXIC BARON", "boss", 130, 41, "loc", "44", "techno",
   {"A": "1d 1d 2M 1d", "B": "5M 6M 2M 1d"},
   {"A": "1:2 1:2 2:2 1:2 r:4 5,:4 | 1:2 1:2 2:2 3:2 2:8 | 1:2 1:2 2:2 1:2 r:4 7,:4 | 1:16",
    "B": "5:4 4:4 3:4 2:4 | 1:16 | 6:4 5:4 4:4 3:4 | 2:16"}, lead="acid", desc="Ticket boss. Bubbling, glowing, profitable.")
_S("t_shadow", "SHADOW EMPEROR", "boss", 104, 40, "hung", "44", "metal2",
   {"A": "1m 4# 5M 1m", "B": "6M 4# 2d 5M"},
   {"A": "1:4 2:4 3:4 4:4 | 5:8 4:8 | 3:4 2:4 1:4 7,:4 | 1:16",
    "B": "6:4 5:4 4:4 3:4 | 2:8 3:8 | 4:4 5:4 6:4 7:4 | 1':16"}, lead="organ", lead2="choir", desc="Ticket boss. The keep has no windows.")
_S("t_overseer", "COSMIC OVERSEER", "boss", 110, 46, "wt", "54", "cosmic",
   {"A": "1 2 3 4", "B": "5 4 2 1"},
   {"A": "1':4 6:2 5:4 4:2 3:4 2:4 | 1:6 2:4 3:6 4:4",
    "B": "5:6 6:4 5:6 4:4 | 3:20"}, groove="five", kit="glitch", desc="Ticket boss. The eye on the throne never blinks.")
_S("t_warlord", "DRAGON WARLORD", "boss", 126, 44, "insen", "44", "eastern",
   {"A": "1 2 1 4", "B": "5 4 2 1"},
   {"A": "1:2 2:2 4:4 5:4 4:2 2:2 | 1:4 5,:4 1:8 | 4:2 5:2 1':4 2':4 1':2 5:2 | 4:16",
    "B": "1':4 5:4 4:4 2:4 | 1:16 | 2:4 4:4 5:4 1':4 | 1':16"}, lead="erhu", groove="boom", desc="Ticket boss. Fire on the pagoda peak.")
# ---------------------------------------------------------------- the Martyr (each phase and the conversations)
_S("martyr_ember", "THE MARTYR I: EMBER SANCTUM", "boss", 120, 40, "hmin", "44", "epic",
   {"A": "1m 6M 4m 5M", "B": "6M 3M 4m 5M"},
   {"A": "1:4 3:4 5:4 1':4 | 7:8 5:8 | 6:4 5:4 4:4 3:4 | 2:8 7,:8",
    "B": "3':6 2':2 1':8 | 7:4 6:4 5:8 | 4:4 5:4 6:4 7:4 | 1':16"},
   form="I A B A2 C D X X O", lead2="choir", counter="brass", groove="boom2", desc="Phase I. Fire and stone.")
_S("martyr_tempest", "THE MARTYR II: TEMPEST SPIRES", "boss", 168, 42, "dor", "78", "balkan",
   {"A": "1m 7M 4M 1m", "B": "3M 4M 5m 7M"},
   {"A": "5:2 4:2 3:2 2:2 1:6 | 7,:2 1:2 2:2 3:2 5:6 | 4:2 5:2 6:2 7:2 1':6 | 7:2 6:2 5:2 4:2 5:6",
    "B": "1':4 2':4 3':6 | 2':4 1':4 7:6 | 6:2 7:2 1':2 2':2 3':6 | 2':14"},
   form="I A B A2 C D X X O", lead="supersaw", lead2="choir", counter="strings", desc="Phase II. Wind and water.")
_S("martyr_astral", "THE MARTYR III: ASTRAL RIFT", "boss", 140, 45, "lyd", "44", "metal2",
   {"A": "1 2 7m 5", "B": "6m 2 4# 5"},
   {"A": "1':4 7:2 5:2 4:4 5:4 | 1':4 2':4 3':8 | 2':4 1':2 7:2 6:4 5:4 | 4:8 5:8",
    "B": "3':4 4':4 5':8 | 4':4 3':4 2':8 | 1':4 2':4 3':4 4':4 | 5':16"},
   form="I A B A2 C D X X O", lead2="choir", counter="choir_o", desc="Phase III. Beyond ordinary time.")

# ---------------------------------------------------------------- premium II: ten home screens and ten battlefields
_S("h_biolume", "BIOLUME TRENCH", "menu", 72, 45, "lyd", "44", "ambient",
   {"A": "1 2 1 2", "B": "6 3 2 5"},
   {"A": "3:4 5:4 7:6 6:2 | 5:8 2':8 | 1':4 7:4 6:4 7:4 | 5:16",
    "B": "6:6 5:2 3:8 | 2:4 3:4 2:8 | 3:4 5:4 6:4 1':4 | 7:12 r:4",
    "C": "1':8 2':8 | 3':16 | 2':8 7:8 | 5:16"},
   form="I A B C A2 O", lead="vibes", lead2="celesta", counter="glasspad", pad="glasspad", bass_i="sub",
   desc="Jellyfish lanterns drifting up through the dark.")
_S("h_spiritshrine", "SPIRIT SHRINE", "menu", 104, 47, "insen", "44", "eastern",
   {"A": "1m 2M 3m 1m", "B": "5M 3m 2M 1m"},
   {"A": "1:2 2:2 3:4 4:4 5:4 | 4:6 3:2 2:8 | 3:2 4:2 5:4 1':4 5:4 | 4:4 3:4 1:8",
    "B": "1':6 2':2 1':4 5:4 | 4:8 3:4 4:4 | 5:4 4:4 2:4 3:4 | 1:12 r:4"},
   lead="koto", lead2="flute", counter="erhu", pad="warmpad", harm_i="koto", desc="Torii gates, moonlight and drifting foxfire.")
_S("h_holocity", "HOLO CITY NIGHTS", "menu", 124, 42, "min", "44", "techno",
   {"A": "1m 6M 3M 7M", "B": "4m 6M 7M 7M"},
   {"A": "1:2 1:2 3:2 5:4 4:2 3:4 | 5:2 5:2 6:2 7:4 6:2 5:4 | 3':4 2':2 1':2 7:4 5:4 | 1':12 r:4",
    "B": "4:4 6:4 1':4 4':4 | 3':6 2':2 1':8 | 7:4 1':4 2':4 5:4 | 7:16"},
   lead="supersaw", lead2="square", counter="glasspad", desc="Rain, neon and a hundred holograms.")
_S("h_tesseract", "THE TESSERACT", "menu", 92, 44, "lyd", "54", "cosmic",
   {"A": "1 2 7 1", "B": "6 5 2 2"},
   {"A": "1:6 5:4 2':6 1':4 | 7:6 5:4 3:6 2:4 | 3:6 6:4 2':6 3':4 | 2':20",
    "B": "6:6 5:4 3:6 5:4 | 2':10 1':10 | 7:6 1':4 2':6 5:4 | 3:20"},
   lead="theremin", lead2="glasspad", counter="celesta", pad="glasspad", desc="Five beats to the bar, four dimensions to the cube.")
_S("h_kaijubay", "KAIJU BAY", "menu", 100, 40, "hmin", "44", "industrial",
   {"A": "1 6 7 1", "B": "4 1 6 5"},
   {"A": "1:8 r:2 1:2 2:2 3:2 | 5:8 4:4 3:4 | 6:6 5:2 4:4 3:4 | 2:4 7,:4 1:8",
    "B": "3:4 4:4 5:4 6:4 | 1':12 7:4 | 6:4 5:4 4:4 3:4 | 2:8 5,:8"},
   lead="brass", lead2="choir", counter="horn", pad="choir", desc="Searchlights, sirens and something enormous wading in.")
_S("h_shroomgrove", "GLOWSHROOM GROVE", "menu", 76, 43, "dor", "44", "dub",
   {"A": "1m 4M 1m 4M", "B": "7M 4M 3M 5m"},
   {"A": "5:2 r:2 5:2 3:2 4:4 5:4 | 6:2 r:2 6:2 4:2 5:8 | 5:2 r:2 5:2 3:2 4:2 5:2 6:2 1':2 | 7:4 6:4 5:8",
    "B": "1':4 7:2 6:2 5:4 4:4 | 3:8 4:8 | 5:4 6:2 7:2 1':4 2':4 | 1':16"},
   lead="marimba", lead2="vibes", counter="flute", pad="warmpad", swing=0.12, desc="Spores rising like slow snow in reverse.")
_S("h_wormsea", "THE DEEP DESERT", "menu", 96, 45, "phd", "44", "desert",
   {"A": "1 2 1 2", "B": "4m 2M 6M 1M"},
   {"A": "1:2 2:2 3:4 2:2 1:2 7,:4 | 1:12 r:4 | 3:2 4:2 5:4 6:2 5:2 4:4 | 3:4 2:4 1:8",
    "B": "5:4 6:4 5:2 4:2 3:4 | 4:8 2:8 | 3:4 4:2 5:2 6:4 1':4 | 7:4 6:4 5:8"},
   lead="erhu", lead2="sitar", counter="reed", pad="warmpad", desc="Three moons, and the sand breathing underneath.")
_S("h_jadetemple", "JADE TEMPLE", "menu", 112, 48, "mix", "44", "eastern",
   {"A": "1 7 4 1", "B": "6m 7 1 5m"},
   {"A": "1:4 3:2 5:2 6:4 5:4 | 4:2 3:2 2:4 1:8 | 1:4 3:2 5:2 7:4 6:2 5:2 | 6:4 7:4 1':8",
    "B": "3':4 2':4 1':2 7:2 6:4 | 5:8 3:8 | 4:4 5:4 6:2 5:2 4:4 | 5:16"},
   lead="flute", lead2="marimba", counter="reed", harm_i="marimba", desc="A feathered serpent turning round the pyramid.")
_S("h_orrery", "THE ORRERY", "menu", 108, 50, "maj", "44", "clock",
   {"A": "1 6 2 5", "B": "4 5 3 6"},
   {"A": "1:2 3:2 5:2 1':2 7:2 5:2 3:2 5:2 | 6:2 1':2 3':2 1':2 6:4 r:4 | 2:2 4:2 6:2 2':2 1':2 7:2 6:2 4:2 | 5:8 7,:4 r:4",
    "B": "4':4 3':4 2':4 1':4 | 7:4 1':4 2':8 | 3':4 2':2 1':2 7:4 6:4 | 5:12 r:4"},
   lead="harpsi", lead2="celesta", counter="music_box", pad="strings", desc="Brass rings turning the stars like clockwork.")
_S("h_ghostarmada", "GHOST ARMADA", "menu", 96, 43, "dor", "68", "jig",
   {"A": "1 7 1 5", "B": "3 7 4 1"},
   {"A": "1:2 1:2 1:2 3:4 5:2 | 4:4 2:2 7,:4 5,:2 | 1:2 1:2 1:2 3:4 5:2 | 4:4 2:2 1:6",
    "B": "5:4 6:2 7:4 1':2 | 7:4 5:2 4:6 | 3:2 4:2 5:2 6:4 4:2 | 5:12"},
   lead="reed", lead2="choir_o", counter="erhu", pad="choir", desc="A shanty for a crew that is no longer alive.")
_S("m_mariana", "MARIANA DEEP", "battle", 172, 43, "min", "44", "dnb",
   {"A": "1 6 7 1", "B": "4 6 3 7"},
   {"A": "5:6 4:2 3:4 1:4 | 2:6 3:2 4:8 | 5:4 6:4 7:4 1':4 | 7:8 5:8",
    "B": "1':6 7:2 6:4 5:4 | 4:8 3:4 4:4 | 5:6 6:2 7:8 | 1':16"},
   lead="hollow", lead2="vibes", counter="glasspad", desc="Battlefield theme. Pressure, dark and drifting light.")
_S("m_torii", "TORII PATH", "battle", 128, 45, "hmin", "44", "eastern",
   {"A": "1 6 4 5", "B": "6 b7M 1 5"},
   {"A": "1:4 2:2 3:2 5:4 3:4 | 2:2 3:2 2:2 1:2 7,:8 | 1:4 3:2 4:2 5:4 6:4 | 5:12 r:4",
    "B": "1':4 7:4 6:2 5:2 6:4 | 5:6 4:2 3:8 | 4:4 5:2 6:2 7:4 6:4 | 5:16"},
   lead="erhu", lead2="koto", counter="flute", desc="Battlefield theme. Taiko on the temple stair.")
_S("m_gridlock", "NEON GRIDLOCK", "battle", 140, 41, "min", "44", "trap",
   {"A": "1 6 3 7", "B": "6 7 1 1"},
   {"A": "1':2 r:2 1':2 7:2 5:4 3:4 | 4:2 r:2 4:2 3:2 1:8 | 1':2 r:2 1':2 2':2 3':4 2':4 | 7:16",
    "B": "5:2 5:2 6:4 7:4 1':4 | 6:8 5:8 | 3:2 3:2 4:4 5:4 7:4 | 1':16"},
   lead="bell", lead2="supersaw", counter="choir_o", desc="Battlefield theme. Rooftops, rain and 808s.")
_S("m_paradox", "PARADOX ENGINE", "battle", 140, 44, "dor", "78", "glitch",
   {"A": "1 7 6 7", "B": "4 5 1 1"},
   {"A": "1:2 3:2 5:4 2':6 | 1':4 7:4 5:6 | 3:2 5:2 7:4 2':6 | 1':14",
    "B": "6:4 5:4 4:2 3:4 | 2:4 4:4 7,:6 | 1:2 2:2 3:4 5:6 | 4:6 3:8"},
   lead="square", lead2="hollow", counter="theremin", desc="Battlefield theme. Seven beats, folded in on themselves.")
_S("m_kaiju", "KAIJU BAY: LANDFALL", "battle", 136, 40, "hmin", "44", "metal2",
   {"A": "1 6 4 5", "B": "1 3 6 5"},
   {"A": "1:2 1:2 1:2 5:2 4:4 3:4 | 2:2 2:2 2:2 6:2 5:4 4:4 | 3:4 5:4 1':4 7:4 | 1':8 5:8",
    "B": "3':4 2':4 1':4 7:4 | 6:4 5:4 4:8 | 3:4 4:2 5:2 6:4 7:4 | 1':16"},
   lead="supersaw", lead2="brass", counter="choir", desc="Battlefield theme. It has come ashore.")
_S("m_mycelia", "MYCELIA", "battle", 104, 45, "dor", "44", "funk",
   {"A": "1m7 4M7 1m7 5m7", "B": "3M7 4M7 2m7 5m7"},
   {"A": "1:2 r:2 3:2 4:2 5:2 r:2 3:4 | 4:2 5:2 7:2 5:2 4:4 3:4 | 1:2 r:2 3:2 4:2 5:2 7:2 1':4 | 7:4 5:4 r:8",
    "B": "5:4 7:4 1':2 2':2 3':4 | 2':6 1':2 7:8 | 6:4 1':4 2':4 4':4 | 3':12 r:4"},
   lead="ep", lead2="marimba", counter="flute", swing=0.18, desc="Battlefield theme. The forest floor has a groove.")
_S("m_wormsmaw", "WORM'S MAW", "battle", 126, 44, "phd", "54", "desert",
   {"A": "1 2 1 7", "B": "4m 2M 6M 1M"},
   {"A": "1:4 2:2 3:4 4:2 5:4 4:4 | 3:6 2:4 1:6 2:4 | 3:4 4:2 5:4 6:2 5:4 4:4 | 3:4 2:4 1:12",
    "B": "5:6 6:4 5:6 4:4 | 3:10 2:10 | 1:4 2:2 3:4 4:2 5:8 | 1':20"},
   lead="reed", lead2="erhu", counter="brass", desc="Battlefield theme. Five beats on the edge of the pit.")
_S("m_serpent", "SERPENT STAIRS", "battle", 120, 46, "dor", "44", "epic",
   {"A": "1 7 4 1", "B": "3 7 4 5"},
   {"A": "1:4 5:4 4:2 3:2 4:4 | 5:6 6:2 5:8 | 1':4 7:2 6:2 5:4 4:4 | 3:4 2:4 1:8",
    "B": "3:4 4:4 5:8 | 6:4 7:4 1':8 | 2':4 1':2 7:2 6:4 5:4 | 5:16"},
   lead="brass", lead2="flute", counter="horn", harm_i="marimba", desc="Battlefield theme. Drums from the temple steps.")
_S("m_astrolabe", "ASTROLABE", "battle", 132, 47, "lyd", "44", "techno",
   {"A": "1 2 5 1", "B": "6 3 2 5"},
   {"A": "1:2 5:2 2':2 3':2 5:4 3':4 | 2':2 6:2 1':2 2':2 6:4 2':4 | 3':2 5':2 4':2 3':2 2':4 7:4 | 1':16",
    "B": "6:4 3':4 2':4 6:4 | 5:4 2':4 1':8 | 7:4 1':2 2':2 3':4 5':4 | 2':16"},
   lead="celesta", lead2="supersaw", counter="glasspad", desc="Battlefield theme. Clockwork in four on the floor.")
_S("m_ghostreef", "GHOST REEF", "battle", 100, 43, "hmin", "34", "gothic",
   {"A": "1 4 5 1", "B": "6 4 5 5"},
   {"A": "1:4 3:4 5:4 | 6:6 5:2 4:4 | 3:4 2:4 7,:4 | 1:12",
    "B": "5:4 1':4 7:4 | 6:6 5:2 3:4 | 4:4 6:4 5:4 | 5:12"},
   lead="organ", lead2="choir", counter="erhu", desc="Battlefield theme. A waltz for drowned sailors.")
