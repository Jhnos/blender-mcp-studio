import { useChatStore } from '../../stores/chatStore'
import { EmptyState } from '../../components/ui'

// ---------------------------------------------------------------------------
// log-viewer — execution record. Reads client state (chatStore.blenderLogs);
// no backend action needed. Advanced-level section (hidden in basic mode).
// ---------------------------------------------------------------------------

export function LogViewerNode() {
  const blenderLogs = useChatStore((s) => s.blenderLogs)

  if (blenderLogs.length === 0) {
    return <EmptyState icon="log" title="尚無執行記錄" />
  }
  return (
    <div className="space-y-2 px-2">
      {[...blenderLogs].reverse().map((log, i) => (
        <div
          key={i}
          className={`rounded-md border p-2.5 text-xs font-mono whitespace-pre-wrap break-all ${
            log.isError
              ? 'border-danger/40 bg-danger-bg text-danger'
              : 'border-border bg-surface-sunken text-success'
          }`}
        >
          <div className="mb-1 text-fg-subtle">{log.timestamp}</div>
          {log.output}
        </div>
      ))}
    </div>
  )
}
