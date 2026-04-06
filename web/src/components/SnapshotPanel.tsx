import { useState, useEffect, useCallback } from 'react'

const _base = import.meta.env.BASE_URL.replace(/\/$/, '')

interface Snapshot {
  id: string
  label: string
  created_at: string
  session_id: string
  thumbnail: string | null
}

export function SnapshotPanel() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [label, setLabel] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  const fetchSnapshots = useCallback(async () => {
    try {
      const res = await fetch(`${_base}/api/snapshots`)
      if (!res.ok) return
      const data = await res.json() as { snapshots: Snapshot[] }
      setSnapshots(data.snapshots)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    void fetchSnapshots()
  }, [fetchSnapshots])

  const showStatus = (msg: string) => {
    setStatus(msg)
    setTimeout(() => setStatus(null), 2500)
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${_base}/api/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: label || 'Snapshot' }),
      })
      if (!res.ok) throw new Error('Failed to save')
      await fetchSnapshots()
      setLabel('')
      showStatus('✅ 快照已儲存')
    } catch (e) {
      showStatus(`❌ ${String(e)}`)
    } finally {
      setLoading(false)
    }
  }

  const handleRestore = async (snap: Snapshot) => {
    setLoading(true)
    try {
      const res = await fetch(`${_base}/api/snapshot/${snap.id}/restore`, { method: 'POST' })
      if (!res.ok) throw new Error('Restore failed')
      showStatus(`✅ 還原：${snap.label}`)
    } catch (e) {
      showStatus(`❌ ${String(e)}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (snap: Snapshot) => {
    if (!window.confirm(`刪除快照「${snap.label}」？`)) return
    try {
      const res = await fetch(`${_base}/api/snapshot/${snap.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Delete failed')
      setSnapshots((prev) => prev.filter((s) => s.id !== snap.id))
      showStatus('🗑️ 已刪除')
    } catch (e) {
      showStatus(`❌ ${String(e)}`)
    }
  }

  return (
    <div className="flex flex-col gap-3 p-3 h-full overflow-auto">
      {/* Save row */}
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="快照名稱（可選）"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void handleSave() }}
        />
        <button
          onClick={() => void handleSave()}
          disabled={loading}
          className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          📸 儲存快照
        </button>
      </div>

      {/* Status toast */}
      {status && (
        <div className="rounded bg-gray-700 px-3 py-1 text-center text-sm text-white">
          {status}
        </div>
      )}

      {/* Snapshot list */}
      {snapshots.length === 0 ? (
        <p className="text-center text-sm text-gray-500">尚無快照</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {snapshots.map((snap) => (
            <li
              key={snap.id}
              className="flex items-center gap-2 rounded border border-gray-700 bg-gray-800 p-2"
            >
              {/* Thumbnail */}
              {snap.thumbnail ? (
                <img
                  src={`data:image/png;base64,${snap.thumbnail}`}
                  alt={snap.label}
                  className="h-12 w-12 flex-shrink-0 rounded object-cover"
                />
              ) : (
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded bg-gray-700 text-2xl">
                  🎲
                </div>
              )}

              {/* Info */}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-white">{snap.label}</p>
                <p className="text-xs text-gray-400">
                  {new Date(snap.created_at).toLocaleString('zh-TW')}
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-1">
                <button
                  onClick={() => void handleRestore(snap)}
                  disabled={loading}
                  title="還原此快照"
                  className="rounded bg-green-700 px-2 py-1 text-xs text-white hover:bg-green-600 disabled:opacity-50"
                >
                  ↩ 還原
                </button>
                <button
                  onClick={() => void handleDelete(snap)}
                  title="刪除此快照"
                  className="rounded bg-red-800 px-2 py-1 text-xs text-white hover:bg-red-700"
                >
                  🗑️
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
