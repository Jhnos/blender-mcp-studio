import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CommandDefinition } from '../commands/types'
import { CommandPalette } from './CommandPalette'

const command = (
  id: string,
  title: string,
  keywords: string[],
  run = vi.fn(),
): CommandDefinition => ({ id, title, keywords, run, isAvailable: () => true })

describe('CommandPalette', () => {
  it('filters commands and executes the active result with Enter', () => {
    const undo = vi.fn()
    const onOpenChange = vi.fn()
    render(
      <CommandPalette
        commands={[
          command('refresh', '刷新場景', ['refresh']),
          command('undo', '復原上一個操作', ['undo'], undo),
        ]}
        open
        onOpenChange={onOpenChange}
      />,
    )
    const search = screen.getByRole('searchbox', { name: '搜尋指令' })

    fireEvent.change(search, { target: { value: 'undo' } })
    expect(screen.getAllByRole('option')).toHaveLength(1)
    fireEvent.keyDown(search, { key: 'Enter' })

    expect(undo).toHaveBeenCalledTimes(1)
    expect(onOpenChange).toHaveBeenLastCalledWith(false)
  })

  it('supports arrow navigation, Escape, and active descendant semantics', () => {
    const first = vi.fn()
    const second = vi.fn()
    const onOpenChange = vi.fn()
    render(
      <CommandPalette
        commands={[
          command('first', '第一個指令', ['one'], first),
          command('second', '第二個指令', ['two'], second),
        ]}
        open
        onOpenChange={onOpenChange}
      />,
    )
    const search = screen.getByRole('searchbox', { name: '搜尋指令' })

    expect(search).toHaveAttribute('aria-activedescendant', 'command-option-first')
    fireEvent.keyDown(search, { key: 'ArrowDown' })
    expect(search).toHaveAttribute('aria-activedescendant', 'command-option-second')
    fireEvent.keyDown(search, { key: 'Enter' })
    expect(second).toHaveBeenCalledTimes(1)

    fireEvent.keyDown(search, { key: 'Escape' })
    expect(onOpenChange).toHaveBeenLastCalledWith(false)
  })

  it('renders an empty result without exposing a stale active option', () => {
    render(
      <CommandPalette
        commands={[command('refresh', '刷新場景', ['refresh'])]}
        open
        onOpenChange={vi.fn()}
      />,
    )
    const search = screen.getByRole('searchbox', { name: '搜尋指令' })

    fireEvent.change(search, { target: { value: 'missing' } })

    expect(screen.getByText('找不到符合的指令')).toBeVisible()
    expect(search).not.toHaveAttribute('aria-activedescendant')
  })

  it('renders nothing while closed', () => {
    const { container } = render(
      <CommandPalette commands={[]} open={false} onOpenChange={vi.fn()} />,
    )

    expect(container).toBeEmptyDOMElement()
  })
})
