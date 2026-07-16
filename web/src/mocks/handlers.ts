import { http, HttpResponse, ws } from 'msw'
import { MOCK_MATERIALS, MOCK_OBJECTS, MOCK_PREVIEW_SVG, MOCK_SNAPSHOTS } from './fixtures'

// Mutable dummy state so delete/rename/save reflect in the UI during the run.
let objects = [...MOCK_OBJECTS]
let snapshots = [...MOCK_SNAPSHOTS]

const B = '/blender'
const ok = () => HttpResponse.json({ success: true, message: 'ok' })

export const handlers = [
  http.get(`${B}/api/health`, () => HttpResponse.json({ status: 'ok' })),

  // Scene / objects
  http.get(`${B}/api/scene`, () => HttpResponse.json({ objects })),
  http.post(`${B}/api/object/:name/select`, () => ok()),
  http.put(`${B}/api/object/:name`, async ({ params, request }) => {
    const { new_name } = (await request.json()) as { new_name: string }
    objects = objects.map((o) => (o.name === params.name ? { ...o, name: new_name } : o))
    return ok()
  }),
  http.delete(`${B}/api/object/:name`, ({ params }) => {
    objects = objects.filter((o) => o.name !== params.name)
    return ok()
  }),

  // Snapshots
  http.get(`${B}/api/snapshots`, () => HttpResponse.json({ snapshots })),
  http.post(`${B}/api/snapshot`, async ({ request }) => {
    const { label } = (await request.json()) as { label: string }
    snapshots = [...snapshots, {
      id: `snap_${snapshots.length + 1}`, label: label || 'Snapshot',
      created_at: '2026-07-15T11:00:00Z', session_id: 'mock', thumbnail: null,
    }]
    return ok()
  }),
  http.post(`${B}/api/snapshot/:id/restore`, () => ok()),
  http.delete(`${B}/api/snapshot/:id`, ({ params }) => {
    snapshots = snapshots.filter((s) => s.id !== params.id)
    return ok()
  }),

  // Materials
  http.get(`${B}/api/materials/search`, () => HttpResponse.json({ results: MOCK_MATERIALS })),
  http.post(`${B}/api/materials/apply`, () => ok()),

  // Viewport preview (SVG blob stands in for the render)
  http.get(`${B}/api/preview`, () =>
    new HttpResponse(MOCK_PREVIEW_SVG, { headers: { 'Content-Type': 'image/svg+xml' } })),
  http.post(`${B}/api/export`, () =>
    new HttpResponse(MOCK_PREVIEW_SVG, { headers: { 'Content-Type': 'model/stl' } })),

  // History
  http.post(`${B}/api/undo`, () => HttpResponse.json({ success: true, message: '已復原上一步' })),
  http.post(`${B}/api/redo`, () => HttpResponse.json({ success: true, message: '已重做' })),

  // Vision refine
  http.post(`${B}/api/refine`, () => HttpResponse.json({
    converged: true,
    iteration_count: 2,
    final_screenshot: null,
    iterations: [
      { iteration: 1, vision_analysis: '桌腳長度不一致，正在調整。', commands_executed: ['scale_object(...)'], converged: false, screenshot: null },
      { iteration: 2, vision_analysis: '場景已符合目標。', commands_executed: [], converged: true, screenshot: null },
    ],
  })),
]

// WebSocket mock: accept the connection (→ isConnected = true) and echo a
// canned streamed reply that reports a scene change (drives AI tag + executed
// chip + preview refresh).
// Mirror useWebSocket's URL derivation exactly. A hardcoded host/port silently
// fails to intercept on any other port (e.g. the deployed vite on 19504), so
// the REAL backend leaks into what should be an isolated dummy run — the mock
// appears "on" while live data flows through. Derive, never hardcode.
const _wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:'
const chat = ws.link(`${_wsProto}//${location.host}/blender/ws/chat`)
export const wsHandlers = [
  chat.addEventListener('connection', ({ client }) => {
    client.addEventListener('message', () => {
      // session_id rides along with the reply (a bare session_id message would
      // create an empty assistant bubble via the existing WS handler).
      client.send(JSON.stringify({ status: 'streaming', content: '好的，', session_id: 'mock-session' }))
      client.send(JSON.stringify({ status: 'streaming', content: '正在建立物件…' }))
      client.send(JSON.stringify({
        status: 'done',
        content: '已在場景中央建立一個立方體。',
        blender_output: '✅ 已建立 Cube',
      }))
    })
  }),
]
