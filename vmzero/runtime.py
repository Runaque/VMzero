"""Tier 1 runtime: runs MicroPython/UiFlow2 source natively under CPython."""

import os
import sys
import traceback

from .host import AppExit, get_host
from .shim import lcd, modules


def run_native(app):
    """Run an app until it returns, crashes, or the user presses the exit key."""
    host = get_host()
    host.exit_requested = False
    host.key_queue.clear()

    saved_modules = set(sys.modules)
    saved_path = list(sys.path)
    saved_cwd = os.getcwd()
    app_dir = os.path.dirname(app.entry)

    modules.install()
    sys.path.insert(0, app_dir)
    os.chdir(app_dir)
    lcd.screen().fillScreen(0)

    result = "exited"
    try:
        with open(app.entry, encoding="utf-8") as f:
            code = compile(f.read(), app.entry, "exec")
        exec(code, {"__name__": "__main__", "__file__": app.entry})
    except AppExit:
        result = "closed"
    except SystemExit:
        result = "exited"
    except BaseException as e:  # show crash on the device screen, not just stderr
        traceback.print_exc()
        _crash_screen(e)
        result = "crashed"
    finally:
        os.chdir(saved_cwd)
        sys.path[:] = saved_path
        for name in set(sys.modules) - saved_modules:
            sys.modules.pop(name, None)
        modules.uninstall()
        host.exit_requested = False
        host.key_queue.clear()
    return result


def _crash_screen(e):
    host = get_host()
    s = lcd.screen()
    s.fillScreen(0x300000)
    s.setFont(lcd.FONTS.DejaVu9)
    s.setTextSize(1)
    s.setTextColor(0xFFFFFF, None)
    s.setCursor(2, 2)
    s.print("App crashed\n%s\n\n" % type(e).__name__)
    s.setTextColor(0xFFB0B0, None)
    msg = str(e)
    for i in range(0, min(len(msg), 160), 36):
        s.print(msg[i:i + 36] + "\n")
    s.setTextColor(0xAAAAAA, None)
    s.setCursor(2, s.height() - 12)
    s.print("any key: back to VMzero")
    host.present(force=True)
    _wait_key()


def _wait_key():
    import time
    host = get_host()
    host.key_queue.clear()
    host.exit_requested = False
    while not host.key_queue and not host.exit_requested:
        host.pump()
        time.sleep(0.02)
    host.key_queue.clear()
    host.exit_requested = False
