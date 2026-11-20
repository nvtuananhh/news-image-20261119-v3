"""Draw "The World in One Day" -- Thursday 19 November 2026.

A one-page newspaper front page summing up the day's world news, drawn
entirely with the Python standard library: embedded DejaVu glyph bitmaps
(see fontdata.py) and a hand-rolled PNG encoder. No network, no wall
clock, no randomness: two runs write byte-identical files.

Layout (1024x1024, drawn at 2x and downsampled):
  masthead + red subline, region strip, six big numbers,
  3 illustrated lead stories, 10 illustrated cards, a world map with
  an 18-item "also on" list, a markets strip, a date-check box, footer.
Stories: 3 leads + 10 cards + 18 also-list = 31, every region covered.
Only stories that happened, or were first reported, on Thursday
19 November 2026 appear as news; items first reported on 18 November
(Jeffries' nomination, Voyager 1's one-light-day crossing, the EU's
proposed EUR45bn Ukraine loan, the Pew projection) are named in the
date-check box as NOT today's news.
"""

import base64
import math
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fontdata import CHARS, FONTS

S = 2                      # supersample factor (draw 2048, output 1024)
W, H = 1024, 1024
PW, PH = W * S, H * S

PAPER = (247, 242, 231)
INK = (26, 26, 26)
RED = (163, 22, 33)
NAVY = (31, 58, 95)
NAVY_D = (18, 34, 58)
TEAL = (15, 92, 96)
GOLD = (176, 124, 30)
GREY = (90, 86, 78)
LINE = (60, 55, 48)
PALE = (232, 226, 212)
SEA = (198, 214, 224)
LAND = (216, 200, 160)
WHITE = (255, 255, 255)
CREAM = (252, 248, 238)


# ---------------------------------------------------------------- fonts

class Font(object):
    """One decoded glyph set: per-char (advance, xoff, w, h, yoff, rows)."""

    def __init__(self, name):
        raw = base64.b64decode("".join(FONTS[name]))
        self.glyphs = {}
        i = 0
        for ch in CHARS:
            adv = raw[i]
            xo = raw[i + 1] - 128
            w = raw[i + 2]
            h = raw[i + 3]
            yo = raw[i + 4] - 128
            i += 5
            n = ((w + 7) // 8) * h
            self.glyphs[ch] = (adv, xo, w, h, yo, raw[i:i + n])
            i += n
        self.name = name

    def width(self, text):
        return sum(self.glyphs.get(c, self.glyphs[" "])[0] for c in text)

    def height(self):
        # cap height of 'H' plus a little, in 2x pixels
        return self.glyphs["H"][3]


_FONTS = {}


def font(name):
    if name not in _FONTS:
        _FONTS[name] = Font(name)
    return _FONTS[name]


# ---------------------------------------------------------------- canvas

class Page(object):
    def __init__(self):
        self.pix = bytearray(PW * PH * 3)
        self.fill_rect(0, 0, W, H, PAPER)

    def _px(self, x, y):
        return (y * PW + x) * 3

    def set(self, x, y, c):
        if 0 <= x < PW and 0 <= y < PH:
            o = self._px(x, y)
            self.pix[o] = c[0]
            self.pix[o + 1] = c[1]
            self.pix[o + 2] = c[2]

    def fill_rect(self, x0, y0, x1, y1, c):
        x0, y0 = max(0, int(x0 * S)), max(0, int(y0 * S))
        x1, y1 = min(PW, int(x1 * S)), min(PH, int(y1 * S))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for y in range(y0, y1):
            o = (y * PW + x0) * 3
            self.pix[o:o + len(row)] = row

    def rect(self, x0, y0, x1, y1, c, w=1):
        self.fill_rect(x0, y0, x1, y0 + w, c)
        self.fill_rect(x0, y1 - w, x1, y1, c)
        self.fill_rect(x0, y0, x0 + w, y1, c)
        self.fill_rect(x1 - w, y0, x1, y1, c)

    def hline(self, x0, x1, y, c, w=1):
        self.fill_rect(x0, y, x1, y + w, c)

    def vline(self, x, y0, y1, c, w=1):
        self.fill_rect(x, y0, x + w, y1, c)

    def line(self, x0, y0, x1, y1, c, w=1):
        x0, y0, x1, y1 = int(x0 * S), int(y0 * S), int(x1 * S), int(y1 * S)
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        r = max(1, w * S // 2)
        while True:
            for yy in range(y0 - r, y0 + r + 1):
                for xx in range(x0 - r, x0 + r + 1):
                    self.set(xx, yy, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c):
        cx, cy, r = int(cx * S), int(cy * S), int(r * S)
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            dx = int((r * r - dy * dy) ** 0.5)
            o0 = (y * PW + cx - dx) * 3
            self.pix[o0:o0 + (2 * dx + 1) * 3] = bytes(c) * (2 * dx + 1)

    def ring(self, cx, cy, r, c, w=2):
        cx, cy, r = int(cx * S), int(cy * S), int(r * S)
        w = max(1, w * S)
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            d2 = r * r - dy * dy
            if d2 < 0:
                continue
            dx = int(d2 ** 0.5)
            d2i = (r - w) * (r - w) - dy * dy
            dxi = int(d2i ** 0.5) if d2i > 0 else 0
            for x in range(cx - dx, cx - dxi):
                self.set(x, y, c)
            for x in range(cx + dxi + 1, cx + dx + 1):
                self.set(x, y, c)

    def poly(self, pts, c):
        """Scanline fill of a polygon; pts in display coords."""
        pts = [(int(x * S), int(y * S)) for x, y in pts]
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(PH, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) // (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                a, b = xs[i], xs[i + 1]
                if b >= a:
                    o = (y * PW + max(0, a)) * 3
                    self.pix[o:o + (min(PW - 1, b) - max(0, a) + 1) * 3] = (
                        bytes(c) * (min(PW - 1, b) - max(0, a) + 1))

    # ---------------------------------------------------------------- text

    def blit(self, f, ch, x, baseline, c, shear=0.0):
        """Draw one glyph; x, baseline in 2x pixels. Returns advance."""
        g = f.glyphs.get(ch)
        if g is None:
            g = f.glyphs["?"]
        adv, xo, w, h, yo, rows = g
        if w and h:
            stride = (w + 7) // 8
            gx = x + xo
            gy = baseline + yo
            for r in range(h):
                sh = int(shear * (h - r))
                yy = gy + r
                if yy < 0 or yy >= PH:
                    continue
                row = rows[r * stride:(r + 1) * stride]
                for col in range(w):
                    if row[col >> 3] & (0x80 >> (col & 7)):
                        self.set(gx + col + sh, yy, c)
        return adv

    def text(self, fname, x, baseline, s, c, shear=0.0):
        """Draw string; x, baseline in display coords. Returns width."""
        f = font(fname)
        xx = int(x * S)
        for ch in s:
            xx += self.blit(f, ch, xx, int(baseline * S), c, shear)
        return (xx // S) - x

    def text_w(self, fname, s):
        return font(fname).width(s) // S

    def centred(self, fname, cx, baseline, s, c, shear=0.0):
        w = self.text_w(fname, s)
        return self.text(fname, cx - w // 2, baseline, s, c, shear)

    def wrap(self, fname, s, maxw):
        """Greedy word wrap; returns list of lines fitting maxw (display px)."""
        words = s.split(" ")
        lines, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if self.text_w(fname, trial) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines


# ---------------------------------------------------------------- output

def _png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(rgb, w, h):
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    data = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) +
            _png_chunk(b"IDAT", data) + _png_chunk(b"IEND", b""))


def downsample(p):
    """Box-average 2x2 from the 2048 canvas to 1024x1024 RGB bytes."""
    out = bytearray(W * H * 3)
    src = p.pix
    for y in range(H):
        for x in range(W):
            o = (y * W + x) * 3
            acc = [0, 0, 0]
            for dy in range(2):
                base = ((2 * y + dy) * PW + 2 * x) * 3
                for dx in range(2):
                    q = base + dx * 3
                    acc[0] += src[q]
                    acc[1] += src[q + 1]
                    acc[2] += src[q + 2]
            out[o] = (acc[0] + 2) // 4
            out[o + 1] = (acc[1] + 2) // 4
            out[o + 2] = (acc[2] + 2) // 4
    return bytes(out)


# ---------------------------------------------------------------- helpers

def kicker(p, x, y, num, place, beat, color=RED):
    p.text("XB24", x, y, str(num), RED)
    px = x + p.text_w("XB24", str(num)) + 6
    p.text("XB24", px, y, place, color)
    p.text("XB24", px + p.text_w("XB24", place) + 8, y, beat, GREY)


def headline(p, x, y, w, s, fname="SB36", lh=21, maxlines=2):
    lines = p.wrap(fname, s, w)[:maxlines]
    for i, ln in enumerate(lines):
        p.text(fname, x, y + (i + 1) * lh - 6, ln, INK)
    return y + len(lines) * lh


def deck(p, x, y, w, s, fname="R25", lh=15, maxlines=3):
    lines = p.wrap(fname, s, w)[:maxlines]
    for i, ln in enumerate(lines):
        p.text(fname, x, y + (i + 1) * lh - 4, ln, (52, 48, 42))
    return y + len(lines) * lh


def flag_us(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (178, 34, 52))
    for i in range(7):
        p.fill_rect(x, y + i * h // 7, x + w, y + (i + 1) * h // 7,
                    WHITE if i % 2 else (178, 34, 52))
    p.fill_rect(x, y, x + w * 2 // 5, y + h * 4 // 7, NAVY_D)


def flag_cn(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (222, 41, 16))
    p.circle(x + w // 5, y + h // 4, max(1, h // 8), (255, 222, 0))


def flag_ru(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h // 3, WHITE)
    p.fill_rect(x, y + h // 3, x + w, y + 2 * h // 3, (0, 57, 166))
    p.fill_rect(x, y + 2 * h // 3, x + w, y + h, (213, 0, 50))


def flag_gb(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (0, 36, 125))
    p.fill_rect(x, y + h // 3, x + w, y + 2 * h // 3, WHITE)
    p.fill_rect(x + w // 3, y, x + 2 * w // 3, y + h, WHITE)
    p.fill_rect(x, y + h * 2 // 5, x + w, y + h * 3 // 5, (204, 0, 0))
    p.fill_rect(x + w * 2 // 5, y, x + w * 3 // 5, y + h, (204, 0, 0))


def skyline(p, x, y, w, h, c, seed=7):
    """Deterministic blocky skyline silhouette inside (x, y, w, h)."""
    bx = x
    n = 0
    while bx < x + w:
        bw = 14 + ((seed * 13 + n * 29) % 26)
        bh = h // 3 + ((seed * 7 + n * 41) % (2 * h // 3))
        p.fill_rect(bx, y + h - bh, min(x + w, bx + bw), y + h, c)
        if (n * 7 + seed) % 3 == 0:
            p.fill_rect(bx + bw // 3, y + h - bh - 6,
                        bx + 2 * bw // 3, y + h - bh, c)
        bx += bw + 3
        n += 1


# ---------------------------------------------------------------- scenes
# Each scene draws inside (x, y, w, h) in display coords.

def scene_summit(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (38, 64, 110))
    skyline(p, x, y + h - 58, w, 58, (24, 40, 72), seed=3)
    p.fill_rect(x, y + h - 34, x + w, y + h, (120, 82, 52))
    p.fill_rect(x, y + h - 34, x + w, y + h - 30, (150, 108, 66))
    suits = [(30, 52, 96), (24, 24, 24), (30, 52, 96)]
    flags = [flag_us, flag_cn, flag_ru]
    names = ["TRUMP", "XI", "PUTIN"]
    for i in range(3):
        cx = x + w * (0.20 + 0.30 * i)
        p.poly([(cx - 26, y + h - 34), (cx + 26, y + h - 34),
                (cx + 18, y + h - 78), (cx - 18, y + h - 78)], suits[i])
        p.fill_rect(cx - 4, y + h - 76, cx + 4, y + h - 40, WHITE)
        p.poly([(cx - 5, y + h - 74), (cx + 5, y + h - 74),
                (cx, y + h - 52)], RED)
        p.circle(cx, y + h - 92, 15, (232, 196, 160))
        p.fill_rect(cx - 15, y + h - 106, cx + 15, y + h - 100, (90, 70, 50))
        fx = cx - 13
        p.fill_rect(fx + 12, y + h - 30, fx + 14, y + h - 12, (220, 220, 210))
        flags[i](p, fx, y + h - 30, 26, 17)
        p.fill_rect(cx - 24, y + h - 12, cx + 24, y + h - 2, CREAM)
        p.centred("XB22", cx, y + h - 4, names[i], INK)


def scene_court(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (233, 224, 200))
    p.fill_rect(x + w // 8, y + 18, x + 7 * w // 8, y + h - 14, (146, 74, 52))
    p.poly([(x + w // 8 - 6, y + 20), (x + 7 * w // 8 + 6, y + 20),
            (x + w // 2, y + 2)], (120, 58, 40))
    for i in range(4):
        cx = x + w * (0.22 + 0.18 * i)
        p.fill_rect(cx - 6, y + 22, cx + 6, y + h - 16, (240, 232, 212))
    p.fill_rect(x + w // 8, y + h - 16, x + 7 * w // 8, y + h - 10,
                (120, 58, 40))
    # scales of justice, foreground right
    sx = x + w - 52
    p.fill_rect(sx - 2, y + 34, sx + 2, y + h - 8, (52, 44, 34))
    p.fill_rect(sx - 30, y + 36, sx + 30, y + 40, (52, 44, 34))
    p.circle(sx, y + 32, 5, GOLD)
    for dx in (-28, 28):
        p.line(sx + dx, y + 40, sx + dx - 10, y + 58, (52, 44, 34), 1)
        p.line(sx + dx, y + 40, sx + dx + 10, y + 58, (52, 44, 34), 1)
        p.poly([(sx + dx - 12, y + 58), (sx + dx + 12, y + 58),
                (sx + dx, y + 70)], GOLD)
    p.fill_rect(x + 8, y + 8, x + 66, y + 36, RED)
    p.centred("XB26", x + 37, y + 32, "9\u20136", WHITE)


def scene_cop31(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (16, 74, 74))
    p.circle(x + 62, y + h // 2, 44, (52, 130, 190))
    p.poly([(x + 34, y + h // 2 - 18), (x + 52, y + h // 2 - 30),
            (x + 66, y + h // 2 - 12), (x + 52, y + h // 2 + 2)],
           (74, 160, 90))
    p.poly([(x + 58, y + h // 2 + 8), (x + 84, y + h // 2 + 4),
            (x + 92, y + h // 2 + 24), (x + 66, y + h // 2 + 30)],
           (74, 160, 90))
    p.poly([(x + 84, y + h // 2 - 26), (x + 102, y + h // 2 - 18),
            (x + 98, y + h // 2 - 2), (x + 84, y + h // 2 - 8)],
           (74, 160, 90))
    # thermometer
    tx = x + w - 46
    p.fill_rect(tx, y + 10, tx + 14, y + h - 34, WHITE)
    p.fill_rect(tx + 3, y + h - 52, tx + 11, y + h - 34, RED)
    p.circle(tx + 7, y + h - 26, 13, RED)
    p.circle(tx + 7, y + h - 26, 8, (255, 120, 110))
    p.text("XB24", x + 116, y + 30, "FOSSIL", WHITE)
    p.text("XB24", x + 116, y + 50, "FUELS", WHITE)
    p.line(x + 112, y + 24, x + 178, y + 24, RED, 2)
    p.line(x + 112, y + 44, x + 178, y + 44, RED, 2)
    p.fill_rect(x + 116, y + 66, x + 168, y + 92, RED)
    p.centred("XB24", x + 142, y + 88, "CUT", WHITE)


def scene_gta(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h // 2, (48, 16, 84))
    p.fill_rect(x, y + h // 2, x + w, y + h, (24, 10, 46))
    p.circle(x + w - 52, y + 34, 24, (255, 140, 60))
    skyline(p, x, y + h - 74, w, 52, (12, 6, 28), seed=11)
    for wx in range(x + 8, x + w - 8, 26):
        if (wx // 26) % 2 == 0:
            p.fill_rect(wx, y + h - 62, wx + 4, y + h - 56, (255, 220, 90))
    # palm
    for px in (x + 26, x + w - 30):
        p.line(px, y + h - 22, px + 6, y + h - 62, (40, 90, 40), 2)
        for dx, dy in ((-16, -8), (-10, -16), (0, -18), (10, -14), (16, -6)):
            p.line(px + 6, y + h - 62, px + 6 + dx, y + h - 62 + dy,
                   (30, 120, 60), 2)
    # pink car
    cx, cy = x + w // 2 - 34, y + h - 26
    p.poly([(cx, cy), (cx + 68, cy), (cx + 62, cy - 12), (cx + 8, cy - 12)],
           (255, 80, 170))
    p.poly([(cx + 14, cy - 12), (cx + 54, cy - 12), (cx + 46, cy - 22),
            (cx + 22, cy - 22)], (255, 150, 205))
    p.circle(cx + 16, cy, 7, INK)
    p.circle(cx + 52, cy, 7, INK)
    p.text("SB52", x + 12, y + 44, "VI", WHITE)


def scene_ipo(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (10, 28, 52))
    bars = [(0, 12, 10, (52, 180, 90)), (1, 16, 14, (52, 180, 90)),
            (2, 14, 12, (230, 70, 70)), (3, 20, 18, (52, 180, 90)),
            (4, 24, 22, (52, 180, 90)), (5, 22, 20, (230, 70, 70)),
            (6, 30, 26, (52, 180, 90))]
    for i, bh, bw, c in bars:
        bx = x + 12 + i * 26
        p.fill_rect(bx, y + h - 10 - bh, bx + bw, y + h - 10, c)
    p.line(x + 12, y + h - 38, x + w - 12, y + 24, (255, 220, 90), 2)
    p.text("XB46", x + 12, y + 34, "ANT", WHITE)
    p.text("XB26", x + 12, y + 52, "$83", (120, 220, 140))


def scene_cyclone(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (70, 140, 185))
    p.poly([(x + w, y), (x + w, y + h), (x + w - 52, y + h),
            (x + w - 30, y + h // 2), (x + w - 44, y)], (222, 196, 150))
    cx, cy = x + w // 2 - 14, y + h // 2
    for r in (34, 26, 18, 10):
        p.ring(cx, cy, r, WHITE, 3)
    p.circle(cx, cy, 6, WHITE)
    for rx in range(x + 6, x + w - 60, 18):
        p.line(rx, y + 8, rx - 5, y + 22, (200, 225, 240), 1)
    p.fill_rect(x + 8, y + h - 22, x + 96, y + h - 6, WHITE)
    p.centred("XB22", x + 52, y + h - 9, "145 km/h", RED)


def scene_bridge(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (214, 228, 238))
    p.fill_rect(x, y + h - 26, x + w, y + h, (70, 130, 180))
    p.fill_rect(x, y + h - 44, x + w, y + h - 38, (90, 90, 96))
    for bx in range(x + 10, x + w - 10, 34):
        p.fill_rect(bx, y + h - 38, bx + 5, y + h - 26, (90, 90, 96))
    p.poly([(x + w // 2 - 70, y + h - 44), (x + w // 2 + 70, y + h - 44),
            (x + w // 2, y + h - 74)], (110, 110, 118))
    ex, ey = x + w // 2 + 26, y + h - 66
    for ang in range(0, 360, 45):
        dx = int(20 * math.cos(math.radians(ang)))
        dy = int(20 * math.sin(math.radians(ang)))
        p.line(ex, ey, ex + dx, ey + dy, (255, 140, 30), 3)
    p.circle(ex, ey, 10, (255, 190, 60))
    p.circle(ex - 12, ey - 8, 8, (120, 120, 120))
    p.circle(ex + 12, ey - 12, 9, (150, 150, 150))


def scene_greenland(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (178, 212, 232))
    p.poly([(x, y + h), (x + w // 3, y + 18), (x + 2 * w // 3, y + h)],
           (240, 246, 250))
    p.poly([(x + w // 3, y + h), (x + 2 * w // 3, y + 8),
            (x + w, y + h)], (200, 220, 235))
    p.poly([(x + w // 3, y + 18), (x + w // 3 + 26, y + 44),
            (x + w // 3 - 14, y + 44)], WHITE)
    for fx, fl in ((x + 18, "dk"), (x + w - 44, "us")):
        p.fill_rect(fx + 12, y + 26, fx + 14, y + 66, (90, 80, 70))
        if fl == "dk":
            p.fill_rect(fx, y + 26, fx + 26, y + 44, (200, 20, 40))
            p.fill_rect(fx, y + 33, fx + 26, y + 37, WHITE)
            p.fill_rect(fx + 8, y + 26, fx + 12, y + 44, WHITE)
        else:
            flag_us(p, fx, y + 26, 26, 17)
    p.fill_rect(x + w - 62, y + h - 24, x + w - 8, y + h - 6, RED)
    p.centred("XB22", x + w - 35, y + h - 9, "109\u20130", WHITE)


def scene_jobs(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, CREAM)
    p.text("XB46", x + 10, y + 32, "4.9%", RED)
    p.text("XB22", x + 10, y + 52, "JOBLESS", INK)
    bars = [(10, GREY), (14, GREY), (20, RED)]
    for i, (bh, c) in enumerate(bars):
        bx = x + 16 + i * 52
        p.fill_rect(bx, y + h - 6 - bh, bx + 34, y + h - 6, c)


def scene_colombia(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (240, 226, 190))
    skyline(p, x, y + h - 66, w, 30, (120, 100, 70), seed=5)
    p.fill_rect(x, y + h - 38, x + w, y + h, (200, 180, 140))
    heads = [(0.12, (232, 196, 160)), (0.28, (200, 160, 120)),
             (0.44, (232, 196, 160)), (0.60, (180, 140, 105)),
             (0.76, (232, 196, 160)), (0.90, (200, 160, 120))]
    for fx, skin in heads:
        cx = x + int(w * fx)
        p.circle(cx, y + h - 30, 10, skin)
        p.poly([(cx - 14, y + h), (cx + 14, y + h), (cx + 10, y + h - 22),
                (cx - 10, y + h - 22)],
               (52, 90, 140) if int(fx * 100) % 2 else (160, 40, 40))
    p.fill_rect(x + w // 2 - 34, y + 8, x + w // 2 + 34, y + 26, WHITE)
    p.rect(x + w // 2 - 34, y + 8, x + w // 2 + 34, y + 26, INK, 1)
    p.centred("XB22", x + w // 2, y + 24, "PARO", INK)


def scene_florida(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h // 2, (150, 170, 190))
    for rx in range(x + 6, x + w - 6, 16):
        p.line(rx, y + 6, rx - 4, y + 18, (220, 230, 240), 1)
    p.fill_rect(x + 24, y + h - 52, x + w - 24, y + h - 30, (240, 220, 180))
    p.poly([(x + 18, y + h - 52), (x + w // 2, y + h - 72),
            (x + w - 18, y + h - 52)], (150, 60, 50))
    p.fill_rect(x + w // 2 - 8, y + h - 40, x + w // 2 + 8, y + h - 30,
                (90, 60, 40))
    p.fill_rect(x, y + h - 30, x + w, y + h, (60, 120, 180))
    p.fill_rect(x + 14, y + h - 22, x + w - 14, y + h - 16, (140, 190, 225))
    p.fill_rect(x + w - 58, y + 8, x + w - 10, y + 26, WHITE)
    p.centred("XB22", x + w - 34, y + 24, "CLOSED", RED)


def scene_ebola(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (110, 24, 28))
    p.text("XB46", x + 10, y + 34, "11,000+", WHITE)
    p.text("XB22", x + 12, y + 56, "CASES", (255, 180, 170))
    for vx, vy, vr in ((x + w - 34, y + 22, 10), (x + w - 62, y + 48, 8),
                       (x + w - 26, y + 62, 7)):
        p.circle(vx, vy, vr, (200, 60, 60))
        for ang in range(0, 360, 60):
            import math
            dx = int((vr + 5) * math.cos(math.radians(ang)))
            dy = int((vr + 5) * math.sin(math.radians(ang)))
            p.line(vx, vy, vx + dx, vy + dy, (200, 60, 60), 1)


def scene_indonesia(p, x, y, w, h):
    p.fill_rect(x, y, x + w, y + h, (226, 214, 186))
    p.fill_rect(x + 16, y + 34, x + w - 16, y + h - 12, (180, 150, 110))
    p.circle(x + w // 2, y + 30, 18, (140, 110, 70))
    p.fill_rect(x + w // 2 - 18, y + 30, x + w // 2 + 18, y + 38,
                (140, 110, 70))
    for i in range(5):
        cx = x + 30 + i * 32
        p.fill_rect(cx - 5, y + 40, cx + 5, y + h - 14, (245, 238, 220))
    p.fill_rect(x + 16, y + h - 14, x + w - 16, y + h - 8, (140, 110, 70))
    p.fill_rect(x + w - 66, y + h - 30, x + w - 10, y + h - 8, WHITE)
    p.centred("XB22", x + w - 38, y + h - 11, "18 YRS", RED)


SCENES = [scene_summit, scene_court, scene_cop31, scene_gta, scene_ipo,
          scene_cyclone, scene_bridge, scene_greenland, scene_jobs,
          scene_colombia, scene_florida, scene_ebola, scene_indonesia]


# ---------------------------------------------------------------- stories

LEADS = [
    ("1", "SHENZHEN", "SUMMIT",
     "First Trump\u2013Xi\u2013Putin summit",
     "The three leaders meet on the APEC sidelines; agenda: nuclear "
     "arms, Ukraine, Iran, trade, AI. \u2014 Reuters"),
    ("2", "THE HAGUE", "JUSTICE",
     "World Court finds Myanmar guilty",
     "ICJ rules 9\u20136 \u2014 the first state ever held responsible; "
     "~10,000 Rohingya killed in 2017; reparations ordered. "
     "\u2014 UN News"),
    ("3", "ANTALYA", "CLIMATE",
     "COP31 draft drops fossil fuels",
     "The slimmed text, due Friday, names no fossil fuel; the "
     "$120bn aid goal is cut. \u2014 Reuters"),
]

CARDS = [
    ("4", "VICE CITY", "GAMES",
     "GTA VI goes on sale after 13 years",
     "Vice City returns; $1.65bn pre-orders. \u2014 ABC"),
    ("5", "NEW YORK", "MARKETS",
     "Anthropic debuts in record IPO",
     "Priced $83; raised $81.3bn; value ~$1.5tn. \u2014 AP"),
    ("6", "ODISHA", "STORM",
     "Cyclone Akvan nears India's coast",
     "Landfall ~20 Nov; winds ~145 km/h. \u2014 IMD"),
    ("7", "CRIMEA", "WAR",
     "Ukraine hits Crimean Bridge",
     "Third strike in a week halts trains. \u2014 Euronews"),
    ("8", "GREENLAND", "SECURITY",
     "Denmark backs Arctic pact",
     "Parliament votes 109\u20130; more US bases. \u2014 AP"),
    ("9", "CANBERRA", "ECONOMY",
     "Australia's jobless rate hits 4.9%",
     "Five-year high; 43,500 jobs lost in October. \u2014 ABS"),
    ("10", "BOGOT\u00c1", "LABOUR",
     "Colombia unions hold strike",
     "Marches in three cities against the bill. \u2014 Infobae"),
    ("11", "FLORIDA", "WEATHER",
     "Floods shut Florida schools",
     "Schools shut a second day; more rain forecast. \u2014 ABC"),
    ("12", "DR CONGO", "HEALTH",
     "Ebola toll climbs in DR Congo",
     "Outbreak tops 11,000 cases, 5,400 deaths. \u2014 UN"),
    ("13", "JAKARTA", "LAW",
     "Indonesia passes asset-seizure law",
     "After 18 years, the state may seize assets. \u2014 AP"),
]

ALSO = [
    ("BEIJING", "China, Korea agree to expand cultural exchange"),
    ("BRUSSELS", "EU greenlights Indonesia trade pact"),
    ("JERUSALEM", "Herzog taps Eisenkot to form a government"),
    ("TALLINN", "Estonia to shut Russia road crossings 1 Dec"),
    ("CARACAS", "US details $12bn in Venezuelan oil revenue"),
    ("NAYPYIDAW", "Myanmar's president rethinks ties with ASEAN"),
    ("SANAA", "Houthis seize Red Sea coastal positions"),
    ("GAZA", "Heavy rain displaces 46,000+ households"),
    ("NEW YORK", "Nasdaq +0.42%; AMD +5.31%, Amazon +3.82%"),
    ("WASHINGTON", "Fed minutes: more rate hikes expected"),
    ("SANTA CLARA", "Nvidia revenue $115.8bn, up 103%"),
    ("SAN FRANCISCO", "Genesis AI raises $500m for factory robots"),
    ("NAIROBI", "Drought deepens Kenya's milk shortage"),
    ("MONACO", "Marathon champion Jepchirchir banned 3 years"),
    ("WELLINGTON", "India\u2013NZ First Test begins"),
    ("SEOUL", "551,864 sit the Suneung college exam"),
    ("PARIS", "French left splits over a M\u00e9lenchon pact"),
    ("YONGBYON", "IAEA: N. Korea expanded uranium enrichment"),
]

REGIONS = [
    ("ASIA", 8, (163, 22, 33)),
    ("MIDDLE EAST", 3, (192, 86, 33)),
    ("EUROPE", 5, (31, 58, 95)),
    ("AFRICA", 3, (46, 125, 50)),
    ("AMERICAS", 8, (106, 27, 154)),
    ("OCEANIA", 2, (0, 131, 143)),
    ("GLOBAL", 2, (85, 85, 85)),
]

NUMBERS = [
    ("3", "presidents at one table"),
    ("9\u20136", "World Court genocide vote"),
    ("$120bn", "aid goal cut at COP31"),
    ("$81.3bn", "Anthropic's record IPO"),
    ("109\u20130", "Arctic pact vote"),
    ("4.9%", "Australian jobless rate"),
]

# (lat, lon) of stories 1-13, for the map pins
PINS = [(22.5, 114.0), (51.0, 2.0), (36.9, 30.7), (25.5, -79.5),
        (40.7, -74.0), (20.0, 86.0), (45.0, 34.0), (58.0, 18.0),
        (-35.3, 149.1), (4.7, -74.0), (28.5, -83.0), (-2.9, 23.7),
        (-6.2, 106.8)]

CONTINENTS = [
    [(-168, 66), (-140, 70), (-120, 71), (-95, 80), (-80, 73), (-60, 60),
     (-55, 47), (-70, 42), (-75, 35), (-80, 26), (-90, 21), (-97, 16),
     (-105, 20), (-115, 28), (-125, 40), (-125, 49), (-145, 60),
     (-168, 66)],
    [(-80, 10), (-72, 12), (-60, 8), (-50, 0), (-40, -5), (-35, -10),
     (-40, -20), (-50, -30), (-60, -38), (-70, -50), (-73, -40),
     (-72, -20), (-80, -5), (-80, 10)],
    [(-17, 15), (-10, 30), (0, 36), (10, 37), (20, 32), (32, 31),
     (35, 28), (40, 15), (48, 11), (51, 10), (40, 0), (35, -15),
     (30, -25), (20, -35), (15, -30), (12, -18), (9, 0), (0, 5),
     (-8, 5), (-17, 15)],
    [(0, 36), (10, 38), (20, 40), (30, 36), (36, 36), (40, 38),
     (48, 42), (55, 45), (60, 50), (70, 55), (80, 60), (90, 65),
     (100, 70), (120, 72), (140, 72), (160, 70), (178, 66), (170, 60),
     (160, 55), (150, 50), (140, 45), (130, 40), (127, 35), (122, 30),
     (115, 22), (108, 18), (105, 10), (100, 8), (95, 15), (90, 22),
     (85, 20), (80, 13), (75, 8), (70, 20), (65, 25), (60, 25),
     (55, 26), (50, 29), (45, 30), (40, 36), (35, 36), (30, 36),
     (25, 38), (20, 40), (15, 38), (10, 37), (5, 36), (0, 36)],
    [(113, -22), (114, -30), (115, -35), (120, -34), (130, -32),
     (137, -35), (140, -38), (145, -38), (150, -37), (153, -32),
     (150, -25), (146, -19), (142, -11), (136, -12), (132, -11),
     (126, -14), (122, -17), (118, -20), (113, -22)],
]


def draw_map(p, x0, y0, w, h):
    p.fill_rect(x0, y0, x0 + w, y0 + h, SEA)
    p.rect(x0, y0, x0 + w, y0 + h, INK, 1)

    def proj(lon, lat):
        return (x0 + 4 + (lon + 180) / 360.0 * (w - 8),
                y0 + 4 + (75 - lat) / 130.0 * (h - 8))

    for poly in CONTINENTS:
        p.poly([proj(lon, lat) for lon, lat in poly], LAND)
    for i, (lat, lon) in enumerate(PINS, 1):
        cx, cy = proj(lon, lat)
        p.circle(int(cx), int(cy), 7, RED)
        p.centred("XB20", int(cx), int(cy) + 4, str(i), WHITE)


# ---------------------------------------------------------------- build

def build(path):
    p = Page()
    # --- top bar
    p.text("XB22", 14, 24, "THE WORLD IN ONE DAY", RED)
    right = "31 STORIES \u00b7 EVERY CONTINENT \u00b7 ALL FROM THIS ONE DAY"
    p.text("R24", 1010 - p.text_w("R24", right), 24, right, GREY)
    p.hline(14, 1010, 30, INK, 2)
    # --- masthead
    p.text("SB116", 14, 96, "Thursday 19 November 2026", INK)
    p.text("SB38", 14, 122,
           "Trump, Xi and Putin share one table \u00b7 Myanmar guilty "
           "\u00b7 COP31 drops fossil fuels", RED, shear=0.18)
    # --- region strip (fixed widths, labels must fit)
    rx = 14
    widths = [170, 150, 140, 110, 170, 130, 126]
    for (name, count, col), rw in zip(REGIONS, widths):
        p.fill_rect(rx, 132, rx + rw, 152, col)
        p.centred("XB22", rx + rw // 2, 149, "%s %d" % (name, count), WHITE)
        rx += rw
    # --- numbers strip
    for i, (num, label) in enumerate(NUMBERS):
        cx = 14 + i * 166 + 83
        p.centred("XB46", cx, 182, num, INK)
        p.centred("R24", cx, 198, label, GREY)
        if i:
            p.vline(14 + i * 166, 158, 200, LINE, 1)
    p.hline(14, 1010, 204, INK, 2)
    # --- leads
    for i, (num, place, beat, head, dk) in enumerate(LEADS):
        x = 14 + i * 332
        SCENES[i](p, x, 210, 320, 134)
        p.rect(x, 210, x + 320, 344, INK, 1)
        kicker(p, x, 362, num, place, beat)
        headline(p, x, 368, 320, head, "SB52", 30, 2)
        deck(p, x, 428, 320, dk, "R29", 17, 3)
    # --- cards (2 rows x 5)
    for i, (num, place, beat, head, dk) in enumerate(CARDS):
        row, col = divmod(i, 5)
        x = 14 + col * 201
        y = 482 + row * 174
        SCENES[3 + i](p, x, y, 191, 76)
        p.rect(x, y, x + 191, y + 76, INK, 1)
        kicker(p, x, y + 92, num, place, beat)
        headline(p, x, y + 98, 191, head, "SB36", 21, 2)
        deck(p, x, y + 140, 191, dk, "R25", 15, 2)
    # --- bottom: map + also-list
    p.text("XB22", 14, 848, "WHERE IT HAPPENED", INK)
    draw_map(p, 14, 854, 330, 96)
    p.text("XB22", 356, 848, "ALSO ON THURSDAY 19 NOVEMBER 2026", RED)
    for i, (place, txt) in enumerate(ALSO):
        col = i // 9
        row = i % 9
        x = 356 + col * 327
        y = 861 + row * 11
        p.text("XB20", x, y, "%d" % (i + 1), RED)
        px = x + 18
        p.text("XB20", px, y, place, INK)
        p.text("R20", px + p.text_w("XB20", place) + 5, y, txt, (52, 48, 42))
    # --- markets strip
    p.fill_rect(14, 958, 1010, 980, NAVY_D)
    mx = 24
    mx += p.text("XB26", mx, 976, "MARKETS \u2014 ", WHITE)
    p.text("R25", mx, 976,
           "S&P \u22120.23% 7,323.63 \u00b7 Dow \u22121.11% 50,198 \u00b7 "
           "Nasdaq +0.42% 24,429.88 \u00b7 Gold ~$3,726 \u00b7 Brent ~$92 \u00b7 "
           "WTI ~$82 \u00b7 Bitcoin ~$63,478", WHITE)
    # --- date check
    p.rect(14, 984, 1010, 1010, RED, 1)
    p.text("R24", 22, 997,
           "DATE CHECK \u2713  First reported WEDNESDAY 18 NOV, so NOT on "
           "this page: Jeffries nominated for Speaker (251\u201311) \u00b7 "
           "Voyager 1 crosses one light-day \u00b7", INK)
    p.text("R24", 22, 1009,
           "the EU's proposed \u20ac45bn Ukraine loan \u00b7 Pew: Islam set "
           "to be the largest religion by 2035 \u00b7 the first COP31 draft "
           "(Monday).", INK)
    # --- footer
    p.text("R24", 14, 1021,
           "All stories happened, or were first reported, on Thursday 19 "
           "November 2026 \u00b7 Sources: Reuters, AP, AFP, BBC, Al Jazeera, "
           "UN News, ABS, IMD", GREY)
    rgb = downsample(p)
    data = encode_png(rgb, W, H)
    with open(path, "wb") as f:
        f.write(data)
    return len(data), 31


if __name__ == "__main__":
    import sys as _sys
    out = _sys.argv[1] if len(_sys.argv) > 1 else "poster.png"
    print(build(out))
