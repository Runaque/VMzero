"""UiFlow2 `Widgets` — the retained-mode UI objects UiFlow2 generates code with."""

from .lcd import FONTS, rgb, screen


def fillScreen(color=0x000000):
    screen().fillScreen(color)


def setRotation(r=1):
    pass


def setBrightness(b):
    pass


class _Widget:
    def __init__(self):
        self._visible = True

    def setVisible(self, v):
        if self._visible and not v:
            self._erase()
        self._visible = bool(v)
        if v:
            self._draw()

    def _erase(self):
        pass

    def _draw(self):
        pass


class Label(_Widget):
    LEFT_ALIGNED, CENTER_ALIGNED, RIGHT_ALIGNED = 0, 1, 2

    def __init__(self, text, x, y, size=1.0, fg=0xFFFFFF, bg=0x000000, font=None):
        super().__init__()
        self.text, self.x, self.y = str(text), int(x), int(y)
        self.size, self.fg, self.bg = float(size), fg, bg
        self.font = font or FONTS.DejaVu12
        self._box = None
        self._draw()

    def _erase(self):
        if self._box:
            screen().fillRect(*self._box, self.bg)
            self._box = None

    def _draw(self):
        if not self._visible:
            return
        s = screen()
        old = (s._font, s._size, s._fg, s._bg, s._datum)
        s._font, s._size, s._datum = self.font, self.size, 0
        s.setTextColor(self.fg, self.bg)
        w = s.drawString(self.text, self.x, self.y)
        self._box = (self.x, self.y, w, s.fontHeight())
        s._font, s._size, s._fg, s._bg, s._datum = old

    def setText(self, text):
        self._erase()
        self.text = str(text)
        self._draw()

    def setColor(self, fg, bg=None):
        self._erase()
        self.fg = fg
        if bg is not None:
            self.bg = bg
        self._draw()

    def setCursor(self, x=None, y=None):
        self._erase()
        if x is not None:
            self.x = int(x)
        if y is not None:
            self.y = int(y)
        self._draw()

    def setFont(self, font):
        self._erase()
        self.font = font
        self._draw()

    def setSize(self, size):
        self._erase()
        self.size = float(size)
        self._draw()


class Title(Label):
    def __init__(self, text, x=3, fg=0xFFFFFF, bg=0x0000FF, font=None):
        self._bar_bg = bg
        screen().fillRect(0, 0, screen().width(), 18, bg)
        super().__init__(text, x, 1, 1.0, fg, bg, font or FONTS.DejaVu12)


class _Shape(_Widget):
    def __init__(self, fill, outline, **geo):
        super().__init__()
        self.__dict__.update(geo)
        self.fill, self.outline = fill, outline
        self._draw()

    def setColor(self, color=None, fill_c=None):
        self._erase()
        if color is not None:
            self.outline = color
        if fill_c is not None:
            self.fill = fill_c
        self._draw()


class Rectangle(_Shape):
    def __init__(self, x, y, w, h, color=0xFFFFFF, fill_c=0x000000):
        super().__init__(fill_c, color, x=x, y=y, w=w, h=h)

    def _draw(self):
        if self._visible:
            screen().fillRect(self.x, self.y, self.w, self.h, self.fill)
            screen().drawRect(self.x, self.y, self.w, self.h, self.outline)

    def _erase(self):
        screen().fillRect(self.x, self.y, self.w, self.h, 0x000000)

    def setSize(self, w, h):
        self._erase()
        self.w, self.h = w, h
        self._draw()

    def setCursor(self, x, y):
        self._erase()
        self.x, self.y = x, y
        self._draw()


class Circle(_Shape):
    def __init__(self, x, y, r, color=0xFFFFFF, fill_c=0x000000):
        super().__init__(fill_c, color, x=x, y=y, r=r)

    def _draw(self):
        if self._visible:
            screen().fillCircle(self.x, self.y, self.r, self.fill)
            screen().drawCircle(self.x, self.y, self.r, self.outline)

    def _erase(self):
        screen().fillCircle(self.x, self.y, self.r, 0x000000)

    def setRadius(self, r):
        self._erase()
        self.r = r
        self._draw()

    def setCursor(self, x, y):
        self._erase()
        self.x, self.y = x, y
        self._draw()


class Image(_Widget):
    def __init__(self, path, x=0, y=0, *a, **k):
        super().__init__()
        self.path, self.x, self.y = path, x, y
        self._draw()

    def _draw(self):
        if self._visible:
            screen().drawImage(self.path, self.x, self.y)

    def setImage(self, path):
        self.path = path
        self._draw()

    def setCursor(self, x, y):
        self.x, self.y = x, y
        self._draw()
