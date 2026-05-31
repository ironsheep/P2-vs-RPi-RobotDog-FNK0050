# Raspberry Pi GPIO / Pin Usage

![Doc Type](https://img.shields.io/badge/doc-pin%20reference-blue)
![Platform](https://img.shields.io/badge/platform-Propeller%202-blue)
![PCB](https://img.shields.io/badge/PCB-v1.0-orange)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![License](https://img.shields.io/badge/license-MIT-green)

Reverse-engineered from the server source (`Code/Server/`). **No schematic exists** for
this kit in the repo — every pin below was traced from the code that drives it, with the
file/line cited. All GPIO numbers are **BCM** (Broadcom) numbering, which is what both
`gpiozero` and `rpi_ws281x` use by default. Official kit docs: **Freenove FNK0050** —
https://docs.freenove.com/projects/fnk0050/en/latest/ . For the P2 swap (power, charging,
wiring map) see [`P2_MIGRATION_WIRING.md`](P2_MIGRATION_WIRING.md).

> **This build uses PCB v1.0.** On the v1.0 connection board the WS2812 LED data line is
> **GPIO18 (PWM0)** via the `rpi_ws281x` driver — *not* the SPI0/GPIO10 path used by PCB
> v2.0. (Reminder: PCB v1.0 + Raspberry Pi 5 is **unsupported** for the LEDs; v1.0 targets
> Pi 1–4.) Everything else below is identical across PCB versions.

> **Key takeaway:** very little hangs off raw GPIO. The 13 servos, the battery ADC, and
> the IMU are all on the **I²C bus**, reached through dedicated driver chips. Only the
> buzzer, the ultrasonic sensor, and the WS2812 LED data line use discrete GPIO pins —
> and the LED pin *changes with PCB/Pi version*.

## Device inventory — what's accessed, how, and why

Every peripheral the server touches, and the bus it rides. Note the **"On raw GPIO?"**
column: only the buzzer and the ultrasonic ("ping") sensor — plus the LED data line — talk
to the Pi over discrete GPIO. The remaining sensors/actuators are on I²C behind driver
chips, so they consume **no** dedicated GPIO beyond the shared SDA/SCL pair.

| Device | Type | Access path | On raw GPIO? | Purpose in the robot | Source |
|---|---|---|---|---|---|
| **HC‑SR04 ultrasonic** ("ping") | Sensor (input) | TRIG=GPIO27, ECHO=GPIO22 | **Yes** | Forward obstacle / distance ranging; reported on `CMD_SONIC` | `Ultrasonic.py` |
| **MPU6050 IMU** | Sensor (input) | I²C `0x68` | No (I²C) | 6-axis accel+gyro for self-balancing and body attitude (roll/pitch/yaw); feeds Kalman + PID | `IMU.py`, `Control.py` |
| **ADS7830 ADC** | Sensor (input) | I²C `0x48` | No (I²C) | Battery-voltage monitoring (ch 0); low-battery auto-shutdown < 6.4 V | `ADS7830.py`, `Server.py` |
| **Pi Camera** | Sensor (input) | CSI ribbon | No (CSI) | Live video stream to client (port 8001); face/ball tracking on client side | `Server.py`, `camera.py` |
| **PCA9685 → 13× servos** | Actuator (output) | I²C `0x40` → PWM ch 2–13, 15 | No (I²C) | 12 leg-joint servos (gait/IK) + 1 head-pan servo | `Servo.py`, `Control.py`, `Action.py` |
| **Passive buzzer** | Actuator (output) | GPIO17 | **Yes** | Audible alert / horn (`CMD_BUZZER`) | `Buzzer.py` |
| **WS2812 RGB strip (7 px)** | Actuator (output) | GPIO18 *or* SPI0‑MOSI GPIO10 | **Yes** (data line) | Status / decorative lighting effects (`CMD_LED`, `CMD_LED_MOD`) | `Led.py`, `rpi_ledpixel.py`, `spi_ledpixel.py` |

**Direct answer on the ping sensor:** yes — the HC‑SR04 ultrasonic is the one *sensor*
wired to raw Raspberry Pi GPIO (TRIG on GPIO27, ECHO on GPIO22, via `gpiozero`). It is the
robot's only distance/proximity sensor and its only GPIO **input**. Every other sensor
(IMU, battery ADC, camera) reaches the Pi over a bus (I²C or CSI), not discrete GPIO.

## Summary table

| BCM GPIO | Hdr pin | Direction | Signal / function | Attached device | Source |
|---|---|---|---|---|---|
| GPIO2 (SDA1) | 3 | bidir | **I²C data** — servos, ADC, IMU | PCA9685, ADS7830, MPU6050 | `PCA9685.py:29`, `ADS7830.py:6`, `IMU.py:24` |
| GPIO3 (SCL1) | 5 | out | **I²C clock** — same bus | same as above | same |
| GPIO17 | 11 | out | **Buzzer** drive (on/off) | passive/active buzzer | `Buzzer.py:3` |
| GPIO27 | 13 | out | **Ultrasonic TRIG** | HC‑SR04 | `Ultrasonic.py:8` |
| GPIO22 | 15 | in | **Ultrasonic ECHO** | HC‑SR04 | `Ultrasonic.py:9` |
| GPIO18 (PWM0) | 12 | out | **WS2812 LED data** — *PCB v1 + Pi ≤4 only* | RGB LED strip (7 px) | `rpi_ledpixel.py:23` |
| GPIO10 (SPI0 MOSI) | 19 | out | **WS2812 LED data** — *PCB v2 (all Pi)* | RGB LED strip (7 px) | `spi_ledpixel.py` + `Led.py:22` |
| GPIO9 / 11 / 8 | 21 / 23 / 24 | — | SPI0 MISO / SCLK / CE0 — *reserved when SPI is enabled, not actively used* | — | SPI0 bus |
| CSI camera connector | (ribbon) | — | Camera video (not on the 40‑pin header) | Pi Camera | `Server.py`, `camera.py` |

GPIO numbers **not** used by this code: everything else on the header is free as far as
the software is concerned (GPIO0, 1, 4–7, 12–16, 19–26 — note the SPI0 secondaries above
are only occupied if SPI is enabled for the v2 LED path).

---

## 1. I²C bus (GPIO2 = SDA1, GPIO3 = SCL1)

All driver chips share I²C bus **1** (`smbus.SMBus(1)`). Three devices live here:

| Device | I²C addr | Role | Source |
|---|---|---|---|
| **PCA9685** | `0x40` | 16-channel PWM generator → drives all servos | `PCA9685.py:28`, `Servo.py:7` |
| **ADS7830** | `0x48` | 8-channel ADC → reads battery voltage (ch 0) | `ADS7830.py:8` |
| **MPU6050** | `0x68` | 6-axis IMU (accel + gyro) for balance/attitude | `IMU.py:24` |

`config.txt` enables this bus with `dtparam=i2c_arm=on`.

### Servo channel map (PCA9685, **PWM channels — not Pi GPIO**)
The PCA9685 outputs PWM on its own 16 channels @ 50 Hz; angle 0–180° maps to count 102–512
(`Servo.py`). 13 of the 16 channels are used:

| PCA9685 ch | Function | Source |
|---|---|---|
| 2, 3, 4 | Leg 0 (front-left): lower, middle, hip | `Control.py:112-114` (i=0) |
| 5, 6, 7 | Leg 1 (front-right): lower, middle, hip | `Control.py:112-114` (i=1) |
| 8, 9, 10 | Leg 2 (rear-left): hip, middle, lower | `Control.py:115-117` (i=0) |
| 11, 12, 13 | Leg 3 (rear-right): hip, middle, lower | `Control.py:115-117` (i=1) |
| 15 | **Head pan** servo | `Server.py` (`CMD_HEAD`), `Action.py:8` |
| 0, 1, 14 | unused | — |

(Each leg = 3 joints; the gait engine writes all 12 leg channels per `run()` step. The
head is driven directly by `CMD_HEAD#<angle>`.)

### Battery sense (ADS7830 channel 0)
`adc.power(0)` reads ADC channel 0 and scales `data/255 * 5.0 * 2` — the `× 2` implies a
half-scale resistor divider on the pack voltage. Server shuts the dog down below 6.4 V
(`Server.battery_reminder`).

---

## 2. Buzzer — GPIO17 (header pin 11)

`gpiozero.Buzzer(17)`, simple on/off (`Buzzer.py`). Triggered by `CMD_BUZZER#1` / `#0`.
Note: `config.txt` has commented-out IR overlays that *would* also claim GPIO17
(`dtoverlay=gpio-ir,gpio_pin=17`) — they are disabled, so no conflict, but worth knowing.

## 3. Ultrasonic distance — TRIG GPIO27 (pin 13), ECHO GPIO22 (pin 15)

`gpiozero.DistanceSensor(echo=22, trigger=27, max_distance=3)` (`Ultrasonic.py`). HC‑SR04
style sensor; `get_distance()` returns cm. Served on demand via `CMD_SONIC`. ECHO is the
only **input** GPIO in the design — on a real HC‑SR04 its 5 V echo needs a divider to the
Pi's 3.3 V input (assume present on the PCB).

## 4. WS2812 RGB LEDs — pin depends on PCB **and** Pi version

`Led.py` picks the driver from `params.json` (set by `parameter.py`). Both paths drive a
**7-pixel** strip, but over different hardware:

| PCB | Pi | Driver | Data pin | Notes |
|---|---|---|---|---|
| v1.0 | Pi 1–4 | `Freenove_RPI_WS281X` (rpi_ws281x) | **GPIO18** (PWM0) | `Adafruit_NeoPixel(7, 18, 800000, 10, …)` → pin 18, DMA 10, ch 0 (`rpi_ledpixel.py:23`) |
| v2.0 | Pi 1–5 | `Freenove_SPI_LedPixel` (spidev) | **GPIO10** (SPI0 MOSI) | Bit-bangs WS2812 timing over SPI MOSI; needs SPI enabled (`spi_ledpixel.py`) |
| v1.0 | Pi 5 | — | — | **Unsupported**; LEDs disabled (`Led.py:24`) |

For the v2/SPI path the WS2812 data rides **GPIO10 (MOSI)** only; SPI0's MISO (GPIO9),
SCLK (GPIO11) and CE0 (GPIO8) are reserved by the enabled SPI peripheral but not
functionally used for the LEDs. SPI must be turned on (`dtparam=spi=on` / `raspi-config`);
the driver prints setup hints if `/dev/spidev*` is missing.

## 5. Camera — CSI connector (not a GPIO)

`Server.py` / `camera.py` use `picamera2`; the camera attaches via the dedicated CSI
ribbon connector, not the 40-pin GPIO header. `Code/Patch/` patches `libmmal.so` for the
legacy stack on Bullseye.

---

## Caveats

- Pins were traced from code only; without a schematic, **level-shifting, pull resistors,
  power rails, and the exact 5 V/3.3 V routing on the connection PCB are unconfirmed.** The
  ADS7830 `×2` divider and the HC‑SR04 echo divider are inferred, not verified.
- Header pin numbers assume the standard 40-pin Raspberry Pi GPIO header.
- The version-dependent LED pin (GPIO18 vs GPIO10) is the single biggest gotcha for any
  port: read `params.json` before assuming which line carries LED data.

---

## License

MIT License - See [LICENSE](../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
