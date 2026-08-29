# Four-DOF tendon universal-joint concept

**Status:** ACTIVE

## Goal

Create one parametric, FDM-conscious vertebra part that can be printed repeatedly. Three
identical vertebrae must form two two-axis interfaces, four rotational axes, and four
continuous tendon routes without a second printable part type.

## Context to read

1. `AGENTS.md`
2. `.agents/skills/blender-mcp-studio/SKILL.md`
3. This task only; historical feature plans are not design input.

## Specification

- One interface provides X and Y ball-socket rotation; two interfaces provide four joint axes.
- Every vertebra has one upper male ball/neck and one lower Y-split female snap socket. The
  three assembly objects must share one mesh data block to prove one repeatable part type.
- Four tendon guides are placed symmetrically around the centerline and remain identifiable
  through all repeated vertebrae.
- Generate an assembly view plus side/top/bottom views of the repeated part. Keep dimensions
  in millimetres and name every component deterministically.
- This is a concept prototype, not a load-certified final actuator. Record assumptions visibly.

## Acceptance checks

- The generator has pure parameter validation tests and fails on unprintable clearances.
- The Blender scene contains three same-mesh vertebrae, four named hinge axes, and four
  tendon paths.
- A rendered image makes the mechanism and hole routing legible.
- Print-readiness or explicit separated-part checks identify remaining review items honestly.
- Human acceptance is required before final STL export dimensions are frozen.

## Hand-off

### Verified facts

- The original two-part design was sealed in `6841cd7`, then superseded by the user's
  one-repeatable-part requirement.
- The new RED failed because `TendonVertebraSpec` did not exist. After explicitly re-recording
  the changed product contract at RED, 9 focused tests passed and the ratchet stayed green.
- `TendonVertebraSpec` is an immutable domain value object: 3 units, 2 interfaces, 4 DOF,
  one printable part type, 10.0 mm ball and 10.6 mm socket at 0.3 mm radial clearance.
- Blender 5.1 executed `scripts/model_tendon_joint.py` through the addon socket and saved
  `/tmp/blender-mcp-tendon-joint/tendon_joint_4dof.blend`.
- Independent Blender oracle observed 3 `TJ_PRINTABLE_VERTEBRA_*` objects sharing one mesh,
  four named axes (`J1_X`, `J1_Y`, `J2_X`, `J2_Y`), and four tendon guides.
- The public local Streamable HTTP MCP endpoint exposed the exact nine-tool catalog and
  successfully called `check_print_readiness` against three views of the shared mesh.
- Removing the whole-part bevel cleared all non-manifold and intersection findings. The final
  MCP report completed without truncation: 3 objects, 8,448 triangles, approximately
  36,238 mm³ aggregate volume and 15,070 mm² aggregate area.
- Visual evidence is generated at
  `/tmp/blender-mcp-tendon-joint/tendon_joint_4dof_assembly.png` and
  `/tmp/blender-mcp-tendon-joint/tendon_joint_4dof_print_layout.png`.
- A fresh-context verifier passed all seven one-part visual targets: no separate cross part,
  male ball and Y-split female socket visible, four holes and tendons, four labeled axes,
  complete text, uncropped separation, and sufficient contrast.
- `scripts/ci.sh --real` passed T1/T2 plus the real REST nonce, MCP protocol nonce,
  print-readiness fixtures, and one-Undo batch oracle after the one-part redesign.

### Open failures

- Print-readiness remains `review`: the approximate ray check reports 225 sampled thin-wall
  faces and the 45° profile reports 1,289 overhang faces across three display orientations.
  The ball underside and female spherical cavity need slicer-support planning.
- The Tailnet gateway returned HTTP 502 during this run while the local identity-protected
  MCP endpoint and Blender socket were healthy. This did not block the local public MCP
  protocol proof, but remote routing still needs an independent service check.
- The external DDD purity sentinel passes the new `tendon_joint.py` in isolation but finds
  seven pre-existing violations in four unchanged domain modules. They remain outside this
  mechanical-concept slice and are not hidden by the green project CI result.

### Next step

- Get human acceptance on the one-part ball-socket mechanism and 42 mm body diameter. If
  accepted, freeze the print orientation/support strategy, run a physical tolerance coupon,
  and export the single repeated vertebra STL.
