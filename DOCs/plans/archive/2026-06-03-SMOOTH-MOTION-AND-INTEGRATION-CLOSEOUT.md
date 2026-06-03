[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Sprint Closeout — Smooth-Motion Engine + 3-Cog Integration + IMU Leveling

**Date:** 2026-06-03 · **Build:** 0.1.1 · **Tag:** `smooth-motion-sprint`
**Plan:** [`SMOOTH-MOTION-AND-INTEGRATION-SPRINT-PLAN.md`](SMOOTH-MOTION-AND-INTEGRATION-SPRINT-PLAN.md)
**Tasks:** #3320–#3326 (7 of 7 complete) · **Commits:** `9044a2d` (§1–§6), `ff74fa9` (§7)

> **Audit basis:** the plan, section by section — verified against current code, not the commit
> log. Each commitment is marked SHIPPED with a `file:line` citation.

## Verification status (read first)

**Code-complete and compile-verified; on-hardware behavioral verification PENDING.** The only
automated gate is the `pnut-ts` compile sweep (no behavioral test runner). Every behavior in this
sprint is proven on the bench via
[`SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md`](../SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md),
which **Stephen runs at the bench when ready** — it has not yet been run. Notably, the §4
non-blocking smart-pin ranging path remains **UNPROVEN on hardware** until Exercise 4 passes. Do
not read "SHIPPED" below as "behaviorally verified" — it means "implemented + compiles clean."

## Cross-reference reconciliation

The plan's §1–§7 ↔ #3320–#3326 table reconciles cleanly **both directions**: every numbered
section has a task row and every task maps to a real section. No stale rows; the table was trusted.

## Per-section audit

### §1 — Motion engine core (fixed-rate, eased, blendable) — `«#3320»` ✅ SHIPPED
- Fixed-rate 50 Hz CT-gated frame loop: `FRAME_HZ=50` (`isp_robot_dog.spin2:93`), `motionTask`
  (`:269`) wrap-safe `getct()` deadline, `advanceFrame()` (`:282`).
- Ease-in/out smoothstep `3s²−2s³` fixed-point: `easeFactor()` (`:652`), `lerpFix()` (`:668`),
  `EASE_ONE=4096` (`:94`).
- Body-level state arrays `curX/Y/Z`, `tgtX/Y/Z`, `startX/Y/Z` (leg order FL/BL/FR/BR) (`:149–161`).
- Eased pose lerp `stepPose()` (`:592`); `armMove()` snapshots live start (`:580`) → blending.
- Commit + reachability guard: `commitCur()` (`:612`) → `guardReach()` (`:630`, clamps to
  `REACH_MIN_MM/REACH_MAX_MM = 25/130`, `:97–98`, ported `checkPoint`) → `writeLegs()` (`:622`).

### §2 — Retrofit poses + hello onto the engine (kill snaps) — `«#3321»` ✅ SHIPPED
- `standPose` (`:525`), `relaxPose` (`:531`), `sitPose` (`:537`) now set targets via
  `beginPoseMove()` (`:572`) — eased, not direct writes.
- Hello eases in over `HELLO_LEADIN_FRAMES=8` (`:80`) in `advanceHello()` (`:505–506`); eases back
  in `finishGesture()` (`:516`).
- Low-batt forced relax eases: `applySafetyFloor()` (`:360`) calls `relaxPose()` (eased path).

### §3 — Full gait catalog port — `«#3322»` ✅ SHIPPED
- New CMD enum members `CMD_BACKWARD/TURN_LEFT/TURN_RIGHT/STEP_LEFT/STEP_RIGHT` (`:49`).
- `advanceGait()` dispatcher (`:372`) → `gaitLinearFwd` (`:396`), `gaitSidestep` (`:414`),
  `gaitTurn` (`:432`, X/Z coupled).
- Speed knob: `startGait()` (`:462`) + `setGaitSpeed()` (`:477`), arg0 = deg/frame, 0=default 15,
  clamp 3..45. Mapped onto verified neutral (X=0, Z=±STANCE_LATERAL_MM); Freenove offsets dropped.

### §4 — 3-cog integration + scripted orchestrator — `«#3323»` ✅ SHIPPED
- New top `src/isp_robot_dog_top.spin2`: `cogspin` IO cog first (`:101`), then backend (`:109`).
- Scripted 4-phase concurrency demo `runConcurrentDemo()` (`:123`); telemetry from both mailboxes
  with a `fresh` pingSeq detector (`:177`). End marker `DEMO_DONE`.
- ⚠ Non-blocking `startSmart` ranging path flagged UNPROVEN on hardware (file header + playbook).

### §5 — IMU level measure + static stance trim — `«#3324»` ✅ SHIPPED
- `isp_calibration.spin2`: `stancePitchDeg/stanceRollDeg` (`:60–61`), `stanceTrimDegrees()`
  (`:91`), `stanceTrimY(legIdx)` (`:100`, levers HALF_BODY_LENGTH=136 / WIDTH=76, `:41–42`).
  Trims default 0 until metered on the bench.
- `isp_robot_dog.spin2`: `setLevelStandTargets()` (`:678`) folds the trim into the neutral stand;
  used by `standPose` (`:528`) and `seedStand` (`:563`).
- Measure harness `src/test_level.spin2` (measure → paste → re-measure residual).

### §6 — Documentation (spec + ToOps + README + version) — `«#3325»` ✅ SHIPPED
- New `DOCs/spec/P2-RobotDog-Specifications.md` (house-style, behavioral contract).
- `DOCs/P2_FIRMWARE_THEORY_OF_OPS.md` §6.2 as-built engine added (`:305`); §2 cog-map + §9
  open-items refreshed.
- `src/README.md` §3 updated for engine + catalog + integrated top.
- Version bumped 0.1.0 → 0.1.1 (`src/isp_version.spin2:24–26`).

### §7 — Bench verification playbook — `«#3326»` ✅ SHIPPED
- `DOCs/plans/SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md`: numbered, pass/fail-keyed,
  compile-gate-first, four headless driver flashes + opportunistic low-batt check.
- New production-path driver `src/test_gaits.spin2` (posts all six gaits + speed knob through the
  backend mailbox) — closes the §3 coverage gap where the scripted top only drove FORWARD +
  TURN_LEFT.

## Plan certification

**CERTIFIED — all 7 commitments SHIPPED.** No MISSING/PARTIAL/AMBIGUOUS items; no scope decision
required from Stephen. Behavioral proof is deferred to the bench playbook (above).

## Exit baseline

- **Entry baseline (from plan sprint-start):** GREEN — 36/36 `src/*.spin2` clean (PNut-ts v1.55).
- **Exit baseline (2026-06-03):** GREEN — **39/39** `src/*.spin2` clean, 0 errors, 0 warnings, 0
  skips (compile-all sweep; exit code 0). +3 objects this sprint: `isp_robot_dog_top.spin2`,
  `test_level.spin2`, `test_gaits.spin2`.
- **Comparison:** not worsened — no new failures, no new skips, all prior objects still clean. The
  caveat stands: green compile ≠ on-hardware correctness (the bench playbook owns behavioral proof).

## Carryover

None from this sprint's scope — all sections shipped. Standing/out-of-scope items (unchanged,
tracked elsewhere):

- **Real Wi-Fi/serial command link (cog 0 comms)** — deferred by scope decision #2; the orchestrator
  is a scripted demo, not a live link.
- **Live closed-loop IMU balance** — deferred by scope decision #3; this sprint did static leveling.
- **Stance-trim values** in `isp_calibration` remain **0** pending bench measurement (playbook Ex 2).
- **LED gamma correction** — pre-existing punch-list item, still deferred (no win until a fade/breathing effect).
- Additional gestures (pushups, head-scan) — future motion-catalog work on this engine.

---

## License

MIT License - See [LICENSE](../../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
