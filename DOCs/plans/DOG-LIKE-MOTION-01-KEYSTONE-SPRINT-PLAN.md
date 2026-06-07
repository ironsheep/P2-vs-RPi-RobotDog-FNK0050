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

---

## 1. Single neutral source-of-truth: `neutralFootTarget(idx)` + crouch CONs

**Why.** Neutral is currently re-derived **inline in ~8 places** — `setLevelStandTargets()`
(`isp_robot_dog.spin2:1204-1206`), `leadGaitNeutral()` (729-731), the three gait floors
(639-640, 657-658, 678-679), `advancePushups()` (827/835), HELLO `leanStandFoot()` (815) and
`GST_LEAN_OUT` (797) — each hardcoding `STAND_HEIGHT_MM + cal.stanceTrimY(idx)`, X=0,
Z=±STANCE_LATERAL_MM. Redefining neutral in 8 spots is error-prone; it must become one accessor.

**Current code.** `isp_robot_dog.spin2:73-76` geometry CON block; `setLevelStandTargets()`
at 1195-1206.

**Target.** Add four bench-tunable CONs (after `:76`) and two accessors (near `:1195`):

```
NEUTRAL_FRONT_Y_MM = 95    ' front a touch lower than 99 (elbow/shoulder flex)   -- bench-tune
NEUTRAL_REAR_Y_MM  = 85    ' rear folds deeper (the loaded hindquarter)          -- bench-tune
NEUTRAL_FRONT_X_MM = 0     ' front feet under the shoulders                       -- bench-tune
NEUTRAL_REAR_X_MM  = -12   ' rear feet tucked toward tail (60:40 + femur~90°)     -- bench-tune

PRI neutralFootTarget(idx) : fx, fy, fz | front
    front := (idx & 1) == 0                                   ' FRONT = FL(0), FR(2)
    fx := front ? NEUTRAL_FRONT_X_MM : NEUTRAL_REAR_X_MM
    fy := (front ? NEUTRAL_FRONT_Y_MM : NEUTRAL_REAR_Y_MM) + cal.stanceTrimY(idx)
    fz := (idx < 2) ? STANCE_LATERAL_MM : -STANCE_LATERAL_MM

PRI neutralFootY(idx) : fy                                    ' the per-leg planted floor
    fy := ((idx & 1) == 0) ? NEUTRAL_FRONT_Y_MM : NEUTRAL_REAR_Y_MM
    fy += cal.stanceTrimY(idx)
```

`STAND_HEIGHT_MM=99` is **kept** — it remains the *tall* reference for SIT-front (977-978),
BOW-rear (1005-1006) and PARADE sub-poses, which are deliberate "stand tall," not neutral.

**Starting-value reasoning (bench-tunable).** Smaller Y = more fold; rear ~14 mm lower than
front gives a visibly loaded rear; a 12 mm rear tuck against the 136 mm half-body lever
(`HALF_BODY_LENGTH_MM`) biases load forward without an extreme posture. Exact mm are bench
knobs — the deliverable is the mechanism + sane, clamp-safe starting values + readback (§5).

**Integration.** Route `setLevelStandTargets()` (1204-1206) and `leadGaitNeutral()` (729-731,
all of X/Y/Z) through `neutralFootTarget(idx)` — the rear now eases to `NEUTRAL_REAR_X_MM`,
not literal 0.

**Verification cases.** *Normal:* STAND `dumpState` shows front tgt(0,95,±10), rear
tgt(−12,85,±10). *Edge:* `solveIKdegrees` on all four targets solves without degenerate
guards and lands every servo angle inside the clamps, rear knee `c` tighter than front.
*Error:* a clamp-pegged joint (raise `NEUTRAL_REAR_Y_MM` — less fold — rather than fight the clamp).

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

## 3. Zero the stale leveling trim + re-measure flow

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

## 4. Specification update (changed behavior)

**Why.** `DOCs/spec/P2-RobotDog-Specifications.md` §2.2 "Verified neutral stance" (lines 72-75)
documents the square X=0/Y=99 stance; line 86 ("foot lift clamped to `Y ≤ STAND_HEIGHT_MM`")
and the CON table (line 223) reference it. The keystone changes this behavior, so the spec is a
deliverable.

**Target.** Update §2.2 to describe the loaded-rear-crouch neutral (front/rear split Y, rear −X
load shift, the `neutralFootTarget` source-of-truth), correct the foot-lift-clamp wording to the
**per-leg** floor, and add the four `NEUTRAL_*` CONs to the CON table. Note the 60:40 bias and
the bench pitch decision.

**Verification.** Spec §2.2 matches the shipped CONs and accessor; no remaining reference to a
single `STAND_HEIGHT_MM` neutral floor for gaits.

## 5. Verification playbook (bench — the real gate)

The automated gate is the **compile-all sweep** (`pnut-ts` over `src/*.spin2`). Real
verification is on the P2 bench unit:

1. **IK dry-run (no hardware)** — `test_ik.spin2` pointed at the four neutral targets: all
   solve, servo angles inside clamps, **rear `c` tighter than front**. Gate before any servo moves.
2. **Static stand + readback** — `test_dog_stand.spin2`: STAND dump shows the new targets, no
   clamp pegging, dog visibly stands in a loaded rear crouch; CROUCH/RELAX/SIT still complete.
3. **Leveling re-measure** — `test_dog_level.spin2` with trims zeroed (§3); apply the bench
   pitch decision.
4. **Gaits** — `test_dog_gaits.spin2`: FWD/BACK/TURN L-R/STEP L-R show per-leg floors, X=0
   stride, no lead-in→walk hitch, STOP returns to new neutral.
5. **Gestures** — PUSHUPS bob parallel to new neutral; HELLO frees FR without tipping.

"Still works" = every pose/gait/gesture completes its move, nothing pegs a clamp, STOP/finish
returns to the **new** loaded crouch (not the old square stance).

---

## Files

- `src/isp_robot_dog.spin2` — CONs, two accessors, stand/lead-in/gait/pushup/HELLO routing (§1, §2)
- `src/isp_calibration.spin2` — zero stale stancePitch/Roll (§3)
- `src/isp_leg.spin2` — read-only (`solveIKdegrees` reused; no edit)
- `DOCs/spec/P2-RobotDog-Specifications.md` — §2.2 + CON table (§4)
- `src/test_ik.spin2`, `test_dog_stand.spin2`, `test_dog_level.spin2`, `test_dog_gaits.spin2`
  — verification harnesses (§5); optional `test_ik` dry-run edit

## Open decisions (carried to the bench, not blocking)

- **Pitch intent** — keep the loaded nose-up posture (pitch trim ~0) vs. flatten to IMU-level.
  Decided when Stephen can see it on hardware (§3).
- **Exact crouch magnitudes** — the four `NEUTRAL_*` CONs are starting values; tuned from the
  bench readback (§1, §5).

_No open questions block this plan — code research is complete and the questions pass is empty._
