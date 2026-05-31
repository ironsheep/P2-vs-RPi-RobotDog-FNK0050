# P2 Robot Dog overlay — p2-dev-cycle

Additive rules for the Spin2/PASM2 dev cycle on this project. The central steps stay in force.

## Augments §1 Compile — authoring standard is a hard gate

Every `.spin2` file MUST conform to **`DOCs/policy/SPIN2-AUTHORING-GUIDE.md`** before a compile
is considered clean: ASCII-only (box-drawing OK in comments); VSCode/PNUT_TS doc-comment style
(`''` PUB / `'` PRI, `@param`/`@returns`/`@local`, blank separators); single exit point (`quit`
from loops, never `return`); named constants (no magic numbers); descriptive names (no
single-letter/generic locals); object constants referenced via the OBJ prefix; block-decl
labels `CON ' ---- Label ----`; `{{` `}}` only for header/license. The guide's end checklist is
the pre-commit gate.

## Augments §1 Compile — project-verified pnut-ts gotchas (extends the central "reserved names" pitfall)

Beyond the central list (`ones`, `addbits`), these were hit and verified on `pnut-ts` v1.55:

- **Reserved identifiers** (cause `m241` / "unique name" / "unique method" errors): `step`
  (repeat..step), `sumX`/`sumY`/`sumZ` (collide with the `SUMC`/`SUMNC`/`SUMZ`/`SUMNZ` PASM2
  family). Pick other names.
- **CORDIC/math builtins:** `qsin(length, angle, twopi)` and `qcos(...)` take **three** args
  (`twopi = 0` → full circle = 2^32 angle units); the 2-arg form fails. `xypol(x, y) : rho, theta`
  (2 in / 2 out). Integer square root is the named operator **`sqrt(expr)`**, NOT `^^`. Unsigned
  divide is `+/`.
- **P2 angle units:** `$4000_0000` = 90°. deg→units = `deg * 11_930_465` (= 2^32/360, wraps mod
  360 via 32-bit overflow); units→deg = `units +/ 11_930_465` then fold `>180` by `-360`.
- **Use `p2kb-mcp`** (authoritative P2 KB) to confirm any Spin2 builtin signature or PASM2
  encoding rather than web search or memory — the KB's `qsin` doc itself listed a wrong arity.

## Augments §0 First-session / §3 Flash — flash is bench-side in this container

This dev container has **`pnut-ts` only** — `pnut-term-ts` is **not installed**, so the device
check (§0), flash (§3), and log-inspect (§4) steps cannot run here. The in-container loop is
**compile-only** (`pnut-ts -d {{SPIN2_TOP_FILE}}` from `{{P2_WORK_DIR}}`). Hand the compiled
`.bin` and `DOCs/P2_BRINGUP_PLAYBOOK.md` to {{USER_NAME}} for the flash/run/observe half on the
bench, and resume diagnosis (§5) from the log {{USER_NAME}} pastes back.
