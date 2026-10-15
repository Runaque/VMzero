# Hello VMzero — a stock UiFlow2-style Cardputer app.
# Nothing in here knows about VMzero: it uses the same M5 / Widgets / hardware
# imports it would on a real Cardputer ADV. VMzero's shim makes them work on the Zero.

import os, sys, io
import M5
from M5 import *
from hardware import MatrixKeyboard
import time

title0 = None
label_typed = None
label_info = None
label_ticks = None
kb = None
typed = ""


def kb_pressed_event(kb_0):
    global typed
    code = kb.get_key()
    if code == 0x08:            # backspace
        typed = typed[:-1]
    elif code == 0x0D:          # enter
        typed = ""
    elif 0x20 <= code < 0x7F:
        typed = (typed + chr(code))[-24:]
    label_typed.setText("> " + typed + "_")


def setup():
    global title0, label_typed, label_info, label_ticks, kb
    M5.begin()
    Widgets.fillScreen(0x222222)
    title0 = Widgets.Title("Hello from VMzero", 3, 0xFFFFFF, 0x0050A0, Widgets.FONTS.DejaVu12)
    label_info = Widgets.Label("UiFlow2 app, running natively", 6, 26, 1.0, 0x9AD0FF, 0x222222, Widgets.FONTS.DejaVu12)
    label_typed = Widgets.Label("> _", 6, 56, 1.0, 0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    label_ticks = Widgets.Label("", 6, 112, 1.0, 0x888888, 0x222222, Widgets.FONTS.DejaVu9)
    kb = MatrixKeyboard()
    kb.set_callback(kb_pressed_event)


def loop():
    M5.update()
    kb.tick()
    label_ticks.setText("uptime %d ms   bat %d%%" % (time.ticks_ms() % 100000, M5.Power.getBatteryLevel()))


if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg

            print_error_msg(e)
        except ImportError:
            print("please update to latest firmware")
