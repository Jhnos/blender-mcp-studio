import type { PrintReadinessReport } from '../domain/printReadiness'
import { Button, StatusBadge } from './ui'

interface PrintReadinessPanelProps {
  report: PrintReadinessReport | null
  loading: boolean
  stale: boolean
  error: string | null
  minWallThicknessMm: number
  overhangAngleDeg: number
  onMinWallThicknessChange: (value: number) => void
  onOverhangAngleChange: (value: number) => void
  onCheck: () => void
}

const integer = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 })
const decimal = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 2 })

const statusPresentation = (report: PrintReadinessReport) => {
  if (report.status === 'ready') return { status: 'success' as const, label: '可以切片' }
  if (report.status === 'review') return { status: 'warning' as const, label: '需要確認' }
  return { status: 'danger' as const, label: '無法匯出' }
}

export function PrintReadinessPanel({
  report,
  loading,
  stale,
  error,
  minWallThicknessMm,
  overhangAngleDeg,
  onMinWallThicknessChange,
  onOverhangAngleChange,
  onCheck,
}: PrintReadinessPanelProps) {
  const status = report ? statusPresentation(report) : null
  const issues = report
    ? [...report.issues].sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'error' ? -1 : 1))
    : []

  return (
    <section aria-label="3D 列印就緒檢查" className="space-y-3 border-y border-border py-3">
      <div className="flex items-center gap-2">
        <div>
          <p className="text-xs font-semibold text-fg">匯出前健檢</p>
          <p className="mt-0.5 text-[9px] text-fg-subtle">FDM · 0.4 mm 噴嘴基準</p>
        </div>
        <div className="flex-1" />
        {loading && <StatusBadge status="info" label="檢查中" pulse />}
        {!loading && stale && <StatusBadge status="neutral" label="需要重新檢查" />}
        {!loading && !stale && status && <StatusBadge {...status} />}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <label className="text-[10px] text-fg-muted">
          最小壁厚（mm）
          <input
            aria-label="最小壁厚（mm）"
            type="number"
            min="0.01"
            max="10"
            step="0.1"
            value={minWallThicknessMm}
            onChange={(event) => onMinWallThicknessChange(Number(event.target.value))}
            className="mt-1 w-full rounded-md border border-border bg-surface-sunken px-2 py-1.5 text-xs text-fg outline-none focus:border-accent"
          />
        </label>
        <label className="text-[10px] text-fg-muted">
          懸空角度（°）
          <input
            aria-label="懸空角度（°）"
            type="number"
            min="0"
            max="90"
            step="1"
            value={overhangAngleDeg}
            onChange={(event) => onOverhangAngleChange(Number(event.target.value))}
            className="mt-1 w-full rounded-md border border-border bg-surface-sunken px-2 py-1.5 text-xs text-fg outline-none focus:border-accent"
          />
        </label>
      </div>

      {error && (
        <div className="rounded-md border border-danger/40 bg-danger-bg px-3 py-2 text-[10px] text-danger">
          <p>{error}</p>
          <Button variant="ghost" className="mt-1 !px-0 text-danger" onClick={onCheck}>
            重試檢查
          </Button>
        </div>
      )}

      {report && (
        <div className={stale ? 'opacity-50' : ''} aria-disabled={stale}>
          <div className="grid grid-cols-2 overflow-hidden rounded-lg border border-border bg-surface-sunken">
            <div className="col-span-2 border-b border-border px-3 py-2">
              <span className="block text-[9px] uppercase tracking-wider text-fg-subtle">成品尺寸</span>
              <span className="mt-0.5 block font-mono text-sm text-fg">
                {report.metrics.dimensions_mm.map((value) => decimal.format(value)).join(' × ')} mm
              </span>
            </div>
            <div className="border-r border-border px-3 py-2">
              <span className="block text-[9px] text-fg-subtle">三角面</span>
              <span className="font-mono text-xs text-fg">{integer.format(report.metrics.triangle_count)}</span>
            </div>
            <div className="px-3 py-2">
              <span className="block text-[9px] text-fg-subtle">網格物件</span>
              <span className="font-mono text-xs text-fg">{integer.format(report.metrics.object_count)}</span>
            </div>
            <div className="border-r border-t border-border px-3 py-2">
              <span className="block text-[9px] text-fg-subtle">估算體積</span>
              <span className="font-mono text-xs text-fg">
                {integer.format(report.metrics.estimated_volume_mm3)} mm³
              </span>
            </div>
            <div className="border-t border-border px-3 py-2">
              <span className="block text-[9px] text-fg-subtle">表面積</span>
              <span className="font-mono text-xs text-fg">
                {integer.format(report.metrics.surface_area_mm2)} mm²
              </span>
            </div>
          </div>

          {issues.length > 0 && (
            <ul className="mt-2 max-h-32 space-y-1.5 overflow-y-auto" aria-label="健檢問題">
              {issues.map((issue) => (
                <li
                  key={`${issue.code}-${issue.object_names.join('-')}`}
                  data-testid="print-issue"
                  className={`rounded-md border px-2.5 py-2 text-[10px] leading-relaxed ${
                    issue.severity === 'error'
                      ? 'border-danger/35 bg-danger-bg text-danger'
                      : 'border-warning/35 bg-warning-bg text-warning'
                  }`}
                >
                  <span className="font-semibold">{issue.severity === 'error' ? '錯誤' : '注意'} · </span>
                  {issue.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {!loading && (stale || (!report && !error)) && (
        <Button variant="subtle" onClick={onCheck} className="w-full">
          {report ? '重新檢查' : '開始檢查'}
        </Button>
      )}
    </section>
  )
}
