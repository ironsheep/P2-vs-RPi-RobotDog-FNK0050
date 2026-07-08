# plans — sprint plans, playbooks & the punch list

![Doc Type](https://img.shields.io/badge/doc-planning-blue)
![Platform](https://img.shields.io/badge/platform-Propeller%202-blue)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![License](https://img.shields.io/badge/license-MIT-green)

Working planning documents — the **active** sprint plan, the bench-verification playbook
it executes against, and the running punch list. Completed/superseded plans move to
[`archive/`](archive/) so this level always shows what's live.

### Active

| File | What it is |
|------|------------|
| [`PUNCH-LIST.md`](PUNCH-LIST.md) | Running list of small open/deferred items (e.g. LED gamma correction). |
| [`VOICE-INTEGRATION-SPRINT-PLAN.md`](VOICE-INTEGRATION-SPRINT-PLAN.md) | The voice-recognition sprint plan. |
| [`VOICE-INTEGRATION-TEST-PLAYBOOK.md`](VOICE-INTEGRATION-TEST-PLAYBOOK.md) | Its bench-verification playbook. |

_The **Voice Integration** sprint shipped in build 0.3.0 (2026-06-11): the 2nd-bus voice recognizer, the
cog-0 dispatch loop, the confirmed **17-word command map** (`voiceToDogCmd()` wired live, plus built-in
aliases), and the command-driven **LED engine** are all **code-complete and bench-confirmed**. Remaining
before closeout/archive: the **live end-to-end voice→motion demo** and the **full LED feedback scheme**.
(The earlier **Dog-Like-Motion-01 Keystone** sprint closed at build 0.2.0 and is in [`archive/`](archive/).)_

> Note: the voice sprint plan/playbook were authored for the **plumbing** phase, when the map seam
> deliberately returned `CMD_NONE`. The CMDID→behavior map has **since been completed** — see
> [`../subsystems/VoiceSensor/VOICE-COMMAND-MAP.md`](../subsystems/VoiceSensor/VOICE-COMMAND-MAP.md) and
> the Theory of Operations §2/§5 for the current behavior.

### Archive

Closed-out plans, kept for history — see [`archive/`](archive/).

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
