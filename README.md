# Terminal Tanks — website

The static website for **Terminal Tanks** (desktop game 1.6.0, DS port 1.5.0), served by GitHub Pages.
Every page is plain HTML that shares `site.css` and `site.js`; there is no build step to serve it.

## Run it locally

    python3 tools/serve.py 8766          # then open http://127.0.0.1:8766/home.html

Use `tools/serve.py` rather than `python3 -m http.server`: it answers HTTP Range requests, which the
Jukebox and the video previews need for seeking.

## Pages

| page | what it is |
|---|---|
| play.html | the real `terminaltanks.py` running in the browser (Pyodide in a Web Worker), with sound, the X special button and saves in the browser. Sound plays from files rendered ahead of time: music through the browser's plain media player (`music/`), effects through Web Audio (`audio/sfx.mp3`), analyser bars from `music/spec/`. The game never synthesises audio while you play |
| catalog.html | every tank, ammo, paint, map, home screen, workshop part, unlockable and boss (`catalog.json`, `shots/`) |
| workshop.html | build a tank from parts, including animated paints and HOVER (`tank.js` draws tanks exactly like the game) |
| jukebox.html | all 277 songs, with analyser, EQ and a persistent playbar (`data/music.json`, `music/`). Music plays on the plain media player; the analyser reads `music/spec/`; only a non-flat EQ uses Web Audio |
| cheats.html | every cheat code (`data/cheats.json` adds any that are not written up yet) |
| save-forge.html | read, edit and write real save files and backups (`forge.js`) |
| install.html | desktop download (`downloads/terminaltanks.zip`, `downloads/info.json`) |
| ds.html | the Nintendo DS port, with real screenshots and the ROM (`downloads/terminaltanks-ds.nds`) |
| about.html, home.html, links.html | story (including Martyr's Blessing), news (`news.json`), roadmap (`roadmap.json`) |

## Updating after a new game version

Put the new game at `terminaltanks.py`, then:

    python3 tools/export_site_data.py           # catalog.json, data/*.json and the generated block in site.js
    python3 tools/render_catalog.py             # pictures/clips in shots/ for anything new or changed
    python3 tools/render_music.py               # new or changed songs (music/*.mp3, covers, discs); --all to redo every song
    python3 tools/render_sfx.py                 # every sound effect into audio/sfx.mp3 + audio/sfx.json (about 3 minutes)
    python3 tools/render_spectrum.py            # each song's analyser readings, music/spec/*.bin (after render_music.py)
    python3 tools/release/build_download.py     # downloads/terminaltanks.zip + downloads/info.json (reproducible)
    python3 tools/export_site_data.py --check   # fails if the generated files are out of date

All of these read the game itself (`tools/ttgame.py` loads it without sound), so names, prices, stats and
art come from the source rather than being typed by hand. `--game PATH` points them at another copy.
They need Python 3, Pillow, numpy and ffmpeg.

`python3 tools/check_tank_port.py` compares the JavaScript tank renderer with the game's pixel for pixel.

### DS port

Screenshots come from the real ROM running in the NooDS emulator core, driven by `tools/ds/dsshot.cpp`
(build line in that file):

    python3 tools/ds/capture.py downloads/terminaltanks-ds.nds path/to/dsshot ds/
    python3 tools/ds/capture_clip.py downloads/terminaltanks-ds.nds path/to/dsshot ds/   # the 60 fps clip on the DS page
    python3 tools/ds/release_info.py            # downloads/ds-info.json (size, SHA-256, header facts)

For a new DS release: replace `downloads/terminaltanks-ds.nds`, run the three commands above, and update the DS-vs-PC
comparison table in `ds.html` (those counts come from the DS build itself). The version shown on the page comes from
`downloads/ds-info.json`.

## Tests

With the server running on port 8766 and Playwright installed:

    python3 tools/tests/make_test_saves.py      # saves made by the game's own SaveData code in /tmp/tt-test-saves (never your own)
    python3 tools/tests/forge_roundtrip.py --e2e
    python3 tools/tests/smoke_play.py
    python3 tools/tests/audio_play.py
    python3 tools/tests/xbutton.py ; python3 tools/tests/xbutton.py --mobile
    python3 tools/tests/jukebox_test.py
    python3 tools/tests/catalog_test.py
    python3 tools/tests/workshop_test.py
    python3 tools/tests/site_check.py           # every page: links/files exist, no script errors, no sideways scroll at 375 px
    python3 tools/tests/perf_play.py            # the browser game's frame time with a 4x slower CPU (should stay near 30 fps)
    python3 tools/tests/perf_page.py jukebox.html --play   # how busy a page keeps the browser while it plays
    python3 tools/tests/perf_main.py            # how busy play.html keeps the page on the home screen


## Deploy

Commit and push to the branch GitHub Pages serves. Everything is static. Note that `music/` is about
135 MB (MP3s plus 14 MB of analyser data) (GitHub's limits are 100 MB per file and about 1 GB per Pages site; the largest song is well
under the per-file limit).
