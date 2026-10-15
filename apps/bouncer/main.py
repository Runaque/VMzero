# Bouncer — raw M5.Lcd drawing + MicroPython timing calls (ticks_ms / sleep_ms).
# Written the way you'd write it for a Cardputer; runs unchanged under VMzero.

import M5
from M5 import *
import time

M5.begin()
W, H = M5.Lcd.width(), M5.Lcd.height()
x, y, dx, dy, r = 40, 40, 3, 2, 8
canvas = M5.Lcd.newCanvas(W, H)
start = time.ticks_ms()
frames = 0

while True:
    M5.update()
    canvas.fillScreen(0x101830)
    for gx in range(0, W, 20):
        canvas.drawFastVLine(gx, 0, H, 0x18244A)
    for gy in range(0, H, 20):
        canvas.drawFastHLine(0, gy, W, 0x18244A)
    x += dx
    y += dy
    if x < r or x > W - r:
        dx = -dx
    if y < r or y > H - r:
        dy = -dy
    canvas.fillCircle(x, y, r, 0xFFB000)
    canvas.drawCircle(x, y, r + 3, 0xFFFFFF)
    frames += 1
    secs = max(1, time.ticks_diff(time.ticks_ms(), start)) / 1000
    canvas.setTextColor(0xFFFFFF, 0x101830)
    canvas.setCursor(4, H - 12)
    canvas.print("%.0f fps  esc = back" % (frames / secs))
    canvas.push(0, 0)
    time.sleep_ms(16)
