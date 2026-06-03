[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Smooth-Motion + 3-Cog + IMU-Leveling — Bench Verification Playbook

The on-hardware proof for the **smooth-motion / 3-cog integration / IMU-leveling** sprint
(build **0.1.1**). Every exercise drives the robot **through the production backend mailboxes**
(`dog.postCommand` / `io.postCommand`) via scripted headless driver tops — never a bespoke servo
shortcut path ([[production-path-testing]]). Run it when you are at the bench; results here are
what lets `sprint-closeout` report "verified on the canonical target."

![doc-test](https://img.shields.io/badge/doc-test-informational?labelColor=black)
![platform-Propeller 2](https://img.shields.io/badge/platform-Propeller%202-blue?labelColor=black)
![PCB-v1.0](https://img.shields.io/badge/PCB-v1.0-orange?labelColor=black)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![license-MIT](https://img.shields.io/badge/license-MIT-green?labelColor=black)

> **Build:** ships as **0.1.1** (`FW_VERSION_*` in `src/isp_version.spin2`).
> **Target:** the **P2 bench unit** — one P2 Edge on the adapter plate, **battery connected**
> (the board regulates 5 V → 3.3 V from the pack; do not power the P2 from USB alone for servo
> tests), **Load/servo switch ON**, USB serial to the **programming port**.
> **Terminal:** **2 Mbaud (2,000,000)**, 8-N-1 — the project standard for all P2 comms.
> **Est. run time:** ~30–40 min (four driver flashes + an opportunistic low-battery check).

> **Relationship to the standing bring-up playbook.** `DOCs/P2_BRINGUP_PLAYBOOK.md` proves each
> driver **standalone** (I²C, IMU, buzzer, LED, ultrasonic, servos, one leg). **Run that green
> first** — this playbook assumes every subsystem already passed there and now exercises them
> **integrated, through the production mailboxes**, against this sprint's behavioral contract
> (`DOCs/spec/P2-RobotDog-Specifications.md`).

---

## >> LIFT / SUPPORT THE ROBOT << — read before every motion exercise

Every exercise below **moves servos**. On launch each driver calibrates the gyro (hold the body
**still and level**) and then **STANDS via IK**, after which it walks/poses on its own schedule.

1. **Lift and support the robot** so the legs hang free, or stand it where a stumble can't fall it
   off the bench. Keep hands clear of the joints once it starts.
2. **Load/servo switch ON** — the buzzer **and** the HC-SR04 ultrasonic are on the Load rail; the
   "logic-only" mode powers neither.
3. **HC-SR04 ECHO is 5 V undivided** → reaches **P9 through the ~1 kΩ inline series resistor**
   (P2 pin clamps to VIO, ≤ 10 mA). Confirm that resistor is in line before powering the Load rail
   (`DOCs/P2_MIGRATION_WIRING.md` §4).
4. **Battery, not USB**, powers the servos. A sagging pack will brown-out mid-gait — start each
   run on a healthy pack (and see Exercise 6 for the low-battery behavior).

---

## Headless run recipe (the project convention)

Each driver is a **scripted, self-running top** that emits P2 `DEBUG()` at 2 Mbaud and **exits on
its end-marker**. Build to RAM, then run headless ([[headless-debug-baud]] — the `-b 2000000` is
**required**; without it the 2 Mbaud DEBUG is garbage):

```bash
pnut-ts -d -q src/<driver>.spin2
pnut-term-ts -r src/<driver>.bin -b 2000000 --headless --end-marker "<MARKER>" --timeout <s>
```

| Driver | End-marker | Timeout | Proves (plan §) |
|---|---|---|---|
| `src/test_backend.spin2`        | `TEST_DONE` | 70  | engine smoothness + eased poses (§1, §2) |
| `src/test_level.spin2`          | `TEST_DONE` | 70  | IMU static leveling: measure → trim → re-measure (§5) |
| `src/test_gaits.spin2`          | `TEST_DONE` | 120 | full gait catalog + speed knob (§3) |
| `src/isp_robot_dog_top.spin2`   | `DEMO_DONE` | 90  | 3-cog concurrency + blend + smart-pin ranging (§4, §2-blend) |

Logs land in `logs/`. Record each exercise's pass/fail and the captured numbers inline.

---

## Exercise 0 — Automated gate (compile sweep) — *run first*

- **Verifies:** the only automated gate — every `src/*.spin2` object compiles clean. A red sweep
  stops the playbook before it spends bench time on firmware not known-good.
- **Targets:** host only (no hardware).
- **Action:**
  ```bash
  cd "$(git rev-parse --show-toplevel)"
  rc=0; for f in src/*.spin2; do pnut-ts -q "$f" || rc=1; done; rm -f src/*.bin; echo "rc=$rc"
  ```
- **Expected:** every object compiles, `rc=0`, no errors/warnings (39/39 with this sprint's
  `test_gaits.spin2` added). Any failure ⇒ fix before flashing anything.
- **Pass/fail:** `[ ]`   objects compiled: ____ / ____

---

## Exercise 1 — Engine smoothness: eased poses (no snap)

- **Verifies:** §1 fixed-rate eased engine + §2 poses retrofitted onto it — RELAX→STAND→SIT→STAND
  and a head pan, all **gapless** (the "beat Freenove's staccato" bar). `«#3320»`, `«#3321»`.
- **Targets:** 1 P2 bench unit, all 13 servos, battery, Load ON.
- **Driver:** `src/test_backend.spin2` → `TEST_DONE` (timeout 70). Sequence it posts:
  init STAND → `CMD_RELAX` → `CMD_STAND` → `CMD_SIT` → `CMD_STAND` → head pan 60/120/90.
- **Setup:** Robot lifted/supported, held still & level during the "calibrating gyro" countdown.
- **Action:** Flash & run the driver headless. Watch the body through each transition; watch the
  console telemetry (`mode=`, `tilt p/r`). Compare the motion qualitatively against a Freenove
  stock-firmware demo clip.
- **Expected:** Each transition **eases in and out** (all joints start and arrive together) with
  **no snap** at either end and **no stop-and-hold gap** between the named poses; visibly smoother
  / less staccato than the Freenove clip. Telemetry shows `mode=0` (IDLE) at rest, `mode=3`
  (RELAXED) after `CMD_RELAX`. Head pans smoothly to each angle.
- **Pass/fail:** `[ ]`   Gapless vs Freenove? ____   Any snap seen at a boundary? ____

## Exercise 2 — IMU static leveling: measure → trim → re-measure

- **Verifies:** §5 — measure body tilt at the calibrated neutral stand, apply the per-leg foot-Y
  stance trim, confirm residual ≈ 0. `«#3324»`. This exercise also **captures** the stance-trim
  values that get committed to `isp_calibration.spin2`.
- **Targets:** 1 P2 bench unit, all 12 leg servos, IMU, battery, Load ON.
- **Driver:** `src/test_level.spin2` → `TEST_DONE` (timeout 70). It echoes the currently-compiled
  stance trim, commands `CMD_STAND`, settles, then averages `getAttitude()` over 32 samples.
- **Setup:** **CRITICAL — the body must be on a level surface (or held truly level) and still.**
  The measurement *is* the tilt of the body relative to gravity; a tilted bench corrupts the trim.
- **Action — measure pass (trim still 0):**
  1. Confirm `isp_calibration` `stancePitchDeg`/`stanceRollDeg` are **0** (the harness prints
     "trim is 0 → this MEASURE is the RAW un-leveled tilt").
  2. Flash & run. Record `pitch avg` and `roll avg` (the `x10` tenths-of-a-degree figures give
     sub-degree resolution).
- **Action — apply & re-measure:**
  3. Paste the measured `pitch avg` / `roll avg` into `isp_calibration.spin2`
     `stancePitchDeg` / `stanceRollDeg`. Rebuild (`pnut-ts -q src/isp_calibration.spin2` clean).
  4. Re-run the driver. The harness now prints "trim applied → this MEASURE is the RESIDUAL tilt;
     expect ~0."
- **Expected:** Measure pass reports a non-trivial tilt; after applying the trim and re-running,
  the **residual pitch/roll is near 0** (small band). If residual grew, **negate** the pasted
  values and re-run (sign convention is bench-confirmed here).
- **Pass/fail:** `[ ]`
  - Raw measured: pitch ____° (×10 ____)  roll ____° (×10 ____)
  - Residual after trim: pitch ____°  roll ____°
  - **Values committed to `isp_calibration`:** stancePitchDeg = ____  stanceRollDeg = ____

## Exercise 3 — Full gait catalog + speed knob

- **Verifies:** §3 — every gait runs a stable trot in the correct direction, and the speed arg
  visibly changes cadence without losing smoothness. `«#3322»`.
- **Targets:** 1 P2 bench unit, all 12 leg servos, battery (healthy — gaits draw the most current),
  Load ON.
- **Driver:** `src/test_gaits.spin2` → `TEST_DONE` (timeout 120). It posts each latched gait for
  ~4 s, `CMD_STOP`-easing to neutral between them, then a FORWARD slow (arg0=5) vs fast (arg0=30)
  speed segment.
- **Setup:** Robot lifted/supported so the feet swing free; you judge direction by the **swing
  direction of the diagonal trot pairs** (A={FL,BR}, B={BL,FR}, 180° out of phase).
- **Action:** Flash & run. For each gait segment watch the leg trajectories and the console
  (`mode=1` = GAITING while a gait runs; back to `mode=0` after each `CMD_STOP`):
  | Gait | Expected foot motion |
  |---|---|
  | FORWARD     | fore/aft stride, trot pairs swing the body **forward** |
  | BACKWARD    | same shape, **reversed** phase (backward) |
  | TURN LEFT   | small fore/aft **+ lateral coupled** swing, yaw **left** |
  | TURN RIGHT  | same, yaw **right** |
  | STEP LEFT   | lateral swing, sidestep **left**, ~no fore/aft |
  | STEP RIGHT  | lateral swing, sidestep **right** |
- **Expected:** Each gait trots in the **right direction**, smoothly, with the swing-foot lift
  visible; no joint slams to a limit (reachability guard holds). In the speed segment, **slow**
  (arg0=5) is an obviously slower, smoother cadence than **fast** (arg0=30); both stay smooth.
  Between gaits the `CMD_STOP` **eases** back to neutral (blend, no snap — see Exercise 4).
- **Pass/fail:** `[ ]`   FWD __ BACK __ TURN-L __ TURN-R __ STEP-L __ STEP-R __  Speed differs? __

## Exercise 4 — 3-cog concurrency + blend + smart-pin ranging

- **Verifies:** §4 — all three cogs live at once (cog0 orchestrator, cog1 backend/I²C, cog2
  IO/discrete pins): **LED animation + live ranging + a gait + a beep simultaneously with no
  hitching** (D7); the **non-blocking `startSmart` ranging path** working **integrated** (flagged
  UNPROVEN on hardware until this passes); and **blend** — a new command mid-gait eases without a
  stop-and-restart (§2-blend, `«#3321»`). `«#3323»`.
- **Targets:** 1 P2 bench unit — full robot: 13 servos + WS2812 ring + buzzer + HC-SR04, battery,
  Load ON, **~1 kΩ series R into P9 confirmed**.
- **Driver:** `src/isp_robot_dog_top.spin2` → `DEMO_DONE` (timeout 90). Scripted phases:
  - **Ph1** IO alone: LED rainbow-cycle + periodic ranging starts (dog idle).
  - **Ph2** FULL concurrency: `CMD_FORWARD` gait **+** LED animating **+** ranging **+** a beep.
  - **Ph3** blend: `CMD_TURN_LEFT` (mid-gait) + LED chase + head pan to 60 + beep, still ranging.
  - **Ph4** `CMD_STOP` eases to neutral + head recenters; IO keeps animating + ranging.
  - wind-down: `CMD_RELAX` + ranging/LED/buzzer off.
- **Setup:** Robot lifted/supported; a hand/target within ~10–300 mm of the HC-SR04 so ranging has
  something to read.
- **Action:** Flash & run. Watch all four behaviors at once and the per-sample telemetry lines:
  `A: ... mode= tilt p/r` (backend) and `B: dist= pingSeq= fresh= ledBusy=` (IO).
- **Expected:**
  - **Concurrency:** the rainbow/chase animates **smoothly while** the gait runs and a beep fires
    — no hitch in any of the three; the ~210 µs LED frame and the beep do not disturb motion.
  - **Ranging live (the unproven path):** `dist=` tracks your hand and **`pingSeq` advances**
    between samples (`fresh=1` repeatedly) **while the gait runs** — proof the non-blocking
    smart-pin path works integrated. `fresh=0` every sample or a stuck `dist` ⇒ ranging not live;
    record it (this is the headline unproven item).
  - **Blend:** Ph2→Ph3 (FORWARD→TURN_LEFT) changes gait with **no pause/restart**; Ph4
    (`CMD_STOP`) **eases** the live gait to the neutral stance — no snap.
  - `mode=` shows `1` (GAITING) during Ph2/Ph3 and `0`/`3` after STOP/RELAX.
- **Pass/fail:** `[ ]`
  - LED + gait + beep concurrent, no hitch? ____
  - Ranging live integrated — `pingSeq` advances / `fresh=1` during the gait? ____  dist@hand ____ mm
  - Blend (FWD→TURN no restart; STOP eases)? ____

## Exercise 5 — Safety floor: low battery eases to RELAX — *opportunistic*

- **Verifies:** §2/§6 — when the pack drops below cutoff the backend forces rest, and that forced
  relax **eases (does not snap)**; mode reports `MODE_LOWBATT`. `«#3321»` (eased
  `applySafetyFloor`).
- **Targets:** 1 P2 bench unit on a **near-depleted** pack.
- **Trigger detail:** `senseTask` reads the battery every ~50 passes; after
  **3 consecutive** reads `< 6400 mV` (`LOW_BATTERY_CUTOFF_MV`; inrush sags are ignored) it forces
  `relaxPose()` **once** and sets `modeState = 4` (`MODE_LOWBATT`).
- **⚠ Caution:** do **not** over-discharge a LiPo to force this. Run it **opportunistically** when
  a pack has naturally drained near 6.4 V (any motion driver above will do), or on a bench supply
  set just under 6.4 V. Do not deep-discharge a good pack just to test.
- **Setup:** Pack/supply at/just below ~6.4 V; robot supported.
- **Action:** Run any motion driver (e.g. `test_backend`) and watch the telemetry `battery=` and
  `mode=` once the reading sits below 6400 mV for several samples.
- **Expected:** After 3 consecutive low reads the body **eases to the relax/tuck pose** (smooth,
  not a snap) and telemetry shows `mode=4` (LOWBATT); it stays latched there.
- **Pass/fail:** `[ ]`   batt at trip ____ mV   eased (not snapped)? ____   mode→4? ____

---

## Results → closeout

Record `[x]`/`[ ]` and the captured numbers inline. A failed exercise is a **finding**: the
default is to **fix it before the sprint closes** (it goes back into sprint work); a carried-over
failure is added to `DOCs/plans/PUNCH-LIST.md` as a new active item. **When a run surfaces more
than one wrong behavior, gather the whole symptom set first**, then hand it to `defect-fixing` as
one inventory — multiple manual-test failures often share one root cause. `sprint-closeout` reads
these results to report verification state honestly.

**Coverage note (no silent caps).** This sprint's only automated gate is the Exercise 0 compile
sweep; behavioral correctness is proven **only** by the bench exercises above. The §4 non-blocking
smart-pin ranging path is **first proven here** (Exercise 4) — until that passes it remains
unproven on hardware. Exercise 5 is **opportunistic** (it depends on pack state) and is the one
exercise without a dedicated, repeatable trigger.

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
