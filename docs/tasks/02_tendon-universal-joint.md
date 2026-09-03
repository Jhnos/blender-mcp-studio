# Short hollow alternating-axis tendon hinge chain

**Status:** AWAITING-ACCEPTANCE

## Goal

Deliver one short, hollow, repeatable module with side-mounted serviceable hinges.
Nine identical modules form eight alternating X/Y joints; the exact centre remains
available for sensor wiring. Generation, export and verification must be reusable modules.

## Context to read

1. `AGENTS.md` and the project `blender-mcp-studio` Skill.
2. This task and [generated-artifact workflow](../verification/generated-artifacts.md).
3. V1/V2/V3 are superseded design history in git, not active specifications.

## V4 specification

- One printable annular body: 28 mm body diameter, 10.4 mm body length, 20 mm pitch.
  Including ears, the single mesh bounds are approximately 35 × 42.2 × 28.6 mm.
  Nine straight modules span 188.6 mm along Z.
- Central through-bore Ø10 mm; four quarter-turn-invariant diagonal tendon bores Ø2.4 mm
  at radius 9.5 mm. Rotations are 0/90/0/90/0/90/0/90/0 degrees.
- Two separate side pins per joint, nominal Ø4 mm; printed bores Ø4.5 mm and optional
  MR84 4×8×3 bearing seats Ø8.1 mm. Pins never cross the central axis.
- Side male/female lug centres are 16/19.5 mm from the axis, with 0.4 mm axial running
  clearance. Lug outside diameter is 19.8 mm; load bridges are 2.4 × 4 mm.
- Bridge placement is derived from a ±34-degree motion envelope with 0.05 mm design
  margin. Four joints per plane give a 136-degree algebraic sum, not a guaranteed tip angle.
- Four tendon lines couple eight joint coordinates; four cable directions are not eight
  independently actuated degrees of freedom. No actuator or inverse-kinematics claim.
- Standard pins/bearings and coloured wire routes are concept visualization, not parts
  to include in the printable STL. No automatic mesh repair or material-strength claim.

## Acceptance checks

- Pure immutable specification and contract tests pass; malformed/truncated evidence fails.
- One command generates the .blend, single-module STL and three PNGs, then performs the
  independent Blender oracle and public MCP readiness call.
- Nine objects share one mesh; the centre ray is unobstructed; straight and displayed bent
  adjacent pairs do not overlap. A single joint passes all 15 samples from −34° to +34°.
- Binary STL is independently readable and reports expected millimetre-scale dimensions.
- Independent visual rubric A–I checks nine modules, open centre, split pins, X/Y alternation,
  four tendons, bent preview, uncropped print views, labels and contrast.
- Slicer inspection and a physical fit coupon are required before manufacturing acceptance.

## Hand-off

### Verified facts

- V3 is sealed in `15e54e4`; the user requested shorter, hollow modules and moved the hinge
  hardware out of the centre. V4 retains only one repeated printable part type.
- `HollowSideHingeSpec` is framework-free. Blender geometry, presentation and STL export
  live in separate helpers; the generic contract/assessment layer does not import `bpy`.
- Focused tests: 14 domain + 16 artifact/verification/render-state tests pass. RED evidence
  included missing domain/contract modules, bridge envelope, missing STL, absent motion
  samples, invalid/truncated readiness, and camera-state leakage.
- Real contract verification passed: nine same-mesh objects, expected rotations and axis
  names, clear centre ray, eight zero-overlap straight pairs, eight zero-overlap bent pairs,
  and 15 zero-overlap single-joint angle samples from −34° to +34°.
- Public MCP readiness on three layout orientations: 9,588 triangles, no non-manifold,
  inconsistent-normal, degenerate, zero-volume or intersection issue; no truncation.
- Independent visual rubric A–I passed. All three final views show complete outlines.
- Independent STL readback: 3,196 triangles and 35 × 42.2 × 28.6 mm dimensions.
- Durable local outputs are in `tmp/hollow-side-hinge/` (Git-ignored). Older system-/tmp
  outputs and the user's copied .blend were not deleted.
- Final `scripts/ci.sh --real` passes every T1 static/build, T2 Python/Web and T3 real
  REST/MCP/readiness/batch gate. The domain-purity sentinel and both TDD ratchets pass.
- The final reproducible run, including STL readback and sampled motion, is recorded in
  `tmp/hollow-side-hinge/verification.log`. No test or real tier was skipped.

### Open failures / limits

- Readiness is still `review`: 882 approximate thin-wall samples and 1,548 overhang samples
  across the three orientations. Do not label this print-ready without slicer review.
- The motion oracle checks adjacent mesh surfaces and 15 discrete single-joint poses, not
  continuous collision detection, all non-adjacent link pairs, pin/bearing clearances under
  load, cable swept volume, fatigue, backlash, friction or guaranteed 136-degree tip travel.
- Central-axis ray clearance does not certify every bent cable diameter or bend radius.
- Physical M4/MR84 fit, print orientation, supports and retention hardware remain untested.
- After a user closes Blender, the API can retain a stale connection. Start Blender, confirm
  :9876 readiness, then reinstall/restart API through launchd before real checks.
- The historical Tailnet gateway 502 and FileProvider-derived backups are outside this
  mechanical slice; no external-URL recovery claim is made here.

### Next step

Inspect the single-module STL in the intended slicer, then print two modules as a hinge/
M4/MR84 fit coupon. Adjust tolerances through the specification and rerun the same contract;
do not rewrite the verification harness or freeze manufacturing dimensions yet.
