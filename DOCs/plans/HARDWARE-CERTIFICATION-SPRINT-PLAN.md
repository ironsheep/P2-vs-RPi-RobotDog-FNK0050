[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Hardware Certification + 0.1.2 Baseline — Sprint Plan

> **📝 DRAFT for Stephen's review** — research complete; **§0 Open Questions must be
> resolved before this becomes a startable plan** (`sprint-start`). Nothing here is committed
> scope yet.

> **Project:** P2 Robot Dog (FNK0050 → Propeller 2 port) · firmware in Spin2/PASM2
> **Plan type:** sprint plan (a ship commitment — bench proof + doc reconciliation + a tagged build)
> **Build version:** targets **0.1.2** (from `0.1.1`; `FW_VERSION_*` in `src/isp_version.spin2`) —
> **stamped at closeout, after the bench passes** (see §0 Q2).
> **North star:** turn "compiles clean, behavior pending" into **"proven on the P2 bench unit"** —
> the first build whose behavior is actually certified, with docs that match the metal.

This is a **certification sprint: no new subsystems.** Everything in `src/` already compiles
clean (41/41, PNut-ts v1.55) and is feature-complete: build 0.1.1 (smooth-motion engine, gait
catalog, 3-cog integration, IMU static leveling) **plus** the post-0.1.1 work now reconciled onto
`main` — gentle power-on glide, deep `CMD_CROUCH`, low-battery warning logging, the 2026-06-03
calibration re-meter (servo trims **and** stance leveling), diagnostics parity across the bench
rungs, and the new `CMD_SHAKE` / `CMD_SALUTE` paw gestures.

**Substantial bench bring-up has already happened** — it is what produced the post-0.1.1 work
above. The full 13-joint servo calibration was metered with a graphical tool and applied live; the
IMU stance trim was measured on the bench via a repeatable crouch-approach protocol and applied;
real defects (relax shoulder-swing, task-stack overflow, the BR-leg diagnosis) were found and fixed
on the metal. So this sprint is **not first contact with the bench.** What it lacks is a
**single, complete, recorded end-to-end pass** of the formal playbook against the *whole* current
command set, plus the handful of behaviors never formally exercised. The job is to **run that
recorded pass, confirm the one open calibration item (§0.1), reconcile the docs the metal
invalidates, and cut a tagged 0.1.2.** The likely-next direction (speech recognition) is explicitly
**out of scope** (below).

---

## §0. Open questions / scope decisions — *owner: Stephen* (resolve before start)

Research surfaced four scope calls that are **Stephen's to make**, not mine to assume. The draft
sections below encode my *recommended* answer to each; confirm or correct.

1. **Calibration & IMU leveling are already DONE on the bench — confirm what (if anything) remains.**
   The brief said *"meter the two zeroed calibration trims."* That premise is stale: **both the
   servo calibration and the IMU stance leveling were built, metered, and applied during prior bench
   bring-up** — this sprint does not meter them.
   - **Servo trims (all 13 joints):** a validated graphical calibrator (`test_cal_full.spin2`,
     `{Spin2_v50}` DEBUG PLOT panel — `b327bda` proved the pipeline on one joint, `aae967d` scaled
     to all 13, with a HOWTO + `tools/gen_cal_assets.py`) produced a **full re-meter 2026-06-03**
     (`d30f1ec`): `legTrim` `isp_calibration.spin2:51-54` (FL −25/−24/−6, BL −4/−6/−9, FR
     −10/−19/−14, BR −6/0/−11) + `HEAD_TRIM_DEG = 12` `:34`, superseding the 2026-06-01 set. These
     are **applied live at leg init** — `isp_robot_dog.spin2:217-223` (`flLeg.setCalibration(cal.legTrims(...))`
     ×4) and `:237` (head). The README §3 "FL/BR tibia trim pending" note is simply **stale**.
   - **IMU stance leveling:** `cf26e5a` is *"from bench bring-up of the IMU-leveling rung."* A
     repeatable **crouch→stand→measure ×3** protocol (`test_dog_level.spin2`, the crouch-approach
     takes up backlash one way → repeatable within ~0.3°) measured `stancePitchDeg = -3` /
     `stanceRollDeg = 2` `:61-62`, applied via `stanceTrimY()` → `setLevelStandTargets()`
     (`isp_robot_dog.spin2:778`, `:832`).
   → **The only genuinely-open calibration item** is whether a **residual** pass — re-run
   `test_dog_level` *with* the −3/+2 trim applied, expecting residual ≈ 0, and **lock the sign
   convention** (`isp_calibration.spin2:60` still says "confirm on bench") — has been recorded yet.
   The commit captured the −3/+2 as the *measured* tilt; it does not state a trim-applied re-run.
   → **Recommended:** §3 is narrowed to **that one residual-confirmation + sign-lock** (plus an
   observational "joints center cleanly" check folded into the §2 motion exercises) — **not**
   re-metering. Confirm, or tell me the residual pass is already done (then §3 collapses into doc
   de-staling only).

2. **Tag-gating: is 0.1.2 cut *only after* the bench passes green?**
   0.1.1 was tagged at code-complete with behavior pending. A *certification* sprint inverts that:
   the deliverable **is** the behavioral proof. → **Recommended:** 0.1.2 is stamped + tagged in §5
   **only after §2's playbook run is green** (findings fixed, not carried). Confirm.

3. **Bench-failure handling.** The playbook's own rule is *fix-in-sprint by default* (a failed
   exercise goes to `defect-fixing`; only a deliberately-carried failure lands on the PUNCH-LIST).
   → **Recommended:** keep that default. Confirm, or name any exercise you'd rather carry than block
   the tag on.

4. **Do the post-0.1.1 behaviors get formal playbook exercises, or spot-checks?**
   Power-on glide, `CMD_CROUCH`, the 6.8 V battery-warning log, and `CMD_SHAKE`/`CMD_SALUTE` (driver
   `test_dog_tricks.spin2` already exists) are **not** in the 0.1.1 playbook. → **Recommended:**
   formalize them as new numbered exercises (§1) so certification coverage matches the shipped
   command set — no silent gaps. Confirm.

---

## Verification model (whole sprint)

- **Automated gate (in-container):** the clean `pnut-ts` **compile sweep** over `src/*.spin2`
  (`BUILD_COMMAND`/`TEST_COMMAND`, `.claude/skill-conventions.md`) — currently **41/41 green**.
  This is the only automated check; it stays green at every step.
- **Real verification (bench, Stephen-run):** the **hardware bench playbook**, run on the P2 bench
  unit. Per [[production-path-testing]], every behavior is exercised **through the production
  backend mailboxes** (`dog.postCommand` / `io.postCommand`) in the real 3-cog shape — never a
  bespoke shortcut path. **Do not assume Stephen is at the bench during authoring;** §1 extends the
  playbook in-container so it is ready to run when he is.
- This sprint's headline is a **complete, recorded end-to-end playbook pass.** Individual behaviors
  have been exercised on the bench during bring-up (that is where the calibration, the leveling
  trim, and several defect fixes came from), but the formal numbered playbook has **never been run
  start-to-finish and its results recorded** — and it predates the post-0.1.1 command set. This
  sprint closes both gaps.

---

## 1. Extend the bench playbook to cover the post-0.1.1 behaviors

> **✅ DELIVERED (ahead of sprint-start).** The playbook
> [`SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md`](SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md)
> is extended to **Exercises 0–8**, **reordered foundational-first** (crouch base → glide/poses →
> leveling → gaits → gestures → concurrency → safety). `test_dog_stand` now posts
> `CMD_CROUCH`→`CMD_STAND` as its first moves so the crouch is proven first. **The playbook is the
> source of truth for exercise numbering;** the pre-extension references below are retained only as
> the rationale for the change.

**Why.** The existing playbook (`DOCs/plans/SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md`,
Exercises 0–5) was authored for 0.1.1 and predates four shipped behaviors. Certifying 0.1.2 with
the 0.1.1 exercise set would leave the new command surface unproven — a silent coverage gap.

**Current starting point (what exists, uncovered).**
- **Power-on glide** — `seedStand()` `isp_robot_dog.spin2:820-833` now snaps once to a deep crouch
  (`CROUCH_HEIGHT_MM = 55`, `:73`) then arms an eased **glide up** over `POWERON_FRAMES = 75` (~1.5 s,
  `:119`). The 0.1.1 Exercise 1 begins *after* "init STAND" and never inspects the rise itself.
- **`CMD_CROUCH`** — new latched pose, enum `:52`, handler `:503-505` → `crouchPose()` `:798`. No
  exercise drives it.
- **Low-battery warning log** — `BATTERY_WARN_MV = 6800` `:109` (distinct from the 6.4 V safety-floor
  cutoff proven in Exercise 5), throttled `BATTERY_WARN_SECS = 5` `:110`, emitted at `:464-465`. No
  exercise observes the warning band.
- **`CMD_SHAKE` / `CMD_SALUTE`** — new one-shot paw gestures, enum `:52`, staged advance
  `advancePawGesture()` `:694-759`; driver **`src/test_dog_tricks.spin2`** already posts
  SIT/SHAKE/SALUTE through mailbox A (end-marker `TRICKS_DONE`). No playbook exercise references it.

**Target (deliverable: the updated playbook doc).**
- **Reframe Exercise 2 (IMU leveling)** for the *already-applied* trim: today it reads as a
  measure-from-zero flow ("trim is 0 → this MEASURE is the RAW tilt"). With `stancePitchDeg = -3` /
  `stanceRollDeg = 2` committed, the first run is a **residual** check (expect ≈ 0). Keep the
  measure-from-zero procedure as the *fallback* if residual is off (§3).
- **New Exercise — power-on glide:** on launch, the body **rises** crouch→stand smoothly over
  ~1.5 s with no snap to attention (`test_dog_stand` already triggers it; add the observation +
  pass/fail key).
- **New Exercise — `CMD_CROUCH`:** post `CMD_CROUCH`, confirm an eased descent to the symmetric deep
  crouch (feet under body, X = 0), then `CMD_STAND` rises back. (Extend `test_dog_stand` or add a
  one-line post; name the driver in the plan-to-tasks step.)
- **New Exercise — battery-warning band:** on a pack sitting **6.4–6.8 V**, confirm the throttled
  `LOW-BATTERY` warning logs ~every 5 s **without** tripping the safety floor (mode stays out of
  `MODE_LOWBATT`); pairs with Exercise 5's below-6.4 V floor. Opportunistic (pack-state dependent),
  like Exercise 5.
- **New Exercise — paw gestures:** run `test_dog_tricks.spin2` (`TRICKS_DONE`); confirm SIT base →
  right-front paw SHAKE (handshake bob) → returns seated; STAND; SIT → SALUTE (paw held high) →
  returns seated. Gesture rejects while busy (D3); other three legs hold the sit.

**Integration points.** The playbook doc; the existing scenario drivers (`test_dog_stand`,
`test_dog_tricks`); the §2 run consumes the extended doc.

**Verification.** Compile sweep stays green; the playbook is complete, numbered, pass/fail-keyed,
and runnable end-to-end by Stephen with **no behavior in the shipped command set left uncovered**
(normal case: each new exercise has a driver + expected result; edge: busy-reject for gestures,
warning-vs-cutoff boundary for battery; error: a driver that never reaches its end-marker is a
finding). Authored via the `test-playbook` skill.

## 2. Execute the full bench playbook on the P2 unit — *the certification itself*

**Why.** This is the sprint's reason to exist. Pieces have been exercised on the bench during
bring-up, but never as **one complete, recorded end-to-end pass** of the formal playbook against
the whole current command set. Certification = that pass actually happening and its results
recorded inline.

**Current starting point.** Four 0.1.1 scenario drivers + the new `test_dog_tricks`, all in the
production 3-cog shape; the headless recipe (`pnut-term-ts ... -b 2000000`, [[headless-debug-baud]])
and the `>> LIFT/SUPPORT THE ROBOT <<` preamble are in the playbook. The **~1 kΩ series R into P9**
and **Load switch ON** preconditions are already documented.

**Target.**
- Run **Exercise 0** (compile sweep, host) green first, then every bench exercise **1–8** on the P2
  unit (the §1 extension, now ordered **foundational-first** — crouch base proven before the
  glide/poses/leveling that build on it), recording `[x]`/`[ ]` and the captured numbers inline.
- The **headline unproven items** get explicit attention (ToOps §9): the **non-blocking smart-pin
  ranging path** producing fresh `pingSeq` *while a gait runs* (Exercise 6), the **CORDIC IK + joint
  side-mirror through motion** (every gait/pose exercise), and the **smooth-motion quality bar**
  (gapless, beats Freenove's staccato — Exercises 2, 4).
- **Findings → `defect-fixing`** as one gathered symptom set (per §0 Q3), fixed before closeout;
  re-run the affected exercise to green.

**Integration points.** The whole firmware, on hardware; results feed §3 (calibration confirm), §4
(doc reconciliation — "proven" replaces "⚠ verify/bench"), and §5 (closeout gate).

**Verification.** Normal: each exercise reaches its end-marker with the expected behavior. Edge:
blend (command mid-gait, no restart), busy-reject (HELLO/SHAKE while busy), reachability guard (no
joint slams a limit). Error: a red exercise is a finding, triaged not ignored. The sprint cannot
close (§5) with an un-triaged red exercise.

## 3. Close out the one open calibration item — leveling residual + sign-lock

**Why.** Servo calibration and IMU leveling are **done and applied** (§0.1): the 13-joint trims
were metered with `test_cal_full` and a full re-meter committed 2026-06-03 (`d30f1ec`), applied at
leg init (`isp_robot_dog.spin2:217-223`, `:237`); the stance trim was measured on the bench
(`cf26e5a`) and is folded into the stand. This section is therefore **not** a re-meter — it closes
the single thing the history does not show recorded: a **trim-applied residual pass** and the
**sign-convention lock**. (Per §0.1; if Stephen confirms the residual pass is already done, this
section collapses into §4 doc de-staling only.)

**Current starting point.**
- The −3/+2 in `isp_calibration.spin2:61-62` is the *measured* neutral tilt; the commit does not
  state a re-run **with the trim applied** showing residual ≈ 0.
- The sign convention is still annotated "confirm on bench" (`:60`).
- The harness already supports this exactly: `test_dog_level.spin2` `reportStoredTrim()` prints
  *"trim applied → this MEASURE is the RESIDUAL tilt; expect ~0"* when the trim is non-zero, and the
  crouch→stand→measure ×3 protocol is already in place (no new tooling needed).

**Target.**
- Run `test_dog_level` (now with −3/+2 committed) → record the **residual** pitch/roll; expect ≈ 0.
  If residual *grew* vs. the raw −3/+2, the sign is inverted → negate the stored values, re-run,
  and **update the `:60` sign-convention comment to the bench-confirmed direction.** If residual is
  ≈ 0, leveling is certified as-is.
- **Servo-trim observation (folded into §2's pose/gait exercises, not a separate run):** confirm
  joints center cleanly and the old "FL/BR toes sit slightly low" symptom is gone under the
  committed knee trims; if it persists, it is a §2 finding.

**Integration points.** `isp_calibration.spin2` (the `:60` sign-convention comment; only re-touch
the −3/+2 values if the residual forces a negate); the §2 leveling/pose exercises; §4 (the stale
"trims default 0" doc claims get corrected to the committed, bench-confirmed values).

**Verification.** Normal: residual ≈ 0 with the trim applied → leveling certified, sign comment
locked. Edge: residual *grew* → negate, re-run, confirm. Error: a residual that won't null even
after the negate is a finding for `defect-fixing` (not a silent re-paste) — but note this is an
*unlikely* tail, since the −3/+2 came from a 3-cycle protocol already repeatable within ~0.3°.

## 4. Reconcile the docs the certification invalidates

**Why.** Documentation is a sprint deliverable. Certification turns "⚠ verify/⚠ bench" claims into
"proven," and the post-0.1.1 drift left several docs describing a world where the trims are 0 and
the command set ends at `CMD_STEP_RIGHT`. The metal is now ahead of the docs.

**Deliverables (each a concrete edit, grounded in what §2/§3 proved).**
- **Spec — `DOCs/spec/P2-RobotDog-Specifications.md`:** add the shipped-but-unspecified commands to
  the §4.1 mailbox-A table (`CMD_CROUCH`, `CMD_SHAKE`, `CMD_SALUTE`) and the §2 engine notes
  (power-on glide: crouch→eased-rise, not the "deliberate snap" §2 currently states); correct §5 /
  §7 so the stance trims read as **metered (−3/+2), bench-confirmed**, not "default 0"; add the
  6.8 V **warning band** alongside the 6.4 V cutoff in §6.
- **`src/README.md` §3:** drop the stale "small tibia trim pending" note (now metered/confirmed);
  add the new commands; mark the CORDIC IK / side-mirror as **verified through motion** (was ⚠).
- **`DOCs/P2_FIRMWARE_THEORY_OF_OPS.md` §9:** move the now-proven items (integrated ranging, IK,
  smooth-motion quality) from "to verify on hardware" to resolved, with the bench date.
- **Top-level `README.md` Status:** refresh the "Early-stage … under development" line to reflect a
  bench-certified 0.1.2 (the *futures* section added this sprint stays as-is).

**Verification.** Docs render; cross-references resolve; **no doc still claims a trim is 0 or omits a
shipped command**; every "proven" claim traces to a §2/§3 result.

## 5. Build-wrapup → tagged 0.1.2 baseline

**Why.** The reconciled drift + the certification together constitute build 0.1.2; the project's
discipline is to stamp the version and record the build at closeout (not mid-drift). Gated on §2
green (§0 Q2).

**Deliverables.**
- **Bump `FW_VERSION`** `src/isp_version.spin2:24-26` (`0.1.1` → `0.1.2`).
- **Author `DOCs/RELEASE-NOTES.md`** (does not exist yet) via the `build-wrapup` skill — first
  entry: the 0.1.2 audience-facing summary (power-on glide, crouch, shake/salute, battery warnings,
  bench-confirmed leveling, **and the certification milestone itself**).
- **Sprint closeout** (`sprint-closeout`): per-section audit, exit baseline (compile sweep still
  green + bench results recorded), tag the build.
- **Punch-list sweep** (`punch-list-maintenance`): archive anything this sprint confirmed done; the
  LED gamma item stays deferred (no fade/breathing effect yet).

**Verification.** `FW_VERSION` reads 0.1.2; release notes render and match the shipped behavior;
the closeout reports certification state **honestly** — "proven on the bench," with any carried
finding named, not glossed.

---

## Out of scope (explicit)

- **Speech recognition** — the likely-next direction; **not this sprint** (no new subsystems).
- **Vision recognition** and a **Bluetooth remote-command radio** — the other two recorded futures
  (README); not this sprint.
- **Real Wi-Fi/serial command link (cog 0 comms)** — still deferred; the orchestrator stays a
  scripted demo.
- **Live closed-loop IMU balance** — still deferred; leveling remains static.
- **Any new gait/gesture/pose** beyond the shipped set — this sprint certifies what exists.

## Sprint-start record — *to be filled at `sprint-start`*

- **Build version:** targets **0.1.2** (from `0.1.1`) — *confirm at start.*
- **Tracking-readiness (entry):** *run `tracking-readiness` at start.*
- **Baseline-health (entry):** compile sweep **41/41 green** as of this drafting (PNut-ts v1.55);
  *re-confirm at start.* Caveat unchanged: green compile ≠ on-hardware correctness — this sprint
  exists to close exactly that gap.

## Section ↔ task cross-reference — *to be filled at `plan-to-tasks`*

| Plan § | Deliverable | Task | seq | Depends on |
| ------ | ----------- | ---- | --- | ---------- |
| §1 | Extend the bench playbook (post-0.1.1 coverage) | TBD | 1 | — |
| §2 | Execute the full playbook on hardware | TBD | 2 | §1 |
| §3 | Confirm committed calibration on the bench | TBD | 3 | §2 |
| §4 | Reconcile docs the certification invalidates | TBD | 4 | §2, §3 |
| §5 | Build-wrapup → tagged 0.1.2 baseline | TBD | 5 | §2, §3, §4 |

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
