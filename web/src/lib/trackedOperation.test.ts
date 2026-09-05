import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useOperationStore } from '../stores/operationStore'
import { errorMessage } from './errorMessage'
import { runTracked } from './trackedOperation'

const operations = () => useOperationStore.getState().operations

describe('errorMessage', () => {
  it('reads the message off an Error', () => {
    expect(errorMessage(new Error('boom'))).toBe('boom')
  })

  it('stringifies anything else, because catch binds unknown', () => {
    expect(errorMessage('plain string')).toBe('plain string')
    expect(errorMessage(42)).toBe('42')
    expect(errorMessage(null)).toBe('null')
  })
})

describe('runTracked', () => {
  beforeEach(() => {
    useOperationStore.getState().clear()
  })

  it('records a success with the resolved message', async () => {
    await runTracked('匯出 STL', async () => 'artifact', { success: 'done' })

    expect(operations()).toHaveLength(1)
    expect(operations()[0]).toMatchObject({ label: '匯出 STL', status: 'success', message: 'done' })
  })

  it('derives the success message from the result when given a function', async () => {
    await runTracked('批次變形', async () => ({ message: '已更新 2 個物件' }), {
      success: (receipt) => receipt.message,
    })

    expect(operations()[0].message).toBe('已更新 2 個物件')
  })

  it('records a failure and does not re-throw', async () => {
    const onError = vi.fn()

    await expect(
      runTracked('列印就緒檢查', async () => { throw new Error('Blender is offline') }, {
        success: 'never',
        onError,
      }),
    ).resolves.toBeUndefined()

    expect(operations()[0]).toMatchObject({ status: 'error', message: 'Blender is offline' })
    expect(onError).toHaveBeenCalledWith('Blender is offline', expect.any(Error))
  })

  it('toggles busy around the run, including on failure', async () => {
    const seen: boolean[] = []
    const setBusy = (busy: boolean) => { seen.push(busy) }

    await runTracked('x', async () => { throw new Error('nope') }, { success: 'y', setBusy })

    expect(seen).toEqual([true, false])
  })

  it('records nothing when tracking is off', async () => {
    await runTracked('background poll', async () => 'ok', { success: 'ok', track: false })

    expect(operations()).toHaveLength(0)
  })

  it('still reports errors locally when tracking is off', async () => {
    const onError = vi.fn()

    await runTracked('background poll', async () => { throw new Error('gone') }, {
      success: 'ok',
      track: false,
      onError,
    })

    expect(operations()).toHaveLength(0)
    expect(onError).toHaveBeenCalledWith('gone', expect.any(Error))
  })

  it('offers a retry only when the operation is declared retryable', async () => {
    await runTracked('刷新預覽', async () => 'ok', { success: 'ok', retryable: true })
    await runTracked('批次變形', async () => 'ok', { success: 'ok' })

    const [batch, refresh] = operations()
    expect(refresh.retry).toBeTypeOf('function')
    // A mutation must never offer to run itself twice.
    expect(batch.retry).toBeUndefined()
  })

  it('re-runs the same operation when the retry is invoked', async () => {
    const run = vi.fn().mockResolvedValue('ok')
    await runTracked('刷新預覽', run, { success: 'ok', retryable: true })

    const [operation] = operations()
    await operation.retry?.()

    expect(run).toHaveBeenCalledTimes(2)
    expect(operations()).toHaveLength(2)
  })
})
