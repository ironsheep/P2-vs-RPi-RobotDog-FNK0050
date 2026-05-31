# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this project is

Porting the **Freenove Robot Dog Kit (FNK0050)** from its stock **Raspberry Pi**
controller to a **Parallax Propeller 2 (P2)**. A P2 Edge Module + breakout board, on
a custom adapter plate, replaces the Pi in the connection board's 40-pin header. The
P2 firmware must drive the same hardware the Pi's Python stack drove.

**This build is connection board PCB v1.0** (WS2812 LED data on GPIO18, the
`rpi_ws281x` path — not the v2.0 SPI0/GPIO10 path). When a behavior is version-
dependent, assume v1.0.

## Repository layout

- `DOCs/` — project documentation (authoritative; see below).
- `src/` — P2 firmware in **Spin2 / PASM2** (work in progress, currently empty).
- `REF/` — upstream Freenove FNK0050 Raspberry Pi Python code, kept **locally for
  porting reference only**. It is **git-ignored** — never commit it, and treat it as
  read-only source material, not project code.

## Authoritative docs — read before changing hardware assumptions

- `DOCs/RPI_GPIO_USAGE.md` — the stock Pi pin/bus usage, reverse-engineered from the
  Freenove server source. Device inventory, I²C addresses, servo channel map.
- `DOCs/P2_MIGRATION_WIRING.md` — the P2 swap: power architecture, header→P2 wiring
  map, and 3.3 V-vs-5 V hazards.
- `DOCs/P2-platform/` — adapter-plate CAD (DXF + 3MF).

> **No schematic exists** for the connection board. Every pin/rail fact in the docs
> was traced from the Freenove code or confirmed from Freenove's published docs.
> Items marked "verify"/"inferred" in `P2_MIGRATION_WIRING.md` must be metered before
> wiring — do not present them as certain.

## Hardware facts to keep straight

Most peripherals are on a single **I²C bus** (Pi I²C-1: SDA=GPIO2/pin 3,
SCL=GPIO3/pin 5) behind driver chips — so the bulk of the port is implementing a P2
I²C master:

| Device | Access | Role |
|--------|--------|------|
| PCA9685 @ `0x40` | I²C | 16-ch PWM @ 50 Hz → 13 servos (12 leg joints + head pan) |
| ADS7830 @ `0x48` | I²C | battery ADC (ch 0); low-battery cutoff < 6.4 V |
| MPU6050 @ `0x68` | I²C | 6-axis IMU for balance/attitude |

Only **three peripherals use discrete GPIO** (each a natural P2 smart-pin job):

| Device | Pi GPIO (hdr pin) | Notes |
|--------|-------------------|-------|
| Buzzer | GPIO17 (11) | simple output |
| HC-SR04 ultrasonic | TRIG GPIO27 (13), ECHO GPIO22 (15) | ECHO is the only GPIO **input**; 5 V echo must arrive ≤ 3.3 V |
| WS2812 LED strip (7 px) | GPIO18 (12) — **v1.0** | data line; 3.3 V data into 5 V strip |

Servo channel map (PCA9685 PWM channels, **not** Pi GPIO): ch 2–13 are the four legs
(3 joints each), ch 15 is the head-pan servo; angle 0–180° → count 102–512.

### Critical electrical gotchas

- **The P2 is a 3.3 V part and is NOT 5 V tolerant** (pin abs-max ≈ 3.6 V). Every
  signal into a P2 pin must be ≤ 3.3 V. Watch the 5 V-native sensors (HC-SR04 ECHO,
  WS2812).
- **3.3 V rail vanishes with the Pi.** Header pins 1/17 were fed *by the Pi*; the P2
  adapter must supply 3.3 V back onto them for the board's I²C pull-ups/chips. #1 gotcha.
- The robot powers the controller (battery → board regulator → 5 V on header pins 2/4),
  not the reverse. Feed the P2 board 5 V; it regulates to 3.3 V on-board.
- **P2 Edge reserved pins:** P58–P61 = boot SPI flash, P62/P63 = serial/programming.
  Keep robot I/O on **P0–P57**.

## Working conventions

- **Don't commit `REF/` or `.DS_Store`** (both git-ignored).
- License is **MIT, © Iron Sheep Productions, LLC**. The `REF/` material is Freenove's
  (CC BY-NC-SA 3.0) and is excluded from this repo's license.
- For P2 architecture, PASM2 instructions, or Spin2 syntax/methods, use the **p2kb-mcp**
  tools (authoritative P2 Knowledge Base) rather than web search. OBEX has existing
  I²C, WS2812, and pulse-measure objects worth reusing — check `p2kb_obex_find`.
- When citing a hardware pin or rail, cite the doc (and its confidence level) — many
  facts are inferred from code, not measured.
