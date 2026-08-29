# Four-DOF tendon universal-joint concept

**Status:** AWAITING-ACCEPTANCE

## Goal

Create a parametric, FDM-conscious Blender concept for two repeated two-axis joint cells.
The assembly must visibly provide four rotational axes and four continuous tendon routes.

## Context to read

1. `AGENTS.md`
2. `.agents/skills/blender-mcp-studio/SKILL.md`
3. This task only; historical feature plans are not design input.

## Specification

- One cell provides orthogonal X and Y hinge axes; two cells provide four joint axes.
- Show male trunnions, female snap yokes, printable clearances, mechanical stops, and rounded
  load-bearing transitions.
- Four tendon guides are placed symmetrically around the centerline and remain identifiable
  through the repeated cells.
- Generate both an articulated assembly view and a print-layout view from one parameterized
  Blender script. Keep dimensions in millimetres and name every component deterministically.
- This is a concept prototype, not a load-certified final actuator. Record assumptions visibly.

## Acceptance checks

- The generator has pure parameter validation tests and fails on unprintable clearances.
- The Blender scene contains two cells, four named hinge axes, and four tendon paths.
- A rendered image makes the mechanism and hole routing legible.
- Print-readiness or explicit separated-part checks identify remaining review items honestly.
- Human acceptance is required before final STL export dimensions are frozen.

## Hand-off

### Verified facts

- `TendonJointSpec` is an immutable domain value object; the RED test failed with
  `ModuleNotFoundError`, then 8 focused tests passed without weakening the recorded tests.
- Blender 5.1 executed `scripts/model_tendon_joint.py` through the addon socket and saved
  `/tmp/blender-mcp-tendon-joint/tendon_joint_4dof.blend`.
- Independent Blender oracle observed 5 printable parts, four named axes
  (`J1_X`, `J1_Y`, `J2_X`, `J2_Y`), and four tendon-guide objects as specified.
- The public local Streamable HTTP MCP endpoint exposed the exact nine-tool catalog and
  successfully called `check_print_readiness` against the five separated layout objects.
- The final MCP report completed without truncation: 5 objects, 12,832 triangles,
  146 × 102 × 36.4 mm layout bounds, approximately 37,789 mm³ volume and 16,910 mm² area.
- Visual evidence is generated at
  `/tmp/blender-mcp-tendon-joint/tendon_joint_4dof_assembly.png` and
  `/tmp/blender-mcp-tendon-joint/tendon_joint_4dof_print_layout.png`.
- The third fresh-context visual verifier passed all seven written targets: part count,
  four axis meanings, four tendon paths, complete labels, separated layout, no cropping,
  and sufficient feature contrast.
- `scripts/ci.sh --real` passed T1/T2 plus the real REST nonce, MCP protocol nonce,
  print-readiness fixtures, and one-Undo batch oracle.

### Open failures

- Print-readiness remains `review`: the tip female snap reports one approximate triangle
  intersection and one sampled wall below 0.8 mm.
- The 45° FDM profile reports 1,254 sampled overhang faces. The middle double-yoke disc
  needs slicer support in this one-piece concept; a split-shell variant is not implemented.
- The Tailnet gateway returned HTTP 502 during this run while the local identity-protected
  MCP endpoint and Blender socket were healthy. This did not block the local public MCP
  protocol proof, but remote routing still needs an independent service check.
- The external DDD purity sentinel passes the new `tendon_joint.py` in isolation but finds
  seven pre-existing violations in four unchanged domain modules. They remain outside this
  mechanical-concept slice and are not hidden by the green project CI result.

### Next step

- Get human acceptance on the mechanism shape and overall 42 mm diameter. If accepted,
  create a new RED test for the chosen tip-snap fix and decide between support-required
  one-piece middle disc or a support-free split-shell variant before exporting STL.
