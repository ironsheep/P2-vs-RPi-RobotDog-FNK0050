[//]: # (markdownlint-configure-file { "MD013": false, "MD033": false })

# Dog-Like Motion Study — Findings & Recommendations

How to take the P2 Robot Dog's motion from **"Freenove-equivalent / it moves"** to **"it moves like a
dog"** — across both **gaits** (dynamic) and **poses** (static) — and spend the P2's surplus (spare
cogs, CORDIC, spare servo channels) on naturalness the Raspberry Pi build never had room for.

![doc-study](https://img.shields.io/badge/doc-study%20%2F%20design-blue?labelColor=black)
![platform-Propeller 2](https://img.shields.io/badge/platform-Propeller%202-blue?labelColor=black)
![status-findings](https://img.shields.io/badge/status-findings%20(pre--implementation)-orange?labelColor=black)
![maintainer-stephen@ironsheep.biz](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![license-MIT](https://img.shields.io/badge/license-MIT-green?labelColor=black)

> **Read me first — this is a *findings* doc, not yet committed work.** It audits our current motion
> against canine biomechanics and proposes prioritized, hardware-feasible changes. Implement after
> Stephen prioritizes.
>
> **Sourcing:** the key biomechanics figures below were **verified against the primary literature via
> web research (2026-06)** — see **Sources** at the end. The headline numbers are confirmed (duty-factor
> walk-vs-trot split, 60:40 weight, swing-leg retraction, walk-pendulum/trot-spring, ~30° hindlimb
> angulation). Exact amplitudes still vary by breed/speed — tune on the bench.

---

## 1. How a real dog moves (the target)

**Gaits.** Two numbers define a symmetric gait (Hildebrand): **duty factor** (% of stride a foot is
down) and the **footfall coupling**.
- **Walk** — lateral sequence, **4-beat**: LH → LF → RH → RF (each hind followed by the *same-side*
  fore). **3 feet down at all times** (statically stable). **DF ≈ 0.65**. The body **vaults** like an
  inverted pendulum (COM *highest* at mid-stance) and **weaves laterally** over the shifting support
  tripod; the **head bobs in time with the forelimbs**.
- **Trot** — diagonal, **2-beat**: LF+RH together, then RF+LH. **DF ≈ 0.5** (dynamic, not statically
  stable). The body **bounces** (spring-mass): COM **lowest at mid-stance**, **2× per stride** — *this
  bob is the visual signature of a trot.* The **head is held steadier** than at a walk. We currently
  implement only a trot.
- **Pace** (ipsilateral pairs) rolls/waddles — the gait to *avoid* accidentally producing.

**Swing-phase paw path is ASYMMETRIC** — a comma/teardrop, not a sine arc: **brisk lift** (tibia+femur
flex) in the first ~40% of swing to a **modest clearance** (~5–15% of limb length), then a **low fast
forward glide**, then a **decelerating retraction** so the paw's ground-speed ≈ 0 at touchdown (soft
landing, no "stab"). Swing-leg retraction before contact is a hallmark of stable biological gait.

**The body is not a level plank** — it heaves/rolls/pitches phase-locked to footfalls (above). Missing
this is the #1 "it's a robot" tell.

**Static postures are angulated and asymmetric.** Dogs **do not stand on straight vertical legs** —
the rear limb is a flexed **stifle+hock "Z" crouch** (a *loaded* crouch, preloaded for instant
movement; ~60% weight front / 40% rear). A relaxed dog **cocks a hip, shifts weight, lets the head
drift off-axis** — never a mirror-perfect sawhorse.

---

## 2. Audit — what we do today (the "robotic" signature)

**Gaits** (`gaitLinearFwd` / `gaitTurn` / `gaitSidestep`): every robotic tell is present.

| Trait | Ours today | Dog | Verdict |
|---|---|---|---|
| Footfall | diagonal trot only | walk *and* trot (+gallop) | missing the walk |
| Swing path | **symmetric** `X=12·cos(φ)`, `Y=stand+6·sin(φ)` (an ellipse) | **asymmetric** comma w/ retraction | ✗ |
| Touchdown | continues the cosine (no slow-down) | **retracts**, ground-speed→0 (soft) | ✗ |
| Coxa (lateral) | **`Z = ±10 fixed`** — never moves | adducts/abducts, circumducts | ✗ **(biggest miss)** |
| Body | **rigidly level** (per-foot Y only, symmetric) | bob (2×/stride) + roll + pitch | ✗ **(biggest miss)** |
| Timing/symmetry | perfectly periodic, perfectly mirrored L↔R | slight L/R + cycle variation, a lead | ✗ |
| Head | static | bobs (walk), steady (trot) | ✗ |

**Poses** (`stand`/`sit`/`crouch`/`relax`/`lie-down`/`bow`/`parade-rest`): all are **perfectly
symmetric foot-XYZ targets** with `Z=±10` fixed and **no rear angulation** — `STAND_HEIGHT=99` is a
near-straight, square stance. No hip-cock, no weight shift, no maintained crouch, no idle micro-motion.

---

## 3. Recommendations (prioritized, mapped to our 12 DOF)

DOF reminder: **coxa** = lateral/vertical swing (the unlocked, *most-wasted* axis), **femur** =
fore-aft stride, **tibia** = reach/clearance/compliance.

### ★ KEYSTONE — angulate the neutral stance
The neutral STAND is the foundation **both poses and gaits build from** (gaits oscillate around it;
poses ease to it). Make it a **loaded crouch**: flexed stifle/hock on the **rear** pair (conformation
references put the **stifle and hock each ~30° off vertical**, femur ~90° to the pelvis), a touch of
elbow/shoulder flex front, and a **60:40 front/rear weight bias** (30% per fore, 20% per hind — verified)
— *not* straight square legs. **One change improves everything downstream.** (Our CLAUDE.md already hints
at a "deeper crouch" stance — this formalizes it.)

### Gaits
1. **Use the coxa.** Add a lateral component to swing (small foot in/out placement + circumduction) and
   a **lateral COM weave** (large in walk, small toward the loaded diagonal in trot). *This is the
   single most-dog change and the one the range-fix just unlocked.*
2. **Asymmetric swing trajectory.** Replace the symmetric ellipse with brisk early lift → low forward
   glide → **retracting** touchdown (paw ground-speed→0). Soft landing via tibia flex.
3. **Trunk bob/roll.** Trot: 2×/stride vertical bob (COM low at mid-stance) + small roll to the loaded
   diagonal. Synthesize from **coordinated leg-length offsets** (no spine servo).
4. **Add a true WALK** (lateral-sequence LH-LF-RH-RF, DF≈0.65) with its vault profile + lateral weave +
   head-bob — the most natural-looking slow gait.
5. **Per-gait duty factor** + correct coupling; never accidentally pace.
6. **Head motion** — bob synced to forelimbs (walk), steady (trot).

### Poses
1. **Angulation everywhere** (from the keystone) — keep joints softly flexed, never locked.
2. **Asymmetry / "personality"** — a small *consistent* L/R offset table (hip cock, head off-axis, feet
   not squared). Not random jitter — a per-individual bias.
3. **Idle micro-motion** — slow breathing-like body rise/fall + occasional head turn/weight-shift so a
   "still" dog isn't a statue.
4. **Refine specific poses** — **sit** → lazy sit (hips rolled to one side); **bow/stretch** → front-low
   / rear-high with the front pair folding and rear extending; **sleep** → head down on paws + breathing;
   **sploot** → **half-sploot** (one hind extended back via femur rear-swing + coxa splay, asymmetric).

### New behaviors (fun, and coxa showcases)
- **Shake-off** (water-shake shimmy) and **rear-wiggle/wag** — both built on the **coxa lateral sweep**;
  the moves that most scream "dog," and they exist *because* of the range fix.
- **Scratch** (hind-leg ear-scratch), **alert/point** (tall, head up, paw raised), **circle-then-settle**.

---

## 4. Hardware adds — the P2 headroom, made physical

The PCA9685 has 16 channels; we use 13 (12 legs + head tilt), leaving **channels 0, 1, 14 free — three
spare servo connectors.** These are "wire it up + add a CON," and each is a high-yield naturalness win
the Pi build had no room for:

| Add | Channels | Unlocks |
|---|---|---|
| **Tail** (wag + raise) | 1–2 | The iconic happy **wag**, submissive **tuck**, alert **up** — the single biggest expressiveness gain. Makes "rear-wiggle" a real tail wag. |
| **Head pan** (→ pan/tilt) | 1 | Quizzical **side-tilt**, **look-around/scan**, **gaze-leads-turn**, and (with the future camera) tracking. |

Until a tail exists, the **rear-wiggle is the stand-in**. These adds double as the literal demonstration
of the surplus the P2 affords.

---

## 5. Why this is a P2 showcase

Every recommendation here *costs motion-control richness* — exactly what the P2 has in surplus over the
Pi: the **CORDIC** does the per-frame IK/trajectory math for free; the **fixed-rate eased engine**
already gives a clean substrate for asymmetric profiles and body oscillation; spare **cogs** and
**I/O** leave room for a tail, a head-pan, vision, and closed-loop balance. The Pi build ran a fixed
sinusoid because that's what fit; **we can afford to move like a dog.**

---

## 6. Suggested order of work

1. **Keystone:** angulate the neutral stance (re-tune `STAND_HEIGHT` / per-leg targets to a loaded rear
   crouch). *Verify it didn't break the gaits/poses that ride on it.*
2. **Coxa-in-gait + asymmetric swing + trot bob** (the three biggest "alive" levers), one at a time.
3. **A true walk** with weave + head-bob.
4. **Pose polish** (asymmetry, idle micro-motion) + the **sleep/stretch/sploot** poses.
5. **Coxa-showcase behaviors** (shake-off, rear-wiggle, scratch).
6. **Tail + head-pan** when ready (spare channels) → real wag + head expression.
7. (Later, per Future Directions §5) **active IMU balance** on top.

---

## Sources (verified 2026-06)

- **Maes et al. (2008)**, "Steady locomotion in dogs…," *J. Exp. Biol.* 211:138 — dog footfall timing;
  **walk DF > 0.5, trot DF ≤ 0.5** across 0.4–10 m/s.
  [journals.biologists.com](https://journals.biologists.com/jeb/article/211/1/138/17472/)
- **Hildebrand** gait classification (duty factor + limb phase; lateral-sequence walk LH-LF-RH-RF at
  ~25% phase). [Cartmill et al. 2002, *Support polygons & symmetrical gaits*](https://www.originalwisdom.com/wp-content/uploads/bsk-pdf-manager/2019/10/Cartmill-et-al_2002_Support-polygons-and-symmetrical-gaits.pdf)
- **Fish et al. (2021)**, "A 60:40 split: differential mass support in dogs," *Anatomical Record* —
  **~60% fore / 40% rear** (30/30/20/20). [Wiley](https://anatomypubs.onlinelibrary.wiley.com/doi/10.1002/ar.24407)
- **Cavagna, Heglund & Taylor (1977)**, "Mechanical work in terrestrial locomotion," *Am. J. Physiol.*
  233 — **walk = pendulum/vault** (PE↔KE, ~65% recovery), **trot/run = bouncing spring-mass** (dogs in
  the study). [PubMed 411381](https://pubmed.ncbi.nlm.nih.gov/411381/)
- **Seyfarth et al.**, "Swing-leg retraction: a simple control model for stable running" — late-swing
  leg **retraction reduces foot-velocity vs. ground / softens landing / improves stability**.
  [ResearchGate](https://www.researchgate.net/publication/10697685_Swing-leg_retraction_a_simple_control_model_for_stable_running)
- Hindlimb angulation (standing **stifle & hock ~30° to vertical**, femur ~90° to pelvis):
  [Determination of the Stifle Angle at Standing Position in Dogs (PMC9697634)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9697634/) ·
  [German-shepherd conformation & posture, *Sci. Reports* 2020](https://www.nature.com/articles/s41598-020-73550-x)
- Fischer & Lilje (2011) *Dogs in Motion* — definitive dog limb kinematics / swing trajectories
  (monograph; consult for paw-path detail). Robotics naturalness: Raibert, *Legged Robots That Balance*;
  Lasseter (1987, SIGGRAPH) on anticipation / follow-through / asymmetry.

---

## License

MIT License - See [LICENSE](../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
