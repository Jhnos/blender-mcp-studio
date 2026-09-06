# Octopus hand V1 — controlled print package

Version-controlled manufacturing files. Working output under `tmp/octopus-hand-v1/` stays
reproducible and is not source-controlled; these are the copies with recorded checksums.

**No physical print has been made yet.** Every number below is measured from the mesh, not
from a printed part. Nothing here is a strength, retention, grip-force or release claim.

## Print this one first

| File | Use |
|---|---|
| **`test_coupon_mm.stl`** | **Start here.** Ø48 mm palm chunk, two bodies, four captive pins — 47.8 × 48.0 × 56.8 mm, 7 shells |
| `octopus_hand_v1_mm.stl` | The whole hand, print-in-place — 144.4 × 138.5 × 117.0 mm, 76 shells |
| `palm_mm.stl` | Palm alone, for inspection |
| `arm_body_mm.stl` | One repeated body, grip pads included |
| `arm_tip_mm.stl` | One terminal tip with its faceted cap |
| `octopus_hand_v1.blend` | Editable Blender source and the complete assembly |

The coupon exists because the whole hand is 117 mm tall with twenty-five live joints, and
the one question no software check can settle costs a night to answer on the hand and an
hour on the coupon: printed arm-up the pin axes go horizontal, so the Ø4.5 mm bores become
bridges and the captive pins get an unsupported crown. The coupon carries a base joint
(tangential pin), a body-to-body joint (radial pin) and a grip pad, so both pin headings
and the pad's 45° chamfer are in it.

## Slicer contract

- Coordinates and dimensions are millimetres. Import at **100% in mm** — STL carries no unit
  metadata, so do not let the slicer guess.
- **Do not auto-arrange the shells.** These are print-in-place assemblies: 76 shells on the
  hand, 7 on the coupon. Auto-arrange scatters them and destroys the assembly.
- Print **arm-up, palm flat on the bed**. That is the pose the V6 roots' 36.6° / 35.8° /
  35.8° slopes and the grip pads' 45° chamfers were designed for.
- Support strategy is a manual decision. Readiness reports thin-wall and overhang warnings
  for slicer and physical review; it does not choose supports for you.
- Into a metre-based Blender scene, import STL at scale 0.001, or open the `.blend`.

## What was verified, and by what

- `manifest.json` records SHA-256, byte length, triangle count and millimetre dimensions,
  read back from the binaries by an independent parser that does not use Blender.
- Contracts `scripts/verify/contracts/octopus_hand.json` and `octopus_hand_tips.json` pass on
  real Blender with no skips: per-arm and inter-arm collision, tip-to-tip clearance, a
  −34°…+34° joint sweep, open wire channel, open cable path through the tip, and an
  untruncated print-readiness report.
- Full evidence and the ten-item visual rubric: [`docs/verification/octopus-hand-v1.md`](../../docs/verification/octopus-hand-v1.md).

## What is not verified

No print, no fit, no release, no grip force, no cable tension, no fatigue. The visual rubric
has not been judged by a fresh reviewer yet. See the task hand-off in
[`docs/tasks/04_octopus-hand-v1.md`](../../docs/tasks/04_octopus-hand-v1.md) for the full list.
