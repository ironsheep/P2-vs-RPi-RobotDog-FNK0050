# P2 Robot Dog overlay — sprint-closeout

Additive rules for closing out a sprint on this project. Central steps stay in force.

## Augments §8 Archive — the archive is LOCAL-ONLY (not under version control)

`{{PLAN_ARCHIVE_DIR}}` (`DOCs/plans/archive/`) is **git-ignored** — a local history of completed
work, intentionally **NOT** in version control. So on this project "archive the plan" (§8) means:

1. Stamp the **lifecycle marker** (shape below) at the very top of the file.
2. **Move** the file into `DOCs/plans/archive/` with a plain `mv` (NOT `git mv` — the destination
   is ignored; `git mv` errors or, with `-f`, wrongly re-tracks it).
3. **`git rm --cached <original-path>`** so the file leaves version control while its content
   persists on disk in the archive. The closeout commit records the removal (a staged deletion).

The dated closeout doc (§5) is written **into the same local-only archive**, so the audit trail is
local history too — by project intent. A fresh clone will not carry the archive; that is expected.

**Lifecycle-marker shape** (§8 defers the shape to this overlay): a blockquote at the very top of
the archived file —
`> **ARCHIVED <YYYY-MM-DD> — closed. Audit: <closeout-doc-filename>.**`

## Augments §8 — the bench PLAYBOOK is closed out and archived like a plan

The hardware bench playbook (`DOCs/plans/SMOOTH-MOTION-AND-INTEGRATION-TEST-PLAYBOOK.md` and its
successors) is a **test plan**, not a permanent living document. Close it out and archive it the
same way as a sprint plan, using the local-only procedure above.

A playbook may **span more than one sprint** (it stays active as the living bench record across
sprints), so archive it at the closeout that **finishes its coverage**, not necessarily its
originating sprint. Before archiving:

- Flip **every** exercise to its final pass/fail with the verification date.
- Mark **every** finding resolved, or **carried** — carryovers move to the consuming sprint's plan
  (e.g. F5–F8 → the bench-repairs plan), never left open in the archived playbook.

Author a **fresh** playbook (via `test-playbook`) for the next sprint's verification rather than
reopening an archived one (archives are never re-edited — see `punch-list-maintenance`).
</content>
