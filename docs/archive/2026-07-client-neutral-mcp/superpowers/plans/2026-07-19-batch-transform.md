# Batch Transform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add checkbox-based batch targets and one-operation incremental move, rotate, and scale with a single Blender Undo entry.

**Architecture:** Frozen domain values and `BatchTransformService` depend on the narrow `SceneBatchCommandPort`; a Blender adapter implements that port with one generated `UNDO` operator. A separate REST router delivers the use case, and the WebUI calls it through the MDR action registry.

**Tech Stack:** Python 3.11+, FastAPI, Blender 5.1 `bpy`, React 19, TypeScript 6, Zustand 5, Vitest, pytest.

## Global Constraints

- Follow inward dependencies: delivery -> use case -> domain <- adapter.
- Domain objects are frozen and import no third-party or outer-layer modules.
- Use RED -> GREEN -> REFACTOR; every production behavior first appears in a failing test.
- One batch request must create exactly one Blender Undo entry.
- Keep the MCP public catalog at nine tools.
- Use `scripts/ci.sh` as the only CI gate and `scripts/ci.sh --real` for real Blender proof.
- Do not add viewport gizmos, pivot modes, absolute transforms, batch delete/duplicate, 3MF, or automatic repair.

## File Structure

- `src/core/domain/batch_transform.py`: immutable values and validation invariants.
- `src/core/ports/batch_transform_port.py`: narrow incoming application protocol.
- `src/core/use_cases/batch_transform.py`: orchestration boundary.
- `src/adapters/batch_transform/blender_batch_transform.py`: Blender code generation and response parsing.
- `api/routers/batch_transform.py`: HTTP mapping only.
- `api/schemas.py`: batch request schema.
- `api/runtime.py`, `api/main.py`: composition-root wiring.
- `web/src/domain/batchTransform.ts`: frontend draft validation and request mapping.
- `web/src/stores/batchSelectionStore.ts`: target SSOT.
- `web/src/components/BatchTransformPanel.tsx`: transform workbar.
- `web/src/mdr/nodes/ObjectListNode.tsx`: checkbox list integration.
- `scripts/verify/batch_transform_verify_real.py`: nonce, oracle, Undo proof.

---

### Task 1: Domain and application contract

**Files:**
- Create: `tests/unit/core/test_batch_transform.py`
- Create: `src/core/domain/batch_transform.py`
- Create: `src/core/ports/batch_transform_port.py`
- Create: `src/core/use_cases/batch_transform.py`
- Modify: `src/core/domain/exceptions.py`

**Interfaces:**
- Consumes: no outer-layer types.
- Produces: `TransformDelta`, `BatchTransformSpec`, `BatchTransformReceipt`, `SceneBatchCommandPort.apply_transform()`, and `BatchTransformService.apply()`.

- [x] **Step 1: Write failing frozen-value and invariant tests**

```python
def test_batch_transform_values_are_frozen_and_incremental_request_is_valid():
    delta = TransformDelta(translation_mm=Vector3(10, 0, 0))
    spec = BatchTransformSpec(("A", "B"), delta)
    assert spec.object_names == ("A", "B")
    with pytest.raises(FrozenInstanceError):
        spec.object_names = ("C",)

@pytest.mark.parametrize("names", [(), ("",), ("A", "A")])
def test_batch_transform_rejects_invalid_targets(names):
    with pytest.raises(BatchTransformError):
        BatchTransformSpec(names, TransformDelta(translation_mm=Vector3(1, 0, 0)))

def test_batch_transform_rejects_zero_and_invalid_scale():
    with pytest.raises(BatchTransformError, match="non-zero"):
        BatchTransformSpec(("A",), TransformDelta())
    with pytest.raises(BatchTransformError, match="greater than -100"):
        TransformDelta(scale_percent=Vector3(-100, 0, 0))
```

- [x] **Step 2: Run tests and verify RED**

Run: `$HOME/miniconda3/envs/blender-mcp/bin/python -m pytest tests/unit/core/test_batch_transform.py -q`  
Expected: collection fails because `src.core.domain.batch_transform` does not exist.

- [x] **Step 3: Implement immutable values, protocol, and service**

```python
@dataclass(frozen=True, slots=True)
class TransformDelta:
    translation_mm: Vector3 = Vector3()
    rotation_deg: Vector3 = Vector3()
    scale_percent: Vector3 = Vector3()

@dataclass(frozen=True, slots=True)
class BatchTransformSpec:
    object_names: tuple[str, ...]
    delta: TransformDelta

@runtime_checkable
class SceneBatchCommandPort(Protocol):
    async def apply_transform(self, spec: BatchTransformSpec) -> BatchTransformReceipt: ...

class BatchTransformService:
    def __init__(self, commands: SceneBatchCommandPort) -> None:
        self._commands = commands

    async def apply(self, spec: BatchTransformSpec) -> BatchTransformReceipt:
        return await self._commands.apply_transform(spec)
```

Implement `__post_init__` checks for the exact limits in the design SSOT and add `BatchTransformError(SceneOperationError)`.

- [x] **Step 4: Run focused and contract tests GREEN**

Run: `$HOME/miniconda3/envs/blender-mcp/bin/python -m pytest tests/unit/core/test_batch_transform.py tests/unit/core/test_scene_operation_contracts.py -q`  
Expected: all tests pass.

- [x] **Step 5: Commit the application slice**

```bash
git add src/core/domain/batch_transform.py src/core/domain/exceptions.py src/core/ports/batch_transform_port.py src/core/use_cases/batch_transform.py tests/unit/core/test_batch_transform.py
git commit -m "feat(core): define batch transform use case"
```

---

### Task 2: Blender adapter and REST delivery

**Files:**
- Create: `tests/unit/adapters/test_blender_batch_transform.py`
- Create: `src/adapters/batch_transform/__init__.py`
- Create: `src/adapters/batch_transform/blender_batch_transform.py`
- Create: `tests/e2e/test_batch_transform_http.py`
- Create: `api/routers/batch_transform.py`
- Modify: `api/schemas.py`
- Modify: `api/runtime.py`
- Modify: `api/main.py`
- Modify: `tests/e2e/test_mcp_streamable_http.py`

**Interfaces:**
- Consumes: `SceneBatchCommandPort`, `BatchTransformSpec`, `BlenderPort.execute(Command)`.
- Produces: `BlenderBatchTransformAdapter.apply_transform()` and `POST /api/scene/batch-transform`.

- [x] **Step 1: Write failing adapter tests**

```python
@pytest.mark.asyncio
async def test_adapter_uses_one_undo_operator_and_serializes_names_as_data():
    blender = RecordingBlender(output={"affected_count": 2, "object_names": ["A", "B"]})
    adapter = BlenderBatchTransformAdapter(blender)
    receipt = await adapter.apply_transform(BatchTransformSpec(
        ("A", "B"),
        TransformDelta(Vector3(10, 0, 0), Vector3(0, 0, 90), Vector3(5, 0, 0)),
    ))
    code = str(blender.commands[0].arguments["code"])
    assert code.count("bpy.ops.blender_mcp.batch_transform") == 1
    assert "{'REGISTER', 'UNDO', 'INTERNAL'}" in code
    assert "math.radians" in code
    assert "10.0 / 1000.0" in code
    assert receipt.affected_count == 2

@pytest.mark.asyncio
async def test_adapter_keeps_hostile_object_name_in_json_payload():
    name = "x'); bpy.ops.wm.quit_blender(); #"
    blender = RecordingBlender(output={"affected_count": 1, "object_names": [name]})
    adapter = BlenderBatchTransformAdapter(blender)
    await adapter.apply_transform(BatchTransformSpec(
        (name,), TransformDelta(translation_mm=Vector3(1, 0, 0)),
    ))
    code = str(blender.commands[0].arguments["code"])
    payload_line = next(line for line in code.splitlines() if line.startswith("payload_json = "))
    assert name not in payload_line
    assert "base64.b64decode" in code
```

- [x] **Step 2: Run adapter tests and verify RED**

Run: `$HOME/miniconda3/envs/blender-mcp/bin/python -m pytest tests/unit/adapters/test_blender_batch_transform.py -q`  
Expected: collection fails because the adapter module does not exist.

- [x] **Step 3: Implement the adapter**

Generate one `execute_code` command. The operator must preflight all objects and
scale factors before its mutation loop, then print JSON with `affected_count` and
`object_names`. Parse that JSON through explicit mapping/list/string/integer
narrowing and raise `BatchTransformError` on malformed or failed results.

```python
class BlenderBatchTransformAdapter:
    def __init__(self, blender: BlenderPort) -> None:
        self._blender = blender

    async def apply_transform(self, spec: BatchTransformSpec) -> BatchTransformReceipt:
        command = Command("execute_code", {"code": _build_code(spec)})
        result = await self._blender.execute(command)
        if not result.success:
            raise BatchTransformError(result.error or "Batch transform failed")
        raw = _decode_receipt(result.output)
        return BatchTransformReceipt(
            tuple(_require_names(raw["object_names"])),
            _require_count(raw["affected_count"]),
            _require_message(raw["message"]),
        )
```

- [x] **Step 4: Write failing REST mapping tests**

```python
def test_batch_transform_endpoint_maps_units_to_shared_service():
    response = client.post("/api/scene/batch-transform", json={
        "object_names": ["A", "B"],
        "translation_mm": [10, 0, 0],
        "rotation_deg": [0, 0, 15],
        "scale_percent": [5, 5, 5],
    })
    assert response.status_code == 200
    assert service.specs[0].delta.rotation_deg.z == 15

def test_batch_transform_endpoint_maps_domain_and_connection_errors():
    assert domain_response.status_code == 422
    assert connection_response.status_code == 503
```

- [x] **Step 5: Run REST tests and verify RED**

Run: `$HOME/miniconda3/envs/blender-mcp/bin/python -m pytest tests/e2e/test_batch_transform_http.py -q`  
Expected: requests return 404 because the router is not registered.

- [x] **Step 6: Implement schema, router, and composition wiring**

```python
class BatchTransformRequest(BaseModel):
    object_names: list[str]
    translation_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale_percent: tuple[float, float, float] = (0.0, 0.0, 0.0)

@router.post("/api/scene/batch-transform")
async def apply_batch_transform(body: BatchTransformRequest, request: Request) -> dict[str, object]:
    service: BatchTransformService = request.app.state.batch_transform
    # Map transport tuples to Vector3 and return asdict(receipt).
```

Wire one adapter/service instance into frozen `AppRuntime`, `_publish_runtime_state`,
`create_app`, and the fake runtime factory. Do not alter the MCP catalog.

- [x] **Step 7: Run focused Python tests GREEN**

Run: `$HOME/miniconda3/envs/blender-mcp/bin/python -m pytest tests/unit/core/test_batch_transform.py tests/unit/adapters/test_blender_batch_transform.py tests/e2e/test_batch_transform_http.py tests/e2e/test_mcp_streamable_http.py -q`  
Expected: all tests pass and MCP still advertises nine tools.

- [x] **Step 8: Commit adapter and delivery**

```bash
git add src/adapters/batch_transform api src/core tests/unit/adapters/test_blender_batch_transform.py tests/e2e/test_batch_transform_http.py tests/e2e/test_mcp_streamable_http.py
git commit -m "feat(api): apply batch transforms with one undo"
```

---

### Task 3: Frontend target selection and request model

**Files:**
- Create: `web/src/domain/batchTransform.test.ts`
- Create: `web/src/domain/batchTransform.ts`
- Create: `web/src/stores/batchSelectionStore.test.ts`
- Create: `web/src/stores/batchSelectionStore.ts`
- Modify: `web/src/mdr/apiActions.test.ts`
- Modify: `web/src/mdr/apiActions.ts`

**Interfaces:**
- Consumes: MDR `dispatch` and the scene object names.
- Produces: `BatchTransformDraft`, `validateBatchTransform`, `toBatchTransformRequest`, and `useBatchSelectionStore`.

- [x] **Step 1: Write failing domain and store tests**

```typescript
it('maps retained drafts to one incremental request', () => {
  expect(toBatchTransformRequest(['A', 'B'], {
    translationMm: [10, 0, 0], rotationDeg: [0, 0, 15], scalePercent: [5, 5, 5],
  })).toEqual({
    object_names: ['A', 'B'], translation_mm: [10, 0, 0],
    rotation_deg: [0, 0, 15], scale_percent: [5, 5, 5],
  })
})

it('prunes targets absent from the refreshed scene', () => {
  useBatchSelectionStore.getState().replace(['A', 'B'])
  useBatchSelectionStore.getState().prune(['B', 'C'])
  expect(useBatchSelectionStore.getState().selectedNames).toEqual(['B'])
})
```

- [x] **Step 2: Run tests and verify RED**

Run: `cd web && npx vitest run src/domain/batchTransform.test.ts src/stores/batchSelectionStore.test.ts`  
Expected: imports fail because both modules are absent.

- [x] **Step 3: Implement request validation and selection SSOT**

```typescript
export type Vector3Tuple = [number, number, number]
export interface BatchTransformDraft {
  translationMm: Vector3Tuple
  rotationDeg: Vector3Tuple
  scalePercent: Vector3Tuple
}

export const useBatchSelectionStore = create<BatchSelectionState>((set) => ({
  selectedNames: [],
  toggle: (name) => set((state) => ({ selectedNames: toggleUnique(state.selectedNames, name) })),
  replace: (names) => set({ selectedNames: unique(names) }),
  clear: () => set({ selectedNames: [] }),
  prune: (available) => set((state) => ({ selectedNames: intersect(state.selectedNames, available) })),
}))
```

Keep the store independent of fetch, React components, and Blender state.

- [x] **Step 4: Register and test the MDR action**

```typescript
registerAction('scene.batch-transform', async (params, { base }) =>
  readJson(await fetch(`${base}/api/scene/batch-transform`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params),
  })),
)
```

Run: `cd web && npx vitest run src/domain/batchTransform.test.ts src/stores/batchSelectionStore.test.ts src/mdr/apiActions.test.ts`  
Expected: all tests pass.

- [x] **Step 5: Commit the frontend model**

```bash
git add web/src/domain/batchTransform.ts web/src/domain/batchTransform.test.ts web/src/stores/batchSelectionStore.ts web/src/stores/batchSelectionStore.test.ts web/src/mdr/apiActions.ts web/src/mdr/apiActions.test.ts
git commit -m "feat(web): model batch transform targets"
```

---

### Task 4: Checkbox list and transform workbar

**Files:**
- Create: `web/src/components/BatchTransformPanel.test.tsx`
- Create: `web/src/components/BatchTransformPanel.tsx`
- Create: `web/src/mdr/nodes/ObjectListNode.test.tsx`
- Modify: `web/src/mdr/nodes/ObjectListNode.tsx`
- Modify: `web/src/components/ui/icon-map.ts`

**Interfaces:**
- Consumes: `useBatchSelectionStore`, `toBatchTransformRequest`, MDR `dispatch`, and `triggerSceneRefresh`.
- Produces: accessible checkbox selection and the segmented incremental-transform workbar.

- [x] **Step 1: Write failing list interaction tests**

```typescript
it('supports select all, partial indeterminate state, and clear', async () => {
  render(<ObjectListNode dispatch={dispatch} />)
  await screen.findByText('Cube')
  await user.click(screen.getByRole('checkbox', { name: 'Select all objects' }))
  expect(screen.getByText('2 selected')).toBeInTheDocument()
  await user.click(screen.getByRole('checkbox', { name: 'Select Cube' }))
  expect(screen.getByRole('checkbox', { name: 'Select all objects' })).toHaveProperty('indeterminate', true)
})
```

- [x] **Step 2: Run list test and verify RED**

Run: `cd web && npx vitest run src/mdr/nodes/ObjectListNode.test.tsx`  
Expected: no target checkboxes are found.

- [x] **Step 3: Add labelled row and select-all checkboxes**

Use a checkbox ref to set `indeterminate`, stop row-click propagation, prune names
after each successful scene refresh, and render `BatchTransformPanel` when the
target count is non-zero.

- [x] **Step 4: Write failing workbar tests**

```typescript
it('sends all retained modes once and refreshes once', async () => {
  render(<BatchTransformPanel dispatch={dispatch} />)
  await user.type(screen.getByLabelText('Move X in millimetres'), '10')
  await user.click(screen.getByRole('tab', { name: 'Rotate deg' }))
  await user.type(screen.getByLabelText('Rotate Z in degrees'), '15')
  await user.click(screen.getByRole('button', { name: 'Apply to 2 objects' }))
  expect(dispatch).toHaveBeenCalledWith('scene.batch-transform', expect.objectContaining({
    translation_mm: [10, 0, 0], rotation_deg: [0, 0, 15],
  }))
  expect(triggerSceneRefresh).toHaveBeenCalledTimes(1)
})

it('preserves the draft when the request fails', async () => {
  dispatch.mockRejectedValueOnce(new Error('Blender is offline'))
  render(<BatchTransformPanel dispatch={dispatch} />)
  const moveX = screen.getByLabelText('Move X in millimetres')
  await user.type(moveX, '10')
  await user.click(screen.getByRole('button', { name: 'Apply to 2 objects' }))
  expect(moveX).toHaveValue(10)
  expect(screen.getByRole('alert')).toHaveTextContent('Blender is offline')
})
```

- [x] **Step 5: Run workbar tests and verify RED**

Run: `cd web && npx vitest run src/components/BatchTransformPanel.test.tsx`  
Expected: component import fails because it does not exist.

- [x] **Step 6: Implement the responsive workbar**

Build controlled drafts for move/rotate/scale, use the shared domain validator,
retain drafts across segmented modes, reset only after success, expose axis text
and axis color, and connect errors through `aria-describedby`.

- [x] **Step 7: Run frontend tests GREEN**

Run: `cd web && npx vitest run src/domain/batchTransform.test.ts src/stores/batchSelectionStore.test.ts src/mdr/nodes/ObjectListNode.test.tsx src/components/BatchTransformPanel.test.tsx src/mdr/inspector.dummyrun.test.tsx`  
Expected: all tests pass without console warnings.

- [x] **Step 8: Commit the WebUI feature**

```bash
git add web/src/components/BatchTransformPanel.tsx web/src/components/BatchTransformPanel.test.tsx web/src/mdr/nodes/ObjectListNode.tsx web/src/mdr/nodes/ObjectListNode.test.tsx web/src/components/ui/icon-map.ts
git commit -m "feat(web): batch edit selected scene objects"
```

---

### Task 5: Real Blender proof and documentation

**Files:**
- Create: `scripts/verify/batch_transform_verify_real.py`
- Modify: `scripts/ci.sh`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/PROGRESS.md`
- Modify: `docs/TODOS.md`
- Modify: `tests/unit/core/test_architecture_ssot.py`

**Interfaces:**
- Consumes: public REST batch endpoint, `/api/undo`, and addon socket oracle at 9876.
- Produces: discriminating single-Undo evidence in `scripts/ci.sh --real`.

- [x] **Step 1: Add a failing architecture/CI gate test**

```python
def test_architecture_names_batch_transform_service_and_port():
    architecture = Path("docs/ARCHITECTURE.md").read_text()
    assert "BatchTransformService" in architecture
    assert "SceneBatchCommandPort" in architecture
    ci = Path("scripts/ci.sh").read_text()
    assert "batch_transform_verify_real.py" in ci
```

Run: `$HOME/miniconda3/envs/blender-mcp/bin/python -m pytest tests/unit/core/test_architecture_ssot.py -q`  
Expected: assertion fails because the architecture and gate are not updated.

- [x] **Step 2: Implement nonce-based real verification**

The script must create two objects with a unique prefix, capture their exact
location/rotation/scale through the addon oracle, POST one mixed batch transform,
verify both changed by expected increments, POST one `/api/undo`, verify both
equal their original values within tolerance, and delete every prefixed object in
`finally`. Any failed hypothesis exits non-zero.

- [x] **Step 3: Wire the real gate and update SSOT documents**

Add a hard `_run` entry after print readiness. Document the new application slice,
REST endpoint, frontend flow, and completed status. Remove any stale entry that
claims multi-select or batch transforms remain outstanding; do not add speculative
work items.

- [x] **Step 4: Run all gates**

Run: `scripts/ci.sh`  
Expected: every T1 and T2 hard gate passes.

Run: `scripts/ci.sh --real`  
Expected: REST, MCP, print readiness, and batch transform real gates pass; one Undo restores both nonce objects.

- [x] **Step 5: Commit verification and docs**

```bash
git add scripts/verify/batch_transform_verify_real.py scripts/ci.sh docs/ARCHITECTURE.md docs/PROGRESS.md docs/TODOS.md tests/unit/core/test_architecture_ssot.py
git commit -m "test: prove batch transform undo on Blender"
```
