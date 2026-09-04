# Reusable generated-artifact verification

This local engineering workflow is independent of the MCP host. It does not add a public
arbitrary-code tool or bypass application services for the public readiness check.

## Run

With Blender addon :9876 and API :19505 connected, from the repository root:

```bash
$HOME/miniconda3/envs/blender-mcp/bin/python \
  scripts/verify/generated_artifact_verify_real.py \
  scripts/verify/contracts/inset_hinge.json

$HOME/miniconda3/envs/blender-mcp/bin/python \
  scripts/verify/generated_artifact_verify_real.py \
  scripts/verify/contracts/inset_hinge_pins.json --skip-generate

$HOME/miniconda3/envs/blender-mcp/bin/python \
  scripts/verify/mesh_probe_verify_real.py \
  scripts/verify/contracts/inset_hinge_probe.json
```

The default run regenerates task-owned objects and outputs, then verifies them. Use
`--skip-generate` only to inspect an already generated scene and existing files. Success
returns 0; missing artifacts, collisions, incomplete evidence or service failures fail loud.
The final stdout line is JSON and can be archived with normal terminal log capture.

Run sequentially, after `scripts/ci.sh --real` finishes. Shared scene selection means serialized
socket requests do not lock the entire generate → select → MCP → assess transaction.

V5 outputs: `tmp/inset-hinge-v5/` contains the nine-module `.blend`, body/pin/coupon `.stl`,
detail/top PNGs, assembly PNG, bent PNG and three-orientation layout PNG. Generated files are ignored
by Git; source, tests and the JSON contract are committed. Keep the STL units as millimetres.
The STL is a prototype for slicer/fit review, not a manufacturing-approved part.

STL has no unit metadata: keep mm/100% in slicers; import with scale 0.001 into a metre-based
Blender scene, or open the `.blend`. The V5 coupon contains two bodies and two headed pins;
the pin is 6 × 6 × 9.2 mm overall, not a 6 mm shaft. Shaft diameter is 4 mm. See the
[V5 target and retention limits](inset-hinge-v5.md) before trial printing.

The V4 contract remains available as `hollow_side_hinge.json`, with outputs in
`tmp/hollow-side-hinge/`. Running either generator replaces task-owned `HH_` scene objects;
saved output files for the other version are retained.

## Module ownership

| Module | Responsibility |
|---|---|
| `src/core/domain/hollow_side_hinge.py` | Immutable dimensions and geometric constraints |
| `src/core/domain/inset_hinge.py` | In-disc roots and printed split-pin dimensions |
| `scripts/model_inset_hinge.py` | V5 body and printable pin assembly |
| `scripts/blender_mesh_primitives.py` | Shared material, cylinder, boolean and cleanup primitives |
| `scripts/inset_hinge_presentation.py` | V5 close-up, top view and fit-coupon layout |
| `scripts/model_hollow_side_hinge_chain.py` | Assemble the model from the specification |
| `scripts/hollow_hinge_geometry.py` | Watertight D-lug and bridge primitives |
| `scripts/hollow_hinge_render.py` | Three views, spaced layout and saved-camera restoration |
| `scripts/blender_artifact_export.py` | Explicit-mesh STL export in mm; restore selection/visibility |
| `src/verification/generated_artifact_contract.py` | Contract parsing and evidence assessment |
| `src/verification/artifact_files.py` | Binary STL length/coordinate validation without Blender |
| `src/verification/mesh_measurements.py` | Fail-closed dimensions, slopes, bores and pin evidence |
| `scripts/verify/mesh_probe_verify_real.py` | JSON-driven read-only geometry measurements |
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
