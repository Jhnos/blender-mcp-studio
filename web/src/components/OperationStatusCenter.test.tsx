import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useOperationStore } from '../stores/operationStore'
import { OperationStatusCenter } from './OperationStatusCenter'

beforeEach(() => useOperationStore.getState().clear())

describe('OperationStatusCenter', () => {
  it('renders the current status and five recent records', () => {
    for (let index = 0; index < 6; index += 1) {
      const id = useOperationStore.getState().begin(`操作 ${index}`)
      useOperationStore.getState().succeed(id, `完成 ${index}`)
    }
    render(<OperationStatusCenter />)

    expect(screen.getByRole('button', { name: '最近操作' })).toHaveTextContent('操作 5')
    fireEvent.click(screen.getByRole('button', { name: '最近操作' }))

    expect(screen.getAllByRole('listitem')).toHaveLength(5)
    const list = screen.getByRole('list', { name: '操作記錄' })
    expect(within(list).getByText('完成 5')).toBeVisible()
    expect(within(list).queryByText('完成 0')).not.toBeInTheDocument()
  })

  it('shows retry only for an operation that supplies it', () => {
    const retry = vi.fn()
    const refresh = useOperationStore.getState().begin('刷新預覽', retry)
    useOperationStore.getState().fail(refresh, 'Blender is offline')
    const transform = useOperationStore.getState().begin('批次變形')
    useOperationStore.getState().fail(transform, 'Unknown outcome')
    render(<OperationStatusCenter />)
    fireEvent.click(screen.getByRole('button', { name: '最近操作' }))

    const retryButtons = screen.getAllByRole('button', { name: '重試' })
    expect(retryButtons).toHaveLength(1)
    fireEvent.click(retryButtons[0])
    expect(retry).toHaveBeenCalledTimes(1)
  })

  it('announces the newest completion in a polite live region', () => {
    const id = useOperationStore.getState().begin('匯出 STL')
    useOperationStore.getState().succeed(id, 'STL 已產生')
    render(<OperationStatusCenter />)

    expect(screen.getByRole('status')).toHaveTextContent('STL 已產生')
  })

  it('renders nothing until an operation exists', () => {
    const { container } = render(<OperationStatusCenter />)

    expect(container).toBeEmptyDOMElement()
  })
})
