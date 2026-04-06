import { useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useRefinementStore, type RefinementIteration } from '../stores/refinementStore'

// BASE_URL injected by Vite (same sub-path as WebSocket)
const _base = import.meta.env.BASE_URL.replace(/\/$/, '')
const API_BASE = `${location.origin}${_base}`

export function RefinementPanel() {
  const { sessionId } = useChatStore()
  const {
    status, iterations, converged, finalScreenshot, errorMessage,
    currentIterationIndex, startRefinement, setResult, setError, reset, setCurrentIteration,
  } = useRefinementStore()

  const [userRequest, setUserRequest] = useState('')
  const [maxIterations, setMaxIterations] = useState(3)

  const handleRefine = async () => {
    if (!userRequest.trim()) return
    if (!sessionId) {
      setError('尚無活躍 session，請先對話後再精煉')
      return
    }
    startRefinement()
    try {
      const res = await fetch(`${API_BASE}/api/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          user_request: userRequest,
          max_iterations: maxIterations,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText })) as { detail: string }
        setError(err.detail ?? res.statusText)
        return
      }
      const data = await res.json() as {
        converged: boolean
        iterations: RefinementIteration[]
        final_screenshot: string | null
        iteration_count: number
      }
      setResult(data)
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-slate-700 shrink-0">
        <h3 className="text-xs font-bold text-violet-300 uppercase tracking-wider mb-2">
          🔁 Vision 迭代精煉
        </h3>
        <textarea
          value={userRequest}
          onChange={(e) => setUserRequest(e.target.value)}
          placeholder="描述你的3D模型目標（Vision AI 會自動比對並修正）"
          rows={2}
          className="w-full text-xs bg-slate-800 border border-slate-600 rounded px-2 py-1.5
                     text-slate-200 placeholder-slate-500 resize-none focus:outline-none
                     focus:border-violet-500 mb-2"
        />
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs text-slate-500">最大迭代數</span>
          {[1, 2, 3, 5].map((n) => (
            <button
              key={n}
              onClick={() => setMaxIterations(n)}
              className={`text-xs px-2 py-0.5 rounded transition-colors ${
                maxIterations === n
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
              }`}
            >
              {n}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRefine}
            disabled={status === 'running' || !userRequest.trim()}
            className="flex-1 text-xs py-1.5 rounded bg-violet-600 hover:bg-violet-500
                       disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold
                       transition-colors"
          >
            {status === 'running' ? '精煉中...' : '▶ 開始精煉'}
          </button>
          {status !== 'idle' && (
            <button
              onClick={reset}
              className="text-xs px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600
                         text-slate-300 transition-colors"
            >
              重置
            </button>
          )}
        </div>
      </div>

      {/* Status banner */}
      {status === 'running' && (
        <div className="px-3 py-2 bg-violet-900/30 border-b border-violet-800 shrink-0">
          <div className="flex items-center gap-2 text-xs text-violet-300">
            <span className="animate-spin">⟳</span>
            Vision AI 正在分析場景...
          </div>
        </div>
      )}
      {status === 'done' && (
        <div className={`px-3 py-2 border-b shrink-0 ${
          converged
            ? 'bg-green-900/30 border-green-800 text-green-300'
            : 'bg-amber-900/30 border-amber-800 text-amber-300'
        }`}>
          <span className="text-xs">
            {converged ? '✅ 精煉完成！場景符合目標' : `⚠️ 達到最大迭代數 (${iterations.length} 輪)`}
          </span>
        </div>
      )}
      {status === 'error' && (
        <div className="px-3 py-2 bg-red-900/30 border-b border-red-800 shrink-0">
          <span className="text-xs text-red-300">❌ {errorMessage}</span>
        </div>
      )}

      {/* Iterations list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {iterations.length === 0 && status === 'idle' && (
          <p className="text-xs text-slate-600 text-center mt-8">
            啟動精煉後，每輪迭代的 Vision 分析將顯示在這裡
          </p>
        )}

        {iterations.map((it, idx) => (
          <IterationCard
            key={it.iteration}
            iteration={it}
            expanded={currentIterationIndex === idx}
            onToggle={() => setCurrentIteration(currentIterationIndex === idx ? -1 : idx)}
          />
        ))}

        {/* Final screenshot */}
        {finalScreenshot && (
          <div className="mt-2">
            <p className="text-xs text-slate-500 mb-1">最終截圖</p>
            <img
              src={`data:image/png;base64,${finalScreenshot}`}
              alt="Final render"
              className="w-full rounded-lg border border-slate-700 object-contain"
            />
          </div>
        )}
      </div>
    </div>
  )
}

function IterationCard({
  iteration,
  expanded,
  onToggle,
}: {
  iteration: RefinementIteration
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <div className={`rounded-lg border transition-colors ${
      iteration.converged ? 'border-green-700 bg-green-900/20' : 'border-slate-700 bg-slate-800/50'
    }`}>
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400">#{iteration.iteration}</span>
          {iteration.converged
            ? <span className="text-xs text-green-400">✅ 收斂</span>
            : <span className="text-xs text-amber-400">🔄 繼續修正</span>}
          {iteration.commands_executed.length > 0 && (
            <span className="text-xs text-slate-500">
              {iteration.commands_executed.length} 個指令
            </span>
          )}
        </div>
        <span className="text-slate-600 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-slate-700">
          {/* Vision analysis */}
          <div className="mt-2">
            <p className="text-xs text-slate-500 mb-1">Vision 分析</p>
            <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
              {iteration.vision_analysis}
            </p>
          </div>

          {/* Commands */}
          {iteration.commands_executed.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">執行指令</p>
              {iteration.commands_executed.map((cmd, i) => (
                <div key={i} className="text-xs font-mono text-green-400 bg-slate-900 rounded px-2 py-0.5 mb-0.5">
                  {cmd}
                </div>
              ))}
            </div>
          )}

          {/* Iteration screenshot if available */}
          {iteration.screenshot && (
            <div>
              <p className="text-xs text-slate-500 mb-1">此輪截圖</p>
              <img
                src={`data:image/png;base64,${iteration.screenshot}`}
                alt={`Iteration ${iteration.iteration}`}
                className="w-full rounded border border-slate-700 object-contain"
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
