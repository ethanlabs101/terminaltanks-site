TERMINALTANKS {VERSION}
Turn-based tank artillery for your terminal.   https://github.com/ethanlabs101/TerminalTanks

WHAT YOU NEED
  Python 3.10 or newer, and a terminal window of at least 96 x 28 characters
  (100 x 30 or larger is better). Nothing else: the game uses no third-party packages.

SOUND
  The game composes and synthesizes its own music and sound effects. To hear them it needs a way to
  play audio, and it picks the first one it finds: the Python package sounddevice or pyaudio if you
  have installed one, the built-in player on Windows, or on macOS and Linux one of paplay
  (PulseAudio), pw-cat (PipeWire), aplay (ALSA), play (SoX) or ffplay. If none is found the game
  runs silently. Turn music and effects on or off under SETTINGS > AUDIO.

START THE GAME
  Windows    Double-click play.bat, or open Windows Terminal in this folder and run:
                 py terminaltanks.py
  macOS      Open Terminal, go to this folder, and run:
                 python3 terminaltanks.py
  Linux      Open a terminal in this folder and run:
                 python3 terminaltanks.py
  (On macOS and Linux, ./play.sh does the same and checks your Python version first.
   If it says "permission denied", run: chmod +x play.sh)
  Keep terminaltanks.py and the tanks folder together: the game is both.

INSTALL PYTHON IF YOU DO NOT HAVE IT
  Windows    https://www.python.org/downloads/  (tick "Add python.exe to PATH"), or the Microsoft Store.
  macOS      https://www.python.org/downloads/  or:  brew install python
  Linux      Debian/Ubuntu: sudo apt install python3      Fedora: sudo dnf install python3
             Arch: sudo pacman -S python

WHERE YOUR PROGRESS IS SAVED
  Windows    %APPDATA%\TerminalTanks\save.json
  macOS      ~/.config/terminaltanks/save.json
  Linux      ~/.config/terminaltanks/save.json   (or $XDG_CONFIG_HOME/terminaltanks/save.json)
  It is one plain file. Copy it somewhere safe to back it up, and copy it back to restore.
  Extra profiles live next to it as save_profile2.json and save_profile3.json, listed in profiles.json.
  The environment variable TERMINALTANKS_SAVE can point the game at a different file.

OPTIONS
  --save-file PATH       use a different progress file
  --color MODE           auto, truecolor, 256 or 16 (try 256 if colours look wrong)
  --seed N               seed maps and AI for reproducible matches
  --reset-progress       delete saved progress and unlocks, then exit
  --export-music DIR     render the whole soundtrack and every sound effect to WAV files in DIR
  --only TEXT            with --export-music: only songs whose id, name or group contains TEXT
  --version              print the version

LAN PLAY
  Two computers on the same network can play each other. The game uses TCP port 47474 and
  UDP port 47475; allow them through your firewall if the other player cannot find you.

TROUBLESHOOTING
  "requires a larger terminal window"   Make the window bigger or reduce the font size.
  Garbled boxes or symbols              Use a UTF-8 terminal with a font that has box-drawing characters.
  Wrong colours                         Run with --color 256 (or --color 16).
  python is not recognised              Reinstall Python and tick "Add python.exe to PATH" on Windows.

Credit: ethanlabs101 - https://github.com/ethanlabs101
