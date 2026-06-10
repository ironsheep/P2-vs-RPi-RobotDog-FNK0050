# `src/` — P2 Firmware Architecture

P2 (Parallax Propeller 2) firmware that replaces the Raspberry Pi controller in the
**Freenove Robot Dog Kit (FNK0050)**. The P2 must drive the same connection-board
hardware the Pi's Python stack drove. Language is **Spin2 / PASM2**, compiled with
**PNut-ts**.

> **Authoritative hardware facts live in `../DOCs/`**, not here. This README is the
> *static* software map — objects, tiers, files, pins. For how the firmware *runs* at
> runtime (cogs, cooperative tasks, the frontend↔backend mailbox protocol), see the
> companion **`../DOCs/P2_FIRMWARE_THEORY_OF_OPS.md`**. For pin/rail facts and their
> confidence levels, see `../DOCs/P2-platform/P2_MIGRATION_WIRING.md` (the swap) and
> `../DOCs/RPI_GPIO_USAGE.md` (the stock Pi usage). Where this README repeats a pin, it is
> for orientation — the wiring doc wins.
>
> **This build targets connection board PCB v1.0** (WS2812 LED data on the discrete data
> line, not the v2.0 SPI path).

---

## 1. Layered object model

Drivers and behaviors stack in **four tiers**. Tiers 1–3 are the per-device driver shape
already established by the seed `isp_i2c_pca9685*` objects;
Tier 4 is the behavioral/coordination layer that composes devices into a robot.

| Tier | Role | Speaks in… | Examples |
|------|------|-----------|----------|
| **1 — transport** | Raw hardware access; one bus / one signal. Knows no device. | bytes, ACK/NAK, pin transitions | `isp_i2c_singleton`, `isp_ws2812.streamBuffer()` |
| **2 — chip** | Register-level access to one device. | register addresses, raw counts | `isp_i2c_pca9685`, `isp_i2c_ads7830` |
| **3 — semantics** | The *user's* mental model of one part. | degrees, volts, named colors | `isp_i2c_pca9685_servo`, `isp_battery_monitor`, `isp_leg`, `isp_head`, `isp_led_ring` |
| **4 — coordination** | Composes many parts into whole-robot behavior. | gaits, poses, commands | `isp_dog_motion` |

Three structural notes:

- **The tier boundary is about *vocabulary*, not `PUB`/`PRI`.** Plenty of Tier-2 register
  pokes are `PUB` on purpose (handy for bring-up/probing). What makes a method "Tier-3" is
  that it talks degrees/volts/colors, never register counts.
- **Tiers can split across files *or* live in one file.** I²C devices get a Tier-1 bus
  singleton shared by all chips, so their tiers are separate objects. The WS2812 has no
  shared bus, so its transport+framing live inside one object — like the serial singleton
  keeps its bit-level smart-pin code and its `dec`/`hex`/`fstr` API in one file.
- **Tiers are a static call hierarchy; cogs are a separate runtime partition.** Which cog
  runs which tier — and why all the I²C-bound objects must run in *one* cog — is the
  Theory of Operations' job, not this map's.

---

## 2. Object inventory & dependency tree

```
robot_dog_top        (T4 top: cog0 orchestrator; cogspins the two service cogs)
  ├─ isp_dog_motion       (cog1: I²C bus owner, mailbox A) ───────────────────────┐
  └─ isp_io_controller   (cog2: discrete-pin owner, mailbox B) ──────────┐       │
                                                                         │       │
isp_dog_motion            (T4: 4 legs + head + IMU + battery; smooth-motion engine, gait catalog, poses, gestures, leveling)
  ├─ isp_leg  ×4         (T3: one leg; moveToXYZ via shared IK, side-mirror, per-leg calibration)
  │   └─ isp_i2c_pca9685_servo  ×3   (T3 servo, seed)
  ├─ isp_head            (T3: pan/center/sweep, PCA9685 ch 15)
  │   └─ isp_i2c_pca9685_servo
  ├─ isp_imu             (T3: attitude — accel g / gyro °/s)        ─┐
  │   └─ isp_i2c_mpu6050 (T2: MPU6050 registers)                    │
  ├─ isp_battery_monitor (T3: pack volts, low-batt cutoff, median)  │
  │   └─ isp_i2c_ads7830 (T2: ADS7830 counts / pin millivolts)      ├─ isp_i2c_pca9685 (T2)
  └─ isp_calibration     (per-joint servo trims + stance leveling)  │     │
                                                                    │     └─ isp_i2c_singleton (T1: I²C master)
isp_io_controller        (T4 IO cog: non-blocking LED + buzzer + ranging service loop)
  ├─ isp_led_ring        (T3: display modes; owns LED count)
  │   └─ isp_ws2812      (T1+T2: WS2812 transport + pixel buffer)
  ├─ isp_buzzer          (T2+T3: buzzer, smart pin — no I²C)
  └─ isp_hcsr04          (T2+T3: ultrasonic, smart pin — no I²C)

(every object) ── DEBUG() built-in (debug output over the 2 Mbaud programming UART)
```

All objects below **compile clean** with PNut-ts v1.55 (`pnut-ts -q`). Items marked
**⚠ verify** contain math/timing inferred from the Freenove code or datasheets that must be
validated on hardware (outputs are clamped, so they are safe to run during bring-up).

| File | Tier | Device / role | Notes |
|------|------|---------------|-------|
| `isp_i2c_singleton.spin2` | 1 | I²C bus master | **seed**; shared by all I²C chips. `setup/present/write/read/wr_block/rd_block/stop`. ACK=0, NAK=1 |
| `isp_i2c_pca9685.spin2` | 2 | PCA9685 @ `0x40` | **seed**; 16-ch PWM register driver |
| `isp_i2c_pca9685_servo.spin2` | 3 | servo | **seed**; degrees/µSec, limits, slew ramp tables |
| `isp_i2c_ads7830.spin2` | 2 | ADS7830 @ `0x48` | `readChannelRaw` / `readChannelMillivolts` (divider-agnostic). VREF 5.0 V (consistent with the metered ÷3 battery) |
| `isp_battery_monitor.spin2` | 3 | battery | 9-sample median, **÷3 divider** undo (METERED 2026-06-01), `isLowBattery` (<6.4 V) |
| `isp_ws2812.spin2` | 1·2 | WS2812 strip (7 px) | inline-PASM, CT-paced fixed-cell + GRB buffer (dumb strip). Timing per jm_rgbx_pixel; confirm WS2812 vs B variant |
| `isp_led_ring.spin2` | 3 | LED display modes | off/solid/wipe/chase/rainbow/rainbow-cycle; `update()` steps one frame |
| `isp_io_controller.spin2` | 4 | discrete-pin IO cog | non-blocking service loop: LED anim + smart-pin ranging + auto-off buzzer; mailbox B (`postCommand`, `getDistanceMm`/`getPingSeq`/`isLedBusy`) |
| `isp_i2c_mpu6050.spin2` | 2 | MPU6050 @ `0x68` | wake + ±2g/±250°/s; burst-read accel/gyro raw |
| `isp_imu.spin2` | 3 | attitude | accel milli-g, gyro milli-°/s, `calibrateGyro` (settle + paced + motion-reject → SUCCESS/E_NOT_STILL), `tiltDegrees` (CORDIC). Mahony fusion = TODO |
| `isp_hcsr04.spin2` | 2·3 | HC-SR04 ultrasonic | polled `readDistanceMm`/`Cm` **and** non-blocking smart-pin path (`startSmart`/`firePing`/`echoReadyMm`) ⚠ verify integrated |
| `isp_buzzer.spin2` | 2·3 | buzzer | active buzzer `on`/`off`/`beep` (IO cog drives non-blocking via auto-off tick) |
| `isp_leg.spin2` | 3 | one leg (3 servos) | `init(side, ending)`, `setJointAngles`, `moveToXYZ` (CORDIC IK ⚠ verify) |
| `isp_head.spin2` | 3 | head pan (ch 15) | `panTo`/`center`/`sweep` |
| `isp_calibration.spin2` | 3 | per-robot trims | per-joint servo trims (metered) + head trim + **static stance leveling** (`stanceTrimY`) |
| `isp_dog_motion.spin2` | 4 | body coordinator | `{Spin2_v47}` cooperative tasks; mailbox A; smooth-motion engine (50 Hz eased), full gait catalog + speed knob, stand/relax/sit, hello, leveling ⚠ verify |
| `isp_io_controller.spin2` | 4 | discrete-pin IO cog | mailbox B; non-blocking LED + ranging + buzzer (see row above) |
| `robot_dog_top.spin2` | 4 | integrated 3-cog top | `cogspin`s backend + IO cogs; scripted demo orchestrator over mailboxes A + B ⚠ verify |

There is **no shared OBEX driver** for the ADS7830, MPU6050, or HC-SR04 — each is
hand-rolled on the seed I²C singleton (or a smart pin). The **full gait catalog**
(forward/backward, turn L/R, sidestep L/R) and the hello gesture in `isp_dog_motion` are
implemented on the smooth-motion engine (build 0.1.1); on-bench behavioral verification is
pending (the trajectory math is still ⚠ verify).

---

## 3. The leg model (Tier 3 → Tier 4)

The 12 leg-joint PCA9685 channels group into **4 legs of 3 joints** (coxa *a* / femur *b* /
tibia *c*; link lengths l1=23, l2=55, l3=55 mm). A leg is created with its body position —
**`init(side, end)`** — and derives its own channel triple, joint-angle mirror, and gait
role from that identity.

| Leg | Side | End | coxa (a) | femur (b) | tibia (c) |
|-----|------|-----|----------|-----------|-----------|
| FL | Left | Front | ch 4 | ch 3 | ch 2 |
| BL | Left | Back | ch 7 | ch 6 | ch 5 |
| BR | Right | Back | ch 8 | ch 9 | ch 10 |
| FR | Right | Front | ch 11 | ch 12 | ch 13 |

- **Side** owns the joint-angle **mirror**: Left legs apply `[a, 90−b, c]`; Right legs apply
  `[a, 90+b, 180−c]`. (Left channels count *down*; Right count *up* — the physical mirror.)
- **End** owns the **gait phase** and stance-offset sign. Diagonal phase pairs are {FL,BR}
  and {FR,BL}.
- **IK lives in `isp_leg`** (`moveToXYZ` = shared `coordinateToAngle` + side-mirror + this
  leg's calibration → 3 servo writes). The **body coordinator** (`isp_dog_motion`) generates
  per-leg target coordinates for gaits/poses and calls each leg.
- **Motion timing lives at the body level (the smooth-motion engine).** `isp_dog_motion` owns a
  CT-gated 50 Hz frame loop with body-level foot-target arrays (`cur/tgt/start[]`, leg order
  FL/BL/FR/BR), an ease-in/out smoothstep, per-frame reachability guard, and blend-from-current —
  so all 13 joints share one timebase and start/arrive together (no per-servo slew, no snaps). It
  drives the **full gait catalog** (forward/backward, turn L/R, sidestep L/R; trotting diagonals
  with an `arg0` speed knob). All poses and gaits share one neutral — the **loaded-rear crouch** —
  through a single source of truth, `neutralFootTarget(idx)` / `neutralFootY(idx)`: front feet at
  `NEUTRAL_FRONT_Y_MM=95`, rear folded deeper to `NEUTRAL_REAR_Y_MM=85` and tucked back
  (`NEUTRAL_REAR_X_MM=−12`) for a ~60:40 forward bias. Gaits clamp each foot's lift to its **own**
  per-leg planted floor (`plantFloor`), so the front/rear height split survives walking;
  `STAND_HEIGHT_MM=99` is retained only as the *tall* SIT/BOW/PARADE reference. The neutral folds in
  the **IMU static-leveling** stance trim (`isp_calibration.stanceTrimY`). The behavioral contract is
  specified in
  [`../DOCs/spec/P2-RobotDog-Specifications.md`](../DOCs/spec/P2-RobotDog-Specifications.md); the
  as-built engine is ToOps §6.2.
- **The three cogs are assembled in `robot_dog_top`** — it `cogspin`s the backend (I²C, mailbox
  A) and `isp_io_controller` (discrete pins, mailbox B), and runs a scripted orchestrator on cog 0.

> ✅ The FL/BL/BR/FR ↔ channel assignment is **verified on hardware 2026-06-01** — each commanded
> leg moved the matching physical leg (FL=4/3/2, BL=7/6/5, BR=8/9/10, FR=11/12/13, head=15). The
> joint-angle **side mirror** and the **CORDIC IK** still need validation through motion (the
> calibration step). Note: at center the FL/BR toes sit slightly low → small tibia trim pending.

Head is a single DOF (PCA9685 **ch 15**, center ≈ 90°, ~50–130°). `isp_head` is intentionally
thin — it earns its keep as the mount point for the future head-pan + ultrasonic scan.
Whole-robot gestures (push-ups, the "hello" wave — which actually waves a *leg*) belong to
`isp_dog_motion`, not the head.

---

## 4. P2 pin map (as-built P8–P15)

**As-built adapter map, verified on hardware 2026-05-31** (base P8; offsets LED +0, ECHO +1,
Buzzer +2, TRIG +3, SCL +5, SDA +7). **Authoritative table + rationale:
`../DOCs/P2-platform/P2_MIGRATION_WIRING.md` §3.**

| P2 pin | Robo hdr pin | Signal | Driver object | Transport |
|--------|--------------|--------|---------------|-----------|
| P8 | 12 | WS2812 LED data | `isp_ws2812` | inline PASM2 |
| P9 | 15 | Ultrasonic ECHO (input) | `isp_hcsr04` | smart pin (pulse in); **~1 kΩ inline series R** |
| P10 | 11 | Buzzer | `isp_buzzer` | smart pin |
| P11 | 13 | Ultrasonic TRIG | `isp_hcsr04` | smart pin (pulse out) |
| P12 | — | *spare* | — | — |
| P13 | 5 | I²C SCL | `isp_i2c_singleton` | I²C (`PU_1K5`) |
| P14 | — | *spare* | — | — |
| P15 | 3 | I²C SDA | `isp_i2c_singleton` | I²C (`PU_1K5`; 6.9 kΩ board pull-down) |

### Devices behind the I²C bus (P13/P15)

| Device | Addr (7-bit) | Driver | Role |
|--------|--------------|--------|------|
| PCA9685 | `0x40` | `isp_i2c_pca9685(_servo)` | 13 servos: ch 2–13 = four legs (3 joints each), ch 15 = head pan; 0–180° → count 102–512 |
| ADS7830 | `0x48` | `isp_i2c_ads7830` → `isp_battery_monitor` | battery ADC ch 0; cutoff < 6.4 V |
| MPU6050 | `0x68` | `isp_i2c_mpu6050` → `isp_imu` | 6-axis IMU for balance/attitude |

> All three I²C devices share **one** physical bus → exactly one cog may drive it. See the
> Theory of Operations for the bus-ownership rule.
>
> Drivers store the address **pre-shifted** (e.g. ADS7830 = `$90` = `0x48 << 1`) and OR in
> `MODE_WRITE` (0) / `MODE_READ` (1), matching the PCA9685 convention.

---

## 5. Runtime overview (→ Theory of Operations)

The static tiers above are partitioned across P2 cogs at runtime, by **resource ownership** —
comms plus two service cogs, one per hardware domain. In brief:

- **Cog 0 — comms / orchestration:** owns the command link only; posts intents to both
  service cogs and reads their telemetry. Never blocks on a peripheral.
- **Cog 1 — backend body-control:** the **sole owner of the I²C bus** (servos + IMU +
  battery); runs motion and IMU/battery sensing as **Spin2 v47 cooperative tasks** — so the
  shared bus is never touched by two cogs, with no lock.
- **Cog 2 — discrete-pin IO:** owns the **non-I²C pins** — WS2812 LED (P8), buzzer (P10),
  ultrasonic (ECHO P9 / TRIG P11). One owner per pin (cross-cog pin handoff is costly); runs LED animation,
  ranging, and beeps as non-blocking tasks (smart-pin timing → ~1 % cog load, no jitter), and
  is the ultrasonic distance producer.

Each service cog is fed by its own hub mailbox (commands in, telemetry out). The full cog map,
the concurrency model, the mailbox protocol, and the backend state machine are documented in
**`../DOCs/P2_FIRMWARE_THEORY_OF_OPS.md`**.

---

## 6. Electrical gotchas (recap — see wiring doc for the authoritative treatment)

- **The P2 is 3.3 V and NOT 5 V tolerant** (pin abs-max ≈ 3.6 V). Every signal *into* a P2
  pin must be ≤ 3.3 V — watch the 5 V-native parts: **HC-SR04 ECHO** (needs a divider) and
  **WS2812** data (3.3 V out into a 5 V strip — a level shifter is the robust fix).
- **The 3.3 V rail vanishes with the Pi.** The adapter must put 3.3 V back on header
  pins 1/17 for the board's I²C pull-ups/chips. (#1 gotcha.)
- **Power flows robot → controller**: feed the P2 board 5 V (header pins 2/4); it regulates
  3.3 V on-board.
- **Keep I/O on P0–P57.** P58–P61 = boot flash, P62/P63 = serial/programming.

Constants once flagged `INFERRED` are being retired as hardware confirms them: the battery
divider is now **METERED ÷3** (2026-06-01), not the ÷2 traced from Freenove code; WS2812 bit
timing matches `REF jm_rgbx_pixel` (only the strip variant needs confirming); the **leg↔channel
map is verified** (2026-06-01). Still to validate through motion: the joint side-mirror, the CORDIC
IK, and per-joint servo trim (the calibration step).

---

## 7. Building

Compiled with **PNut-ts** (`pnut-ts`, v1.55.0+ in this container).

```bash
# Compile one object as the top file (pulls in its child objects automatically):
pnut-ts -q src/isp_ws2812.spin2          # → isp_ws2812.bin

# Useful flags:
pnut-ts -l src/isp_i2c_ads7830.spin2     # also emit .lst listing
pnut-ts -d src/<top>.spin2               # compile with DEBUG
```

Each driver is written so it compiles standalone (it is a valid top object even though its
`null()` notes "not a top-level object"). Objects using cooperative tasks must begin with
the **`{Spin2_v47}`** version directive.

### Proving drivers on hardware — `test_*.spin2` harnesses

Each interface has a dedicated **auto-run** top file (`test_led`, `test_i2c_scan`, `test_buzzer`,
`test_ping`, `test_battery`, `test_imu`, `test_servo_center`, `test_servo_wiggle`, plus `test_smoke`)
that brings up **one** driver, runs it
for a bounded time, and emits P2 `DEBUG()` (no serial singleton, no menu, no keystrokes). Each
declares `DEBUG_BAUD = 2_000_000`, is compiled with `-d`, and ends with `DEBUG("TEST_DONE")`:

```bash
pnut-ts -d -q src/test_i2c_scan.spin2                                       # build with DEBUG
pnut-term-ts -r src/test_i2c_scan.bin -b 2000000 --headless \
             --end-marker "TEST_DONE" --timeout 12                          # download-to-RAM, run, capture
```

> **`-b 2000000` is required.** In `--headless` mode `pnut-term-ts` opens the port at 115200 for the
> *download* (fine, ignore it) but does **not** auto-apply the debug baud to the *runtime* read — so
> 2 Mbaud `DEBUG` comes back as garbage unless you pass `-b 2000000`. Logs land in `logs/`.

These were used for the 2026-06-01 bring-up (results: `../DOCs/P2-platform/P2_MIGRATION_WIRING.md` §7). The smooth-motion bench tests
**all run the production 3-cog shape** (both service cogs launched, isolation by what cog 0
commands — never a single-cog shape): **`test_dog_stand.spin2`** (eased poses), **`test_dog_level.spin2`**
(IMU static-leveling measure), and **`test_dog_gaits.spin2`** (full gait catalog + speed) each keep
the IO cog present-but-quiescent (static LED, ranging dormant), while **`robot_dog_top.spin2`**
is the full concurrency runtime (LED animation + live ranging + motion + beep, scripted orchestrator
on cog 0). They drive `DOCs/plans/SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md`. The real frontend
comms cog (Wi-Fi/serial command link) is still **TODO**.

`.bin` / `.lst` / `.obj` outputs are build artifacts — don't commit them.

---

## 8. Conventions

- **Coding standards (authoritative):** every `.spin2` file MUST follow
  [`../DOCs/policy/SPIN2-AUTHORING-GUIDE.md`](../DOCs/policy/SPIN2-AUTHORING-GUIDE.md) —
  ASCII-only, VSCode/PNUT_TS doc-comment style (`@param`/`@returns`/`@local`), single exit
  point, `quit` (never `return`) from loops, named constants (no magic numbers), descriptive
  names (no single-letter/generic locals), and object constants referenced via the OBJ
  prefix. The guide's checklist is the pre-commit gate.
- **Naming:** `isp_<...>.spin2`, Iron Sheep Productions prefix. If the device is reached over
  **I²C**, put `i2c` in the name (`isp_i2c_ads7830`); smart-pin / single-signal / behavioral
  objects omit it (`isp_ws2812`, `isp_hcsr04`, `isp_leg`, `isp_dog_motion`).
- **Debug:** objects emit diagnostics via the built-in `DEBUG()` (compiled out unless the
  debugger is attached); output lands on the 2 Mbaud programming UART.
- **License:** MIT, © Iron Sheep Productions, LLC (see each file's footer). Upstream
  Freenove `REF/` material is CC BY-NC-SA 3.0 and is **excluded** from this repo.
- **P2 KB / OBEX:** for PASM2/Spin2 questions and reusable objects, use the **p2kb-mcp**
  tools (authoritative) rather than web search.
