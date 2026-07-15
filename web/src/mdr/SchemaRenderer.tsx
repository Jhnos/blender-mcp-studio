import { createElement, useCallback, useState, type ReactNode } from 'react'
import { Section } from '../components/ui'
import { resolve } from './registry'
import type { Dispatch } from './actions'
import type { DisclosureLevel, UINode, UISchema, UISection } from './types'
import { visibleSections } from './types'

// ===========================================================================
// SchemaRenderer — reads a UISchema and renders it. The engine never imports
// concrete node components; it resolves them from the registry by `type`.
// ===========================================================================

/** Visible, non-crashing placeholder for an unknown `type`. */
function FallbackNode({ type }: { type: string }) {
  // Hard signal in dev; graceful placeholder in the UI (never a white screen).
  if (import.meta.env.DEV) console.error(`[mdr] no component registered for type "${type}"`)
  return (
    <div
      role="note"
      data-mdr-fallback={type}
      className="m-2 rounded-md border border-dashed border-warning/50 bg-warning-bg px-3 py-2 text-xs text-warning"
    >
      未知元件 <code className="font-mono">{type}</code>（尚未註冊）
    </div>
  )
}

interface NodeRendererProps {
  node: UINode
  dispatch: Dispatch
}

/** Render one node: resolve its component from the registry, or fall back. */
export function NodeRenderer({ node, dispatch }: NodeRendererProps): ReactNode {
  const renderChild = useCallback(
    (child: UINode, key?: string | number): ReactNode => (
      <NodeRenderer key={key ?? child.id ?? child.type} node={child} dispatch={dispatch} />
    ),
    [dispatch],
  )

  // Dynamic dispatch: the component is looked up in the registry at render time
  // (the whole point of the engine). Using createElement with a lowercase
  // binding is the idiomatic way to render a resolved component.
  const component = resolve(node.type)
  if (!component) return <FallbackNode type={node.type} />
  return createElement(component, { node, dispatch, renderChild })
}

interface SchemaRendererProps {
  schema: UISchema
  mode: DisclosureLevel
  dispatch: Dispatch
  /** Optional slot rendered on the right of a section header (e.g. refresh). */
  sectionHeaderRight?: (section: UISection) => ReactNode
}

export function SchemaRenderer({
  schema, mode, dispatch, sectionHeaderRight,
}: SchemaRendererProps) {
  const sections = visibleSections(schema, mode)

  // Section open/close state (progressive disclosure), seeded from defaultOpen.
  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(schema.sections.map((s) => [s.id, s.defaultOpen ?? true])),
  )
  const toggle = useCallback(
    (id: string) => setOpen((o) => ({ ...o, [id]: !o[id] })),
    [],
  )

  return (
    <div className="flex flex-col">
      {sections.map((section) => (
        <Section
          key={section.id}
          id={section.id}
          title={section.title}
          icon={section.icon}
          open={open[section.id] ?? true}
          onToggle={toggle}
          headerRight={sectionHeaderRight?.(section)}
        >
          <NodeRenderer node={section.body} dispatch={dispatch} />
        </Section>
      ))}
    </div>
  )
}
