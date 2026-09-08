# 靈巧手 V3 — controlled print package

Manifest revision **`hand-V3`**. An anthropomorphic hand: four fingers in a row and an
opposed thumb, three single-axis phalanges per finger closed by **one tendon**, meant to
be worn inside two gloves with air pushed between them by a syringe once the finger has
closed on something.

**No physical print has been made yet — of V1, V2 or V3.** Every number below is measured
from the mesh. Nothing here is a strength, retention, grip-force or release claim, and
the pneumatic interlayer has never been built at all.

V1 and V2 are different machines, not earlier drafts of this one, and both are shipped
untouched beside it.

## Files

| File | What it is |
|---|---|
| **`phalanx_mm.stl`** | **The part you print most.** One phalanx, 24.0 × 22.0 × 67.0 mm. Four per finger, three for the thumb — nineteen in all, and all one part number |
| `palm_mm.stl` | The plate with five knuckle roots, the thenar boss, five tendon channels, the cuff clamp groove and the air port — 140.0 × 44.0 × 90.0 mm |
| `finger_v3_mm.stl` | One assembled finger, for checking fit before committing to nineteen parts |
| `hand_v3_mm.stl` | The whole hand assembled, 140.0 × 44.1 × 319.5 mm — **too tall for a 256 mm bed on purpose.** It is a reference, not a print |
| `finger_v3.blend` | The Blender source these were exported from |

## Printing

Bambu Lab P2S, bed 256 mm. Units mm, 100%, **auto-arrange off** — the layout is already
nested and fits one plate at 182.5 × 100.5 mm.

Print `phalanx_mm.stl` first, once. Check the pin bore and the bearing seat before
committing to nineteen of them.

## What is verified, and what is not

Verified by machine, on the real Blender the files were generated in:

- Every part watertight, zero non-manifold edges.
- The four units of a finger share one mesh — one part number, not four.
- Each tendon bore's centre sits on its joint's moment arm, measured by ray.
- No interference between any two fingers at rest, and none across a joint's full
  ±50° travel.
- The palm is a single connected solid; all five tendon channels and the air port are
  genuinely open, with material confirmed present before the claim.
- The thumb can reach the index fingertip: closest approach 18.2 mm against a 22.0 mm
  contact distance. A thumb left flat in the finger row gives 29.9 mm.

**Not verified, and not claimable from anything here:** grip force, friction, whether it
prints, whether the joints move once printed, and every property of the pneumatic
interlayer. Those need a physical bench, and the protocol for one is in
`docs/hand-v3/v6-scripts.md`.

## Attribution

InMoov is consulted as a dimensional reference and printed separately as a test bed; see
`NOTICE`. None of its geometry is in this package — everything here is generated from
`scripts/model_finger_v3.py`.
