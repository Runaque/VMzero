"""App library: finds apps on disk and decides which execution tier runs each.

Supported layouts inside the apps folder:

    apps/my_app/main.py          (+ optional app.json manifest)
    apps/my_script.py
    apps/some_firmware.bin       (inspected; see classify_bin)

app.json (all fields optional):
    {"name": "Hello", "author": "Runaque", "entry": "main.py", "profile": "cardputer-adv"}
"""

import json
import os
from dataclasses import dataclass, field

TIER_NATIVE = "native"        # Tier 1: MicroPython source on CPython + shim
TIER_MPY_BIN = "mpy-bin"      # Tier 1 later: MicroPython firmware, scripts to be extracted
TIER_EMULATED = "emulated"    # Tier 2: compiled Xtensa firmware -> emulator + profile
TIER_UNKNOWN = "unknown"

ESP_IMAGE_MAGIC = 0xE9
CHIP_IDS = {0: "ESP32", 2: "ESP32-S2", 5: "ESP32-C3", 9: "ESP32-S3", 12: "ESP32-C2",
            13: "ESP32-C6", 16: "ESP32-H2", 18: "ESP32-P4"}


@dataclass
class App:
    name: str
    path: str
    tier: str
    entry: str = ""
    author: str = ""
    chip: str = ""
    profile: str = ""
    note: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def runnable(self):
        return self.tier == TIER_NATIVE


def _esp_chip(header):
    """Chip name from an ESP image header (extended header chip_id at byte 12)."""
    if len(header) >= 16 and header[0] == ESP_IMAGE_MAGIC:
        return CHIP_IDS.get(int.from_bytes(header[12:14], "little"), "ESP (unknown)")
    return ""


def classify_bin(path):
    """Return (tier, chip, note) for a firmware .bin.

    Checks for an ESP image at 0x0 (app image, or S3/C3 merged image) and
    0x1000 (classic ESP32 merged image), then looks for the MicroPython
    banner string to tell MicroPython builds from compiled Arduino/IDF apps.
    """
    with open(path, "rb") as f:
        head = f.read(0x1010)
        f.seek(0)
        blob = f.read(8 * 1024 * 1024)
    chip = _esp_chip(head[:16]) or _esp_chip(head[0x1000:0x1010])
    if not chip:
        return TIER_UNKNOWN, "", "Not an ESP32 firmware image"
    if b"MicroPython v" in blob or b"uiflow" in blob.lower():
        return TIER_MPY_BIN, chip, "MicroPython .bin: extraction coming in v1.x"
    return TIER_EMULATED, chip, "Compiled firmware: needs the v2 emulator"


def _manifest(folder):
    p = os.path.join(folder, "app.json")
    if os.path.isfile(p):
        try:
            with open(p) as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {}


def scan(apps_dir):
    apps = []
    if not os.path.isdir(apps_dir):
        return apps
    for entry in sorted(os.listdir(apps_dir), key=str.lower):
        full = os.path.join(apps_dir, entry)
        if entry.startswith("."):
            continue
        if os.path.isdir(full):
            meta = _manifest(full)
            main = meta.get("entry", "main.py")
            if os.path.isfile(os.path.join(full, main)):
                apps.append(App(meta.get("name", entry), full, TIER_NATIVE,
                                entry=os.path.join(full, main), author=meta.get("author", ""),
                                profile=meta.get("profile", ""), meta=meta))
        elif entry.endswith(".py"):
            apps.append(App(entry[:-3], full, TIER_NATIVE, entry=full))
        elif entry.endswith(".bin"):
            tier, chip, note = classify_bin(full)
            apps.append(App(entry[:-4], full, tier, chip=chip, note=note))
    return apps
