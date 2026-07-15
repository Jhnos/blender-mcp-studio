import type { ComponentType } from 'react'
import type { UINode } from './types'
import type { Dispatch } from './actions'

// ===========================================================================
// Component Registry — the engine depends on this map, never on concrete
// component classes. Adding a component = registering it; the engine and
// existing components stay untouched (OCP).
// ===========================================================================

/** Props every registered node component receives from the engine. */
export interface NodeProps {
  node: UINode
  /** Central action dispatcher (components never call fetch directly). */
  dispatch: Dispatch
  /** Render a child node (engine-provided; enables composition). */
  renderChild: (child: UINode, key?: string | number) => React.ReactNode
}

export type NodeComponent = ComponentType<NodeProps>

const registry = new Map<string, NodeComponent>()

/** Register a component under a `type`. Throws on duplicate to catch collisions. */
export function register(type: string, component: NodeComponent): void {
  if (registry.has(type)) {
    throw new Error(`[mdr] duplicate registry type: "${type}"`)
  }
  registry.set(type, component)
}

/** Resolve a `type` to its component, or undefined if unknown. */
export function resolve(type: string): NodeComponent | undefined {
  return registry.get(type)
}

/** All registered types — used by the surface-area bijection audit. */
export function registeredTypes(): string[] {
  return [...registry.keys()].sort()
}

/** Test/HMR helper: clear the registry. */
export function __resetRegistry(): void {
  registry.clear()
}
