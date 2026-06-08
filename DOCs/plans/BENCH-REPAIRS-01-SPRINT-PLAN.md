[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Bench Repairs 01 — Panel-Pass Findings (F1–F4)

## Context

A repair mini-sprint for the four findings surfaced by the **2026-06-07 control-panel
certification pass**, recorded in
[`SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md`](SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md)
(Findings section). Each fix lands in the **current singleton-I²C driver state** so the playbook
becomes a *record of the fixes in the current state*; Stephen then **retests only the blocked
exercises** (Ex 2 BOW, Ex 5 paw gestures, Ex 6 LED) on the bench via `test_dog_panel`. The later
**non-singleton I²C cutover is a separate effort** whose second pass just re-confirms nothing changed.

**Scope confirmed with Stephen:** F1, F2, F3, F4 are all **in** (F2 panel readout included — his call,
2026-06-07). **Out:** **D1** (gait-transition smoothing — a future post-keystone design item) and the
**I²C cutover** (its own plan).

**Build / verify model.** No new subsystems; firmware is Spin2 (`pnut-ts`). The only automated gate is
the **compile-all sweep** over `src/*.spin2` (`BUILD_COMMAND`/`TEST_COMMAND`). Real verification is the
**bench retest** of the three blocked exercises through the production mailboxes (`test_dog_panel`,
real 3-cog shape) — never a bespoke path. Bench-tunable magnitudes get **reasoned starting values +
`-- bench-tune` comments** (project convention); all `.spin2` follow `DOCs/policy/SPIN2-AUTHORING-GUIDE.md`.

---

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

## 5. Documentation + retest (close the loop)

**Why.** The fixes change observable behavior; the spec and the playbook record must catch up, and the
blocked exercises must flip green to certify the repair.

**Target.**
- **Spec — `DOCs/spec/P2-RobotDog-Specifications.md`:** note BOW now **raises the head to clear the
  surface**; the LED ring's **default color is WHITE** (color modes render from a fresh boot); the paw
  gestures **rebalance (leaned sit) before lifting FR**. (Light touch — only where these behaviors are
  described.)
- **Playbook —** on Stephen's bench retest, flip **Ex 2 (BOW), Ex 5 (paw gestures), Ex 6 (LED)** to
  pass and mark **F1–F4 resolved** in the Findings table (dated). Re-confirm the compile sweep stays
  green.

**Verification.** Spec matches shipped behavior; the three blocked exercises read pass with the fix
date; no Finding row left open except **D1** (explicitly future). The I²C-cutover second pass later
re-runs the full playbook to confirm none of these regressed.

---

## Files

- `src/isp_robot_dog.spin2` — `BOW_HEAD_UP_DEG` CON + `bowPose` head-raise (§1); `advancePawGesture`
  leaned sit + shared lean-offset helper (§3)
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

_No open questions block this plan — scope confirmed, code research complete, fixes are localized._
