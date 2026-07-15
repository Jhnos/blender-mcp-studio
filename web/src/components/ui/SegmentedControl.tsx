import { Icon, type IconName } from './Icon'

// ---------------------------------------------------------------------------
// SegmentedControl — a single, keyboard-accessible toggle group. Replaces the
// ad-hoc button rows (mode toggle, asset type, resolution). Uses roving
// tabindex + arrow keys (WAI-ARIA radiogroup pattern).
// ---------------------------------------------------------------------------

export interface Segment<T extends string> {
  value: T
  label: string
  icon?: IconName
}

interface SegmentedControlProps<T extends string> {
  value: T
  options: Segment<T>[]
  onChange: (value: T) => void
  size?: 'sm' | 'md'
  'aria-label'?: string
  className?: string
}

export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  size = 'sm',
  className = '',
  ...rest
}: SegmentedControlProps<T>) {
  const pad = size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm'

  const onKey = (e: React.KeyboardEvent, idx: number) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    e.preventDefault()
    const next = e.key === 'ArrowRight'
      ? (idx + 1) % options.length
      : (idx - 1 + options.length) % options.length
    onChange(options[next].value)
  }

  return (
    <div
      role="radiogroup"
      aria-label={rest['aria-label']}
      className={`inline-flex gap-0.5 rounded-lg bg-surface-sunken p-0.5 ${className}`}
    >
      {options.map((opt, idx) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(opt.value)}
            onKeyDown={(e) => onKey(e, idx)}
            className={`inline-flex items-center gap-1.5 rounded-md font-medium transition-colors
                        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${pad}
                        ${active
                          ? 'bg-surface-overlay text-fg shadow-sm'
                          : 'text-fg-subtle hover:text-fg-muted'}`}
          >
            {opt.icon && <Icon name={opt.icon} size={size === 'sm' ? 13 : 15} />}
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
