import { useState } from 'react'
import { useOperationStore, type OperationStatus } from '../stores/operationStore'
import { Icon, type IconName } from './ui'

const STATUS_ICON: Record<OperationStatus, IconName> = {
  running: 'refresh',
  success: 'success',
  error: 'danger',
}

const STATUS_CLASS: Record<OperationStatus, string> = {
  running: 'text-accent',
  success: 'text-success',
  error: 'text-danger',
}

const time = new Intl.DateTimeFormat('zh-TW', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

export function OperationStatusCenter() {
  const operations = useOperationStore((state) => state.operations)
  const [open, setOpen] = useState(false)
  const newest = operations[0]

  if (!newest) return null

  return (
    <div className="relative">
      <button
        type="button"
        aria-label="最近操作"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex max-w-40 items-center gap-1.5 rounded-md px-2 py-1 text-[10px] text-fg-muted hover:bg-surface-overlay focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <Icon
          name={STATUS_ICON[newest.status]}
          size={13}
          className={`${STATUS_CLASS[newest.status]} ${newest.status === 'running' ? 'animate-spin' : ''}`}
        />
        <span className="truncate">{newest.label}</span>
      </button>

      <span role="status" aria-live="polite" className="sr-only">
        {newest.message ?? `${newest.label}進行中`}
      </span>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-72 overflow-hidden rounded-xl border border-border bg-surface-raised shadow-xl">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <p className="text-xs font-semibold text-fg">最近操作</p>
            <span className="text-[9px] text-fg-subtle">最多 5 筆</span>
          </div>
          <ul aria-label="操作記錄" className="divide-y divide-border">
            {operations.map((operation) => (
              <li key={operation.id} className="flex gap-2 px-3 py-2.5">
                <Icon
                  name={STATUS_ICON[operation.status]}
                  size={14}
                  className={`mt-0.5 shrink-0 ${STATUS_CLASS[operation.status]} ${operation.status === 'running' ? 'animate-spin' : ''}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="truncate text-[11px] font-medium text-fg">{operation.label}</span>
                    <time className="ml-auto shrink-0 text-[9px] text-fg-subtle">
                      {time.format(operation.timestamp)}
                    </time>
                  </div>
                  {operation.message && (
                    <p className={`mt-0.5 text-[10px] ${operation.status === 'error' ? 'text-danger' : 'text-fg-muted'}`}>
                      {operation.message}
                    </p>
                  )}
                  {operation.retry && operation.status === 'error' && (
                    <button
                      type="button"
                      onClick={() => void operation.retry?.()}
                      className="mt-1 text-[10px] font-medium text-accent hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    >
                      重試
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
