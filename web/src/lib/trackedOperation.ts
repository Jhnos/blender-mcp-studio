import { useOperationStore, type OperationRetry } from '../stores/operationStore'
import { errorMessage } from './errorMessage'

export interface TrackedOptions<T> {
  /** Message shown when the operation succeeds; a function receives the result. */
  success: string | ((result: T) => string)
  /** Set false to run without recording — e.g. a background poll nobody asked for. */
  track?: boolean
  /**
   * Offer a retry that re-runs this exact operation. Only set it when re-running
   * is genuinely safe — an incremental transform would move the objects twice.
   *
   * The retry is built here rather than by the caller on purpose: a component
   * that hands in `() => itsOwnCallback()` has to reference that callback before
   * it is declared, which the react-hooks rules reject for good reason.
   */
  retryable?: boolean
  /** Toggled true for the duration, so the caller keeps no try/finally of its own. */
  setBusy?: (busy: boolean) => void
  /** Local cleanup or panel-local error display. The store is already updated. */
  onError?: (message: string, error: unknown) => void
}

/**
 * Run one user-visible operation and record its lifecycle in the shared store.
 *
 * The begin/succeed/fail dance was hand-written at five call sites. Four of them
 * reported into the operation store and one — the print-readiness inspection —
 * only set panel-local state, so a failed inspection never appeared in the
 * status centre. Routing every operation through here is what makes that kind of
 * omission a missing call rather than a silently different code path.
 *
 * Errors are not re-thrown: the store already holds the outcome and callers
 * respond through `onError`. Re-throwing would force every call site back into
 * the try/catch this exists to remove.
 */
export async function runTracked<T>(
  label: string,
  run: () => Promise<T>,
  options: TrackedOptions<T>,
): Promise<void> {
  const { success, track = true, retryable = false, setBusy, onError } = options
  const retry: OperationRetry | undefined = retryable
    ? () => runTracked(label, run, options)
    : undefined
  const store = useOperationStore.getState()
  const operationId = track ? store.begin(label, retry) : null

  setBusy?.(true)
  try {
    const result = await run()
    if (operationId !== null) {
      const message = typeof success === 'function' ? success(result) : success
      useOperationStore.getState().succeed(operationId, message)
    }
  } catch (error) {
    const message = errorMessage(error)
    if (operationId !== null) {
      useOperationStore.getState().fail(operationId, message)
    }
    onError?.(message, error)
  } finally {
    setBusy?.(false)
  }
}
