# P2 Robot Dog — Firmware Specifications

The behavioral contract of the Robot Dog (FNK0050) P2 firmware: the smooth-motion engine, the
gait catalog and its speed knob, the three-cog command + telemetry interface (mailboxes A and B),
and the IMU static-leveling behavior. This is the **as-built spec** for build 0.1.2 — what the
firmware *does* and how a caller drives it.

![doc-spec](https://img.shields.io/badge/doc-spec-informational?labelColor=black)
![platform-Propeller 2](https://img.shields.io/badge/platform-Propeller%202-blue?labelColor=black)
![PCB-v1.0](https://img.shields.io/badge/PCB-v1.0-orange?labelColor=black)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![license-MIT](https://img.shields.io/badge/license-MIT-green?labelColor=black)

> **Scope & authority.** This document owns the *firmware behavioral contract*. The **static**
> object/tier map lives in [`../../src/README.md`](../../src/README.md); the **runtime** cog/task
> model and mailbox protocol live in
> [`../P2_FIRMWARE_THEORY_OF_OPS.md`](../P2_FIRMWARE_THEORY_OF_OPS.md) (ToOps); hardware pin/rail
> facts live in [`../P2-platform/P2_MIGRATION_WIRING.md`](../P2-platform/P2_MIGRATION_WIRING.md). Where they overlap, those
> documents win for their domain and this one cites them.
>
> **Verification status.** All firmware here **compiles clean** (PNut-ts, full sweep). Behavioral
> correctness is proven on the bench via the verification playbook, not by an automated runner —
> items needing the bench are flagged **⚠ bench** inline.

---

## 1. Overview

The firmware runs as **three cogs** (ToOps §2): a comms/orchestrator cog (cog 0), the backend
body-control cog (cog 1, the sole I²C-bus owner), and the discrete-pin IO cog (cog 2). A caller on
cog 0 drives the robot **only** through two hub mailboxes — never by touching a bus or pin:

- **Mailbox A → backend** (`isp_robot_dog`): motion, posture, head, gestures; reports attitude,
  battery, mode.
- **Mailbox B → IO** (`isp_io_controller`): LED ring, buzzer, ultrasonic ranging; reports distance,
  ping sequence, LED-busy.

`src/robot_dog_top.spin2` is the first object to assemble all three cogs; it runs a scripted
demo orchestrator (a stand-in until the real Wi-Fi/serial command link is built).

---

## 2. The smooth-motion engine

**Quality bar:** beat Freenove's wobbly/staccato look (ToOps §6.1). The engine owns body-level
interpolation on one shared timebase so all joints start and arrive together — no per-servo slew,
no snaps, no gaps.

### 2.1 Contract

| Property | Value | Notes |
|----------|-------|-------|
| Frame rate | **50 Hz**, CT-gated | `FRAME_HZ`; one timebase for all 13 joints |
| Ease curve | smoothstep `3s² − 2s³` | fixed-point, `EASE_ONE = 4096`; shared `s: 0→1` |
| Pose duration | **30 frames** (~0.6 s) | `POSE_FRAMES` |
| Head-pan duration | **20 frames** (~0.4 s) | `HEAD_FRAMES` |
| Reachability guard | foot **25–130 mm** from hip | `REACH_MIN_MM`/`REACH_MAX_MM`; ported Freenove `checkPoint` |
| Write discipline | all legs + head per frame, between I²C transactions | never one leg at a time; never yields mid-transaction (ToOps §3) |

- **Poses** (stand/relax/sit/head) ease point-to-point: the move snapshots `start := current`,
  sets `target`, and `stepPose()` lerps every joint over the same frame count with the shared ease
  factor.
- **Gaits and gestures** write the four feet directly each frame from a Cartesian sinusoid (already
  smooth, so no easing is layered on) and commit through the same per-frame reachability guard.
- **Blending:** a new command eases from the *live* current pose — no stop-and-restart. `CMD_STOP`
  eases to the neutral stance, interrupting any running gait.
- **Power-on** seeds the neutral stance once (`seedStand`, a deliberate snap — there is no prior
  pose to blend from).
- **Reachability guard** scales any out-of-range foot back onto the reachable shell; the 0–180°
  servo-angle clamp in `isp_leg` is the belt-and-suspenders second line.

### 2.2 Neutral stance — the loaded-rear crouch

All trajectories are mapped onto a single **loaded-rear-crouch neutral** — the one source of truth
every pose eases to/from and every gait oscillates around, exposed by `neutralFootTarget(idx)` (and
`neutralFootY(idx)` for just the per-leg planted floor). It is **per-leg**, not one shared height:

| Legs | Foot X | Foot Y (extension) | Foot Z |
|------|--------|--------------------|--------|
| Front (FL/FR) | `NEUTRAL_FRONT_X_MM = 0` (under the shoulders) | `NEUTRAL_FRONT_Y_MM = 95` | ±`STANCE_LATERAL_MM = 10` (L +, R −) |
| Rear (BL/BR) | `NEUTRAL_REAR_X_MM = −12` (tucked toward the tail) | `NEUTRAL_REAR_Y_MM = 85` (folds deeper) | ±`STANCE_LATERAL_MM` |

The rear folds deeper (smaller Y) and tucks back (−X) against the `HALF_BODY_LENGTH_MM = 136` lever to
bias the weight **~60:40 forward** — a visibly loaded hindquarter, the dog-like resting crouch. All
four `NEUTRAL_*` are bench-tune knobs. `neutralFootTarget` folds each leg's static leveling trim
(`cal.stanceTrimY`) into Y, so it returns the level-corrected target. **Bench pitch decision (open):**
the crouch is meant to sit a touch nose-up; at leveling re-measure we either keep that intended
nose-up (leave the pitch trim ≈ 0) or flatten it (paste the measured pitch) — see §5.

`STAND_HEIGHT_MM = 99` is **no longer the neutral** — it is retained only as the *tall* stand
reference for the deliberately-tall sub-poses (SIT front, BOW rear, PARADE REST). Freenove's absolute
`changeCoordinates` offsets (+10 X, ±10 Z) are **not** applied — only its trajectory amplitudes and
phase shapes are ported.

---

## 3. Gait catalog

All gaits are **trotting**: diagonal pairs **A = {FL, BR}** and **B = {BL, FR}** run 180° out of
phase. Each is a **latched mode** (D1) — one command sustains it until `CMD_STOP` or another
command. Trajectories are ported from `REF/.../Control.py` onto the loaded-rear-crouch neutral
(§2.2); each foot's lift is clamped to its **own** planted floor (`Y ≤ neutralFootY(idx)` via
`plantFloor`), so a mixed diagonal pair keeps the front-vs-rear height difference while walking.
Stride X stays centred on 0 (the rear −X tuck is a static-neutral property, not part of the walking
trajectory).

| Gait | Command | Trajectory (per foot) | Amplitudes |
|------|---------|-----------------------|------------|
| Forward | `CMD_FORWARD` | X = A·cos(φ) stride, Y = L·sin(φ)+h lift | X `GAIT_X_AMPL_MM=12`, lift `GAIT_LIFT_MM=6` |
| Backward | `CMD_BACKWARD` | same shape, phase **decrements** | same as forward |
| Turn left | `CMD_TURN_LEFT` | X = A·cos(φ), Z coupled to X (yaw), Y = L·sin(φ)+h | XZ `TURN_XZ_AMPL_MM=3`, lift `TURN_LIFT_MM=8` |
| Turn right | `CMD_TURN_RIGHT` | turn-left mapping with X amplitudes negated | same |
| Step left | `CMD_STEP_LEFT` | X = 0, Z = A·cos(φ) added to lateral, Y = L·sin(φ)+h | Z `STEP_Z_AMPL_MM=10`, lift `STEP_LIFT_MM=5` |
| Step right | `CMD_STEP_RIGHT` | same shape, phase **decrements** | same as step-left |

> Each `Y = L·sin(φ)+h` uses **h = that leg's `neutralFootY(idx)`** (front 95 / rear 85, plus the
> leveling trim) — the per-leg planted floor, not one shared height; `plantFloor` clamps each foot to
> its own floor.
>
> ⚠ bench — the turn XZ amplitude (3 mm) is small but faithful to the reference; tune on the bench.

### Speed knob

Every gait takes **`arg0` = phase step (degrees/frame)** — the speed/smoothness knob. `0` selects
the default `GAIT_STEP_DEG = 15`; any other value is clamped to **`GAIT_SPEED_MIN..MAX = 3..45`**.
Smaller = slower and smoother (more frames per stride).

---

## 4. Command & telemetry interface

### 4.1 Mailbox A — backend (`isp_robot_dog`)

**Post:** `dog.postCommand(commandId, arg0, arg1, arg2, arg3)` — latest-wins, single slot; args are
written first and the sequence word last (lock-free publish, ToOps §4).

| Command | Value | arg0 | Effect |
|---------|-------|------|--------|
| `CMD_STOP` | 1 | — | ease to neutral stance, mode IDLE |
| `CMD_FORWARD` | 2 | speed | latched forward gait |
| `CMD_RELAX` | 3 | — | ease to tucked rest, mode RELAXED |
| `CMD_STAND` | 4 | — | ease to neutral stance, mode IDLE |
| `CMD_SIT` | 5 | — | ease to sit (rear lowered) |
| `CMD_HELLO` | 6 | — | one-shot wave (eased in/out); rejected while busy (D3) |
| `CMD_HEAD` | 7 | angle° | pan head (eases when idle; immediate during a gait) |
| `CMD_BACKWARD` | 8 | speed | latched backward gait |
| `CMD_TURN_LEFT` | 9 | speed | latched turn-left |
| `CMD_TURN_RIGHT` | 10 | speed | latched turn-right |
| `CMD_STEP_LEFT` | 11 | speed | latched sidestep-left |
| `CMD_STEP_RIGHT` | 12 | speed | latched sidestep-right |

> **One-shot gestures.** Beyond the motion set above, the backend exposes one-shot gesture
> commands (`CMD_HELLO`, `CMD_SHAKE`, `CMD_SALUTE`, `CMD_BOW`, …), each eased in/out and rejected
> while busy (D3). Behaviors to note:
> - **`CMD_BOW`** drops the front chest **and raises the head** (`BOW_HEAD_UP_DEG`, eased in
>   lock-step with the chest) so the snout clears the surface; on the **`BOW→STAND`** that leaves the
>   bow, the head **eases back to the angle it held at bow entry** (snapshotted into `savedHeadDeg`),
>   so a one-shot bow returns the head where it started — a deliberate `CMD_HEAD` posted while bowed
>   still wins.
> - The **paw gestures** (`CMD_SHAKE` / `CMD_SALUTE`) first **rebalance into a leaned sit** —
>   shifting the CoG into the FL/BL/BR tripod (`PAW_LEAN_LAT_MM`) — **before** lifting the front-right
>   paw; when the paw lowers they **ease the lean back out to a level, centered seated posture** (the
>   `GST_LEVEL_OUT` stage) so the gesture ends balanced, not frozen in its terminal tilt, and holds
>   that level sit until a later `CMD_STAND`/`CMD_STOP`.
> - **`CMD_HELLO`** waves the front-right foot with a **lift bias** (`HELLO_LIFT_MM`) so the whole
>   wave floats above the surface and the foot never contacts the floor, then re-levels to the neutral
>   stand on its way out.
>
> ⚠ bench — lean, head-raise, and wave-lift magnitudes are bench-tunable.

**Telemetry (getters, safe from any cog):**

| Getter | Returns |
|--------|---------|
| `getModeState()` | `MODE_IDLE/GAITING/GESTURE_BUSY/RELAXED/LOWBATT` (0–4) |
| `getBatteryMilliVolts()` | pack millivolts (median, divider undone) |
| `getAttitude()` | `pitchDeg, rollDeg` (accelerometer tilt; **pitch = fore/aft, roll = lateral** — see §5 axis mapping) |
| `isBusy()` | TRUE while a one-shot gesture runs |

### 4.2 Mailbox B — IO (`isp_io_controller`)

**Post:** `io.postCommand(commandId, arg0, arg1, arg2, arg3)` — same latest-wins/publish contract.

| Command | Value | arg0 | Effect |
|---------|-------|------|--------|
| `IO_LED_SOLID` | 1 | `$RRGGBB` | all pixels one color (static) |
| `IO_LED_MODE` | 2 | ring mode | set display mode; animated modes self-step |
| `IO_LED_BRIGHT` | 3 | 0–255 | brightness |
| `IO_LED_OFF` | 4 | — | blank the ring |
| `IO_BUZZ_BEEP` | 5 | ms | non-blocking beep (auto-off) |
| `IO_BUZZ_OFF` | 6 | — | silence |
| `IO_RANGE_ON` | 7 | interval ms (0=default) | start periodic ranging |
| `IO_RANGE_OFF` | 8 | — | stop ranging |

Ring modes (`IO_LED_MODE` arg0): `OFF/SOLID/WIPE/CHASE/RAINBOW/RAINBOW_CYCLE` (0–5); ≥ WIPE are
animated. The three color modes (`SOLID`/`WIPE`/`CHASE`) paint in a **default white** until an
`IO_LED_SOLID $RRGGBB` overrides the color, so they render visibly from a fresh boot (before any
color is posted); `RAINBOW`/`RAINBOW_CYCLE` self-color via the wheel.

**Telemetry:**

| Getter | Returns |
|--------|---------|
| `getDistanceMm()` | latest distance, mm (`NO_ECHO = −1` if the last ping found nothing) |
| `getPingSeq()` | ranging sequence (bumps each reading → readers detect freshness) |
| `isLedBusy()` | TRUE while an animated LED mode runs |

> ⚠ bench — the IO cog's **non-blocking smart-pin ranging path** (`startSmart`/`firePing`/
> `echoReadyMm`) is first exercised integrated by `robot_dog_top`; previously only the blocking
> menu path ran. Confirm live ranging (fresh `pingSeq`) on the bench.

### 4.3 Three-cog launch

`robot_dog_top.main()` runs on cog 0 and:

1. `cogspin` **IO** → cog 2: `io.start(WS2812=8, BUZZER=10, TRIG=11, ECHO=9)` (owns no bus → alive
   immediately).
2. `cogspin` **backend** → cog 1: `dog.start(SCL=13, SDA=15)` (inits, gyro-cals, stands).
3. Runs the scripted orchestrator: posts mailbox A and B concurrently and samples both telemetry
   regions — proving LED animation + live ranging + a gait + a beep run together with no stutter
   (D7). Pins per the as-built map (ToOps §2 / wiring §3).

---

## 5. IMU static leveling

A **static** measure → store → apply trim that makes the body stand level at neutral (not a live
closed loop).

- **Measure:** `src/test_dog_level.spin2` (production 3-cog shape, IO cog quiescent) commands the
  calibrated neutral stand, lets it settle, and averages `getAttitude()` over many samples → the
  measured pitch/roll ("how level is it").
- **Store:** the measured pitch/roll are captured into `isp_calibration` (`stancePitchDeg`,
  `stanceRollDeg`) the same way the servo trims were — metered values committed to source.
- **Apply:** `isp_calibration.stanceTrimY(legIdx)` converts the stored tilt into a per-leg foot-Y
  delta using the body lever arms — pitch over the fore/aft half-span (`HALF_BODY_LENGTH_MM = 136`),
  roll over the lateral half-span (`HALF_BODY_WIDTH_MM = 76`), small-angle `ΔY = lever·deg/57`. The
  backend folds these deltas into the neutral stand (`setLevelStandTargets`, used by both the eased
  `standPose` and power-on `seedStand`).
- **Confirm:** re-run `test_dog_level` after storing → residual tilt should be ≈ 0.

**Axis mapping.** The MPU6050 is **mounted rotated 90° in yaw** relative to the textbook X-forward
orientation, so the board's accelerometer **Y axis reads fore/aft** and **X reads lateral**.
`isp_imu.tiltDegrees()` therefore computes **pitch from accel Y** (fore/aft) and **roll from accel X**
(lateral) — `getAttitude()` returns pitch = fore/aft tilt (nose-up positive), roll = left/right tilt.
The fore/aft mapping was **bench-confirmed 2026-06-08** (`test_dog_panel`: a rear-down `SIT` drove
pitch positive, a front-down `BOW` drove it negative, while the lateral channel held the build's
residual). The **lateral (roll) sign is not yet confirmed** — no pure left/right tilt was in that run.

Sign convention (confirm on bench): **+pitch = front high** → lower front, raise back; **+roll =
left high** → lower left, raise right. Both trims default **0**, so the stance is unchanged until
metered.

> ⚠ bench — the IMU **roll (lateral) sign** and the captured trim values are bench-determined; verify
> the roll sign by tilting the body left/right. The fore/aft (pitch) mapping is confirmed; defaults are 0.

---

## 6. Safety floor

Backend-owned (D2), independent of frontend commands. **Two tiers:**

- **Soft advisory — < 6.4 V** (`LOW_BATTERY_CUTOFF_MV`): when the pack reads below the cutoff for
  `LOW_BATT_CONSECUTIVE = 3` consecutive reads (inrush sags are ignored), the backend **eases** to
  RELAX and reports `MODE_LOWBATT`. The forced rest uses the same eased pose path — no snap. The dog
  may still be re-commanded above the hard floor.
- **Hard floor — < 5.0 V** (`CRITICAL_BATTERY_MV`, F8): on **any** read below 5 V the backend runs a
  **confirm-burst** — 3 fresh reads with a wait between (`isCriticalLowConfirmed()`) so a single
  recovering sag does **not** trip it. If all 3 confirm, it logs **`"battery too low"`**, eases to
  RELAX, and **latches a refuse-motion HALT** (`isHalted()` TRUE) — further motion is ignored until
  reset/power-cycle. The orchestrator/panel polls `isHalted()` to **stop the whole run**, not just
  see a refused command. Bench-verified 2026-06-08 (the floor fired on a genuinely flat 4998 mV pack).

---

## 7. Constants reference (build 0.2.0)

| Constant | Value | Meaning |
|----------|-------|---------|
| `FRAME_HZ` | 50 | motion frame rate |
| `EASE_ONE` | 4096 | fixed-point 1.0 for ease/lerp |
| `POSE_FRAMES` / `HEAD_FRAMES` | 30 / 20 | eased pose / head-pan duration |
| `REACH_MIN_MM` / `REACH_MAX_MM` | 25 / 130 | reachability guard |
| `NEUTRAL_FRONT_Y_MM` / `NEUTRAL_REAR_Y_MM` | 95 / 85 | loaded-rear-crouch neutral foot extension (front / deeper-folded rear) — §2.2 |
| `NEUTRAL_FRONT_X_MM` / `NEUTRAL_REAR_X_MM` | 0 / −12 | neutral fore/aft (front under shoulders / rear tucked back → ~60:40 forward bias) — §2.2 |
| `STAND_HEIGHT_MM` | 99 | *tall* stand reference for SIT/BOW/PARADE sub-poses — **no longer the gait/pose neutral** (§2.2) |
| `STANCE_LATERAL_MM` | 10 | foot lateral offset (L +, R −) |
| `RELAX_X_MM` / `RELAX_HEIGHT_MM` | 55 / 78 | tucked rest pose |
| `SIT_FRONT_HEIGHT_MM` | 60 | sit: rear lowered |
| `GAIT_X_AMPL_MM` / `GAIT_LIFT_MM` | 12 / 6 | forward/backward stride / lift |
| `TURN_XZ_AMPL_MM` / `TURN_LIFT_MM` | 3 / 8 | turn fore-aft+lateral / lift |
| `STEP_Z_AMPL_MM` / `STEP_LIFT_MM` | 10 / 5 | sidestep lateral / lift |
| `GAIT_STEP_DEG` | 15 | default gait speed (deg/frame) |
| `GAIT_SPEED_MIN` / `GAIT_SPEED_MAX` | 3 / 45 | gait speed clamp |
| `HALF_BODY_LENGTH_MM` / `HALF_BODY_WIDTH_MM` | 136 / 76 | leveling lever arms |
| `BOW_HEAD_UP_DEG` | 35 | bow head-raise off center (F1); restored to `savedHeadDeg` on `BOW→STAND` (F5) |
| `PAW_LEAN_LAT_MM` | 16 | paw-gesture leaned-sit lateral CoG shift (F4); eased back out on finish (F6) |
| `HELLO_LIFT_MM` | 40 | HELLO wave lift bias so the foot floats off the floor (F7) |
| `LOW_BATTERY_CUTOFF_MV` | 6400 | soft low-battery advisory → ease to RELAX (§6) |
| `CRITICAL_BATTERY_MV` | 5000 | hard floor (F8): confirm-burst → `"battery too low"` + latched HALT (§6) |

---

## 8. Leg kinematics, servo characteristics & limits

Each leg is a **3-link chain** driven by three servos; the head is a single tilt servo. The leg servos
are **unmarked metal-gear micro servos (MG90S-class)**; the head is an **SG90** (plastic gear). **No
datasheet exists for the leg units — every value below was measured on the bench (2026-06-07)** and is
authoritative for these specific servos.

### 8.1 Servo µs ↔ angle

`0–180° = 500–2500 µs`, center `90° = 1500 µs` (matches Freenove `Servo.py`, counts 102/512 @ 50 Hz;
**corrected 2026-06 from a too-narrow 800–2200 µs that reached only ~126°** of travel). **Usable
drivable range ≈ ±80° from center (servo ~10–170°).** Past that the servo just stops responding — a
*pulse edge*, **no mechanical stop, no stall noise**; the gears free-spin further by hand with power off
(~190°/~340°), but that range is blind to the electronics and not commandable.

### 8.2 Leg geometry & axes

| Joint | Link | Length | Axis | Center (90°) | Moves the foot |
|---|---|---|---|---|---|
| Coxa (shoulder) | L1 | 23 mm | horizontal, **fore-aft** (along body) | down-and-out | **lateral ↔ vertical** (in / out / up) |
| Femur (thigh) | L2 | 55 mm | horizontal, **across** (lateral) | straight down | **fore ↔ aft** (stride) + extension |
| Tibia (knee→foot) | L3 | 55 mm | horizontal, **across** (lateral) | foot flat, toes-forward | extension / reach |

The coxa sets the leg's lateral-vertical *plane*; the femur and tibia move the foot fore-aft and in-out
*within* it (`footX` from the femur, `footZ/footY` from the coxa). All-servos-centered = femur vertical
+ foot flat = the natural low-torque "parade rest" pose.

### 8.3 Per-joint drivable clamps (enforced in `isp_leg`)

Both `setJointAngles` and `driveServoDegrees` clamp each joint to its measured drivable range, replacing
the old blanket 0–180°:

| Joint | Servo° clamp | Inward limit set by |
|---|---|---|
| Coxa | **65–170°** | the **body** (leg swings into it) |
| Femur | **10–170°** | none — full servo sweep |
| Tibia | **20–170°** | the **housing** (foot contacts ~15°) |

### 8.4 Calibration

Per-joint mounting offsets are stored as `legTrim` (+ `HEAD_TRIM_DEG`) in `isp_calibration`, applied at
leg init and added inside `setJointAngles`. They are found with the `test_cal_full` Cal tool (dial each
joint, `p` to dump, paste into `isp_calibration`); re-metered 2026-06 under the corrected 500–2500 µs
mapping. The tool starts **centered** (trims = 0) for from-scratch calibration; **`k`** loads the
committed values to dial poses relative to true neutral; **`C`** re-centers.

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
