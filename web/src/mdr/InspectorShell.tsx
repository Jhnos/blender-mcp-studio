import { useChatStore } from '../stores/chatStore'
import { SchemaRenderer } from './SchemaRenderer'
import { inspectorSchema } from './inspector.schema'
import { useDispatch } from './useDispatch'

// ---------------------------------------------------------------------------
// InspectorShell — mounts the MDR engine for the right panel. It knows nothing
// about objects/materials/snapshots; it just renders the schema. Swapping the
// inspector layout = editing inspector.schema.ts, not this file (OCP).
// ---------------------------------------------------------------------------

export function InspectorShell() {
  const uiMode = useChatStore((s) => s.uiMode)
  const dispatch = useDispatch()

  return (
    <div className="flex-1 overflow-y-auto">
      <SchemaRenderer schema={inspectorSchema} mode={uiMode} dispatch={dispatch} />
    </div>
  )
}
