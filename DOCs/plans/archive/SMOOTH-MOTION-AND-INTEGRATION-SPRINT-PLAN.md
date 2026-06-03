[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Smooth-Motion Engine + 3-Cog Integration + IMU Leveling — Sprint Plan

> **🏁 CLOSED 2026-06-03** — all 7 sections SHIPPED (build 0.1.1). Audit:
> [`archive/2026-06-03-SMOOTH-MOTION-AND-INTEGRATION-CLOSEOUT.md`](2026-06-03-SMOOTH-MOTION-AND-INTEGRATION-CLOSEOUT.md).
> Code-complete + compile-clean (39/39); on-hardware behavioral verification pending the bench playbook.

> **Project:** P2 Robot Dog (FNK0050 → Propeller 2 port) · firmware in Spin2/PASM2
> **Plan type:** sprint plan (a ship commitment — real code changes)
> **Build version:** ships as **0.1.1** (agreed at sprint-start; `FW_VERSION` in `src/isp_version.spin2`, from `0.1.0`).
> **North star:** visibly **beat Freenove's staccato demo motion** — fluid, gapless, deterministic.

This sprint converts the backend from *snap-then-wait* motion to a real **fixed-rate, eased,
blendable motion engine**, ports the **full reference gait catalog** onto it, brings the **IO
cog online** for the first time (full 3-cog runtime), and closes the dropped **IMU level
check** by measuring tilt at neutral and applying a static stance trim so the dog stands level.

## Settled scope decisions (owner: Stephen)

1. **Gait neutral:** keep the **hardware-verified X = 0 neutral** (commit `48229eb`). Port the
   reference trajectory *shapes* (amplitudes + phase) only — **drop** Freenove's absolute
   `+10` X / `±10` Z offsets baked into `changeCoordinates`.
2. **Comms scope:** prove the 3-cog architecture with a **scripted top-level orchestrator**
   (posts to mailbox A + B). A real Wi-Fi/serial command link (cog 0) is **deferred**.
3. **IMU leveling:** **static** — measure tilt once at neutral, compute per-leg foot-Y deltas
   that null it, persist in `isp_calibration`, apply at every stand. Live closed-loop IMU
   balance remains a future item.
4. **Documentation:** create the first **`DOCs/spec/P2-RobotDog-Specifications.md`** this
   sprint, **and** update Theory-of-Ops + `src/README` + author the bench playbook.

## Verification model (whole sprint)

- **Automated gate (in-container):** clean `pnut-ts` **compile sweep** over `src/*.spin2`
  (the `BUILD_COMMAND`/`TEST_COMMAND` in `.claude/skill-conventions.md`). This is the only
  automated check — there is no behavioral test runner.
- **Real verification (bench, Stephen-run):** the §7 **hardware bench playbook**. Per
  [[production-path-testing]], every behavior is exercised **through the real backend mailbox
  on the production path** — not via bespoke shortcut harnesses. **Do not assume Stephen is at
  the bench during development;** the playbook is authored for him to run when ready.
- Bump `FW_VERSION` (`src/isp_version.spin2`, currently `0.1.0`) as part of §6.

---

## 1. Motion engine core — fixed-rate, eased, blendable interpolator

**Why.** Today motion *snaps*: poses write final angles in one shot
(`isp_robot_dog.spin2:266-291` → `standPose`/`relaxPose`/`sitPose` `:361-377`), and
`motionTask` (`:222-233`) advances gaits **once per cooperative pass with no wall-clock
gating** — so frame timing is whatever the scheduler happens to do. This section builds the
foundation every other motion section rides on. Per `DOCs/P2_FIRMWARE_THEORY_OF_OPS.md` §6.1,
coordination lives at the **body** level (`isp_robot_dog` is the conductor; `isp_leg` stays the
IK/angle provider). We deliberately **do not** use the per-servo S-curve slew that already
exists in `isp_i2c_pca9685_servo.spin2:412/232` — it cannot share one body timebase across 12
joints.

**Current starting point.**
- `motionTask` `isp_robot_dog.spin2:222-233` — case on `activeMode`, no timebase.
- Poses snap through `allLegsToXYZ` `:379-390` → `flLeg.moveToXYZ(...)` etc.
- `isp_leg.moveToXYZ` `isp_leg.spin2:151-203` is the per-leg IK (CORDIC); outputs clamped to
  0–180° in `setJointAngles` `:123-149`. **No reachability guard** before the clamp.
- The IO cog already demonstrates the wrap-safe CT pattern to reuse: `due(deadlineTick)`
  `isp_io_controller.spin2:254-260` and `getct()` cadence gating.

**Target behavior.**
- **Body-level state arrays** (backend-cog DAT): `currentXYZ[4][3]` and `targetXYZ[4][3]` (foot
  X/Y/Z per leg, leg order FL/BL/FR/BR to match the existing leg objects) plus head
  current/target. A move sets `targetXYZ` (+ a duration in frames); the frame loop walks
  `current → target`.
- **Fixed-rate frame loop:** `motionTask` gates each frame on a `getct()` deadline at
  **~50 Hz** (`FRAME_MS`/`FRAME_TICKS`, wrap-safe via the `due()` pattern). Every frame it
  advances the active motion and **writes all 12 leg joints + head together** — never one leg
  at a time. It still `tasknext()`s so `senseTask`/`dispatchLoop` keep running (yield discipline
  per Theory-of-Ops §3 — never mid-I²C-transaction).
- **Ease-in/out:** a normalized `s : 0→1` over the move's frames, shaped by an **S-curve**
  (e.g. smoothstep `3s²−2s³`, integer fixed-point). All joints share one `s` so they **start
  and arrive together** (synchronized timing). This is our refinement over Freenove's linear
  steps.
- **Joint-space lerp primitive** (poses) and a hook for **Cartesian per-frame IK** (gaits, §3).
- **Reachability guard (port `checkPoint`, `Control.py:122`):** before committing a frame's
  foot targets, validate each leg's reach is within **25–130 mm** of the hip; clamp/skip
  illegal targets. Belt-and-suspenders with the existing servo-angle clamp.
- **Blending:** a new command eases from **`current` (wherever the body is *now*)** into the new
  target — no stop-and-restart. `current` is always live, so an interrupted move blends cleanly.

**Integration points.** `motionTask`, the pose methods, gait advance, and gesture advance all
become *producers of `targetXYZ`*; the frame loop is the single writer to the legs. `dispatchLoop`
/`consumeCommand` set targets + mode, never write servos directly.

**Verification.** Compile-clean. Bench (§7): a stand→sit→stand cycle is visibly smooth with no
snap; a mid-move command change blends without a stop.

---

## 2. Retrofit poses & the hello gesture onto the engine (kill every snap)

**Why.** Once the engine exists, the existing motions must stop snapping. Poses currently write
final angles inside `consumeCommand` (`isp_robot_dog.spin2:266-291`); the hello gesture
(`advanceHello` `:340-350`) is already per-frame but **snaps at start/end** and `finishGesture`
`:352-359` hard-stands.

**Current starting point.**
- `consumeCommand` `:258-291`: CMD_STAND/STOP→`standPose`, CMD_RELAX→`relaxPose`,
  CMD_SIT→`sitPose`, CMD_HELLO→sets gesture state.
- Pose geometry CONs `:55-70` (`STAND_HEIGHT_MM=99`, `STANCE_LATERAL_MM=10`, `RELAX_*`,
  `SIT_FRONT_HEIGHT_MM=60`) — **unchanged**; only how they're *reached* changes.

**Target behavior.**
- `standPose`/`relaxPose`/`sitPose` set **`targetXYZ` + a duration** (N-step eased lerp via §1),
  not direct writes. STAND/STOP/RELAX/SIT all ease in.
- **STOP eases to neutral** (Theory-of-Ops §6 "ease to neutral stance"), interrupting any gait
  via the §1 blend.
- **Hello** eases into the wave start pose, oscillates (keep the `qsin` wave), then eases back to
  stand on `finishGesture` — no snap at either boundary. `busyFlag` semantics (D3 reject-while-busy)
  preserved.

**Integration points.** `consumeCommand`, `finishGesture`, `applySafetyFloor` (the low-batt
forced RELAX `:293-303` should also ease, not snap).

**Verification.** Compile-clean. Bench (§7): RELAX→STAND→SIT→STAND and a HELLO all fluid;
low-batt forced relax eases.

---

## 3. Port the full gait catalog onto the engine

**Why.** Stephen's call: port the **whole** reference gait catalog now (the trajectory math is
right there in `Control.py`). Today only a forward trot exists (`advanceGait`
`isp_robot_dog.spin2:305-329`).

**Current starting point.**
- `advanceGait` already matches the reference **forward** shape: `X=12cos`, `Y=6sin+h`, diagonal
  pairs {FL,BR} & {FR,BL} 180° apart, `GAIT_STEP_DEG=15` phase advance.
- Reference catalog (from `Control.py`, extracted): **forward** `X=12cos,Y=6sin+h`;
  **backward** same shape, phase decrements; **turnLeft/Right** `X=3cos,Y=8sin+h,Z=X` (X/Z
  coupled for yaw); **stepLeft/Right** `Z=10cos,Y=5sin+h,X=0`; all trot; `self.speed` default
  **8°/step**; foot-lift clamp `Y ≤ height`.

**Target behavior.**
- Implement **backward, turnLeft, turnRight, stepLeft, stepRight** as Cartesian phase
  trajectories driven by the §1 per-frame IK path, alongside the existing forward.
- **Map onto our verified X=0 / Z=±`STANCE_LATERAL_MM` neutral** (decision #1) — port amplitudes
  + phase + the `Y ≤ STAND_HEIGHT_MM` lift clamp; **do not** add Freenove's `+10`/`±10` offsets.
- **Speed knob:** expose `self.speed` as a gait command **arg0** (phase-degrees/frame), default
  to the current value; clamp to a sane range. Add the new commands to the CMD_* enum
  (`:32-43`) and mode handling, mirroring CMD_FORWARD's latched-mode pattern (D1).
- Diagonal-pair phase (180°) preserved for all trotting gaits; turn gaits add the Z=X coupling.

**Integration points.** CMD_* enum + `consumeCommand` + `motionTask` gait dispatch; the §1 frame
loop and reachability guard; `isp_leg.moveToXYZ`.

**Verification.** Compile-clean. Bench (§7): each gait executes a stable trot in the right
direction; speed arg visibly changes cadence without losing smoothness.

---

## 4. 3-cog integration — bring the IO cog online + scripted orchestrator

**Why.** The IO cog (`isp_io_controller.spin2`) is **fully built and non-blocking** (LED P8,
buzzer P10, smart-pin ultrasonic ECHO P9/TRIG P11 via `sonic.startSmart`/`firePing`/`echoReadyMm`)
but **has never been launched** — `grep cogspin` finds only `test_backend.spin2:36` launching the
dog. This section realizes the documented **3-cog runtime** (Theory-of-Ops §2 cog map: cog 0
comms, cog 1 backend/I²C, cog 2 IO/discrete pins) and proves concurrency with no hitching (D7).

**Current starting point.**
- `isp_robot_dog.start` `:125-158` → cog 1 (I²C owner), mailbox A.
- `isp_io_controller.start(led,buzz,trig,echo)` `:92-111` → cog 2 (discrete pins), mailbox B;
  service loop `:157-165` already steps LED + buzzer + ranging non-blocking.
- `test_backend.spin2` is the existing single-cog launcher/driver pattern to generalize.

**Target behavior.**
- **New integrated top object** (e.g. `isp_robot_dog_top.spin2`) whose `main()` runs on **cog 0**
  and:
  - `cogspin`s `isp_robot_dog.start(PIN_SCL, PIN_SDA)` → cog 1, and
    `isp_io_controller.start(PIN_WS2812, PIN_BUZZER, PIN_TRIG, PIN_ECHO)` → cog 2 (pins per the
    as-built map: LED P8 / ECHO P9 / buzzer P10 / TRIG P11 / SCL P13 / SDA P15).
  - Runs a **scripted demo orchestrator**: posts mailbox-B (`IO_LED_MODE` animation,
    `IO_RANGE_ON`, `IO_BUZZ_BEEP`) **and** mailbox-A (a gait + pose sequence) concurrently, and
    reads telemetry (`getDistanceMm`/`getPingSeq` + attitude/mode) — demonstrating LED animation
    + live ranging + motion + a beep all running together with no stutter.
- Confirm the smart-pin ranging path works in the integrated build (it has only ever run via the
  blocking `readDistanceMm` menu test `isp_dog_bringup.spin2:221-236`; the **non-blocking
  `startSmart` path is unproven on hardware** — flag for bench attention).

**Integration points.** Both backend mailboxes (A `:91-99`, B `:59-64`); pin map CONs; cog
stacks. No change to the bus-owner / pin-owner contract.

**Verification.** Compile-clean. Bench (§7): with all three cogs live, LED animates smoothly
while ranging publishes fresh `pingSeq` and a gait runs and a beep fires — visually no hitching
in any of them.

---

## 5. IMU level check at neutral + static stance trim (the dropped TODO)

**Why.** The roadmap's deferred item: stand at calibrated neutral, see how level the robot
actually is, and correct it. `imu.tiltDegrees()` (`isp_imu.spin2:175`) gives accel pitch/roll,
but there is **no leveling mechanism** — `calibrateGyro` only removes gyro bias, and
`isp_calibration` has per-joint + head trims (`legTrims` `:47`, `headTrim` `:64`) but **no body
pitch/roll stance trim**. So the correction is a new capability.

**Current starting point.**
- `getAttitude()` `isp_robot_dog.spin2:190-197` exposes the latest pitch/roll from `senseTask`.
- Stand neutral is set in `standPose` → `allLegsToXYZ(0, STAND_HEIGHT_MM, ±STANCE_LATERAL_MM)`.
- Body geometry for the tilt→foot-Y mapping: length ≈ **136 mm**, width ≈ **76 mm** (reference
  `Control.py`).

**Target behavior.**
- **Measure:** a routine that commands the calibrated neutral stand, lets it settle, and reads
  `tiltDegrees()` (averaged over several samples) → measured pitch/roll. Report it (this *is* the
  "how level is it" answer).
- **Apply (static):** convert measured pitch/roll → **per-leg foot-Y deltas** (pitch → front-vs-
  back Y offset using half-length; roll → left-vs-right Y offset using half-width), persist as a
  **new stance-trim slot in `isp_calibration`**, and add the deltas into `standPose`'s neutral so
  the body stands level. One-time measure → store → apply.
- Re-measure after applying to confirm residual tilt ≈ 0.

**Integration points.** `isp_calibration` (new stance-trim accessor + stored values),
`isp_robot_dog.standPose`/`allLegsToXYZ`, `senseTask` attitude mailbox, the §7 playbook captures
the measured values like the existing servo-trim capture flow.

**Verification.** Compile-clean. Bench (§7): record pitch/roll before trim, apply, re-measure —
residual within a small target band; stance visibly level.

---

## 6. Documentation — spec doc (new) + Theory-of-Ops + README + version

**Why.** Documentation is a sprint deliverable. This sprint changes the motion model, adds the
full gait catalog, brings the IO cog online, and adds IMU leveling — all must be recorded.

**Deliverables.**
- **Create `DOCs/spec/P2-RobotDog-Specifications.md`** (decision #4; the designated SPEC home,
  not yet authored). First content: the motion engine contract (fixed-rate frames, ease,
  blend), the gait catalog + speed knob, the 3-cog/mailbox-A/B command + telemetry contract, and
  the IMU leveling behavior. Follow the project markdown house style ([[markdown-house-style]]:
  badge header + License/collection footer).
- **Update `DOCs/P2_FIRMWARE_THEORY_OF_OPS.md`:** promote §6.1 from *implementation guide* to an
  **as-built §6.2** (what the engine actually does); update the cog map / §2 note now that the IO
  cog is launched in the integrated top; refresh §9 open-items.
- **Update `src/README.md` §3** (motion/IK ownership) for the engine + catalog + integrated top.
- **Bump `FW_VERSION`** in `src/isp_version.spin2` (`0.1.0` → `0.1.1`).

**Verification.** Docs render; cross-references resolve; spec matches the shipped code.

---

## 7. Hardware bench verification playbook

**Why.** The compile sweep is the only automated gate; real proof is on the bench, and Stephen
runs it when ready. Authoring the playbook is a deliverable (via the `test-playbook` skill).

**Deliverables.** A numbered, pass/fail-keyed exercise doc that drives **everything through the
production backend mailboxes** ([[production-path-testing]]), covering:
1. Engine smoothness — stand/sit/relax transitions are gapless (the "beat Freenove's staccato"
   bar; compare against a Freenove demo clip qualitatively).
2. Blend — issue a new command mid-move; confirm no stop-and-restart.
3. Each gait (forward/backward/turnL/turnR/stepL/stepR) + the speed arg.
4. 3-cog concurrency — LED animation + live ranging + gait + beep simultaneously, no hitching;
   confirm the **non-blocking `startSmart` ranging path** works integrated.
5. IMU leveling — measured pitch/roll before/after trim; record the stance-trim values captured.
6. Safety floor still eases to RELAX on low battery.

Include the `>> LIFT/SUPPORT THE ROBOT <<` safety preamble (servo motion) and the headless run
recipe (`pnut-term-ts ... -b 2000000`, [[headless-debug-baud]]).

**Verification.** Playbook is complete and runnable end-to-end by Stephen at the bench.

---

## Out of scope (explicit)

- Real Wi-Fi/serial **command link** (cog 0 comms) — deferred (decision #2).
- **Live closed-loop IMU balance** — deferred; this sprint does static leveling only (decision #3).
- Additional gestures beyond hello (pushups, etc.) and head-scan behaviors — future motion-catalog
  work on top of this engine.

## Sprint-start record

- **Build version:** ships as **0.1.1** (from `0.1.0`).
- **Tracking-readiness (entry):** READY — todo-mcp tasks empty, context 0 keys, auto-memory
  clean. No archiving/pruning needed.
- **Baseline-health (entry):** GREEN — compile-all sweep (PNut-ts v1.55) compiled **36/36**
  `src/*.spin2` objects clean (0 errors, 0 warnings); no skips, no failure groups. Exit
  baseline at closeout must not worsen (still 36/36 clean + any new objects this sprint adds).
  Caveat: green compile ≠ on-hardware correctness (bench playbook owns behavioral proof).

## Section ↔ task cross-reference

Sprint tag: `smooth-motion-sprint` · build 0.1.1. `seq` is the operational order (`todo_next`
walks it); declared dependencies are documentary.

| Plan § | Deliverable | Task | seq | Depends on |
| ------ | ----------- | ---- | --- | ---------- |
| §1 | Motion engine core (fixed-rate, eased, blendable) | «#3320» | 1 | — |
| §2 | Retrofit poses + hello onto the engine | «#3321» | 2 | #3320 |
| §3 | Full gait catalog port | «#3322» | 3 | #3320 |
| §4 | 3-cog integration + scripted orchestrator | «#3323» | 4 | #3320,#3321,#3322 |
| §5 | IMU level measure + static stance trim | «#3324» | 5 | #3320,#3321 |
| §6 | Documentation (new spec doc + Theory-of-Ops/README + version) | «#3325» | 6 | #3320–#3324 |
| §7 | Bench verification playbook | «#3326» | 7 | #3320–#3325 |

## Open questions

None — research complete; all four scope trade-offs resolved with Stephen (see *Settled scope
decisions*).
