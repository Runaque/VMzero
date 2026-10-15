"""M5GFX-compatible drawing surface (the `M5.Lcd` / `M5.Display` object).

Implements the subset of the UiFlow2 Lcd API that community apps use most.
Colours are UiFlow2-style 24-bit ints (0xRRGGBB). Anything not implemented
yet is a silent no-op (see __getattr__) so apps keep running; set
VMZERO_STRICT=1 to make missing calls raise instead, which is how we find
what to implement next.
"""

import os
import re

import pygame

from ..host import get_host

STRICT = os.environ.get("VMZERO_STRICT") == "1"


def rgb(c):
    if c is None:
        return None
    if isinstance(c, tuple):
        return c
    c = int(c) & 0xFFFFFF
    return ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)


class Color:
    BLACK = 0x000000
    WHITE = 0xFFFFFF
    RED = 0xFF0000
    GREEN = 0x00FF00
    BLUE = 0x0000FF
    YELLOW = 0xFFFF00
    MAGENTA = 0xFF00FF
    CYAN = 0x00FFFF
    ORANGE = 0xFFA500
    PINK = 0xFFC0CB
    PURPLE = 0x800080
    NAVY = 0x000080
    DARKGREY = 0x808080
    LIGHTGREY = 0xD3D3D3
    DARKGREEN = 0x006400


class Font:
    """Stand-in for a UiFlow2 font handle; only its pixel size matters here."""

    def __init__(self, name, px):
        self.name, self.px = name, px

    def __repr__(self):
        return "<Font %s %dpx>" % (self.name, self.px)


class Fonts:
    """Widgets.FONTS / Lcd.FONTS: DejaVu9..72, ASCII7, EFont*, Montserrat* ..."""

    def __getattr__(self, name):
        m = re.search(r"(\d+)$", name)
        px = int(m.group(1)) if m else 12
        if name.startswith("ASCII"):
            px = 8
        f = Font(name, px)
        setattr(self, name, f)
        return f


FONTS = Fonts()
_font_cache = {}


def pg_font(font, size_mult=1.0):
    px = max(6, int(round(font.px * 1.3 * size_mult)))
    if px not in _font_cache:
        _font_cache[px] = pygame.font.Font(None, px)
    return _font_cache[px]


class Canvas:
    """A drawable surface. The screen itself is a Canvas wrapping host.screen."""

    COLOR = Color
    FONTS = FONTS

    def __init__(self, surface):
        self._s = surface
        self._fg = (255, 255, 255)
        self._bg = None
        self._font = FONTS.DejaVu12
        self._size = 1.0
        self._cx = 0
        self._cy = 0
        self._datum = 0  # top-left

    # ---- geometry -----------------------------------------------------
    def width(self):
        return self._s.get_width()

    def height(self):
        return self._s.get_height()

    def setRotation(self, r=1):
        pass  # virtual screen is already in the app's landscape orientation

    # ---- primitives ---------------------------------------------------
    def fillScreen(self, color=0):
        self._s.fill(rgb(color))
        self._cx = self._cy = 0

    clear = fillScreen

    def drawPixel(self, x, y, color=0xFFFFFF):
        self._s.set_at((int(x), int(y)), rgb(color))

    def drawLine(self, x0, y0, x1, y1, color=0xFFFFFF):
        pygame.draw.line(self._s, rgb(color), (x0, y0), (x1, y1))

    def drawFastHLine(self, x, y, w, color=0xFFFFFF):
        self.drawLine(x, y, x + w - 1, y, color)

    def drawFastVLine(self, x, y, h, color=0xFFFFFF):
        self.drawLine(x, y, x, y + h - 1, color)

    def drawRect(self, x, y, w, h, color=0xFFFFFF):
        pygame.draw.rect(self._s, rgb(color), (x, y, w, h), 1)

    def fillRect(self, x, y, w, h, color=0xFFFFFF):
        pygame.draw.rect(self._s, rgb(color), (x, y, w, h))

    def drawRoundRect(self, x, y, w, h, r, color=0xFFFFFF):
        pygame.draw.rect(self._s, rgb(color), (x, y, w, h), 1, border_radius=int(r))

    def fillRoundRect(self, x, y, w, h, r, color=0xFFFFFF):
        pygame.draw.rect(self._s, rgb(color), (x, y, w, h), border_radius=int(r))

    def drawCircle(self, x, y, r, color=0xFFFFFF):
        pygame.draw.circle(self._s, rgb(color), (x, y), r, 1)

    def fillCircle(self, x, y, r, color=0xFFFFFF):
        pygame.draw.circle(self._s, rgb(color), (x, y), r)

    def drawTriangle(self, x0, y0, x1, y1, x2, y2, color=0xFFFFFF):
        pygame.draw.polygon(self._s, rgb(color), [(x0, y0), (x1, y1), (x2, y2)], 1)

    def fillTriangle(self, x0, y0, x1, y1, x2, y2, color=0xFFFFFF):
        pygame.draw.polygon(self._s, rgb(color), [(x0, y0), (x1, y1), (x2, y2)])

    # ---- text ---------------------------------------------------------
    def setFont(self, font):
        self._font = font

    def setTextColor(self, fg=0xFFFFFF, bg=None):
        self._fg, self._bg = rgb(fg), rgb(bg)

    def setTextSize(self, size):
        self._size = float(size)

    def setTextDatum(self, datum):
        self._datum = datum

    def setTextScroll(self, enable):
        pass

    def setCursor(self, x=0, y=0):
        self._cx, self._cy = int(x), int(y)

    def getCursor(self):
        return (self._cx, self._cy)

    def fontHeight(self, font=None):
        return pg_font(font or self._font, self._size).get_linesize()

    def textWidth(self, text, font=None):
        return pg_font(font or self._font, self._size).size(str(text))[0]

    def _render(self, text, x, y, fg=None, bg=None, font=None):
        f = pg_font(font or self._font, self._size)
        img = f.render(str(text), True, fg or self._fg, bg if bg is not None else self._bg)
        w, h = img.get_size()
        if self._datum in (1, 4, 7):      # *_center
            x -= w // 2
        elif self._datum in (2, 5, 8):    # *_right
            x -= w
        if self._datum in (3, 4, 5):      # middle_*
            y -= h // 2
        elif self._datum in (6, 7, 8):    # bottom_*
            y -= h
        self._s.blit(img, (x, y))
        return w

    def drawString(self, text, x, y, font=None):
        return self._render(text, int(x), int(y), font=font)

    drawCenterString = lambda self, t, x, y, font=None: self._render(
        t, int(x) - self.textWidth(t, font) // 2, int(y), font=font)

    def print(self, text, color=None):
        fg = rgb(color) if color is not None else None
        lh = self.fontHeight()
        for i, line in enumerate(str(text).split("\n")):
            if i:
                self._cx = 0
                self._cy += lh
            if line:
                self._cx += self._render(line, self._cx, self._cy, fg=fg)
        if self._cy + lh > self.height():
            self._scroll(self._cy + lh - self.height())

    def printf(self, fmt, *args):
        self.print(fmt % args if args else fmt)

    def println(self, text=""):
        self.print(str(text) + "\n")

    def _scroll(self, dy):
        self._s.scroll(0, -dy)
        self._s.fill(self._bg or (0, 0, 0), (0, self.height() - dy, self.width(), dy))
        self._cy -= dy

    # ---- images / canvases --------------------------------------------
    def drawImage(self, path, x=0, y=0, *a, **k):
        try:
            img = pygame.image.load(path)
            self._s.blit(img, (x, y))
        except Exception:
            self.drawRect(x, y, 32, 32, 0xFF00FF)

    drawPng = drawJpg = drawBmp = drawImage

    def newCanvas(self, w, h, bpp=16, psram=False):
        return Canvas(pygame.Surface((int(w), int(h))))

    def push(self, x=0, y=0):
        get_host().screen.blit(self._s, (x, y))

    pushSprite = push

    def delete(self):
        pass

    def startWrite(self):
        pass

    def endWrite(self):
        pass

    def display(self):
        get_host().present(force=True)

    def setBrightness(self, b):
        pass

    def __getattr__(self, name):
        if STRICT:
            raise AttributeError("VMzero shim: Lcd.%s not implemented yet" % name)
        return lambda *a, **k: None


_screen = None


def screen():
    """The canvas bound to the host's virtual screen (created lazily)."""
    global _screen
    if _screen is None or _screen._s is not get_host().screen:
        _screen = Canvas(get_host().screen)
    return _screen
