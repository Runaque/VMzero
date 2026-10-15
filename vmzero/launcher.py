"""The VMzero library screen: pick an app, press Enter, VMzero routes it to a tier."""

import time

import pygame

from . import __version__
from .host import get_host
from .library import TIER_EMULATED, TIER_MPY_BIN, TIER_NATIVE, scan
from .runtime import run_native
from .shim import lcd

BADGES = {
    TIER_NATIVE: ("PY", 0x2EC27E),
    TIER_MPY_BIN: ("MPY", 0xE5A50A),
    TIER_EMULATED: ("XT", 0x9A6DE0),
}
BG = 0x0E1116
PANEL = 0x1A2030
ACCENT = 0x3DAEE9
DIM = 0x7A8494
ROW_H = 17
TOP = 20
UP_KEYS = (pygame.K_UP, ord(";"))
DOWN_KEYS = (pygame.K_DOWN, ord("."))
ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)


class Launcher:
    def __init__(self, apps_dir):
        self.apps_dir = apps_dir
        self.apps = scan(apps_dir)
        self.sel = 0
        self.top = 0
        self.message = ""
        self.message_until = 0.0

    # ---- drawing ------------------------------------------------------
    def draw(self):
        s = lcd.screen()
        W, H = s.width(), s.height()
        s.setTextSize(1)
        s.setTextDatum(0)
        s.fillScreen(BG)

        # header
        s.fillRect(0, 0, W, TOP - 3, PANEL)
        s.setFont(lcd.FONTS.DejaVu12)
        s.setTextColor(ACCENT, None)
        s.drawString("VMzero", 4, 2)
        s.setFont(lcd.FONTS.DejaVu9)
        s.setTextColor(DIM, None)
        info = "v%s  %d apps" % (__version__, len(self.apps))
        s.drawString(info, W - s.textWidth(info) - 4, 4)

        rows = (H - TOP - 14) // ROW_H
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + rows:
            self.top = self.sel - rows + 1

        if not self.apps:
            s.setTextColor(DIM, None)
            s.drawString("No apps in %s" % self.apps_dir[-28:], 6, TOP + 4)

        for i, app in enumerate(self.apps[self.top:self.top + rows]):
            idx = self.top + i
            y = TOP + i * ROW_H
            selected = idx == self.sel
            if selected:
                s.fillRoundRect(2, y, W - 4, ROW_H - 2, 3, PANEL)
                s.fillRect(2, y + 2, 2, ROW_H - 6, ACCENT)
            s.setFont(lcd.FONTS.DejaVu12)
            s.setTextColor(0xFFFFFF if app.runnable else 0xB0B6C0, None)
            s.drawString(app.name[:24], 9, y + 2)
            label, colour = BADGES.get(app.tier, ("?", 0x555555))
            s.setFont(lcd.FONTS.DejaVu9)
            bw = s.textWidth(label) + 8
            bx = W - bw - 6
            s.fillRoundRect(bx, y + 2, bw, ROW_H - 6, 3, colour)
            s.setTextColor(0x0E1116, None)
            s.drawString(label, bx + 4, y + 3)

        # footer: hint or status message
        s.fillRect(0, H - 13, W, 13, PANEL)
        s.setFont(lcd.FONTS.DejaVu9)
        if self.message and time.monotonic() < self.message_until:
            s.setTextColor(0xFFD479, None)
            s.drawString(self.message[:46], 4, H - 11)
        else:
            app = self.apps[self.sel] if self.apps else None
            hint = "; . select   enter run   esc back"
            if app and app.chip:
                hint = "%s  %s" % (app.chip, hint)
            s.setTextColor(DIM, None)
            s.drawString(hint, 4, H - 11)

    def flash(self, text, seconds=3.0):
        self.message = text
        self.message_until = time.monotonic() + seconds

    # ---- loop ---------------------------------------------------------
    def run(self):
        host = get_host()
        dirty = True
        while True:
            host.pump()
            if host.exit_requested:          # Esc on the home screen: nothing to leave
                host.exit_requested = False
            k = host.pop_key()
            if k:
                key, ch = k
                dirty = True
                if self.apps:
                    if key in UP_KEYS or ch == ";":
                        self.sel = (self.sel - 1) % len(self.apps)
                    elif key in DOWN_KEYS or ch == ".":
                        self.sel = (self.sel + 1) % len(self.apps)
                    elif key in ENTER_KEYS or ch == "\r":
                        self.launch(self.apps[self.sel])
                if ch == "r":
                    self.apps = scan(self.apps_dir)
                    self.sel = min(self.sel, max(0, len(self.apps) - 1))
                    self.flash("Library rescanned")
            if dirty or (self.message and time.monotonic() >= self.message_until):
                if self.message and time.monotonic() >= self.message_until:
                    self.message = ""
                self.draw()
                host.present(force=True)
                dirty = False
            time.sleep(0.016)

    def launch(self, app):
        if app.runnable:
            result = run_native(app)
            self.flash("%s %s" % (app.name, result))
        else:
            self.flash(app.note or "This app type isn't supported yet", 4.0)
