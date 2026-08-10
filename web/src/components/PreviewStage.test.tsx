import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Dispatch } from '../mdr/actions'
import { useChatStore } from '../stores/chatStore'
import { useOperationStore } from '../stores/operationStore'
import { useBatchSelectionStore } from '../stores/batchSelectionStore'
import { PreviewStage } from './PreviewStage'

const { dispatch } = vi.hoisted(() => ({ dispatch: vi.fn<Dispatch>() }))

vi.mock('../mdr', async (importOriginal) => {
  const original = await importOriginal<typeof import('../mdr')>()
  return { ...original, useDispatch: () => dispatch }
})

beforeEach(() => {
  dispatch.mockReset()
  dispatch.mockImplementation(async (action) => {
    if (action === 'preview.get') return new Blob(['png'], { type: 'image/png' })
    if (action === 'undo') return { success: true, action: 'undo', message: 'undo ok' }
    if (action === 'redo') return { success: true, action: 'redo', message: 'redo ok' }
    throw new Error(`Unexpected action: ${action}`)
  })
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:preview')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  useChatStore.setState({ liveScreenshot: null, sceneRefreshTick: 0 })
  useOperationStore.getState().clear()
  useBatchSelectionStore.getState().clear()
  useBatchSelectionStore.getState().prune([])
})

describe('PreviewStage operation status', () => {
  it('opens the curated palette with mod-k and selects all known batch targets', async () => {
    useBatchSelectionStore.getState().prune(['CatBody', 'CatTail'])
    render(<PreviewStage />)
    await screen.findByAltText('Blender 模型預覽')

    fireEvent.keyDown(window, { key: 'k', metaKey: true })
    const search = screen.getByRole('searchbox', { name: '搜尋指令' })
    fireEvent.change(search, { target: { value: 'select all' } })
    fireEvent.keyDown(search, { key: 'Enter' })

    expect(useBatchSelectionStore.getState().selectedNames).toEqual(['CatBody', 'CatTail'])
    expect(screen.queryByRole('dialog', { name: 'Studio 指令面板' })).not.toBeInTheDocument()
  })

  it('records manual preview refresh and offers an explicit retry path', async () => {
    render(<PreviewStage />)
    await screen.findByAltText('Blender 模型預覽')
    dispatch.mockClear()

    fireEvent.click(screen.getByTitle('刷新預覽'))

    await waitFor(() => expect(useOperationStore.getState().operations[0]).toMatchObject({
      label: '刷新預覽',
      status: 'success',
      message: '預覽已更新',
    }))
    expect(useOperationStore.getState().operations[0].retry).toEqual(expect.any(Function))
    expect(screen.getByRole('button', { name: '最近操作' })).toBeVisible()
  })

  it('records undo completion without serializing the transport envelope', async () => {
    render(<PreviewStage />)
    await screen.findByAltText('Blender 模型預覽')

    fireEvent.click(screen.getByTitle('復原 (⌘Z)'))

    await waitFor(() => expect(useOperationStore.getState().operations[0]).toMatchObject({
      label: '復原',
      status: 'success',
      message: 'undo ok',
    }))
    expect(useOperationStore.getState().operations[0].message).not.toContain('[object Object]')
  })

  it('records an undo failure and does not offer unsafe retry', async () => {
    dispatch.mockImplementation(async (action) => {
      if (action === 'preview.get') return new Blob(['png'], { type: 'image/png' })
      if (action === 'undo') throw new Error('Blender is offline')
      throw new Error(`Unexpected action: ${action}`)
    })
    render(<PreviewStage />)
    await screen.findByAltText('Blender 模型預覽')

    fireEvent.click(screen.getByTitle('復原 (⌘Z)'))

    await waitFor(() => expect(useOperationStore.getState().operations[0]).toMatchObject({
      label: '復原',
      status: 'error',
      message: 'Blender is offline',
    }))
    expect(useOperationStore.getState().operations[0].retry).toBeUndefined()
  })
})
