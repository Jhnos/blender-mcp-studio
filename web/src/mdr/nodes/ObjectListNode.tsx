import { useCallback, useEffect, useRef, useState } from 'react'
import { BatchTransformPanel } from '../../components/BatchTransformPanel'
import { useChatStore } from '../../stores/chatStore'
import { useBatchSelectionStore } from '../../stores/batchSelectionStore'
import { Icon, EmptyState, type IconName } from '../../components/ui'
import type { NodeProps } from '../registry'
import type { Dispatch } from '../actions'
import type { SceneObject } from '../apiActions'

const TYPE_ICON: Record<string, IconName> = {
  MESH: 'mesh', CURVE: 'curve', LIGHT: 'light',
  CAMERA: 'camera', EMPTY: 'empty', ARMATURE: 'armature',
}

// ---------------------------------------------------------------------------
// object-list — the Scene panel. Talks to the backend only via `dispatch`.
// Row actions reveal on hover OR keyboard focus (fixes the old hover-only
// discoverability gap — Norman signifier + a11y).
// ---------------------------------------------------------------------------

function ObjectRow({ obj, dispatch, onChanged, checked, onToggle }: {
  obj: SceneObject
  dispatch: Dispatch
  onChanged: () => void
  checked: boolean
  onToggle: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(obj.name)
  const [busy, setBusy] = useState(false)

  const run = useCallback(async (fn: () => Promise<unknown>) => {
    setBusy(true)
    try { await fn(); onChanged() }
    catch (e) { console.warn('[object-list]', e) }
    finally { setBusy(false) }
  }, [onChanged])

  const rename = async () => {
    if (name === obj.name || !name.trim()) { setEditing(false); setName(obj.name); return }
    await run(() => dispatch('object.rename', { name: obj.name, newName: name.trim() }))
    setEditing(false)
  }
  const del = () => {
    if (!window.confirm(`刪除物件「${obj.name}」？`)) return
    void run(() => dispatch('object.delete', { name: obj.name }))
  }

  return (
    <div className="group flex items-center gap-1.5 rounded-md px-2 py-1.5 hover:bg-surface-overlay transition-colors">
      <input
        type="checkbox"
        aria-label={`選取 ${obj.name}`}
        checked={checked}
        onChange={onToggle}
        onClick={(event) => event.stopPropagation()}
        className="size-3.5 shrink-0 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      />
      <Icon name={TYPE_ICON[obj.type] ?? 'empty'} size={14} className="shrink-0 text-fg-subtle" />
      {editing ? (
        <input
          autoFocus value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void rename()
            if (e.key === 'Escape') { setEditing(false); setName(obj.name) }
          }}
          onBlur={() => void rename()}
          className="flex-1 rounded bg-surface-sunken px-1.5 py-0.5 text-xs text-fg
                     focus:outline-none focus:ring-1 focus:ring-accent"
        />
      ) : (
        <button
          onClick={() => void run(() => dispatch('object.select', { name: obj.name }))}
          disabled={busy}
          className="flex-1 truncate text-left text-sm text-fg hover:text-accent
                     transition-colors disabled:opacity-50"
        >
          {obj.name}
        </button>
      )}
      <span className="shrink-0 text-xs text-fg-subtle opacity-0 group-hover:opacity-100 group-focus-within:opacity-100">
        {obj.type}
      </span>
      <div className="flex shrink-0 items-center gap-0.5 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
        <button onClick={() => setEditing(true)} title="重新命名"
          className="rounded p-1 text-fg-subtle hover:text-fg hover:bg-surface-raised">
          <Icon name="rename" size={13} />
        </button>
        <button onClick={del} title="刪除"
          className="rounded p-1 text-fg-subtle hover:text-danger hover:bg-surface-raised">
          <Icon name="delete" size={13} />
        </button>
      </div>
    </div>
  )
}

function SelectAllCheckbox({ checked, indeterminate, onChange }: {
  checked: boolean
  indeterminate: boolean
  onChange: () => void
}) {
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate
  }, [indeterminate])
  return (
    <input
      ref={ref}
      type="checkbox"
      aria-label="全選場景物件"
      checked={checked}
      onChange={onChange}
      className="size-3.5 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    />
  )
}

export function ObjectListNode({ dispatch }: NodeProps) {
  const [objects, setObjects] = useState<SceneObject[]>([])
  const [error, setError] = useState<string | null>(null)
  const sceneRefreshTick = useChatStore((s) => s.sceneRefreshTick)
  const selectedNames = useBatchSelectionStore((state) => state.selectedNames)
  const toggle = useBatchSelectionStore((state) => state.toggle)
  const replace = useBatchSelectionStore((state) => state.replace)
  const clear = useBatchSelectionStore((state) => state.clear)
  const prune = useBatchSelectionStore((state) => state.prune)

  const refresh = useCallback(async () => {
    try {
      const { objects } = await dispatch('scene.list') as { objects: SceneObject[] }
      const nextObjects = objects ?? []
      setObjects(nextObjects)
      prune(nextObjects.map((object) => object.name))
      setError(null)
    } catch {
      setError('無法連線至 Blender')
      setObjects([])
    }
  }, [dispatch, prune])

  // Refresh on mount and whenever a Blender command changes the scene.
  // Async data fetch: setState happens after `await`, not synchronously — this
  // is the intended "sync with external system" effect, not a cascading render.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void refresh() }, [refresh, sceneRefreshTick])

  if (error) {
    return <div className="px-3 py-2"><EmptyState icon="warning" title={error} hint="請確認 Blender 正在運行" /></div>
  }
  if (objects.length === 0) {
    return <EmptyState icon="scene" title="場景是空的" hint="用左側對話描述你想建立的物件" />
  }
  const allSelected = selectedNames.length === objects.length
  const partiallySelected = selectedNames.length > 0 && !allSelected
  return (
    <div className="px-2">
      <div className="mb-1.5 flex items-center gap-2 border-b border-border px-2 pb-2">
        <SelectAllCheckbox
          checked={allSelected}
          indeterminate={partiallySelected}
          onChange={() => allSelected ? clear() : replace(objects.map((object) => object.name))}
        />
        <span className="text-[10px] font-medium text-fg-muted">批次目標</span>
        <span className="flex-1" />
        {selectedNames.length > 0 && (
          <>
            <span className="text-[10px] text-accent">已選 {selectedNames.length} 個</span>
            <button
              type="button"
              aria-label="清除批次目標"
              onClick={clear}
              className="text-[10px] text-fg-subtle hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              清除
            </button>
          </>
        )}
      </div>
      <div className="space-y-0.5">
        {objects.map((obj) => (
          <ObjectRow
            key={obj.name}
            obj={obj}
            dispatch={dispatch}
            onChanged={refresh}
            checked={selectedNames.includes(obj.name)}
            onToggle={() => toggle(obj.name)}
          />
        ))}
      </div>
      {selectedNames.length > 0 && (
        <BatchTransformPanel dispatch={dispatch} selectedNames={selectedNames} />
      )}
    </div>
  )
}
