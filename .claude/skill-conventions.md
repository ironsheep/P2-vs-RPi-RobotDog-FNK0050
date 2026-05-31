# Project skill conventions — P2 Robot Dog

Slot values for the central skill set. Schema: `~/.claude/skills-docs/SKILLS-MAINT.md`.
Required slots have no default; optional slots omitted here fall back to documented defaults.

**Project note:** this is **P2 firmware** (Spin2/PASM2, `pnut-ts`), not an app with a unit-test
suite. There is no automated behavioral test runner — the automated gate is a **compile-all
sweep** of every `.spin2` object, and real verification is the **hardware bench playbook**
(`DOCs/P2_BRINGUP_PLAYBOOK.md`). `BUILD_COMMAND` and `TEST_COMMAND` therefore both run the
compile sweep.

---

## Identity

```yaml
USER_NAME: Stephen
PROJECT_NAME: P2 Robot Dog
```

## Build & test

```yaml
# Both run a compile-all sweep over every object (the only automated gate).
# Real hardware verification lives in DOCs/P2_BRINGUP_PLAYBOOK.md.
BUILD_COMMAND: |
  cd "$(git rev-parse --show-toplevel)" || exit 1
  rc=0; for f in src/*.spin2; do pnut-ts -q "$f" || rc=1; done
  rm -f src/*.bin; exit $rc
TEST_COMMAND: |
  cd "$(git rev-parse --show-toplevel)" || exit 1
  rc=0; for f in src/*.spin2; do pnut-ts -q "$f" || rc=1; done
  rm -f src/*.bin; exit $rc
CANONICAL_TEST_TARGET: PNut-ts v1.55 compile sweep over src/ (host); on-hardware verification via the P2 bench playbook
```

## Build version

```yaml
# Spin2 CON constant, single source of truth. Bump on each build.
BUILD_VERSION_LOCATION: src/isp_version.spin2
BUILD_VERSION_KEY: FW_VERSION_MAJOR / FW_VERSION_MINOR / FW_VERSION_PATCH
BUILD_VERSION_EXAMPLE: 0.1.0
```

## Doc paths

```yaml
PLAN_DIR: DOCs/plans/
PLAN_ARCHIVE_DIR: DOCs/plans/archive/
ANALYSIS_DIR: DOCs/analysis/
PUNCH_LIST_DOC: DOCs/plans/PUNCH-LIST.md
RELEASE_NOTES_DOC: DOCs/RELEASE-NOTES.md
SPEC_DOC: DOCs/spec/P2-RobotDog-Specifications.md   # designated home; create when first authored
# STYLE_GUIDE_DOC / HELP_VOICING_GUIDE / MANUAL_VOICING_GUIDE: omitted (no UI/help/manual)
```

## Audience & vocabulary

```yaml
# RELEASE_NOTES_AUDIENCE: omitted -> default "end users"
TEST_FLEET_DESCRIPTION: the P2 bench unit
```

## Tracking-readiness

```yaml
PROJECT_INIT_DATE: 2026-05-31
```

## P2 development cycle

```yaml
# Declarative path: only pnut-ts is installed (no wrapper scripts, no flexspin).
# pnut-term-ts is not in this container, so flash/run is bench-side; the
# p2-dev-cycle skill constructs the flash invocation from slots when run on the bench.
P2_WORK_DIR: src/
SPIN2_TOP_FILE: isp_dog_bringup.spin2   # current top; override per invocation for other tops
P2_CLOCK_FREQ: 200_000_000              # _clkfreq used across the firmware; pre-flash clock check
P2_DEBUG_BAUD: 2000000                  # PROJECT STANDARD: ALL P2 comms (debug + the bring-up console) at 2 Mbaud
# P2_USB_DEVICE / RUN_TIMEOUT_SECONDS / P2_INCLUDE_PATHS / P2_LOG_DIR /
# P2_END_MARKER / P2_COMPAT_COMPILE_COMMAND / P2_COMPILE_COMMAND / P2_FLASH_COMMAND:
#   omitted -> documented defaults (single device auto-detect, flat src/, no compat compiler)
```
