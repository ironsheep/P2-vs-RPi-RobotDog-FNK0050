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


# =================================================================================================
#  Full calibration panel (single-joint navigator) -- assets + layout
# =================================================================================================
# Window 480x240. Reuses cal_font.bmp (40x60 digits) for the trim value. Leg name and joint name
# are blitted from strips so one background serves all 13 joints. Layout constants below are the
# single source of truth -- the script prints a Spin2 CON block to paste into the .spin2.

PANEL_W, PANEL_H = 480, 288
LEG_NAMES   = ["FRONT-LEFT", "BACK-LEFT", "BACK-RIGHT", "FRONT-RIGHT", "HEAD"]
JOINT_NAMES = ["SHOULDER", "THIGH", "KNEE", "PAN", ""]   # index 4 = blank
LEG_CELL_W,  LEG_CELL_H  = 220, 30
JNT_CELL_W,  JNT_CELL_H  = 170, 30
LEG_SLOT_X,  LEG_SLOT_Y  = 28, 48     # where the leg-name cell is blitted
JNT_SLOT_X,  JNT_SLOT_Y  = 264, 48    # where the joint-name cell is blitted
PBOX_X, PBOX_Y, PBOX_W, PBOX_H = 160, 100, 140, 64      # trim value box
PSLOT_SIGN, PSLOT_TENS, PSLOT_ONES = 170, 210, 250      # 3 digit slots (CELL_W=40 apart)
PDIG_Y = 102
STEP_BOX_X, STEP_BOX_Y, STEP_BOX_W, STEP_BOX_H = 250, 178, 44, 64   # step indicator box (1 digit)
STEP_DIG_X, STEP_DIG_Y = 252, 180     # where the step digit is blitted


def make_panel_bg():
    img = Image.new("RGB", (PANEL_W, PANEL_H), BG)
    d = ImageDraw.Draw(img)
    title = load_font(22)
    lab = load_font(16)
    small = load_font(15)
    centered(d, PANEL_W // 2, 16, "P2 Robot Dog  -  Servo Calibration", title, LABEL)
    centered(d, PBOX_X + PBOX_W // 2, 90, "trim", small, LABEL)
    d.rectangle([PBOX_X, PBOX_Y, PBOX_X + PBOX_W, PBOX_Y + PBOX_H], fill=BOX)
    d.text((PBOX_X + PBOX_W + 10, PBOX_Y + 22), "deg", font=lab, fill=LABEL)
    # step indicator: black box (so the black-backed font cell blends) + labels
    d.rectangle([STEP_BOX_X, STEP_BOX_Y, STEP_BOX_X + STEP_BOX_W, STEP_BOX_Y + STEP_BOX_H], fill=BOX)
    d.text((STEP_BOX_X - 110, STEP_BOX_Y + 22), "STEP =", font=lab, fill=LABEL)
    d.text((STEP_BOX_X + STEP_BOX_W + 8, STEP_BOX_Y + 22), "deg", font=lab, fill=LABEL)
    centered(d, PANEL_W // 2, 250, "a / d : down / up      1 : step 1 deg      5 : step 5 deg", small, LABEL)
    centered(d, PANEL_W // 2, 270, "j : joint    l : leg    c : center ALL    s : save    p : print ALL", small, ACCENT)
    img.save(os.path.join(OUT, "panel_bg.bmp"))


def make_word_strip(names, cell_w, cell_h, fname, color=ACCENT, size=18):
    img = Image.new("RGB", (cell_w, cell_h * len(names)), BG)
    d = ImageDraw.Draw(img)
    f = load_font(size)
    for i, name in enumerate(names):
        if name:
            centered(d, cell_w // 2, i * cell_h + cell_h // 2, name, f, color)
    img.save(os.path.join(OUT, fname))


def emit_spin2_con():
    print("\n--- paste into test_cal_full.spin2 CON (layout; matches the BMPs) ---")
    print(f"  PANEL_W = {PANEL_W}")
    print(f"  PANEL_H = {PANEL_H}")
    print(f"  LEG_CELL_W = {LEG_CELL_W}")
    print(f"  LEG_CELL_H = {LEG_CELL_H}")
    print(f"  JNT_CELL_W = {JNT_CELL_W}")
    print(f"  JNT_CELL_H = {JNT_CELL_H}")
    print(f"  LEG_SLOT_X = {LEG_SLOT_X}")
    print(f"  LEG_SLOT_Y = {LEG_SLOT_Y}")
    print(f"  JNT_SLOT_X = {JNT_SLOT_X}")
    print(f"  JNT_SLOT_Y = {JNT_SLOT_Y}")
    print(f"  PBOX_X = {PBOX_X}")
    print(f"  PBOX_Y = {PBOX_Y}")
    print(f"  PBOX_W = {PBOX_W}")
    print(f"  PBOX_H = {PBOX_H}")
    print(f"  PSLOT_SIGN = {PSLOT_SIGN}")
    print(f"  PSLOT_TENS = {PSLOT_TENS}")
    print(f"  PSLOT_ONES = {PSLOT_ONES}")
    print(f"  PDIG_Y = {PDIG_Y}")
    print(f"  STEP_DIG_X = {STEP_DIG_X}")
    print(f"  STEP_DIG_Y = {STEP_DIG_Y}")
    print(f"  CELL_W = {CELL_W}")
    print(f"  CELL_H = {CELL_H}")
    print("--- leg-name strip rows (srcY = idx*LEG_CELL_H): " + ", ".join(f"{i}={n}" for i, n in enumerate(LEG_NAMES)))
    print("--- joint-name strip rows (srcY = idx*JNT_CELL_H): " + ", ".join(f"{i}={n or 'blank'}" for i, n in enumerate(JOINT_NAMES)))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_background()
    make_font_strip()
    make_panel_bg()
    make_word_strip(LEG_NAMES, LEG_CELL_W, LEG_CELL_H, "panel_legs.bmp")
    make_word_strip(JOINT_NAMES, JNT_CELL_W, JNT_CELL_H, "panel_joints.bmp", color=GLYPH)
    for f in ("cal_bg.bmp", "cal_font.bmp", "panel_bg.bmp", "panel_legs.bmp", "panel_joints.bmp"):
        print("wrote:", os.path.join(OUT, f))
    print(f"font cells: {CELL_W}x{CELL_H}, glyphs='{GLYPHS}'")
    print(f"inc1 value box : x={BOX_X} y={BOX_Y} w={BOX_W} h={BOX_H}")
    emit_spin2_con()
