import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useDispatch } from '../mdr'
import { Button, StatusBadge } from './ui'
import { ExportPanel, type ExportOptions, type ExportPanelHandle } from './ExportPanel'
import { ModelViewport } from './ModelViewport'
import { OperationStatusCenter } from './OperationStatusCenter'
import { CommandPalette } from './CommandPalette'
import { useOperationStore } from '../stores/operationStore'
import { useBatchSelectionStore } from '../stores/batchSelectionStore'
import { createStudioCommands } from '../commands/studioCommands'
import { useGlobalShortcuts } from '../hooks/useGlobalShortcuts'
import type {
  PrintReadinessOptions,
  PrintReadinessReport,
} from '../domain/printReadiness'

// ---------------------------------------------------------------------------
// PreviewStage — the center focal point (single focal point principle). The
// live Blender viewport is persistent here, not one tab among six. Toolbar
// actions (refresh / export / undo / redo) all go through the dispatcher.
// ---------------------------------------------------------------------------

export function PreviewStage() {
  const dispatch = useDispatch()
  const liveScreenshot = useChatStore((s) => s.liveScreenshot)
  const sceneRefreshTick = useChatStore((s) => s.sceneRefreshTick)
  const triggerSceneRefresh = useChatStore((s) => s.triggerSceneRefresh)

  const [polledUrl, setPolledUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string | null>(null)
  const objectUrlRef = useRef<string | null>(null)
  const exportPanelRef = useRef<ExportPanelHandle>(null)

  const refreshPreview = useCallback(async (announce = false) => {
    const operationId = announce
      ? useOperationStore.getState().begin('刷新預覽', () => refreshPreview(true))
      : null
    setLoading(true)
    try {
      const blob = await dispatch('preview.get', { t: Date.now() }) as Blob
      const url = URL.createObjectURL(blob)
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = url
      setPolledUrl(url)
      if (operationId) useOperationStore.getState().succeed(operationId, '預覽已更新')
    } catch (error) {
      setPolledUrl(null)
      if (operationId) {
        useOperationStore.getState().fail(
          operationId,
          error instanceof Error ? error.message : String(error),
        )
      }
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

  const runHistory = useCallback(async (action: 'undo' | 'redo') => {
    const label = action === 'undo' ? '復原' : '重做'
    const operationId = useOperationStore.getState().begin(label)
    try {
      const r = await dispatch(action) as { success: boolean; message: string }
      if (r.success) {
        useOperationStore.getState().succeed(operationId, r.message)
        triggerSceneRefresh()
      } else {
        useOperationStore.getState().fail(operationId, r.message)
      }
    } catch (error) {
      useOperationStore.getState().fail(
        operationId,
        error instanceof Error ? error.message : String(error),
      )
    }
  }, [dispatch, triggerSceneRefresh])

  const doExport = async (options: ExportOptions) => {
    const format = options.format.toUpperCase()
    const operationId = useOperationStore.getState().begin(`匯出 ${format}`)
    setExporting(true)
    try {
      const blob = await dispatch('export.scene', options) as Blob
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `blender-scene.${options.format}`; a.click()
      URL.revokeObjectURL(url)
      useOperationStore.getState().succeed(operationId, `${format} 已產生，可交給切片器處理`)
    } catch (error) {
      useOperationStore.getState().fail(
        operationId,
        error instanceof Error ? error.message : String(error),
      )
    }
    finally { setExporting(false) }
  }

  const inspectPrintReadiness = async (
    options: PrintReadinessOptions,
  ): Promise<PrintReadinessReport> => (
    await dispatch('print.readiness', options) as PrintReadinessReport
  )

  const focusElement = useCallback((id: string) => {
    const element = document.getElementById(id)
    element?.scrollIntoView?.({ block: 'center', behavior: 'smooth' })
    element?.focus()
  }, [])

  const commands = useMemo(() => createStudioCommands({
    refreshPreview: () => refreshPreview(true),
    undo: () => runHistory('undo'),
    redo: () => runHistory('redo'),
    selectAllTargets: () => {
      const selection = useBatchSelectionStore.getState()
      selection.replace(selection.availableNames)
    },
    clearTargets: () => useBatchSelectionStore.getState().clear(),
    focusBatchTransform: () => focusElement('batch-transform-panel'),
    focusObjectList: () => focusElement('scene-object-list'),
    openPrintReadiness: () => exportPanelRef.current?.open(),
    rerunPrintReadiness: () => exportPanelRef.current?.rerunInspection(),
  }), [focusElement, refreshPreview, runHistory])

  const openPalette = useCallback(() => setPaletteOpen(true), [])
  useGlobalShortcuts({
    onPalette: openPalette,
    onUndo: () => { void runHistory('undo') },
    onRedo: () => { void runHistory('redo') },
  })

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-surface">
      {/* Stage toolbar */}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        {isLive
          ? <StatusBadge status="live" label="即時串流" pulse />
          : <span className="text-xs font-medium text-fg-subtle">預覽</span>}
        {lastUpdate && <span className="text-xs text-fg-subtle">{lastUpdate}</span>}
        <div className="flex-1" />
        <OperationStatusCenter />
        <Button variant="ghost" icon="command" iconOnly title="指令面板 (⌘K)" onClick={openPalette} />
        <Button variant="ghost" icon="undo" iconOnly title="復原 (⌘Z)" onClick={() => void runHistory('undo')} />
        <Button variant="ghost" icon="redo" iconOnly title="重做 (⌘⇧Z)" onClick={() => void runHistory('redo')} />
        <Button variant="ghost" icon="refresh" iconOnly title="刷新預覽" onClick={() => void refreshPreview(true)} />
        <ExportPanel
          ref={exportPanelRef}
          onExport={(options) => void doExport(options)}
          onInspect={inspectPrintReadiness}
          sceneRevision={sceneRefreshTick}
          busy={exporting}
        />
      </div>

      {/* Viewport */}
      <div className="min-h-0 flex-1 p-3">
        <ModelViewport imageUrl={displayUrl} loading={loading} />
      </div>
      <CommandPalette commands={commands} open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  )
}
