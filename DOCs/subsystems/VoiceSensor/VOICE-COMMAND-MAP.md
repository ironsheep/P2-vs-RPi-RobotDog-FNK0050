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
| 6  | 10 | Bow          | `CMD_BOW`        | trick |
| 7  | 11 | Forward      | `CMD_FORWARD`    | gait (latched) |
| 8  | 12 | Backward     | `CMD_BACKWARD`   | gait (latched) |
| 9  | 13 | Turn Left    | `CMD_TURN_LEFT`  | gait (latched) |
| 10 | 14 | Turn Right   | `CMD_TURN_RIGHT` | gait (latched) |
| 11 | 15 | Halt         | `CMD_STOP`       | stop |
| 12 | 16 | Wave         | `CMD_HELLO`      | one-shot |
| 13 | 17 | Shake        | `CMD_SHAKE`      | one-shot |
| 14 | 18 | Salute       | `CMD_SALUTE`     | one-shot |
| 15 | 19 | Push Ups     | `CMD_PUSHUPS`    | one-shot |
| 16 | 20 | Nod          | `CMD_NOD`        | one-shot |
| 17 | 21 | Parade Rest  | `CMD_PARADE_REST`| posture |

**Excluded** (panel had ~19 behaviors, only 17 slots): `STEP_LEFT` / `STEP_RIGHT` (acoustically close to
"Turn Left/Right", subtle on camera). Also panel-UI-only, not voice behaviors: head-pan angles, the speed
selector, SPIN (a timed turn), SPEAK (bark+nod composite).

## Status
- 2026-06-10 run 1 (`test_voice_map`, `src/logs/debug_260610-133727.log`): **slots 5–15 verified** —
  Stand…Halt all matched in order (train-order = CMDID-order confirmed). **Slots 16–21 NOT on the
  device** — Wave/Shake/Salute/Push Ups/Nod/Parade Rest mis-recognized onto existing slots (6/8/9), i.e.
  the last 6 words never trained. Renamed slot 16 "Hello" -> "Wave" (collided with the "Hello Peabody"
  wake phrase).
- **Next:** (re)train slots 16–21 = Wave, Shake, Salute, Push Ups, Nod, Parade Rest, then re-run
  `test_voice_map` for a clean 17/17. If they still won't take, the device may cap custom words below 17
  -> trim the table to fit. Then wire `voiceToDogCmd()` + LED feedback.
