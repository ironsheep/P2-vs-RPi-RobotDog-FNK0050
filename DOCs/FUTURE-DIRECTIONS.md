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

## 1. Speech recognition — *short-term, next up*

**What.** A speech-recognition **module** so the dog takes **spoken** commands — "sit", "shake",
"forward", "hello" — instead of only scripted/mailbox commands.

**Hardware candidate.** [amazon.com/dp/B0C5XG3BXW](https://www.amazon.com/dp/B0C5XG3BXW) — interface
**UART *or* I²C**.

**P2 integration.**
- **Prefer UART** if it exposes the richer stream (recognized phrase/ID **+ confidence**), vs an I²C
  "poll a result register" mode — confidence lets us gate noisy matches and support a larger
  vocabulary. UART drops onto a P2 smart-pin serial; I²C joins the existing bus.
- Recognized command → look up the matching `CMD_*` → `postCommand` into mailbox A/B. No motion change.

**Open questions.** Confirm what each interface mode actually returns; wake-word vs push-to-talk;
vocabulary mapping table (spoken phrase → `CMD_*`).

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

**What.** A wireless command link to replace the scripted demo orchestrator, driving the **same
mailbox command set** from a phone or gamepad — the first real realization of the still-**TODO**
"comms cog 0" the firmware reserves a seat for.

**Hardware candidates (pick ONE).** [amazon.com/dp/B0DRNSV5CS](https://www.amazon.com/dp/B0DRNSV5CS)
and [amazon.com/dp/B0GGB1L8N5](https://www.amazon.com/dp/B0GGB1L8N5) — interface **SPI / I²C**.

**P2 integration.** The **I²C** option shares the existing bus (distinct address); the **SPI** option
takes ~3–4 dedicated pins. Either way it posts the same `CMD_*` set into the mailboxes.

**Open questions.** Pick the module (SPI vs I²C, range/power); pairing + wire protocol.

---

## Hardware candidates at a glance

| Direction | Device | Interface | Status |
|---|---|---|---|
| Speech | [B0C5XG3BXW](https://www.amazon.com/dp/B0C5XG3BXW) | UART (richer) / I²C | short-term, next up |
| Vision + pan/tilt head | [B0CX93M5DW](https://www.amazon.com/dp/B0CX93M5DW) | I²C | longer-term |
| Audio out | *(P2 smart-pin DAC/PWM)* | — | longer-term |
| BLE remote | [B0DRNSV5CS](https://www.amazon.com/dp/B0DRNSV5CS) / [B0GGB1L8N5](https://www.amazon.com/dp/B0GGB1L8N5) | SPI / I²C | longer-term (pick one) |

> **Pin/bus budget is not a constraint.** Only P8–P15 are in use today, so P0–P7 and P16–P57 are
> open: a UART speech module (2 pins) plus an SPI BLE (~4 pins) fit easily, and the I²C devices just
> need distinct addresses on the existing master.

---

## License

MIT License - See [LICENSE](../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
