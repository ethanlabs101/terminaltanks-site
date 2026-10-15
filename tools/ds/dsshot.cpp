// Headless driver for the NooDS core (https://github.com/Hydr8gon/NooDS, GPL-3.0): runs a .nds ROM with no window and
// saves both screens as PPM images. Used by tools/ds/capture.py to take real screenshots of Terminal Tanks DS.
//   dsshot ROM SCRIPT OUTDIR   script lines: <frame> press|release <KEY> | <frame> touch X Y | <frame> untouch | <frame> shot NAME
//   dsshot ROM - OUTDIR        interactive: reads commands on stdin (run N | press K | release K | touch X Y | untouch | shot NAME | quit)
//                              and answers "ok <frame>" after each, so a script can look at the screen before deciding what to press.
// Build (from a NooDS checkout's src folder):
//   g++ -O2 -std=c++11 -I. core/*.cpp core/*/*.cpp path/to/dsshot.cpp -lpthread -o dsshot
#include "core/core.h"
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <map>
static const std::map<std::string, int> KEYS = {{"A", 0}, {"B", 1}, {"SELECT", 2}, {"START", 3}, {"RIGHT", 4}, {"LEFT", 5}, {"UP", 6}, {"DOWN", 7}, {"R", 8}, {"L", 9}, {"X", 10}, {"Y", 11}};
static uint32_t buf[256 * 192 * 2 * 4];
static Core *core;
static int frame = 0;

static void step() {                     // one emulated frame; keep the newest finished picture in buf
    core->running.store(true);
    core->runCore();
    core->gpu.getFrame(buf, false);
    frame++;
}

static void shot(const std::string &dir, const std::string &name) {
    std::string p = dir + "/" + name + ".ppm";
    FILE *o = fopen(p.c_str(), "wb");
    fprintf(o, "P6 256 384 255\n");
    for (int i = 0; i < 256 * 384; i++) { uint32_t c = buf[i]; unsigned char px[3] = {(unsigned char)(c & 0xFF), (unsigned char)((c >> 8) & 0xFF), (unsigned char)((c >> 16) & 0xFF)}; fwrite(px, 1, 3, o); }
    fclose(o);
}

static bool apply(const std::vector<std::string> &w, const std::string &dir) {
    if (w.empty()) return true;
    if (w[0] == "press") core->input.pressKey(KEYS.at(w[1]));
    else if (w[0] == "release") core->input.releaseKey(KEYS.at(w[1]));
    else if (w[0] == "touch") { core->input.pressScreen(); core->spi.setTouch(std::stoi(w[1]), std::stoi(w[2])); }
    else if (w[0] == "untouch") { core->input.releaseScreen(); core->spi.clearTouch(); }
    else if (w[0] == "shot") shot(dir, w[1]);
    else if (w[0] == "run") { int n = std::stoi(w[1]); for (int i = 0; i < n; i++) step(); }
    else if (w[0] == "quit" || w[0] == "end") return false;
    return true;
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: dsshot ROM SCRIPT|- OUTDIR\n"); return 2; }
    Settings::threaded2D = 0; Settings::threaded3D = 0; Settings::emulateAudio = 0; Settings::fpsLimiter = 0;
    Settings::directBoot = 1; Settings::screenFilter = 0; Settings::highRes3D = 0; Settings::savesFolder = 0;
    Settings::basePath = argv[3];
    try { core = new Core(argv[1]); } catch (int e) { fprintf(stderr, "core error %d\n", e); return 1; }
    std::string dir = argv[3];
    if (std::string(argv[2]) == "-") {
        std::string line;
        while (std::getline(std::cin, line)) {
            std::istringstream ss(line); std::vector<std::string> w; std::string t; while (ss >> t) w.push_back(t);
            bool go = apply(w, dir);
            std::cout << "ok " << frame << std::endl;
            if (!go) break;
        }
        return 0;
    }
    std::ifstream sc(argv[2]); std::string line;
    std::multimap<int, std::vector<std::string>> ev; int last = 0;
    while (std::getline(sc, line)) { std::istringstream ss(line); int f; if (!(ss >> f)) continue; std::vector<std::string> w; std::string t; while (ss >> t) w.push_back(t); ev.insert({f, w}); if (f > last) last = f; }
    while (frame <= last) {
        auto r = ev.equal_range(frame);
        for (auto it = r.first; it != r.second; ++it) if (!apply(it->second, dir)) return 0;
        step();
    }
    return 0;
}
