import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { __resetActions, createDispatch } from './actions'
import { registerApiActions } from './apiActions'

beforeEach(() => {
  __resetActions()
  registerApiActions()
})

afterEach(() => vi.restoreAllMocks())

describe('export.scene action', () => {
  it('sends all slicer options to the backend', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('mesh', { status: 200, headers: { 'Content-Type': 'model/stl' } }),
    )
    const dispatch = createDispatch({ base: '/blender' })

    const result = await dispatch('export.scene', {
      format: 'stl',
      selectionOnly: true,
      applyModifiers: false,
      triangulate: true,
    })

    expect(result).toBeInstanceOf(Blob)
    expect(fetchMock).toHaveBeenCalledWith('/blender/api/export', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        format: 'stl',
        selection_only: true,
        apply_modifiers: false,
        triangulate: true,
      }),
    }))
  })
})
