# VOICE-INTEGRATION — Sprint Plan

**Status:** planned (research complete; ready for `sprint-start`)
**Project build at plan time:** 0.2.0 (`src/isp_version.spin2`; bump is a `sprint-start` decision)
**This is the LAST planned sprint.** See [[project-status]] sequence and the design note
[[voice-integration-design]].

---

## §0 — Scope, boundaries, and why a 2nd I²C bus

**Goal of THIS sprint:** stand up the **plumbing** that lets the robot *hear* — a 2nd I²C bus
carrying the DFRobot **DF2301Q** offline voice recognizer, polled by the firmware — and **prove
that recognized commands are observable** (which command-word IDs arrive over I²C). It also builds
the **top-level dispatch-loop architecture** that future command-mapping will plug into. It does
**not** wire any spoken command to any dog behavior.

**Explicit boundary — what we DO NOT do this sprint (deferred to a separate "voice command
mapping" sprint):**
- No voice-CMDID → dog-`CMD_*` mapping table.
- No assignment of trained custom-word slots (`CMD_CUSTOM_1..17`) to behaviors.
- No behavior actually driven by voice. The dispatch loop is built and exercised, but its
  map step returns "no behavior" for every recognized ID this sprint.

This split is Stephen's explicit call: *first* prove "do we hear commands at all, and which ones
do we see"; *then*, as a separate planned sprint, decide which phrases occupy which slots and wire
them to motion.

**What is PREBUILT and NOT ours to build or validate** (arrived 2026-06-10, all tracked):
- `src/isp_voice_recognizer.spin2` — the DF2301Q driver (hardware-tested). Public surface used
  here: `start(scl, sda, khz, pullup) : bFound`, non-blocking `pollCMDID() : cmdId` (0 = none),
  `getCMDID()` alias. The `CMD_*` constant catalog it reports (`isp_voice_recognizer.spin2:22-188`)
  is the **DF2301Q's** vocabulary — a *different* numbering space from the dog's `CMD_*` mailbox
  catalog (that translation is the deferred sprint).
- `src/isp_i2c.spin2` — VAR/instance I²C bus master that **honors clock-stretch** (`STRETCH_LIMIT`,
  `isp_i2c.spin2:43`), required by the DF2301Q. API matches the singleton
  (`setup/present/start/stop/write/read`, `NAK`, `PU_*`).
- `src/isp_voice_command_names.spin2` — optional ID→phrase lookup (`cmdName(cmdId) : pStr`,
  `:113`) + a custom-word table. Used here only for human-readable bench output.
- `DOCs/subsystems/VoiceSensor/` — device docs (USER-GUIDE, COMMAND-CATALOG, CHANGELOG).

**What WE build/integrate this sprint:** the bus-2 wiring into the IO cog, the recognized-CMDID
telemetry, the top-level dispatch loop + motion-gating skeleton, an observability test harness, a
minimal recognition LED indication, and the documentation deltas.

**Why a 2nd I²C bus (one paragraph, since it's the structural reason for the sprint):** bus 1
(`isp_i2c_singleton`, P13 SCL / P15 SDA, owned by the backend cog) carries the PCA9685, ADS7830 and
MPU6050 — none of which clock-stretch, and the project's singleton had clock-stretch *removed*. The
DF2301Q **holds SCL low while it prepares data**, so it cannot share that singleton. It gets its own
bus (P18 SCL / P16 SDA) driven by the clock-stretch-honoring `isp_i2c` VAR instance, **owned by the
IO cog** (cog 2). Clean ownership: cog 1 owns bus 1 (DAT singleton), cog 2 owns bus 2 (VAR instance),
no cross-cog bus sharing. (The separate idea of re-unifying the two masters by adding clock-stretch
*back* to the singleton is an already-deferred punch-list experiment — out of scope here; see
`DOCs/plans/PUNCH-LIST.md`.)

---

## §1 — Bus-2 bring-up: point the voice driver at the instance master

**Why:** the prebuilt driver hardwires `OBJ i2c : "isp_i2c_singleton"`
(`isp_voice_recognizer.spin2:237`) — the clock-stretch-stripped DAT singleton, unusable for the
DF2301Q and wrong-scoped for a 2nd bus. Memory's "INTEGRATION STEP — one edit to the prebuilt
driver" ([[voice-integration-design]]) is this swap.

**Current code:** `isp_voice_recognizer.spin2:237` → `i2c : "isp_i2c_singleton"`.

**Target:** `i2c : "isp_i2c"` (the VAR/instance, clock-stretch-honoring master). The driver's
per-instance VAR (`isp_voice_recognizer.spin2:240-250`) already isolates its own bus state, and
`isp_i2c`'s VAR isolates the bus pins/timing — so this single instance *is* bus 2 on whatever pins
`start()` receives.

**Integration points / API parity (verified):** the driver calls `i2c.setup(scl,sda,khz,pullup)`,
`i2c.present(DEV_WR)`, `i2c.start()`, `i2c.stop()`, `i2c.write()`, `i2c.read(i2c.NAK)`, and the
`i2c.PU_*` constants — all present in `isp_i2c.spin2` with identical signatures. The swap is
API-safe; only storage scope (DAT→VAR) and the restored clock-stretch differ.

**Config to settle at integration (not a design fork — a wiring-driven value):**
- **Speed:** `khz = 100` (DF2301Q standard; the driver's own quick-start).
- **Pull-up:** the `pullup` arg passed to `voice.start()`. Default to `i2c.PU_NONE` **iff** the
  voice-module board carries its own SDA/SCL pull-ups; otherwise an internal option (`PU_3K3`).
  This is the open electrical item from [[voice-integration-design]] ("power rail / 3.3-vs-5 V") and
  is resolved by the §6 wiring-doc metering, then encoded as the `voice.start()` pull-up argument.

**Verification (this section):**
- *normal:* compile sweep stays green with the swapped OBJ; `custom_words_example.spin2` (which
  also instantiates `isp_voice_recognizer`, `:22`) still compiles.
- *edge:* a 2-instance build (bus 1 singleton + bus 2 `isp_i2c` on P13/P15 and P18/P16) compiles
  with no pin/state collision — the instance variant was already compile-proven this way (memory).
- *error:* `voice.start()` on an absent/mis-wired module returns `bFound = FALSE`; callers must
  treat that as "voice disabled," not a hang (the bounded `STRETCH_LIMIT` guarantees no stuck-bus
  lock-up).

---

## §2 — IO cog: poll voice in the round-robin, publish recognized-CMDID telemetry

**Why:** memory's design — "add the voice poll as another cooperative round-robin task in the IO
cog's existing loop" ([[voice-integration-design]], [[spin2-task-concurrency]]). The IO cog already
owns a non-blocking service loop over LED / buzzer / ultrasonic (`isp_io_controller.spin2:170-180`);
voice becomes a 4th step. The IO cog **owns bus 2 and only publishes telemetry** — it does **not**
map and does **not** post to mailbox A. That keeps it a pure peripheral server (no dog reference, no
mapping), and makes "monitor the cog that can do voice" literally = read IO telemetry.

**Current code starting point:**
- OBJ block `isp_io_controller.spin2:52-58` (ring/buzzer/sonic/term/stack) — **add**
  `voice : "isp_voice_recognizer"`.
- `start(ledPin, buzzerPin, trigPin, echoPin)` `:95` and its `serviceLoop()` `:170` /
  `stepLed/stepBuzzer/stepRanging` `:225-257`.
- Telemetry DAT `:67-71` (`distMm`, `pingSeq`, `ledBusy`) — the exact latest-wins pattern to mirror.

**Target behavior:**
1. **Launch variant (avoid churning the other 5 tops).** `io.start()` has **6** launch/instantiate
   sites; only the voice build should change. Keep `start(led,buzz,trig,echo)` as-is and add
   `startWithVoice(led, buzz, trig, echo, vScl, vSda)`; `start()` calls `startWithVoice(..., -1, -1)`
   (voice disabled). A `vScl = -1` sentinel means "no voice bus on this build," so the 5 quiescent
   test tops (`test_dog_gaits/level/tricks/stand/panel`) stay **untouched and valid**.
2. In `startWithVoice`, when voice is enabled, call `voice.start(vScl, vSda, 100, <pullup>)` and
   record `bVoicePresent := result`. A `FALSE` (absent) result disables `stepVoice` for the run.
3. Add `stepVoice()` to `serviceLoop()`: if voice present, call `voice.pollCMDID()` (it self-limits
   to one bus read per ≥50 ms — `isp_voice_recognizer.spin2:304` — so calling it every pass is
   safe and non-blocking). On a **non-zero** result, publish it latest-wins:
   `voiceCmdId := id; voiceCmdSeq++`.
4. New telemetry DAT (mirror `distMm`/`pingSeq`): `voiceCmdId LONG 0`, `voiceCmdSeq LONG 0`, plus
   accessors `getVoiceCmdId() : id` and `getVoiceSeq() : seq` (DAT-only reads — cog-safe, like
   `getDistanceMm`/`getPingSeq`).

**Integration points:** none into the backend; this is self-contained in `isp_io_controller` +
the new `voice` child. Bus 2 is wholly owned here.

**Verification (this section):**
- *normal:* speaking a recognized word makes `getVoiceSeq()` advance and `getVoiceCmdId()` carry
  the DF2301Q CMDID; LED/buzzer/ranging keep running with no hitch (the round-robin invariant).
- *edge:* repeated identical recognitions each bump `voiceCmdSeq` (a consumer detects "new" by seq,
  not by value change) — confirm the seq bumps even when the CMDID repeats.
- *error:* module absent at launch (`bVoicePresent = FALSE`) → `stepVoice` is skipped, the cog runs
  exactly as today (LED/buzzer/ultrasonic unaffected); no bus-2 traffic, no hang.

---

## §3 — Top level: `robot_dog_top` becomes the dispatch loop (with motion-complete gating)

**Why:** Stephen's design — `robot_dog_top` "starts all the backend cogs and then sits in a loop …
monitoring the cog that can do voice … when it sees a voice command come in, it hands it to the
motion cog … every time a new command comes in, except it waits until an existing motion completes."
Today `robot_dog_top` is a **scripted demo**: cog0 runs `runConcurrentDemo()` then idles in `repeat`
(`robot_dog_top.spin2:126-131`). This section evolves cog0 from "scripted demo" into the **persistent
dispatch loop** — the real product top.

**Current code starting point:**
- `main()` `robot_dog_top.spin2:95-131`: launches IO cog `:109`, backend cog `:118`, then
  `runConcurrentDemo()` `:133-162` and idles.
- It already posts to mailbox A (`dog.postCommand(...)`, e.g. `:146`) and reads telemetry — so the
  "hand a command to the motion cog" primitive is proven; we change *what triggers* a post.

**Backend gating signals already exist (no backend work):**
- `dog.getMoveComplete() : bComplete` (`isp_dog_motion.spin2:368`) — FALSE while an eased move runs.
- `dog.getModeState() : mode` (`:329`) — `MODE_IDLE / MODE_GAITING / MODE_GESTURE_BUSY /
  MODE_RELAXED / MODE_LOWBATT`.
- `dog.isBusy() : bActive` (`:352`) — TRUE during a one-shot gesture; `dog.isHalted()` (`:359`).

**Target behavior — the dispatch loop (cog0):**
1. Launch: cog0 calls `io.startWithVoice(... , PIN_VSCL=18, PIN_VSDA=16)` (the §2 variant) plus the
   backend cog as today.
2. After init, enter a persistent loop (replacing `runConcurrentDemo` as the steady state):
   - Track `lastVoiceSeq`. Each pass, read `io.getVoiceSeq()`; if it advanced, a **fresh** voice
     CMDID is available via `io.getVoiceCmdId()`.
   - **This sprint:** on a fresh CMDID, **report it** — `DEBUG` the raw CMDID and its phrase via
     `names.cmdName(id)` (the observability deliverable; §4 is the dedicated harness, this is the
     same report wired into the product loop). Then pass it through the **map seam**
     `voiceToDogCmd(id) : dogCmd` — a single function that this sprint returns `CMD_NONE` for every
     input (the deferred sprint fills its table).
   - **Motion-gate (skeleton, exercised structurally):** before handing a mapped command to the
     motion cog, gate on completion: if the backend is mid one-shot (`isBusy()` /
     `getMoveComplete() == FALSE`), hold the command until it finishes; if `MODE_GAITING` (a latched
     gait that never self-completes), the new command is allowed to supersede/stop it. Because the
     map returns `CMD_NONE` this sprint, no `postCommand` fires — but the gating decision is computed
     and `DEBUG`-traced so the architecture is real and reviewable.
3. Preserve the concurrency self-test: keep the `runConcurrentDemo` body available (behind a startup
   `DEMO_ON_BOOT` CON or moved to a `test_*` top) so the 3-cog concurrency proof isn't lost; the
   default boot path is the dispatch loop.

**Integration points:** cog0 already holds `dog` and `io` references and posts to mailbox A — the
only new dependency is reading the §2 voice telemetry. No new mailbox, no cross-cog bus access.

**Verification (this section):**
- *normal:* with the dog supported on the bench, speaking recognized words prints "fresh CMDID =
  N (phrase)" once per recognition; the loop keeps sampling distance/attitude telemetry meanwhile.
- *edge:* two recognitions in quick succession each register as fresh (seq advances twice); the
  motion-gate trace shows "would-hold" vs "would-post" correctly against a *temporary* test mapping
  (see §7) for both a one-shot and a latched target.
- *error:* voice module absent → `getVoiceSeq()` never advances → the loop runs as a quiet
  orchestrator (telemetry only), never blocking; `isHalted()` (low batt) suppresses any handoff.

---

## §4 — Observability test harness: `src/test_voice.spin2`

**Why:** Stephen's stated initial test — "do we hear commands at all coming in over I²C, and which
commands do we see?" This is the **first gate**, isolated from motion: a minimal top that brings up
*only* the IO cog (voice on bus 2) and prints every recognized CMDID. It mirrors the existing
single-subsystem harness pattern (`test_imu.spin2`, `test_ping.spin2`).

**Target:** `test_voice.spin2` — `PUB main()`:
- `cogspin` the IO cog via `io.startWithVoice(PIN_WS2812, PIN_BUZZER, PIN_TRIG, PIN_ECHO, 18, 16)`
  (LED/buzzer available for the §5 indication; ultrasonic harmless).
- Loop: watch `io.getVoiceSeq()`; on advance, `DEBUG` `getVoiceCmdId()` + `names.cmdName(id)` and a
  running count. No backend cog, no servos — safe to run with the dog unpowered/unsupported.
- Print a startup banner including `voice.version()` and the bus pins, and an explicit
  "voice present = T/F" from the `start()` probe so a wiring fault is obvious immediately.

**Verification:** *normal* — each spoken built-in word prints its CMDID and phrase; *edge* — an
**unrecognized** utterance prints nothing (CMDID 0 is never published), confirming we only surface
real recognitions; *error* — module unplugged → banner shows "voice present = F" and the loop idles.

---

## §5 — Recognition LED indication (minimal now; full scheme documented for later)

**Why:** Stephen — the DF2301Q **speaks** its own verbal acknowledgement (free audible confirmation),
so the buzzer is not needed for ACK. The dog-side LED scheme is a "first thought" tied to "actual dog
shape": **moving/green = recognized & acting**, **red = command not recognized/refused**, **all off =
idle/complete**. That scheme only becomes *fully* meaningful once commands map to motion (the deferred
sprint), because "recognized-and-acting" vs "refused" requires the map.

**This sprint (minimal, useful for bench observation):** on any fresh recognition, the IO cog gives a
brief **green LED blink** on the ring (it already owns the ring — `ring.setColor/setMode/update`,
`isp_io_controller.spin2:191-208`) as a visual "I heard something," then returns to off. No
red/spinning states yet (nothing is refused or acting on motion this sprint).

**Documented target (carried into the deferred mapping sprint, not built now):** spinning/green while
a mapped command executes (gate on `getMoveComplete`), solid red on a recognized-but-unmapped or
`isHalted`-refused command, all-off on completion/idle. Recorded in the spec (§6) as the intended
feedback model so the next sprint implements against it.

**Verification:** *normal* — a recognized word produces one short green blink coincident with the
DEBUG line; *edge* — rapid recognitions each blink without the ring sticking on; *error* — voice
disabled → ring behaves exactly as today (no spurious blinks).

---

## §6 — Documentation deliverables

Keeping the project docs current is part of the work, not an afterthought.

1. **Wiring — `DOCs/P2-platform/P2_MIGRATION_WIRING.md` (has NO voice content today).** Add the
   **2nd I²C bus**: P18 = SCL, P16 = SDA (pin group 16; note it sits **outside** the committed P8–P15
   block, which had P16/P18 unallocated), DF2301Q @ `$64`, the **clock-stretch requirement**, and the
   **power rail / 3.3-vs-5 V** handling + **pull-up source** (board vs internal) — the open electrical
   item from [[voice-integration-design]]. Mark metered-vs-inferred per the doc's confidence
   convention; the pull-up finding feeds the §1 `voice.start()` argument.
2. **Pin-map tables — `CLAUDE.md` (and the §3 table in `P2_MIGRATION_WIRING.md`).** Add the bus-2
   row(s) and a "voice (DF2301Q)" device entry in the hardware table; note P16/P18 are now used (were
   "spare"). Keep v1.0-board framing.
3. **Spec — `DOCs/spec/P2-RobotDog-Specifications.md`.** New subsystem section: voice recognition,
   2nd bus + ownership, the recognized-CMDID telemetry, the dispatch-loop architecture, and the
   **intended LED feedback model** (§5 target). State explicitly that command→behavior mapping is a
   separate sprint.
4. **Theory-of-ops — `DOCs/P2_FIRMWARE_THEORY_OF_OPS.md`.** Update the cog/mailbox topology: IO cog
   now also owns bus 2 and publishes voice telemetry; cog0 is the persistent dispatch loop (no longer
   "scripted demo"). Update `robot_dog_top.spin2`'s header comment block (`:20-35`) to match.
5. **Subsystem docs** under `DOCs/subsystems/VoiceSensor/` are vendor/driver docs — reference, not
   rewritten here; cite them from the spec.

---

## §7 — Verification plan (the real gates)

Per project convention there is no automated behavioral runner — the automated gate is the
**compile-all sweep**; real verification is the **hardware bench**.

**Automated gate (host):** `pnut-ts -q` over every `src/*.spin2` stays green, including the swapped
voice OBJ (§1), the new `isp_io_controller` methods/telemetry (§2), the reshaped `robot_dog_top`
(§3), and the new `test_voice.spin2` (§4). `custom_words_example.spin2` and all 5 untouched IO-cog
test tops must still compile.

**Bench playbook (Stephen-driven on the P2 bench unit) — authored as its own doc via `test-playbook`
at execution:**
1. **Bus-2 recognition (`test_voice.spin2`, dog unpowered/safe):** banner shows "voice present = T";
   speaking each of a handful of built-in words prints the correct CMDID + phrase; an unrecognized
   utterance prints nothing; the module's own verbal ACK is heard; green blink coincides with each
   recognition. **This is the primary "do we hear commands, and which ones" gate.**
2. **Bus coexistence:** with the full `robot_dog_top` build, confirm bus 1 (servos/IMU/battery) is
   unaffected by bus 2 traffic — the dog still inits, calibrates, stands; ranging/LED still run; voice
   recognitions still register. (Two independent buses, two owners.)
3. **Dispatch-loop + gating skeleton:** temporarily point the §3 map seam `voiceToDogCmd()` at a
   **throwaway test mapping** (one built-in word → a one-shot like `CMD_NOD`, one → a latched gait,
   one → `CMD_STOP`) to *exercise* the loop end-to-end: confirm the one-shot blocks the next handoff
   until `getMoveComplete()`, the latched gait is interruptible by the next command, and `isHalted()`
   suppresses handoff. **Revert the throwaway mapping before closeout** — the real mapping is the next
   sprint. (`log`/DEBUG this so the temporary nature is unmistakable.)
4. **Absent-module degradation:** unplug voice → `robot_dog_top` runs as a quiet orchestrator, no
   hang, all other subsystems normal.

---

## Deferred / explicitly out of scope

- **Voice→dog command mapping + custom-slot assignment** — the next planned sprint. This sprint
  leaves a single `voiceToDogCmd()` seam returning `CMD_NONE`.
- **Full LED feedback scheme** (spinning-green-acting / red-refused / off-idle) — documented in the
  spec now, implemented when commands drive motion.
- **Unify the two I²C masters** (add clock-stretch back to the singleton) — already a deferred
  punch-list experiment (`DOCs/plans/PUNCH-LIST.md`).
- **A real comms/Wi-Fi command link** — still deferred (`robot_dog_top.spin2:23-24`).

## Open questions

**None blocking.** All design forks resolved with Stephen (posting via a top-level dispatch loop with
motion-complete gating; no behavior mapping this sprint — observability only; minimal green-blink
indication now with the full LED scheme documented for later). The one electrical unknown (bus-2
power rail / pull-up source) is **scoped in** as the §6 metering deliverable that sets the §1
`voice.start()` pull-up argument — it is resolved *within* this sprint, not a precondition to it.
