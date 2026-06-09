# P2 Robot Dog — Release Notes

User-facing summary of each firmware build. Newest at the top.

---

## 0.2.0 — 2026-06-09

Closes the **Dog-Like-Motion-01 Keystone** sprint — the dog's resting stance was rebuilt so poses and
walking all grow from one consistent shape, and the bench pass that proved it fixed two things that
looked wrong.

**The new resting stance**

- **A natural "loaded" crouch.** At rest the dog now settles into a single, consistent stance — the
  hindquarters carry a bit more and tuck slightly back, the front stands a touch taller — and every
  pose and gait now eases to and from that same shape instead of a flat, square box. Measured on the
  bench, it stands **level**.

**What works now that didn't before**

- **Salute.** The dog now **salutes standing at attention** instead of from a sit — it shifts its
  weight, raises the front-right paw, holds, and lowers, all without tipping over. (Before, the salute
  could tip toward the raised paw.)
- **Shake** still offers its paw from a seated position, and settles back level when done.
- **Lie down.** Reworked into a clean **low, flat rest** — the dog sits low and level with its paws
  flat on the ground (the earlier version tilted nose-up and lifted the front paws off the floor).
- **Walking.** Each leg keeps its own foot height while walking, so the rear stays lower than the front
  through the whole gait instead of flattening out mid-stride. All six gaits and the speed control run
  smoothly and ease cleanly to a stop.

**Confirmed on the bench**

- The tilt sensor's **left/right direction** was verified by hand-tilting the dog — leaning left reads
  positive, as intended. Combined with the earlier front/back check, both tilt axes are now trusted.
- The resting stance measures **level**, so no leveling trim is applied.

**Naming**

- The integrated demo program was renamed from `isp_robot_dog_top` to **`robot_dog_top`** so the
  top-level app is clearly distinct from the internal building-block modules.

**Known / not yet verified**

- The new low **lie-down** is proven safe and was checked in the geometry self-test, but its final
  on-robot look is a quick visual confirm on the next flash.
- A noticeably *lower* lie-down (belly near the floor) is limited by one leg's calibration and would
  need that leg re-trimmed — a separate bench task.

---

## 0.1.2 — 2026-06-08

First tagged build. Closes the **Bench-Repairs-01** sprint — a round of fixes to how the dog poses,
gestures, and protects itself, all verified on the bench.

**What works now that didn't before**

- **Bow.** The dog now lifts its head as it bows, so the snout clears the surface instead of dipping
  into it — and when it stands back up, the head returns to wherever you had it pointed before the bow.
- **Shake & salute.** Before lifting the front-right paw, the dog shifts its weight onto the other three
  legs so it no longer tips. When the trick finishes, it settles back to a level, centered sit instead
  of staying leaned over.
- **Hello / wave.** The waving foot now floats clearly above the floor through the whole wave — it no
  longer scuffs the ground at the bottom of each swing.
- **LED ring.** The solid / wipe / chase color modes now light up from a fresh power-on (they default
  to white) instead of looking dead until a color was sent. The control panel also shows which LED mode
  is active by name.

**New protection**

- **Low-battery safety.** A new hard cutoff: if the pack drops below 5 V (confirmed over several quick
  re-reads so a momentary dip won't trip it), the dog announces "battery too low," eases gently down to
  rest, and refuses further movement until it's powered off and back on. The earlier "getting low"
  warning at 6.4 V still works as a softer advisory. Verified on a genuinely flat pack.

**Behind the scenes (affects what you see in logs)**

- The bench tilt readings are now taken after the body has fully settled, so the numbers reflect the
  final pose rather than a mid-motion blur.
- A tilt-sensor axis labeling error was corrected — "pitch" now means front/back tilt and "roll" means
  left/right tilt, as you'd expect.

**Known / not yet verified**

- The left/right tilt **sign** (which way counts as positive) hasn't been confirmed yet — it needs a
  deliberate left/right tilt test, planned for the next sprint.
- The dog still stands with a few degrees of residual lean; squaring that up is the focus of the next
  ("dog-like motion") sprint.
