"""Builds the fake MicroPython/UiFlow2 modules an app imports.

    import M5 / from M5 import *      -> Lcd, Display, Widgets, BtnA, Speaker, Power ...
    from hardware import MatrixKeyboard, Pin, I2C ...
    import machine, utime, time.ticks_ms() ...

Fresh module objects are built for every app launch so one app can't leave
state behind for the next. Real Zero GPIO/I2C/IR backends plug in where the
stubs are today (see Stub below).
"""

import sys
import time as _time
import types

import pygame

from ..host import AppExit, get_host
from . import lcd as _lcd
from . import widgets as _widgets

SHIM_NAMES = ("M5", "hardware", "machine", "utime", "Widgets", "M5Things", "unit", "module", "utility")

# Host key -> Cardputer keycode/char. The Cardputer has no arrow keys; its
# firmware convention is ; , . / for up/left/down/right, so host arrows map there.
SPECIAL = {
    pygame.K_RETURN: (0x0D, "\r"),
    pygame.K_KP_ENTER: (0x0D, "\r"),
    pygame.K_BACKSPACE: (0x08, "\b"),
    pygame.K_TAB: (0x09, "\t"),
    pygame.K_DELETE: (0x7F, ""),
    pygame.K_UP: (ord(";"), ";"),
    pygame.K_LEFT: (ord(","), ","),
    pygame.K_DOWN: (ord("."), "."),
    pygame.K_RIGHT: (ord("/"), "/"),
}

BTN_A_KEY = pygame.K_F1  # the Cardputer's G0 button


def translate_key(key, char):
    if key in SPECIAL:
        return SPECIAL[key]
    if char and ord(char[0]) < 0x80:
        return ord(char[0]), char[0]
    return None


class Stub:
    """Accepts any constructor/method call. Placeholder for Zero-side drivers."""

    def __init__(self, *a, **k):
        self._name = type(self).__name__

    def __getattr__(self, name):
        def call(*a, **k):
            return 0
        return call

    def value(self, v=None):
        return 0 if v is None else None


def _stub_class(name, **consts):
    return type(name, (Stub,), dict(consts))


Pin = _stub_class("Pin", IN=1, OUT=3, PULL_UP=1, PULL_DOWN=2, OPEN_DRAIN=7, IRQ_RISING=1, IRQ_FALLING=2)
I2C = _stub_class("I2C")
SoftI2C = _stub_class("SoftI2C")
SPI = _stub_class("SPI")
UART = _stub_class("UART")
ADC = _stub_class("ADC", ATTN_11DB=3)
PWM = _stub_class("PWM")
RMT = _stub_class("RMT")
IR = _stub_class("IR")
RGB = _stub_class("RGB")


class MatrixKeyboard:
    """hardware.MatrixKeyboard — the Cardputer's built-in keyboard."""

    def __init__(self, *a, **k):
        self._cb = None
        self._last = 0
        self._buf = []

    def tick(self):
        host = get_host()
        while True:
            k = host.pop_key()
            if k is None:
                break
            t = translate_key(*k)
            if t:
                self._buf.append(t)
        if self._buf and self._cb:
            # UiFlow2 fires the callback once per key; get_key() inside it
            # returns that key.
            pending, self._buf = self._buf, []
            for t in pending:
                self._buf = [t]
                self._cb(self)
                self._buf = []

    def is_pressed(self):
        return bool(self._buf)

    isPressed = is_pressed

    def get_key(self):
        if self._buf:
            self._last = self._buf.pop(0)[0]
            return self._last
        return 0

    def get_string(self):
        if self._buf:
            code, ch = self._buf.pop(0)
            self._last = code
            return ch
        return ""

    def set_callback(self, cb):
        self._cb = cb


class Button:
    def __init__(self):
        self._down = False
        self._clicked = False
        self._pressed_evt = False
        self._released_evt = False
        self._cbs = {}

    CB_TYPE = types.SimpleNamespace(WAS_CLICKED=0, WAS_PRESSED=1, WAS_RELEASED=2,
                                    WAS_HOLD=3, WAS_DOUBLECLICKED=4)

    def _sample(self):
        down = bool(pygame.key.get_pressed()[BTN_A_KEY])
        self._pressed_evt = down and not self._down
        self._released_evt = self._down and not down
        self._clicked = self._released_evt
        self._down = down
        for kind, flag in ((0, self._clicked), (1, self._pressed_evt), (2, self._released_evt)):
            if flag and kind in self._cbs:
                self._cbs[kind](state=True)

    def isPressed(self):
        return self._down

    def isReleased(self):
        return not self._down

    def wasPressed(self):
        return self._pressed_evt

    def wasReleased(self):
        return self._released_evt

    def wasClicked(self):
        return self._clicked

    def setCallback(self, type=0, cb=None):
        self._cbs[type] = cb


class _Speaker:
    def tone(self, freq, ms=100, *a, **k):
        pass  # TODO: ALSA/PWM backend on the Zero

    def setVolume(self, v):
        pass

    def setVolumePercentage(self, p):
        pass

    def end(self):
        pass

    def __getattr__(self, n):
        return lambda *a, **k: None


class _Power:
    def getBatteryLevel(self):
        return 100

    def getBatteryVoltage(self):
        return 4100

    def isCharging(self):
        return False

    def __getattr__(self, n):
        return lambda *a, **k: 0


def _ticks_ms():
    return int(_time.monotonic() * 1000) & 0x3FFFFFFF


def _ticks_us():
    return int(_time.monotonic() * 1_000_000) & 0x3FFFFFFF


def _ticks_diff(a, b):
    return ((a - b + 0x20000000) & 0x3FFFFFFF) - 0x20000000


def _ticks_add(a, d):
    return (a + d) & 0x3FFFFFFF


MP_TIME = {
    "ticks_ms": _ticks_ms,
    "ticks_us": _ticks_us,
    "ticks_cpu": _ticks_us,
    "ticks_diff": _ticks_diff,
    "ticks_add": _ticks_add,
    "sleep_ms": lambda ms: _sleep_responsive(ms / 1000),
    "sleep_us": lambda us: _time.sleep(us / 1_000_000),
}


def _sleep_responsive(seconds):
    """Sleep without freezing the window, and stay exit-able (Esc)."""
    host = get_host()
    end = _time.monotonic() + seconds
    while True:
        host.pump()
        if host.exit_requested:
            raise AppExit()
        left = end - _time.monotonic()
        if left <= 0:
            return
        _time.sleep(min(left, 0.02))


def build_modules():
    host = get_host()
    screen = _lcd.screen()
    btn_a = Button()

    # --- Widgets -------------------------------------------------------
    W = types.ModuleType("Widgets")
    for n in ("fillScreen", "setRotation", "setBrightness", "Label", "Title",
              "Rectangle", "Circle", "Image"):
        setattr(W, n, getattr(_widgets, n))
    W.FONTS = _lcd.FONTS

    # --- M5 --------------------------------------------------------------
    M5 = types.ModuleType("M5")

    def begin(*a, **k):
        screen.fillScreen(0)

    def update():
        host.pump()
        if host.exit_requested:
            raise AppExit()
        btn_a._sample()
        if len(host.key_queue) > 64:
            del host.key_queue[:-64]
        host.present()
        _time.sleep(0.002)  # tight UiFlow loops would otherwise pin a core

    M5.begin = begin
    M5.update = update
    M5.Lcd = M5.Display = screen
    M5.Widgets = W
    M5.BtnA = btn_a
    M5.Speaker = _Speaker()
    M5.Power = _Power()
    M5.getBoard = lambda: 0x14  # BOARD.M5CardputerADV-ish; real ID TBD
    M5.BOARD = types.SimpleNamespace(M5Cardputer=0x13, M5CardputerADV=0x14, M5StickS3=0x15)
    M5.__all__ = ["M5", "Lcd", "Display", "Widgets", "BtnA", "Speaker", "Power", "begin", "update"]
    M5.M5 = M5
    M5.Lcd, M5.Display = screen, screen

    # --- hardware / machine ---------------------------------------------
    hw = types.ModuleType("hardware")
    machine = types.ModuleType("machine")
    for n, obj in (("Pin", Pin), ("I2C", I2C), ("SoftI2C", SoftI2C), ("SPI", SPI),
                   ("UART", UART), ("ADC", ADC), ("PWM", PWM), ("RMT", RMT)):
        setattr(hw, n, obj)
        setattr(machine, n, obj)
    hw.MatrixKeyboard = MatrixKeyboard
    hw.IR = IR
    hw.RGB = RGB
    machine.freq = lambda *a: 240_000_000
    machine.reset = lambda: (_ for _ in ()).throw(AppExit())
    machine.unique_id = lambda: b"VMZERO"
    machine.idle = lambda: _time.sleep(0.001)

    # --- utime + MicroPython extras on the real time module ---------------
    utime = types.ModuleType("utime")
    for n in ("time", "localtime", "gmtime", "mktime", "sleep"):
        setattr(utime, n, getattr(_time, n))
    for n, fn in MP_TIME.items():
        setattr(utime, n, fn)
        if not hasattr(_time, n):
            setattr(_time, n, fn)

    # --- catch-all for unit/module drivers not ported yet ----------------
    def lazy_pkg(name):
        m = types.ModuleType(name)
        m.__getattr__ = lambda attr: _stub_class(attr)
        return m

    utility = types.ModuleType("utility")

    def print_error_msg(e):
        import traceback
        traceback.print_exception(e)
        screen.setTextColor(0xFF4040, 0x000000)
        screen.setCursor(0, 0)
        screen.print("App error:\n%s: %s" % (type(e).__name__, e))
        host.present(force=True)

    utility.print_error_msg = print_error_msg

    return {
        "utility": utility,
        "M5": M5,
        "Widgets": W,
        "hardware": hw,
        "machine": machine,
        "utime": utime,
        "unit": lazy_pkg("unit"),
        "module": lazy_pkg("module"),
        "M5Things": lazy_pkg("M5Things"),
    }


def install():
    mods = build_modules()
    sys.modules.update(mods)
    return mods


def uninstall():
    for n in SHIM_NAMES:
        sys.modules.pop(n, None)
