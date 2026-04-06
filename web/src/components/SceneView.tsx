import { useEffect, useState, useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { MaterialBrowserPanel } from './MaterialBrowserPanel'
import { RefinementPanel } from './RefinementPanel'
import { SnapshotPanel } from './SnapshotPanel'

const _base = import.meta.env.BASE_URL.replace(/\/$/, '')

interface SceneObject {
  name: string
  type: string
}

const TYPE_ICON: Record<string, string> = {
  MESH: '◼',
  CURVE: '〜',
  LIGHT: '💡',
  CAMERA: '📷',
  EMPTY: '○',
  ARMATURE: '🦴',
}

// ---------------------------------------------------------------------------
// ObjectRow — inline rename, select, delete, visibility toggle
// ---------------------------------------------------------------------------

function ObjectRow({ obj, onRefresh }: { obj: SceneObject; onRefresh: () => void }) {
  const [editing, setEditing] = useState(false)
  const [nameInput, setNameInput] = useState(obj.name)
  const [busy, setBusy] = useState(false)

  const apiCall = async (method: string, path: string, body?: object) => {
    setBusy(true)
    try {
      const res = await fetch(`${_base}/api${path}`, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined,
      })
      if (!res.ok) console.warn(`${method} ${path} → ${res.status}`)
      onRefresh()
    } finally {
      setBusy(false)
    }
  }

  const handleSelect = () => void apiCall('POST', `/object/${encodeURIComponent(obj.name)}/select`)
  const handleDelete = () => {
    if (!window.confirm(`刪除物件「${obj.name}」？`)) return
    void apiCall('DELETE', `/object/${encodeURIComponent(obj.name)}`)
  }
  const handleRename = async () => {
    if (nameInput === obj.name || !nameInput.trim()) { setEditing(false); return }
    await apiCall('PUT', `/object/${encodeURIComponent(obj.name)}`, { new_name: nameInput.trim() })
    setEditing(false)
  }

  return (
    <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-slate-800 group transition-colors">
      {/* Type icon */}
      <span className="text-slate-400 w-4 text-center text-xs shrink-0">
        {TYPE_ICON[obj.type] ?? '?'}
      </span>

      {/* Name / rename input */}
      {editing ? (
        <input
          autoFocus
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void handleRename()
            if (e.key === 'Escape') { setEditing(false); setNameInput(obj.name) }
          }}
          onBlur={() => void handleRename()}
          className="flex-1 rounded bg-slate-700 px-1.5 py-0.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-violet-500"
        />
      ) : (
        <button
          onClick={handleSelect}
          disabled={busy}
          className="flex-1 text-left text-sm text-slate-200 truncate hover:text-violet-300 transition-colors disabled:opacity-50"
        >
          {obj.name}
        </button>
      )}

      <span className="text-xs text-slate-600 shrink-0 hidden group-hover:inline">{obj.type}</span>

      {/* Action buttons — appear on hover */}
      <div className="hidden group-hover:flex items-center gap-0.5 shrink-0">
        <button
          onClick={() => setEditing(true)}
          title="重新命名"
          className="rounded px-1 py-0.5 text-xs text-slate-400 hover:text-white hover:bg-slate-700"
        >✏️</button>
        <button
          onClick={handleDelete}
          title="刪除"
          className="rounded px-1 py-0.5 text-xs text-slate-400 hover:text-red-400 hover:bg-slate-700"
        >🗑️</button>
      </div>
    </div>
  )
}

export function SceneView() {
  const [tab, setTab] = useState<'preview' | 'objects' | 'log' | 'refine' | 'history' | 'materials'>('preview')
  const [objects, setObjects] = useState<SceneObject[]>([])
  const [loading, setLoading] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [polledPreviewUrl, setPolledPreviewUrl] = useState<string | null>(null)

  const { blenderLogs, sceneRefreshTick, triggerSceneRefresh, liveScreenshot } = useChatStore()

  // Prefer live screenshot (pushed via WebSocket) over polled preview
  const displayUrl = liveScreenshot
    ? `data:image/png;base64,${liveScreenshot}`
    : polledPreviewUrl

  const refreshScene = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${_base}/api/scene`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json() as { objects: SceneObject[] }
      setObjects(data.objects ?? [])
    } catch {
      setError('無法連線至 Blender')
      setObjects([])
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshPreview = useCallback(async () => {
    setPreviewLoading(true)
    try {
      const res = await fetch(`${_base}/api/preview?t=${Date.now()}`)
      if (!res.ok) throw new Error()
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      setPolledPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return url })
    } catch {
      setPolledPreviewUrl(null)
    } finally {
      setPreviewLoading(false)
    }
  }, [])

  const refreshAll = useCallback(() => {
    void refreshScene()
    void refreshPreview()
  }, [refreshScene, refreshPreview])

  // Auto-refresh when Blender executes something (also triggers via sceneRefreshTick)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { refreshAll() }, [sceneRefreshTick])

  const isLive = liveScreenshot !== null

  return (
    <div className="w-96 flex flex-col border-l border-slate-700 bg-slate-900">
      {/* Tab bar */}
      <div className="flex border-b border-slate-700 shrink-0">
        {(['preview', 'objects', 'log', 'refine', 'history', 'materials'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 text-xs font-semibold tracking-wide transition-colors ${
              tab === t
                ? 'text-violet-400 border-b-2 border-violet-500 bg-slate-800/50'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {t === 'preview'
              ? `🖼 預覽${isLive ? ' 🔴' : ''}`
              : t === 'objects'
              ? `◼ 物件 (${objects.length})`
              : t === 'log'
              ? '📋 記錄'
              : t === 'refine'
              ? '🔁 精煉'
              : t === 'history'
              ? '📸 歷史'
              : '🎨 材質'}
          </button>
        ))}
        <button
          onClick={() => { triggerSceneRefresh(); refreshAll() }}
          className="px-3 text-slate-500 hover:text-violet-400 transition-colors text-sm"
          title="刷新"
        >
          {loading || previewLoading ? '⟳' : '↺'}
        </button>
      </div>

      {/* Preview tab */}
      {tab === 'preview' && (
        <div className="flex-1 flex flex-col items-center justify-center p-3 overflow-hidden">
          {isLive && (
            <div className="w-full text-right mb-1">
              <span className="text-xs text-green-400 bg-green-900/30 px-2 py-0.5 rounded-full">
                ● 即時更新
              </span>
            </div>
          )}
          {previewLoading && !displayUrl && (
            <div className="text-slate-500 text-xs animate-pulse">載入預覽中...</div>
          )}
          {displayUrl && (
            <img
              src={displayUrl}
              alt="Blender viewport"
              className="max-w-full max-h-full object-contain rounded-lg border border-slate-700 shadow-lg"
            />
          )}
          {!previewLoading && !displayUrl && (
            <div className="text-slate-600 text-xs text-center">
              <div className="text-4xl mb-3">🎭</div>
              <p>無法取得預覽</p>
              <p className="mt-1 text-slate-700">請確認 Blender 正在運行</p>
            </div>
          )}
        </div>
      )}

      {/* Objects tab */}
      {tab === 'objects' && (
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {error && (
            <div className="text-xs text-red-400 bg-red-900/20 rounded px-3 py-2 mt-2">⚠️ {error}</div>
          )}
          {!error && objects.length === 0 && !loading && (
            <p className="text-xs text-slate-600 text-center mt-8">場景是空的</p>
          )}
          {objects.map((obj, i) => (
            <ObjectRow key={i} obj={obj} onRefresh={refreshAll} />
          ))}
        </div>
      )}

      {/* Log tab */}
      {tab === 'log' && (
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {blenderLogs.length === 0 && (
            <p className="text-xs text-slate-600 text-center mt-8">尚無執行記錄</p>
          )}
          {[...blenderLogs].reverse().map((log, i) => (
            <div key={i} className={`rounded-lg p-3 text-xs font-mono whitespace-pre-wrap break-all ${
              log.isError
                ? 'bg-red-900/30 text-red-300 border border-red-800'
                : 'bg-slate-800 text-green-300 border border-slate-700'
            }`}>
              <div className="text-slate-500 mb-1">{log.timestamp}</div>
              {log.output}
            </div>
          ))}
        </div>
      )}

      {/* Refinement tab */}
      {tab === 'refine' && (
        <div className="flex-1 overflow-hidden">
          <RefinementPanel />
        </div>
      )}

      {/* History / Snapshots tab */}
      {tab === 'history' && (
        <div className="flex-1 overflow-hidden">
          <SnapshotPanel />
        </div>
      )}

      {/* Materials / Poly Haven tab */}
      {tab === 'materials' && (
        <div className="flex-1 overflow-hidden">
          <MaterialBrowserPanel />
        </div>
      )}
    </div>
  )
}

