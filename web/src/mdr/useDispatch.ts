import { useMemo } from 'react'
import { createDispatch, type Dispatch } from './actions'
import { registerInspector } from './nodes/register'

// Register node components + backend actions once, at module load (idempotent).
registerInspector()

// API base — same sub-path the WebSocket/fetch use ("/blender").
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '')

/** Shared action dispatcher for every zone (inspector, stage, chat). */
export function useDispatch(): Dispatch {
  return useMemo(() => createDispatch({ base: BASE }), [])
}
