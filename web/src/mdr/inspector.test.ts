import { describe, it, expect } from 'vitest'
import { registeredTypes, registeredActions, collectTypes } from './index'
import { inspectorSchema } from './inspector.schema'
import { registerInspector } from './nodes/register'

// Surface-area bijection: the schema and the registry must line up exactly.
// A schema type with no component = broken panel; a registered component no
// schema references = dead code. Both are caught here.
registerInspector()

describe('inspector surface-area bijection', () => {
  const schemaTypes = [...collectTypes(inspectorSchema)].sort()
  const registered = registeredTypes()

  it('every schema type has a registered component (no orphan reference)', () => {
    const missing = schemaTypes.filter((t) => !registered.includes(t))
    expect(missing).toEqual([])
  })

  it('every registered component is used by the schema (no dead registration)', () => {
    const unused = registered.filter((t) => !schemaTypes.includes(t))
    expect(unused).toEqual([])
  })

  it('registers the expected inspector panels', () => {
    expect(registered).toEqual(['asset-browser', 'log-viewer', 'object-list', 'snapshot-list'])
  })

  it('registers every backend action the panels dispatch', () => {
    // Actions referenced across ObjectList / AssetBrowser / SnapshotList nodes.
    const required = [
      'scene.list', 'object.select', 'object.rename', 'object.delete',
      'snapshot.list', 'snapshot.save', 'snapshot.restore', 'snapshot.delete',
      'material.search', 'material.apply',
    ]
    const actions = registeredActions()
    expect(required.filter((a) => !actions.includes(a))).toEqual([])
  })
})
