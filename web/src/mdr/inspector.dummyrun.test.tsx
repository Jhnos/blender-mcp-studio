import { describe, it, expect, beforeAll, afterAll, afterEach, beforeEach, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import { InspectorShell } from './InspectorShell'
import { useChatStore } from '../stores/chatStore'
import { useBatchSelectionStore } from '../stores/batchSelectionStore'
import { useOperationStore } from '../stores/operationStore'
import { PreviewStage } from '../components/PreviewStage'

// ===========================================================================
// AUTOMATED DUMMY RUN (T3 core, headless).
//
// DUMMY RUN, not mock: the REAL InspectorShell + REAL MDR engine (schema →
// registry → node → dispatch → apiActions → fetch) all run. Only the BACKEND
// INPUT is swapped for fixtures. Proves axis M (mechanism) without Blender,
// the API, or an LLM being up.
//
// Browser-driven checks (layout widths, live WS, screenshots) stay in
// docs/verification/frontend-redesign/dummy-run-plan.md.
// ===========================================================================

const DUMMY_OBJECTS = [
  { name: 'Cube', type: 'MESH' },
  { name: 'Table_Top', type: 'MESH' },
  { name: 'Sun', type: 'LIGHT' },
]

const server = setupServer(
  http.get('*/api/scene', () => HttpResponse.json({ objects: DUMMY_OBJECTS })),
  http.get('*/api/snapshots', () => HttpResponse.json({ snapshots: [] })),
  http.get('*/api/preview', () => new HttpResponse('preview', {
    headers: { 'Content-Type': 'image/png' },
  })),
  http.post('*/api/scene/batch-transform', async ({ request }) => {
    const body = await request.json() as { object_names: string[] }
    return HttpResponse.json({
      object_names: body.object_names,
      affected_count: body.object_names.length,
      message: `Updated ${body.object_names.length} objects`,
    })
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
beforeEach(() => {
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:dummy-preview')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  useBatchSelectionStore.getState().clear()
  useBatchSelectionStore.getState().prune([])
  useOperationStore.getState().clear()
  useChatStore.setState({ sceneRefreshTick: 0, liveScreenshot: null, uiMode: 'basic' })
})
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('dummy run — real engine, dummy backend input', () => {
  it('completes the keyboard batch-productivity path', async () => {
    render(<div><PreviewStage /><InspectorShell /></div>)
    await screen.findByText('Cube')

    fireEvent.keyDown(window, { key: 'k', metaKey: true })
    const search = screen.getByRole('searchbox', { name: '搜尋指令' })
    fireEvent.change(search, { target: { value: 'select all' } })
    fireEvent.keyDown(search, { key: 'Enter' })

    fireEvent.change(await screen.findByLabelText('移動 X（mm）'), { target: { value: '10' } })
    fireEvent.click(screen.getByRole('button', { name: '套用到 3 個物件' }))
    await waitFor(() => expect(useOperationStore.getState().operations[0]).toMatchObject({
      status: 'success',
      message: 'Updated 3 objects',
    }))

    fireEvent.click(screen.getByRole('button', { name: '最近操作' }))
    expect(within(screen.getByRole('list', { name: '操作記錄' }))
      .getByText('Updated 3 objects')).toBeVisible()
  })

  it('inspector populates from the dummy backend (schema→registry→dispatch→http)', async () => {
    render(<InspectorShell />)
    // Every fixture object must reach the screen through the real engine.
    for (const o of DUMMY_OBJECTS) {
      expect(await screen.findByText(o.name)).toBeInTheDocument()
    }
  })

  it('progressive disclosure: basic hides the advanced Log section', async () => {
    useChatStore.setState({ uiMode: 'basic' })
    render(<InspectorShell />)
    expect(await screen.findByText('場景')).toBeInTheDocument()
    expect(screen.queryByText('執行記錄')).not.toBeInTheDocument()
  })

  it('progressive disclosure: advanced reveals the Log section', async () => {
    useChatStore.setState({ uiMode: 'advanced' })
    render(<InspectorShell />)
    expect(await screen.findByText('執行記錄')).toBeInTheDocument()
  })

  it('surfaces a real backend failure instead of silently showing nothing', async () => {
    server.use(http.get('*/api/scene', () => HttpResponse.error()))
    useChatStore.setState({ uiMode: 'basic' })
    render(<InspectorShell />)
    expect(await screen.findByText('無法連線至 Blender')).toBeInTheDocument()
  })
})
