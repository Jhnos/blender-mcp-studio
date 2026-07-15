// ===========================================================================
// Action Dispatcher — behaviour is declared as an action-ID and resolved
// centrally. Components emit `dispatch('object.delete', {...})` and never know
// the API URL. Swapping the backend = changing handlers, not components.
//
// Discipline: an unknown action-ID THROWS (never a silent no-op). A typo in a
// schema must fail loudly, not quietly do nothing (NO_SILENT_FALLBACK).
// ===========================================================================

export interface ActionContext {
  /** API base path, e.g. "/blender". */
  base: string
}

export type ActionHandler = (
  payload: unknown,
  ctx: ActionContext,
) => Promise<unknown>

/** The function threaded to every component to trigger behaviour. */
export type Dispatch = (actionId: string, payload?: unknown) => Promise<unknown>

const handlers = new Map<string, ActionHandler>()

export function registerAction(id: string, handler: ActionHandler): void {
  if (handlers.has(id)) {
    throw new Error(`[mdr] duplicate action id: "${id}"`)
  }
  handlers.set(id, handler)
}

export function hasAction(id: string): boolean {
  return handlers.has(id)
}

export function registeredActions(): string[] {
  return [...handlers.keys()].sort()
}

export function __resetActions(): void {
  handlers.clear()
}

/** Build a Dispatch bound to a context. Unknown action-IDs throw. */
export function createDispatch(ctx: ActionContext): Dispatch {
  return async (actionId, payload) => {
    const handler = handlers.get(actionId)
    if (!handler) {
      // Loud failure by design — surface the typo, don't swallow it.
      throw new Error(`[mdr] unknown action: "${actionId}"`)
    }
    return handler(payload, ctx)
  }
}
