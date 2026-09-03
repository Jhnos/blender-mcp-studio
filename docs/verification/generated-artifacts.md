# Reusable generated-artifact verification

This local engineering workflow is independent of the MCP host. It does not add a public
arbitrary-code tool or bypass application services for the public readiness check.

## Run

With Blender addon :9876 and API :19505 connected, from the repository root:

```bash
$HOME/miniconda3/envs/blender-mcp/bin/python \
  scripts/verify/generated_artifact_verify_real.py \
  scripts/verify/contracts/hollow_side_hinge.json
```

The default run regenerates task-owned objects and outputs, then verifies them. Use
`--skip-generate` only to inspect an already generated scene and existing files. Success
returns 0; missing artifacts, collisions, incomplete evidence or service failures fail loud.
The final stdout line is JSON and can be archived with normal terminal log capture.

Outputs: `tmp/hollow-side-hinge/` contains the nine-module `.blend`, one printable module
`.stl`, assembly PNG, bent PNG and three-orientation layout PNG. Generated files are ignored
by Git; source, tests and the JSON contract are committed. Keep the STL units as millimetres.
The STL is a prototype for slicer/fit review, not a manufacturing-approved part.

## Module ownership

| Module | Responsibility |
|---|---|
| `src/core/domain/hollow_side_hinge.py` | Immutable dimensions and geometric constraints |
| `scripts/model_hollow_side_hinge_chain.py` | Assemble the model from the specification |
| `scripts/hollow_hinge_geometry.py` | Watertight D-lug and bridge primitives |
| `scripts/hollow_hinge_render.py` | Three views, spaced layout and saved-camera restoration |
| `scripts/blender_artifact_export.py` | Explicit-mesh STL export in mm; restore selection/visibility |
| `src/verification/generated_artifact_contract.py` | Contract parsing and evidence assessment |
| `src/verification/artifact_files.py` | Binary STL length/coordinate validation without Blender |
| `scripts/verify/generated_artifact_verify_real.py` | Sequential addon oracle and public MCP orchestration |
| `scripts/verify/contracts/*.json` | Per-model paths, names and expected observations |

## Add another repeated-joint model

1. Write a failing specification or artifact-contract test first.
2. Reuse geometry/render/export helpers where their geometry applies; keep new mechanical
   rules in an immutable specification. Do not copy the socket/MCP verifier.
3. Add a JSON contract: generator/reload paths, artifacts, expected object count and
   rotations, scene-list metadata, centre probe, collision groups and readiness selection.
4. Optional `joint_sweep` describes a master object, local Z pivot offset, bend axis,
   mating Z twist and explicit angle samples. It constructs temporary BMeshes only.
5. Run the same CLI, then obtain a fresh-context visual rubric on the actual output PNGs.
   The CLI does not replace visual inspection or claim that images were AI-graded.
6. Run `scripts/ci.sh --real` before committing the completed slice.

## Evidence boundaries and safety

- Generation is trusted local developer code. Only the task's object prefix is regenerated;
  unrelated scene objects are hidden temporarily for rendering and their visibility restored.
- The oracle reads world-space BMeshes, not local-space trees from separated objects.
  Collision groups compare adjacent objects in numeric-name order, not all pairs.
- The centre probe tests the master's local Z axis; it is not a volumetric cable-sweep test.
- Joint sweep is discrete surface-overlap testing; containment and between-sample contact
  are not certified. Bearing/pin graphics are outside the printable-mesh collision groups.
- Readiness deliberately selects/unhides only the configured generated layout prefix.
  Do not run this workflow concurrently with interactive edits or another Blender writer.
- Empty, invalid or truncated readiness cannot pass; configured structural issues fail.
  Thin-wall/overhang warnings remain visible and require slicer/physical review.
- STL carries no unit metadata. The exporter multiplies metre coordinates by 1000; the
  independent parser reports numeric extents under that mm contract, not encoded STL units.
