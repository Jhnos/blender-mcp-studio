import { useCallback, useEffect, useRef, useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useDispatch } from '../mdr'
import { Button, EmptyState, StatusBadge } from './ui'

// ---------------------------------------------------------------------------
// PreviewStage — the center focal point (single focal point principle). The
// live Blender viewport is persistent here, not one tab among six. Toolbar
// actions (refresh / export / undo / redo) all go through the dispatcher.
// ---------------------------------------------------------------------------

const EXPORT_FORMATS = [
  { fmt: 'stl', label: 'STL（3D 列印）' },
  { fmt: 'obj', label: 'OBJ' },
  { fmt: 'fbx', label: 'FBX' },
  { fmt: 'glb', label: 'GLB' },
] as const

function ExportMenu({ onExport, busy }: { onExport: (fmt: string) => void; busy: boolean }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative">
      <Button variant="subtle" icon="export" onClick={() => setOpen((o) => !o)} disabled={busy}>
        {busy ? '匯出中' : '匯出'}
      </Button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-1 min-w-[160px] rounded-lg border border-border
                          bg-surface-overlay py-1 shadow-xl">
            {EXPORT_FORMATS.map(({ fmt, label }) => (
              <button
                key={fmt}
                onClick={() => { setOpen(false); onExport(fmt) }}
                className="block w-full px-3 py-1.5 text-left text-xs text-fg-muted
                           hover:bg-surface-raised hover:text-fg transition-colors"
              >
                {label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

export function PreviewStage() {
  const dispatch = useDispatch()
  const liveScreenshot = useChatStore((s) => s.liveScreenshot)
  const sceneRefreshTick = useChatStore((s) => s.sceneRefreshTick)

  const [polledUrl, setPolledUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const objectUrlRef = useRef<string | null>(null)

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 2500) }

  const refreshPreview = useCallback(async () => {
    setLoading(true)
    try {
      const blob = await dispatch('preview.get', { t: Date.now() }) as Blob
      const url = URL.createObjectURL(blob)
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = url
      setPolledUrl(url)
    } catch {
      setPolledUrl(null)
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // Poll the viewport whenever a Blender command changes the scene.
  useEffect(() => { void refreshPreview() }, [refreshPreview, sceneRefreshTick])

  useEffect(() => {
    if (liveScreenshot) setLastUpdate(new Date().toLocaleTimeString('zh-TW'))
  }, [liveScreenshot])

  useEffect(() => () => { if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current) }, [])

  const isLive = liveScreenshot !== null
  const displayUrl = isLive ? `data:image/png;base64,${liveScreenshot}` : polledUrl

  const runHistory = async (action: 'undo' | 'redo') => {
    try {
      const r = await dispatch(action) as { success: boolean; message: string }
      showToast(`${action === 'undo' ? '↩ 復原' : '↪ 重做'}：${r.success ? '✓' : '✗'} ${r.message}`)
    } catch (e) { showToast(`${action} 失敗：${String(e)}`) }
  }

  const doExport = async (format: string) => {
    setExporting(true)
    try {
      const blob = await dispatch('export.scene', { format }) as Blob
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `blender_scene.${format}`; a.click()
      URL.revokeObjectURL(url)
    } catch (e) { showToast(`匯出失敗：${String(e)}`) }
    finally { setExporting(false) }
  }

  // Keyboard: Cmd/Ctrl+Z = undo, +Shift = redo
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        void runHistory(e.shiftKey ? 'redo' : 'undo')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-surface">
      {/* Stage toolbar */}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        {isLive
          ? <StatusBadge status="live" label="即時串流" pulse />
          : <span className="text-xs font-medium text-fg-subtle">預覽</span>}
        {lastUpdate && <span className="text-xs text-fg-subtle">{lastUpdate}</span>}
        <div className="flex-1" />
        <Button variant="ghost" icon="undo" iconOnly title="復原 (⌘Z)" onClick={() => void runHistory('undo')} />
        <Button variant="ghost" icon="redo" iconOnly title="重做 (⌘⇧Z)" onClick={() => void runHistory('redo')} />
        <Button variant="ghost" icon="refresh" iconOnly title="刷新預覽" onClick={() => void refreshPreview()} />
        <ExportMenu onExport={(f) => void doExport(f)} busy={exporting} />
      </div>

      {/* Viewport */}
      <div className="relative flex flex-1 items-center justify-center overflow-hidden p-4">
        {loading && !displayUrl && <span className="animate-pulse text-xs text-fg-subtle">載入預覽中...</span>}
        {displayUrl ? (
          <img
            src={displayUrl}
            alt="Blender viewport"
            className="max-h-full max-w-full rounded-lg border border-border object-contain shadow-lg"
          />
        ) : !loading && (
          <EmptyState icon="camera" title="無法取得預覽" hint="請確認 Blender 正在運行" />
        )}
        {toast && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-md bg-surface-overlay
                          px-3 py-1.5 text-xs text-fg-muted shadow-lg">
            {toast}
          </div>
        )}
      </div>
    </div>
  )
}
