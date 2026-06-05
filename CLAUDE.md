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
- `DOCs/P2-platform/P2_MIGRATION_WIRING.md` — the P2 swap: power architecture, header→P2 wiring
  map, and 3.3 V-vs-5 V hazards.
- `DOCs/P2-platform/` — adapter-plate CAD (DXF + 3MF).

> **No schematic exists** for the connection board. Every pin/rail fact in the docs
> was traced from the Freenove code or confirmed from Freenove's published docs.
> Items marked "verify"/"inferred" in `DOCs/P2-platform/P2_MIGRATION_WIRING.md` must be metered before
> wiring — do not present them as certain.

## Hardware facts to keep straight

Most peripherals are on a single **I²C bus** (Pi I²C-1: SDA=GPIO2/pin 3,
SCL=GPIO3/pin 5) behind driver chips — so the bulk of the port is implementing a P2
I²C master:

| Device | Access | Role |
|--------|--------|------|
| PCA9685 @ `0x40` | I²C | 16-ch PWM @ 50 Hz → 13 servos (12 leg joints + head pan) |
| ADS7830 @ `0x48` | I²C | battery ADC (ch 0); **÷3 divider** (metered 2026-06-01); low-battery cutoff < 6.4 V |
| MPU6050 @ `0x68` | I²C | 6-axis IMU for balance/attitude |

Only **three peripherals use discrete GPIO** (each a natural P2 smart-pin job):

| Device | Pi GPIO (hdr pin) | Notes |
|--------|-------------------|-------|
| Buzzer | GPIO17 (11) | simple output; on the **Load/servo rail** — silent unless the Load switch is ON |
| HC-SR04 ultrasonic | TRIG GPIO27 (13), ECHO GPIO22 (15) | ECHO is the only GPIO **input**; 5 V echo must arrive ≤ 3.3 V |
| WS2812 LED strip (7 px) | GPIO18 (12) — **v1.0** | data line; 3.3 V data into 5 V strip |

### Committed P2 pin mapping (P8–P15)

All signals route to **P2 pins P8–P15**. **As-built adapter map (verified on hardware
2026-05-31)**, base P8 with offsets LED +0, ECHO +1, Buzzer +2, TRIG +3, SCL +5, SDA +7.
Authoritative table + rationale: `DOCs/P2-platform/P2_MIGRATION_WIRING.md` §3.

| P2 pin | Robo hdr pin | Signal |
|--------|--------------|--------|
| P8 | 12 | WS2812 LED data |
| P9 | 15 | Ultrasonic ECHO (in) — 5 V undivided → ~1 kΩ inline series R |
| P10 | 11 | Buzzer |
| P11 | 13 | Ultrasonic TRIG |
| P12 | — | spare |
| P13 | 5 | I²C SCL |
| P14 | — | spare |
| P15 | 3 | I²C SDA |

Servo channel map (PCA9685 PWM channels, **not** Pi GPIO): ch 2–13 are the four legs
(3 joints each), ch 15 is the head-pan servo; angle 0–180° → count 102–512. **Verified on hardware
2026-06-01:** FL=4/3/2, BL=7/6/5, BR=8/9/10, FR=11/12/13, head=15. (PCA9685 needed a wake-from-SLEEP
fix in `isp_i2c_pca9685` before any servo would drive.)

### Critical electrical gotchas

- **P2 over-voltage:** the P2 cannot *drive* 5 V, and a *bare* pin must stay ≤ VIO+0.3 V
  (~3.6 V) — **but** the datasheet permits over-voltage via the pin's internal clamp diode to
  VIO as long as clamp current ≤ ±10 mA, so a **~1 kΩ series resistor lets a P2 pin safely
  *read* 5 V** (e.g. HC-SR04 ECHO; R ≥ (Vin−3.6)/10 mA). The original **RPi GPIO was 3.3 V and
  NOT 5 V-tolerant** with no such clamp. **Resolved (metered 2026-05/06-01):** the board does
  **not** divide ECHO — header pin 15 carries **undivided 5 V** — so a **~1 kΩ series R into P9 is
  fitted**, and HC-SR04 ranging is verified working. (Clamp/abs-max in the P2 datasheet; see
  `DOCs/P2-platform/P2_MIGRATION_WIRING.md` §4, §7.)
- **3.3 V rail vanishes with the Pi.** Header pins 1/17 were fed *by the Pi*; the P2
  adapter must supply 3.3 V back onto them for the board's I²C pull-ups/chips. #1 gotcha.
- The robot powers the controller (battery → board regulator → 5 V on header pins 2/4),
  not the reverse. Feed the P2 board 5 V; it regulates to 3.3 V on-board.
- **P2 Edge reserved pins:** P58–P61 = boot SPI flash, P62/P63 = serial/programming.
  Keep robot I/O on **P0–P57** — the committed P8–P15 block is safely inside that range.

## Working conventions

- **Don't commit `REF/` or `.DS_Store`** (both git-ignored).
- License is **MIT, © Iron Sheep Productions, LLC**. The `REF/` material is Freenove's
  (CC BY-NC-SA 3.0) and is excluded from this repo's license.
- For P2 architecture, PASM2 instructions, or Spin2 syntax/methods, use the **p2kb-mcp**
  tools (authoritative P2 Knowledge Base) rather than web search. OBEX has existing
  I²C, WS2812, and pulse-measure objects worth reusing — check `p2kb_obex_find`.
- When citing a hardware pin or rail, cite the doc (and its confidence level) — many
  facts are inferred from code, not measured.
