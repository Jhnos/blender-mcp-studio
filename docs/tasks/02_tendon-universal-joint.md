# Biaxial-root hollow hinge with retained PINs — V6

**Status:** AWAITING-ACCEPTANCE

## Goal and context

One repeatable body with orthogonal side hinges, an open sensor-wire centre and roots that
widen in both principal directions. The same body supports either a print-in-place captive
PIN or separately printed grooved PIN plus C clip. Read `AGENTS.md`, the project Skill and
the [artifact workflow](../verification/generated-artifacts.md). [V5 history](../archive/tendon-hinge-v5.md)
is superseded, not the current dimensional contract.

## Current specification

- Disc Ø36 × 4 mm; complete body 36 × 36 × 29.6 mm; 19 mm pitch.
  Nine bodies / eight alternating joints span 188 mm in the straight assembly.
- Centre Ø10 mm; four Ø2.4 mm tendon holes at diagonal positions, radius 13 mm.
- Ear OD 10.6 mm; Ø4.5 mm running bores; three-stage roots widen axially and tangentially.
  Measured root slopes are 36.6071° / 35.8377° / 35.8377°, under the 45° target.
- PIP coupon: two bodies and two interleaved Ø4 mm double-headed captive PINs.
- Separate coupon: two bodies, two Ø4 mm headed/grooved PINs and two 0.9 mm C clips.
  The same recessed Ø6.6 mm retainer seats accept both workflows.
- All exported STL coordinates are millimetres. These are prototype geometries, not
  certified bearings, retainers or load-bearing components.

## Hand-off

### Verified facts

- Frozen pure `BiaxialHingeSpec` extends the reusable V5 specification without importing
  Blender. Body construction accepts an injected spec; retention geometry and presentation
  are separate Blender adapter modules.
- Real Blender generated all body, PIN, clip, coupon, `.blend` and PNG artifacts. Independent
  STL readback reports body 36 × 36 × 29.6 mm, grooved PIN 6 × 6 × 9.2 mm, clip
  5.6967 × 6 × 0.9 mm, PIP coupon 48.6 × 36 × 36 mm and separate coupon 82 × 48 × 29.6 mm.
- Nine straight and nine bent bodies have zero adjacent surface intersections. Fifteen
  single-joint samples from −34° through +34° also have zero surface intersections.
- All 45 centre/tendon rays are clear. Sixteen captive PINs are inside radius
  6.8–15.2971 mm and have zero initial body overlap.
- Split hardware is inside radius 5.8–15.2971 mm; eight neutral body–hardware pairs have
  zero surface overlap. Four ±1 mm withdrawal samples produce positive stop overlap,
  proving the checker reaches both retention geometries without claiming holding force.
- MCP readiness for the three-body, PIP and split layouts returns `review`, no structural
  errors and no truncation. Thin-wall and overhang findings remain visible for slicer review.
- Visual evidence and rubric live in [biaxial-hinge-v6.md](../verification/biaxial-hinge-v6.md).
  A fresh-context reviewer passed final items A–I after three bounded evidence rounds.
  Generated outputs live under ignored `tmp/biaxial-hinge-v6/`.
- `scripts/ci.sh --real` passed T1 static, T2 Python/Web tests and all T3 real-machine
  REST, MCP, readiness and batch-transform checks without skipped tiers.
- Five verified STL files and the complete `.blend` source are promoted into
  [`models/biaxial-hinge-v6/`](../../models/biaxial-hinge-v6/) with a generated SHA-256,
  byte-length, triangle-count and millimetre-dimension manifest. A package test re-reads
  every committed binary; arbitrary `tmp/`, backup, log and render files remain excluded.

### Open failures and limitations

- No physical print, slicer support decision, dimensional-fit, breakaway, retention-force,
  fatigue, cable swept-volume or motorized test has been performed.
- The PIP coupon has 0.25 mm radial shaft clearance and 0.3 mm retainer clearance; actual
  release depends on printer/process calibration. Do not auto-arrange its four shells.
- The printed C clip is only 0.9 mm thick and is experimental. It is not a rated spring,
  safety retainer or substitute for a metal clip under load.
- MCP thin-wall is an approximate face sample and reports warnings on bodies/hardware;
  readiness does not certify strength, retention or slicer support strategy.
- Sampled collision and displaced-stop checks are discrete surface tests, not continuous
  collision detection or force analysis.

### Next step

Merge [PR #4](https://github.com/Jhnos/blender-mcp-studio/pull/4), download the controlled package and import one coupon at 100% millimetres into the slicer.
First print the six-part separate
coupon to tune bore/PIN/clip fit without trapping material; then print the PIP coupon with
joint axes vertical and supports chosen manually. Record actual clearance, release and clip
survival before scaling to the nine-body chain or applying motor load.

Run all artifact commands sequentially. For Blender's metre-based scene import STL at scale
0.001, or open `biaxial_hinge_v6.blend`; do not shrink the exported STL.
