#!/usr/bin/env python3
"""Generate 24-bit uncompressed BMP assets for the P2 Robot Dog MOVE PANEL DEBUG PLOT display.

An interactive control panel: a grid of clickable buttons (mouse) that POST commands through the
production backend/IO mailboxes, plus a live telemetry readout (mode, battery, tilt, head, distance,
ping-seq). Companion of tools/gen_cal_assets.py; same conventions (Pillow -> 24-bit BI_RGB BMP, no
alpha; layout constants are the SINGLE SOURCE OF TRUTH and are printed as a Spin2 CON block to paste
into src/test_dog_panel.spin2).

Outputs (written next to the .spin2 source, in src/):
  dog_panel_bg.bmp   660xH  - background: title, all buttons (idle look), readout labels + black boxes, footer
  dog_btn_hi.bmp     100xN  - vertical strip of HIGHLIGHTED button cells, one per grid slot (srcY = slot*CELL_H)
  dog_font.bmp       Wx34   - readout digit/sign font strip, cells "0123456789-"
  dog_modes.bmp      WxN    - mode-name word strip (IDLE/GAITING/GESTURE/RELAXED/LOWBATT), srcY = mode*MODE_CELL_H
  dog_led_modes.bmp  WxN    - LED-mode word strip (OFF/SOLID/WIPE/CHASE/RAINBOW/CYCLE), srcY = ledMode*LED_CELL_H
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "src"))

# ---- palette ----
BG       = (24, 26, 34)        # panel background
BOX      = (0, 0, 0)           # readout value box / font-cell background (match for seamless blits)
GLYPH    = (60, 230, 110)      # bright green readout digits
LABEL    = (212, 217, 227)     # light gray text
DIM      = (140, 146, 162)     # dim gray (footer)
# category idle fills + the shared highlighted look
CAT = {
    "pose": (44, 60, 96),      # blue-gray
    "gait": (40, 84, 60),      # green-gray
    "gest": (96, 74, 36),      # amber-gray
    "head": (70, 52, 92),      # purple-gray
    "io":   (52, 52, 60),      # neutral
    "spd":  (40, 60, 70),      # teal-gray
}
BORDER   = (96, 104, 122)
HI_FILL  = (60, 230, 110)      # highlighted button fill (bright green)
HI_TEXT  = (10, 14, 12)        # dark label on the bright highlight

# ---- button grid geometry ----
MARGIN   = 15
TITLE_H  = 40
COLS, ROWS = 6, 5
CELL_W, CELL_H = 100, 40
GAP_X, GAP_Y   = 6, 8
PITCH_X, PITCH_Y = CELL_W + GAP_X, CELL_H + GAP_Y
GRID_X, GRID_Y   = MARGIN, TITLE_H
GRID_BOTTOM = GRID_Y + ROWS * PITCH_Y          # y just below the last button row
PANEL_W = MARGIN + COLS * CELL_W + (COLS - 1) * GAP_X + MARGIN   # 660

# ---- button table: (row, col, label, target, cmd, arg, category) ----
#   target "dog"/"io" -> postCommand on that object; "panel" -> handled locally (speed/toggle state)
BUTTONS = [
    (0, 0, "STAND",  "dog", "CMD_STAND",      0, "pose"),
    (0, 1, "SIT",    "dog", "CMD_SIT",        0, "pose"),
    (0, 2, "CROUCH", "dog", "CMD_CROUCH",     0, "pose"),
    (0, 3, "RELAX",  "dog", "CMD_RELAX",      0, "pose"),
    (0, 4, "STOP",   "dog", "CMD_STOP",       0, "pose"),

    (1, 0, "FWD",    "dog", "CMD_FORWARD",    0, "gait"),
    (1, 1, "BACK",   "dog", "CMD_BACKWARD",   0, "gait"),
    (1, 2, "TURN-L", "dog", "CMD_TURN_LEFT",  0, "gait"),
    (1, 3, "TURN-R", "dog", "CMD_TURN_RIGHT", 0, "gait"),
    (1, 4, "STEP-L", "dog", "CMD_STEP_LEFT",  0, "gait"),
    (1, 5, "STEP-R", "dog", "CMD_STEP_RIGHT", 0, "gait"),

    (2, 0, "HELLO",  "dog", "CMD_HELLO",      0, "gest"),
    (2, 1, "SHAKE",  "dog", "CMD_SHAKE",      0, "gest"),
    (2, 2, "SALUTE", "dog", "CMD_SALUTE",     0, "gest"),
    (2, 3, "HEAD 60",  "dog", "CMD_HEAD",    60, "head"),
    (2, 4, "HEAD 90",  "dog", "CMD_HEAD",    90, "head"),
    (2, 5, "HEAD 120", "dog", "CMD_HEAD",   120, "head"),

    (3, 0, "LED",    "io",  "IO_LED_MODE",    5, "io"),   # 5 = MODE_RAINBOW_CYCLE; toggles off in firmware
    (3, 1, "BEEP",   "io",  "IO_BUZZ_BEEP", 120, "io"),
    (3, 2, "RANGE",  "io",  "IO_RANGE_ON",    0, "io"),   # toggles ranging on/off in firmware
    (3, 3, "SLOW",   "panel", "SPEED",        5, "spd"),
    (3, 4, "NORM",   "panel", "SPEED",       15, "spd"),
    (3, 5, "FAST",   "panel", "SPEED",       30, "spd"),

    (4, 0, "DOWN",   "dog", "CMD_LIE_DOWN",   0, "pose"),
    (4, 1, "BOW",    "dog", "CMD_BOW",        0, "pose"),
    (4, 2, "PUSHUP", "dog", "CMD_PUSHUPS",    0, "gest"),
    (4, 3, "NOD",    "dog", "CMD_NOD",        0, "gest"),
    (4, 4, "SPIN",   "dog", "CMD_TURN_LEFT",  0, "gait"),   # panel-timed: TURN then auto-STOP
    (4, 5, "SPEAK",  "io",  "SPEAK",          0, "io"),     # panel-composed: buzzer bark + nod
]


def slot_of(row, col):
    return row * COLS + col


def btn_xy(row, col):
    return GRID_X + col * PITCH_X, GRID_Y + row * PITCH_Y


# ---- readout font ----
RW, RH = 22, 34
RGLYPHS = "0123456789-"        # index 0..9 digits, 10 = minus

# ---- mode word strip ----
MODE_NAMES = ["IDLE", "GAITING", "GESTURE", "RELAXED", "LOWBATT"]
MODE_CELL_W, MODE_CELL_H = 150, 30

# ---- LED-mode word strip (matches isp_led_ring MODE_OFF..MODE_RAINBOW_CYCLE, the LED button's step order) ----
LED_MODE_NAMES = ["OFF", "SOLID", "WIPE", "CHASE", "RAINBOW", "CYCLE"]
LED_CELL_W, LED_CELL_H = 150, 30        # same cell as the mode strip (holds "RAINBOW")

# ---- readout field layout (lower panel) ----
RO_Y = GRID_BOTTOM + 14        # top of readout area
COL_L_X, COL_R_X = MARGIN, 340 # two label columns
RO_ROW = 44                    # row pitch in the readout area
# each field: (key, label, col_x, row, box_w, n_slots)  -- box height fixed = RH+4
FIELDS = [
    ("mode", "MODE", COL_L_X, 0, MODE_CELL_W, 0),   # word, not digits
    ("batt", "BATT", COL_L_X, 1, RW * 4 + 8, 4),    # mV (e.g. 8123)
    ("head", "HEAD", COL_L_X, 2, RW * 3 + 8, 3),    # deg
    ("tilt", "TILT", COL_R_X, 0, RW * 7 + 8, 7),    # P -nn  R -nn  -> 7 glyph slots
    ("dist", "DIST", COL_R_X, 1, RW * 4 + 8, 4),    # mm
    ("ping", "PING", COL_R_X, 2, RW * 5 + 8, 5),    # seq
    ("led",  "LED",  COL_L_X, 3, LED_CELL_W + 6 + RW, 1),  # word (layer 5) + a 1-digit index to its right
]
LABEL_W = 56                   # gap from label to value box
BOX_H = RH + 4
PANEL_H = RO_Y + 4 * RO_ROW + 40   # 4 readout rows (left col adds LED at row 3); leave room for footer


def field_box(f):
    """Return (box_x, box_y, box_w, box_h) for a field tuple."""
    _, _, col_x, row, box_w, _ = f
    bx = col_x + LABEL_W
    by = RO_Y + row * RO_ROW
    return bx, by, box_w, BOX_H


def field_slots(f):
    """Digit slot X positions (left-to-right), spaced RW; first slot inset 4px in the box."""
    bx, _, _, _ = field_box(f)
    n = f[5]
    return [bx + 4 + i * RW for i in range(n)]


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


def draw_button(d, x, y, label, fill, txt, border=True):
    d.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], fill=fill,
                outline=(BORDER if border else fill))
    centered(d, x + CELL_W // 2, y + CELL_H // 2, label, load_font(17), txt)


def make_panel_bg():
    img = Image.new("RGB", (PANEL_W, PANEL_H), BG)
    d = ImageDraw.Draw(img)
    centered(d, PANEL_W // 2, 18, "P2 Robot Dog  -  Move Panel  (click a button)", load_font(22), LABEL)

    # idle buttons
    for (row, col, label, target, cmd, arg, cat) in BUTTONS:
        x, y = btn_xy(row, col)
        draw_button(d, x, y, label, CAT[cat], LABEL)

    # readout labels + black value boxes
    lab = load_font(17)
    for f in FIELDS:
        key, label, col_x, row, box_w, n = f
        ly = RO_Y + row * RO_ROW
        d.text((col_x, ly + 8), label, font=lab, fill=LABEL)
        bx, by, bw, bh = field_box(f)
        d.rectangle([bx, by, bx + bw, by + bh], fill=BOX)
        # P / R sub-labels for tilt are baked into the box background (drawn over black)
        if key == "tilt":
            sl = field_slots(f)
            d.text((sl[0] - 14, by + 6), "P", font=load_font(15), fill=DIM)
            d.text((sl[3] + RW - 6, by + 6), "R", font=load_font(15), fill=DIM)

    # footer help
    centered(d, PANEL_W // 2, PANEL_H - 18,
             "click posts the command   -   SLOW/NORM/FAST set gait speed   -   LED & RANGE toggle",
             load_font(14), DIM)
    img.save(os.path.join(OUT, "dog_panel_bg.bmp"))


def make_btn_hi():
    """Vertical strip of highlighted button cells; srcY = slot*CELL_H. Blank slots = plain bg cell."""
    img = Image.new("RGB", (CELL_W, ROWS * COLS * CELL_H), BG)
    d = ImageDraw.Draw(img)
    defined = {slot_of(r, c): lbl for (r, c, lbl, *_rest) in BUTTONS}
    for slot in range(ROWS * COLS):
        y = slot * CELL_H
        if slot in defined:
            d.rectangle([0, y, CELL_W - 1, y + CELL_H - 1], fill=HI_FILL, outline=HI_FILL)
            centered(d, CELL_W // 2, y + CELL_H // 2, defined[slot], load_font(17), HI_TEXT)
        else:
            d.rectangle([0, y, CELL_W - 1, y + CELL_H - 1], fill=BG, outline=BG)
    img.save(os.path.join(OUT, "dog_btn_hi.bmp"))


def make_font_strip():
    img = Image.new("RGB", (RW * len(RGLYPHS), RH), BOX)
    d = ImageDraw.Draw(img)
    f = load_font(28)
    for i, ch in enumerate(RGLYPHS):
        centered(d, i * RW + RW // 2, RH // 2, ch, f, GLYPH)
    img.save(os.path.join(OUT, "dog_font.bmp"))


def make_word_strip(names, cell_w, cell_h, filename):
    """Vertical word-cell strip: one centered green name per cell (srcY = index*cell_h)."""
    img = Image.new("RGB", (cell_w, cell_h * len(names)), BOX)
    d = ImageDraw.Draw(img)
    f = load_font(20)
    for i, name in enumerate(names):
        centered(d, cell_w // 2, i * cell_h + cell_h // 2, name, f, GLYPH)
    img.save(os.path.join(OUT, filename))


def make_modes_strip():
    make_word_strip(MODE_NAMES, MODE_CELL_W, MODE_CELL_H, "dog_modes.bmp")


def make_led_modes_strip():
    make_word_strip(LED_MODE_NAMES, LED_CELL_W, LED_CELL_H, "dog_led_modes.bmp")


def emit_spin2_con():
    print("\n' ---- layout (generated by tools/gen_dog_panel_assets.py; matches the BMPs) ----")
    print(f"  PANEL_W = {PANEL_W}")
    print(f"  PANEL_H = {PANEL_H}")
    print(f"  COLS = {COLS}")
    print(f"  ROWS = {ROWS}")
    print(f"  CELL_W = {CELL_W}")
    print(f"  CELL_H = {CELL_H}")
    print(f"  PITCH_X = {PITCH_X}")
    print(f"  PITCH_Y = {PITCH_Y}")
    print(f"  GRID_X = {GRID_X}")
    print(f"  GRID_Y = {GRID_Y}")
    print(f"  RW = {RW}")
    print(f"  RH = {RH}")
    print(f"  GLYPH_MINUS = 10")
    print(f"  MODE_CELL_W = {MODE_CELL_W}")
    print(f"  MODE_CELL_H = {MODE_CELL_H}")
    print(f"  LED_CELL_W = {LED_CELL_W}")
    print(f"  LED_CELL_H = {LED_CELL_H}")
    print("\n' ---- readout field boxes (box_x, box_y) and digit slot-0 X (slots step by RW) ----")
    for f in FIELDS:
        key = f[0].upper()
        bx, by, bw, bh = field_box(f)
        sl = field_slots(f)
        s0 = sl[0] if sl else bx + 4
        if f[0] == "led":
            s0 = bx + LED_CELL_W + 6        # index digit sits to the RIGHT of the LED-mode name cell
        print(f"  RO_{key}_BX = {bx}")
        print(f"  RO_{key}_BY = {by}")
        print(f"  RO_{key}_BW = {bw}")
        print(f"  RO_{key}_S0 = {s0}")
    print(f"  RO_BOX_H = {BOX_H}")
    print("\n' ---- button table (slot = row*COLS + col); paste into the DAT btnTbl ----")
    print("'   slot  x    y   label    target cmd            arg   cat")
    for (row, col, label, target, cmd, arg, cat) in BUTTONS:
        x, y = btn_xy(row, col)
        print(f"'   {slot_of(row,col):>3}  {x:>3}  {y:>3}  {label:<8} {target:<4} {cmd:<16} {arg:>4}  {cat}")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_panel_bg()
    make_btn_hi()
    make_font_strip()
    make_modes_strip()
    make_led_modes_strip()
    for fn in ("dog_panel_bg.bmp", "dog_btn_hi.bmp", "dog_font.bmp", "dog_modes.bmp", "dog_led_modes.bmp"):
        print("wrote:", os.path.join(OUT, fn))
    print(f"panel {PANEL_W}x{PANEL_H}; button cell {CELL_W}x{CELL_H} pitch {PITCH_X}x{PITCH_Y}; readout font {RW}x{RH}")
    emit_spin2_con()
