import { registerAction, type ActionContext } from './actions'
import type {
  BatchTransformReceipt,
  BatchTransformRequest,
} from '../domain/batchTransform'
import type {
  PrintReadinessOptions,
  PrintReadinessReport,
} from '../domain/printReadiness'

// ===========================================================================
// API action handlers — the ONLY place the frontend talks to the backend.
// Node components emit `dispatch('object.delete', {...})`; they never know a
// URL. Swapping/mocking the backend happens here (and the T3 dummy run swaps
// the server underneath these, not the components).
//
// Every non-OK response THROWS (NO_SILENT_FALLBACK) so callers can surface it.
// ===========================================================================

async function http(
  method: string,
  url: string,
  body?: unknown,
): Promise<Response> {
  const res = await fetch(url, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res
      .json()
      .then((d: { detail?: string }) => d.detail)
      .catch(() => res.statusText)
    throw new Error(detail || `HTTP ${res.status}`)
  }
  return res
}

const json = <T>(r: Response) => r.json() as Promise<T>
const enc = encodeURIComponent

export interface SceneObject { name: string; type: string }
export interface SnapshotItem {
  id: string; label: string; created_at: string; session_id: string; thumbnail: string | null
}
export interface PHAsset {
  id: string; name: string; categories: string[]; tags: string[]
  thumbnail_url: string; download_count: number
}

/** Register the real backend handlers. Call once at app startup. */
export function registerApiActions(): void {
  // --- Scene / objects ---
  registerAction('scene.list', async (_p, { base }: ActionContext) =>
    json<{ objects: SceneObject[] }>(await http('GET', `${base}/api/scene`)),
  )
  registerAction('object.select', async (p, { base }) => {
    const { name } = p as { name: string }
    await http('POST', `${base}/api/object/${enc(name)}/select`)
    return { ok: true }
  })
  registerAction('object.rename', async (p, { base }) => {
    const { name, newName } = p as { name: string; newName: string }
    await http('PUT', `${base}/api/object/${enc(name)}`, { new_name: newName })
    return { ok: true }
  })
  registerAction('object.delete', async (p, { base }) => {
    const { name } = p as { name: string }
    await http('DELETE', `${base}/api/object/${enc(name)}`)
    return { ok: true }
  })
  registerAction('scene.batch-transform', async (p, { base }) =>
    json<BatchTransformReceipt>(await http(
      'POST',
      `${base}/api/scene/batch-transform`,
      p as BatchTransformRequest,
    )),
  )

  // --- Snapshots ---
  registerAction('snapshot.list', async (_p, { base }) =>
    json<{ snapshots: SnapshotItem[] }>(await http('GET', `${base}/api/snapshots`)),
  )
  registerAction('snapshot.save', async (p, { base }) => {
    const { label } = (p ?? {}) as { label?: string }
    await http('POST', `${base}/api/snapshot`, { label: label || 'Snapshot' })
    return { ok: true }
  })
  registerAction('snapshot.restore', async (p, { base }) => {
    const { id } = p as { id: string }
    await http('POST', `${base}/api/snapshot/${enc(id)}/restore`)
    return { ok: true }
  })
  registerAction('snapshot.delete', async (p, { base }) => {
    const { id } = p as { id: string }
    await http('DELETE', `${base}/api/snapshot/${enc(id)}`)
    return { ok: true }
  })

  // --- Materials (Poly Haven) ---
  registerAction('material.search', async (p, { base }) => {
    const { query, assetType, limit } = p as { query: string; assetType: string; limit?: number }
    const qs = new URLSearchParams({ q: query, asset_type: assetType, limit: String(limit ?? 24) })
    return json<{ results: PHAsset[] }>(await http('GET', `${base}/api/materials/search?${qs}`))
  })
  registerAction('material.apply', async (p, { base }) => {
    const { assetId, resolution, fileFormat, applyAs } = p as {
      assetId: string; resolution: string; fileFormat: string; applyAs: string
    }
    await http('POST', `${base}/api/materials/apply`, {
      asset_id: assetId, resolution, file_format: fileFormat, apply_as: applyAs,
    })
    return { ok: true }
  })

  // --- Viewport preview / export / history (blob + JSON) ---
  registerAction('preview.get', async (p, { base }) => {
    const { t } = (p ?? {}) as { t?: number }
    const res = await http('GET', `${base}/api/preview?t=${t ?? ''}`)
    return res.blob()
  })
  registerAction('export.scene', async (p, { base }) => {
    const { format, selectionOnly, applyModifiers, triangulate } = p as {
      format: string
      selectionOnly: boolean
      applyModifiers: boolean
      triangulate: boolean
    }
    const res = await http('POST', `${base}/api/export`, {
      format,
      selection_only: selectionOnly,
      apply_modifiers: applyModifiers,
      triangulate,
    })
    return res.blob()
  })
  registerAction('print.readiness', async (p, { base }) => {
    const {
      selectionOnly,
      applyModifiers,
      minWallThicknessMm,
      overhangAngleDeg,
    } = p as PrintReadinessOptions
    return json<PrintReadinessReport>(await http('POST', `${base}/api/print-readiness`, {
      selection_only: selectionOnly,
      apply_modifiers: applyModifiers,
      min_wall_thickness_mm: minWallThicknessMm,
      overhang_angle_deg: overhangAngleDeg,
    }))
  })
  registerAction('undo', async (_p, { base }) =>
    json<{ success: boolean; message: string }>(await http('POST', `${base}/api/undo`)),
  )
  registerAction('redo', async (_p, { base }) =>
    json<{ success: boolean; message: string }>(await http('POST', `${base}/api/redo`)),
  )

  // --- Vision iterative refinement (an AI operation, not a passive panel) ---
  registerAction('refine.run', async (p, { base }) => {
    const { sessionId, userRequest, maxIterations } = p as {
      sessionId: string; userRequest: string; maxIterations: number
    }
    return json<{
      converged: boolean
      iterations: unknown[]
      final_screenshot: string | null
      iteration_count: number
    }>(await http('POST', `${base}/api/refine`, {
      session_id: sessionId,
      user_request: userRequest,
      max_iterations: maxIterations,
    }))
  })
}
