[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Bench Repairs 01 — Panel-Pass Findings (F1–F4) + Retest Refinements (F5–F8)

> **Status 2026-06-08.** **Part A — F1–F4: ✅ DONE, bench-verified 2026-06-08** (panel retest, logs
> `debug_260607-225246` / `230530`; compile sweep 42/42 green). **Part B — F5–F8: the new active
> scope** — refinements found *during* that retest (BOW head-return, post-gesture re-level, HELLO
> foot-depth, battery < 5 V hard-floor). The originating cert plan + playbook are **closed and
> archived** (`archive/2026-06-08-HARDWARE-CERTIFICATION-CLOSEOUT.md`). Ships **0.1.2**.

## Context

A repair sprint for findings surfaced by the **control-panel certification** work. **Part A (F1–F4)**
came from the 2026-06-07 panel pass and is now fixed + bench-verified. **Part B (F5–F8)** came from
the 2026-06-08 retest of those fixes. Each fix lands in the **current singleton-I²C driver state**;
Stephen retests on the bench via `test_dog_panel` (real 3-cog shape, production mailboxes). (The
former "I²C cutover second pass" is gone — the non-singleton I²C is now built only for the **new
voice-recognition bus**, a separate last sprint; bus 1 stays the singleton.)

**Scope:** Part A — F1, F2, F3, F4 (done). Part B — F5, F6, F7, F8 (active). **Out:** **D1**
(gait-transition smoothing — future post-keystone design item).

**Build / verify model.** No new subsystems; firmware is Spin2 (`pnut-ts`). The only automated gate is
the **compile-all sweep** over `src/*.spin2` (`BUILD_COMMAND`/`TEST_COMMAND`). Real verification is the
**bench retest** of the three blocked exercises through the production mailboxes (`test_dog_panel`,
real 3-cog shape) — never a bespoke path. Bench-tunable magnitudes get **reasoned starting values +
`-- bench-tune` comments** (project convention); all `.spin2` follow `DOCs/policy/SPIN2-AUTHORING-GUIDE.md`.

---

# Part A — Panel-pass findings F1–F4 (✅ DONE, bench-verified 2026-06-08)

## 1. F1 — BOW raises the head so the snout clears the surface

**Why.** On the bench, `CMD_BOW` drove the head into the table. The play-bow drops the front chest
but leaves the head where it was, so the snout dips into the surface.

**Current code.** `bowPose()` (`isp_robot_dog.spin2:1000-1007`) sets the four leg targets only (FL/FR
to `BOW_FRONT_HEIGHT_MM=50` `:121`, BL/BR to `STAND_HEIGHT_MM`) then calls **`beginPoseMove(POSE_FRAMES)`**.
`beginPoseMove` (`:1067-1073`) **holds the head**: `tgtHeadDeg := curHeadDeg`. The eased pose loop
(`stepPose`, `:1083-1105`) *will* ease the head when `startHeadDeg <> tgtHeadDeg` and call
`head.panTo` — so the head *can* be eased during a pose; the bow simply never sets a head target.
Head is a **tilt** servo (`isp_head.spin2`: `HEAD_CENTER_DEG=90`, `HEAD_MIN_DEG=50`, `HEAD_MAX_DEG=130`;
`panTo` clamps).

**Target.** Add a bench-tunable CON (near the head CONs, `:147`) and route the bow's head up:
```
BOW_HEAD_UP_DEG = 35   ' tilt the head UP off center during a bow so the snout clears the surface
                       ' -- bench-tune; FLIP THE SIGN if the head tilts toward the table instead
```
In `bowPose()`, after the leg targets, set the head target and arm the move **directly** (not via
`beginPoseMove`, which would re-pin the head to current):
```
tgtHeadDeg := head.HEAD_CENTER_DEG + cal.headTrim() + BOW_HEAD_UP_DEG   ' panTo clamps to 50..130
armMove(POSE_FRAMES)
```
so the head eases up in lock-step with the chest dropping.

**Integration.** Only `bowPose`. The eased head path (`armMove`→`stepPose`) is reused as-is. No change
to `beginPoseMove` (other poses keep holding the head — the project's existing convention).

**Verification.** *Normal:* BOW — snout/head visibly **clears the table**; front-down / rear-up
geometry unchanged; head and chest ease together, no snap. *Edge:* if the tilt goes the wrong way
(snout dips *more*), **flip `BOW_HEAD_UP_DEG` sign** and re-flash — pure bench tune. After `BOW→STAND`
the head **holds raised** until the next head command (existing "poses hold the head" convention) —
flagged as an acceptable follow; do **not** silently make STAND recenter the head (that would drop a
deliberate `CMD_HEAD` look on every stand). *Error:* if the head clamps at `HEAD_MAX_DEG` and still
strikes, the bow front is geometrically too low for this surface — note it; reducing `BOW_FRONT_HEIGHT_MM`
exposure is a separate call, not this fix.

## 2. F3 — LED color modes render (default `currentColor` to a visible color)

**Why.** Stepping the panel's LED button, three of the six modes looked dead. **SOLID / WIPE / CHASE**
paint with `currentColor`, which initializes to **BLACK** and is only ever changed by the
`IO_LED_SOLID` command — and the panel posts **only `IO_LED_MODE`**, so those three render black and
are indistinguishable from OFF. (RAINBOW / RAINBOW_CYCLE self-color via `wheel()`, so they worked.)

**Current code.** `isp_led_ring.spin2:68` `currentColor := strip.BLACK` (in `start()`); the only
writer is `IO_LED_SOLID`→`ring.setColor` (`isp_io_controller.spin2:192`). Color modes:
`fill(currentColor)` `:111`, `setPixelPacked(.., currentColor)` `:114` (WIPE) / `:124` (CHASE).

**Target.** Default `currentColor` to a **visible** color so a mode switch always paints something:
```
currentColor := strip.WHITE            ' was strip.BLACK -- BLACK made SOLID/WIPE/CHASE invisible
```
(`strip.WHITE = $FF_FF_FF`, `isp_ws2812.spin2:65`; `DEFAULT_BRIGHTNESS=64` keeps 7 px tame.) White is
the safe "obviously on" default — a later `IO_LED_SOLID` still overrides it.

**Integration.** One line in `isp_led_ring.start()`. No API change; `IO_LED_SOLID` path untouched.

**Verification.** *Normal:* from a **fresh boot**, stepping the LED button shows six **visibly distinct**
states — OFF (dark) → white SOLID → white WIPE → white CHASE → RAINBOW → RAINBOW_CYCLE → OFF. *Edge:* a
posted `IO_LED_SOLID $RRGGBB` still recolors SOLID/WIPE/CHASE (color override still works). *Error:* none
expected; brightness is non-zero by default, so "renders black" cannot recur from this path.

## 3. F4 — Paw gestures rebalance before lifting the FR paw

**Why.** SHAKE and SALUTE tip the robot toward the lifted front-right paw. They rebalance by **sitting
only** — the sit lowers the CoG *rearward* but never shifts it *laterally*, so removing the FR support
pitches the body forward-right. HELLO does it right (a lateral lean **before** freeing FR); the paw
gestures don't. (Stephen also saw single-arm moves tip generally — so HELLO's lean magnitude is
re-checked here too.)

**Current code.** `advancePawGesture()` `GST_SIT_IN` (`isp_robot_dog.spin2:880-900`) builds a **level**
sit: per-leg `sy` (BL/BR low, FL/FR tall), `X=0`, `Z=±STANCE_LATERAL_MM` — **no lean**. The act
stages then lift FR while FL/BL/BR **hold** that level sit. The rebalance primitive already exists:
`leanStandFoot(idx, freeLeg)` (`:804-816`) returns lean offsets that shift every foot to move the CoG
**away** from `freeLeg` — `LEAN_FWD_MM=8` / `LEAN_LAT_MM=12` (`:115-116`, bench-tunable). HELLO uses it
in its `GST_LEAN_IN` stage (`:761-775`).

**Target.** Make the paw-gesture sit a **leaned sit** — keep the per-leg sit *heights*, but add the
same fore/lateral CoG shift `leanStandFoot(.., FREE_FR_LEG)` produces, so the CoG sits inside the
FL+BL+BR tripod **before** FR lifts:
- In `GST_SIT_IN`, set each foot's sit target to `X = LEAN_FWD_MM` (front-free → feet forward) and
  `Z = ±STANCE_LATERAL_MM + leanLatOffset(idx)` (free-right → feet shift right), keeping `sy` as the
  per-leg sit height. (Factor the X/Z offset out of `leanStandFoot` so the sit reuses the *same* lean
  math, not a copy — keep it DRY.)
- Mirror the offset in `GST_PAW_DOWN`'s FR rest target (`:940`) so FR returns to the **leaned** sit,
  not a level one.
- **Re-tune the lean** against the bench: `LEAN_LAT_MM=12` may be too small (it's what HELLO uses, and
  Stephen saw tipping) — treat the paw-gesture lean as bench-tunable, possibly a larger dedicated
  `PAW_LEAN_LAT_MM`, and confirm HELLO holds too.

**Integration.** `advancePawGesture` (`GST_SIT_IN`, `GST_PAW_DOWN`) + a small shared lean-offset helper
reused by `leanStandFoot`. `finishPawGesture` still holds the (now leaned) sit until a later STAND eases
out — no change needed there.

**Verification.** *Normal:* SHAKE and SALUTE — the body **leans into the FL/BL/BR tripod**, frees FR,
**holds without tipping**, then returns seated; the other three legs stay planted; HELLO frees FR with
no tip. *Edge:* lean still insufficient (tips toward FR) → **increase `LEAN_LAT_MM`/`PAW_LEAN_LAT_MM`**;
over-lean (tips away) → decrease — bench tune. *Error:* the added lean offset must not drive a support
leg into a joint clamp / `guardReach` trip — confirm no clamp peg on the leaned sit (host clamp check
is cheap if needed).

## 4. F2 — Panel LED-mode readout (which mode is active, + index)

**Why.** The panel gives no on-screen feedback for which of the 6 LED modes is active (the button is
only lit/unlit), so the dead-mode confusion in F3 was hard to localize. Add a live readout.

**Current code.** `test_dog_panel.spin2` blits readouts from BMP layers: `showMode()` (`:480-483`)
paints the robot mode name from `dog_modes.bmp` (a 5-name glyph sheet); digits come from
`dog_font.bmp` via `blitGlyph`/`showRight`. Layout boxes are CONs generated by
`tools/gen_dog_panel_assets.py` (which authors `dog_panel_bg.bmp`, `dog_btn_hi.bmp`, `dog_font.bmp`,
`dog_modes.bmp`). The panel already tracks `ledMode` (0..5) and `LED_MODE_COUNT=6`; `stepLed()`
(`:339-349`) is where it changes.

**Target.**
- **`tools/gen_dog_panel_assets.py`:** add an **LED-mode name sheet** (6 names OFF/SOLID/WIPE/CHASE/
  RAINBOW/CYCLE, same glyph-sheet pattern as `dog_modes.bmp`) and a labelled **readout box** in
  `dog_panel_bg.bmp` for it; emit its box/cell CONs. Regenerate the four BMPs.
- **`test_dog_panel.spin2`:** add the generated CONs + a `showLedMode(mode)` that blits the active
  name (and its index digit via the existing `blitGlyph`), called from `stepLed()` and once at
  startup. Add the new BMP as a panel layer if a separate sheet is used.

**Integration.** Panel asset generator + the panel top only — no firmware/runtime change. The readout
reflects panel-side `ledMode`; no new command.

**Verification.** *Normal:* stepping the LED button updates the on-screen readout to the active mode
**name + index**, in step with the ring. *Edge:* wrap 5→0 shows **OFF** and the ring goes dark
together. *Error:* a regenerated-asset / CON mismatch shows as a misaligned or wrong-glyph readout —
caught visually on the first run; regenerate and re-flash.

## 5. Documentation + retest (Part A close-the-loop) — ✅ DONE 2026-06-08

**Why.** The fixes change observable behavior; the spec and the playbook record had to catch up.

**Done.**
- **Spec — `DOCs/spec/P2-RobotDog-Specifications.md`:** ✅ noted BOW **raises the head**, LED ring
  **default WHITE**, paw gestures **rebalance (leaned sit) before lifting FR** (#7a).
- **Playbook —** ✅ on the 2026-06-08 bench retest, **Ex 2 / Ex 5 / Ex 6 flipped to pass** and
  **F1–F4 marked resolved** (dated); the playbook is now **closed + archived** (local-only,
  `archive/2026-06-08-HARDWARE-CERTIFICATION-CLOSEOUT.md`). Compile sweep **42/42 green**.
- **Note:** the retest surfaced four follow-on refinements → **Part B (F5–F8)** below; their docs +
  retest are §10, not here.

---

# Part B — Retest refinements F5–F8 (active, found 2026-06-08)

> Bench prerequisite for all of Part B's motion retests: **charge the battery.** The 2026-06-08 run
> sagged 6.7→5.3 V under load and confounded motion; once F8 lands, a low pack will halt the run.

## 6. F5 — BOW restores the head after standing back up

**Why.** Set head to 60, BOW raised it to ~120 (F1, correct); but `BOW→STAND` left the head at 120
instead of returning to 60. A one-shot trick should leave the head where it started.

**Current code.** `bowPose()` raises the head (`isp_robot_dog.spin2:1026`,
`beginPoseMoveWithHead(POSE_FRAMES, head.HEAD_CENTER_DEG + cal.headTrim() + BOW_HEAD_UP_DEG)`). The
following `standPose()` arms via the head-holding path (`beginPoseMove` → `tgtHeadDeg := curHeadDeg`),
so the head holds at the raised angle. (F1's §1 originally flagged this "hold" as an acceptable
follow — F5 supersedes that.)

**Target.** Snapshot the head angle at bow **entry** (the live `curHeadDeg` before the raise) into a
saved field; on leaving the bow (the next STAND after a BOW), restore the head to the saved angle via
the eased head path rather than holding it raised. Implement as a facet of F6's "restore entry state"
mechanism (shared — see §7), scoped so a deliberate `CMD_HEAD` between bow and stand still wins.

**Verification.** *Normal:* head 60 → BOW (head eases up) → STAND (head eases **back to 60**), in
lock-step with the body. *Edge:* a `CMD_HEAD` posted while bowed overrides the saved restore. *Error:*
none — restore clamps via `panTo` like any head move.

## 7. F6 — One-shot gestures re-level to their entry posture when they finish

**Why.** SALUTE (and the paw gestures generally) **end with the body tilted off-center** — the leaned
sit holds its lean after the paw lowers, so the dog sits crooked. Stephen's call: every one-shot
gesture should ease back to the **leveled posture it started from** when it finishes, rather than
freezing in the gesture's terminal tilt.

**Current code.** `advancePawGesture` `GST_PAW_DOWN` (`isp_robot_dog.spin2:~940`) returns FR to the
**leaned** sit (the F4 mirror) and `finishPawGesture` holds that leaned sit — so the body stays tilted
until a later STAND. The lean offsets come from the shared `leanOffsets(freeLeg, latMag)` helper
(added in F4).

**Target.** At gesture completion, ease the lean back out to a **centered/level** end posture: in
`GST_PAW_DOWN` (or a new final stage) drive all four feet from the leaned sit to the **level** sit
(lean offset → 0), so the gesture ends balanced and centered. Unify with F5 as a single "restore the
entry/neutral state on completion" mechanism (head for BOW, lateral lean for paw gestures). Keep the
ease — no snap.

**Integration.** `advancePawGesture`/`finishPawGesture` + the shared restore mechanism (also serves
F5). HELLO already re-levels on its way out — confirm it still does.

**Verification.** *Normal:* after SHAKE/SALUTE the body eases back to a **level, centered** seated
posture (no residual tilt); BOW restores the head (F5). *Edge:* a command posted mid-gesture still
takes over via the normal blend. *Error:* the re-level must not trip `guardReach` / a joint clamp —
host clamp check is cheap.

## 8. F7 — HELLO wave foot stops dipping into the floor

**Why.** HELLO's lean/lift/CoG is good, but the waving FR foot **hits the floor** at the bottom of the
wave — it shouldn't reach down that far.

**Current code.** `waveY := ly + qsin(HELLO_AMPL_MM, degToUnits(gesturePhase * HELLO_SPEED_DEG), 0)`
(`isp_robot_dog.spin2:783`) centers the wave on `ly` (the lean-stand foot Y = ground level for that
leg), so the down-half of the ±`HELLO_AMPL_MM=30` swing drives the foot ~30 mm **below** ground.

**Target.** Add a **lift bias** so the whole wave floats above the surface — raise the wave center
(`waveY := ly - HELLO_LIFT_MM + qsin(...)`, new bench-tunable `HELLO_LIFT_MM`) and/or trim
`HELLO_AMPL_MM` so even the lowest point of the wave clears the floor. Bench-tune the pair so the wave
is visible but never contacts.

**Verification.** *Normal:* HELLO waves with the FR foot **clearly off the floor** through the whole
wave; lean/CoG unchanged (still no tip). *Edge:* increase `HELLO_LIFT_MM` if it still grazes; reduce
if the wave looks cramped. *Error:* lifting the center must not push the foot past a reach/clamp limit
at the top of the swing — confirm.

## 9. F8 — Battery hard-floor: halt under 5 V (confirm-burst), don't just ease-to-rest

**Why.** The 2026-06-08 pack sagged **6.7→5.3 V under load** and the dog **kept executing gestures**
the whole way down, flopping (`roll=11–13°`) — there wasn't enough power to hold. The current 6.4 V
cutoff only **eases to RELAX as a background advisory; it never refuses a re-commanded motion**, so
motion kept being attempted at 5.3 V.

**Current code.** `LOW_BATTERY_CUTOFF_MV = 6400` (`isp_battery_monitor.spin2:38`); the safety floor
(`senseTask` → `applySafetyFloor`) forces `relaxPose()` once after 3 consecutive `< 6400 mV` reads and
sets `MODE_LOWBATT`, but does not latch a motion-refusing halt. (Minor: a `BATTERY LOW` line currently
prints even **above** 6.4 V — tidy.)

**Target (Stephen's spec).** Add a **hard floor at 5000 mV** distinct from the 6.4 V advisory:
- On **any** read `< 5000 mV`, immediately take **3 confirming reads with a wait (~150 ms)** between
  each (new CONs, e.g. `BATTERY_HALT_MV = 5000`, `BATTERY_HALT_CONFIRMS = 3`, `BATTERY_HALT_WAIT_MS`).
- If **all 3** are `< 5000 mV` → **log `"battery too low"`**, ease to **RELAX**, and **latch a
  refuse-motion HALT** (further motion commands are ignored until reset/power-cycle).
- Keep **6.4 V** as the soft "getting low" advisory above the hard floor; fix the print to fire only
  in-band.

**Integration.** `isp_battery_monitor` (the confirm-burst + threshold) + the backend safety path
(`applySafetyFloor` → latch + refuse motion + the `"battery too low"` log). No frontend change.

**Verification.** *Normal (bench, drained/bench-supply pack):* below 5 V the dog logs `"battery too
low"`, eases to RELAX, and **ignores further move commands**; between 5.0 and 6.4 V it still runs but
logs the advisory. *Edge:* a single sub-5 V inrush sag that recovers on the confirm-burst does **not**
halt (3-of-3 required). *Error:* the halt must ease (not snap) to RELAX; never drop limbs.

## 10. F5–F8 documentation + retest (Part B close-the-loop)

**Target.**
- **Spec —** note the BOW head-return (F5), the gesture re-level (F6), the HELLO foot lift (F7), and
  the new **< 5 V hard-floor halt** behavior (F8) where each is described.
- **Retest —** Stephen bench-retests on a **charged** pack via `test_dog_panel`: BOW head returns,
  SALUTE/SHAKE end level, HELLO foot clears the floor, and (drained/bench-supply pack) the < 5 V halt
  fires with the `"battery too low"` log. Author a **fresh** verification playbook for F5–F8 (the prior
  one is archived) — or fold the steps into closeout. Re-confirm the compile sweep stays green.
- **Closeout —** `sprint-closeout` + `build-wrapup` → stamp/tag **0.1.2**.

**Verification.** Spec matches shipped behavior; each F5–F8 retest passes on the bench (dated); compile
sweep green; sprint closed and 0.1.2 tagged.

---

## Files

- `src/isp_robot_dog.spin2` — `BOW_HEAD_UP_DEG` CON + `bowPose` head-raise (§1); `advancePawGesture`
  leaned sit + shared lean-offset helper (§3); head-restore + gesture re-level (§6, §7); `HELLO_LIFT_MM`
  + wave bias (§8)
- `src/isp_battery_monitor.spin2` — < 5 V hard-floor confirm-burst + halt-latch CONs (§9)
- `src/isp_led_ring.spin2` — default `currentColor` to `strip.WHITE` (§2)
- `tools/gen_dog_panel_assets.py` + `src/test_dog_panel.spin2` — LED-mode readout (§4)
- `DOCs/spec/P2-RobotDog-Specifications.md` — behavior backport (§5)
- `DOCs/plans/SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md` — retest flip (§5, at bench)

## Process notes (not silently skipped)

- **Version bump** (`src/isp_version.spin2`) and entry **baseline-health** are set/run by `sprint-start`,
  not here.
- **Retest is on the P2 bench** (`test_dog_panel`, Load ON, ~1 kΩ series R into P9, 2 Mbaud, robot
  supported). The container gate is the compile sweep only.

## Sprint-start record — 2026-06-08

- **Build version:** ships as **0.1.2** (from 0.1.1) — agreed 2026-06-08; repairs fold into the
  certified functional baseline. `FW_VERSION_*` (`src/isp_version.spin2`) is stamped at
  closeout/`build-wrapup`, not now.
- **Working-tree audit:** clean — only this plan doc was untracked (committed as the sprint
  foundation); **no uncommitted edits** to any source the sprint touches (`isp_robot_dog`,
  `isp_led_ring`, `test_dog_panel`, `gen_dog_panel_assets.py`).
- **Tracking-readiness (entry):** **READY** — todo-mcp tasks 0, context 0 keys (container rebuilt
  this session), `MEMORY.md` current. No leftovers to fold in.
- **Baseline-health (entry):** **GREEN** — compile-all sweep **42/42 objects, 0 warnings, 0
  failures** (pnut-ts; the project's only automated gate). No behavioral suite — real verification is
  the bench retest. This is the entry baseline `sprint-closeout` asserts the exit baseline against.

## Out of scope (explicit)

- **D1** — gait-transition smoothing (phase-0 / planted-boundary gait switch). Future **post-keystone**
  Dog-Like Motion step; it touches the per-leg neutral keystone changes.
- **Non-singleton I²C cutover** — separate plan; this repair batch lands in the current singleton state.

## Section ↔ task cross-reference

**Part A (✅ done + bench-verified 2026-06-08):**

| Plan § | Deliverable | Task | seq |
| ------ | ----------- | ---- | --- |
| §2 | F3 — LED default color (color modes render) | «#3» ✅ | 1 |
| §1 | F1 — BOW raises the head to clear the surface | «#4» ✅ | 2 |
| §3 | F4 — paw-gesture rebalance (leaned sit) | «#5» ✅ | 3 |
| §4 | F2 — panel LED-mode readout | «#6» ✅ | 4 |
| §5 | Docs backport + Part A retest flip | «#7» ✅ | 5 |

**Part B (active — tasks created at `plan-to-tasks`):**

| Plan § | Deliverable | Task | seq |
| ------ | ----------- | ---- | --- |
| §6 | F5 — BOW restores the head after standing | TBD | 6 |
| §7 | F6 — gestures re-level to entry posture | TBD | 7 |
| §8 | F7 — HELLO wave foot clears the floor | TBD | 8 |
| §9 | F8 — battery < 5 V hard-floor halt | TBD | 9 |
| §10 | F5–F8 docs + retest + 0.1.2 closeout | TBD | 10 |

Sprint tag: `bench-repairs-01`.

_Part A done + bench-verified; Part B scope confirmed with Stephen 2026-06-08, fixes localized (file:line above). No open questions block Part B._
