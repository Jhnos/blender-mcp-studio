import { useChatStore } from '../stores/chatStore'
import { SegmentedControl, StatusBadge } from './ui'

// ---------------------------------------------------------------------------
// AppHeader — title, connection status (dual-encoded badge), and the global
// simple/advanced disclosure toggle that drives progressive disclosure.
// ---------------------------------------------------------------------------

export function AppHeader() {
  const isConnected = useChatStore((s) => s.isConnected)
  const uiMode = useChatStore((s) => s.uiMode)
  const setUiMode = useChatStore((s) => s.setUiMode)

  return (
    <header className="flex items-center justify-between border-b border-border bg-surface-raised px-4 py-2.5">
      <div className="flex items-center gap-2.5">
        <svg viewBox="0 0 48 48" className="h-6 w-6" aria-hidden>
          <path d="M24 8 L38 16 L24 24 L10 16 Z" fill="var(--color-accent-hover)" />
          <path d="M24 24 L38 16 L38 32 L24 40 Z" fill="var(--color-accent)" />
          <path d="M24 24 L10 16 L10 32 L24 40 Z" fill="#5f45cc" />
        </svg>
        <span className="text-base font-semibold tracking-tight text-fg">Blender MCP Studio</span>
      </div>

      <div className="flex items-center gap-3">
        <StatusBadge
          status={isConnected ? 'success' : 'danger'}
          label={isConnected ? '已連線' : '等待連線'}
          pulse={!isConnected}
        />
        <SegmentedControl<'basic' | 'advanced'>
          aria-label="介面模式"
          value={uiMode}
          onChange={setUiMode}
          options={[
            { value: 'basic', label: '簡易' },
            { value: 'advanced', label: '進階', icon: 'settings' },
          ]}
        />
      </div>
    </header>
  )
}
