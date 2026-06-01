#!/usr/bin/env python3
"""Generate 24-bit uncompressed BMP assets for the P2 servo-calibration DEBUG PLOT display.

Outputs (written next to the .spin2 source, in src/):
  cal_bg.bmp    480x240  - background panel: title, value box (black), labels, instructions
  cal_font.bmp  480x60   - digit/sign font strip, 12 cells of 40x60: "0123456789-+"

BMP format produced by Pillow for an 'RGB' image is 24-bit, uncompressed (BI_RGB), no alpha --
exactly what the P2 DEBUG `LAYER` command requires.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "src"))

# ---- shared palette ----
BG      = (28, 30, 40)      # panel background
BOX     = (0, 0, 0)         # value box / font-cell background (must match for seamless blits)
GLYPH   = (40, 230, 90)     # bright green digits
LABEL   = (210, 215, 225)   # light gray text
ACCENT  = (90, 160, 255)    # blue accents

# ---- font cell geometry (keep in sync with test_cal_display.spin2) ----
CELL_W, CELL_H = 40, 60
GLYPHS = "0123456789-+"     # index 0..9 digits, 10='-', 11='+'

# ---- value box geometry on the background (keep in sync with the .spin2) ----
BOX_X, BOX_Y, BOX_W, BOX_H = 160, 90, 140, 64


def load_font(size):
    for path in ("/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/Library/Fonts/Arial.ttf",
                 "/System/Library/Fonts/SFNS.ttf"):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def centered(draw, cx, cy, text, font, fill):
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (r - l) / 2 - l, cy - (b - t) / 2 - t), text, font=font, fill=fill)


def make_background():
    img = Image.new("RGB", (480, 240), BG)
    d = ImageDraw.Draw(img)
    title = load_font(22)
    sub = load_font(18)
    small = load_font(15)

    centered(d, 240, 22, "P2 Robot Dog  -  Servo Calibration", title, LABEL)
    centered(d, 240, 52, "FL coxa  (PCA9685 ch 4)", sub, ACCENT)

    # value box (black) + units label
    d.rectangle([BOX_X, BOX_Y, BOX_X + BOX_W, BOX_Y + BOX_H], fill=BOX)
    d.text((BOX_X + BOX_W + 12, BOX_Y + 20), "deg", font=sub, fill=LABEL)
    centered(d, 240, BOX_Y - 12, "trim", small, LABEL)

    centered(d, 240, 196, "a / d : trim  -1 / +1 deg      s : save (dump to log)", small, LABEL)
    centered(d, 240, 218, "(robot lifted; nudge until the leg matches the others)", small, (140, 145, 160))
    img.save(os.path.join(OUT, "cal_bg.bmp"))
    return img


def make_font_strip():
    img = Image.new("RGB", (CELL_W * len(GLYPHS), CELL_H), BOX)
    d = ImageDraw.Draw(img)
    glyph_font = load_font(52)
    for i, ch in enumerate(GLYPHS):
        centered(d, i * CELL_W + CELL_W // 2, CELL_H // 2, ch, glyph_font, GLYPH)
    img.save(os.path.join(OUT, "cal_font.bmp"))
    return img


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_background()
    make_font_strip()
    print("wrote:", os.path.join(OUT, "cal_bg.bmp"))
    print("wrote:", os.path.join(OUT, "cal_font.bmp"))
    print(f"font cells: {CELL_W}x{CELL_H}, glyphs='{GLYPHS}'")
    print(f"value box : x={BOX_X} y={BOX_Y} w={BOX_W} h={BOX_H}")
