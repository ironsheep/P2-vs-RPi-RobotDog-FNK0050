# VOICE-INTEGRATION — Bench Verification Playbook

**Build:** 0.3.0 · **Targets:** 1 P2 bench unit (DF2301Q voice on the 2nd I²C bus, P18 SCL / P16 SDA)
— plus the host (no robot) for Exercise 0, and a **multimeter** for Exercise 1. **Est. run time:**
~45–60 min.

This is the on-hardware proof for the **voice-recognizer wiring-in** sprint (VOICE-INTEGRATION,
plan §7 `«#26»`). The sprint is **plumbing + observability only** — it proves *we hear commands over
I²C and which CMDIDs arrive*, and that the new bus/cog/dispatch plumbing coexists with everything
already shipped. **Voice CMDID → behavior mapping is the NEXT sprint**; the `voiceToDogCmd()` seam
returns `CMD_NONE` for every word, so in normal builds **no spoken word moves the dog**. Exercise 5
*temporarily* wires a throwaway mapping to exercise the dispatch+gating path end-to-end, then reverts.

Each exercise is tagged so you know what it's for:

- **[NEW]** — verify new voice behavior shipped this sprint (recognition, telemetry, dispatch/gating).
- **[CERT]** — certify a previously-trusted subsystem still works now that cog 2 owns a 2nd bus and
  cog 0 is a dispatch loop (bus-1 motion/IMU/battery, ranging, LED).
- **[ELEC]** — confirm the bus-2 electrical setup (module supply rail; pull-up already settled at
  `PU_1K5` from the working-driver precedent, wiring §3a).

> Record pass/fail on each exercise — `sprint-closeout` reads these. A failed exercise is a finding:
> fix it before closeout, or (exception) carry it to `DOCs/plans/PUNCH-LIST.md`. If a run surfaces
> several wrong behaviors, **record them all first**, then hand the set to `defect-fixing` as one
> symptom inventory — they often share a root cause.

---

## What's new this build — what to look (and listen) for

- **A 2nd I²C bus now exists** on P18/P16, owned by the **IO cog** (cog 2), carrying the DF2301Q.
  Bus 1 (servos/IMU/battery on P13/P15, cog 1) is untouched — the two buses must not interfere.
- **The IO cog publishes recognized CMDIDs** as latest-wins telemetry (`getVoiceCmdId()` /
  `getVoiceSeq()`), exactly like it publishes ranging (`distMm` / `pingSeq`).
- **cog 0 (`robot_dog_top`) is now a persistent dispatch loop**, not a scripted demo. It watches the
  voice telemetry and *would* hand commands to the backend — but the map seam yields `CMD_NONE`, so
  it only **traces** its dispatch+gating decisions this sprint.
- **Feedback you can sense:** the DF2301Q **speaks its own verbal acknowledgement** (vendor firmware,
  free), and the firmware adds a **single green LED-ring blink** on each recognition. (The full
  spinning-green / red-refused / off-idle scheme is documented as the mapping sprint's target.)

---

## Driver map & run pattern

| Exercise | Driver | Build | End-marker | Timeout | Robot? |
|----------|--------|-------|------------|---------|--------|
| 0 Automated gate | compile sweep (`BUILD_COMMAND`) | — | — | — | no (host) |
| 1 Bus-2 electrical pre-flight | (multimeter; `test_voice` loaded) | `test_voice` | — | — | no (dog unpowered) |
| 2 Bus-2 recognition | `test_voice.spin2` | `test_voice` | *(none — runs to timeout)* | 120 | no (dog unpowered/safe) |
| 3 Bus coexistence | `robot_dog_top.spin2` (clean) | `robot_dog_top` | *(none — dispatch loop)* | 90 | yes |
| 4 Absent-module degradation | `robot_dog_top.spin2` (clean) | `robot_dog_top` | *(none — dispatch loop)* | 60 | yes |
| 5 Dispatch + gating (throwaway map) | `robot_dog_top.spin2` (**temp mapping**) | `robot_dog_top` | *(none — dispatch loop)* | 120 | yes |

Flash/run pattern (all P2 comms at **2 Mbaud**). The voice harness and the dispatch loop are
**persistent** — they run until the harness `--timeout`, with **no end-marker**:

```bash
pnut-ts -d -q src/<driver>.spin2
pnut-term-ts -r src/<driver>.bin -b 2000000 --headless --timeout <N>
```

---

## Exercise 0 — Automated compile-sweep GATE (run before any hardware step) [CERT]

- **Verifies:** §7 `«#26»` — every `.spin2` object still compiles after the sprint diff (swapped
  voice OBJ §1, the IO-cog voice telemetry + green blink §2/§5, the reshaped `robot_dog_top` dispatch
  loop §3, and the new `test_voice.spin2` §4). This is the cheap gate: if it's red, **fix the code
  before spending bench time.**
- **Targets:** host only, no robot.
- **Action:**
  ```bash
  cd "$(git rev-parse --show-toplevel)"
  rc=0; for f in src/*.spin2; do pnut-ts -q "$f" || rc=1; done; rm -f src/*.bin; echo "rc=$rc"
  ```
- **Expected:** **45/45 GREEN** (the 44-object baseline + the new `test_voice.spin2`). The four
  untouched IO-cog test tops (`test_dog_gaits/level/tricks/stand/panel`) and `custom_words_example`
  still compile.
- **PASS TELL:** `rc=0`, every file reports `Wrote …` with no error.
- **Pass/fail:** `[ ]`  45/45 green? ______

---

## Exercise 1 — Bus-2 electrical pre-flight: supply rail (pull-up already settled) [ELEC] [NEW]

- **Verifies:** wiring §3a — the bus-2 electrical setup is safe before trusting recognition. **The
  pull-up is already resolved:** `VOICE_I2C_PULLUP = PU_1K5`, matching the **bench-proven working
  driver** on this hardware (vendor quick-start + `custom_words_example` both call `i2c.PU_1K5`). So
  this exercise just confirms the **module supply rail** and the logic-level that follows.
- **Targets:** 1 bench unit, **dog unpowered** (Load OFF — voice needs only the module + P2), multimeter.
- **Setup:** P2 powered, DF2301Q wired on P18 (SCL) / P16 (SDA) and powered from its supply rail.
  Flash `test_voice` (Exercise 2's build) so the P2 configures the bus-2 pins (`PU_1K5`), then leave it
  idling at the `LISTENING` banner.
- **Action / OBSERVE (multimeter, DC):**
  1. **Supply rail** — measure the DF2301Q VCC pin: **3.3 V or 5 V?** Record it. If **5 V**, its
     SDA/SCL idle high will exceed 3.3 V → the P2 needs a clamp/level-shift on those lines (wiring §4
     voice row) before relying on the bus; prefer running the module at **3.3 V**.
  2. **Sanity (optional)** — with the bus idle, SDA (P16) / SCL (P18) should idle **high** (≈ rail);
     the P2's `PU_1K5` holds them up. If they sit low, check wiring/GND before Exercise 2.
- **PASS TELL:** supply rail recorded = ____ V; if 5 V, clamp/level-shift fitted; SDA/SCL idle high.
- **Feeds closeout:** confirm/record the supply-rail value in wiring §3a (the last open bus-2 item).
- **Pass/fail:** `[ ]`  rail ____ V · clamp fitted if 5 V? ______ · SDA/SCL idle high? ______

---

## Exercise 2 — Bus-2 recognition: "do we hear commands, and which CMDIDs?" [NEW]

- **Verifies:** §4 `«#23»` (the primary observability gate) + §5 `«#22»` (green blink). **The headline
  exercise of the sprint.** Depends on Ex 0 green and a confirmed supply rail (Ex 1).
- **Targets:** 1 bench unit, **dog unpowered / unsupported is fine** — only the IO cog runs; no
  servos, no IMU, no backend. Safe to run on the desk.
- **Driver:** `test_voice.spin2` (timeout 120, no end-marker — speak during the window).
- **Setup:** module wired + powered (Ex 1). Flash `test_voice`; watch the banner.
- **OBSERVE (console):**
  - Banner prints: driver version, `voice bus = SCL P18 / SDA P16 (DF2301Q @ I2C $64)`, and
    **`voice present = T`**, then `LISTENING`.
  - Speak the DF2301Q **wake word** (e.g. "Hello Robot"), then a handful of **built-in command words**
    from `DOCs/subsystems/VoiceSensor/COMMAND-CATALOG.md` — e.g. **"Go Forward" (CMDID 22)**,
    **"Retreat" (23)**, **"Turn Left 90 Degrees" (25)**. Each should print
    `heard #N: CMDID <id>  '<phrase>'` with the **correct catalog ID + phrase**.
  - Say something **not** in the vocabulary → **nothing prints** (CMDID 0 is never published).
- **PASS TELL (all four):**
  1. banner shows **`voice present = T`**;
  2. each spoken built-in word prints its **correct CMDID + phrase**;
  3. an unrecognized utterance prints **nothing**;
  4. you **hear the module's own verbal ACK** and see **one green LED-ring blink** per recognition.
- **If FAIL:** `voice present = F` → re-check Ex 1 wiring/pull-up/rail; wrong/absent IDs → confirm the
  module's command-word card matches the catalog; no blink → check the WS2812 (LED is on the IO cog).
- **Pass/fail:** `[ ]`  present=T? ___ · correct CMDIDs+phrases? ___ · unknown prints nothing? ___ ·
  verbal ACK + green blink? ___

---

## Exercise 3 — Bus coexistence: full robot, both buses live [CERT] [NEW]

- **Verifies:** §7 `«#26»` — with the **full `robot_dog_top` build**, bus 1 (servos/IMU/battery) is
  **unaffected** by bus-2 voice traffic; two independent buses, two owner cogs. Depends on Ex 2.
- **Targets:** 1 bench unit, full 3-cog shape, all 13 servos, IMU, battery, **Load ON**, voice module
  wired.
- **Driver:** `robot_dog_top.spin2` (clean, `DEMO_ON_BOOT = FALSE` — the default dispatch loop;
  timeout 90).
- **Setup:** **support the robot** during gyro-cal + first rise; then set down level.
- **OBSERVE:**
  - **[CERT]** Boot proceeds normally: IO cog up (green "alive" + hello chirp), backend inits,
    **gyro-cals, and STANDS** in the loaded-rear crouch — exactly as build 0.2.0. Banner reports
    **`voice present = T`**.
  - **[CERT]** Telemetry sane while voice is being spoken at the module: battery mV reads, the dog
    holds its stand (no servo glitching), and if you exercise ranging/LED via the panel build they
    still work. (Bus-1 traffic doesn't stall.)
  - **[NEW]** Speaking built-in words still logs `voice: CMDID <id> '<phrase>'` from the dispatch loop
    **while the dog stands** — recognitions register concurrently with a live bus-1 backend.
  - **[NEW]** Each recognition traces a **gate line** (`gate: dogCmd=0 mode=… → …`) and
    **`no behavior mapped (CMD_NONE); nothing posted`** — confirming the dog **does not move** on voice
    this sprint.
- **PASS TELL:** the dog **inits/cal/stands normally AND voice recognitions log concurrently**, with
  no servo disturbance and **no motion triggered** by speech.
- **Pass/fail:** `[ ]`  normal stand? ___ · voice logs while standing? ___ · no servo glitch / no
  motion on speech? ___

---

## Exercise 4 — Absent-module degradation: quiet orchestrator, no hang [NEW]

- **Verifies:** §7 `«#26»` — with the voice module **unplugged**, `robot_dog_top` runs as a quiet
  orchestrator: no hang on the missing bus, all other subsystems normal. Reuses Ex 3's clean build.
- **Targets:** 1 bench unit, full 3-cog shape, **voice module unplugged** (or power its bus off).
- **Driver:** `robot_dog_top.spin2` (same clean build as Ex 3; timeout 60).
- **Setup:** physically **disconnect the DF2301Q** from P18/P16; support the robot for cal + rise.
- **OBSERVE:**
  - Boot reaches **`voice present = F`** (the start() probe NAKs; the bounded clock-stretch guard means
    **no stuck bus**).
  - The dog still **inits, gyro-cals, and stands** normally; the dispatch loop runs **silently** (no
    voice lines — `getVoiceSeq()` never advances) and **never hangs**.
- **PASS TELL:** `voice present = F`, normal stand, dispatch loop idles cleanly for the whole window —
  **no freeze, no servo fault.**
- **Pass/fail:** `[ ]`  present=F? ___ · normal stand? ___ · no hang, quiet idle? ___

---

## Exercise 5 — Dispatch + motion-gating, end-to-end (TEMPORARY throwaway mapping) [NEW]

> ⚠ This is the **only** exercise where a spoken word moves the dog, and it uses a **throwaway test
> mapping that MUST be reverted before closeout.** Real word→behavior mapping is the next sprint.

- **Verifies:** §3 `«#24»` — the dispatch loop + motion-gating skeleton work end-to-end: a one-shot
  blocks the next handoff until `getMoveComplete()`, a latched gait is interruptible, and `isHalted()`
  suppresses handoff. Depends on Ex 3.
- **Targets:** 1 bench unit, full 3-cog shape, all servos, IMU, battery, Load ON, voice wired.
  **Keep the dog supported** — it will move on command.
- **Setup — apply the throwaway mapping** in `src/robot_dog_top.spin2`, replacing the body of
  `voiceToDogCmd()`. Mark it unmistakably temporary:
  ```spin2
  PRI voiceToDogCmd(voiceCmdId) : dogCmd
  ' >>> THROWAWAY BENCH MAPPING -- §7 Ex 5 ONLY -- REVERT TO `dogCmd := dog.CMD_NONE` BEFORE CLOSEOUT <<<
      dogCmd := dog.CMD_NONE
      case voiceCmdId
          23: dogCmd := dog.CMD_NOD        ' "Retreat"            -> one-shot (gating: blocks next handoff)
          22: dogCmd := dog.CMD_FORWARD    ' "Go Forward"         -> latched gait (interruptible)
          24: dogCmd := dog.CMD_STOP       ' "Park A Car"         -> stop / supersede
  ```
  Recompile (`pnut-ts -d -q src/robot_dog_top.spin2`) and flash (timeout 120).
- **Action / OBSERVE:**
  1. **One-shot blocks next handoff** — say **"Retreat"** (→ `CMD_NOD`). The dog nods; **immediately**
     say "Retreat" again. The 2nd command's gate line shows **`busy`/`moveDone=0` → withhold** (held)
     until the nod completes (`getMoveComplete()` TRUE), then it hands off. *One-shots don't stomp each
     other mid-move.*
  2. **Latched gait is interruptible** — say **"Go Forward"** (→ `CMD_FORWARD`, latched). The dog walks.
     Say **"Park A Car"** (→ `CMD_STOP`) → the gate **allows the supersede** and the gait eases to a
     stop. *A new command interrupts a latched gait.*
  3. **(If feasible) halt suppresses** — on a low/critical battery, `isHalted()` latches: gate lines
     show **`halted=1 → withhold`** and **nothing posts**. (Skip if you can't safely reach the floor.)
- **PASS TELL:** the three gating behaviors are observable in the **gate trace + the dog's motion**:
  one-shot holds, gait interrupts, (halt suppresses).
- **MANDATORY REVERT:** restore `voiceToDogCmd()` to `dogCmd := dog.CMD_NONE` (drop the `case`),
  recompile, and confirm Ex 0 is green again. **Log the revert** so closeout sees the throwaway gone.
- **Pass/fail:** `[ ]`  one-shot holds? ___ · gait interruptible? ___ · halt suppresses (or n/a)? ___ ·
  **throwaway mapping REVERTED + recompiled?** ___

---

## Closeout inputs

- **Per-exercise pass/fail** above → `sprint-closeout` verification state.
- **Ex 1 supply-rail result** → record the 3.3-vs-5 V finding in wiring §3a (the last open bus-2
  electrical item; the pull-up is already settled at `PU_1K5`).
- **Ex 5 revert confirmation** → the throwaway mapping must be gone (Ex 0 green) before the sprint closes.
- Any failure not fixed in-sprint → new active item in `DOCs/plans/PUNCH-LIST.md`.
