# 靈巧手 compact — controlled print package

Manifest revision **`hand-compact-V1`**. The human-scale instance of the same hand as V3:
four fingers in a row and an opposed thumb, three single-axis phalanges per finger closed by
**one tendon**, meant to be worn inside two gloves with air pushed between them by a syringe
once the finger has closed on something. It is not a redesign of V3 — it is the same
generator fed a smaller link (`CompactHingeLinkSpec`: 2 mm pin, no bearings, 1.5 mm tendon
bore), and the moment arms it recovers by being smaller are what buy back joint sequencing
that V3 had to hand to its springs.

**No physical print has been made yet — of V1, V2, V3 or this one.** Every number below is
measured from the mesh. Nothing here is a strength, retention, grip-force or release claim,
and the pneumatic interlayer has never been built at all.

This package shipped on 2026-09-09 after the three renders beside it passed the user's
Lane B look (does it read as a hand, does the grip posture make sense, is the syringe
reachable). That is the only human judgement in it; everything else is machine-measured.

## Files

| File | What it is |
|---|---|
| **`phalanx_base_mm.stl`** | The proximal phalanx, 17.0 × 15.0 × 53.0 mm, tendon bore at the 5.5 mm moment arm. One per chain — five prints |
| **`phalanx_distal_mm.stl`** | The middle and distal phalanx, same 17.0 × 15.0 × 53.0 mm envelope, tendon bore at the 3.6 mm arm. Two per chain — ten prints |
| `palm_mm.stl` | The plate with five knuckle roots, the thenar boss, five tendon channels, the cuff clamp groove and the air port — 110.0 × 30.0 × 90.5 mm |
| `finger_compact_mm.stl` | One assembled finger, 17.0 × 15.0 × 149.0 mm, for checking fit before committing to fifteen parts |
| `hand_compact_mm.stl` | The whole hand assembled, 110.0 × 30.1 × 234.5 mm. It fits a 256 mm bed, but it is a reference, not a print — the joints are modelled closed |
| `hand_compact.blend` | The Blender source these were exported from |
| `compact_assembly.png`, `compact_joint_detail.png`, `compact_print_layout.png` | The three renders the Lane B verdict was given on |

Fifteen phalanges in all, two part numbers: five of `phalanx_base_mm.stl` and ten of
`phalanx_distal_mm.stl`. The two differ only in where the tendon bore sits; the outside is
the same, so a base printed as a distal will assemble and then close in the wrong order.
Mark them.

## Printing

Bambu Lab P2S, bed 256 mm. Units mm, 100%, **auto-arrange off** — the layout is already
nested and fits one plate at 191.0 × 90.5 mm — four parts, the loose finger's three
phalanges laid flat and the palm.

This link is tighter than V3's everywhere: 1.2 mm minimum wall, 0.2 mm printed radial
clearance on a 2 mm pin, 1.36 mm per side left for the interlayer against V3's 1.70. Print
`phalanx_base_mm.stl` first, once, and measure it against `docs/hand-v3/v6b-coupon.md`
before printing fifteen — the bands are derived from the link, so
`scripts/analyse_coupon.py --instance hand-compact` judges the readings against this link,
not V3's.

## What is verified, and what is not

Verified by machine, on the real Blender the files were generated in (contracts
`scripts/verify/contracts/hand_compact.json`, 20 checks, and `hand_compact_finger.json`,
14 checks; both run in `scripts/ci.sh --real`, and the shipped STLs are re-derived and
compared triangle for triangle on every real run):

- Every part watertight, zero non-manifold edges, one shell each.
- The finger's three units share exactly two meshes — two part numbers, declared by the
  instance and checked on the scene, not assumed from the generator.
- Each tendon bore's centre sits on its joint's moment arm, measured by ray: 5.5 mm in the
  base, 3.6 mm in the distal.
- Both bores are open and the axis between them is solid; the wiring runs dorsally,
  mirrored from the tendon.
- No interference between any two digits at rest: all ten cross-digit pairs measured on the
  real mesh, zero overlapping faces. The first placement of this thumb failed exactly this
  check — a straight thumb brushed the third finger by eight faces — which is why the
  offline placement model now refuses a thumb whose rest clearance is not positive. At rest
  the straight thumb clears the nearest finger by 3.48 mm.
- No interference across a joint's full ±50° travel, and the finger's closure trajectory
  is measured against the plan's.
- The print plate is 191.0 × 90.5 mm against a 256 mm bed, measured down two independent
  paths and required to agree.
- The palm is a single connected solid; all five tendon channels and the air port are
  genuinely open, with material confirmed present before the claim.
- The thumb can reach the index fingertip: closest approach 1.1 mm against a 15.0 mm
  contact distance. A thumb left flat in the finger row gives 24.0 mm.

**Not verified, and not claimable from anything here:** grip force, friction, whether it
prints, whether a 2 mm pin at 0.2 mm clearance turns once printed, and every property of
the pneumatic interlayer. Those need a physical bench, and the protocol for one is in
`docs/hand-v3/v6-scripts.md`.

## Attribution

InMoov is consulted as a dimensional reference and printed separately as a test bed; see
`NOTICE`. None of its geometry is in this package — everything here is generated from
`scripts/model_hand_compact.py`, which reads the registered instance and nothing else.
