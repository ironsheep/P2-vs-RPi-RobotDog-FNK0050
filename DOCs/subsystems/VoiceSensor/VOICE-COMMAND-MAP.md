# Voice Command Map (custom vocabulary)

Single source of truth for the dog's **custom** voice vocabulary: the words trained into the DF2301Q's
17 custom slots, and the dog motion each maps to. This file drives **both** the on-device training order
**and** the firmware (`registerCustomTable()` phrases + `voiceToDogCmd()` routing).

**Contract:** the DF2301Q assigns custom slot IDs **in training order** and stores no text — it only ever
reports the slot number. So the training order below **is** the CMDID assignment: first word trained =
CMDID 5, second = 6, … last = 21. Train in this exact order; the firmware table mirrors it.

**Name / wake word:** the dog is **Peabody** ("P2"-body; Mr. Peabody, the genius cartoon dog). Wake phrase
**"Hello Peabody"**, replacing the stock "Hello Robot". (Confirm the device retains a retrained wake word
across power cycles.)

## The 17 custom commands (training order = CMDID 5..21)

| Train # | CMDID | Word (train + speak) | Dog command | Class |
|--------:|------:|----------------------|-------------|-------|
| 1  | 5  | Stand        | `CMD_STAND`      | posture |
| 2  | 6  | Sit          | `CMD_SIT`        | posture |
| 3  | 7  | Lie Down     | `CMD_LIE_DOWN`   | posture |
| 4  | 8  | Crouch       | `CMD_CROUCH`     | posture |
| 5  | 9  | Relax        | `CMD_RELAX`      | posture |
| 6  | 10 | Take a Bow   | `CMD_BOW`        | trick |
| 7  | 11 | Forward      | `CMD_FORWARD`    | gait (latched) |
| 8  | 12 | Backward     | `CMD_BACKWARD`   | gait (latched) |
| 9  | 13 | Turn Left    | `CMD_TURN_LEFT`  | gait (latched) |
| 10 | 14 | Turn Right   | `CMD_TURN_RIGHT` | gait (latched) |
| 11 | 15 | Halt         | `CMD_STOP`       | stop |
| 12 | 16 | Say Hi       | `CMD_HELLO`      | one-shot |
| 13 | 17 | Shake        | `CMD_SHAKE`      | one-shot |
| 14 | 18 | Salute       | `CMD_SALUTE`     | one-shot |
| 15 | 19 | Push Ups     | `CMD_PUSHUPS`    | one-shot |
| 16 | 20 | Nod Yes      | `CMD_NOD`        | one-shot |
| 17 | 21 | Parade Rest  | `CMD_PARADE_REST`| posture |

## Built-in aliases (factory words mapped as extra triggers)

A couple of our custom words are acoustically close to the module's **built-in** command words, so the
recognizer occasionally returns the built-in instead. Those built-ins are factory-trained (very reliable)
and mean the same thing, so we map them as aliases in `voiceToDogCmd()` — say either word, same action:

| Built-in CMDID | Built-in phrase | Mapped to |
|---:|---|---|
| 22 | "Go Forward" | `CMD_FORWARD` (alias of custom "Forward" = 11) |
| 23 | "Retreat" | `CMD_BACKWARD` (alias of custom "Backward" = 12) |

(The built-in `Turn Left/Right NN Degrees` words are **not** mapped — they're specific-angle turns, not the
continuous gait our "Turn Left/Right" runs.)

**Excluded** (panel had ~19 behaviors, only 17 slots): `STEP_LEFT` / `STEP_RIGHT` (acoustically close to
"Turn Left/Right", subtle on camera). Also panel-UI-only, not voice behaviors: head-pan angles, the speed
selector, SPIN (a timed turn), SPEAK (bark+nod composite).

## Status
- 2026-06-10/11 (4 catalog runs): **slots 5–15 reliably trained** (Stand…Halt, 1:1 in order). **16–21
  never committed** — those words alias onto 6/7/8/9 (multiple words -> same CMDID). ROOT CAUSE
  (per Stephen): the original training session was **interrupted mid-way** and words were added after a
  break, which corrupts the DF2301Q's sequential slot assignment -- so the "~11 cap" is likely an
  artifact of the broken session, not a real device limit.
- **Plan (2026-06-11):** **wipe all custom words, retrain all 17 in ONE uninterrupted pass** in the order
  above, then catalog twice (`test_voice_map`) and diff the SUMMARY blocks -- identical == trusted. This
  answers both unknowns: *can we train cleanly?* and *can we identify the trained words?*
- **Easier-to-train words applied** (single-syllable words train poorly): Bow -> **"Take a Bow"**,
  Hello/Wave -> **"Say Hi"** (also dodges the "Hello Peabody" wake phrase), Nod -> **"Nod Yes"**.
- The robot is already wired (`voiceToDogCmd()`); once the catalog confirms, trim only if some slots
  still won't take, then add LED feedback.
