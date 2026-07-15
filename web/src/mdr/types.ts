import type { IconName } from '../components/ui'

// ===========================================================================
// MDR — UI Schema contract (pure data; declares WHAT, never HOW).
// The engine renders this; changing the UI = changing this data, not code.
// ===========================================================================

export type DisclosureLevel = 'basic' | 'advanced'

/** A renderable node. `type` is the registry key; the engine dispatches on it. */
export interface UINode {
  /** Registry key — which component renders this node. */
  type: string
  /** Optional stable id (keys, testing). */
  id?: string
  /** Declarative props handed to the component. No functions/logic here. */
  props?: Record<string, unknown>
  /** Optional child nodes, rendered recursively by the engine. */
  children?: UINode[]
}

/** A top-level collapsible group in the inspector (progressive-disclosure unit). */
export interface UISection {
  id: string
  title: string
  icon?: IconName
  /** `advanced` sections are hidden in basic mode. */
  level: DisclosureLevel
  defaultOpen?: boolean
  /** The content rendered inside the section. */
  body: UINode
}

/** The full inspector schema. `version` gates breaking changes. */
export interface UISchema {
  version: number
  sections: UISection[]
}

// --- Runtime validation (schema is external data → validate before trusting) ---

export function isUINode(v: unknown): v is UINode {
  if (typeof v !== 'object' || v === null) return false
  const n = v as Record<string, unknown>
  if (typeof n.type !== 'string' || n.type.length === 0) return false
  if (n.children !== undefined) {
    if (!Array.isArray(n.children)) return false
    if (!n.children.every(isUINode)) return false
  }
  return true
}

export function isUISection(v: unknown): v is UISection {
  if (typeof v !== 'object' || v === null) return false
  const s = v as Record<string, unknown>
  return (
    typeof s.id === 'string' &&
    typeof s.title === 'string' &&
    (s.level === 'basic' || s.level === 'advanced') &&
    isUINode(s.body)
  )
}

export interface SchemaValidation {
  valid: boolean
  errors: string[]
}

/** Validate a schema shape. Returns all problems, not just the first. */
export function validateSchema(v: unknown): SchemaValidation {
  const errors: string[] = []
  if (typeof v !== 'object' || v === null) {
    return { valid: false, errors: ['schema is not an object'] }
  }
  const s = v as Record<string, unknown>
  if (typeof s.version !== 'number') errors.push('schema.version must be a number')
  if (!Array.isArray(s.sections)) {
    errors.push('schema.sections must be an array')
  } else {
    s.sections.forEach((sec, i) => {
      if (!isUISection(sec)) errors.push(`schema.sections[${i}] is not a valid section`)
    })
  }
  return { valid: errors.length === 0, errors }
}

/** Sections visible at the current disclosure level. basic mode hides advanced. */
export function visibleSections(schema: UISchema, mode: DisclosureLevel): UISection[] {
  if (mode === 'advanced') return schema.sections
  return schema.sections.filter((s) => s.level === 'basic')
}

/** Collect every `type` referenced by a schema (for surface-area bijection audit). */
export function collectTypes(schema: UISchema): Set<string> {
  const types = new Set<string>()
  const walk = (node: UINode) => {
    types.add(node.type)
    node.children?.forEach(walk)
  }
  schema.sections.forEach((sec) => walk(sec.body))
  return types
}
