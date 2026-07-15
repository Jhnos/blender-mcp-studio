import { useCallback, useEffect, useState } from 'react'
import { useChatStore } from '../../stores/chatStore'
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

function ObjectRow({ obj, dispatch, onChanged }: {
  obj: SceneObject; dispatch: Dispatch; onChanged: () => void
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

export function ObjectListNode({ dispatch }: NodeProps) {
  const [objects, setObjects] = useState<SceneObject[]>([])
  const [error, setError] = useState<string | null>(null)
  const sceneRefreshTick = useChatStore((s) => s.sceneRefreshTick)

  const refresh = useCallback(async () => {
    try {
      const { objects } = await dispatch('scene.list') as { objects: SceneObject[] }
      setObjects(objects ?? [])
      setError(null)
    } catch {
      setError('無法連線至 Blender')
      setObjects([])
    }
  }, [dispatch])

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
  return (
    <div className="space-y-0.5 px-2">
      {objects.map((obj) => (
        <ObjectRow key={obj.name} obj={obj} dispatch={dispatch} onChanged={refresh} />
      ))}
    </div>
  )
}
