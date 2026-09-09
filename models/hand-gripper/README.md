# 靈巧手 gripper — controlled print package

Manifest revision **`hand-gripper-V1`**. The three-station instance of the same hand as V3
and compact: a two-finger row and an opposed thumb, three single-axis phalanges per digit
closed by **one tendon**. It is not a redesign — it is the same generator fed the same
compact link (`CompactHingeLinkSpec`: 2 mm pin, no bearings, 1.5 mm tendon bore) with the
finger row set to two instead of four.

That one change is the reason this instance exists. The row count had only ever been built
at four, and the compact hand's thumb placement does not survive the narrower plate: its
offset cantilevers the thenar boss past a plate half its width, and the spec refuses it.
The placement here came out of a fresh sweep, and it is deliberately not the sweep's best
point — scored on clearance alone the leaders all sat at the edge of the swept range, which
says more about the scoring than the hand. This is the placement whose whole neighbourhood
is also a hand.

**No physical print has been made yet — of V1, V2, V3, compact or this one.** Every number
below is measured from the mesh. Nothing here is a strength, retention, grip-force or
release claim, and the pneumatic interlayer has never been built at all.

This package shipped on 2026-09-09 after the three renders beside it passed the user's
Lane B look (does it read as something that could grip, is the thumb where it should be).
That is the only human judgement in it; everything else is machine-measured.

## Files

| File | What it is |
|---|---|
| **`phalanx_base_mm.stl`** | The proximal phalanx, 17.0 × 15.0 × 53.0 mm, tendon bore at the 5.5 mm moment arm. One per chain — three prints |
| **`phalanx_distal_mm.stl`** | The middle and distal phalanx, same 17.0 × 15.0 × 53.0 mm envelope, tendon bore at the 3.6 mm arm. Two per chain — six prints |
| `palm_mm.stl` | The plate with three knuckle roots, the thenar boss, three tendon channels, the cuff clamp groove and the air port — 56.0 × 30.0 × 80.5 mm |
| `finger_gripper_mm.stl` | One assembled digit, 17.0 × 15.0 × 149.0 mm, for checking fit before committing to the whole set |
| `hand_gripper_mm.stl` | The whole gripper assembled, 82.2 × 30.3 × 224.5 mm. It fits a 256 mm bed, but it is a reference, not a print — the joints are modelled closed |
| `hand_gripper.blend` | The Blender source these were exported from |
| `gripper_assembly.png`, `gripper_joint_detail.png`, `gripper_print_layout.png` | The three renders the Lane B verdict was given on |

Nine phalanges in all, two part numbers: three of `phalanx_base_mm.stl` and six of
`phalanx_distal_mm.stl`. The two differ only in where the tendon bore sits; the outside is
the same, so a base printed as a distal will assemble and then close in the wrong order.
Mark them.

## Printing

Bambu Lab P2S, bed 256 mm. Units mm, 100%, **auto-arrange off** — the layout is already
nested and fits one plate at 137.0 × 80.5 mm — four parts, the loose digit's three
phalanges laid flat and the palm.

The link is the compact one, so the tolerances are the compact ones: 1.2 mm minimum wall,
0.2 mm printed radial clearance on a 2 mm pin. Print `phalanx_base_mm.stl` first, once, and
measure it against `docs/hand-v3/v6b-coupon.md` before printing the rest — the bands are
derived from the link, so `scripts/analyse_coupon.py --instance hand-gripper` judges the
readings against this link, not V3's.

## What is verified, and what is not

Verified by machine, on the real Blender the files were generated in (contracts
`scripts/verify/contracts/hand_gripper.json`, 20 checks, and `hand_gripper_finger.json`,
14 checks; both run in `scripts/ci.sh --real`, and the shipped meshes are re-derived and
compared triangle for triangle on every real run):

- Every part watertight, zero non-manifold edges, one shell each.
- The digit's three units share exactly two meshes — two part numbers, declared by the
  instance and checked on the scene, not assumed from the generator.
- Each tendon bore's centre sits on its joint's moment arm, measured by ray: 5.5 mm in the
  base, 3.6 mm in the distal.
- Both bores are open and the axis between them is solid; the wiring runs dorsally,
  mirrored from the tendon.
- No interference between any two digits: all three cross-digit pairs measured on the real
  mesh, zero overlapping faces. At rest the straight thumb clears the nearer finger by
  3.04 mm.
- No interference across a joint's full ±50° travel, with zero overlapping faces at every
  step.
- The print plate is 137.0 × 80.5 mm against a 256 mm bed, measured down two independent
  paths and required to agree.
- The palm is a single connected solid; all three tendon channels and the air port are
  genuinely open, with material confirmed present before the claim.
- The thumb can reach the index fingertip: closest approach 1.8 mm against a 15.0 mm
  contact distance. A thumb left flat in the finger row gives 16.0 mm.
- Rebuilt four times in the live Blender, only the distal phalanx moved, and by two
  triangles — inside the budget the differential allows.

**Not verified, and not claimable from anything here:** grip force, friction, whether it
prints, whether a 2 mm pin at 0.2 mm clearance turns once printed, and every property of
the pneumatic interlayer. Those need a physical bench, and the protocol for one is in
`docs/hand-v3/v6-scripts.md`.

## Attribution

InMoov is consulted as a dimensional reference and printed separately as a test bed; see
`NOTICE`. None of its geometry is in this package — everything here is generated from
`scripts/model_hand_gripper.py`, which reads the registered instance and nothing else.
