import { useMemo, useState } from 'react'
import {
  toBatchTransformRequest,
  validateBatchTransform,
  type BatchTransformDraft,
  type BatchTransformReceipt,
  type Vector3Tuple,
} from '../domain/batchTransform'
import type { Dispatch } from '../mdr/actions'
import { useChatStore } from '../stores/chatStore'
import { Button, SegmentedControl } from './ui'

type TransformMode = 'move' | 'rotate' | 'scale'
type TextVector = [string, string, string]

interface TransformTextDraft {
  move: TextVector
  rotate: TextVector
  scale: TextVector
}

interface BatchTransformPanelProps {
  dispatch: Dispatch
  selectedNames: readonly string[]
}

const MODE_OPTIONS = [
  { value: 'move', label: '移動 mm' },
  { value: 'rotate', label: '旋轉 °' },
  { value: 'scale', label: '縮放 %' },
] satisfies { value: TransformMode; label: string }[]

const MODE_META: Record<TransformMode, { title: string; unit: string }> = {
  move: { title: '移動', unit: 'mm' },
  rotate: { title: '旋轉', unit: '°' },
  scale: { title: '縮放', unit: '%' },
}

const AXES = [
  { label: 'X', color: 'text-red-400 border-red-400/40 focus:border-red-400' },
  { label: 'Y', color: 'text-emerald-400 border-emerald-400/40 focus:border-emerald-400' },
  { label: 'Z', color: 'text-sky-400 border-sky-400/40 focus:border-sky-400' },
] as const

const emptyTextDraft = (): TransformTextDraft => ({
  move: ['0', '0', '0'],
  rotate: ['0', '0', '0'],
  scale: ['0', '0', '0'],
})

const numericVector = (vector: TextVector): Vector3Tuple => vector.map((value) => {
  const trimmed = value.trim()
  return trimmed === '' ? Number.NaN : Number(trimmed)
}) as Vector3Tuple

const numericDraft = (draft: TransformTextDraft): BatchTransformDraft => ({
  translationMm: numericVector(draft.move),
  rotationDeg: numericVector(draft.rotate),
  scalePercent: numericVector(draft.scale),
})

const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : String(error)

export function BatchTransformPanel({ dispatch, selectedNames }: BatchTransformPanelProps) {
  const [mode, setMode] = useState<TransformMode>('move')
  const [draft, setDraft] = useState<TransformTextDraft>(emptyTextDraft)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const triggerSceneRefresh = useChatStore((state) => state.triggerSceneRefresh)
  const parsedDraft = useMemo(() => numericDraft(draft), [draft])
  const validation = useMemo(() => validateBatchTransform(parsedDraft), [parsedDraft])
  const allZero = [...draft.move, ...draft.rotate, ...draft.scale]
    .every((value) => value.trim() !== '' && Number(value) === 0)
  const meta = MODE_META[mode]

  const updateAxis = (axis: number, value: string) => {
    setDraft((current) => {
      const vector = [...current[mode]] as TextVector
      vector[axis] = value
      return { ...current, [mode]: vector }
    })
    setError(null)
    setSuccess(null)
  }

  const reset = () => {
    setDraft(emptyTextDraft())
    setError(null)
    setSuccess(null)
  }

  const apply = async () => {
    if (!validation.valid || selectedNames.length === 0 || busy) return
    setBusy(true)
    setError(null)
    setSuccess(null)
    try {
      const receipt = await dispatch(
        'scene.batch-transform',
        toBatchTransformRequest(selectedNames, parsedDraft),
      ) as BatchTransformReceipt
      setDraft(emptyTextDraft())
      setSuccess(receipt.message)
      triggerSceneRefresh()
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  const validationMessage = validation.valid || allZero ? null : validation.message

  return (
    <section
      id="batch-transform-panel"
      aria-label="批次變形"
      className="mt-2 space-y-3 rounded-xl border border-border bg-surface-sunken/70 p-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-fg">變形工作條</p>
          <p className="mt-0.5 text-[10px] text-fg-subtle">增量套用 · 一次復原</p>
        </div>
        <SegmentedControl
          value={mode}
          options={MODE_OPTIONS}
          onChange={setMode}
          aria-label="變形模式"
        />
      </div>

      <div className="grid grid-cols-3 gap-2">
        {AXES.map((axis, index) => {
          const inputId = `batch-${mode}-${axis.label.toLowerCase()}`
          return (
            <label key={axis.label} htmlFor={inputId} className={`text-[10px] font-semibold ${axis.color.split(' ')[0]}`}>
              {axis.label}
              <input
                id={inputId}
                aria-label={`${meta.title} ${axis.label}（${meta.unit}）`}
                aria-describedby={validationMessage ? 'batch-transform-error' : undefined}
                type="number"
                step="any"
                value={draft[mode][index]}
                onChange={(event) => updateAxis(index, event.target.value)}
                className={`mt-1 w-full rounded-md border bg-surface px-2 py-1.5 font-mono text-xs text-fg outline-none ${axis.color}`}
              />
            </label>
          )
        })}
      </div>

      {validationMessage && (
        <p id="batch-transform-error" role="alert" className="text-[10px] text-danger">
          {validationMessage}
        </p>
      )}
      {error && <p role="alert" className="text-[10px] text-danger">{error}</p>}
      {success && <p role="status" className="text-[10px] text-success">{success} · 可使用復原</p>}

      <div className="flex items-center justify-between gap-2">
        <Button variant="ghost" onClick={reset}>重設增量</Button>
        <Button
          variant="primary"
          disabled={!validation.valid || selectedNames.length === 0 || busy}
          onClick={() => void apply()}
        >
          {busy ? '套用中…' : `套用到 ${selectedNames.length} 個物件`}
        </Button>
      </div>
    </section>
  )
}
