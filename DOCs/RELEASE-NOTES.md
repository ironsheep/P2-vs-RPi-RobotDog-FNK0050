# P2 Robot Dog — Release Notes

User-facing summary of each firmware build. Newest at the top.

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
