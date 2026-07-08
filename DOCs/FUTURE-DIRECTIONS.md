[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Future Directions — P2 Robot Dog

Detailed companion to the top-level [README](../README.md) "Possible future directions" summary.
These are **candidate** directions for **after** the current port is fully bench-certified —
**none is committed or in progress**, and the current firmware does not depend on any of them. They
are recorded here so the intent — and the hardware/integration thinking behind each — is visible.

![doc-roadmap](https://img.shields.io/badge/doc-roadmap-informational?labelColor=black)
![platform-Propeller 2](https://img.shields.io/badge/platform-Propeller%202-blue?labelColor=black)
![status-not started](https://img.shields.io/badge/status-not%20started-lightgrey?labelColor=black)
![maintainer-stephen@ironsheep.biz](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![license-MIT](https://img.shields.io/badge/license-MIT-green?labelColor=black)

> **The common thread.** Every direction below is an **input** that posts into the **cog-0 command
> mailboxes** (`dog.postCommand` / `io.postCommand`) — the exact path the bench move-panel uses. So
> the **motion engine, gait catalog, and gesture set need no change**; each new source just calls
> `postCommand`. A useful consequence: **every `CMD_*` we add now becomes a future *spoken* and
> *remote* command word.**

---

## 1. Speech recognition — *✅ implemented (build 0.3.0)*

**Shipped.** The dog now takes **spoken** commands. A **DFRobot DF2301Q "Gravity" offline voice
recognizer** (`0x64`) was chosen and integrated on a **dedicated 2nd I²C bus** (P18 SCL / P16 SDA), owned
by the IO cog (cog 1). The wake phrase is **"Hello Peabody"**; a 17-word custom vocabulary maps 1:1 to the
dog's `CMD_*` set (plus built-in aliases), dispatched by the cog-0 loop through the motion gate. Full
detail: [`subsystems/VoiceSensor/`](subsystems/VoiceSensor/) and the release notes. Remaining polish: the
live end-to-end bench demo and the full LED feedback scheme.

**How the choice landed vs. the original candidates** (kept for the record). The exploration considered a
UART-*or*-I²C module ([amazon.com/dp/B0C5XG3BXW](https://www.amazon.com/dp/B0C5XG3BXW)) and leaned UART for
a confidence stream. In practice the **I²C DF2301Q** was selected — it does fully-offline recognition with
its own trained vocabulary and reports a latched command-word **ID** (no confidence field), polled from a
result register; it clock-stretches, so it got its own bus rather than joining bus 1. Recognized ID →
`voiceToDogCmd()` → `postCommand` into mailbox A, exactly the "no motion change" integration anticipated.

---

## 2. Pan/tilt head + vision AI camera — *longer-term*

**What.** Replace the current head — a **single, tilt-only servo** (up/down, PCA9685 ch 15; note the
code/docs currently mislabel it "pan") — with a **pan/tilt** mount carrying a **vision AI camera**
that reports *what it sees* (detected objects/scene) back to the controller.

**Hardware candidate.** [amazon.com/dp/B0CX93M5DW](https://www.amazon.com/dp/B0CX93M5DW) — interface
**I²C**.

**P2 integration.**
- The camera runs inference **on-board** and emits **results over I²C** — so there is **no USB-host
  or CSI-ribbon requirement** (the camera-integration risk we worried about is resolved). It joins
  the existing I²C master (P13 SCL / P15 SDA) alongside PCA9685 `0x40` / ADS7830 `0x48` /
  MPU6050 `0x68`; just needs a distinct address and a bus-loading/pull-up check.
- The pan/tilt servos are two more PCA9685 channels (spares today: ch 0, 1, 14 — plus the current
  ch 15 head servo).
- Detections feed **react-to-what-it-sees** behaviors — follow a target, look-at, find/scan — and a
  real **pan** axis restores side-to-side gestures (head-shake "no", lateral scans) that the
  tilt-only head can't do.

**Open questions.** I²C bandwidth/latency for detection results; physical mount; whether pan/tilt
reuses ch 15 + a spare or two fresh channels.

---

## 3. P2 native audio output — *longer-term*

**What.** The P2 can synthesize **real audio** (smart-pin DAC/PWM), well beyond today's on/off
**buzzer** (GPIO17 / P10, driven by the IO cog) — a path to actual **barks, sound effects, and
spoken output**.

**P2 integration.** A smart-pin audio output + a small amp/speaker; pairs naturally with the
speech-recognition direction (hear a command, *answer* with a bark). The `SPEAK` trick can ship first
as a buzzer pattern, with the P2-audio version as the eventual target.

**Open questions.** Amp/speaker choice; output pin; where sample/clip data lives.

---

## 4. BLE radio for remote commanding — *longer-term*

**What.** A wireless command link to join (or replace) the voice dispatch loop on cog 0, driving the
**same mailbox command set** from a phone or gamepad — a fuller realization of the still-**TODO**
"comms cog 0" the firmware reserves a seat for (voice is the first command source).

**Hardware candidates (pick ONE).** [amazon.com/dp/B0DRNSV5CS](https://www.amazon.com/dp/B0DRNSV5CS)
and [amazon.com/dp/B0GGB1L8N5](https://www.amazon.com/dp/B0GGB1L8N5) — interface **SPI / I²C**.

**P2 integration.** The **I²C** option shares the existing bus (distinct address); the **SPI** option
takes ~3–4 dedicated pins. Either way it posts the same `CMD_*` set into the mailboxes.

**Open questions.** Pick the module (SPI vs I²C, range/power); pairing + wire protocol.

---

## 5. Active IMU balance (closed-loop) — *longer-term, after the motion studies*

**What.** Use the MPU6050 **during** motion, not just at rest — so the dog can **react to disturbances
in real time**: if it steps onto something while walking, or starts drifting out of balance, it adjusts
foot placement / shifts its center of gravity, or **stops/freezes to avoid tipping**.

**Where we are.** Today the IMU is used only for **static leveling** (measure the neutral-stand tilt
once → per-leg foot-Y trim; firmware spec §5). The attitude is read continuously but does **not** correct
motion in flight — the gaits are open-loop.

**Why it's sequenced after the dog-movement work.** Closed-loop balance is a robustness *layer* on top of
the open-loop trajectories — there's no point stabilizing motion that isn't yet shaped the way we want.
First get the gaits/poses **dog-like** (the motion studies); then add the IMU feedback that keeps them
upright on uneven ground. No hardware needed (the MPU6050 is already on the bus) — this is firmware.

**Open questions.** Detection thresholds (what tilt rate = "losing it"); reaction policy (correct vs.
freeze); how to fold a correction into the fixed-rate eased engine without fighting the gait trajectory.

---

## Hardware candidates at a glance

| Direction | Device | Interface | Status |
|---|---|---|---|
| ~~Speech~~ | **DFRobot DF2301Q** (SEN0539, `0x64`) | I²C (2nd bus, P18/P16) | **✅ implemented (0.3.0)** |
| Vision + pan/tilt head | [B0CX93M5DW](https://www.amazon.com/dp/B0CX93M5DW) | I²C | longer-term |
| Audio out | *(P2 smart-pin DAC/PWM)* | — | longer-term |
| BLE remote | [B0DRNSV5CS](https://www.amazon.com/dp/B0DRNSV5CS) / [B0GGB1L8N5](https://www.amazon.com/dp/B0GGB1L8N5) | SPI / I²C | longer-term (pick one) |

> **Pin/bus budget is not a constraint.** Only P8–P15 (robot signals) plus P16/P18 (the voice 2nd I²C
> bus) are in use today, so P0–P7, P17, and P19–P57 are open: an SPI BLE (~4 pins) fits easily, and more
> I²C devices just need distinct addresses on the existing masters.

---

## License

MIT License - See [LICENSE](../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
