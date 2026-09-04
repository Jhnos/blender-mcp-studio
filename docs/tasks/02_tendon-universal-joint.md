# Reinforced in-disc hollow hinge — V5

**Status:** AWAITING-ACCEPTANCE

## Goal and context

One repeatable body with orthogonal front/rear side hinges, open centre, shallow reinforced
roots and printable pins. Read `AGENTS.md`, the project Skill and the
[artifact workflow](../verification/generated-artifacts.md).
[V4 history](../archive/tendon-hinge-v4.md) is superseded, not the current dimensional contract.

## Current specification

- Disc Ø34 × 4 mm; complete body 34 × 34 × 29.6 mm; 20 mm pitch.
  Nine bodies / eight joints span 189.6 mm in the straight assembly.
- Centre Ø10 mm; four Ø2.4 mm tendon holes at diagonal positions, radius 13 mm.
- Male/female centres 8 / 11.6 mm; ears 3 mm thick; axial running clearance 0.6 mm.
- Foot flares in both directions at 38.66° to the disc face; tangential gussets at 34.99°.
  Vertical ear sidewalls remain above the sloped foot.
- Plain Ø4.5 mm bores; printed shaft Ø4, head Ø6 × 1.6, total length 9.2 mm.
  Print 9 bodies + 16 pins for the full chain: one body type and one pin type.
- No bearing seats. Metal pins/bearings need a separate interface revision.
- Four tendons couple eight joint coordinates, not eight independent actuators.
  Four joints per plane have a 136° algebraic sum, not guaranteed tip travel.

## Hand-off

### Verified facts

- Frozen pure `InsetHingeSpec`; V4/V5 share extracted mesh primitives, rendering, export,
  socket/MCP verification and STL parsing. New generic mesh probes use JSON contracts.
- 11 new specification cases + 5 measured-evidence cases pass RED→GREEN; both ratchets
  confirm unchanged tests. Existing 30 geometry/artifact cases pass.
- Real Blender: nine bodies share one mesh; rotations alternate 0/90°; centre ray clear.
  Eight straight and eight bent adjacent pairs, plus 15 single-joint samples in ±34°,
  all have zero body surface overlap.
- Measured slopes: 38.6598° / 34.9920° / 38.6598°. All 45 hole rays clear.
  Sixteen pins against nine bodies (144 static pairs) have zero surface overlap.
  Pins occupy radial distances 5.8–15.2971 mm, inside the 17 mm disc radius.
- MCP body layouts: `review`, 60 approximate thin-wall and 1,573 overhang samples.
  Pin layouts: `ready`, no issues. Neither report has structural errors or truncation.
- STL readback: body 34 × 34 × 29.6 mm, pin 6 × 6 × 9.2 mm,
  two-body/two-pin coupon 78 × 45 × 29.6 mm. Coordinates are millimetres.
- Independent visual rubric A–H passed; [target](../verification/inset-hinge-v5.md).
  Assembly lower label slightly overlaps the lowest ear but remains readable; no cropping.
- Full `scripts/ci.sh --real` passed all T1/T2/T3 gates, no skipped tier.
- Outputs and reports: `tmp/inset-hinge-v5/`, Git-ignored. V4 output files remain intact.

### Open failures and limitations

- No physical print, slicer acceptance, load, fatigue or motorized test yet.
- Pins have heads but **no positive withdrawal retention**. Do not operate motors or load
  the chain before retention and fit acceptance. MCP `ready` is not mechanical certification.
- Body warnings need slicer review; geometry alone does not prove improved print strength.
- Motion checks are sampled adjacent-body surface tests; hardware checks are static.
  No continuous collision, non-adjacent links or bent cable swept-volume certification.
- Initial CI/generation overlapped and contaminated selection. Those results were discarded;
  accepted runs were serialized. The workflow now explicitly documents transaction boundaries.
- Checkpoint task detection does not reliably recognize acceptance-pending status.
  Keep the real status above; verify the three hand-off buckets independently of C1.
- Extra whole-domain purity audit reports seven existing findings in unchanged command,
  pipeline, scene and session models; this is not a clean whole-domain claim. The new V5
  value object is checked separately. Broader model migration is outside this geometry slice.

### Next step

Import the body and pin STLs into the slicer as millimetres at 100%; first print two bodies
and two pins, inspect supports/bore fit, then design positive retention. The coupon STL is
four separate laid-out solids, not an assembled joint. For Blender's metre-based scene use
STL import scale **0.001**, or open `inset_hinge_v5.blend`; do not shrink the exported STL.

Run the artifact commands sequentially, never concurrently with real CI, another verifier
or interactive scene edits. Four-part coupon orientation still needs slicer/support review.
