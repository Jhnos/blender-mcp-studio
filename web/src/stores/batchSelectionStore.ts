import { create } from 'zustand'

interface BatchSelectionState {
  selectedNames: string[]
  toggle: (name: string) => void
  replace: (names: readonly string[]) => void
  clear: () => void
  prune: (availableNames: readonly string[]) => void
}

const uniqueValidNames = (names: readonly string[]): string[] => {
  const seen = new Set<string>()
  return names.filter((name) => {
    const valid = name.length > 0 && name === name.trim() && !seen.has(name)
    if (valid) seen.add(name)
    return valid
  })
}

export const useBatchSelectionStore = create<BatchSelectionState>((set) => ({
  selectedNames: [],
  toggle: (name) => set((state) => ({
    selectedNames: state.selectedNames.includes(name)
      ? state.selectedNames.filter((selected) => selected !== name)
      : uniqueValidNames([...state.selectedNames, name]),
  })),
  replace: (names) => set({ selectedNames: uniqueValidNames(names) }),
  clear: () => set({ selectedNames: [] }),
  prune: (availableNames) => {
    const available = new Set(availableNames)
    set((state) => ({
      selectedNames: state.selectedNames.filter((name) => available.has(name)),
    }))
  },
}))
