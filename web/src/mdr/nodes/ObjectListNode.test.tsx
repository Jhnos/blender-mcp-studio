import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ObjectListNode } from './ObjectListNode'
import { useBatchSelectionStore } from '../../stores/batchSelectionStore'
import { useChatStore } from '../../stores/chatStore'
import type { Dispatch } from '../actions'

const firstScene = {
  objects: [
    { name: 'Cube', type: 'MESH' },
    { name: 'Light', type: 'LIGHT' },
  ],
}

const nodeProps = (dispatch: Dispatch) => ({
  node: { type: 'object-list' },
  dispatch,
  renderChild: () => null,
})

beforeEach(() => {
  useBatchSelectionStore.getState().clear()
  useChatStore.setState({ sceneRefreshTick: 0 })
})

describe('ObjectListNode batch targets', () => {
  it('supports select all, partial indeterminate state, and clear', async () => {
    const dispatch = vi.fn<Dispatch>().mockResolvedValue(firstScene)
    render(<ObjectListNode {...nodeProps(dispatch)} />)
    await screen.findByText('Cube')

    const selectAll = screen.getByRole('checkbox', { name: '全選場景物件' })
    fireEvent.click(selectAll)
    expect(screen.getByText('已選 2 個')).toBeVisible()
    expect(screen.getByRole('checkbox', { name: '選取 Cube' })).toBeChecked()

    fireEvent.click(screen.getByRole('checkbox', { name: '選取 Cube' }))
    expect(selectAll).toHaveProperty('indeterminate', true)
    expect(screen.getByText('已選 1 個')).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: '清除批次目標' }))
    expect(selectAll).not.toBeChecked()
    expect(screen.queryByText(/已選/)).not.toBeInTheDocument()
  })

  it('prunes selected names that disappear after scene refresh', async () => {
    const dispatch = vi.fn<Dispatch>()
      .mockResolvedValueOnce(firstScene)
      .mockResolvedValue({ objects: [{ name: 'Light', type: 'LIGHT' }] })
    render(<ObjectListNode {...nodeProps(dispatch)} />)
    await screen.findByText('Cube')
    act(() => useBatchSelectionStore.getState().replace(['Cube', 'Light']))

    act(() => useChatStore.getState().triggerSceneRefresh())

    await waitFor(() => {
      expect(useBatchSelectionStore.getState().selectedNames).toEqual(['Light'])
    })
    expect(screen.queryByText('Cube')).not.toBeInTheDocument()
  })
})
