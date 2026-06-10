# P2 Robot Dog — Punch List

Active-work register: things noticed during development that we **may or may not** implement.
This carries **outstanding** items only. When an item is confirmed done (`[x]` /
~~struck~~ ✅), `punch-list-maintenance` sweeps it into a dated archive
(`PUNCH-LIST-<YYYY-MM-DD>-archive.md`). States: `[ ]` open · `[~]` applied, not yet validated
on hardware · `[x]` done.

---

## Active

### [ ] Unify the two I2C bus masters — add clock-stretch back to the DAT singleton — *experiment; deferred*

**What:** we now have two I2C bus masters that have **diverged**: `src/isp_i2c.spin2` (VAR/instance,
built for the 2nd/voice bus) **honors clock-stretch** (`STRETCH_LIMIT`), while `src/isp_i2c_singleton.spin2`
(DAT, bus 1 — servos/IMU/battery) had clock-stretch **removed**. The experiment: add the same bounded
clock-stretch waits back into the **singleton** and confirm bus 1's devices (PCA9685 `$40`, ADS7830
`$48`, MPU6050 `$68`) still talk correctly.

**Why it would pay off:** if it proves out, we have **one I2C structure / one bus engine, in two
implementations** — a DAT (singleton) and a VAR (instance) — that differ **only in storage scope**, not
in behavior. That keeps the matched pair maintainable (a bus-logic fix lands in both the same way)
instead of two drifting engines.

**Why it's expected to be safe:** a device that does **not** clock-stretch releases SCL immediately
after `drvh scl`, so the bounded `testp scl wc` wait passes on the first check — ~1 extra instruction per
bit, no timing/behavior change. The bound (`STRETCH_LIMIT`) prevents any hang if a line is stuck.

**Where:** port the `read()`/`wait()`/`stop()` clock-stretch waits from `isp_i2c.spin2` (or the
voice-tested `DOCs/REF-NO-COMMMIT/` copy) into `src/isp_i2c_singleton.spin2`; bench-verify bus 1 unchanged
(servo/IMU/battery via the existing test drivers). *Noticed 2026-06-10, during the voice 2nd-bus prep.*

### [ ] Lower LIE_DOWN needs front-leg re-trim — *deferred; cal task, not a CON tweak*

**What:** the lie-down rest currently ships at `LIEDOWN_HEIGHT_MM=50` (low + level, paws flat,
verified on the bench 2026-06-09). It cannot go meaningfully lower with these calibrations: two
front joints carry large cal trims — **FL coxa ≈ −16°** and **FR femur ≈ −14°** — that box in the
low-pose envelope. At `Y=50` the right-front leg already rides at its fully-folded drivable limit
(the host gate `test_keystone_geometry` reports this as an **advisory WARN**, not a FAIL, by design).

**Why it would pay off:** a genuinely belly-down lie-down (body near the floor) would read more
"lying down." It needs the FL-coxa and FR-femur leg trims re-measured/re-trimmed (cal tool) to buy
clamp headroom — a bench calibration task, out of scope for the keystone sprint.

**Where:** `isp_calibration` leg trims (FL coxa, FR femur), then lower `LIEDOWN_HEIGHT_MM` and re-run
the host gate. *Noticed 2026-06-09, DOG-LIKE-MOTION-01 keystone §7 closeout.*

### [ ] Gamma correction for the LED ring — *deferred; perceptual only, no current win*

**What:** optional gamma (perceptual-brightness) correction of RGB channel values before transmit.

**Why it is NOT needed for the LED's sake:** the WS2812 is a **radiometrically linear** emitter
— drive duty *d*, get ~*d* of the photons. Metered emitted light is consistently strong and
linear per channel, and there is **no CRT-style transfer function to undo**. (Gamma originated
as a fix for the CRT's nonlinear voltage→luminance response; LEDs simply don't have one.) A
light meter sees nothing to gain — which is exactly what we measured.

**Why it *could* matter — human perception:** the **eye** perceives brightness nonlinearly
(~cube-root / CIE L\*). A linear PWM code ramp 0…255 therefore *looks* like it snaps bright
early then plateaus, and low-end fades stair-step. Gamma redistributes the 8-bit codes so equal
code steps look like equal *perceived* brightness steps — smooth fades, clean dim rendering. It
is a **perceptual** refinement, not a correctness fix.

**When it would pay off:** only for **smooth fades / breathing / very-dim ambient** effects. It
buys ~nothing for fixed-brightness status use — solid, blink, theater-chase, full-brightness
rainbow — which is all this ring currently does.

**Where it would go:** in **`isp_led_ring`** (the effects / Tier-3 layer), as a 256-byte
`gamma8` lookup (cf. `REF/iOT-code/jm_gamma8.spin2`), applied to r/g/b just before
`isp_ws2812.setPixelColor`. The transport (`isp_ws2812`) stays **pure** — no change there.

**Trigger to implement:** the day we add a fade / breathing / dim-ambient LED effect. Until
then, deliberately omitted — no measurable win and zero cost to defer.

*Noticed 2026-05-31, during the WS2812 ratification against `jm_rgbx_pixel`.*
