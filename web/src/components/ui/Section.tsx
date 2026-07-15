import { useId, type ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

// ---------------------------------------------------------------------------
// Section — a collapsible region, the workhorse of progressive disclosure.
// Baymard research: vertical "Expanded Sections" beat horizontal tabs for
// primary navigation (tabs get missed on scroll). This replaces the 6-tab bar.
// Collapse state is controlled by the parent so it can be persisted.
// ---------------------------------------------------------------------------

interface SectionProps {
  id: string
  title: string
  icon?: IconName
  open: boolean
  onToggle: (id: string) => void
  count?: number
  headerRight?: ReactNode
  children: ReactNode
}

export function Section({
  id, title, icon, open, onToggle, count, headerRight, children,
}: SectionProps) {
  const panelId = useId()
  return (
    <section className="border-b border-border">
      <div className="flex items-center">
        <button
          onClick={() => onToggle(id)}
          aria-expanded={open}
          aria-controls={panelId}
          className="flex flex-1 items-center gap-2 px-3 py-2.5 text-left
                     text-fg-muted hover:text-fg transition-colors
                     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset"
        >
          <Icon name={open ? 'chevron-down' : 'chevron-right'} size={14} className="text-fg-subtle shrink-0" />
          {icon && <Icon name={icon} size={15} className="shrink-0" />}
          <span className="text-sm font-semibold tracking-tight">{title}</span>
          {count != null && (
            <span className="rounded-full bg-surface-overlay px-1.5 text-xs text-fg-subtle tabular-nums">
              {count}
            </span>
          )}
        </button>
        {headerRight && <div className="pr-2 shrink-0">{headerRight}</div>}
      </div>
      {open && (
        <div id={panelId} className="pb-2">
          {children}
        </div>
      )}
    </section>
  )
}
