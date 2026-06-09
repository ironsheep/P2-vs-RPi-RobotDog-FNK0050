# Dog-Like Motion — Sprint 01: ★ Keystone (Loaded Rear Crouch)

## Context

Step 1 (the ★ Keystone) of the committed 10-step order in `DOCs/DOG-LIKE-MOTION-STUDY.md`
§6. The neutral STAND is the foundation **both poses and gaits build from** — gaits
oscillate around it, poses ease to/from it, the leveling trim is measured against it.
Today neutral is square straight legs (`isp_robot_dog.spin2:74` `STAND_HEIGHT_MM=99`, all
four feet X=0, Y=99, Z=±10). The study (sourced dog biomechanics) wants a **loaded rear
crouch**: front a touch flexed, rear folded deeper (target ~30° stifle/hock off vertical,
femur ~90° to pelvis), **60:40 front/rear weight bias** via rear feet tucked toward the
tail. *One change improves everything downstream.* The stale `stancePitch/Roll` trim
(measured against the old square stance + old servo map) is re-measured here.

**Scope confirmed with Stephen:** full keystone **including the rear −X load-shift**; the
nose-up pitch the front/rear fold creates is a **bench decision** (keep the loaded look vs.
flatten to IMU-level) — the plan documents both; no auto re-measure silently undoes it.

**Cadence (firm):** this is a *buildable increment* — mechanism + reasoned, clearly
bench-tunable starting numbers + a joint-angle readback. Stephen bench-tests; numbers and
trim are tuned from that feedback; then Step 2 is planned.

**Engine facts (source-verified, this sprint builds on them):** motion engine is
foot-Cartesian — targets are foot (X,Y,Z) mm per leg → `isp_leg.moveToXYZ()` → CORDIC IK →
servo. **+X = forward (nose)**, shared body frame, no per-leg X mirror. **Smaller Y =
lower/more-folded.** Index FL=0, BL=1, FR=2, BR=3; FRONT={0,2}, REAR={1,3}, LEFT=idx<2.
`isp_leg.solveIKdegrees(fx,fy,fz):a,b,c` is a no-servo IK dry-run (IK-frame degrees, before
the side mirror); per-joint drivable clamps coxa 65..170 / femur 10..170 / tibia 20..170.

**Mechanical constraint (fixed spine — shapes the whole arc).** The robot has a rigid chassis:
the shoulder and hip girdles are fixed relative to each other (`HALF_BODY_LENGTH_MM` is a
**constant, not a state variable**) and there is **no spinal DOF** (13 servos = 12 leg joints +
head pan). A real dog produces a loaded-rear crouch with leg fold *and* lumbar flexion; we
synthesize **all** of it from leg geometry — foot (X,Y,Z) + joint angles are the only levers.
Three consequences: **(1)** FRONT and REAR neutral are tuned **independently** — there is no
coupling DOF between the girdles, so §1's front/rear decomposition is exactly the right model, not
a shortcut. **(2)** The rear leg joints carry the spine's share of the fold, so they sit **closer
to their clamps** than a dog's hindlimb — the §3 clamp-safety gate matters *more*, and the rear
starting numbers are deliberately conservative. **(3)** Gallop spring, bound back-arch, and spinal
stretch/extension (a true beg) are permanently out of reach and **out of scope for the entire
Dog-Like Motion arc**, not just Step 1 — we approximate *static* posture and weight bias, never the
spinal dynamics.

**Testability note (host vs. hardware).** Two tiers exist. (1) **Container, no P2:** the
only automated gate is the compile-all sweep (`pnut-ts` over `src/*.spin2`). (2) **Bare P2,
no robot peripherals:** the `test_*.spin2` dry-run harnesses run headless over serial
(`pnut-term-ts ... -b 2000000 --headless --end-marker "TEST_DONE"`) — *pure math, no
servos / no I2C / no IMU / no actuator power* (`test_ik.spin2` is the existing example).
§3 below expands tier 2 into a **self-checking** geometry harness so the new crouch's
clamp-safety is proven in math before any servo strains on the bench. This honours
[[production-path-testing]] — the harness exercises the **real** engine math, not a copy.

**Entry prerequisites (sequenced before execution — not in this plan's scope).** Keystone
executes after bench certification is **functional-green** on the P2 unit (achieved: BENCH-REPAIRS-01
closed, 0.1.2 tagged, F1–F8 bench-verified). **No I2C cutover precedes this sprint.** Per the
2026-06-08 sequencing decision, **bus 1 stays the DAT singleton** (PCA9685/ADS7830/MPU6050, backend
cog) and is **never migrated**; the non-singleton/var-owner I2C driver is built only for the **new
voice bus** in the voice-recognition sprint (sequenced **last**). The §3 harness and all object
construction therefore target the **current singleton** driver — there is no infra swap stacked under
this behaviour change. See memory [[voice-integration-design]] and [[project-status]].

---

## 1. Single neutral source-of-truth: `neutralFootTarget(idx)` + crouch CONs

**Why.** Neutral is currently re-derived **inline in ~8 places** — `setLevelStandTargets()`
(`isp_robot_dog.spin2:1204-1206`), `leadGaitNeutral()` (729-731), the three gait floors
(639-640, 657-658, 678-679), `advancePushups()` (827/835), HELLO `leanStandFoot()` (815) and
`GST_LEAN_OUT` (797) — each hardcoding `STAND_HEIGHT_MM + cal.stanceTrimY(idx)`, X=0,
Z=±STANCE_LATERAL_MM. Redefining neutral in 8 spots is error-prone; it must become one accessor.

**Current code.** `isp_robot_dog.spin2:73-76` geometry CON block; `setLevelStandTargets()`
at 1195-1206.

**Target.** Add four bench-tunable CONs (after `:76`) and two accessors (near `:1195`). The
accessors are **`PUB`** (not `PRI`) and **`start()`-independent** — they read CON + committed
DAT (`cal.stanceTrimY`) only — so the §3 harness can call them without bringing up the
backend. That start()-independence is a maintenance invariant; note it in the method comment.

```
NEUTRAL_FRONT_Y_MM = 95    ' front a touch lower than 99 (elbow/shoulder flex)   -- bench-tune
NEUTRAL_REAR_Y_MM  = 85    ' rear folds deeper (the loaded hindquarter)          -- bench-tune
NEUTRAL_FRONT_X_MM = 0     ' front feet under the shoulders                       -- bench-tune
NEUTRAL_REAR_X_MM  = -12   ' rear feet tucked toward tail (60:40 + femur~90°)     -- bench-tune

PUB neutralFootTarget(idx) : fx, fy, fz | front
    front := (idx & 1) == 0                                   ' FRONT = FL(0), FR(2)
    fx := front ? NEUTRAL_FRONT_X_MM : NEUTRAL_REAR_X_MM
    fy := (front ? NEUTRAL_FRONT_Y_MM : NEUTRAL_REAR_Y_MM) + cal.stanceTrimY(idx)
    fz := (idx < 2) ? STANCE_LATERAL_MM : -STANCE_LATERAL_MM

PUB neutralFootY(idx) : fy                                    ' the per-leg planted floor
    fy := ((idx & 1) == 0) ? NEUTRAL_FRONT_Y_MM : NEUTRAL_REAR_Y_MM
    fy += cal.stanceTrimY(idx)
```

`STAND_HEIGHT_MM=99` is **kept** — it remains the *tall* reference for SIT-front (977-978),
BOW-rear (1005-1006) and PARADE sub-poses, which are deliberate "stand tall," not neutral.

**Starting-value reasoning (bench-tunable).** Smaller Y = more fold; rear ~14 mm lower than
front gives a visibly loaded rear; a 12 mm rear tuck against the 136 mm half-body lever
(`HALF_BODY_LENGTH_MM`) biases load forward without an extreme posture. Exact mm are bench
knobs — the deliverable is the mechanism + sane, clamp-safe starting values + readback (§3, §7).
Because the spine is rigid (Engine facts above), the rear −X tuck and the rear-Y fold are
**coupled through the body**: lowering the rear pitches the nose up (which *alone* shifts weight
rearward), and the −X tuck is what restores the **60:40 *front* bias** — so the two are bench-tuned
**as a pair**, watching pitch and bias together, not one knob at a time. (Terminology: "loaded
rear" = the hindquarters *coiled/folded*; the 60:40 is the natural head-forward *static* front
load — the two are not in tension.)

**Integration.** Route `setLevelStandTargets()` (1204-1206) and `leadGaitNeutral()` (729-731,
all of X/Y/Z) through `neutralFootTarget(idx)` — the rear now eases to `NEUTRAL_REAR_X_MM`,
not literal 0.

**Verification cases.** *Normal:* STAND `dumpState` shows front tgt(0,95,±10), rear
tgt(−12,85,±10). *Edge:* §3 harness proves all four targets solve, every servo angle inside
the clamps, rear knee `c` tighter than front. *Error:* a clamp-pegged joint (raise
`NEUTRAL_REAR_Y_MM` — less fold — rather than fight the clamp). *Regression:* the stand-tall
sub-poses SIT/BOW/PARADE still read off `STAND_HEIGHT_MM=99`, not the new neutral.

## 2. Per-leg gait planted-Y floor + dependent oscillators

**Why.** Gait diagonal pairs **mix front+rear** — pair A = {FL(0,front), BR(3,rear)}, pair B
= {BL(1,rear), FR(2,front)} (`isp_robot_dog.spin2:641-644`). Today each pair shares one
`footYA/footYB` floor clamped `<# STAND_HEIGHT_MM`. With front≠rear neutral height the floor
**must split per leg**, or the gait flattens the crouch.

**Current code.** `gaitLinearFwd` (637-644), `gaitSidestep` (655-662), `gaitTurn` (676-683):
`footYx := (STAND_HEIGHT_MM + qsin(lift,units)) <# STAND_HEIGHT_MM`. `advancePushups()` bob
(835): `y := STAND_HEIGHT_MM - dip`.

**Target.** In all three gaits, compute the planted floor **per foot** via `neutralFootY(idx)`,
e.g. `setCur(0, strideXA, (neutralFootY(0)+qsin(...)) <# neutralFootY(0), +lat)` and likewise
for 3/1/2 — splitting the shared `footYA/footYB`. **Stride X stays centered on 0** (deliberate:
the rear −X load offset is a *static-neutral* property; the walking trajectory is the
Freenove-faithful X=0-centred stride). Add a comment recording that decision so it is not
"fixed" later as a bug. `advancePushups()` dips each leg off its own `neutralFootY(idx)` (and
uses per-leg neutral X) so the bob stays parallel to the new stance.

**Integration.** Also re-base HELLO `leanStandFoot()` (814-816) and `GST_LEAN_OUT` (796-798)
on `neutralFootTarget`/`neutralFootY` so the rebalance tracks the new CoG. `seedStand()` /
soft-seed power-on path uses its own SEED/RELAX heights — **untouched** (safety path preserved).

**Verification cases.** *Normal:* mid-gait `dumpState` shows front floors ~95, rear ~85,
stride X centred on 0; STOP eases to the new neutral. *Edge:* gait-start transition (lead-in
eases to rear-tucked, first walking frame re-centres stride to X=0) shows **no visible hitch**
— `NEUTRAL_REAR_X_MM` kept small for pass 1; if a hitch appears, decouple the *gait* lead-in
to X=0. *Error:* `guardReach()` (REACH_MIN 25 / MAX 130) never trips — deeper crouch shortens
reach (moves away from MAX); confirm the rear −X foot stays above REACH_MIN.

## 3. Host-side dry-run testability — `solveServoDegrees` + self-checking harness

**Why.** The new crouch must be proven **clamp-safe without moving servos**. Today the
mirror+trim+clamp lives inside `setJointAngles()` (`isp_leg.spin2:134-169`), which *writes
hardware in the same method* — so the full foot-XYZ→servo-angle pipeline cannot run on a
bare P2. `test_ik.spin2` only prints raw IK-frame angles. This section closes that gap and
turns the dry-run into a self-asserting test.

**Current code.** `setJointAngles()` fuses mirror/trim/clamp + servo writes (147-169);
`solveIKdegrees()` is the pure IK (no mirror); `test_ik.spin2` is the existing pure-math harness.

**Target.**
- **Extract** `PRI ikToServo(coxaIK, femurIK, tibiaIK) : cS, fS, tS` in `isp_leg` — the
  mirror + trim + clamp math, **no writes** — and refactor `setJointAngles()` to call it then
  write (behaviour-preserving, DRY).
- **Add** `PUB solveServoDegrees(footX, footY, footZ) : cS, fS, tS` = `solveIKdegrees` +
  `ikToServo`, **no hardware writes** — the whole pipeline as a pure function.
- **New harness `src/test_keystone_geometry.spin2`** (pure math, no servos/I2C/IMU/power).
  For each leg idx 0..3: read the **real** `dog.neutralFootTarget(idx)` (object instantiated
  *without* `start()`), run `leg.solveServoDegrees(x,y,z)` for that leg's side, print foot
  XYZ + IK `a/b/c` + servo `c/f/t`, and **self-assert PASS/FAIL**:
  - every servo angle strictly *inside* its clamp (not pegged) — clamp-safety gate,
  - rear knee more flexed than front (the loaded-crouch conformation),
  - rear-X load shift present (rear X < front X).
  Also dump `neutralFootY(idx)` at a few gait phase points (the per-leg planted floor).
  End with a single `PASS`/`FAIL` summary + `TEST_DONE` end-marker (headless convention,
  [[headless-debug-baud]]).
- **Update `test_ik.spin2`** to point its `showIK` calls at the four new neutral targets and
  correct its "Expected neutral [0,99,10] … a~84 b~-46 c~92" header comment.

**Verification cases.** *Normal:* harness prints `PASS` for all four legs on a bare P2.
*Edge:* a too-deep starting `NEUTRAL_REAR_Y_MM` makes a joint peg → harness prints `FAIL`
with the offending joint, caught in math (no servo strain). *Error:* `solveServoDegrees`
output equals the live `getServoAngles()` after a real `moveToXYZ` to the same target —
confirms the pure path and the production path agree.

## 4. Zero the stale leveling trim + re-measure flow

**Why.** `stancePitchDeg=-3`, `stanceRollDeg=+2` (`isp_calibration.spin2:88-93`) were measured
against the old square stance + old servo map → invalid for the new geometry.

**Target.** Set both to `0` (update comments → "re-measure against loaded-rear neutral
2026-06-07"). With both 0, `stanceTrimY()` returns 0 → `neutralFootTarget` yields the raw new
geometry — exactly what `test_dog_level.spin2` must measure.

**Integration / flow (unchanged harness).** `test_dog_level.spin2` does
CROUCH→STAND→avg-32-IMU-samples→prints pitch/roll, and measures whatever the *current* neutral
is — so it picks up the new crouch automatically. Bench loop: run with trims 0 → read raw tilt
→ **bench decision** (keep loaded nose-up = leave pitch near 0; vs. flatten = paste the measured
pitch/roll) → rebuild → re-run → residual → expected target.

**Verification cases.** *Normal:* `reportStoredTrim` echoes 0/0 and labels the measure "RAW
un-leveled tilt." *Edge:* the intended nose-up pitch appears in the first measurement — that is
expected, not a defect. *Error:* roll should be near-symmetric; a large unexpected roll means a
per-leg trim/servo regression to chase before pasting.

## 5. Documentation backport (all code-state docs that describe the stance/motion model)

**Why.** Several documents describe the neutral stance / gait-Y model as it stands today; the
keystone changes that behaviour, so keeping them current is a sprint deliverable, not an
afterthought.

**Target — update each to the loaded-rear-crouch / per-leg-floor / `neutralFootTarget` model:**
- **`DOCs/spec/P2-RobotDog-Specifications.md`** — §2.2 "Verified neutral stance" (72-75),
  the foot-lift-clamp wording (86, now *per-leg* floor), and the CON table (223): add the
  four `NEUTRAL_*` CONs, note the 60:40 bias and the bench pitch decision.
- **`DOCs/P2_FIRMWARE_THEORY_OF_OPS.md`** — the gait `Y=6·sin(phase)+height` + foot-lift-clamp
  description (≈284) and the "ease/hold neutral stance" narrative (≈218-227): describe the
  per-leg planted floor and the single `neutralFootTarget` source-of-truth.
- **`src/README.md`** — the firmware-architecture doc the ToO defers to (§3); backport the
  neutral-stance + gait-floor description.
- **`DOCs/plans/SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md`** — (a) the cited committed
  trim `-3/+2` (163-164, 180) goes stale → note it is being re-measured (final values land at
  closeout); (b) add a **Keystone loaded-crouch** exercise housing the §7 bench steps + the §3
  host dry-run gate. (Authored via the `test-playbook` skill at execution.)
- **In-code doc comments** — `test_ik.spin2` header expected-values (done in §3) and any
  `isp_robot_dog` neutral-related method doc-comments.

*Intentionally NOT backported:* `DOCs/DOG-LIKE-MOTION-STUDY.md` — it is the rationale/source,
not a code-state-of-record (its §6 step-1 is marked done at sprint closeout, not here).

**Verification.** Each doc matches the shipped CONs/accessor; no remaining reference to a
single `STAND_HEIGHT_MM` neutral floor for gaits.

## 6. Coding-style audit (gate on every modified object)

**Why.** All code modifications are audited against project style. There is no separate Spin2
style *doc*; the authority is established in-code idiom + p2kb-mcp + a review pass.

**Target.** New CONs, accessors, `ikToServo`/`solveServoDegrees`, and the harness must match
the surrounding idiom: `''` public / `'` internal doc comments with `@param`/`@local`/
`@returns`, `{Spin2_Doc_CON}` markers, `ALL_CAPS_MM` CON naming, camelCase methods, the
existing clamp/`#>`/`<#` style. Use **p2kb-mcp** (`p2kb_get`) for any unfamiliar Spin2/PASM2
construct rather than guessing (per CLAUDE.md). Run a **`/code-review` pass on the final
diff** as the gate before the build is considered done.

**Verification.** `/code-review` returns no style/correctness findings on the diff; doc-comment
blocks present on every new `PUB`/`PRI`.

## 7. Verification playbook (bench — the real gate)

The automated gate is the **compile-all sweep** (`pnut-ts` over `src/*.spin2`). Real
verification is on the P2 bench unit:

1. **Host dry-run (no robot)** — `test_keystone_geometry.spin2` (§3) + `test_ik.spin2`:
   `PASS` for all four legs, servo angles inside clamps, rear `c` tighter than front. *Gate
   before any servo moves.*
2. **Static stand + readback** — `test_dog_stand.spin2`: STAND dump shows the new targets, no
   clamp pegging, dog visibly stands in a loaded rear crouch; CROUCH/RELAX/SIT still complete.
3. **Leveling re-measure** — `test_dog_level.spin2` with trims zeroed (§4); apply the bench
   pitch decision.
4. **Gaits** — `test_dog_gaits.spin2`: FWD/BACK/TURN L-R/STEP L-R show per-leg floors, X=0
   stride, no lead-in→walk hitch, STOP returns to new neutral.
5. **Gestures** — PUSHUPS bob parallel to new neutral; HELLO frees FR without tipping.

"Still works" = every pose/gait/gesture completes its move, nothing pegs a clamp, STOP/finish
returns to the **new** loaded crouch (not the old square stance).

---

## Files

- `src/isp_robot_dog.spin2` — CONs, two PUB accessors, stand/lead-in/gait/pushup/HELLO routing (§1, §2)
- `src/isp_leg.spin2` — `ikToServo` extraction + `solveServoDegrees` (§3); `setJointAngles` refactor
- `src/isp_calibration.spin2` — zero stale stancePitch/Roll (§4)
- `src/test_keystone_geometry.spin2` — **new** self-checking host dry-run harness (§3)
- `src/test_ik.spin2` — retarget to new neutral + fix header (§3)
- `DOCs/spec/P2-RobotDog-Specifications.md`, `DOCs/P2_FIRMWARE_THEORY_OF_OPS.md`,
  `src/README.md`, `DOCs/plans/SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md` — doc backport (§5)
- Bench harnesses `test_dog_stand/level/gaits.spin2` — verification (§7)

## Process notes (not silently skipped)
- **Build version: `0.2.0`** — agreed at `sprint-start` 2026-06-09 (MINOR bump from 0.1.2:
  new loaded-rear-crouch neutral, opens the Dog-Like-Motion arc). Set in `src/isp_version.spin2`.
- **Release notes** (`DOCs/RELEASE-NOTES.md`) are authored by `build-wrapup` at closeout.

## Entry checks (sprint-start 2026-06-09)

- **Working tree:** clean; `src/` fully committed (HEAD `7583c95`). Only sprint-start's own
  edits pending (this plan + version bump) — committed as the sprint-start foundation commit.
- **Tracking-readiness:** **READY.** Task board empty; context = 1 live key
  (`sprint_resume_keystone_next`, the current resume pointer); `MEMORY.md` ~8 lines; no drift,
  nothing to prune.
- **Entry baseline (baseline-health):** compile-all sweep over `src/*.spin2` — **42/42 green, 0
  fail** (matches the 0.1.2 closeout baseline; version bump is an edit, not a new file). No failures
  to triage. This is the exit baseline `sprint-closeout` checks against; no regression permitted at
  closeout. New §3 harness `test_keystone_geometry.spin2` will raise the count to 43 when added.

## Open decisions (carried to the bench, not blocking)

- **Pitch intent** — keep the loaded nose-up posture (pitch trim ~0) vs. flatten to IMU-level.
  Decided when Stephen can see it on hardware (§4).
- **Exact crouch magnitudes** — the four `NEUTRAL_*` CONs are starting values; tuned from the
  §3 readback (§1, §7).

_No open questions block this plan — code research is complete and the questions pass is empty._
