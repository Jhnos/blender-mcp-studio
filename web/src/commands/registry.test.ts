import { describe, expect, it, vi } from 'vitest'
import { createCommandRegistry } from './registry'

describe('command registry', () => {
  it('registers unique commands and searches title plus keywords', () => {
    const registry = createCommandRegistry()
    const run = vi.fn()
    registry.register({
      id: 'scene.refresh',
      title: '刷新場景預覽',
      keywords: ['refresh', 'preview'],
      isAvailable: () => true,
      run,
    })

    expect(registry.search('preview').map((command) => command.id)).toEqual(['scene.refresh'])
    expect(registry.search('刷新').map((command) => command.id)).toEqual(['scene.refresh'])
    expect(() => registry.register({
      id: 'scene.refresh',
      title: '再次刷新',
      keywords: [],
      isAvailable: () => true,
      run,
    })).toThrow(/duplicate/i)
  })

  it('excludes unavailable commands from list and search', () => {
    const registry = createCommandRegistry()
    registry.register({
      id: 'scene.redo',
      title: '重做',
      keywords: ['redo'],
      isAvailable: () => false,
      run: vi.fn(),
    })

    expect(registry.list()).toEqual([])
    expect(registry.search('redo')).toEqual([])
  })

  it('ranks title prefix before title and keyword matches', () => {
    const registry = createCommandRegistry()
    const create = (id: string, title: string, keywords: string[]) => ({
      id, title, keywords, isAvailable: () => true, run: vi.fn(),
    })
    registry.register(create('keyword', '開啟面板', ['場景']))
    registry.register(create('contains', '重新整理場景', []))
    registry.register(create('prefix', '場景預覽', []))

    expect(registry.search('場景').map((command) => command.id)).toEqual([
      'prefix', 'contains', 'keyword',
    ])
  })
})
