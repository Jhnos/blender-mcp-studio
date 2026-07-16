import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import { InspectorShell } from './InspectorShell'
import { useChatStore } from '../stores/chatStore'

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
)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('dummy run — real engine, dummy backend input', () => {
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
