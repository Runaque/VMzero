"""Entry point: python -m vmzero [--apps DIR] [--size 240x135] [--scale 3] [--fullscreen]"""

import argparse
import os

from .host import Host, set_host
from .launcher import Launcher

PROFILES = {
    # name: virtual screen the apps were written for
    "cardputer-adv": (240, 135),
    "cardputer": (240, 135),
    "sticks3": (240, 135),
}


def main(argv=None):
    p = argparse.ArgumentParser(prog="vmzero", description="Run M5Stack apps on the Cardputer Zero.")
    p.add_argument("--apps", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps"),
                   help="folder holding your apps (default: ./apps)")
    p.add_argument("--profile", default="cardputer-adv", choices=sorted(PROFILES),
                   help="device the apps were written for (sets the virtual screen size)")
    p.add_argument("--size", help="override virtual screen size, e.g. 320x170")
    p.add_argument("--scale", type=int, default=3, help="window scale on a desktop (default 3)")
    p.add_argument("--fullscreen", action="store_true", help="use the whole display (on the Zero itself)")
    a = p.parse_args(argv)

    w, h = PROFILES[a.profile]
    if a.size:
        w, h = (int(v) for v in a.size.lower().split("x"))

    set_host(Host(w, h, scale=a.scale, fullscreen=a.fullscreen))
    Launcher(os.path.abspath(a.apps)).run()


if __name__ == "__main__":
    main()
