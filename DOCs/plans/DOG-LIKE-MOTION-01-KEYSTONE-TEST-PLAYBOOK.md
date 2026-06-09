# DOG-LIKE-MOTION-01 Keystone — Bench Verification Playbook

**Build:** 0.2.0 · **Targets:** 1 P2 bench unit (full 3-cog shape), all 13 servos, IMU, battery,
Load ON — plus the host (no robot) for Exercise 1. **Est. run time:** ~45–60 min.

This is the on-hardware proof for the **loaded-rear-crouch keystone** (sprint DOG-LIKE-MOTION-01,
§7 `«#19»`). It does two jobs, and each exercise is tagged so you know which you're doing:

- **[CERT]** — *certify the regression baseline*: the pose/gait/gesture you already trusted still
  completes its move, eases cleanly, and nothing pegs a clamp after the refactor.
- **[NEW]** — *verify the new keystone characteristic*: the dog now rests and walks in a
  **loaded-rear crouch**, and gaits keep the front/rear height split while walking.

> Most exercises are **both** — the same run certifies the old behavior *and* shows you the new
> stance. Read the **OBSERVE** line for what to look at and the **PASS TELL** line for the one thing
> that says "good."

---

## The visual signature — what should look DIFFERENT this build

Before you run anything, here is the change you are looking for with your eyes:

- **At rest (STAND), the dog now sits in a loaded-rear crouch, not a square box.** The
  **hindquarters are visibly lower and tucked slightly back toward the tail**; the front stands a
  touch taller. Weight is biased **~60:40 forward**. The body line should read a little **nose-up**.
  (Front feet ≈ 95 mm extension at X=0; rear feet ≈ 85 mm and tucked back ≈ 12 mm.)
- **The old build stood all four feet at one height (99 mm), square.** If the dog stands flat and
  level like a table, that's the OLD stance — a fail.
- **While walking, the rear stays lower than the front.** The gait does **not** flatten the crouch
  out to a level square stance mid-stride.
- **Every transition still eases** (no snap), and **STOP / finish returns to the loaded crouch**, not
  to the old square stance.

---

## Driver map & end-markers

| Exercise | Driver | End-marker | Timeout | Robot? |
|----------|--------|------------|---------|--------|
| 0 Automated gate | `BUILD_COMMAND` (compile sweep) | — | — | no |
| 1 Host geometry gate | `test_keystone_geometry.spin2`, `test_ik.spin2` | `TEST_DONE` | 15 | **no (host)** |
| 2 Stand + poses | `test_dog_stand.spin2` | `STAND_DONE` | 75 | yes |
| 3 Leveling re-measure | `test_dog_level.spin2` | `LEVEL_DONE` | 80 | yes |
| 4 Gaits | `test_dog_gaits.spin2` | `GAITS_DONE` | 130 | yes |
| 5 Paw tricks | `test_dog_tricks.spin2` | `TRICKS_DONE` | 90 | yes |
| 6 Gestures HELLO + PUSHUPS | `test_dog_panel.spin2` (interactive) | — | — | yes |
| 7 Full concurrency | `isp_robot_dog_top.spin2` | (demo) | — | yes |

Flash/run pattern (all P2 comms at **2 Mbaud**):

```bash
pnut-ts -d -q src/<driver>.spin2
pnut-term-ts -r src/<driver>.bin -b 2000000 --headless --end-marker "<MARKER>" --timeout <N>
```

> `-b 2000000` is required — headless mode opens 115200 for the *download* but won't apply the debug
> baud to the *runtime* read, so 2 Mbaud `DEBUG` comes back as garbage without it. Logs land in `logs/`.

> **Safety, every robot exercise:** **lift/support the robot** during gyro-cal and the first stand
> transition (servos move). For leveling (Ex 3) and stance checks, then **set it down on a known-level
> surface** before you read tilt or judge the stance. Use a **healthy pack** — a sagging pack makes
> tilt unrepeatable and can trip the low-battery floor mid-run.

---

## Exercise 0 — Automated gate: compile sweep *(run first)* [CERT]

- **Verifies:** the only in-container automated gate — every `.spin2` object compiles under PNut-ts.
  Nothing below is worth a person's time until this is green.
- **Targets:** host, no robot.
- **Action:** from the repo root, run the compile sweep (`BUILD_COMMAND`):
  ```bash
  for f in src/*.spin2; do pnut-ts -q "$f" || echo "FAIL: $f"; done; rm -f src/*.bin
  ```
- **Expected / PASS TELL:** **no `FAIL:` line** — every object compiles. (Recorded green this build:
  **43/43**.)
- **Pass/fail:** `[ ]`  ___ / 43 compile · any FAIL? ______

---

## Exercise 1 — Host geometry GATE (no servos, run before any robot step) [NEW]

- **Verifies:** §3 `«#14»` — the new loaded-rear crouch is **clamp-safe in math** before any servo
  ever moves. This is the gate: if it fails, **do not flash the robot** — a too-deep rear fold would
  strain a joint on the bench.
- **Targets:** host only, no robot.
- **Action:**
  1. `pnut-ts -d -q src/test_keystone_geometry.spin2` → run headless, end-marker `TEST_DONE`.
  2. `pnut-ts -d -q src/test_ik.spin2` → run headless, end-marker `TEST_DONE`.
- **OBSERVE (console):**
  - Per-leg lines `leg N XYZ(x,y,z) IK a/b/c servo coxa/femur/tibia` — front legs show **Y≈95, X=0**;
    rear legs show **Y≈85, X=−12**.
  - The conformation block: `ok rear knee … > front …` (rear knee more flexed) and
    `ok rear tuck … < front …` (rear foot tucked back) for both body sides.
  - `test_ik`: FRONT `[0,95,10]` ≈ a 84 / b −49 / c 98; REAR `[-12,85,10]` ≈ c 109 (rear knee deeper).
- **PASS TELL:** the harness prints **`RESULT: PASS (all four legs clamp-safe; loaded-rear
  conformation holds)`**. Every servo angle is strictly **inside** its clamp (coxa 65–170,
  femur 10–170, tibia 20–170) — none pegged.
- **If FAIL:** read which joint/leg pegged; the rear Y (85) or rear X (−12) likely needs easing in
  `isp_robot_dog.spin2` `NEUTRAL_*`. Fix and re-run before touching the robot.
- **Pass/fail:** `[ ]`  `RESULT: PASS`? ______ · any joint pegged? ______

---

## Exercise 2 — Static stand + poses: see the loaded crouch, certify the pose set [NEW]+[CERT]

- **Verifies:** §1 `«#13»` (the new neutral lands on the robot) + regression of CROUCH/STAND/RELAX/
  SIT/head. **Depends on Ex 1 passing.**
- **Targets:** 1 bench unit, full 3-cog shape, all 13 servos.
- **Driver:** `test_dog_stand.spin2` → `STAND_DONE` (timeout 75). Posts, in order:
  power-on glide → `CMD_CROUCH` → `CMD_STAND` → `CMD_RELAX` → `CMD_STAND` → `CMD_SIT` → `CMD_STAND`
  → head 60 / 120 / 90.
- **Setup:** support during gyro-cal + first rise; then set down level to judge the stand.
- **OBSERVE:**
  - **[NEW] The STAND pose is a loaded-rear crouch** — hindquarters lower and tucked back, front
    taller, body slightly nose-up (see "visual signature" above). The console `dumpState` after STAND
    shows **front tgt ≈ (0, 95, ±10)** and **rear tgt ≈ (−12, 85, ±10)**.
  - **[CERT]** Each transition eases in/out, no snap; CROUCH is low & symmetric; RELAX tucks; SIT
    drops the rear; head pans smoothly to each angle.
- **PASS TELL:**
  - **[NEW]** rear sits visibly lower/tucked than front (not a flat square) **and** the dump shows the
    asymmetric targets above — **no clamp pegging** reported.
  - **[CERT]** every posted pose completes and returns; `STAND_DONE` prints.
- **Pass/fail:** `[ ]`  loaded-rear crouch visible? ______ · dump targets 95/85, X 0/−12? ______ ·
  CROUCH/RELAX/SIT/head all eased & complete? ______

---

## Exercise 3 — IMU static leveling: roll-sign check + re-measure [NEW]

- **Verifies:** §4 `«#16»` — with the leveling trims **zeroed** (this build), measure the RAW tilt of
  the new crouch and make the bench pitch decision. **This is where the open bench decisions get
  recorded for closeout.** Depends on Ex 1 (crouch proven) + a clean Ex 2 stand.
- **Targets:** 1 bench unit, full 3-cog shape, IMU, battery.
- **STEP A — verify the IMU lateral-roll SIGN first (carryover from BENCH-REPAIRS-01):**
  - With the dog standing, **tilt the whole body to its LEFT** by hand a few degrees and read the
    console `roll` (or panel attitude). Convention: **+roll = LEFT side high**.
  - **OBSERVE / PASS TELL:** tilting left drives roll **positive**; tilting right drives it
    **negative**. If it's **backwards**, flip the `−accelX` term at `isp_imu.spin2:188`, rebuild, and
    re-confirm **before** trusting any roll number below. (Pitch/fore-aft was confirmed last sprint:
    nose-down = negative.)
  - `[ ]`  roll sign correct as-is? ______  (flipped isp_imu:188? ______)
- **STEP B — read the RAW tilt:**
  - **Driver:** `test_dog_level.spin2` → `LEVEL_DONE` (timeout 80). It echoes the compiled trim
    (now **0/0**, so it prints **"trim is 0 → this MEASURE is the RAW un-leveled tilt"**), runs
    crouch→stand→measure, and averages `getAttitude()`.
  - **Setup:** support for gyro-cal + transitions, then **set down on a known-level surface**, on its
    feet, healthy pack, during the settle window before each measure.
  - **OBSERVE:** the averaged **RAW pitch / roll** of the loaded crouch.
  - **PASS TELL:** a **small, repeatable** RAW reading. A **slightly nose-up pitch is EXPECTED, not a
    defect** — the crouch is meant to sit a touch nose-up. A **large unexpected roll** (left/right
    lean) is a per-leg trim/servo regression to chase **before** pasting anything.
- **STEP C — bench pitch decision (record for closeout):**
  - **Keep the intended nose-up** → leave `stancePitchDeg = 0`. **OR flatten it** → paste the measured
    `pitch`/`roll` into `isp_calibration.spin2`, rebuild, re-run; residual should read ≈ 0.
- **Pass/fail:** `[ ]`  RAW pitch ____° roll ____° · decision: keep nose-up / flatten (paste ___/___)
  · residual after paste (if flattened): pitch ____° roll ____°

---

## Exercise 4 — Full gait catalog + speed knob: per-leg floors while walking [NEW]+[CERT]

- **Verifies:** §2 `«#15»` (per-leg planted floor survives walking) + regression of all six gaits and
  the speed knob.
- **Targets:** 1 bench unit, full 3-cog shape, all 12 leg servos.
- **Driver:** `test_dog_gaits.spin2` → `GAITS_DONE` (timeout 130). Runs each latched gait ~4 s with a
  `CMD_STOP`-ease to neutral between: **FORWARD → BACKWARD → TURN LEFT → TURN RIGHT → STEP LEFT →
  STEP RIGHT**, then **FORWARD @slow** then **@fast** (speed knob).
- **Setup:** support so feet swing free (or a low-friction surface if walking in place).
- **OBSERVE:**
  - **[NEW] mid-gait the rear stays lower than the front** — the crouch does **not** flatten while
    walking. Console `dumpState` mid-gait shows **front floors ≈ 95, rear ≈ 85**; **stride X centred
    on 0** (the rear −12 tuck is a *standing* property, not in the walking stride).
  - **[CERT]** each gait shape is right (forward/back stride, turn yaw, sidestep lateral); **no
    lead-in→walk hitch** (it eases into the gait, doesn't snap); **STOP eases back to the new loaded
    crouch** between gaits, not the old square stance; the reachability guard (25/130) never trips.
  - **[CERT]** @slow visibly takes more frames per stride than @fast.
- **PASS TELL:** all six gaits + both speeds run start-to-finish, `GAITS_DONE` prints, **and** the
  rear-lower-than-front floor is visible/dumped throughout — no flatten, no clamp peg, clean STOP.
- **Pass/fail:** `[ ]`  rear floors ≈85 < front ≈95 mid-gait? ______ · X centred 0? ______ · all 6
  gaits + slow/fast complete & ease cleanly? ______ · STOP → loaded crouch? ______

---

## Exercise 5 — Paw tricks: SIT / SHAKE / SALUTE [CERT]

- **Verifies:** regression of the paw-gesture rebalance (BENCH-REPAIRS-01 F4/F6) under the new neutral.
- **Targets:** 1 bench unit, full 3-cog shape.
- **Driver:** `test_dog_tricks.spin2` → `TRICKS_DONE` (timeout 90): init STAND → SIT → STAND →
  **SHAKE** (right paw) → STAND → **SALUTE** (right paw) → STAND.
- **OBSERVE:** the dog leans into a balanced sit, frees the **right front** paw to shake/salute
  **without tipping**, and eases back to a **level centered sit / STAND** each time.
- **PASS TELL:** both gestures complete, the dog never tips or pegs a clamp, and it returns balanced;
  `TRICKS_DONE` prints. (The return is to the loaded-crouch STAND, not the old square stance.)
- **Pass/fail:** `[ ]`  SHAKE balanced & returns? ______ · SALUTE balanced & returns? ______

---

## Exercise 6 — Gestures HELLO + PUSHUPS: bob parallel to the new neutral [NEW]+[CERT]

- **Verifies:** §2 `«#15»` gesture rebasing — PUSHUPS bobs off each leg's **own** neutral floor, and
  HELLO frees the FR foot relative to the loaded crouch.
- **Targets:** 1 bench unit, full 3-cog shape. **Interactive.**
- **Driver:** `test_dog_panel.spin2` (menu console, 2 Mbaud). Bring it up, then press:
  - **`12`** → `CMD_HELLO` (wave).
  - **`26`** → `CMD_PUSHUPS` (bob).
- **OBSERVE:**
  - **[NEW] PUSHUPS:** the body dips and rises **parallel to the loaded crouch** — the bob stays
    rear-lower/front-higher throughout, not flattening to level at the top of each rep.
  - **[NEW] HELLO:** the dog rebalances and **floats the FR foot off the floor** to wave **without
    tipping**, then eases back to the loaded crouch.
- **PASS TELL:** PUSHUPS bob keeps the front/rear height split (parallel dip); HELLO frees FR cleanly
  and returns to the loaded crouch — neither tips nor pegs a clamp.
- **Pass/fail:** `[ ]`  PUSHUPS dip parallel to new neutral? ______ · HELLO frees FR, no tip,
  returns to crouch? ______

---

## Exercise 7 — Full concurrency runtime: live integration [CERT]

- **Verifies:** the whole stack runs together under the production 3-cog runtime — motion (new
  neutral) + LED animation + live ranging + buzzer, scripted on cog 0.
- **Targets:** 1 bench unit, full 3-cog shape, everything live.
- **Driver:** `isp_robot_dog_top.spin2` (the integrated demo orchestrator).
- **OBSERVE:** the dog runs its scripted sequence with **LED animation playing and ranging live**
  while it moves; motion still rests/finishes in the **loaded crouch**; no stutter, no cog starvation,
  beeps fire on cue.
- **PASS TELL:** the full demo runs end-to-end with all three cogs live and motion unchanged from the
  isolated runs above — final integration confidence.
- **Pass/fail:** `[ ]`  full runtime smooth, motion in loaded crouch, LED+ranging+beep concurrent?
  ______

---

## Recording results

- **Certified [CERT]:** every old pose/gait/gesture completes its move, eases cleanly, returns to the
  **new loaded crouch** (not the old square stance), and pegs no clamp.
- **New characteristics [NEW] confirmed:** loaded-rear crouch stance (Ex 1/2), per-leg gait floors
  (Ex 4), gesture bob parallel to neutral (Ex 6), leveling re-measured (Ex 3).
- **Two open bench decisions to capture for closeout** (from Ex 3): (1) **pitch intent** — keep the
  intended nose-up or flatten (and the pasted trim if flattened); (2) **exact crouch magnitudes** — if
  any `NEUTRAL_*` was eased on the bench to clear a clamp or improve balance, record the final values.
- A failed exercise is a **finding**: gather *all* odd behaviors seen across the whole session, then
  hand the set to `defect-fixing` as one symptom inventory (multiple manual-test failures often share
  one root cause) before fixing — don't fix exercise-by-exercise.
</content>
