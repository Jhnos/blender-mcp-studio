# Batch Transform and Productivity Design

**Status:** Approved on 2026-07-19  
**Scope:** WebUI batch scene editing, command palette, and operation status center  
**Principles:** DDD, SOLID, TDD, client-neutral application services, script-driven verification

## Purpose

Blender MCP Studio must let a user target multiple scene objects from the WebUI,
apply one incremental move/rotate/scale operation, and undo the whole change with
one Undo. The next productivity increment adds a curated command palette and a
shared operation status center so scene actions have consistent keyboard access,
progress, success, and failure feedback.

The backend capability is not owned by the WebUI. REST is the first delivery
adapter, while the application service and port remain reusable by MCP or another
host without importing HTTP or React concepts.

## Architecture Decision

Use a dedicated batch-transform application slice:

```text
WebUI -> REST router -> BatchTransformService -> SceneBatchCommandPort
                                              -> BlenderBatchTransformAdapter
```

The domain owns immutable request and receipt value objects. The service owns
validation and error translation. The Blender adapter owns Blender unit conversion
and the single-Undo operator. The REST router only maps transport values.

Rejected alternatives:

- Frontend fan-out through the existing single-object endpoint would permit
  partial failure, make several socket calls, and create several Undo steps.
- A generic execute-code endpoint would couple clients to Blender Python and
  weaken the typed security boundary.
- Adding batch methods to the existing scene command port would violate ISP;
  existing adapters and MCP hosts do not need the new command.

No tenth public MCP tool is added in this increment. The application contract is
client-neutral so a later delivery adapter can expose it without moving business
logic.

## Domain Contract

All domain types are frozen value objects and import only the standard library or
same-layer domain types.

```python
TransformDelta(
    translation_mm: Vector3,
    rotation_deg: Vector3,
    scale_percent: Vector3,
)

BatchTransformSpec(
    object_names: tuple[str, ...],
    delta: TransformDelta,
)

BatchTransformReceipt(
    object_names: tuple[str, ...],
    affected_count: int,
    message: str,
)
```

Validation invariants:

- One to 100 unique, non-empty object names.
- Every numeric component is finite.
- At least one delta component is non-zero.
- Translation is limited to plus or minus 100,000 mm per axis.
- Rotation is limited to plus or minus 3,600 degrees per axis.
- Scale is greater than -100% and no greater than 10,000% per axis.
- The complete target set is checked before mutation; a missing object rejects the
  complete request.

Transform semantics use Blender object transform channels:

```text
location += translation_mm / 1000
rotation_euler += radians(rotation_deg)
scale *= 1 + scale_percent / 100
```

This deliberately models incremental edits. It does not expose pivot mode,
world/local switching, keyframes, or absolute transforms.

## Blender Adapter and Undo

The adapter sends one generated, data-only payload to Blender. Object names are
serialized as data and never interpolated as executable source fragments.

The generated code registers one internal Blender operator with
`bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}` and invokes it with
`('EXEC_DEFAULT', True)` so the programmatic call explicitly enables its undo
transaction. Its execute method performs a
preflight over every object and scale factor before changing any transform. A
successful invocation therefore adds one Undo entry for the entire request.

The adapter does not use `bpy.ops.ed.undo_push`, which Blender documents as an
internal operation. Real-Blender verification is the authoritative gate for the
single-Undo behavior.

## REST Contract

```http
POST /api/scene/batch-transform
Content-Type: application/json
```

```json
{
  "object_names": ["CatBody", "CatTail"],
  "translation_mm": [10.0, 0.0, 0.0],
  "rotation_deg": [0.0, 0.0, 15.0],
  "scale_percent": [5.0, 5.0, 5.0]
}
```

```json
{
  "object_names": ["CatBody", "CatTail"],
  "affected_count": 2,
  "message": "Updated 2 objects"
}
```

- Domain or request validation failure: HTTP 422.
- Missing target objects: HTTP 422 with their names.
- Blender unavailable: HTTP 503.
- Existing scene and export contracts remain unchanged.

## Batch Editing UI

### Selection model

Each object row receives a labelled checkbox. A select-all checkbox supports the
checked, unchecked, and indeterminate states. Checked names form a frontend-local
batch target set; they do not silently change Blender's active object or global
selection. This distinction avoids a socket call for every checkbox and makes the
batch request independent of transient Blender selection.

When the scene list refreshes, names no longer present are pruned. Selection
survives panel rerenders and explicit refreshes when the object still exists.

### Transform workbar

The selected count opens a compact transform workbar below the list:

```text
+--------------------------------------------------+
| 8 selected                         Clear targets |
| [Move mm] [Rotate deg] [Scale %]                  |
| X [ 10.0 ]   Y [ 0.0 ]   Z [ 0.0 ]              |
| Reset                         Apply to 8 objects  |
+--------------------------------------------------+
```

The three segmented modes retain their independent X/Y/Z drafts. One Apply sends
all non-zero move, rotate, and scale deltas together. X, Y, and Z use restrained
red, green, and blue accents derived from Blender's axis vocabulary; text labels
remain present so color is never the only cue.

Apply is disabled when there are no targets, all values are zero, values are not
finite, or scale is outside the domain range. Failure preserves targets and draft
values. Success resets the deltas, preserves targets, refreshes the scene once,
and records `Updated N objects; Undo is available` in the operation center.

The panel stacks vertically at narrow widths, exposes visible focus rings, labels
every checkbox and number input, and links validation text with
`aria-describedby`.

## Command Palette

The command palette is a curated frontend registry, not a generic backend action
executor. Each `CommandDefinition` declares an id, title, keywords, availability
predicate, and run callback. Adding commands extends the registry without adding
branches to the palette component.

Initial commands:

- Refresh scene preview.
- Undo and redo.
- Select all batch targets.
- Clear batch targets.
- Open/focus batch transform.
- Focus the object list.
- Open Prepare for Slicing.
- Re-run print readiness.

`Cmd/Ctrl+K` opens the palette. Arrow keys move the active result, Enter executes,
and Escape closes. Global shortcuts do not run while focus is in an input,
textarea, select, or contenteditable element.

## Operation Status Center

A focused Zustand store owns at most five recent operations. Each record has a
stable id, label, status (`running`, `success`, or `error`), timestamp, optional
message, and an optional retry callback only when the originating operation is
idempotent.

The status center renders a compact current-status control and an accessible
recent-activity popover. It replaces component-local toast state in PreviewStage.
The store has no knowledge of REST response shapes and the command palette has no
knowledge of rendering.

## Error Handling

- Validation errors appear next to the relevant transform inputs.
- HTTP errors preserve the server detail message when safe and otherwise use a
  concrete recovery message.
- Network or Blender availability errors state that Blender must be connected and
  provide retry only for idempotent operations.
- Batch transform is not automatically retried because an ambiguous network
  failure could have changed Blender already.
- No exception is swallowed and no fallback reports success.

## Test Strategy

### Python unit and contract tests

- Frozen domain values and all numeric/name invariants.
- Service delegates through the narrow port and maps adapter failures.
- Adapter code serializes hostile names as data, uses one `UNDO` operator, converts
  millimetres/degrees/percent correctly, and preflights before mutation.
- REST returns 200, 422, and 503 with stable structured responses.
- Architecture tests preserve inward dependency direction and the nine-tool MCP
  catalog.

### Web tests

- Select all, clear, and indeterminate checkbox states.
- Missing scene objects are pruned from targets.
- All three unit modes retain drafts and map one request correctly.
- Invalid and all-zero drafts disable Apply.
- Success refreshes once and failure preserves inputs.
- Palette filtering and keyboard navigation.
- Editable targets suppress global shortcuts.
- Operation history is capped at five and retry is shown only when provided.

### Script-driven real verification

`scripts/verify/batch_transform_verify_real.py` creates two nonce-named objects,
applies one mixed transform through REST, verifies both objects through a separate
Blender query, calls one Undo, verifies both objects are restored, and cleans up in
a `finally` block. `scripts/ci.sh --real` invokes it after the existing real gates.

## Delivery Sequence

1. Commit this approved design and its implementation plans.
2. Commit domain, port, service, and RED-to-GREEN tests.
3. Commit Blender adapter, REST router, and contract tests.
4. Commit object targets and transform workbar with component tests.
5. Commit operation store and migrate existing feedback.
6. Commit command palette and keyboard tests.
7. Commit real-Blender verification and documentation/architecture updates.
8. Run `scripts/ci.sh` and `scripts/ci.sh --real`, audit every requirement, remove
   stale TODOs, and push the branch.

## Explicitly Deferred Scope

The approved scope does not include viewport gizmo dragging, pivot/orientation
modes, keyframes, absolute transforms, batch deletion/duplication, 3MF, automatic
mesh repair, or a tenth MCP tool. These are future product choices, not TODOs left
by this implementation.
