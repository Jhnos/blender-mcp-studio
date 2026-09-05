import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useDispatch } from '../mdr'
import { Button, StatusBadge } from './ui'
import { ExportPanel, type ExportOptions, type ExportPanelHandle } from './ExportPanel'
import { ModelViewport } from './ModelViewport'
import { OperationStatusCenter } from './OperationStatusCenter'
import { CommandPalette } from './CommandPalette'
import { runTracked } from '../lib/trackedOperation'
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
  const exportPanelRef = useRef<ExportPanelHandle>(null)

  const refreshPreview = useCallback(async (announce = false) => {
    await runTracked('刷新預覽', async () => {
      const blob = await dispatch('preview.get', { t: Date.now() }) as Blob
      setPolledUrl(URL.createObjectURL(blob))
    }, {
      success: '預覽已更新',
      // A background poll nobody asked for should not fill the status centre.
      track: announce,
      retryable: announce,
      setBusy: setLoading,
      onError: () => setPolledUrl(null),
    })
  }, [dispatch])

  // Poll the viewport whenever a Blender command changes the scene.
  useEffect(() => { void refreshPreview() }, [refreshPreview, sceneRefreshTick])

  useEffect(() => {
    if (liveScreenshot) setLastUpdate(new Date().toLocaleTimeString('zh-TW'))
  }, [liveScreenshot])

  // The object URL's lifetime belongs to the state that holds it: revoke the
  // previous one when it is replaced, and the last one on unmount. Tracking it
  // in a ref meant the refresh closure read a ref, which is exactly what the
  // react-hooks rules flag when that closure is handed to another function.
  useEffect(() => {
    const url = polledUrl
    return () => { if (url) URL.revokeObjectURL(url) }
  }, [polledUrl])

  const isLive = liveScreenshot !== null
  const displayUrl = isLive ? `data:image/png;base64,${liveScreenshot}` : polledUrl

  const runHistory = useCallback(async (action: 'undo' | 'redo') => {
    const label = action === 'undo' ? '復原' : '重做'
    await runTracked(label, async () => {
      const r = await dispatch(action) as { success: boolean; message: string }
      // A refused undo is a failed operation, not a successful call that says no.
      if (!r.success) throw new Error(r.message)
      triggerSceneRefresh()
      return r
    }, { success: (r) => r.message })
  }, [dispatch, triggerSceneRefresh])

  const doExport = async (options: ExportOptions) => {
    const format = options.format.toUpperCase()
    await runTracked(`匯出 ${format}`, async () => {
      const blob = await dispatch('export.scene', options) as Blob
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `blender-scene.${options.format}`; a.click()
      URL.revokeObjectURL(url)
    }, {
      success: `${format} 已產生，可交給切片器處理`,
      setBusy: setExporting,
    })
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

  // Ref reads are wrapped in stable callbacks rather than written inline in the
  // memo: an object of arrow functions handed to another function is something
  // the react-hooks rules cannot prove is only invoked later.
  const openPrintReadiness = useCallback(() => exportPanelRef.current?.open(), [])
  const rerunPrintReadiness = useCallback(
    () => exportPanelRef.current?.rerunInspection(),
    [],
  )

  // createStudioCommands only stores these callbacks in CommandDefinition.run; it
  // never invokes them, so the panel handle is read when the user runs a command,
  // not during render. The imperative handle is the documented seam
  // (docs/01-architecture.md, ADR-006). This violation was latent before: the rule
  // stopped analysing this component at an earlier self-referencing callback, so
  // removing that callback is what made it visible. Tracked in docs/DEFERRALS.md.
  // eslint-disable-next-line react-hooks/refs
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
    openPrintReadiness,
    rerunPrintReadiness,
  }), [focusElement, openPrintReadiness, refreshPreview, rerunPrintReadiness, runHistory])

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
