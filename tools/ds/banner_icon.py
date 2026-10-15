#!/usr/bin/env python3
"""Extracts the 32 x 32 icon and the title text from a .nds ROM's banner (what a DS menu shows for the game).
    python3 tools/ds/banner_icon.py ROM OUT.png"""
import struct, sys
from PIL import Image
d = open(sys.argv[1], "rb").read()
off = struct.unpack("<I", d[0x68:0x6C])[0]
bm, pal = d[off + 0x20:off + 0x220], d[off + 0x220:off + 0x240]
cols = []
for i in range(16):
    v = struct.unpack("<H", pal[i * 2:i * 2 + 2])[0]
    cols.append(((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31, 0 if i == 0 else 255))
im = Image.new("RGBA", (32, 32))
for ty in range(4):
    for tx in range(4):
        tile = bm[(ty * 4 + tx) * 32:(ty * 4 + tx + 1) * 32]
        for y in range(8):
            for x in range(8):
                b = tile[y * 4 + x // 2]
                im.putpixel((tx * 8 + x, ty * 8 + y), cols[(b >> 4) if x & 1 else (b & 15)])
im.save(sys.argv[2])
print(d[off + 0x240:off + 0x340].decode("utf-16le").rstrip("\x00"))
