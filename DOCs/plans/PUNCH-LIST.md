# P2 Robot Dog — Punch List

Active-work register: things noticed during development that we **may or may not** implement.
This carries **outstanding** items only. When an item is confirmed done (`[x]` /
~~struck~~ ✅), `punch-list-maintenance` sweeps it into a dated archive
(`PUNCH-LIST-<YYYY-MM-DD>-archive.md`). States: `[ ]` open · `[~]` applied, not yet validated
on hardware · `[x]` done.

---

## Active

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
