"""Terminal Tanks - turn-based artillery for the terminal.

The game lives in this package; run it with `python3 terminaltanks.py` from the folder above. Layout:

    config, colors, settings      constants, colour maths, player settings
    terminal, screen, web         terminal and browser I/O, the cell screen and pixel canvas
    content/                      everything you can add to: tanks, ammo, maps, paints, home screens, songs, shop, ...
    art/                          drawing: tanks, shells, scenery, home-screen art, song covers, bosses
    battle/                       the simulation: terrain, physics, tanks, effects, AI, special-ammo mechanics
    match/                        sessions (a match, a mission, a ticket, the tournament, the Martyr), LAN data
    save, profiles, net           progress on disk, save profiles, LAN networking
    audio/                        the synthesizer, composer, mixer, output devices and the music director
    ui/, scenes/                  widgets and every screen of the game
    app                           the Application (scene stack, main loop) and the command line"""
from __future__ import annotations


__version__ = "2.0.0"
CREDIT_NAME = "ethanlabs101"
CREDIT_URL = "github.com/ethanlabs101"
