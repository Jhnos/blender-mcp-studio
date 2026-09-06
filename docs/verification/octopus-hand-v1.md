# Octopus hand V1 — target, evidence and manufacturing limits

Five V6 biaxial arms on a pentagonal palm, printed in one piece with the cables threaded
afterwards. Read [generated-artifacts.md](generated-artifacts.md) for the workflow and
[biaxial-hinge-v6.md](biaxial-hinge-v6.md) for the arm's own dimensional contract — this
document only covers what the hand adds.

## What it is

| | |
|---|---|
| Palm | Regular pentagon, 6 mm thick, 126.8 × 120.6 mm as exported |
| Arms | Five, each 5 bodies on a Ø36 mm V6 profile, 19 mm pitch |
| Joints | Five per arm — four between bodies plus one where the palm socket carries the first body |
| Cables | Four Ø2.4 mm tendon holes per arm, 20 in total, at radius 13 mm about each arm axis |
| Wiring | One Ø10 mm channel on the palm axis, 18.1 mm clear of the nearest tendon hole |
| Tip | Four cross-drilled Ø3 mm eyelets over the tendon exits, one 14 mm claw leaning 40° inward |
| Whole hand | 126.774 × 120.570 × 113.800 mm, 104 642 triangles |

The palm's top face is treated as a body centre plane. That is the whole trick: the socket
carries the same male ears any body carries on its +Z face, so V6's `create_body` is reused
without modification and the arm gains a base joint for free.

## Print pose

Arms **upright**, palm flat on the bed. Splayed flat the hand needs Ø275.9 mm and does not
fit a 220 mm bed; upright it needs 133.3 mm square by the spec's conservative bound, and
126.8 × 120.6 mm as actually exported. `OctopusHandSpec` rejects any variant whose upright
envelope exceeds `max_bed_mm`, so the bed is a machine-checked invariant, not a note.

Upright also puts V6's three-stage roots (36.6° / 35.8° / 35.8°, all under 45°) back in the
orientation they were designed for, and keeps the claw's 40° lean self-supporting.

**The open question this pose creates:** the pin axes become horizontal, so the Ø4.5 mm
bores print as bridges and the captive pins have an unsupported crown. That is the opposite
of the orientation `biaxial-hinge-v6.md` recommends for the PIP coupon. Nothing in software
can answer it — it is the first thing the physical print must settle.

## Machine evidence (2026-09-06, real Blender)

Two contracts, both green with no skips:
`scripts/verify/contracts/octopus_hand.json` and `octopus_hand_tips.json`.

| Claim | Evidence |
|---|---|
| Arm chain twists correctly | rotations `(90, 0, 90, 0)` on arm 1; tips `(90, 162, 234, 306, 18)` |
| Bodies share one mesh | `shared_mesh_count = 1` for both the 20 plain bodies and the 5 tips |
| No collision inside an arm | 5 per-arm groups, 4 objects each, all adjacent overlaps 0 |
| **No collision between arms** | `HH_OCT_SEG_` group of 20 sorted level-by-level: 19 adjacent pairs, all 0 |
| Tips clear each other | `HH_OCT_TIP_` group of 5, 4 adjacent pairs, all 0 |
| Joint articulates | sweep −34°…+34°, 15 samples, 0 overlap — run for the plain body and again for the tip |
| Wire channel open | palm centre ray misses (`center_ray_hit = false`) |
| Cable path open through the tip | tip centre ray misses after the eyelet bosses were unioned on |
| Tip features really applied | `arm_tip_mm.stl` 5140 triangles against the plain body's 3436 |
| Readiness complete | `status = review`, no forbidden structural code, **not truncated** |

Independent STL readback (no Blender): palm 10 222 triangles at 126.774 × 120.570 × 18.800 mm;
arm body 3436 at 36 × 36 × 29.6 mm; tip 5140 at the same envelope; whole hand 104 642 at
126.774 × 120.570 × 113.800 mm.

## Fresh-context visual rubric

Judge these against the generated PNGs, not against this text.

- **A** Palm is a regular pentagon with an arm station at each of the five vertices.
- **B** Every station shows the three-stage sloped root fused into the palm, not floating on it.
- **C** Twenty tendon holes are visible, four grouped about each arm axis at equal radius.
- **D** One central channel is open through the palm and clear of every tendon hole.
- **E** Each arm shows five bodies with alternating joint axes up its length.
- **F** A captive pin is seated at every joint, including the base joint at the palm.
- **G** Each tip carries four eyelet bosses, each cross-drilled and sitting over a tendon exit.
- **H** Each claw rises from the rim and leans toward the palm axis, not sideways or outward.
- **I** No arm touches its neighbour anywhere along its length.
- **J** The print layout view shows three distinct parts: palm, plain body, tip.

## Evidence boundaries

- No physical print, slicer support decision, dimensional-fit, release, grip-force,
  retention, cable-tension or fatigue test has been performed. Every dimension here is a
  fit-coupon dimension; nothing is a rated mechanical claim.
- The claw is an experimental hook. It is not a rated gripper, and the 0.9 mm-class printed
  features inherited from V6 are not rated retainers.
- Readiness reports 92 thin-wall and 4603 overhang sampled faces as warnings across the three
  parts. Those are for slicer and physical review; the check does not certify strength or a
  support strategy.
- Collision testing is discrete surface overlap in the neutral pose plus a single-joint sweep.
  It is not continuous collision detection, and it does not cover the fully curled hand.
- The inter-arm group's adjacency pairs cover arms 1↔2, 2↔3, 3↔4 and 4↔5 at each level. The
  5↔1 pair is not compared directly; the arms are identical on a regular pentagon, so it is
  covered by symmetry rather than by measurement.
- The palm↔first-body joint is not in any adjacency group. Its clearance is inferred from the
  same joint geometry the sweep exercises, not measured in place.
- The tip body keeps V6's unused male ears on its top face. They are harmless and pin-free,
  but they add height and a snag edge; trimming them is a V2 change.
- STL carries no unit metadata. Keep mm and 100% in the slicer; import at scale 0.001 into a
  metre-based Blender scene, or open the `.blend`.
