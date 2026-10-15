"""Headless smoke test: drives the launcher with scripted keys and saves screenshots.

    SDL_VIDEODRIVER=dummy python tests/smoke_test.py [outdir]
"""

import os
import shutil
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from vmzero.host import Host, set_host  # noqa: E402
from vmzero.launcher import Launcher  # noqa: E402
from vmzero.library import TIER_EMULATED, TIER_MPY_BIN, TIER_NATIVE, scan  # noqa: E402


def fake_firmware(path, chip_id, micropython=False):
    head = bytearray(32)
    head[0] = 0xE9
    head[12:14] = chip_id.to_bytes(2, "little")
    body = b"\x00" * 4096 + (b"MicroPython v1.25.0 on 2026-01-01; M5Cardputer" if micropython else b"arduino")
    with open(path, "wb") as f:
        f.write(head + body)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "screenshots")
    out = os.path.abspath(out)  # apps run with their own folder as cwd
    os.makedirs(out, exist_ok=True)
    apps = tempfile.mkdtemp(prefix="vmzero-apps-")
    for name in os.listdir(os.path.join(ROOT, "apps")):
        shutil.copytree(os.path.join(ROOT, "apps", name), os.path.join(apps, name))
    fake_firmware(os.path.join(apps, "marauder_s3.bin"), 9)
    fake_firmware(os.path.join(apps, "uiflow2_cardputer.bin"), 9, micropython=True)

    tiers = {a.name: a.tier for a in scan(apps)}
    assert tiers["Hello VMzero"] == TIER_NATIVE, tiers
    assert tiers["marauder_s3"] == TIER_EMULATED, tiers
    assert tiers["uiflow2_cardputer"] == TIER_MPY_BIN, tiers
    print("routing OK:", tiers)

    host = Host(240, 135, scale=1)
    set_host(host)
    shot = lambda n: ("shot", os.path.join(out, n))
    # sorted list: bouncer, Hello VMzero, marauder_s3, uiflow2_cardputer
    host.script = [
        (0.3, shot("01_launcher.png")),
        (0.4, pygame.K_RETURN),                 # run bouncer
        (1.4, shot("02_bouncer.png")),
        (1.5, pygame.K_ESCAPE),                 # back to launcher
        (1.8, pygame.K_DOWN),                   # Hello VMzero
        (1.9, pygame.K_RETURN),
        (2.4, "hi zero"),
        (2.9, shot("03_hello_typed.png")),
        (3.0, pygame.K_ESCAPE),
        (3.3, pygame.K_DOWN),                   # marauder_s3 (compiled)
        (3.4, pygame.K_RETURN),
        (3.7, shot("04_compiled_routed.png")),
        (3.9, ("quit",)),
    ]
    try:
        Launcher(apps).run()
    except SystemExit:
        pass
    print("screenshots in", out)


if __name__ == "__main__":
    main()
