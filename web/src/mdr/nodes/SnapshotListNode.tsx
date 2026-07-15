import { useCallback, useEffect, useState } from 'react'
import { Button, EmptyState, Icon } from '../../components/ui'
import type { NodeProps } from '../registry'
import type { SnapshotItem } from '../apiActions'

// ---------------------------------------------------------------------------
// snapshot-list — save / restore / delete scene snapshots via dispatch.
// A "history as safety net" surface (research: timeline lets users experiment
// without fear of losing prior outputs).
// ---------------------------------------------------------------------------

export function SnapshotListNode({ dispatch }: NodeProps) {
  const [snapshots, setSnapshots] = useState<SnapshotItem[]>([])
  const [label, setLabel] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  const toast = (msg: string) => { setStatus(msg); setTimeout(() => setStatus(null), 2500) }

  const refresh = useCallback(async () => {
    try {
      const { snapshots } = await dispatch('snapshot.list') as { snapshots: SnapshotItem[] }
      setSnapshots(snapshots ?? [])
    } catch { /* keep last known list */ }
  }, [dispatch])

  useEffect(() => { void refresh() }, [refresh])

  const save = async () => {
    setBusy(true)
    try { await dispatch('snapshot.save', { label }); setLabel(''); await refresh(); toast('已儲存快照') }
    catch (e) { toast(`儲存失敗：${String(e)}`) }
    finally { setBusy(false) }
  }
  const restore = async (s: SnapshotItem) => {
    try { await dispatch('snapshot.restore', { id: s.id }); toast(`已還原：${s.label}`) }
    catch (e) { toast(`還原失敗：${String(e)}`) }
  }
  const del = async (s: SnapshotItem) => {
    if (!window.confirm(`刪除快照「${s.label}」？`)) return
    try {
      await dispatch('snapshot.delete', { id: s.id })
      setSnapshots((prev) => prev.filter((x) => x.id !== s.id))
      toast('已刪除')
    } catch (e) { toast(`刪除失敗：${String(e)}`) }
  }

  return (
    <div className="flex flex-col gap-2 px-2">
      <div className="flex gap-1.5">
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void save() }}
          placeholder="快照名稱（可選）"
          className="flex-1 rounded-md border border-border bg-surface-sunken px-2 py-1 text-sm
                     text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <Button variant="primary" icon="snapshot" onClick={() => void save()} disabled={busy}>
          儲存
        </Button>
      </div>

      {status && (
        <div className="rounded-md bg-surface-overlay px-3 py-1 text-center text-xs text-fg-muted">{status}</div>
      )}

      {snapshots.length === 0 ? (
        <EmptyState icon="snapshot" title="尚無快照" hint="儲存目前場景，隨時可還原" />
      ) : (
        <ul className="flex flex-col gap-1.5">
          {snapshots.map((s) => (
            <li key={s.id} className="flex items-center gap-2 rounded-md border border-border bg-surface-raised p-2">
              {s.thumbnail ? (
                <img src={`data:image/png;base64,${s.thumbnail}`} alt={s.label}
                  className="h-11 w-11 shrink-0 rounded object-cover" />
              ) : (
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded bg-surface-overlay">
                  <Icon name="snapshot" size={18} className="text-fg-subtle" />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-fg">{s.label}</p>
                <p className="text-xs text-fg-subtle">{new Date(s.created_at).toLocaleString('zh-TW')}</p>
              </div>
              <div className="flex shrink-0 gap-0.5">
                <Button variant="subtle" icon="restore" onClick={() => void restore(s)}>還原</Button>
                <Button variant="danger" icon="delete" iconOnly title="刪除" onClick={() => void del(s)} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
