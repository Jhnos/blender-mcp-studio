import { create } from 'zustand'

export interface RefinementIteration {
  iteration: number
  vision_analysis: string
  commands_executed: string[]
  converged: boolean
  screenshot?: string | null  // base64 PNG of this iteration
}

export type RefineStatus = 'idle' | 'running' | 'done' | 'error'

interface RefinementStore {
  status: RefineStatus
  iterations: RefinementIteration[]
  converged: boolean | null
  finalScreenshot: string | null
  errorMessage: string | null
  currentIterationIndex: number  // which iteration panel is expanded

  startRefinement: () => void
  setResult: (data: {
    converged: boolean
    iterations: RefinementIteration[]
    final_screenshot: string | null
  }) => void
  setError: (msg: string) => void
  reset: () => void
  setCurrentIteration: (idx: number) => void
}

export const useRefinementStore = create<RefinementStore>((set) => ({
  status: 'idle',
  iterations: [],
  converged: null,
  finalScreenshot: null,
  errorMessage: null,
  currentIterationIndex: 0,

  startRefinement: () =>
    set({ status: 'running', iterations: [], converged: null, errorMessage: null, finalScreenshot: null }),

  setResult: ({ converged, iterations, final_screenshot }) =>
    set({
      status: 'done',
      converged,
      iterations,
      finalScreenshot: final_screenshot,
      currentIterationIndex: iterations.length - 1,
    }),

  setError: (errorMessage) => set({ status: 'error', errorMessage }),

  reset: () =>
    set({
      status: 'idle',
      iterations: [],
      converged: null,
      finalScreenshot: null,
      errorMessage: null,
      currentIterationIndex: 0,
    }),

  setCurrentIteration: (currentIterationIndex) => set({ currentIterationIndex }),
}))
