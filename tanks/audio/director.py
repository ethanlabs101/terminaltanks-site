"""The music director: which song plays where (home screens, battlefields, bosses, missions, the Martyr) and which
songs the Jukebox has unlocked."""
from __future__ import annotations

import re

from tanks.audio.house_composer import gen_song
from tanks.content.homes import ANCIENT_THEMES, HOME_ORDER, HOME_THEMES
from tanks.content.maps import ANCIENT_MAPS, MAPS, all_maps
from tanks.content.missions import MISSIONS
from tanks.content.songs import SONGS
from tanks.content.tickets import TICKET_BOSSES


_HOME_HAND = {"CLASSIC": "main_theme", "MEADOW": "green_hills", "CAMPFIRE": "embers_and_ale", "DESERT": "mirage_road",
              "ARCTIC": "frost_lullaby", "NEON": "neon_arcade", "DEEPSEA": "undertow_dub", "MOLTEN": "ash_kingdom", "JUNGLE": "canopy",
              "GALAXY": "starlight_drift", "GHOSTTOWN": "ghost_waltz", "INVASION": "first_contact", "SOLARIS": "solaris_hymn",
              "CHRONOS": "chronos_clockwork", "ETERNAL": "protector", "MASTER": "masters_throne", "SECRET": "kernel_panic",
              "GLASSDESERT": "glass_desert", "LANTERNFEST": "lantern_festival", "WORLDTREE": "worldtree", "SKYWHALE": "sky_whale",
              "SHATTERLINE": "shatterline", "BIOLUME": "h_biolume", "SPIRITSHRINE": "h_spiritshrine", "HOLOCITY": "h_holocity",
              "TESSERACT": "h_tesseract", "KAIJUBAY": "h_kaijubay", "SHROOMGROVE": "h_shroomgrove", "WORMSEA": "h_wormsea",
              "JADETEMPLE": "h_jadetemple", "ORRERY": "h_orrery", "GHOSTARMADA": "h_ghostarmada"}
TOURNAMENT_SONGS = ("boss_stinger", "boss_warden", "boss_specter", "boss_colossus", "boss_sentinel", "boss_glacier", "boss_helios", "boss_rattler",
                    "boss_miasma", "boss_bastion", "boss_zephyr", "boss_geode", "boss_mirage", "boss_revenant", "boss_corsair", "boss_tyrant",
                    "boss_archon", "boss_obsidian", "boss_tempest", "boss_master")
MARTYR_SONGS = ("martyr_ember", "martyr_tempest", "martyr_astral")
MAP_FAMILY_SONGS = {"fire": ("magma_pressure",), "frost": ("frostbite_front",), "desert": ("sandstorm_siege",), "water": ("tidebreaker",),
                    "cosmic": ("orbital_barrage",), "city": ("scrapyard_riot",), "storm": ("eye_of_the_storm",), "wild": ("jungle_drums",),
                    "dark": ("graveyard_shift",), "pastoral": ("hedgerow_skirmish",), "plain": ("steel_rain", "iron_valley", "cartridge_war")}
_MAP_WORDS = (("fire", "lava magma volcan forge ember inferno molten cinder scorch burn hell crater caldera brimstone furnace solar sun obsidian shelled"),
              ("frost", "ice snow frost glacier arctic tundra frozen cryo polar winter crystal fjord crevasse aurora"),
              ("desert", "desert dune sand mesa canyon pyramid oasis sahara badland dust wasteland salt worm"),
              ("water", "sea lagoon harbor harbour beach lake swamp marsh reef coral tide coast river delta wave bay island breakwater causeway culvert cascade falls deep mariana"),
              ("cosmic", "space orbit star starfall nebula galaxy void rift astral cosmic moon moonscape lunar comet asteroid quasar mothership eclipse spiral elevator astrolabe celestial"),
              ("city", "city neon cyber skyline factory rust steam station scrap junk metro foundry industrial citadel rail mine quarry skyscraper skybridge clockwork glitch grid gridlock tokyo vapor synth market"),
              ("storm", "storm thunder gale monsoon tempest cyclone spire lightning maelstrom"),
              ("wild", "jungle forest bamboo grove canopy wild vine root emerald tree gardens anthill mycelia serpent torii"),
              ("dark", "ghost grave blood gothic haunt crypt tomb shadow night skull bone maw sludge cathedral labyrinth cauldron fog"),
              ("pastoral", "meadow valley hill hills hilltop farm field prairie garden orchard hollow pasture glen knoll haystack windmill picnic spring harvest dawn sunset lakeside autumn twilight"))
_MAP_FX = {"embers": "fire", "inferno": "fire", "snow": "frost", "stardust": "cosmic", "rift": "cosmic", "fireflies": "wild", "ash": "dark",
           "storm": "storm", "tempest": "storm", "motes": "city", "plankton": "water", "sakura": "wild", "rain": "city", "spores": "wild",
           "sandfall": "desert", "ghostlights": "dark"}
_PREMIUM_MAP_SONGS = {"glass-desert": "glass_dunes_battle", "lantern-terraces": "lantern_terraces", "worldtree-roots": "worldtree_roots",
                      "whalefall": "whalefall", "shatterline": "shatterline_battle", "mariana-deep": "m_mariana", "torii-path": "m_torii",
                      "neon-gridlock": "m_gridlock", "paradox-engine": "m_paradox", "kaiju-bay": "m_kaiju", "mycelia": "m_mycelia",
                      "worm's-maw": "m_wormsmaw", "serpent-stairs": "m_serpent", "astrolabe": "m_astrolabe", "ghost-reef": "m_ghostreef"}


def family_of(text: str, fx: str) -> str:
    words = set(re.findall(r"[a-z]+", text.lower()))
    for fam, kw in _MAP_WORDS:
        for k in kw.split():
            if k in words or any(w.rstrip("s") == k or (len(k) >= 4 and w.startswith(k)) for w in words):
                return fam
    return _MAP_FX.get(fx, "plain")


def map_family(m) -> str:
    return family_of(f"{m.key} {m.name}", m.theme.fx)


def _build_music_map() -> tuple:
    """One song per home screen and one per battlefield: hand-written where one exists, otherwise the house composer's."""
    homes: dict = {}
    for key in HOME_ORDER:
        if key in _HOME_HAND:
            homes[key] = _HOME_HAND[key]
            continue
        th = HOME_THEMES.get(key)
        name, blurb, fx = (th.name, th.blurb, th.fx) if th else (key.title(), "", "")
        hint = None
        for bt in TICKET_BOSSES:
            if bt.theme == key:
                hint = "t_" + bt.key
        if key in ANCIENT_THEMES[:3]:
            hint = MARTYR_SONGS[ANCIENT_THEMES.index(key)]
        sid = "home_" + key.lower()
        fam = family_of(f"{key} {name}", "")
        if fam == "plain":
            fam = family_of(blurb, fx)
        gen_song(sid, name + (" (VAULT)" if hint and hint.startswith("t_") else " (SANCTUM)" if hint else ""), "menu", fam, "Home screen. " + blurb, hint)
        homes[key] = sid
    maps: dict = dict(_PREMIUM_MAP_SONGS)
    for b_ in TICKET_BOSSES:
        maps[b_.map_key] = "t_" + b_.key
    for i, am in enumerate(ANCIENT_MAPS):
        maps[am.key] = MARTYR_SONGS[i]
    left = {f: list(v) for f, v in MAP_FAMILY_SONGS.items()}
    every = list(all_maps().values())
    for m in every:                                        # the original battle themes each keep one battlefield of their own
        if m.key in maps:
            continue
        fam = map_family(m)
        if left.get(fam):
            maps[m.key] = left[fam].pop(0)
    for m in every:
        if m.key in maps:
            continue
        sid = "map_" + m.key.replace("'", "")
        gen_song(sid, m.name, "battle", map_family(m), "Battlefield. " + m.description)
        maps[m.key] = sid
    return homes, maps


HOME_SONG, MAP_SONG = _build_music_map()
SONG_HOMES: dict = {}
for _k, _v in HOME_SONG.items():
    SONG_HOMES.setdefault(_v, []).append(_k)
SONG_MAPS: dict = {}
for _k, _v in MAP_SONG.items():
    SONG_MAPS.setdefault(_v, []).append(_k)


def map_song(m) -> str:
    if m is None:
        return "steel_rain"
    return MAP_SONG.get(m.key, "steel_rain")


JUKEBOX_GROUPS = (("HOME SCREENS", "menu"), ("BATTLEFIELDS", "battle"), ("TOURNAMENT", "tbos"), ("MISSIONS", "mission"),
                  ("ANCIENT HOARDERS", "ticket"), ("THE MARTYR", "martyr"), ("STORY", "story"))


def song_group(sid: str) -> str:
    if sid in TOURNAMENT_SONGS:
        return "tbos"
    if sid in ("saucer_attack", "mothership", "boss_rush", "squad_up"):
        return "mission"
    if sid.startswith("t_"):
        return "ticket"
    if sid in MARTYR_SONGS:
        return "martyr"
    return {"menu": "menu", "battle": "battle", "story": "story"}.get(SONGS[sid].cat, "battle")


def jukebox_unlocked(app, sid: str) -> bool:
    """Everything you have heard, plus everything your progress has reached (so older saves start with a full shelf)."""
    sv = app.save
    if sid in heard_songs(sv) or sid in ("main_theme", "tutorial", "shop_jingle", "workshop"):
        return True
    if sid in TOURNAMENT_SONGS:
        return TOURNAMENT_SONGS.index(sid) + 1 in sv.completed
    if sid.startswith("t_"):
        return sid[2:] in sv.tickets_won
    if sid == "whisper":
        return bool(sv.tickets_won) or sv.martyr_won
    if sid in MARTYR_SONGS or sid in ("time_machine", "the_blessing", "protector"):
        return sv.martyr_won or (sid in MARTYR_SONGS and sv.martyr_seen and MARTYR_SONGS.index(sid) <= sv.martyr_phase)
    if sid in ("saucer_attack", "squad_up", "first_contact"):
        return sv.missions_open()
    if sid in ("mothership", "boss_rush"):
        return len(MISSIONS) in sv.mission_completed or (sid == "boss_rush" and 40 in sv.mission_completed)
    owned = sv.home_modes()
    if any(h in owned for h in SONG_HOMES.get(sid, ())):
        return True
    am = all_maps()
    return any(k in am and (am[k] in MAPS or sv.is_unlocked("map:" + k)) for k in SONG_MAPS.get(sid, ()))


def heard_songs(sv) -> set:
    return set(filter(None, sv.settings.get("heard", "").split(",")))
