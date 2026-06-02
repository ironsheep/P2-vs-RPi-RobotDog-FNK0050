# P2 Firmware — Theory of Operations

How the Robot Dog (FNK0050) P2 firmware *runs*: the cog partition (comms + two
resource-owner service cogs), the cooperative-task concurrency model, and the comms↔service
mailbox protocol. This is the **dynamic**
companion to the **static** structure in [`../src/README.md`](../src/README.md) (objects,
tiers, files, pins). When the two overlap, this document owns runtime behavior; the README
owns the object/tier map.

> Status: **proposed/agreed design; driver objects drafted.** All Tier 1–4 objects named here
> now exist in `src/` and compile clean (PNut-ts v1.55), but the three-cog wiring (cogspin of
> the backend, the IO cog, and the comms loop, with mailboxes A + B) is not yet assembled, the
> smart-pin ultrasonic + non-blocking buzzer refactors the IO cog needs are pending, and the
> IK/gait/timing math is flagged **⚠ verify** pending hardware. This records the model we build to.

---

## 1. Settled decisions (quick reference)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Gaits are latched modes** — FORWARD/TURN/BALANCE run until STOP or a new command | matches Freenove `condition()`; one message = sustained motion |
| D2 | **Backend is a pure executor** — owns only actuator safety (low-battery relax, joint limits); obstacle avoidance is *frontend* policy that emits STOP | keeps the control loop simple and predictable |
| D3 | **Command mailbox is latest-wins, single slot** — with a "reject if busy" rule for one-shot gestures | teleop semantics; no stale command backlog |
| D4 | **One cog owns the I²C bus** — IMU + servos + battery ADC all share one physical bus | only safe way to multi-master a single bus without a lock |
| D5 | **Backend concurrency is Spin2 v47 cooperative tasks** (coroutines), not separate cogs or interrupts | no preemption → no mid-transaction bus corruption; no lock |
| D6 | **A discrete-pin IO cog owns all non-I²C peripherals** — WS2812 LED (P8), buzzer (P10), ultrasonic (ECHO P9/TRIG P11). The top level *tasks* it via a mailbox and never blocks. | one owner *per pin* (smart-pin handoff across cogs is costly); consolidating the discrete-pin domain offloads the top level. Ultrasonic still behaves as a producer (publishes distance). Head-pan stays with the backend — it's a PCA9685/I²C channel. |
| D7 | **The IO cog runs non-blocking** — smart-pin pulse-measure ranging, timer/smart-pin buzzer, frame-stepped LED — so all three multiplex on one cog with **no jitter**. | P2 headroom + smart-pin timing offload mean ~1 % cog load; HC-SR04's own ~15–20 Hz echo physics caps ranging rate, not the cog. No reason to split ranging onto its own cog. |

---

## 2. Execution model: cogs

The P2 has 8 cogs running truly in parallel, no OS, communicating through shared hub RAM.
We partition the firmware across cogs by **resource ownership** — and *ownership* is the
operative word, because a hardware resource shared across cogs is the central hazard.

> **Two resource domains, each with a single owner cog:**
>
> 1. **The I²C bus** — PCA9685 servos (`0x40`), ADS7830 battery ADC (`0x48`), MPU6050 IMU
>    (`0x68`) all sit on one physical bus (P13/P15). A bus cannot be driven by two cogs
>    without a hardware lock, and `isp_i2c_singleton` holds bus state in shared DAT, so
>    **exactly one cog owns it** (*mandatory* — it is one shared resource).
> 2. **The discrete pins** — WS2812 (P8), buzzer (P10), ultrasonic (ECHO P9/TRIG P11). A *single pin*
>    cannot be cheaply shared across cogs: smart-pin mode is per-pin state and DIR/OUT OR
>    across cogs, so handing a pin between cogs means reconfiguring it. The rule is therefore
>    **one owner cog *per pin*.** Consolidating all discrete-pin devices into one **IO cog**
>    is *elective* (the pins are independent — you could split them), chosen for cog economy,
>    a single non-blocking service loop, and to offload the top level.

### Cog map

| Cog | Role | Owns (hardware) | Talks to others via |
|-----|------|-----------------|---------------------|
| **0** | **Comms / orchestration** | the command link (Wi-Fi/serial) only | writes command mailboxes A + B; reads telemetry + ping |
| **1** | **Backend body-control** | **the I²C bus** (P13/P15): 13 servos, IMU, battery ADC | reads command mailbox A; writes telemetry |
| **2** | **Discrete-pin IO** | WS2812 LED (P8), buzzer (P10), ultrasonic (ECHO P9/TRIG P11) | reads command mailbox B; writes ping/IO telemetry |
| 3–7 | free | — | — |

Two service cogs by resource domain (backend = I²C, IO = discrete pins), each fed by a
mailbox from the comms cog. Cogs 3–7 are spare. With cooperative tasks (§3) we are not forced
to spend a cog per concurrent activity, so we have ample headroom (e.g. a future
behavior/autonomy cog).

---

## 3. Concurrency inside the backend cog: cooperative tasks

The backend cog must do several things "at once" — consume commands, step the current
motion, sample the IMU and battery — **all while being the only cog touching the I²C bus.**
We do this with **Spin2 v47 cooperative multitasking** (verified to compile on PNut-ts
v1.55):

- `taskspin(id, method(), @stack)` launches a Spin2 method as a task (coroutine) with its
  own stack and PC. Up to 32 per cog.
- `tasknext()` yields round-robin to the next task. A task runs until *it* yields.
- `taskstop(id)` / `THISTASK` / `NEWTASK` manage lifetimes.
- The source file must begin with the **`{Spin2_v47}`** directive.

This is **cooperative coroutine multitasking**: there is no preemption. That property is
exactly what makes it safe on a shared bus —

> **A task is never interrupted mid-I²C-transaction.** It yields only at the `tasknext()`
> points it chooses, which we place strictly *between* complete transactions. So the bus
> stays coherent with **no lock**, and the "IMU is a producer, motion consumes a value"
> model is realized *within one cog*: `senseTask` produces, `motionTask` consumes, a hub
> mailbox sits between them.

### Backend tasks

| Task | Does | Yields |
|------|------|--------|
| `dispatchTask` (main) | reads the command mailbox, sets mode / starts gestures, enforces safety floor | after each poll |
| `motionTask` | advances the current gait/gesture **one step** (the IK trajectory) and writes servos | after each step, between transactions |
| `senseTask` | reads IMU → attitude mailbox; periodically reads battery → telemetry | after each read, between transactions |

**Yield discipline (the contract):**
1. Never call `tasknext()` in the middle of an I²C transaction (between START and STOP).
2. Keep each task's run-between-yields short — cooperative preemption latency equals the
   longest such run, and a STOP command must be honored within one yield cycle.

**Caveat — cog-RAM overlap:** the per-task pointer table occupies cog registers
`$100..$11F`, building *downward* from `$11F`. That range **overlaps the inline-PASM
`ORG..END` region** (`$000..$11F`), and `isp_i2c_singleton` uses inline PASM. With our
handful of tasks (table uses only the top few longs) and small inline blocks this is fine,
but it is a real limit to watch if task count or inline-PASM size grows.

### The IO cog uses the same model — but simpler

The discrete-pin IO cog (cog 2) runs the same way: a non-blocking service loop (or Spin2 v47
tasks `ledTask` / `rangeTask` / `buzzerTask`) that, each pass, steps the LED animation if one
is active, kicks/reads ranging when due, and turns the buzzer off at its expiry tick. It is
**simpler than the backend** because each task owns its *own* pin — there is no shared bus, so
no re-entrancy to coordinate and no transaction-boundary yield discipline. The hard
requirement is only that every operation be non-blocking, which the **smart pins make true**:

| IO task | Non-blocking form |
|---------|-------------------|
| ranging | smart-pin pulse-width measurement — fire TRIG, read the hardware-measured echo later; the cog never busy-waits |
| buzzer | drive on + record off-tick (or a smart-pin tone); turn off when due |
| LED | step one frame per pass; the ~210 µs transmit is the only atomic op |

With timing offloaded to smart pins, the cog's compute load is ~1 %, so LED + ranging +
buzzer coexist with no jitter (per D7).

---

## 4. Data flow: producers, consumers, mailboxes

Everything crosses cogs through **single-writer hub mailboxes** — no cog reads another
cog's pins. Four regions, each with exactly one writer. Two are command mailboxes (comms →
each service cog), two are telemetry (each service cog → anyone):

```
' === COMMAND mailbox A  (writer: cog 0 comms → reader: cog 1 backend) ===
aCmdSeq   long      ' comms bumps this LAST, after args -> publishes the command
aCmdId    long      ' MOVE_FORWARD, TURN_LEFT, HEAD, ATTITUDE, PUSHUPS, RELAX, ...
aCmdArg   long[4]   ' speed / height / roll,pitch,yaw / head-angle, as the command needs
aAckSeq   long      ' backend sets = aCmdSeq when consumed (comms sees "accepted")

' === COMMAND mailbox B  (writer: cog 0 comms → reader: cog 2 IO) ===
bCmdSeq   long      ' comms bumps this LAST, after args -> publishes the command
bCmdId    long      ' LED_SOLID / LED_MODE / LED_BRIGHT / BUZZ_BEEP / BUZZ_TONE / RANGE_ENABLE
bCmdArg   long[4]   ' color / mode / level / ms / freq, as the command needs
bAckSeq   long      ' IO cog sets = bCmdSeq when consumed

' === TELEMETRY (writer: cog 1 backend → readers: anyone) ===
attRPY    long[3]   ' roll / pitch / yaw, centi-degrees (from senseTask)
battMv    long      ' pack millivolts (median, divider undone)
modeState long      ' IDLE / GAITING / GESTURE_BUSY / RELAXED / LOW_BATT
busyFlag  long      ' 1 while a one-shot gesture is running

' === IO TELEMETRY (writer: cog 2 IO → readers: anyone) ===
distMm    long      ' latest measured distance (the ultrasonic producer)
pingSeq   long      ' bumps each new reading (readers detect freshness)
ledBusy   long      ' 1 while a one-shot LED pattern is running
```

**Handshake (lock-free, single-writer/single-reader), used identically on both command
mailboxes:** the comms cog writes `*CmdArg[]` and `*CmdId` *first*, then bumps `*CmdSeq`
*last*. The service cog polls `*CmdSeq != *AckSeq`, reads the (now-stable) args, processes,
and sets `*AckSeq := *CmdSeq`. Writing the sequence word last guarantees the reader never
sees torn arguments. This is the cross-cog version of Freenove clearing `self.order=['',...]`
after consuming it.

---

## 5. Command routing

The Freenove `CMD_*` set sorts by *which resource owner* services it — one bucket per
service cog, plus pure queries the comms cog answers from telemetry:

| Bucket | Commands | Routed to | Resource |
|--------|----------|-----------|----------|
| **Motion / posture → mailbox A** | `MOVE_*`, `TURN_*`, `BALANCE`, `HEIGHT`, `HORIZON`, **`HEAD`**, `ATTITUDE`, `RELAX`, `CALIBRATION` + gestures (push-ups, hello) | cog 1 backend | I²C bus |
| **LED / buzzer / sonic → mailbox B** | `LED`, `LED_MOD`, `BUZZER`, `SONIC` (enable/rate) | cog 2 IO | discrete pins |
| **Query (comms-local)** | `POWER`, `WORKING_TIME` | cog 0 answers from telemetry / IO telemetry | — |

`CMD_HEAD` lands in the **backend** bucket because the head-pan servo is PCA9685 ch 15 — on
the backend's bus, not a discrete pin. A "look around and range" behavior is therefore a
**backend ⇄ IO collaboration**: the backend pans the head, the IO cog reports distance, and
the fusion (angle ↔ distance) is comms/behavior policy (per D2). `SONIC` distance and `POWER`
voltage are read by the comms cog from the IO and backend telemetry regions respectively.

---

## 6. Motion model & backend state machine

Two classes of motion, distinguished by lifetime:

- **Latched / cyclic** (FORWARD, BACKWARD, sidestep, TURN, BALANCE): the command sets a
  *mode*. `motionTask` repeats the gait cycle every step until a different command or STOP
  arrives (D1). One message → sustained walking.
- **One-shot** (PUSHUPS, HELLO, RELAX, a HEIGHT/HORIZON/ATTITUDE step, CALIBRATION): runs to
  completion with `busyFlag = 1`, then returns to IDLE / last stance. New gestures are
  rejected while busy (D3).

Backend loop, expressed as cooperative tasks:

```
dispatchTask:
  repeat
    if cmdSeq <> ackSeq                      ' new intent published
      latch cmdId/cmdArg;  ackSeq := cmdSeq
      case cmdId
        MOVE_*/TURN_*/BALANCE : mode := that gait          ' latched (D1)
        HEIGHT/HORIZON/ATTITUDE/HEAD/RELAX : start one-shot move
        gesture (PUSHUPS/HELLO) : if not busyFlag -> start; else ignore (D3)
        MOVE_STOP : mode := IDLE (ease to neutral stance)
    enforce safety floor: if battMv < cutoff -> force RELAX, modeState := LOW_BATT  (D2)
    tasknext()

motionTask:
  repeat
    case mode
      GAIT_*  : compute next per-leg XYZ for this gait step; leg[i].moveToXYZ(...)   ' preemptible each step
      GESTURE : advance gesture trajectory one step; if done -> mode := IDLE, busyFlag := 0
      IDLE    : hold stance
    tasknext()

senseTask:
  repeat
    read IMU -> attRPY mailbox
    every N passes: read battery -> battMv
    tasknext()
```

Because `motionTask` checks the latched `mode` (set by `dispatchTask`) every step, a STOP or
new command preempts a running gait within one yield cycle — responsive, without preemption.

IK ownership: `isp_leg.moveToXYZ(x,y,z)` does the per-leg inverse kinematics
(`coordinateToAngle` + side-mirror + that leg's calibration); `isp_robot_dog` generates the
gait/pose target coordinates and drives all four legs. See [`../src/README.md`](../src/README.md) §3.

### 6.1 Smooth-motion engine (implementation guide)

**Goal:** regular, fluid motion with **no gaps or snaps** between moves. Today's code *snaps*
(`isp_i2c_pca9685_servo.writePosition` writes once; `standPose`/`relaxPose` set final angles in one
shot). The engine below replaces that. **`isp_leg` is the IK/angle provider; `isp_robot_dog` is the
conductor** — coordination (timing, synchronization) lives at the **body** level, because
synchronized, simultaneous multi-leg motion needs one shared timebase.

**The model**
- **One fixed-rate frame loop** (`motionTask`, CT-based ~50 Hz). Every frame it advances the motion
  and writes **all 12 leg joints + head together** — never one leg at a time.
- **Synchronized joint timing (within a leg):** a point-to-point move sets each joint's *target*
  (via IK), then all joints interpolate from current→target over the **same duration** sharing one
  normalized `s: 0→1`. Each joint moves at its own *relative* speed (distance ÷ T) but they **start
  and arrive together**. Apply an **ease-in/out** S-curve on `s` so they accelerate/decelerate.
- **All legs together (across legs):** one shared `s` (poses) or one shared gait phase (gaits)
  drives every leg the same frame → the whole body arrives together.
- **Two interpolation spaces:**
  - *Joint-space lerp* — cheap; fine for poses (stand/relax/sit/transitions). Foot path is slightly
    curved (invisible).
  - *Cartesian foot-path + per-frame IK* — for gaits, where the foot must trace a defined path
    (flat stance, arc swing). The CORDIC makes per-frame IK affordable.
- **Blending:** when a new command arrives, ease from the *current* pose into the next pose/gait —
  no stop-and-restart. This is what removes the gaps.

**What we PORT from the reference (most of it) — `REF/FNK0050-Code/Server/Control.py`:**
- `run()` (≈ line 97): IK for all 4 legs from `point[]`, apply per-leg calibration + the side
  mirror, clamp 0–180, **write all 12 servos**. This is our per-frame "write all legs" — `point[]`
  ⇄ our body-held target/current arrays.
- `stop()` (≈ line 337): `delta = (target − current)/N`, loop N× adding delta and calling `run()` —
  the **synchronized N-step point-to-point lerp** (all legs together). Our pose moves use this shape.
- Gaits `forWard`/`backWard`/`turnLeft`/`turnRight`/`setpLeft`/`setpRight` (≈ line 284+): **Cartesian
  foot trajectories** (`X=12·cos(phase)`, `Y=6·sin(phase)+height`, foot-lift clamp, diagonal pairs
  180° apart), phase stepped by **`self.speed`** (the smoothness/speed knob). The full gait catalog
  is here to port.
- `changeCoordinates()` (≈ line 244): maps a gait's X/Y/Z into the 4-leg `point[]` mirror/diagonal
  pattern. `checkPoint()` (≈ line 122): reachability guard (leg length 25–130 mm) — port as a safety
  clamp.

**What is OURS to invent (the P2 real-time layer):**
- Freenove uses **blocking Python `for` loops** (timing = loop speed; `time.sleep` commented out).
  We run the same math on a **non-blocking, fixed-rate cooperative frame** in `motionTask` so the IO
  and comms cogs stay live and motion timing is deterministic.
- **Mailbox-driven, interruptible/blendable** motion (Freenove finishes a gait loop before the next
  command; ours blends/redirects mid-motion via the latched `mode` + current-pose blend).
- **Ease-in/out** curves (Freenove steps are *linear* / constant-speed) — our refinement.

**Refactor path:** give `isp_robot_dog` body-level `current[]`/`target[]` joint (or foot-XYZ) arrays
and a `speed`/duration; turn `motionTask` into the fixed-rate interpolator that writes all legs each
frame (a `run()`-equivalent); express poses as N-step lerps and gaits as Cartesian phase trajectories
— porting `Control.py`'s math. Build this **before** authoring the full motion catalog, since it
changes how every motion is issued.

---

## 7. Startup / init sequence

1. **Cog 0** boots (Spin top object): start `isp_serial_singleton` (debug), parse config.
2. Cog 0 launches **cog 2** (IO). Cog 2 owns its discrete pins: brings up `isp_led_ring`
   (idle/boot pattern), idles the buzzer, configures the ultrasonic smart pins, and begins
   periodic ranging — publishing `distMm`/`pingSeq`. Then it services mailbox B.
3. Cog 0 launches **cog 1** (backend). Cog 1:
   - `isp_i2c_singleton.setup()` (it now owns the bus),
   - `present()`-checks PCA9685 / ADS7830 / MPU6050; reports any missing device via telemetry,
   - configures the PCA9685 (PWM freq), reads IMU calibration, eases legs to a safe stance,
   - `taskspin`s `motionTask` and `senseTask`, then runs `dispatchTask`.
4. Steady state: cog 0 orchestrates (posts to mailboxes A + B, renders telemetry); cog 1
   runs motion/sense; cog 2 runs LED/buzzer/ranging.

---

## 8. Safety behaviors (backend-owned, per D2)

- **Low battery:** when `battMv` < 6.4 V (`isp_battery_monitor`), the backend forces RELAX
  and sets `modeState = LOW_BATT` regardless of frontend commands. Mirrors Freenove's
  auto-shutdown. The **IO cog** can pulse the ring red by *reading* `modeState` from the
  backend telemetry region — a status display driven entirely by telemetry, no command needed.
- **Joint limits:** `isp_i2c_pca9685_servo` clamps every move to its configured µSec range;
  `isp_leg` clamps IK results to legal angles. Out-of-range targets are clamped, not faulted.
- **Obstacle avoidance is *not* here.** The backend does not auto-stop on a close ping
  reading; it stays a pure executor. Turning "obstacle too close" into a STOP is frontend
  policy (it reads the ping mailbox and emits `MOVE_STOP`).

---

## 9. Open items / to verify on hardware

- **Leg ↔ channel ↔ side mapping** (README §3) is inferred from Freenove gait logic — meter
  before trusting.
- **Servo write budget:** the seed `write9685OffOnWords` does `waitms(1)` per channel → ~13 ms
  for a full-body update. Batch leg channels 2–13 in one PCA9685 auto-increment burst to
  collapse this; sets the control-loop ceiling.
- **IMU rate vs. servo cadence:** decide whether `senseTask` reads the IMU faster than the
  full-body write rate (read-often / write-on-change) or runs the whole loop at one rate.
- **Cooperative yield granularity:** tune gait-step size so STOP latency stays small.
- **`{Spin2_v47}` task table vs inline-PASM** (`$100..$11F` overlap) — watch as task count
  or inline-PASM grows.
- **IO-cog enabling refactors:** `isp_hcsr04` must move from its current polled echo-wait to a
  **smart-pin pulse-width measurement** (non-blocking) and the buzzer to a timer/smart-pin
  tone, so LED + ranging + buzzer multiplex on the one IO cog (per D7). The top-level cog
  launch (`cogspin` of backend + IO + the comms loop) and mailbox B are not yet assembled.
- **WS2812 bit timing** in `isp_ws2812` now matches `REF jm_rgbx_pixel` (fixed 1.25 µs cell,
  400/800 ns high) — only the strip variant remains to confirm on the bench (WS2812 350/700
  vs WS2812B 400/800).

---

*Companion document:* [`../src/README.md`](../src/README.md) — static architecture (objects,
tiers, files, pins). *Hardware authority:* `P2_MIGRATION_WIRING.md`, `RPI_GPIO_USAGE.md`.
