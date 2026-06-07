[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Hardware Certification — Functional Baseline (Dog-Like Motion arc entry + I2C-cutover gate)

> **📝 DRAFT for Stephen's review — RETOOLED 2026-06-07.** Research complete. Re-scoped from a
> manual exercise-by-exercise playbook run into a **control-panel-driven functional sweep**, and
> repositioned as the **entry baseline for the Dog-Like Motion arc**. **§0 Open Questions are
> Stephen's to resolve before `sprint-start`.** Nothing here is committed scope yet.

> **Project:** P2 Robot Dog (FNK0050 → Propeller 2 port) · firmware in Spin2/PASM2
> **Plan type:** certification sprint — *no new subsystems*; bench proof + doc reconciliation + a tagged build.
> **Build version:** targets **0.1.2** (from `0.1.1`; `FW_VERSION_*` in `src/isp_version.spin2`) —
> **stamped at closeout, after the sweep is green** (§0 Q3). Version is confirmed at `sprint-start`.
> **North star:** turn "compiles clean, behavior pending" into a **recorded functional-green
> baseline on the P2 bench unit** — the known-good floor the I²C cutover and the keystone build on.

## Why this exists now (the retool)

We have a finished interactive **dog control panel** — `src/test_dog_panel.spin2`: a DEBUG-PLOT
window of clickable buttons (keyboard-mirrored) that posts **every shipped command** through the
**production backend/IO mailboxes** (`dog.postCommand` / `io.postCommand`) in the real 3-cog shape,
with a live telemetry readout (mode / battery / tilt / head / distance / ping-seq) and **IMU-settle
logging after STAND/CROUCH/RELAX**. That means we can **rip through the whole command set fast** —
click each move, any order — and the captured DEBUG session **log is the audit**: did every command
post, complete (highlight clears on completion, not on timeout), and leave telemetry sane?

**This sprint's role in the arc.** It is the **functional-green entry baseline** for the
Dog-Like Motion work, *and* the **regression gate for the non-singleton I²C cutover**:

```
  THIS sprint: baseline cert (current singleton I²C)
        → I²C cutover (sibling effort)
        → re-cert (re-run this sweep, diff the logs)        ← proves the swap is behaviour-neutral
        → DOG-LIKE-MOTION-01 keystone execution
```

Per [[production-path-testing]], everything is exercised **through the production mailboxes** in the
real 3-cog shape — never a bespoke shortcut path.

**Prior bench bring-up is real.** The 13-joint servo calibration was metered with a graphical tool
and applied live; the IMU stance trim was measured via a repeatable crouch-approach protocol; real
defects (relax shoulder-swing, task-stack overflow, the BR-leg diagnosis) were found and fixed on
the metal. So this is **not first contact with the bench** — what is missing is a single,
**complete, recorded** functional pass of the *whole current command set*, now cheap via the panel.

---

## §0. Open questions / scope decisions — *owner: Stephen* (resolve before start)

The draft below encodes my *recommended* answer to each; confirm or correct.

1. **Sequencing & this doc's reuse.** The plan is **baseline cert → I²C cutover → re-cert →
   keystone** (above). This doc is the **reusable certification mechanism** — the same §1 panel
   sweep + §2 scripted-driver record are run *twice*: once now (baseline, singleton I²C) and once
   after the cutover (re-cert, §6). → **Recommended:** adopt as written. Confirm.

2. **I²C-cutover packaging.** The non-singleton I²C cutover is a real implementation effort (driver
   rewrite + reseating every object's bus handle), distinct from *certifying*. → **Recommended:** it
   gets its **own plan doc**; THIS doc only **brackets** it (baseline before, re-cert after) — keeps
   the cert mechanism clean and reusable. Confirm, or fold the cutover in here as a section.

3. **Tag-gating: is 0.1.2 cut *only after* the sweep passes green?** 0.1.1 was tagged at
   code-complete with behavior pending; a certification sprint inverts that. → **Recommended:** 0.1.2
   is stamped + tagged in §5 **only after §1 is green** (findings fixed, not carried). Confirm.

4. **Calibration scope — most of it is moot here.** Servo trims + IMU stance leveling are **done and
   applied** (history below). Two things matter, and one is short-lived:
   - **Durable:** confirm the 13-joint servo trims still center cleanly (folded into the §1 sweep —
     no separate run), and **lock the sign convention** (`isp_calibration.spin2:60` still says
     "confirm on bench").
   - **Short-lived:** the stance `stancePitchDeg=-3` / `stanceRollDeg=+2` (`isp_calibration.spin2:61-62`)
     are **about to be re-zeroed and re-measured against the new loaded-rear crouch by keystone §4** —
     so **do not over-invest** in nulling their residual now. A quick observational "stand looks
     level" via the panel's IMU-after-STAND log is enough. → **Recommended:** scope §3 to the durable
     servo-trim check + sign-lock; defer the stance pitch/roll residual to keystone. Confirm.

   *Calibration history (grounding):* graphical calibrator `test_cal_full.spin2` (`{Spin2_v50}` DEBUG
   PLOT) produced a **full re-meter 2026-06-03** (`d30f1ec`) — `legTrim` `isp_calibration.spin2:51-54`
   + `HEAD_TRIM_DEG=12` `:34` — applied live at leg init (`isp_robot_dog.spin2:217-223`, `:237`). The
   README §3 "FL/BR tibia trim pending" note is **stale**.

---

## Verification model (whole sprint)

Three tiers, each with a distinct job:

- **Automated gate (in-container):** the clean `pnut-ts` **compile sweep** over `src/*.spin2`
  (`BUILD_COMMAND`/`TEST_COMMAND`) — currently **41/41 green**; stays green at every step.
- **§1 Control-panel sweep (primary, fast functional cert):** `test_dog_panel.spin2`, **interactive**
  (windowed — mouse/keyboard). Drive every command once; the captured session log is the audit. Best
  for "**does it all still work at all?**" — complete command coverage in minutes.
- **§2 Scripted end-marker drivers (deterministic regression record):** `test_dog_stand` /
  `test_dog_level` / `test_dog_gaits` / `test_dog_tricks`, **headless** with fixed sequences + end
  markers (`pnut-term-ts ... -b 2000000 --headless --end-marker ...`, [[headless-debug-baud]]). These
  are **reproducible**, so their logs are the artifact **re-run identically after the I²C cutover**
  and diffed (§6) — the panel sweep, being human-paced and order-free, can't be diffed that cleanly.

**What the panel sweep proves / doesn't.** Proves *functional*: every command posts, the move
**completes** (the watcher clears the highlight on completion vs. a safety timeout), gaits run and
STOP, telemetry stays live, IMU settles. Does **not** prove *qualitative*: smoothness, a subtle
residual tilt, or a silently clamp-pegged joint. Label the baseline **"functional-green,"** not full
qualitative cert — that's exactly the bisect anchor the cutover and keystone need.

---

## 1. Control-panel functional sweep — *the certification itself*

**Why.** This is the sprint's reason to exist: one **complete, recorded** functional pass of the
whole current command set, fast, through the production mailboxes.

**Mechanism.** Run the panel (from its header):

```
  pnut-ts -d -q src/test_dog_panel.spin2
  cd src && pnut-term-ts -r test_dog_panel.bin -b 2000000      # bare BMP names resolve here
```

Preconditions (already documented): **>> LIFT/SUPPORT THE ROBOT <<** on launch (cog1 gyro-cal, then
soft-start to RELAX), **Load/servo switch ON**, **~1 kΩ series R into P9** for ECHO, healthy battery.
`DEBUG_MASK` defaults to **commands + IMU** logging on — that *is* the audit stream.

**Coverage is by construction** — the panel already exposes the entire shipped set, so the four
post-0.1.1 behaviors that the old playbook lacked are covered automatically:
- **Poses:** STAND / SIT / **CROUCH** / RELAX / STOP / DOWN(LIE) / BOW / PARADE-REST(key `r`).
- **Gaits:** FWD / BACK / TURN-L/R / STEP-L/R / SPIN — cadence from the SPEED radio (SLOW/NORM/FAST).
- **Gestures:** HELLO / **SHAKE** / **SALUTE** / PUSHUPS / NOD / SPEAK.
- **Head:** pan 60 / 90 / 120.   **IO:** LED (6 patterns) / BEEP / RANGE toggle.
- **Power-on glide:** observed at launch (crouch→eased rise to RELAX/STAND, no snap).

**Headline unproven items get exercised in passing** (ToOps §9): toggle **RANGE while a gait runs**
→ the ping-seq readout must keep incrementing (non-blocking smart-pin ranging during motion); every
gait/pose exercises **CORDIC IK + the joint side-mirror**; **smooth-motion quality** is watched live
(gapless, beats Freenove's staccato).

**Battery-warning band (opportunistic).** On a pack sitting **6.4–6.8 V**, the panel's battery
readout + the throttled `LOW-BATTERY` log (`BATTERY_WARN_MV=6800`, `isp_robot_dog.spin2:109`) appear
**without** the mode dropping to `MODE_LOWBATT` (the 6.4 V floor). Pack-state dependent.

**Target / deliverable.** A captured panel-session log showing **every command posted → completed**,
telemetry sane throughout, IMU-after-STAND ≈ level — recorded as the **functional-green baseline**.
**Findings → `defect-fixing`** as one gathered symptom set, fixed before closeout (§0 Q3).

**Verification.** *Normal:* each command's highlight clears on completion (not timeout); gaits STOP
cleanly; STAND returns to the leveled stance. *Edge:* command mid-gait blends (no restart);
HELLO/SHAKE rejects while busy; ping-seq advances with RANGE on during a gait. *Error:* a move that
only clears on the safety timeout, a flat ping-seq under RANGE, or a clamp-slam is a finding.

## 2. Deterministic regression record — scripted end-marker drivers

**Why.** The panel sweep is human-paced and order-free, so its log can't be **diffed** cleanly. The
scripted drivers run a fixed sequence headless to an end marker — their logs are the **reproducible
artifact** we re-run identically after the I²C cutover (§6) to prove the swap changed nothing.

**Target.** Run each headless, capture the log as the baseline record:
- `test_dog_stand` (STAND/CROUCH/RELAX/SIT + readback), `test_dog_level` (crouch→stand→measure ×3),
  `test_dog_gaits` (FWD/BACK/TURN/STEP), `test_dog_tricks` (SIT/SHAKE/SALUTE → `TRICKS_DONE`).
- Store the captured logs under `src/logs/` (the established convention) tagged as the **0.1.2
  baseline** set, so the §6 re-cert diff has a fixed reference.

**Verification.** Each driver reaches its end marker with expected telemetry; the log set is archived
as the named baseline. (These same drivers are also keystone §7's bench harnesses — certifying them
green now makes that later check differential.)

## 3. Calibration close-out — durable servo-trim check + sign-lock (stance trim deferred to keystone)

**Why.** Servo calibration + IMU leveling are **done and applied** (§0 Q4). This section closes only
the **durable** residue and explicitly **defers** the part keystone will redo.

**Target.**
- **Servo trims:** confirm joints center cleanly under the committed `legTrim` during the §1
  pose/gait sweep (the old "FL/BR toes sit slightly low" symptom gone); a persistent symptom is a §1
  finding — **no separate run**.
- **Sign-convention lock:** `isp_calibration.spin2:60` still reads "confirm on bench." Use the
  panel's IMU-after-STAND log to confirm the trim direction reduces tilt, and **update the comment to
  the bench-confirmed sign.**
- **Stance pitch/roll residual — DEFERRED.** `stancePitchDeg=-3` / `stanceRollDeg=+2` are re-zeroed
  and re-measured against the loaded-rear crouch in **keystone §4**; do not null their residual here.
  A panel IMU-after-STAND "looks level" observation is sufficient.

**Verification.** Servo centers clean; sign comment locked to the bench-confirmed direction; a note
recorded that stance pitch/roll certification is owned by keystone, not this sprint.

## 4. Reconcile the docs the certification invalidates (durable fixes first)

**Why.** Certification turns "⚠ verify/⚠ bench" claims into "proven," and post-0.1.1 drift left docs
describing a 0-trim world whose command set ends at `CMD_STEP_RIGHT`.

**Target — prioritize the durable edits; flag the short-lived ones:**
- **Durable:** add shipped-but-unspecified commands (`CMD_CROUCH/SHAKE/SALUTE`, and BOW/LIE/NOD/
  PUSHUPS/SPIN/SPEAK if absent) to the spec §4.1 mailbox-A table + `src/README.md`; correct the
  power-on narrative (crouch→eased-rise, not "deliberate snap"); add the 6.8 V **warning band**
  alongside the 6.4 V cutoff; mark CORDIC IK / side-mirror / integrated ranging / smooth-motion as
  **verified through motion** (ToOps §9 → resolved, bench-dated).
- **Short-lived (light touch — keystone §5 re-touches):** the stance-trim *values* in
  `DOCs/spec/P2-RobotDog-Specifications.md` and the playbook (the `-3/+2`) — note they are
  **being re-measured against the new neutral by the keystone sprint**, rather than re-asserting
  numbers this sprint is about to invalidate.

**Verification.** Docs render; cross-references resolve; **no doc still omits a shipped command**;
every "proven" claim traces to a §1/§2 result; stance-trim numbers carry the "re-measured in keystone"
note rather than a soon-stale value.

## 5. Build-wrapup → tagged 0.1.2 baseline

**Why.** The reconciled docs + the functional sweep constitute build 0.1.2; stamp at closeout, gated
on §1 green (§0 Q3).

**Deliverables.**
- **Bump `FW_VERSION`** `src/isp_version.spin2` (`0.1.1` → version set at `sprint-start`).
- **Author `DOCs/RELEASE-NOTES.md`** (does not exist yet) via `build-wrapup` — first entry: the 0.1.2
  audience summary (power-on glide, crouch, shake/salute, battery warnings, **the functional-green
  certification milestone itself**, and that it is the arc/I²C baseline).
- **Sprint closeout** (`sprint-closeout`): per-section audit; exit baseline (compile sweep green +
  panel/driver logs archived); tag the build.
- **Punch-list sweep** (`punch-list-maintenance`): archive what this sprint confirmed done; LED gamma
  stays deferred.

**Verification.** `FW_VERSION` reads the bumped value; release notes render and match shipped
behavior; closeout reports certification state **honestly** — "functional-green on the bench," any
carried finding named.

## 6. Re-cert after the I²C cutover *(runs only when the cutover lands — same mechanism)*

**Why.** The cutover is transport-only; everything reaches the bus through PCA9685/MPU6050/ADS7830,
so a clean re-run **is** the proof it changed nothing.

**Target.** After the non-singleton I²C cutover: re-run the **§1 panel sweep** (fast functional
confirm) and the **§2 scripted drivers** headless, **diff the §2 logs against the 0.1.2 baseline
set**. A clean diff certifies the swap behavior-neutral; any delta is a cutover finding. Only then is
the keystone clear to execute (per its Entry-prerequisites note).

**Verification.** §2 driver logs diff clean vs. baseline; panel sweep functional-green; result
recorded as the cutover's regression gate.

---

## Out of scope (explicit)

- **The I²C cutover *implementation*** — its own effort (§0 Q2); this doc only brackets it.
- **Speech / vision / Bluetooth remote** — recorded futures; not this sprint (no new subsystems).
- **Real Wi-Fi/serial command link (cog 0 comms)** — still deferred; orchestrator stays scripted.
- **Live closed-loop IMU balance** — still deferred; leveling remains static.
- **Stance pitch/roll re-measure & any new gait/gesture/pose** — owned by the keystone sprint, not here.

## Sprint-start record — *to be filled at `sprint-start`*

- **Build version:** targets **0.1.2** (from `0.1.1`) — *confirm at start.*
- **Tracking-readiness (entry):** *run `tracking-readiness` at start.*
- **Baseline-health (entry):** compile sweep **41/41 green** as of drafting (PNut-ts v1.55);
  *re-confirm at start.* Caveat: green compile ≠ on-hardware correctness — this sprint closes that gap.

## Section ↔ task cross-reference — *to be filled at `plan-to-tasks`*

| Plan § | Deliverable | Task | seq | Depends on |
| ------ | ----------- | ---- | --- | ---------- |
| §1 | Control-panel functional sweep (the cert) | TBD | 1 | — |
| §2 | Scripted-driver deterministic baseline logs | TBD | 2 | — |
| §3 | Servo-trim check + sign-lock (stance deferred) | TBD | 3 | §1 |
| §4 | Reconcile docs (durable-first) | TBD | 4 | §1, §2, §3 |
| §5 | Build-wrapup → tagged 0.1.2 baseline | TBD | 5 | §1, §2, §3, §4 |
| §6 | Re-cert after I²C cutover | TBD | 6 | §5 + cutover |

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
