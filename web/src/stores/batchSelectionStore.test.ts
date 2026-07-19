import { beforeEach, describe, expect, it } from 'vitest'
import { useBatchSelectionStore } from './batchSelectionStore'

beforeEach(() => useBatchSelectionStore.getState().clear())

describe('batch selection store', () => {
  it('toggles one target without duplicates', () => {
    const store = useBatchSelectionStore.getState()
    store.toggle('A')
    store.toggle('A')
    store.toggle('B')

    expect(useBatchSelectionStore.getState().selectedNames).toEqual(['B'])
  })

  it('selects all with stable order and removes invalid names', () => {
    useBatchSelectionStore.getState().replace(['B', '', 'A', 'B', ' C '])

    expect(useBatchSelectionStore.getState().selectedNames).toEqual(['B', 'A'])
  })

  it('prunes targets absent from the refreshed scene', () => {
    useBatchSelectionStore.getState().replace(['A', 'B'])
    useBatchSelectionStore.getState().prune(['B', 'C'])

    expect(useBatchSelectionStore.getState().selectedNames).toEqual(['B'])
  })

  it('clears every target', () => {
    useBatchSelectionStore.getState().replace(['A', 'B'])
    useBatchSelectionStore.getState().clear()

    expect(useBatchSelectionStore.getState().selectedNames).toEqual([])
  })
})
