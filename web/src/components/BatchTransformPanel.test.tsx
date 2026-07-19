import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { BatchTransformPanel } from './BatchTransformPanel'
import { useChatStore } from '../stores/chatStore'
import type { Dispatch } from '../mdr/actions'

const receipt = {
  object_names: ['A', 'B'],
  affected_count: 2,
  message: 'Updated 2 objects',
}

beforeEach(() => {
  useChatStore.setState({ sceneRefreshTick: 0 })
})

describe('BatchTransformPanel', () => {
  it('retains all unit modes and sends one request with one scene refresh', async () => {
    const dispatch = vi.fn<Dispatch>().mockResolvedValue(receipt)
    render(<BatchTransformPanel dispatch={dispatch} selectedNames={['A', 'B']} />)

    const moveX = screen.getByLabelText('移動 X（mm）')
    fireEvent.change(moveX, { target: { value: '10' } })
    fireEvent.click(screen.getByRole('radio', { name: '旋轉 °' }))
    const rotateZ = screen.getByLabelText('旋轉 Z（°）')
    fireEvent.change(rotateZ, { target: { value: '15' } })
    fireEvent.click(screen.getByRole('radio', { name: '縮放 %' }))
    const scaleY = screen.getByLabelText('縮放 Y（%）')
    fireEvent.change(scaleY, { target: { value: '5' } })

    fireEvent.click(screen.getByRole('button', { name: '套用到 2 個物件' }))

    expect(dispatch).toHaveBeenCalledTimes(1)
    expect(dispatch).toHaveBeenCalledWith('scene.batch-transform', {
      object_names: ['A', 'B'],
      translation_mm: [10, 0, 0],
      rotation_deg: [0, 0, 15],
      scale_percent: [0, 5, 0],
    })
    expect(await screen.findByRole('status')).toHaveTextContent('Updated 2 objects')
    expect(useChatStore.getState().sceneRefreshTick).toBe(1)

    fireEvent.click(screen.getByRole('radio', { name: '移動 mm' }))
    expect(screen.getByLabelText('移動 X（mm）')).toHaveValue(0)
  })

  it('preserves targets and draft after a failed request', async () => {
    const dispatch = vi.fn<Dispatch>().mockRejectedValue(new Error('Blender is offline'))
    render(<BatchTransformPanel dispatch={dispatch} selectedNames={['A', 'B']} />)

    const moveX = screen.getByLabelText('移動 X（mm）')
    fireEvent.change(moveX, { target: { value: '10' } })
    fireEvent.click(screen.getByRole('button', { name: '套用到 2 個物件' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Blender is offline')
    expect(moveX).toHaveValue(10)
    expect(useChatStore.getState().sceneRefreshTick).toBe(0)
  })

  it('disables apply for zero and invalid scale deltas', async () => {
    const dispatch = vi.fn<Dispatch>()
    render(<BatchTransformPanel dispatch={dispatch} selectedNames={['A']} />)

    expect(screen.getByRole('button', { name: '套用到 1 個物件' })).toBeDisabled()
    fireEvent.click(screen.getByRole('radio', { name: '縮放 %' }))
    const scaleX = screen.getByLabelText('縮放 X（%）')
    fireEvent.change(scaleX, { target: { value: '-100' } })

    expect(screen.getByRole('alert')).toHaveTextContent('greater than -100')
    expect(screen.getByRole('button', { name: '套用到 1 個物件' })).toBeDisabled()
    expect(dispatch).not.toHaveBeenCalled()
  })

  it('resets every retained mode explicitly', async () => {
    render(<BatchTransformPanel dispatch={vi.fn<Dispatch>()} selectedNames={['A']} />)
    fireEvent.change(screen.getByLabelText('移動 X（mm）'), { target: { value: '10' } })
    fireEvent.click(screen.getByRole('button', { name: '重設增量' }))

    await waitFor(() => expect(screen.getByLabelText('移動 X（mm）')).toHaveValue(0))
  })
})
