# Octopus hand V2 — target, evidence and manufacturing limits

V2 changes the palm and where the grip pads sit. Everything else is V1's, and V1's own
package is untouched — see [octopus-hand-v1.md](octopus-hand-v1.md) for the arm, the
joints and the cable scheme, and [biaxial-hinge-v6.md](biaxial-hinge-v6.md) for the
hinge underneath both.

## What it is

| | |
|---|---|
| Palm | Regular pentagon turned so a **corner stands on each arm**, corners cut back 3.0 mm to flats, both rims chamfered 1.5 mm at 45°. 116.618 × 122.619 × 18.800 mm |
| Stems | One buttress per arm, radius 48.0 → 60.0 mm, 8.0 → 1.2 mm tall, ramp at 29.5° |
| Wiring | Central Ø10 channel **plus one Ø6 bore per arm** at palm radius 30.0 mm |
| Grip pads | Four, on the **cardinals** — every body presents one to the palm centre |
| Tip | V1's faceted cap, flare raised 3.0 → 4.0 mm (see "the graze" below) |
| Whole hand | 119.442 × 124.934 × 118.000 mm, 131 824 triangles, 76 shells |
| Bed | Declared 256 mm (Bambu Lab P2S). Upright footprint 129.342 mm, set by the **arms**, no longer by the plate |

## Why the plate got smaller and deeper at the same time

A corner reaches further from the axis than an edge does. With an edge facing each arm,
the plate had to reach `station + envelope + wall` **along the heading itself**. With a
corner facing each arm, the two edges either side only have to clear the socket at
`pi / 5` off the heading, so the station's contribution is its projection onto the edge
normal:

```
V1   inradius = 41.5·cos(0°)  + 17.920 + 2.0 = 61.420   across corners 151.840
V2   inradius = 41.5·cos(36°) + 17.920 + 2.0 =  53.495   across corners 126.516
```

Material behind a socket went from 2.000 mm — exactly one wall — to 3.703 mm after the
truncation is paid for, and that surplus is what the stem is built from.

## Machine evidence (2026-09-07, real Blender)

Two contracts, both green with no skips: `scripts/verify/contracts/octopus_hand_v2.json`
and `octopus_hand_v2_tips.json`.

| Claim | Evidence |
|---|---|
| One arm is four bodies from one mesh | `object_count = 4`, `shared_mesh_count = 1` — the cardinal pad set survived the twist, so no second master |
| The chain alternates its joints | `rotations_deg = (0, 90, 0, 90)`; tips at `(0, 72, 144, 216, 288)` |
| Arms do not touch, within or across | six collision groups, `adjacent_overlap_pairs` all `0`, including the 20-body umbrella |
| The joint clears through its whole travel | 15 sampled angles −34…+34, `overlap_pairs` all `0` |
| Tips do not touch each other | `HH_OCT2_TIP_` group, 5 objects, overlaps `0` |
| The palm's wire channel is open | `center_ray_hit = false` on `HH_OCT2_PALM` |
| The tip's cable path is open | `center_ray_hit = false` on `HH_OCT2_TIP_1` |
| All five per-arm wire bores are open | `bore_ray_hits = [false, false, false, false, false]` — one ray per bore, and a short list fails closed |
| The readiness verdict is complete | `status = review`, `analysis_truncated = false`, no forbidden code |
| Every body aims a pad at the palm | ray along the inward heading hits **21.000 mm** on all ten bodies of arms 1 and 3, twists 0/90/144/234 — pad face, not the 18.0 mm bare disc |
| Aiming is the roomier placement | full-travel pad-to-pad clearance measured on real V1 geometry: **0.204 mm** diagonal, **0.553 mm** cardinal |
| The cardinals were never occupied out at the rim | ear and root reach 16.70 mm on a cardinal; the pad's buried face starts at 17.20 mm |
| The stem stays under the swinging arm | swept floor has a throat near radius 60 (4.07 mm of headroom above the plate); the ramp's worst margin is **2.87 mm** |
| All three masters are watertight | 0 boundary edges, 0 non-manifold edges on palm, body and tip |

Independent STL readback (no Blender): palm 11 494 triangles 116.618 × 122.619 × 18.800 mm;
body 3408, 42.000 × 42.000 × 29.600; tip 3514, 42.000 × 42.000 × 33.800; whole hand
131 824, 119.442 × 124.934 × 118.000; coupon 11 894, 45.623 × 48.000 × 56.800. The same
triangle counts came out of macOS and Windows builds.

## The graze, and the empty exports

Two defects were found and fixed while building V2. Both are recorded here because both
are latent in code V1 also uses.

**`export_stl_mm` did not restore `hide_render`.** Generators hide their master bodies
before exporting them, and the STL exporter honours that flag, so `arm_body_mm.stl`,
`arm_tip_mm.stl` and `test_coupon_mm.stl` were written as 84-byte, zero-triangle files —
valid STLs containing nothing. Held everything else constant on Blender 5.2.1: one
876-face body exported 84 bytes with `hide_render = True` and 168 984 with it clear.
V1's own unmodified generator reproduces the empty files on that Blender; the files
shipped in `models/octopus-hand-v1/` were built on one that did not do this. Fixed at the
chokepoint, and an export that writes no triangles now raises.

**A 45° cap flare grazes the disc rim.** With `tip_cap_flare_mm = 3.0` the flare's
run equals its rise, so the cap's radius at the trim plane is exactly the disc's radius,
and the cap surface touches the trimmed rim edge instead of crossing it. The next Boolean
opened 12 boundary edges at the cap's facet corners, and the four tendon drills turned
those into 204 non-manifold edges. Measured, everything else fixed:

| `tip_cap_flare_mm` | flare slope | cap radius at trim plane | disc rim | boundary edges |
|---|---|---|---|---|
| 3.0 | 45.0° | 18.000 | 18.0 | 12 |
| 3.5 | 41.6° | 17.889 | 18.0 | 0 |
| 4.0 | 38.7° | 17.800 | 18.0 | 0 |

V1 survives it only because its diagonal pads happen to bury four of the six facet corners
in solid material. That is luck, and it ran out when the pads moved. V2 uses 4.0 and the
spec now rejects a flare that grazes.

## Fresh-context visual rubric

Judged four times, each round by a reviewer given only the renders — no filenames, no
captions, no documentation. The in-scene captions were blanked and the files renamed and
shuffled before each round, because a caption reading "buttress ramping outward" hands the
reviewer the answer to the item asking whether there is one.

- **A** The plate is a pentagon whose five corners are cut back to short flats — no sharp points.
- **B** An arm stands on each of the five corners, not midway along the edges.
- **C** Both the top and the bottom rim carry their own angled face, not a square corner.
- **D** A tapered rib runs outward from each socket and ramps down to the plate.
- **E** Twenty small holes, in five groups of four at equal radius about each arm's axis.
- **F** Five larger holes, one per arm, inboard of its socket and distinct from the twenty.
- **G** One hole at the plate's centre, larger than the twenty.
- **H** Each arm is five stacked bodies, the topmost ending in a faceted cone.
- **I** Each body carries four rim pads, one of which points at the plate's centre.
- **J** The pads' top edge is chamfered rather than square.
- **K** ~~Nothing on the plate intersects anything else.~~ **Withdrawn before round two.** It
  asks a reviewer to certify a global absence of modelling error from shaded renders, and
  the eye is the wrong instrument for it. Mesh validity is measured directly and
  completely: 0 boundary edges and 0 non-manifold edges on all three masters, and a
  readiness report carrying no `intersections` code.

### Result — four rounds, zero FAIL

| Item | round 1 (11 views) | round 2 (13) | round 3 (14) | round 4 (16) |
|---|---|---|---|---|
| A B D E F G | PASS | PASS | PASS | PASS |
| H | UNCLEAR | PASS | PASS | PASS |
| C | UNCLEAR | UNCLEAR | PASS | UNCLEAR |
| I | UNCLEAR | PASS | UNCLEAR | PASS |
| J | PASS | PASS | UNCLEAR | UNCLEAR |

**No reviewer, in any round, marked any item FAIL.** Nobody ever saw something wrong; the
disagreements are only about what can be confirmed from a shaded render.

Round one exposed a defect in the *renders*, not the model: the underside view was an empty
grey frame, because the camera sat below a 300 mm floor plane that occluded the plate. Round
two added the missing views for H and I. Round three added the rim-from-below view that
finally showed the bottom chamfer, and round four added a frame holding one body and the
plate's centre hole together, which settled I.

**C, I and J stopped converging.** Round three fixed C and lost I; round four fixed I and
lost C. That oscillation is the signature of an item sitting at the resolution limit of the
medium, not of an unstable model — so those three are recorded against measurement instead,
and no further renders were made for them. Reframing until a judge happens to agree would be
fitting the exam, not the part.

| Item | What the eye could not settle | What measures it |
|---|---|---|
| C | whether the *bottom* rim has its own face | the plate's outline has four rings — z = −4.000 and +2.000 at radius 61.7305, z = −2.500 and +0.500 at 63.2579. Two chamfers, each rising 1.500 mm over a 1.5274 mm run, symmetric top to bottom |
| I | which pad faces the palm | a ray along the inward heading hits pad face at **21.000 mm** on all ten bodies of arms 1 and 3, twists 0/90/144/234 — the bare disc would read 18.0 |
| J | a 0.6 mm chamfer on a 42 mm part | the pad's rim has two levels, z = 4.000 at corner radius 22.5089 and z = 3.400 at 23.1709: a real 0.6 mm face, not a corner |

The chamfer is 0.6 mm because it is subtracted from the gripping face and the face is the
point. It was not enlarged to make the rubric pass.

## Evidence boundaries

- **No physical print exists**, of V1 or V2. No fit, release, grip force, cable tension or
  fatigue result is claimed.
- Printed arm-up the pin axes go horizontal, so the Ø4.5 bores become bridges and the
  captive pins get an unsupported crown. Only a print answers that.
- The stem's clearance to the swinging arm is a conservative analytic bound taken on the
  arm's centreline, sampled discretely; the Blender sweep measures body against body, not
  body against stem.
- Collision sampling is discrete, not continuous, and measures surface overlap only.
- The palm ↔ first-body gap is in no collision group; the 5↔1 arm pair has no direct
  comparison and relies on the pentagon's symmetry. Both inherited from V1.
- Grip pads are contact **area**. Total flat face is 312 mm² against V1's 355 — 12% less —
  in exchange for 79% of it facing the grasp where V1 had none. No force is claimed.
- Readiness reports 430 thin-wall and 3972 overhang sampled faces as warnings, for slicer
  and physical review. Neither strength nor a support strategy is certified.
- STL files carry no units. Import at 100% in millimetres.
