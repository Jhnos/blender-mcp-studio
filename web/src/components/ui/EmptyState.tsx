import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

// ---------------------------------------------------------------------------
// EmptyState — one consistent treatment for "nothing here yet". A clear
// signifier (icon) + plain message + optional next action, instead of the
// scattered one-line hints. Reduces the "blank canvas" freeze for new users.
// ---------------------------------------------------------------------------

interface EmptyStateProps {
  icon?: IconName
  title: string
  hint?: string
  children?: ReactNode  // optional action(s), e.g. example prompt chips
  className?: string
}

export function EmptyState({ icon = 'info', title, hint, children, className = '' }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2 px-6 py-10 text-center ${className}`}>
      <Icon name={icon} size={28} className="text-fg-subtle" />
      <p className="text-sm text-fg-muted">{title}</p>
      {hint && <p className="text-xs text-fg-subtle max-w-[240px]">{hint}</p>}
      {children && <div className="mt-2 flex flex-wrap justify-center gap-1.5">{children}</div>}
    </div>
  )
}
