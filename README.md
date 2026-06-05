# P2-vs-RPi-RobotDog-FNK0050

![Project Status](https://img.shields.io/badge/status-in%20development-yellow)
![Platform](https://img.shields.io/badge/platform-Propeller%202-blue)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![License](https://img.shields.io/badge/license-MIT-green)

One of the things I really enjoy doing is finding robotic platforms with a collection of servos and actuators and sensors that look like they'd be fun to control and might be a good challenge for me to expand my skills in programming the P2. When I find these platforms, I look at how they're set up and how compatible they might be. In this case, this was driven by a Raspberry Pi, so I know the interface is going to be pretty easy to adopt when it comes to taking out the Raspberry Pi and replacing it with a P2.

This project is exactly that: the record of me doing this work of replacing a Pi with a P2 and then building the code around it. I built this so you can follow along and play and even use the code if you wish for experiments on your own. 

-*Stephen*

<p align="center">
  <img src='DOCs/Picture/fullbody-right.png' width='60%' alt='Freenove FNK0050 Robot Dog with the Parallax P2 Edge Module mounted where the Raspberry Pi used to sit'/>
</p>

> *The FNK0050 Robot Dog with the Parallax **P2 Edge Module** mounted in place of the Raspberry Pi — the "P2 EDGE" module and chip are visible on top.*

Porting the **Freenove Robot Dog Kit (FNK0050)** from its stock **Raspberry Pi**
controller to a **Parallax Propeller 2 (P2)**. The P2 — on an Edge Module +
breakout board carried by a custom adapter plate — drops into the spot where the
Pi normally sits and mates to the connection board's 40-pin header.

The goal: drive the same robot hardware (13 servos, IMU, battery ADC, ultrasonic
sensor, buzzer, and WS2812 LEDs) from P2 firmware instead of the Pi's Python stack.

> **This build uses connection board PCB v1.0** — so the WS2812 LED data line is on
> **GPIO18** (the `rpi_ws281x` path), not the SPI0/GPIO10 path used by PCB v2.0.

## Why the P2?

The Freenove design puts almost everything on **I²C** behind driver chips
(PCA9685 servo controller, ADS7830 battery ADC, MPU6050 IMU), so most of the port
is "implement an I²C master on the P2." Only three peripherals use discrete GPIO —
the buzzer, the HC-SR04 ultrasonic sensor, and the WS2812 LED strip — and each maps
naturally onto a P2 smart pin. See the wiring map for the full breakdown.

## Repository layout

| Path | Contents |
|------|----------|
| [`DOCs/`](DOCs/) | Project documentation — pin usage, the P2 migration wiring map, mounting hardware CAD, and supporting images/sources. |
| `src/` | P2 firmware (Spin2 / PASM2) — work in progress. |
| `REF/` | Upstream Freenove FNK0050 Raspberry Pi code, kept locally for porting reference. **Git-ignored** — not part of this repo's deliverables. |

## Documentation

Start here when planning or executing the hardware swap:

- **[`DOCs/P2-platform/`](DOCs/P2-platform/)** — the **physical-platform hub**: the
  [build walk-through](DOCs/P2-platform/HARDWARE_SETUP.md) (model/print the adapter plate,
  assemble the P2 board onto it, mount it on the robot), the
  [wiring map](DOCs/P2-platform/P2_MIGRATION_WIRING.md) (power architecture, the 3.3 V
  provenance gotcha, the header→P2 map, and the 3.3 V-vs-5 V hazards — the P2 is **not**
  5 V tolerant), and the adapter-plate **CAD** (DXF + 3MF).
- **[`DOCs/RPI_GPIO_USAGE.md`](DOCs/RPI_GPIO_USAGE.md)** — the stock Pi pin/bus
  usage, reverse-engineered from the Freenove server source (no schematic exists).
  Device inventory, I²C addresses, servo channel map, and which signals ride raw GPIO.

## Hardware reference

- **Kit:** Freenove Robot Dog Kit for Raspberry Pi (FNK0050) —
  https://docs.freenove.com/projects/fnk0050/en/latest/
- **Controller (new):** Parallax Propeller 2 Edge Module + breakout board.
- **Power:** 2× 18650 Li-ion (2S), externally charged; the connection board's
  regulator delivers 5 V to the controller. See the wiring map for details.

## Status

Early-stage. Documentation and mechanical/electrical planning are in place; the P2
firmware in `src/` is under development.

## Possible future directions

These are **candidate** directions for after the current port is fully bench-certified —
**none is committed or in progress**, and the current firmware does not depend on any of
them. They are recorded here so the intent is visible; the most likely next one is
**speech recognition**.

- **Speech recognition** *(most likely up next)* — let the dog take spoken commands
  ("sit", "forward", "hello") instead of only scripted/mailbox commands. Would plug into
  the existing cog-0 command path (post into mailbox A/B), so the motion engine and gait
  catalog need no change.
- **Vision recognition** — add a camera and on-/off-board inference so the dog can react
  to what it sees (follow a target, detect obstacles, recognize markers). The biggest open
  question is where the inference runs, given the P2's resources versus the Pi's old stack.
- **Bluetooth radio for remote commanding** — a wireless command link to replace the
  scripted demo orchestrator, driving the same mailbox command set from a phone or
  gamepad. This is the natural first realization of the still-**TODO** "real comms cog 0"
  command link the firmware already reserves a seat for.

---

## License

MIT License - See [LICENSE](LICENSE) for details. © 2026 Iron Sheep Productions, LLC.

Note: the upstream Freenove reference material under `REF/` (git-ignored) is released
by Freenove under CC BY-NC-SA 3.0 and is not covered by this repository's license.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
