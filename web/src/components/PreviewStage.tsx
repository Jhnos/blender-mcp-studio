import { useCallback, useEffect, useRef, useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useDispatch } from '../mdr'
import { Button, StatusBadge } from './ui'
import { ExportPanel, type ExportOptions } from './ExportPanel'
import { ModelViewport } from './ModelViewport'

// ---------------------------------------------------------------------------
// PreviewStage — the center focal point (single focal point principle). The
// live Blender viewport is persistent here, not one tab among six. Toolbar
// actions (refresh / export / undo / redo) all go through the dispatcher.
// ---------------------------------------------------------------------------

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

  const doExport = async (options: ExportOptions) => {
    setExporting(true)
    try {
      const blob = await dispatch('export.scene', options) as Blob
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `blender-scene.${options.format}`; a.click()
      URL.revokeObjectURL(url)
      showToast(`${options.format.toUpperCase()} 已產生，可交給切片器處理`)
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
        <ExportPanel onExport={(options) => void doExport(options)} busy={exporting} />
      </div>

      {/* Viewport */}
      <div className="min-h-0 flex-1 p-3">
        <ModelViewport imageUrl={displayUrl} loading={loading} toast={toast} />
      </div>
    </div>
  )
}
