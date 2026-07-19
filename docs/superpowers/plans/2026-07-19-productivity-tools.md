# Productivity Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a curated keyboard command palette and one shared operation status center for consistent progress, success, failure, and safe retry feedback.

**Architecture:** A pure command registry models available UI commands and a focused Zustand store models recent operations. Rendering components depend on those abstractions; existing scene controls publish operation state instead of owning isolated toast timers.

**Tech Stack:** React 19, TypeScript 6, Zustand 5, Lucide React, Tailwind CSS 4, Vitest and Testing Library.

## Global Constraints

- Complete the batch-transform plan before this plan.
- Command definitions are curated and typed; never expose arbitrary backend action invocation.
- Add command types by registration, not an expanding conditional chain.
- Global shortcuts must ignore input, textarea, select, and contenteditable targets.
- Keep operation history at five records and show retry only when a callback is explicitly supplied.
- Do not automatically retry batch transforms.
- Preserve the current nine-tool MCP catalog and existing REST response contracts.
- Use RED -> GREEN -> REFACTOR and finish with `scripts/ci.sh` plus browser-level dummy evidence.

## File Structure

- `web/src/stores/operationStore.ts`: operation lifecycle SSOT.
- `web/src/components/OperationStatusCenter.tsx`: compact status and history popover.
- `web/src/commands/types.ts`: command contract.
- `web/src/commands/registry.ts`: registry and search.
- `web/src/commands/studioCommands.ts`: Studio-specific command composition.
- `web/src/hooks/useGlobalShortcuts.ts`: editable-target guard and shortcut routing.
- `web/src/components/CommandPalette.tsx`: dialog and keyboard navigation.
- `web/src/components/PreviewStage.tsx`: status migration and shell integration.

---

### Task 1: Operation lifecycle store and status center

**Files:**
- Create: `web/src/stores/operationStore.test.ts`
- Create: `web/src/stores/operationStore.ts`
- Create: `web/src/components/OperationStatusCenter.test.tsx`
- Create: `web/src/components/OperationStatusCenter.tsx`
- Create: `web/src/components/PreviewStage.test.tsx`
- Modify: `web/src/components/PreviewStage.tsx`
- Modify: `web/src/components/BatchTransformPanel.tsx`

**Interfaces:**
- Consumes: labels/messages from callers; no REST shapes.
- Produces: `beginOperation`, `succeedOperation`, `failOperation`, `clearOperations`, and `OperationStatusCenter`.

- [x] **Step 1: Write failing store tests**

```typescript
it('tracks lifecycle and caps newest-first history at five', () => {
  const store = useOperationStore.getState()
  for (let index = 0; index < 6; index += 1) {
    const id = store.begin(`Operation ${index}`)
    useOperationStore.getState().succeed(id, `Done ${index}`)
  }
  const operations = useOperationStore.getState().operations
  expect(operations).toHaveLength(5)
  expect(operations[0].message).toBe('Done 5')
})

it('stores retry only when the caller supplies one', () => {
  const id = useOperationStore.getState().begin('Refresh', retry)
  useOperationStore.getState().fail(id, 'Offline')
  expect(useOperationStore.getState().operations[0].retry).toBe(retry)
})
```

- [x] **Step 2: Run store tests and verify RED**

Run: `cd web && npx vitest run src/stores/operationStore.test.ts`  
Expected: import fails because `operationStore` does not exist.

- [x] **Step 3: Implement the focused store**

```typescript
export type OperationStatus = 'running' | 'success' | 'error'
export interface OperationRecord {
  id: string; label: string; status: OperationStatus; timestamp: number
  message?: string; retry?: () => void | Promise<void>
}

export const useOperationStore = create<OperationState>((set) => ({
  operations: [],
  begin: (label, retry) => { const id = createOperationId(); set((s) => ({ operations: prepend(s, { id, label, status: 'running', timestamp: Date.now(), retry }) })); return id },
  succeed: (id, message) => set((s) => ({ operations: update(s.operations, id, 'success', message) })),
  fail: (id, message) => set((s) => ({ operations: update(s.operations, id, 'error', message) })),
  clear: () => set({ operations: [] }),
}))
```

Use a module-local monotonic suffix with `Date.now()` so ids are stable without a
browser crypto dependency in tests.

- [x] **Step 4: Write failing status-center tests**

```typescript
it('renders current status and only explicit retries', async () => {
  render(<OperationStatusCenter />)
  await user.click(screen.getByRole('button', { name: /recent operations/i }))
  expect(screen.getByText('Blender is offline')).toBeVisible()
  expect(screen.getAllByRole('button', { name: 'Retry' })).toHaveLength(1)
})
```

- [x] **Step 5: Implement status center and migrate local toasts**

Render a polite live region for the newest completion, a toolbar button with the
current status, and a five-row popover. Replace PreviewStage's local toast timer
with lifecycle calls for preview, undo, redo, and export. Batch transform records
no retry callback.

- [x] **Step 6: Run focused tests GREEN**

Run: `cd web && npx vitest run src/stores/operationStore.test.ts src/components/OperationStatusCenter.test.tsx src/components/PreviewStage.test.tsx src/components/BatchTransformPanel.test.tsx`  
Expected: all tests pass without act or accessibility warnings.

- [x] **Step 7: Commit operation feedback**

```bash
git add web/src/stores/operationStore.ts web/src/stores/operationStore.test.ts web/src/components/OperationStatusCenter.tsx web/src/components/OperationStatusCenter.test.tsx web/src/components/PreviewStage.tsx web/src/components/PreviewStage.test.tsx web/src/components/BatchTransformPanel.tsx
git commit -m "feat(web): centralize operation feedback"
```

---

### Task 2: Command registry, shortcuts, and palette

**Files:**
- Create: `web/src/commands/registry.test.ts`
- Create: `web/src/commands/registry.ts`
- Create: `web/src/commands/types.ts`
- Create: `web/src/commands/studioCommands.test.ts`
- Create: `web/src/commands/studioCommands.ts`
- Create: `web/src/hooks/useGlobalShortcuts.test.tsx`
- Create: `web/src/hooks/useGlobalShortcuts.ts`
- Create: `web/src/components/CommandPalette.test.tsx`
- Create: `web/src/components/CommandPalette.tsx`
- Modify: `web/src/components/PreviewStage.tsx`
- Modify: `web/src/components/ui/icon-map.ts`

**Interfaces:**
- Consumes: explicit Studio callbacks for refresh, undo, redo, selection, panel focus, and readiness.
- Produces: registry `register/list/search`, `createStudioCommands`, guarded global shortcuts, and accessible palette dialog.

- [x] **Step 1: Write failing registry tests**

```typescript
it('registers unique commands and searches title plus keywords', () => {
  const registry = createCommandRegistry()
  registry.register({ id: 'scene.refresh', title: 'Refresh scene', keywords: ['preview'], isAvailable: () => true, run })
  expect(registry.search('preview').map((command) => command.id)).toEqual(['scene.refresh'])
  expect(() => registry.register({ id: 'scene.refresh', title: 'Again', keywords: [], isAvailable: () => true, run })).toThrow(/duplicate/i)
})

it('excludes unavailable commands from search', () => {
  const registry = createCommandRegistry()
  registry.register({
    id: 'scene.redo', title: 'Redo', keywords: [],
    isAvailable: () => false, run,
  })
  expect(registry.search('redo')).toEqual([])
})
```

- [x] **Step 2: Run registry tests and verify RED**

Run: `cd web && npx vitest run src/commands/registry.test.ts`  
Expected: import fails because the registry does not exist.

- [x] **Step 3: Implement OCP-style command registry**

```typescript
export interface CommandDefinition {
  id: string
  title: string
  keywords: readonly string[]
  isAvailable: () => boolean
  run: () => void | Promise<void>
}

export function createCommandRegistry(): CommandRegistry {
  const commands = new Map<string, CommandDefinition>()
  return { register, list, search }
}
```

Normalize text with `toLocaleLowerCase()` and rank title prefix before title
contains before keyword contains. The palette component must not branch on ids.

- [x] **Step 4: Write failing shortcut and palette tests**

```typescript
it('opens with mod-k but ignores editable targets', async () => {
  render(<Harness />)
  fireEvent.keyDown(window, { key: 'k', metaKey: true })
  expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeVisible()
  await user.click(screen.getByRole('textbox', { name: 'Scene name' }))
  fireEvent.keyDown(window, { key: 'k', metaKey: true })
  expect(onShortcut).not.toHaveBeenCalled()
})

it('supports filtering, arrows, enter, and escape', async () => {
  render(<CommandPalette commands={commands} open onOpenChange={onOpenChange} />)
  const search = screen.getByRole('searchbox', { name: 'Search commands' })
  await user.type(search, 'undo')
  fireEvent.keyDown(search, { key: 'ArrowDown' })
  fireEvent.keyDown(search, { key: 'Enter' })
  expect(undo).toHaveBeenCalledTimes(1)
  render(<CommandPalette commands={commands} open onOpenChange={onOpenChange} />)
  fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Escape' })
  expect(onOpenChange).toHaveBeenLastCalledWith(false)
})
```

- [x] **Step 5: Implement guarded shortcuts and accessible palette**

`isEditableTarget(event.target)` returns true for input, textarea, select, and
contenteditable ancestry. The dialog uses `role="dialog"`, an labelled searchbox,
`role="listbox"`, `role="option"`, `aria-activedescendant`, focus restoration, and
Escape closure. Respect reduced motion and keep animation to one short opening
transition.

- [x] **Step 6: Compose the initial Studio commands**

```typescript
export interface StudioCommandActions {
  refreshPreview(): Promise<void>
  undo(): Promise<void>
  redo(): Promise<void>
  selectAllTargets(): void
  clearTargets(): void
  focusBatchTransform(): void
  focusObjectList(): void
  openPrintReadiness(): void
  rerunPrintReadiness(): Promise<void>
}
```

Return nine `CommandDefinition` values with concrete Chinese titles and English
keyword aliases. Each callback is injected; the registry imports no Zustand store
or React component.

- [x] **Step 7: Integrate with PreviewStage and run GREEN tests**

Run: `cd web && npx vitest run src/commands src/hooks/useGlobalShortcuts.test.tsx src/components/CommandPalette.test.tsx src/components/PreviewStage.test.tsx`  
Expected: all tests pass and existing Cmd/Ctrl+Z behavior remains green while editable targets are protected.

- [x] **Step 8: Commit the command palette**

```bash
git add web/src/commands web/src/hooks/useGlobalShortcuts.ts web/src/hooks/useGlobalShortcuts.test.tsx web/src/components/CommandPalette.tsx web/src/components/CommandPalette.test.tsx web/src/components/PreviewStage.tsx web/src/components/ui/icon-map.ts
git commit -m "feat(web): add Studio command palette"
```

---

### Task 3: Dummy-run verification and documentation audit

**Files:**
- Modify: `web/src/mdr/inspector.dummyrun.test.tsx`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/PROGRESS.md`
- Modify: `docs/TODOS.md`
- Modify: `docs/verification/frontend-redesign/dummy-run-plan.md`
- Modify: `tests/unit/core/test_architecture_ssot.py`

**Interfaces:**
- Consumes: completed batch selection, operation status center, and command palette.
- Produces: regression evidence and synchronized architecture/product status.

- [x] **Step 1: Add failing dummy-run assertions**

```typescript
it('completes the keyboard productivity path', async () => {
  render(<InspectorShell schema={inspectorSchema} />)
  fireEvent.keyDown(window, { key: 'k', metaKey: true })
  await user.type(screen.getByRole('searchbox'), 'select all')
  fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Enter' })
  await user.type(screen.getByLabelText('Move X in millimetres'), '10')
  await user.click(screen.getByRole('button', { name: /Apply to 2 objects/ }))
  await user.click(screen.getByRole('button', { name: /recent operations/i }))
  expect(await screen.findByText('Updated 2 objects')).toBeVisible()
})
```

Run: `cd web && npx vitest run src/mdr/inspector.dummyrun.test.tsx`  
Expected: the new path fails before test fixtures and shell wiring are completed.

- [x] **Step 2: Complete dummy fixtures and docs**

Update MSW fixtures only with the stable batch endpoint response. Document the
keyboard path, accessible roles, five-item operation history, and explicit
non-idempotent retry rule. Update architecture and progress SSOT, and remove stale
entries that name command palette or operation feedback as unfinished.

- [x] **Step 3: Run complete Web and project gates**

Run: `cd web && npm run lint && npm run build && npm test`  
Expected: lint, TypeScript/Vite build, and all Vitest suites pass.

Run: `scripts/ci.sh`  
Expected: all T1 and T2 hard gates pass.

Run: `scripts/ci.sh --real`  
Expected: every real Blender hard gate, including batch single-Undo proof, passes.

- [x] **Step 4: Commit the final audit**

```bash
git add web/src/mdr/inspector.dummyrun.test.tsx web/src/mocks docs/ARCHITECTURE.md docs/PROGRESS.md docs/TODOS.md docs/verification/frontend-redesign/dummy-run-plan.md tests/unit/core/test_architecture_ssot.py
git commit -m "docs: close frontend productivity milestone"
```

- [ ] **Step 5: Version-control completion check**

Run: `git status --short --branch && git log --oneline --decorate -12`  
Expected: clean worktree on `codex/client-neutral-mcp`; commits are ordered design, batch core/API/Web/real proof, operation status, command palette, and final audit.

Run: `git push origin codex/client-neutral-mcp`  
Expected: remote branch advances without force push.
