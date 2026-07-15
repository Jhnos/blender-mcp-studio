import { useEffect, useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useRefinementStore, type RefinementIteration } from '../stores/refinementStore'
import { useDispatch } from '../mdr'
import { Button, EmptyState, Icon, SegmentedControl, StatusBadge } from './ui'

// ---------------------------------------------------------------------------
// RefineOverlay — Vision iterative refinement promoted from a passive tab to a
// focused AI action. Opened on demand, run via dispatch('refine.run').
// Each iteration shows the AI's rationale + executed commands (explainability).
// ---------------------------------------------------------------------------

function IterationCard({ it, expanded, onToggle }: {
  it: RefinementIteration; expanded: boolean; onToggle: () => void
}) {
  return (
    <div className={`rounded-lg border ${it.converged ? 'border-success/40 bg-success-bg' : 'border-border bg-surface-raised'}`}>
      <button onClick={onToggle} className="flex w-full items-center justify-between px-3 py-2 text-left">
        <span className="flex items-center gap-2 text-xs">
          <span className="font-mono text-fg-subtle">#{it.iteration}</span>
          {it.converged
            ? <StatusBadge status="success" label="收斂" />
            : <StatusBadge status="warning" label="繼續修正" />}
          {it.commands_executed.length > 0 && (
            <span className="text-fg-subtle">{it.commands_executed.length} 個指令</span>
          )}
        </span>
        <Icon name={expanded ? 'chevron-down' : 'chevron-right'} size={14} className="text-fg-subtle" />
      </button>
      {expanded && (
        <div className="space-y-2 border-t border-border px-3 py-2">
          <div>
            <p className="mb-1 text-xs text-fg-subtle">Vision 分析（AI 為何這麼做）</p>
            <p className="whitespace-pre-wrap text-xs leading-relaxed text-fg-muted">{it.vision_analysis}</p>
          </div>
          {it.commands_executed.length > 0 && (
            <div>
              <p className="mb-1 text-xs text-fg-subtle">執行指令</p>
              {it.commands_executed.map((cmd, i) => (
                <div key={i} className="mb-0.5 rounded bg-surface-sunken px-2 py-0.5 font-mono text-xs text-success">{cmd}</div>
              ))}
            </div>
          )}
          {it.screenshot && (
            <img src={`data:image/png;base64,${it.screenshot}`} alt={`第 ${it.iteration} 輪`}
              className="w-full rounded border border-border object-contain" />
          )}
        </div>
      )}
    </div>
  )
}

export function RefineOverlay({ open, onClose }: { open: boolean; onClose: () => void }) {
  const dispatch = useDispatch()
  const sessionId = useChatStore((s) => s.sessionId)
  const {
    status, iterations, converged, finalScreenshot, errorMessage,
    currentIterationIndex, startRefinement, setResult, setError, reset, setCurrentIteration,
  } = useRefinementStore()
  const [goal, setGoal] = useState('')
  const [maxIter, setMaxIter] = useState('3')

  // Escape to close (a11y).
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open, onClose])

  if (!open) return null

  const run = async () => {
    if (!goal.trim()) return
    if (!sessionId) { setError('尚無活躍 session，請先對話後再精煉'); return }
    startRefinement()
    try {
      const data = await dispatch('refine.run', {
        sessionId, userRequest: goal, maxIterations: Number(maxIter),
      }) as { converged: boolean; iterations: RefinementIteration[]; final_screenshot: string | null }
      setResult(data)
    } catch (e) { setError(String(e)) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-label="Vision 自動精煉"
        className="relative flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-xl
                   border border-border bg-surface-raised shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="flex items-center gap-2 text-sm font-semibold text-fg">
            <Icon name="ai" size={16} className="text-accent" /> Vision 自動精煉
          </span>
          <Button variant="ghost" icon="close" iconOnly title="關閉" onClick={onClose} />
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <p className="mb-3 text-xs text-fg-subtle">
            描述你的目標，Vision AI 會反覆比對場景並自動修正，直到符合目標。
          </p>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            rows={2}
            placeholder="例如：讓桌子的四隻腳一樣長，桌面置中"
            className="mb-3 w-full resize-none rounded-md border border-border bg-surface-sunken px-2.5 py-2
                       text-sm text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <div className="mb-3 flex items-center gap-2 text-xs text-fg-subtle">
            <span>最大迭代</span>
            <SegmentedControl
              aria-label="最大迭代數"
              value={maxIter}
              onChange={setMaxIter}
              options={['1', '2', '3', '5'].map((n) => ({ value: n, label: n }))}
            />
          </div>
          <div className="flex gap-2">
            <Button variant="primary" size="md" icon="refine" className="flex-1"
              onClick={() => void run()} disabled={status === 'running' || !goal.trim()}>
              {status === 'running' ? '精煉中...' : '開始精煉'}
            </Button>
            {status !== 'idle' && <Button variant="subtle" size="md" onClick={reset}>重置</Button>}
          </div>

          {status === 'running' && (
            <div className="mt-3"><StatusBadge status="info" label="Vision AI 正在分析場景..." pulse /></div>
          )}
          {status === 'done' && (
            <div className="mt-3">
              <StatusBadge
                status={converged ? 'success' : 'warning'}
                label={converged ? '精煉完成，場景符合目標' : `達到最大迭代數（${iterations.length} 輪）`}
              />
            </div>
          )}
          {status === 'error' && <div className="mt-3"><StatusBadge status="danger" label={errorMessage ?? '精煉失敗'} /></div>}

          <div className="mt-3 space-y-2">
            {iterations.length === 0 && status === 'idle' && (
              <EmptyState icon="ai" title="啟動精煉後，每輪 Vision 分析會顯示在這裡" />
            )}
            {iterations.map((it, idx) => (
              <IterationCard key={it.iteration} it={it}
                expanded={currentIterationIndex === idx}
                onToggle={() => setCurrentIteration(currentIterationIndex === idx ? -1 : idx)} />
            ))}
            {finalScreenshot && (
              <div>
                <p className="mb-1 text-xs text-fg-subtle">最終截圖</p>
                <img src={`data:image/png;base64,${finalScreenshot}`} alt="最終結果"
                  className="w-full rounded-lg border border-border object-contain" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
