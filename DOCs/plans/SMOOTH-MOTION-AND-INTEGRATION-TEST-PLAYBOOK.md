[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Smooth-Motion + 3-Cog + IMU-Leveling — Bench Verification Playbook

The on-hardware proof for the **smooth-motion / 3-cog integration / IMU-leveling** sprint
(build 0.1.1), **extended into the bench-certification playbook for build 0.1.2** — it now also
covers the post-0.1.1 behaviors (power-on glide, `CMD_CROUCH`, the low-battery **warning** band,
and the `CMD_SHAKE` / `CMD_SALUTE` paw gestures). Every exercise drives the robot **through the
production backend mailboxes** (`dog.postCommand` / `io.postCommand`) via scripted headless driver
tops — never a bespoke servo shortcut path ([[production-path-testing]]). Run it when you are at the
bench; results here are what lets `sprint-closeout` report "verified on the canonical target."

![doc-test](https://img.shields.io/badge/doc-test-informational?labelColor=black)
![platform-Propeller 2](https://img.shields.io/badge/platform-Propeller%202-blue?labelColor=black)
![PCB-v1.0](https://img.shields.io/badge/PCB-v1.0-orange?labelColor=black)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![license-MIT](https://img.shields.io/badge/license-MIT-green?labelColor=black)

> **Build:** **certifies 0.1.2** (`FW_VERSION_*` in `src/isp_version.spin2` still reads `0.1.1`
> until the certification-sprint closeout bumps it — see
> [`HARDWARE-CERTIFICATION-SPRINT-PLAN.md`](HARDWARE-CERTIFICATION-SPRINT-PLAN.md) §5).
> **Target:** the **P2 bench unit** — one P2 Edge on the adapter plate, **battery connected**
> (the board regulates 5 V → 3.3 V from the pack; do not power the P2 from USB alone for servo
> tests), **Load/servo switch ON**, USB serial to the **programming port**.
> **Terminal:** **2 Mbaud (2,000,000)**, 8-N-1 — the project standard for all P2 comms.
> **Est. run time:** ~40–55 min (five driver flashes + two opportunistic battery checks).

> **Exercise order is foundational-first.** The exercises run broadest-dependency → narrowest: the
> **crouch base (Exercise 1) is proven before** the power-on glide and poses that rise *from* it, and
> before leveling (Exercise 3), which measures the body tilt *through* a crouch→stand approach. That
> way a crouch fault is caught at its source instead of silently corrupting a leveling reading or a
> pose downstream. Each later rung adds one behavior on top of the proven base.

> **Relationship to the standing bring-up playbook.** `DOCs/plans/archive/P2_BRINGUP_PLAYBOOK.md` proves each
> driver **standalone** (I²C, IMU, buzzer, LED, ultrasonic, servos, one leg). **Run that green
> first** — this playbook assumes every subsystem already passed there and now exercises them
> **integrated, through the production mailboxes**, against this sprint's behavioral contract
> (`DOCs/spec/P2-RobotDog-Specifications.md`).

---

## Panel pass — 2026-06-07 (functional baseline, pre-I²C-cutover)

This pass was driven through **`src/test_dog_panel.spin2`** (the interactive control panel — same
production `dog.postCommand` / `io.postCommand` mailboxes, real 3-cog shape) rather than the
individual scripted tops, capturing two session logs: `src/logs/debug_260607-165851.log` (poses,
head, LED, IO) and `src/logs/debug_260607-170945.log` (gaits, speed, paw gestures). This playbook is
the **living record**: exercises proven now are checked off inline; exercises blocked by a defect are
listed under **Findings → fix, then retest** (below) and re-run after the fix. The **I²C-cutover
second pass** re-runs every exercise to confirm nothing changed.

| Ex | Status | Note |
|----|--------|------|
| 0 Compile sweep | ✅ | build green; panel + drivers compiled & ran (re-confirm full 41/41 at `sprint-start`) |
| 1 Crouch base | ◑ | `CMD_CROUCH` eased+symmetric ✅, STAND rises ✅; power-on = gentle settle to RELAX (panel path) — explicit crouch→STAND glide still via `test_dog_stand` |
| 2 Eased poses | ✅ | RELAX/STAND/SIT/DOWN/BOW + head pans all eased, smooth (BOW motion fine — see **F1** head clearance) |
| 3 IMU leveling | ⏸ deferred | single-sample STAND tilt −4°/0° (roll good); formal ×3 residual + sign-lock **deferred to keystone** stance re-measure (cert §3) |
| 4 Gaits + speed | ✅ | FWD/BACK/TURN-L/R/STEP-L/R all clean; live speed 5/15/30 mid-gait ✅ |
| 5 Paw gestures | ❌ **F4** | SHAKE/SALUTE execute but **tip over** (no lateral rebalance) |
| 6 Concurrency/blend/ranging | ✅ | blend gait→gait ✅, LED+gait+ranging+beep co-active; ranging stayed live **during a running gait** (visual ✅) |
| 7 Safety floor | n/a | healthy pack — opportunistic, not triggered |
| 8 Warn band | n/a | healthy pack — opportunistic, not triggered |

---

## >> LIFT / SUPPORT THE ROBOT << — read before every motion exercise

Every exercise below **moves servos**. On launch each driver calibrates the gyro (hold the body
**still and level**) and then **glides up to STAND**, after which it walks/poses on its own schedule.

1. **Lift and support the robot** so the legs hang free, or stand it where a stumble can't fall it
   off the bench. Keep hands clear of the joints once it starts.
2. **Load/servo switch ON** — the buzzer **and** the HC-SR04 ultrasonic are on the Load rail; the
   "logic-only" mode powers neither.
3. **HC-SR04 ECHO is 5 V undivided** → reaches **P9 through the ~1 kΩ inline series resistor**
   (P2 pin clamps to VIO, ≤ 10 mA). Confirm that resistor is in line before powering the Load rail
   (`DOCs/P2-platform/P2_MIGRATION_WIRING.md` §4).
4. **Battery, not USB**, powers the servos. A sagging pack will brown-out mid-gait — start each
   run on a healthy pack (and see Exercise 7 for the low-battery behavior).

---

## Headless run recipe (the project convention)

Each driver is a **scripted, self-running top** that emits P2 `DEBUG()` at 2 Mbaud and **exits on
its end-marker**. Build to RAM, then run headless ([[headless-debug-baud]] — the `-b 2000000` is
**required**; without it the 2 Mbaud DEBUG is garbage):

```bash
pnut-ts -d -q src/<driver>.spin2
pnut-term-ts -r src/<driver>.bin -b 2000000 --headless --end-marker "<MARKER>" --timeout <s>
```

| Driver | End-marker | Timeout | Proves (cert Ex) |
|---|---|---|---|
| `src/test_dog_stand.spin2`      | `STAND_DONE`  | 75  | crouch base (glide + `CMD_CROUCH`) + eased poses (Ex 1, 2) |
| `src/test_dog_level.spin2`      | `LEVEL_DONE`  | 80  | IMU leveling residual (Ex 3) |
| `src/test_dog_gaits.spin2`      | `GAITS_DONE`  | 130 | full gait catalog + speed knob (Ex 4) |
| `src/test_dog_tricks.spin2`     | `TRICKS_DONE` | 90  | `CMD_SHAKE` / `CMD_SALUTE` paw gestures (Ex 5) |
| `src/isp_robot_dog_top.spin2`   | `DEMO_DONE`   | 90  | 3-cog concurrency + blend + smart-pin ranging (Ex 6) |

> **New / reordered for the 0.1.2 certification:** the **crouch base is now Exercise 1** (proven
> first — `test_dog_stand` posts `CMD_CROUCH`→`CMD_STAND` as its first moves, before any pose), so
> Exercises 1 and 2 share one `test_dog_stand` flash. Exercise 3 (leveling) is a **residual** check
> (the stance trim is now committed). Exercise 5 adds the paw gestures; Exercise 8 adds the
> low-battery **warning** band.

Logs land in `logs/`. Record each exercise's pass/fail and the captured numbers inline.

> **Production-shape testing (topology, not just the command path).** **Every** driver above
> launches the **real 3-cog shape** — cog0 test facility, cog1 backend/I²C (motors + head + IMU +
> battery + the motion engine), cog2 IO/discrete pins (LED + buzzer + ultrasonic). No test ever
> runs a non-production cog shape. Isolation comes from **what cog0 commands**, not from omitting a
> cog: the motion-only drivers (`test_dog_stand` / `test_dog_level` / `test_dog_gaits` /
> `test_dog_tricks`) keep cog2 **present but quiescent** — a static dim-green "IO cog alive" LED, and
> **ranging dormant** (the unproven smart-pin path never fires because no `IO_RANGE_ON` is sent).
> Only `isp_robot_dog_top` activates mailbox B (LED animation + ranging + beep). So the bring-up
> ladder below adds exactly one new behavior per rung while the topology stays constant — a new
> failure at rung N is attributable to that rung's added behavior, not to a changed cog shape.

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
- **Expected:** every object compiles, `rc=0`, no errors/warnings (**41/41** as of the certification
  sprint — the production-shape scenario tops plus `test_dog_tricks` added the post-0.1.1 coverage).
  Any failure ⇒ fix before flashing anything.
- **Pass/fail:** `[x]`   objects compiled: **41 / 41** — build green; `test_dog_panel` + scenario
  drivers compiled & ran 2026-06-07 (re-confirm the full sweep at `sprint-start`)

---

## Exercise 1 — Crouch base: power-on glide + `CMD_CROUCH` — *prove first*

- **Verifies:** the **foundational crouch base** that everything downstream rises from or measures
  through — proven **first** so a crouch fault is caught at its source, not mistaken for a glide,
  pose, or leveling fault later. Two parts on one flash: (a) the **power-on glide** (cert §1 —
  `seedStand` snaps once to the deep crouch then eases up over `POWERON_FRAMES = 75`, ~1.5 s, instead
  of snapping to attention); (b) the **`CMD_CROUCH`** latched pose eases to the symmetric deep crouch
  (feet under body, X = 0, `CROUCH_HEIGHT_MM = 55`) and `CMD_STAND` rises back out of it. `«#3320»`.
- **Targets:** 1 P2 bench unit (full 3-cog shape), all 12 leg servos, battery, Load ON.
- **Driver:** `src/test_dog_stand.spin2` → `STAND_DONE` (timeout 75). At launch the backend's
  power-on `seedStand` runs (the glide); it then posts `CMD_CROUCH` → `CMD_STAND` as its **first**
  moves — before any pose — so the crouch is exercised in isolation up front.
- **Setup:** Robot lifted/supported so the legs move free, held still & level during the
  "calibrating gyro" countdown. Confirm "IO cog alive in cog N" + a steady dim-green ring (3-cog
  shape up, cog2 present but idle).
- **Action:** Flash & run headless. Watch, in order: (1) the **power-on rise** at the very first
  move after gyro-cal; (2) the posted **`CMD_CROUCH`** descent and the **`CMD_STAND`** rise back
  (console shows `-- post CROUCH ... --` then `-- post STAND ... --`).
- **Expected:**
  - **Power-on glide:** the body **rises smoothly crouch→stand over ~1.5 s** — a gentle glide, **not
    a snap to attention** (lower peak current; the rise is plainly observable).
  - **`CMD_CROUCH`:** eases **down** to a low, **symmetric** crouch (all four feet drawn under the
    body, level, no snap); `CMD_STAND` eases **back up** to neutral. No joint slams a limit (the
    reachability guard holds).
- **Pass/fail:** `[◑]`   Power-on glide (rises, no snap)? **panel soft-starts gently to RELAX, no
  snap** — the explicit crouch→STAND glide is `test_dog_stand`'s path, still to run there.
  `CMD_CROUCH` eased + symmetric? **✅** (Run1 `cmd=13`, `IMU after CROUCH 0/1`, "crouch looks good")
  STAND rises cleanly? **✅**

## Exercise 2 — Engine smoothness: eased poses (no snap)

- **Verifies:** §1 fixed-rate eased engine + §2 poses — RELAX→STAND→SIT→STAND and a head pan, all
  **gapless** (the "beat Freenove's staccato" bar). `«#3320»`, `«#3321»`.
- **Targets:** 1 P2 bench unit (full 3-cog shape), all 13 servos, battery, Load ON.
- **Driver:** `src/test_dog_stand.spin2` → `STAND_DONE` (**the same flash as Exercise 1** — no
  separate build). After the crouch check it posts on mailbox A:
  `CMD_RELAX` → `CMD_STAND` → `CMD_SIT` → `CMD_STAND` → head pan 60/120/90.
- **Setup:** As Exercise 1 (same run, robot lifted/supported).
- **Action:** Continue watching the same run through each named transition; watch the console
  telemetry (`mode=`, `tilt p/r`). Compare the motion qualitatively against a Freenove stock-firmware
  demo clip.
- **Expected:** each transition **eases in and out** (all joints start and arrive together) with **no
  snap** at either end and **no stop-and-hold gap** between the named poses; visibly smoother / less
  staccato than the Freenove clip. Telemetry shows `mode=0` (IDLE) at rest, `mode=3` (RELAXED) after
  `CMD_RELAX`. Head pans smoothly to each angle.
- **Pass/fail:** `[x]`   Poses gapless vs Freenove? **✅ RELAX/STAND/SIT/DOWN/BOW + head pans
  60/90/120 all eased, "looks good" (Run1)**   Any snap seen at a boundary? **none** (BOW *motion*
  is smooth — but see Finding **F1**: BOW drives the head into the table)

## Exercise 3 — IMU static leveling: **residual** check (trim already committed)

- **Verifies:** §5 / cert §3 — the **already-committed** stance trim (`stancePitchDeg = -3`,
  `stanceRollDeg = 2`, metered 2026-06-03) nulls the neutral-stand tilt, i.e. the **residual ≈ 0**,
  and the **sign convention** is correct. `«#3324»`. (This is the one open calibration item; the
  trim is no longer measured-from-zero — that path is kept below only as the fallback.) **Depends on
  Exercise 1:** the measurement rises into the stand *through the crouch-approach*, so the crouch
  must already be proven good (Ex 1) for this reading to be trusted.
- **Targets:** 1 P2 bench unit (full 3-cog shape), all 12 leg servos, IMU, battery, Load ON.
- **Driver:** `src/test_dog_level.spin2` → `LEVEL_DONE` (timeout 80). Launches the full 3-cog shape
  (cog2 IO quiescent), echoes the currently-compiled stance trim, runs the **crouch→stand→measure ×3**
  protocol (rise into the stand each cycle so backlash is taken up one way), and averages
  `getAttitude()`.
- **Setup:** **CRITICAL — the body must measure on its FEET, bearing its own weight, on a
  KNOWN-LEVEL surface.** Support it for gyro cal + the crouch/stand transitions, then **set it down
  level** during the settle window before each measure. A *lifted* measurement reads how your hands
  hold it, not stance level; a tilted surface corrupts the reading. **Use a healthy pack** — a
  sagging pack makes the tilt unrepeatable (see Exercise 8).
- **Action — residual pass (the expected path):**
  1. Confirm `isp_calibration` carries the committed `stancePitchDeg = -3` / `stanceRollDeg = 2`
     (the harness prints **"trim applied → this MEASURE is the RESIDUAL tilt; expect ~0"**).
  2. Flash & run. Record the measured (now **residual**) `pitch avg` / `roll avg`.
- **Expected:** the **residual pitch/roll is near 0** (small band, repeatable across the 3 cycles).
  Leveling is then **certified as-is** and the `isp_calibration.spin2:60` sign-convention comment
  is **locked** (bench-confirmed). If the residual instead **grew** vs. the raw −3/+2 magnitude, the
  sign is inverted → **negate** the stored values, rebuild, re-run, and update the `:60` comment.
- **Fallback — full re-meter (only if residual is *not* ≈ 0 and not a clean sign flip):** temporarily
  set the two trims to **0**, rebuild, re-run (harness prints "trim is 0 → RAW un-leveled tilt"),
  paste the measured average back in, rebuild, and re-run to confirm residual ≈ 0.
- **Pass/fail:** `[⏸ deferred to keystone]`
  - Residual (trim −3/+2 applied): pitch **−4**°  roll **0**°   ≈ 0? **roll yes; ~4° nose-down
    pitch** (single panel sample, Run1 `IMU after STAND`)
  - Sign convention confirmed / comment locked? **deferred**   (negate needed? **tbd**)
  - Re-meter fallback used? **n/a** — the formal ×3 residual + sign-lock is **deferred to the
    keystone stance re-measure** (cert §3 retool: stance pitch/roll is re-zeroed there, so it is
    not certified here)

## Exercise 4 — Full gait catalog + speed knob

- **Verifies:** §3 — every gait runs a stable trot in the correct direction, and the speed arg
  visibly changes cadence without losing smoothness. `«#3322»`.
- **Targets:** 1 P2 bench unit (full 3-cog shape), all 12 leg servos, battery (healthy — gaits draw
  the most current), Load ON.
- **Driver:** `src/test_dog_gaits.spin2` → `GAITS_DONE` (timeout 130). Launches the full 3-cog shape
  (cog2 IO quiescent), then posts each latched gait for ~4 s, `CMD_STOP`-easing to neutral between
  them, then a FORWARD slow (arg0=5) vs fast (arg0=30) speed segment.
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
  Between gaits the `CMD_STOP` **eases** back to neutral (blend, no snap — see Exercise 6).
- **Pass/fail:** `[x]`   FWD ✅ BACK ✅ TURN-L ✅ TURN-R ✅ STEP-L ✅ STEP-R ✅  Speed differs?
  **✅ live 5/15/30 mid-gait** (Run2 `debug_260607-170945.log`, no errors/timeouts)

## Exercise 5 — Paw gestures: `CMD_SHAKE` / `CMD_SALUTE`

- **Verifies:** cert §1 — the one-shot right-front-paw gestures: each eases into a stable **SIT**
  base, acts with the FR paw (handshake bob / held salute) while the other three legs hold the sit,
  lowers the paw, and **ends seated** (a later STAND stands up). Gesture **rejects while busy**;
  no snaps.
- **Targets:** 1 P2 bench unit (full 3-cog shape), all 13 servos, battery, Load ON.
- **Driver:** `src/test_dog_tricks.spin2` → `TRICKS_DONE` (timeout 90). Launches the full 3-cog shape
  (cog2 IO quiescent), then on mailbox A: init STAND → `CMD_SIT` → `CMD_STAND` →
  `CMD_SHAKE` → `CMD_STAND` → `CMD_SALUTE` → `CMD_STAND`. Poses wait on the move-complete edge;
  gestures wait on the busy flag.
- **Setup:** Robot lifted/supported so the FR paw swings free; keep clear of the joints once moving.
- **Action:** Flash & run headless. Watch the FR (right-front) paw through SHAKE then SALUTE and the
  console (`-- post SHAKE ... --`, `isBusy`, per-leg dump at each step).
- **Expected:**
  - **SHAKE:** body **eases into SIT**, the **FR paw lifts and bobs** (handshake), then lowers and
    the body **stays seated**; the other three legs hold the sit throughout. `CMD_STAND` after it
    rises normally.
  - **SALUTE:** body eases into SIT, the **FR paw raises to a held salute** (~held high), then lowers
    and stays seated.
  - **Busy-reject:** the driver's waits show each gesture runs to completion (`isBusy` TRUE→FALSE);
    a second gesture posted while busy would be ignored (D3). No snap at any boundary.
- **Pass/fail:** `[ ] ❌ FAIL → Finding F4`   SHAKE (sit→bob→seated)? **motion executes but tips
  over**   SALUTE (sit→hold→seated)? **motion executes but tips over**
  other 3 legs steady? **no — robot falls toward the lifted FR paw** (paw gestures don't
  lateral-rebalance)   any snap? **n/a (tipped)** — fix per **F4**, then retest

## Exercise 6 — 3-cog concurrency + blend + smart-pin ranging

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
- **Pass/fail:** `[◑ partial]`
  - LED + gait + beep concurrent, no hitch? **co-active on the panel (gait + LED + ranging + beep
    lit together), no hitch observed**
  - Ranging live integrated — `pingSeq` advances / `fresh=1` during the gait? **✅ confirmed
    (visual)** — RANGE toggled ON **during a running FORWARD gait** (Run2: `ranging on` immediately
    after `cmd=2 FORWARD`); ranging stayed working through the gait, no issues. (`pingSeq`/`dist` are
    panel-readout-only, not logged — confirmed by observation.)
  - Blend (FWD→TURN no restart; STOP eases)? **✅ gaits posted back-to-back ran without
    restart/crash (Run2)** — see also design item **D1** (transition smoothing)

## Exercise 7 — Safety floor: low battery eases to RELAX — *opportunistic*

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
- **Action:** Run any motion driver (e.g. `test_dog_stand`) and watch the telemetry `battery=` and
  `mode=` once the reading sits below 6400 mV for several samples.
- **Expected:** After 3 consecutive low reads the body **eases to the relax/tuck pose** (smooth,
  not a snap) and telemetry shows `mode=4` (LOWBATT); it stays latched there.
- **Pass/fail:** `[n/a]`   batt at trip ____ mV   eased (not snapped)? ____   mode→4? ____   —
  **not triggered: healthy pack** (opportunistic; run when a pack drains in-band)

## Exercise 8 — Low-battery **warning** band (6.4–6.8 V) — *opportunistic*

- **Verifies:** cert §1 — the throttled low-battery **warning log** (distinct from the Exercise 7
  cutoff): at/below `BATTERY_WARN_MV = 6800` the backend logs a warning every `BATTERY_WARN_SECS = 5`
  s **without** forcing rest, so results are flagged unreliable *before* the pack sags into the
  6.4 V floor. Added because a depleted pack corrupted the leveling measurement (Exercise 3).
- **Targets:** 1 P2 bench unit on a pack sitting in the **6.4–6.8 V** band.
- **Trigger detail:** `senseTask` emits `!! BATTERY LOW <mV> mV (cutoff 6400 mV) -- charge soon;
  results unreliable` when `battMilliVolts < 6800` and the 5 s throttle window has elapsed; it does
  **not** touch `lowBattReadings`/the safety floor (that is strictly `< 6400 mV`, Exercise 7).
- **⚠ Caution:** opportunistic — run when a pack has naturally drained into 6.4–6.8 V (any motion
  driver will do), or on a bench supply set in-band. Do **not** deep-discharge a good pack to test.
- **Setup:** Pack/supply in the 6.4–6.8 V band; robot supported.
- **Action:** Run any motion driver and watch the console once `battery=` sits in-band.
- **Expected:** the `!! BATTERY LOW <mV> mV ...` line logs **~every 5 s** (throttled, not every
  sample), and the robot **keeps operating** — `mode=` stays out of `4` (`MODE_LOWBATT`) as long as
  the reading stays ≥ 6400 mV. Crossing below 6400 mV escalates to the Exercise 7 floor.
- **Pass/fail:** `[n/a]`   warning logs ~5 s apart? ____   batt in-band ____ mV   stayed out of
  floor (mode≠4)? ____   — **not triggered: healthy pack** (opportunistic; run when a pack drains in-band)

---

## Findings — 2026-06-07 panel pass → fix, then retest

Gathered as **one symptom set** (per the closeout rule below) for a single `defect-fixing` pass.
Each is **retested by re-running its exercise** after the fix; the fixed behavior then joins the
baseline the **I²C-cutover second pass** re-confirms.

| ID | Symptom (bench) | Root cause (code) | Blocks | Retest after fix |
|----|-----------------|-------------------|--------|------------------|
| **F1** | BOW dips the nose into the table | `CMD_BOW` lowers the front but never raises the head servo | Ex 2 (BOW) | BOW: head lifts / clears the surface through the bow |
| **F2** | Can't tell which LED mode is active or how many exist | panel has no LED-mode readout (button only lit/unlit) | Ex 6 (IO usability) | panel shows the active LED-mode name + index |
| **F3** | LED SOLID / WIPE / CHASE show nothing (look like OFF) | `currentColor` inits to `strip.BLACK` and is only set by `IO_LED_SOLID`; the panel posts only `IO_LED_MODE`, so color modes paint black (`isp_led_ring.spin2:68,111,114,124`) | Ex 6 (LED) | all 6 modes visibly distinct from a fresh boot |
| **F4** | SHAKE / SALUTE tip the robot toward the lifted FR paw | paw gestures rebalance by **SIT only** — no lateral lean; HELLO leans via `leanStandFoot`, they don't (`advancePawGesture` `:870`) | **Ex 5** | SHAKE + SALUTE free the FR paw without tipping; re-check HELLO `LEAN_*_MM` magnitude |

**D1 (design — future step, NOT a cert blocker).** Gait-transition smoothing: switch gaits at a
**phase-0 / all-feet-planted** boundary instead of easing to neutral (the current `gaitLeadin`
settle). Speed changes are **already** snap-free (cadence-only — `gaitStepDeg` is the phase
increment, no amplitude change). Belongs to a **post-keystone** Dog-Like Motion step (it touches the
per-leg neutral keystone changes).

**Still to cover (not findings):** Ex 1 explicit crouch→STAND power-on glide via `test_dog_stand`,
and the opportunistic battery Ex 7/8 when a pack is in-band. (Ranging-during-gait ✅ confirmed;
**PARADE-REST** ✅ exercised via the panel key `r` — both 2026-06-07.)

---

## Results → closeout

Record `[x]`/`[ ]` and the captured numbers inline. A failed exercise is a **finding**: the
default is to **fix it before the sprint closes** (it goes back into sprint work); a carried-over
failure is added to `DOCs/plans/PUNCH-LIST.md` as a new active item. **When a run surfaces more
than one wrong behavior, gather the whole symptom set first**, then hand it to `defect-fixing` as
one inventory — multiple manual-test failures often share one root cause. `sprint-closeout` reads
these results to report verification state honestly.

**Coverage note (no silent caps).** Ordered **foundational-first**: the crouch base (Ex 1) is proven
before the glide/poses that rise from it and before leveling (Ex 3), which measures *through* the
crouch-approach — so a crouch fault is caught at its source, not mistaken for a leveling/pose fault.
The only automated gate is the Exercise 0 compile sweep; behavioral correctness is proven **only** by
the bench exercises above. The non-blocking smart-pin ranging path is **first proven** in Exercise 6
— until that passes it remains unproven on hardware. **Exercises 7 and 8 are opportunistic**
(pack-state dependent — the low-battery floor and warning band have no repeatable trigger short of an
in-band pack/supply); run them whenever a pack is naturally in range. **Flash economy:** Exercises 1
(crouch base) and 2 (eased poses) share a single `test_dog_stand` flash.

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
