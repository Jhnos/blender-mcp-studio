import { register } from '../registry'
import { registerApiActions } from '../apiActions'
import { ObjectListNode } from './ObjectListNode'
import { AssetBrowserNode } from './AssetBrowserNode'
import { SnapshotListNode } from './SnapshotListNode'
import { LogViewerNode } from './LogViewerNode'

// ---------------------------------------------------------------------------
// Single startup point: register inspector node components + backend actions.
// Adding a panel = adding one register() line here + one section in the schema.
// The engine and existing components are never touched (OCP).
// ---------------------------------------------------------------------------

let done = false

export function registerInspector(): void {
  if (done) return // idempotent (HMR / double-mount safe)
  done = true
  register('object-list', ObjectListNode)
  register('asset-browser', AssetBrowserNode)
  register('snapshot-list', SnapshotListNode)
  register('log-viewer', LogViewerNode)
  registerApiActions()
}
