# Octopus hand V2 — controlled print package

Manifest revision **`octopus-hand-V2.1`**. The first V2 shipped a six-sided cap that met
two of the four grip directions on a corner; the cap is now eight-sided and turned half a
facet, so every direction meets a flat face. Nothing else about the geometry moved. The
earlier bits keep the name `octopus-hand-V2` and stay in git history — neither has been
printed.

Version-controlled manufacturing files. Working output under `tmp/octopus-hand-v2/` stays
reproducible and is not source-controlled; these are the copies with recorded checksums.
V1 is untouched and still shipped beside this, in `models/octopus-hand-v1/`.

**No physical print has been made yet — of V1 or of V2.** Every number below is measured
from the mesh, not from a printed part. Nothing here is a strength, retention, grip-force
or release claim.

## What changed from V1, and what it cost

| | V1 | V2 |
|---|---|---|
| Pentagon phase | corners 18° off every arm | **a corner on each arm** |
| Plate across corners | 151.8 mm | **126.5 mm** |
| Material behind a socket | 2.0 mm (one wall) | **3.7 mm**, plus an 8 mm buttress |
| Grip pads | four diagonals, none aimed | **four cardinals, one aimed per body** |
| Tip cap | six sides, two grip directions on a corner | **eight sides turned 22.5°, a face down every direction** |
| Pad-to-pad clearance at full travel | 0.204 mm | **0.553 mm** |
| Wiring to a finger | central Ø10 channel only | **+ one Ø6 bore per arm** |
| Square edges on the plate | top rim, bottom rim, five points | **none — 1.5 mm 45° chamfers, corners cut back** |
| Declared bed | 220 mm | **256 mm** (Bambu Lab P2S) |
| Whole hand | 144.4 × 138.5 × 117.0 mm | **119.4 × 124.9 × 118.0 mm** |

The plate got smaller *and* deeper behind each socket because a corner reaches further
than an edge: with a corner on the arm, the two edges either side only have to clear the
socket at 36° off the heading rather than along it.

## Print this one first

| File | Use |
|---|---|
| **`test_coupon_mm.stl`** | **Start here.** Palm chunk, two bodies, four captive pins — 45.6 × 48.0 × 56.8 mm, 7 shells |
| `octopus_hand_v2_mm.stl` | The whole hand, print-in-place — 119.4 × 124.9 × 118.0 mm, 76 shells |
| `palm_mm.stl` | Palm alone, for inspection — 116.6 × 122.6 × 18.8 mm |
| `arm_body_mm.stl` | One repeated body, aimed grip pads included — 42.0 × 42.0 × 29.6 mm |
| `arm_tip_mm.stl` | One terminal tip with its eight-sided cap, turned so a flat face meets each grip direction — 42.0 × 42.0 × 33.8 mm |
| `octopus_hand_v2.blend` | Editable Blender source and the complete assembly |

The coupon exists because the whole hand is 118 mm tall with twenty-five live joints, and
the one question no software check can settle costs a night to answer on the hand and an
hour on the coupon: printed arm-up the pin axes go horizontal, so the Ø4.5 mm bores become
bridges and the captive pins get an unsupported crown. The coupon carries a base joint
(tangential pin), a body-to-body joint (radial pin), a grip pad and a stem, so both pin
headings and the new plate features are in it.

## Slicer contract

- Coordinates and dimensions are millimetres. Import at **100% in mm** — STL carries no
  unit metadata, so do not let the slicer guess.
- **Do not auto-arrange the shells.** These are print-in-place assemblies: 76 shells on the
  hand, 7 on the coupon. Auto-arrange scatters them and destroys the assembly.
- Print **arm-up, palm flat on the bed**. That is the pose the V6 roots' slopes, the grip
  pads' 45° undersides and the plate's 45° bottom chamfer were designed for.
- Support strategy is a manual decision. Readiness reports 430 thin-wall and 3972 overhang
  sampled faces for slicer and physical review; it does not choose supports for you.
- Into a metre-based Blender scene, import STL at scale 0.001, or open the `.blend`.

## What was verified, and by what

- `manifest.json` records SHA-256, byte length, triangle count and millimetre dimensions,
  read back from the binaries by an independent parser that does not use Blender.
- Contracts `scripts/verify/contracts/octopus_hand_v2.json` and `octopus_hand_v2_tips.json`
  pass on real Blender with no skips: per-arm and inter-arm collision, tip-to-tip
  clearance, a −34°…+34° joint sweep, an open wire channel, **all five per-arm wire bores
  open end to end**, an open cable path through the tip, and an untruncated
  print-readiness report.
- Every body presents pad material at radius 21.000 mm along the direction to the palm
  centre — measured by ray on the built scene, not inferred from the pad angles.
- Full evidence: [`docs/verification/octopus-hand-v2.md`](../../docs/verification/octopus-hand-v2.md).

## What is not verified

No print, no fit, no release, no grip force, no cable tension, no fatigue. The visual
rubric has not been judged by a fresh reviewer yet. See the task hand-off in
[`docs/tasks/05_octopus-hand-v2.md`](../../docs/tasks/05_octopus-hand-v2.md) for the full list.
