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
- **All 17 custom words trained & confirmed 1:1 (2026-06-11).** After a clean wipe-and-retrain in **one
  uninterrupted session**, every word committed to its own slot (5..21) and `test_voice_map` cataloged the
  vocabulary 1:1 in training order. The earlier "~11-word cap" was an artifact of an **interrupted**
  training session (words added after a break corrupt the DF2301Q's sequential slot assignment) — **not**
  a device limit; retraining in one pass resolved it.
- **`voiceToDogCmd()` is wired live** (`robot_dog_top`): CMDIDs 5..21 → the matching `CMD_*`, plus the
  built-in aliases 22/23 above. `registerCustomTable()` is registered so the dispatch log resolves each
  CMDID to its phrase.
- **Easier-to-train words applied** (single-syllable words train poorly): Bow → **"Take a Bow"**,
  Hello/Wave → **"Say Hi"** (also dodges the "Hello Peabody" wake phrase), Nod → **"Nod Yes"**.
- **Known flaky pair:** "Backward" ↔ "Forward" occasionally confuse (they rhyme); the "Retreat" / "Go
  Forward" built-in aliases backstop this. Retrain "Backward" → "Reverse" if the confusion bothers a demo.
- **Open:** the live end-to-end voice→motion bench run, and the full LED feedback scheme (only the basic
  green recognition blink is wired today).
