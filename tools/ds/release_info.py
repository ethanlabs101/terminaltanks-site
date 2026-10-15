#!/usr/bin/env python3
"""Checks the DS release and writes downloads/ds-info.json for the DS page.
    python3 tools/ds/release_info.py [downloads/terminaltanks-ds.nds]
Verifies the ROM header checksum (the CRC-16 every DS checks before it boots a cartridge image) and reads the title,
version and icon text from the banner, so the page never states anything the file does not."""
import hashlib, json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
rom = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "downloads" / "terminaltanks-ds.nds"
d = rom.read_bytes()


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


stored = struct.unpack("<H", d[0x15E:0x160])[0]
if crc16(d[:0x15E]) != stored:
    raise SystemExit(f"{rom.name}: header checksum mismatch - the ROM is damaged")
off = struct.unpack("<I", d[0x68:0x6C])[0]
banner = d[off + 0x240:off + 0x340].decode("utf-16le").rstrip("\x00").split("\n")
arm9 = struct.unpack("<I", d[0x2C:0x30])[0]
arm7 = struct.unpack("<I", d[0x3C:0x40])[0]
info = {
    "file": "downloads/" + rom.name, "bytes": len(d), "sha256": hashlib.sha256(d).hexdigest(), "md5": hashlib.md5(d).hexdigest(),
    "title": banner[0] if banner else "", "version": (banner[1].split()[0].lstrip("v") if len(banner) > 1 else ""), "banner": banner,
    "header": {"title": d[0:12].rstrip(b"\0").decode("ascii", "replace"), "code": d[12:16].decode("ascii", "replace"),
               "unit": {0: "Nintendo DS", 2: "Nintendo DS and DSi"}.get(d[0x12], str(d[0x12])), "crc16": f"{stored:04X}",
               "arm9_bytes": arm9, "arm7_bytes": arm7},
    "built_with": [x for x, needle in (("libfat / DLDI for SD-card saves", b"Chishm"), ("NitroFS for game data", b"nitro:/"),
                                       ("DSWiFi for DS-to-DS wireless", b"wifi_arm9")) if needle in d],
    "save_folder": "/data/TerminalTanks/" if b"/data/TerminalTanks" in d else "",
}
out = ROOT / "downloads" / "ds-info.json"
out.write_text(json.dumps(info, indent=1) + "\n")
print(json.dumps(info, indent=1))
