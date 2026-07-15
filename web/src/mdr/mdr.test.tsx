import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  register, resolve, registeredTypes, __resetRegistry,
  registerAction, createDispatch, registeredActions, __resetActions,
  validateSchema, collectTypes, visibleSections, SchemaRenderer,
  type NodeProps, type UISchema,
} from './index'

beforeEach(() => {
  __resetRegistry()
  __resetActions()
})

// --- Registry -------------------------------------------------------------

describe('registry', () => {
  const Dummy = ({ node }: NodeProps) => <div>dummy:{node.type}</div>

  it('registers and resolves by type', () => {
    register('dummy', Dummy)
    expect(resolve('dummy')).toBe(Dummy)
    expect(registeredTypes()).toEqual(['dummy'])
  })

  it('returns undefined for unknown type', () => {
    expect(resolve('nope')).toBeUndefined()
  })

  it('throws on duplicate registration (catches silent collisions)', () => {
    register('dummy', Dummy)
    expect(() => register('dummy', Dummy)).toThrow(/duplicate registry type/)
  })
})

// --- Action dispatcher ----------------------------------------------------

describe('action dispatcher', () => {
  it('dispatches a registered action with payload + context', async () => {
    const spy = vi.fn(async (payload: unknown) => ({ echo: payload }))
    registerAction('thing.do', spy)
    const dispatch = createDispatch({ base: '/blender' })
    const result = await dispatch('thing.do', { a: 1 })
    expect(result).toEqual({ echo: { a: 1 } })
    expect(spy).toHaveBeenCalledWith({ a: 1 }, { base: '/blender' })
  })

  it('THROWS on unknown action-id (no silent no-op)', async () => {
    const dispatch = createDispatch({ base: '/blender' })
    await expect(dispatch('typo.action')).rejects.toThrow(/unknown action/)
  })

  it('throws on duplicate action registration', () => {
    registerAction('x', async () => null)
    expect(() => registerAction('x', async () => null)).toThrow(/duplicate action id/)
    expect(registeredActions()).toEqual(['x'])
  })
})

// --- Schema validation ----------------------------------------------------

describe('schema validation', () => {
  const good: UISchema = {
    version: 1,
    sections: [
      { id: 's1', title: 'Scene', level: 'basic', body: { type: 'object-list' } },
    ],
  }

  it('accepts a well-formed schema', () => {
    expect(validateSchema(good)).toEqual({ valid: true, errors: [] })
  })

  it('reports all problems, not just the first', () => {
    const bad = { version: 'x', sections: [{ id: 's', title: 't' /* no level/body */ }] }
    const res = validateSchema(bad)
    expect(res.valid).toBe(false)
    expect(res.errors.length).toBeGreaterThanOrEqual(2)
  })

  it('collectTypes walks nested children', () => {
    const nested: UISchema = {
      version: 1,
      sections: [{
        id: 'g', title: 'G', level: 'basic',
        body: { type: 'field-group', children: [{ type: 'a' }, { type: 'b' }] },
      }],
    }
    expect([...collectTypes(nested)].sort()).toEqual(['a', 'b', 'field-group'])
  })
})

// --- Renderer: dispatch + graceful fallback + level filtering --------------

describe('SchemaRenderer', () => {
  const schema: UISchema = {
    version: 1,
    sections: [
      { id: 'scene', title: '場景', level: 'basic', body: { type: 'known' } },
      { id: 'log', title: '記錄', level: 'advanced', body: { type: 'ghost' } },
    ],
  }

  const Known = ({ node }: NodeProps) => <div data-testid="known">rendered:{node.type}</div>

  it('renders a registered component via the registry', () => {
    register('known', Known)
    register('ghost', Known)
    const dispatch = createDispatch({ base: '/b' })
    render(<SchemaRenderer schema={schema} mode="advanced" dispatch={dispatch} />)
    expect(screen.getAllByTestId('known').length).toBe(2)
  })

  it('renders a VISIBLE fallback for unknown type (never crashes / white screen)', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const dispatch = createDispatch({ base: '/b' })
    // nothing registered → both bodies unknown
    render(<SchemaRenderer schema={schema} mode="advanced" dispatch={dispatch} />)
    const fallbacks = document.querySelectorAll('[data-mdr-fallback]')
    expect(fallbacks.length).toBe(2)
    expect(screen.getAllByText(/未知元件/).length).toBe(2)
  })

  it('basic mode hides advanced sections (progressive disclosure)', () => {
    expect(visibleSections(schema, 'basic').map((s) => s.id)).toEqual(['scene'])
    expect(visibleSections(schema, 'advanced').map((s) => s.id)).toEqual(['scene', 'log'])

    register('known', Known)
    register('ghost', Known)
    const dispatch = createDispatch({ base: '/b' })
    render(<SchemaRenderer schema={schema} mode="basic" dispatch={dispatch} />)
    expect(screen.getByText('場景')).toBeInTheDocument()
    expect(screen.queryByText('記錄')).not.toBeInTheDocument()
  })
})

// --- Surface-area bijection: schema types ⊆ registry ----------------------

describe('surface-area audit helper', () => {
  it('detects a schema type with no registered component (orphan)', () => {
    register('object-list', (({ node }: NodeProps) => <span>{node.type}</span>))
    const schema: UISchema = {
      version: 1,
      sections: [
        { id: 'a', title: 'A', level: 'basic', body: { type: 'object-list' } },
        { id: 'b', title: 'B', level: 'basic', body: { type: 'not-registered' } },
      ],
    }
    const missing = [...collectTypes(schema)].filter((t) => !registeredTypes().includes(t))
    expect(missing).toEqual(['not-registered'])
  })
})
