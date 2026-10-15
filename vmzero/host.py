"""Host layer: the single pygame window/framebuffer VMzero draws into.

Apps always draw to a *virtual* screen sized like the device they were
written for (e.g. 240x135 for a Cardputer ADV). The host scales that
virtual screen onto the real display (a desktop window while developing,
the Cardputer Zero's panel via SDL kmsdrm/fbdev on the device).
"""

import os
import time

import pygame


class AppExit(BaseException):
    """Raised inside an app to hand control back to the launcher.

    BaseException on purpose: UiFlow2's generated template wraps the main
    loop in `except (Exception, KeyboardInterrupt)`, which must not swallow it.
    """


class Host:
    def __init__(self, width=240, height=135, scale=3, fullscreen=False, exit_key=pygame.K_ESCAPE):
        pygame.init()
        pygame.key.set_repeat(400, 60)
        self.vw, self.vh = width, height
        self.exit_key = exit_key
        flags = pygame.FULLSCREEN if fullscreen else 0
        if fullscreen:
            self.window = pygame.display.set_mode((0, 0), flags)
        else:
            self.window = pygame.display.set_mode((width * scale, height * scale))
        pygame.display.set_caption("VMzero")
        self.screen = pygame.Surface((width, height))
        self.key_queue = []          # (keycode:int, char:str) tuples
        self.exit_requested = False
        self._last_flip = 0.0
        self.min_frame = 1 / 60
        self._t0 = time.monotonic()
        # Scripted input for demos/tests: list of (seconds_from_start, action)
        # where action is a pygame keycode, a str (typed text), ("shot", path)
        # or ("quit",).
        self.script = []

    def _run_script(self):
        now = time.monotonic() - self._t0
        while self.script and self.script[0][0] <= now:
            _, act = self.script.pop(0)
            if isinstance(act, int):
                self.inject_key(act)
            elif isinstance(act, str):
                for ch in act:
                    self.inject_key(ord(ch), ch)
            elif act[0] == "shot":
                self.present(force=True)
                self.save_screenshot(act[1])
            elif act[0] == "quit":
                raise SystemExit(0)

    # ---- events -------------------------------------------------------
    def pump(self):
        if self.script:
            self._run_script()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit(0)
            if ev.type == pygame.KEYDOWN:
                if ev.key == self.exit_key:
                    self.exit_requested = True
                    continue
                self.key_queue.append((ev.key, ev.unicode))

    def pop_key(self):
        return self.key_queue.pop(0) if self.key_queue else None

    def inject_key(self, key, char=""):
        """Used by tests/automation to feed keys without a real keyboard."""
        if key == self.exit_key:
            self.exit_requested = True
        else:
            self.key_queue.append((key, char))

    # ---- output -------------------------------------------------------
    def present(self, force=False):
        now = time.monotonic()
        if not force and now - self._last_flip < self.min_frame:
            return
        ww, wh = self.window.get_size()
        s = min(ww / self.vw, wh / self.vh)
        w, h = int(self.vw * s), int(self.vh * s)
        scaled = pygame.transform.scale(self.screen, (w, h))
        self.window.fill((0, 0, 0))
        self.window.blit(scaled, ((ww - w) // 2, (wh - h) // 2))
        pygame.display.flip()
        self._last_flip = now

    def save_screenshot(self, path):
        pygame.image.save(self.screen, path)


_host = None


def get_host():
    if _host is None:
        raise RuntimeError("VMzero host not initialised")
    return _host


def set_host(h):
    global _host
    _host = h
