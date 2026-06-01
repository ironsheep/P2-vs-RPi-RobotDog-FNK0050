# P2 Bring-Up Playbook

A bench checklist for proving each Robot Dog (FNK0050) subsystem **one at a time** on the
P2, driven by the `src/isp_dog_bringup.spin2` menu console. Run top to bottom — the order is
dependency-first (bus before the chips that ride it, sensors before actuators).

- **Firmware build:** `src/isp_dog_bringup.spin2`, version **0.1.0** (`FW_VERSION_*` in
  `src/isp_version.spin2`).
- **Target:** the **P2 bench unit** — one P2 Edge on the adapter plate, **battery connected**
  (the board regulates 5 V → 3.3 V from the pack; do not power the P2 from USB alone for the
  servo tests), USB serial to the **programming port**.
- **Terminal:** **2 Mbaud (2,000,000)**, 8-N-1 — the project standard for all P2 comms. Each
  exercise names its **menu digit** in its heading — type it to run that test.
- **Est. run time:** ~20-30 min.

> **Conventions.** Authored to the `test-playbook` skill and this project's
> `.claude/skills/test-playbook/project-overlay.md`. This is the project's **standing**
> bring-up playbook (cross-referenced from `../src/README.md` and
> `P2_FIRMWARE_THEORY_OF_OPS.md`), so it keeps this descriptive name rather than the per-sprint
> `<NAME>-TEST-PLAYBOOK.md` pattern under `DOCs/plans/`. With no sprint plan yet, each exercise's
> **Verifies** cites the driver object and the README's ⚠-verify items in place of a plan
> section / `«#N»` task.

> **SAFETY — read before exercises 8-10.** Those move servos. **Lift and support the robot**
> so the legs hang free first. P2 over-voltage: the HC-SR04 **ECHO** (5 V, exercise 7) reaches
> **P9 through a ~1 kΩ inline series resistor** (the P2 pin clamps it to VIO, ≤ 10 mA); the
> WS2812 data is 3.3 V into a 5 V part (usually fine). See `P2_MIGRATION_WIRING.md` §4.

> **⚠ verify items.** Some constants were inferred, not metered. **Resolved 2026-06-01:** the
> battery divider is **÷3, not ÷2** (ex. 3 — metered 7.68 V → reads 7.76 V). The **leg↔channel
> map is verified** (ex. 8–10, 2026-06-01). **Still inferred:** the WS2812 **strip variant** (ex. 6
> — bit timing matches `jm_rgbx_pixel`; only WS2812 350/700 vs WS2812B 400/800 ns remains), and the
> joint **side-mirror + CORDIC IK** (ex. 10, validate through motion). Where an exercise proves one
> of these, it is marked **⚠**; record the measured reality in the notes.

---

## Bring-up results — 2026-06-01 (non-motion interfaces)

First pass done **not** via the menu console below but with per-interface **auto-run** top files
(`src/test_*.spin2`) that emit P2 `DEBUG()` at 2 Mbaud and exit on `TEST_DONE` — driven headless:
`pnut-ts -d -q src/test_X.spin2` then `pnut-term-ts -r src/test_X.bin -b 2000000 --headless
--end-marker "TEST_DONE"`. **The `-b 2000000` is required** (headless does not auto-apply the debug
baud to the runtime read; without it the 2 Mbaud DEBUG is garbage). Logs land in `logs/`.

| Ex. | Interface | Result | Finding |
|---|---|---|---|
| 1 | Serial / DEBUG console | ✅ | DEBUG @ 2 Mbaud clean once `-b 2000000` passed. |
| 2 | I²C bus scan | ✅ | 0x40, 0x48, 0x68 (+0x70 PCA9685 all-call). 3.3 V rail + `PU_1K5` confirmed. |
| 3 | Battery | ✅ FIXED | Divider is **÷3** (was ÷2); 7.68 V metered → 7.76 V read. |
| 4 | IMU | ✅ | Accel `az≈+1 g`, gyro `<0.25 deg/s` at rest after **hardened** `calibrateGyro` (motion-reject). |
| 5 | Buzzer | ✅ | Audible **only with the Load/servo rail ON** (buzzer is on the Load rail). |
| 6 | LED ring | ✅ | R/G/B (GRB) + rainbow, 7 px. |
| 7 | Ultrasonic | ✅ | Tracks motion; **~1 kΩ series R into P9 fitted** (5 V echo via pin clamp). Load on. |
| 8–10 | Servos / legs / head | ✅ | **PCA9685 wake bug fixed** (MODE1 SLEEP never cleared → no PWM); all 13 servos center & hold. **Leg map verified**: FL=4/3/2, BL=7/6/5, BR=8/9/10, FR=11/12/13, head=15. FL/BR toes need a small tibia trim (calibration). |

---

## 0. Setup (once)

- **Action:** Build and flash `src/isp_dog_bringup.spin2` (`pnut-ts -q src/isp_dog_bringup.spin2`,
  then load to RAM/FLASH). Open the serial terminal at 2 Mbaud (2,000,000).
- **Expected:** The banner `=== Robot Dog (P2) bring-up console ===` and the numbered menu
  appear, ending with `> `.
- **Pass/fail:** `[ ]`

---

## 1. Serial console  — *implicit*

- **Verifies:** `isp_serial_singleton` on the programming port; clock config (`_clkfreq`).
- **Targets:** 1 P2, no peripherals.
- **Setup:** Exercise 0 complete.
- **Action:** Observe the menu; press any unmapped key (e.g. `0`).
- **Expected:** Menu renders cleanly (no garbage = correct baud/clock); unmapped key prints
  `? unknown choice` and the menu redraws.
- **Pass/fail:** `[ ]`

## 2. I²C bus scan  — menu `1`

- **Verifies:** I²C master (`isp_i2c_singleton`), the **3.3 V rail restored onto header pins
  1/17**, and the **P2-supplied pull-ups (`PU_1K5`)** — the board has none (#1 migration gotcha).
  Detects PCA9685 / ADS7830 / MPU6050. (Requires the bus set up with `PU_1K5`, not `PU_NONE`.)
- **Targets:** 1 P2 + connection board powered from the battery.
- **Setup:** Battery connected; nothing lifted needed.
- **Action:** Press `1`.
- **Expected:** `found 0x40`, `found 0x48`, `found 0x68` and `3 device(s)`. Missing any one
  ⇒ stop and check the 3.3 V rail / SDA-SCL wiring before going further (every later I²C test
  depends on this).
- **Pass/fail:** `[ ]`   Found: ______________________

## 3. Battery  — menu `2`  ⚠

- **Verifies:** `isp_battery_monitor` → `isp_i2c_ads7830`; ADC read, median, ÷2 divider, cutoff.
- **Targets:** 1 P2 + battery.
- **Setup:** Note the pack voltage from a multimeter for comparison.
- **Action:** Press `2`.
- **Expected:** `battery: NNNN mV (N.N V)` within ~±0.3 V of the metered pack voltage.
  Low-pack warns below 6.4 V.
- **⚠ verify:** if the reading is off by a constant factor, the VREF (5000 mV) or divider
  (×2) constant in `isp_i2c_ads7830` / `isp_battery_monitor` is wrong — record metered vs read.
- **Pass/fail:** `[ ]`   Metered ____ V / Read ____ V

## 4. IMU  — menu `3` (live)

- **Verifies:** `isp_imu` → `isp_i2c_mpu6050`; wake, ranges, accel/gyro burst read, gyro
  calibration, accel tilt (CORDIC).
- **Targets:** 1 P2 + battery; robot sitting still on the bench.
- **Setup:** Hold the robot **level and still** while it prints "calibrating".
- **Action:** Press `3`. Watch the stream. Tilt the body by hand. Press any key to stop.
- **Expected:** At rest, `az` ≈ +1000 mg (gravity), `ax`/`ay` near 0, gyro near 0 mdps after
  calibration. Tilting forward/back changes `tilt p`; rolling changes `tilt r`, sign
  consistent with the tilt direction.
- **Pass/fail:** `[ ]`   Rest az ____ mg / tilt tracks? ____

## 5. Buzzer  — menu `4`

- **Verifies:** `isp_buzzer` on P10.
- **Targets:** 1 P2.
- **Setup:** none.
- **Action:** Press `4`.
- **Expected:** Three audible ~150 ms beeps.
- **Pass/fail:** `[ ]`

## 6. LED ring  — menu `5` (live)  ⚠

- **Verifies:** `isp_led_ring` → `isp_ws2812` on P8; GRB framing, brightness, modes,
  WS2812 bit timing.
- **Targets:** 1 P2 + 7-pixel strip.
- **Setup:** none (a level shifter on the data line is recommended).
- **Action:** Press `5`. Observe solid **red**, then **green**, then **blue**, then a moving
  rainbow. Press any key to stop (ring goes off).
- **Expected:** Correct colors in the right order (proves GRB byte order) on all 7 pixels;
  smooth rainbow (proves timing). Wrong colors per pixel ⇒ wire-order constant; flicker/wrong
  hues ⇒ **⚠** WS2812 timing constants vs `datasheet/WS2812.pdf`.
- **Pass/fail:** `[ ]`   Color order OK? ____ Rainbow stable? ____

## 7. Ultrasonic  — menu `6` (live)

- **Verifies:** `isp_hcsr04` on TRIG P11 / ECHO P9; trigger pulse + echo timing + mm conversion.
- **Targets:** 1 P2 + HC-SR04. ECHO is **5 V, undivided** (metered 2026-05-31) → **~1 kΩ series
  resistor into P9** (P2 pin clamps to VIO, ≤ 10 mA); no divider.
- **Setup:** ⚠️ The ultrasonic is on the **Load/servo rail** — turn the **Load switch ON** to
  power it (the logic-only "legs-off" mode won't), so **support the robot** for this test.
  Confirm the ~1 kΩ series R is in line to P9 before connecting.
- **Action:** Press `6`. Move a hand/target to known distances (e.g. 100 mm, 300 mm). Press a
  key to stop.
- **Expected:** Distance tracks the target within ~±10 mm; `-- no echo --` when pointed at
  open space beyond range.
- **Pass/fail:** `[ ]`   @100mm reads ____ / @300mm reads ____

## 8. Servo controller + head center  — menu `7`  *(MOVES)*

- **Verifies:** `isp_i2c_pca9685` start/configure (PWM freq) and a single servo write via
  `isp_head` (ch 15).
- **Targets:** 1 P2 + battery + PCA9685 + head servo.
- **Setup:** **LIFT/SUPPORT THE ROBOT.** Battery connected (servos need pack current).
- **Action:** Press `7`.
- **Expected:** PCA9685 config debug prints; the head servo moves to/holds center (~90°),
  no buzzing/stall.
- **Pass/fail:** `[ ]`

## 9. Head pan sweep  — menu `8`  *(MOVES)*

- **Verifies:** `isp_head` `sweep` across its travel limits and re-center.
- **Targets:** as exercise 8.
- **Setup:** Controller already up (or this test brings it up); robot supported.
- **Action:** Press `8`.
- **Expected:** Head pans smoothly min→max, then back to center; stays within ~50-130° (no
  mechanical binding at the ends).
- **Pass/fail:** `[ ]`

## 10. One leg (front-left)  — menu `9`  *(MOVES)*  ⚠

- **Verifies:** `isp_leg` channel map + side mirror (`setJointAngles`) and the **CORDIC inverse
  kinematics** (`moveToXYZ`), plus the leg↔channel↔side assignment.
- **Targets:** 1 P2 + battery + PCA9685 + the front-left leg's 3 servos.
- **Setup:** **ROBOT LIFTED/SUPPORTED**, front-left leg free to move.
- **Action:** Press `9`. Watch: direct mid pose → IK neutral `(0,99,10)` → reach `(20,90,10)`
  → back to neutral.
- **Expected:** The **front-left** leg (and only it) moves; the three joints move in sane
  directions; the IK poses look like a leg reaching/lifting, not slamming to a limit.
- **⚠ verify:** if a *different* leg moves, the channel/side map is wrong (README §3). If
  joints move backwards or jam at 0/180°, the IK scaling/quadrant or the femur/tibia mirror is
  wrong — record which joints and directions.
- **Pass/fail:** `[ ]`   Correct leg? ____ Sane motion? ____

---

## Integration milestones (beyond the standalone console)

Exercises 1-10 prove each driver **standalone** in the bring-up console's own cog. The
production firmware runs them under two resource-owner service cogs plus a comms cog (see
`P2_FIRMWARE_THEORY_OF_OPS.md`), so integration is **staged** — prove all of 1-10 green first.

### Stage I — discrete-pin IO cog (`isp_io_controller`)

- **Verifies:** one cog owns LED + buzzer + ultrasonic, served non-blocking via mailbox B.
  Exercises **5 (buzzer)**, **6 (LED)**, **7 (ultrasonic)** are its per-driver prerequisites.
  Note ex. 7 tests the *blocking* ranging path; the IO cog uses the **non-blocking smart-pin**
  path (`startSmart`/`firePing`/`echoReadyMm`, `P_HIGH_TICKS`), first proven *here*.
- **Setup:** a small top harness that `cogspin`s `isp_io_controller` and posts to mailbox B
  via `postCommand` (**TODO** — analogous to the bring-up console). Robot supported as usual.
- **Action / Expected:** post `IO_RANGE_ON` **+** an animated `IO_LED_MODE` **+** an
  `IO_BUZZ_BEEP` together. The rainbow animates **smoothly while** `getDistanceMm()` updates
  stream and a beep fires — **no hitching** in any of the three. The ~210 µs LED frame must not
  disturb ranging; a beep must not freeze the animation. (Per D7: smart-pin timing → ~1 % cog
  load → no jitter.)
- **Pass/fail:** `[ ]`  concurrent LED + range + beep clean? ____

### Stage II — backend body-control cog (`isp_robot_dog`)

Motion + IMU/battery sensing under cooperative tasks on the **I²C-owning** cog, driven via
mailbox A. Do **not** run gaits until single-leg motion (ex. 10) is validated.

### Stage III — full robot

Both service cogs + the comms cog wired together (`cogspin` of backend + IO + the comms loop);
teleop via mailboxes A/B; gaits, poses, gestures. The top-level cog launch is the remaining
build step. See `P2_FIRMWARE_THEORY_OF_OPS.md`.

---

*Record results inline (`[x]` pass, note failures). A failed exercise is a finding: fix the
driver and re-run, or log it as outstanding work. Companion docs: `../src/README.md`
(object/pin inventory), `P2_MIGRATION_WIRING.md` (authoritative wiring), `HARDWARE_SETUP.md`.*
