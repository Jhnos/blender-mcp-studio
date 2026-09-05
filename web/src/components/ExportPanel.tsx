import { forwardRef, useCallback, useImperativeHandle, useMemo, useState } from 'react'
import type {
  PrintReadinessOptions,
  PrintReadinessReport,
} from '../domain/printReadiness'
import { PrintReadinessPanel } from './PrintReadinessPanel'
import { Button } from './ui'
import { runTracked } from '../lib/trackedOperation'

export type ExportFormat = 'stl' | 'obj' | 'ply' | 'glb' | 'fbx'

export interface ExportOptions {
  format: ExportFormat
  selectionOnly: boolean
  applyModifiers: boolean
  triangulate: boolean
}

interface ExportPanelProps {
  busy: boolean
  sceneRevision: number
  onInspect: (options: PrintReadinessOptions) => Promise<PrintReadinessReport>
  onExport: (options: ExportOptions) => void
}

export interface ExportPanelHandle {
  open: () => void
  rerunInspection: () => Promise<void>
}

const PRINT_FORMATS = [
  { format: 'stl', label: 'STL', hint: '最通用的切片格式' },
  { format: 'obj', label: 'OBJ', hint: '保留材質與群組' },
  { format: 'ply', label: 'PLY', hint: '網格與頂點顏色' },
] as const

const INTERCHANGE_FORMATS = [
  { format: 'glb', label: 'GLB', hint: '網頁與即時預覽' },
  { format: 'fbx', label: 'FBX', hint: 'DCC 軟體交換' },
] as const

export const ExportPanel = forwardRef<ExportPanelHandle, ExportPanelProps>(function ExportPanel({
  busy,
  sceneRevision,
  onInspect,
  onExport,
}, ref) {
  const [open, setOpen] = useState(false)
  const [format, setFormat] = useState<ExportFormat>('stl')
  const [selectionOnly, setSelectionOnly] = useState(false)
  const [applyModifiers, setApplyModifiers] = useState(true)
  const [triangulate, setTriangulate] = useState(true)
  const [minWallThicknessMm, setMinWallThicknessMm] = useState(0.8)
  const [overhangAngleDeg, setOverhangAngleDeg] = useState(45)
  const [report, setReport] = useState<PrintReadinessReport | null>(null)
  const [checkedOptions, setCheckedOptions] = useState<string | null>(null)
  const [checkedSceneRevision, setCheckedSceneRevision] = useState<number | null>(null)
  const [inspectionBusy, setInspectionBusy] = useState(false)
  const [inspectionError, setInspectionError] = useState<string | null>(null)

  const readinessOptions: PrintReadinessOptions = useMemo(() => ({
    selectionOnly,
    applyModifiers,
    minWallThicknessMm,
    overhangAngleDeg,
  }), [applyModifiers, minWallThicknessMm, overhangAngleDeg, selectionOnly])
  const optionsKey = JSON.stringify(readinessOptions)
  const stale = report !== null && (
    checkedOptions !== optionsKey || checkedSceneRevision !== sceneRevision
  )

  const runInspection = useCallback(async () => {
    const inspectedOptions = readinessOptions
    const inspectedKey = optionsKey
    const inspectedRevision = sceneRevision
    setInspectionError(null)
    // Tracked like every other operation: a failed inspection used to stop at
    // this panel's own state and never reached the status centre.
    await runTracked('列印就緒檢查', async () => {
      const nextReport = await onInspect(inspectedOptions)
      setReport(nextReport)
      setCheckedOptions(inspectedKey)
      setCheckedSceneRevision(inspectedRevision)
      return nextReport
    }, {
      success: (nextReport) => `檢查完成：${nextReport.status}`,
      setBusy: setInspectionBusy,
      onError: setInspectionError,
    })
  }, [onInspect, optionsKey, readinessOptions, sceneRevision])

  const openPanel = useCallback(() => {
    setOpen(true)
    if (report === null || stale) void runInspection()
  }, [report, runInspection, stale])

  useImperativeHandle(ref, () => ({
    open: openPanel,
    rerunInspection: async () => {
      setOpen(true)
      await runInspection()
    },
  }), [openPanel, runInspection])

  const togglePanel = () => {
    if (open) {
      setOpen(false)
      return
    }
    openPanel()
  }

  const exportOptions = (): ExportOptions => ({
    format,
    selectionOnly,
    applyModifiers,
    triangulate,
  })

  const formatGroup = (
    title: string,
    items: readonly { format: ExportFormat; label: string; hint: string }[],
  ) => (
    <fieldset className="space-y-1.5">
      <legend className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
        {title}
      </legend>
      <div className="grid grid-cols-3 gap-1.5">
        {items.map((item) => (
          <label
            key={item.format}
            className={`cursor-pointer rounded-md border px-2 py-2 transition-colors ${
              format === item.format
                ? 'border-accent bg-accent/10 text-fg'
                : 'border-border bg-surface-raised text-fg-muted hover:border-fg-subtle'
            }`}
          >
            <input
              type="radio"
              name="export-format"
              value={item.format}
              checked={format === item.format}
              onChange={() => setFormat(item.format)}
              className="sr-only"
              aria-label={`${item.label} — ${item.hint}`}
            />
            <span className="block text-xs font-semibold">{item.label}</span>
            <span className="mt-0.5 block text-[9px] leading-tight text-fg-subtle">{item.hint}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )

  const downloadDisabled = busy || inspectionBusy || stale || report?.status === 'invalid' || !report
  const downloadLabel = report?.status === 'review'
    ? `仍要下載 ${format.toUpperCase()}`
    : `下載 ${format.toUpperCase()}`

  return (
    <div className="relative">
      <Button variant="subtle" icon="export" onClick={togglePanel} disabled={busy}>
        {busy ? '產生檔案中' : '準備切片'}
      </Button>
      {open && (
        <div
          role="dialog"
          aria-label="3D 模型匯出"
          className="absolute right-0 z-50 mt-2 max-h-[calc(100vh-72px)] w-[min(440px,calc(100vw-24px))]
                     space-y-4 overflow-y-auto rounded-xl border border-border bg-surface-overlay p-4 shadow-2xl"
        >
          <div>
            <p className="text-sm font-semibold text-fg">匯出 3D 模型</p>
            <p className="mt-1 text-[10px] leading-relaxed text-fg-subtle">
              STL、OBJ、PLY 會自動轉為毫米，下載後可直接匯入 Cura、PrusaSlicer 或 OrcaSlicer。
            </p>
          </div>

          {formatGroup('3D 列印格式', PRINT_FORMATS)}
          {formatGroup('交換與預覽格式', INTERCHANGE_FORMATS)}

          <div className="grid grid-cols-1 gap-2 border-t border-border pt-3 text-xs text-fg-muted">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectionOnly}
                onChange={(event) => setSelectionOnly(event.target.checked)}
              />
              僅匯出已選取物件
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={applyModifiers}
                onChange={(event) => setApplyModifiers(event.target.checked)}
              />
              套用修改器
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={triangulate}
                onChange={(event) => setTriangulate(event.target.checked)}
              />
              三角化網格
            </label>
          </div>

          <PrintReadinessPanel
            report={report}
            loading={inspectionBusy}
            stale={stale}
            error={inspectionError}
            minWallThicknessMm={minWallThicknessMm}
            overhangAngleDeg={overhangAngleDeg}
            onMinWallThicknessChange={setMinWallThicknessMm}
            onOverhangAngleChange={setOverhangAngleDeg}
            onCheck={() => void runInspection()}
          />

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>取消</Button>
            <Button
              variant={report?.status === 'review' ? 'primary' : 'subtle'}
              icon="export"
              disabled={downloadDisabled}
              onClick={() => onExport(exportOptions())}
            >
              {downloadLabel}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
})
