import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useOperationStore } from './operationStore'

beforeEach(() => useOperationStore.getState().clear())

describe('operation lifecycle store', () => {
  it('tracks running, success, and error states newest first', () => {
    const first = useOperationStore.getState().begin('刷新預覽')
    useOperationStore.getState().succeed(first, '預覽已更新')
    const second = useOperationStore.getState().begin('批次變形')
    useOperationStore.getState().fail(second, 'Blender is offline')

    expect(useOperationStore.getState().operations).toMatchObject([
      { id: second, label: '批次變形', status: 'error', message: 'Blender is offline' },
      { id: first, label: '刷新預覽', status: 'success', message: '預覽已更新' },
    ])
  })

  it('caps history at five records', () => {
    for (let index = 0; index < 6; index += 1) {
      const id = useOperationStore.getState().begin(`Operation ${index}`)
      useOperationStore.getState().succeed(id, `Done ${index}`)
    }

    const operations = useOperationStore.getState().operations
    expect(operations).toHaveLength(5)
    expect(operations[0].message).toBe('Done 5')
    expect(operations.at(-1)?.message).toBe('Done 1')
  })

  it('stores retry only when the caller explicitly supplies one', () => {
    const retry = vi.fn()
    const refresh = useOperationStore.getState().begin('刷新預覽', retry)
    const transform = useOperationStore.getState().begin('批次變形')
    useOperationStore.getState().fail(refresh, 'Offline')
    useOperationStore.getState().fail(transform, 'Unknown outcome')

    const operations = useOperationStore.getState().operations
    expect(operations.find((item) => item.id === refresh)?.retry).toBe(retry)
    expect(operations.find((item) => item.id === transform)?.retry).toBeUndefined()
  })

  it('fails loudly when completing an unknown operation', () => {
    expect(() => useOperationStore.getState().succeed('missing', 'Done')).toThrow(/unknown/i)
    expect(() => useOperationStore.getState().fail('missing', 'Failed')).toThrow(/unknown/i)
  })
})
