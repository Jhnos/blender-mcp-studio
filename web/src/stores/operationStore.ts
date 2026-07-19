import { create } from 'zustand'

export type OperationStatus = 'running' | 'success' | 'error'
export type OperationRetry = () => void | Promise<void>

export interface OperationRecord {
  id: string
  label: string
  status: OperationStatus
  timestamp: number
  message?: string
  retry?: OperationRetry
}

interface OperationState {
  operations: OperationRecord[]
  begin: (label: string, retry?: OperationRetry) => string
  succeed: (id: string, message: string) => void
  fail: (id: string, message: string) => void
  clear: () => void
}

const HISTORY_LIMIT = 5
let sequence = 0

const createOperationId = (): string => {
  sequence += 1
  return `operation-${Date.now()}-${sequence}`
}

export const useOperationStore = create<OperationState>((set, get) => {
  const complete = (id: string, status: 'success' | 'error', message: string) => {
    if (!get().operations.some((operation) => operation.id === id)) {
      throw new Error(`Unknown operation: ${id}`)
    }
    set((state) => ({
      operations: state.operations.map((operation) =>
        operation.id === id ? { ...operation, status, message } : operation),
    }))
  }

  return {
    operations: [],
    begin: (label, retry) => {
      const id = createOperationId()
      const operation: OperationRecord = {
        id,
        label,
        status: 'running',
        timestamp: Date.now(),
        ...(retry ? { retry } : {}),
      }
      set((state) => ({
        operations: [operation, ...state.operations].slice(0, HISTORY_LIMIT),
      }))
      return id
    },
    succeed: (id, message) => complete(id, 'success', message),
    fail: (id, message) => complete(id, 'error', message),
    clear: () => set({ operations: [] }),
  }
})
