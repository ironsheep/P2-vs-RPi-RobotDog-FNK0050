# P2 Robot Dog overlay — test-playbook

Additive rules for authoring verification playbooks on this project. Central steps stay in force.

## Augments §4 verification-surface nature / §5 targets — one bench unit, human-driven

The verification surface is **a single P2 bench unit** ({{TEST_FLEET_DESCRIPTION}}), not a
fleet — most exercises target one unit; there is no multi-device sync to specify. There is **no
automated or interactive simulator**: exercises are run by hand at the bench through the
**`isp_dog_bringup` menu console** (flash it, open serial on the programming port at 2 Mbaud
— the project standard, `P2_DEBUG_BAUD` — press the test's menu digit). Live tests run until a keypress. State each exercise's
**menu key** in its heading (or Setup). The model playbook is `DOCs/P2_BRINGUP_PLAYBOOK.md`.

## Augments §2 exercise format — every inferred constant gets a metered-vs-read check

Per CLAUDE.md, facts marked "verify"/"inferred" in the docs (ADC VREF + battery divider,
WS2812 bit timing, the leg↔channel↔side map, the CORDIC IK, HC-SR04 conversion) are traced
from the Freenove code/datasheets, **not metered**. Any exercise that exercises one MUST be
tagged **⚠** and record **metered-vs-read** (e.g. "metered ___ V / read ___ V"), so a wrong
constant is caught and corrected rather than silently trusted. Cite the doc and its confidence
level when an Expected value rests on an inferred fact.

## Augments §2 Setup — servo-motion safety preconditions

Any exercise that commands a servo (PCA9685 channels: legs, head) MUST carry a Setup
precondition to **lift/support the robot** so limbs are free, and to keep the battery connected
(the board regulates from the pack; do not power servos from USB alone). Sensor exercises that
read a 5 V-native part MUST note the level-shift requirement — the **HC-SR04 ECHO** line must be
divided to ≤ 3.3 V before it reaches the P2 (the P2 is **not** 5 V tolerant).
