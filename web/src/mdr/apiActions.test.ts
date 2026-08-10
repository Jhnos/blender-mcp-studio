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

describe('print.readiness action', () => {
  it('maps client-neutral options to the REST contract', async () => {
    const report = { status: 'ready', metrics: {}, issues: [], analysis_truncated: false }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(report), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const dispatch = createDispatch({ base: '/blender' })

    const result = await dispatch('print.readiness', {
      selectionOnly: true,
      applyModifiers: false,
      minWallThicknessMm: 1.2,
      overhangAngleDeg: 50,
    })

    expect(result).toEqual(report)
    expect(fetchMock).toHaveBeenCalledWith('/blender/api/print-readiness', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        selection_only: true,
        apply_modifiers: false,
        min_wall_thickness_mm: 1.2,
        overhang_angle_deg: 50,
      }),
    }))
  })
})

describe('scene.batch-transform action', () => {
  it('sends one client-neutral incremental transform request', async () => {
    const receipt = {
      object_names: ['A', 'B'],
      affected_count: 2,
      message: 'Updated 2 objects',
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(receipt), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const dispatch = createDispatch({ base: '/blender' })

    const result = await dispatch('scene.batch-transform', {
      object_names: ['A', 'B'],
      translation_mm: [10, 0, 0],
      rotation_deg: [0, 0, 15],
      scale_percent: [5, 5, 5],
    })

    expect(result).toEqual(receipt)
    expect(fetchMock).toHaveBeenCalledWith(
      '/blender/api/scene/batch-transform',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          object_names: ['A', 'B'],
          translation_mm: [10, 0, 0],
          rotation_deg: [0, 0, 15],
          scale_percent: [5, 5, 5],
        }),
      }),
    )
  })
})
