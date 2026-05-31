# P2 Robot Dog overlay — baseline-health

Additive rules for measuring baseline health on this project. Central steps stay in force.

## Augments §1 Clean build — the build is a compile-all sweep

There is no app build; the build is a **`pnut-ts` compile-all sweep** over every object
(`{{BUILD_COMMAND}}` runs `pnut-ts -q` on each `src/*.spin2` and cleans the `.bin`s). "Zero
warnings" means **every object compiles clean** (rc 0, no `error:` / `warning:` lines). A single
object that fails to compile fails the baseline.

## Augments §2-§4 test suite / skips / grouping — no test suite; compile is the gate

This is firmware with **no automated behavioral test suite**, so §2-§4 map as follows:

- **§2 "run the full test suite"** → run the same compile-all sweep ({{TEST_COMMAND}}). The
  **failure unit is a non-compiling object**, not a failing test case.
- **§3 "never allow skips"** → a "skip" here is **any object excluded from the sweep** (e.g. a
  top file deliberately left out, or a `#ifdef`-gated path never compiled). Name it explicitly
  in the hand-back; "green" must mean every object was compiled.
- **§4 "group by cause"** → cluster compile failures by shared root cause before fixing:
  reserved-word/identifier collisions (`step`, `sumX/Y/Z`), CORDIC/IK math or arity errors
  (`qsin`/`sqrt`), a missing/renamed child object, or a guide-checklist violation. One
  diagnosis usually clears the whole cluster.

**Behavioral verification is out of scope for the automated baseline** — it lives in the
hardware bench playbook (`DOCs/P2_BRINGUP_PLAYBOOK.md`, run on {{TEST_FLEET_DESCRIPTION}}). A
green compile baseline never implies on-hardware correctness; say so in the hand-back.
