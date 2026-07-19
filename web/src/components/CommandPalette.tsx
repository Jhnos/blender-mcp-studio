import { useEffect, useMemo, useRef, useState } from 'react'
import { createCommandRegistry } from '../commands/registry'
import type { CommandDefinition } from '../commands/types'
import { Icon } from './ui'

interface CommandPaletteProps {
  commands: readonly CommandDefinition[]
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ commands, open, onOpenChange }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const searchRef = useRef<HTMLInputElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const registry = useMemo(() => {
    const next = createCommandRegistry()
    commands.forEach(next.register)
    return next
  }, [commands])
  const results = registry.search(query)
  const safeActiveIndex = results.length === 0 ? -1 : Math.min(activeIndex, results.length - 1)
  const activeCommand = safeActiveIndex >= 0 ? results[safeActiveIndex] : null

  useEffect(() => {
    if (!open) return
    previousFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    searchRef.current?.focus()
    return () => previousFocusRef.current?.focus()
  }, [open])

  if (!open) return null

  const close = () => {
    setQuery('')
    setActiveIndex(0)
    onOpenChange(false)
  }

  const execute = (command: CommandDefinition) => {
    try {
      const pending = command.run()
      if (pending instanceof Promise) {
        void pending.catch((error: unknown) => console.error('[command-palette]', error))
      }
    } catch (error) {
      console.error('[command-palette]', error)
    } finally {
      close()
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
    } else if (event.key === 'ArrowDown' && results.length > 0) {
      event.preventDefault()
      setActiveIndex((safeActiveIndex + 1) % results.length)
    } else if (event.key === 'ArrowUp' && results.length > 0) {
      event.preventDefault()
      setActiveIndex((safeActiveIndex - 1 + results.length) % results.length)
    } else if (event.key === 'Enter' && activeCommand) {
      event.preventDefault()
      execute(activeCommand)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[120] flex items-start justify-center bg-black/55 px-4 pt-[12vh] backdrop-blur-sm"
      onMouseDown={(event) => { if (event.target === event.currentTarget) close() }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="command-palette-title"
        className="w-full max-w-xl overflow-hidden rounded-2xl border border-border-strong bg-surface-overlay shadow-2xl transition duration-150 motion-reduce:transition-none"
      >
        <h2 id="command-palette-title" className="sr-only">Studio 指令面板</h2>
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Icon name="search" size={17} className="shrink-0 text-fg-subtle" />
          <input
            ref={searchRef}
            type="search"
            role="searchbox"
            aria-label="搜尋指令"
            aria-controls="command-palette-results"
            aria-activedescendant={activeCommand ? `command-option-${activeCommand.id}` : undefined}
            placeholder="輸入指令或關鍵字…"
            value={query}
            onChange={(event) => { setQuery(event.target.value); setActiveIndex(0) }}
            onKeyDown={handleKeyDown}
            className="min-w-0 flex-1 bg-transparent py-4 text-sm text-fg outline-none placeholder:text-fg-subtle"
          />
          <kbd className="rounded border border-border bg-surface-sunken px-1.5 py-0.5 font-mono text-[9px] text-fg-subtle">
            Esc
          </kbd>
        </div>

        <div className="max-h-[min(440px,60vh)] overflow-y-auto p-2">
          {results.length > 0 ? (
            <div id="command-palette-results" role="listbox" aria-label="可用指令">
              {results.map((command, index) => {
                const active = index === safeActiveIndex
                return (
                  <button
                    key={command.id}
                    id={`command-option-${command.id}`}
                    type="button"
                    role="option"
                    aria-selected={active}
                    onMouseMove={() => setActiveIndex(index)}
                    onClick={() => execute(command)}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                      active ? 'bg-accent/15 text-fg' : 'text-fg-muted hover:bg-surface-raised'
                    }`}
                  >
                    <span className={`size-1.5 rounded-full ${active ? 'bg-accent' : 'bg-border-strong'}`} />
                    <span className="flex-1">{command.title}</span>
                    {active && <span className="font-mono text-[9px] text-fg-subtle">Enter</span>}
                  </button>
                )
              })}
            </div>
          ) : (
            <p className="px-3 py-8 text-center text-xs text-fg-subtle">找不到符合的指令</p>
          )}
        </div>
        <div className="flex gap-3 border-t border-border px-4 py-2 text-[9px] text-fg-subtle">
          <span>↑↓ 選擇</span><span>Enter 執行</span><span>Esc 關閉</span>
        </div>
      </div>
    </div>
  )
}
