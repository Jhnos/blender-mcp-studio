import { Icon, type IconName } from './Icon'

// ---------------------------------------------------------------------------
// StatusBadge — status is ALWAYS dual-encoded (color + icon + text), never
// color alone (WCAG 1.4.1). One source of truth for status semantics so
// "success is green + check" is consistent everywhere.
// ---------------------------------------------------------------------------

export type Status = 'success' | 'warning' | 'danger' | 'info' | 'live' | 'neutral'

const STYLE: Record<Status, { cls: string; icon: IconName }> = {
  success: { cls: 'text-success bg-success-bg', icon: 'success' },
  warning: { cls: 'text-warning bg-warning-bg', icon: 'warning' },
  danger: { cls: 'text-danger bg-danger-bg', icon: 'danger' },
  info: { cls: 'text-info bg-info-bg', icon: 'info' },
  live: { cls: 'text-success bg-success-bg', icon: 'live' },
  neutral: { cls: 'text-fg-muted bg-surface-overlay', icon: 'info' },
}

interface StatusBadgeProps {
  status: Status
  label: string
  pulse?: boolean
  className?: string
}

export function StatusBadge({ status, label, pulse = false, className = '' }: StatusBadgeProps) {
  const { cls, icon } = STYLE[status]
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${cls} ${className}`}
    >
      <Icon name={icon} size={12} className={pulse ? 'animate-pulse' : undefined} />
      {label}
    </span>
  )
}
