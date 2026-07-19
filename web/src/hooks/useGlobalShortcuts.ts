import { useEffect } from 'react'

interface GlobalShortcutActions {
  onPalette: () => void
  onUndo: () => void
  onRedo: () => void
}

export const isEditableTarget = (target: EventTarget | null): boolean => {
  if (!(target instanceof Element)) return false
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return true
  return target.closest('[contenteditable]:not([contenteditable="false"])') !== null
}

export function useGlobalShortcuts({
  onPalette,
  onUndo,
  onRedo,
}: GlobalShortcutActions): void {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.isComposing || isEditableTarget(event.target)) return
      const mod = event.metaKey || event.ctrlKey
      if (!mod) return
      const key = event.key.toLocaleLowerCase()
      if (key === 'k') {
        event.preventDefault()
        onPalette()
      } else if (key === 'z') {
        event.preventDefault()
        if (event.shiftKey) onRedo()
        else onUndo()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onPalette, onRedo, onUndo])
}
