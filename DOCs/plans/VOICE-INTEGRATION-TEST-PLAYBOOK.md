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
- **[ELEC]** — bus-2 electrical is already **resolved** (pull-up `PU_1K5`; supply 3.3 V metered) —
  Exercise 1 is record-only, wiring §3a.

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
| 1 Bus-2 electrical | RESOLVED — record-only (pull-up `PU_1K5`, supply 3.3 V) | — | — | — | no |
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
- **Pass/fail:** `[x]`  45/45 green? **YES — 45/45, 2026-06-10** (re-confirmed after the `cmdName` `@@` fix).

---

## Exercise 1 — Bus-2 electrical: RESOLVED (no action) [ELEC]

> **Both bus-2 electrical items are closed — no bench action required.**
> - **Pull-up:** `VOICE_I2C_PULLUP = PU_1K5`, matching the bench-proven working driver (vendor
>   quick-start + `custom_words_example` both call `i2c.PU_1K5`; `PU_3K3` idled the bus low).
> - **Supply rail:** **3.3 V** (metered 2026-06-10) → SDA/SCL idle ≈ 3.3 V, within the P2's range,
>   **no clamp/level-shift needed.**
>
> Kept here for the record; wiring §3a is the authoritative source. Proceed to Exercise 2.

---

## Exercise 2 — Bus-2 recognition: "do we hear commands, and which CMDIDs?" [NEW]

- **Verifies:** §4 `«#23»` (the primary observability gate) + §5 `«#22»` (green blink). **The headline
  exercise of the sprint.** Depends on Ex 0 green (bus-2 electrical already resolved, Ex 1).
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
- **Bench result 2026-06-10** (`src/logs/debug_260610-114927.log` + earlier runs):
  - **`voice present = T`** — module ACKs on bus 2 at `$64`. **PASS.**
  - **Recognition works** — real built-in IDs arrived: **CMDID 2** (Hello Robot / wake) and **CMDID 22**
    (Go Forward). The IO-cog telemetry (`getVoiceSeq`/`getVoiceCmdId`) + 0→nonzero edge-detect are
    proven. **PASS (numeric IDs).**
  - **Phrase display** — initially `zstr_(names.cmdName(cmdId))` dumped the (zero-free) name-offset
    table as binary, and a `$1B` byte in it tripped `DEBUG_END_SESSION`, ending the capture early
    (looked like a premature timeout). **Root cause:** `cmdName` used the bare `@@nmTbl_0[i]` form,
    which under pnut-ts returned the table-entry address instead of resolving the stored offset.
    **Fixed** → explicit `@@WORD[@nmTbl_0][i]` idiom (`isp_voice_command_names.spin2`).
    **CONFIRMED on hardware** (`src/logs/debug_260610-120132.log`): 10 recognitions, every CMDID→phrase
    pair correct vs `COMMAND-CATALOG.md`, spanning all three tables — CMDID **2** `Hello Robot`
    (`nmTbl_0`), **22/23/24** `Go Forward`/`Retreat`/`Park A Car` (`nmTbl_22`), and
    **36/39/42/48/68** `Face Recognition`/`Line Tracking`/`Object Sorting`/`Load Model`/`Read Compass`
    (`nmTbl_29`). Clean run, no binary, full duration. **PASS.**
  - **Green LED blink** — came **on at the first recognition but stayed solid** (did not self-clear /
    re-blink). **FINDING → carries to the LED-feedback work** (see below); the imperative blink in
    `stepVoice` races the LED animator. Not blocking recognition.
- **Pass/fail:** `[x]`  present=T? **YES** · correct CMDIDs+phrases? **YES — 10/10 correct vs catalog,
  3 tables (log 120132)** · unknown prints nothing? **not yet exercised** · verbal ACK? **___** ·
  green blink? **DEFECT (stuck on) — see LED-feedback note**

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
- **Bench result 2026-06-10** (`src/logs/debug_260610-120703.log`):
  - 3-cog runtime up (IO cog1, backend cog2); gyro cal succeeded after 6 motion-retries (expected
    while hand-supported), `bias x=239 y=-248 z=-23`; **initial STAND reached** — all feet
    `tgt(55,78,±10)=cur`, `mode=3`, `tilt p=-1 r=0` (level); `battery 7704 mV`. **`voice present = T`**
    on bus 2 *with the full bus-1 backend live* — coexistence proven.
  - Three recognitions during the stand, phrases correct (fix holds in the full build): CMDID **2**
    `Hello Robot`, **22** `Go Forward`, **23** `Retreat`. Each traced
    `gate: … moveDone=1 busy=0 halted=0 -> HANDOFF` then `no behavior mapped (CMD_NONE); nothing posted`
    — **no motion on speech**. **PASS.**
  - Minor notes (non-blocking): (a) banner labels cogs `cog1 backend | cog2 IO`, but runtime launched
    **IO=cog1 / backend=cog2** — cosmetic label vs dynamic cog assignment → punch-list nit;
    (b) ranging idle (`dist=-1 mm pingSeq=0`) — out of Ex 3 scope, confirm separately.
- **Pass/fail:** `[x]`  normal stand? **YES** · voice logs while standing? **YES (2/22/23)** · no servo
  glitch / no motion on speech? **YES (CMD_NONE, nothing posted)** · *(visual: green-alive/chirp = eyeball)*

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
- **Bench result 2026-06-10** — two disconnect cases run:
  - **All voice pins disconnected** (`src/logs/debug_260610-121854.log`): **`voice present = F`** —
    correct. Normal 3-cog boot, gyro cal (`bias x=243 y=-248 z=-28`), **STAND reached** (`tilt p=-1 r=0`,
    `battery 7704 mV`), dispatch loop idle, clean session end — **no hang.** **PASS.**
  - **3.3 V supply removed but SDA/SCL + GND still wired** (`src/logs/debug_260610-121417.log`):
    **`voice present = T` — FALSE POSITIVE.** The probe is `i2c.present(DEV_WR)`, an address-ACK only
    (`isp_voice_recognizer.spin2:278`). With the `PU_1K5` pull-ups + GND connected, the unpowered
    DF2301Q is **parasitically powered through its I/O clamp diodes** and still ACKs `$64`. So
    **`present = T` means "something ACKs at `$64`", NOT "the module is powered + functional."**
- **FINDING → probe hardening: IMPLEMENTED.** `start()` now follows the address-ACK with a **liveness
  check** — `probeLive()` writes two distinct values to `REG_WAKE_TIME ($06)` and requires each to read
  back exactly (original restored). A phantom-powered chip ACKs but cannot store+return register data.
  - **Bench-confirmed 2026-06-10 — both directions, finding CLOSED:**
    - 3.3 V lifted / phantom-powered (`src/logs/debug_260610-124713.log`): the state that previously read
      `T` now reads **`voice present = F`** — false positive eliminated.
    - 3.3 V reconnected / powered (`src/logs/debug_260610-124838.log`): **`voice present = T`**, and
      recognition unaffected (CMDID 2/22/23 correct) — the liveness check is not over-strict and the
      `REG_WAKE_TIME` round-trip + restore does not disturb operation. **PASS.**
- **Pass/fail:** `[x]`  present=F (all pins off)? **YES** · normal stand? **YES** · no hang, quiet idle?
  **YES** · *(note: power-only-off gives a false present=T — probe-hardening finding above)*

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
- **Bus-2 electrical** → fully resolved (pull-up `PU_1K5`; supply 3.3 V metered 2026-06-10),
  recorded in wiring §3a. No open electrical items.
- **Ex 5 revert confirmation** → the throwaway mapping must be gone (Ex 0 green) before the sprint closes.
- **Open findings → `DOCs/plans/PUNCH-LIST.md`:**
  - **Voice probe hardening** (Ex 4) — DONE + fully bench-verified both directions: address-ACK +
    `REG_WAKE_TIME` write/read-back liveness check. Phantom (3.3 V-lifted) → `F`, powered → `T` with
    recognition intact. No longer an open finding.
  - **Green-blink stuck-on** (Ex 2) — RESOLVED by the new LED engine (`isp_led_engine`: single owner of
    the ring; cues are single-shot overlays that revert to the base). Bench-verified 2026-06-10 via
    `test_led_engine` (`src/logs/debug_260610-124917.log`): 4 recognition-style green cues each flash and
    revert to OFF — no stuck-on. (Also added a slower, readable chase/wipe pace and a `RAINBOW_BREATHE`
    mode.) The live voice cue now routes through `led.blink()` on the same engine path.
  - **Cog-label banner nit** (Ex 3) — fixed in `robot_dog_top` (now `cog1 IO | cog2 backend`).
- Any failure not fixed in-sprint → new active item in `DOCs/plans/PUNCH-LIST.md`.
