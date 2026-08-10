import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useGlobalShortcuts } from './useGlobalShortcuts'

function Harness({ onPalette, onUndo, onRedo }: {
  onPalette: () => void
  onUndo: () => void
  onRedo: () => void
}) {
  useGlobalShortcuts({ onPalette, onUndo, onRedo })
  return (
    <div>
      <input aria-label="場景名稱" />
      <textarea aria-label="說明" />
      <select aria-label="格式"><option>STL</option></select>
      <div aria-label="編輯器" contentEditable><span>文字</span></div>
    </div>
  )
}

describe('global shortcuts', () => {
  it('routes mod-k and guarded undo/redo', () => {
    const onPalette = vi.fn()
    const onUndo = vi.fn()
    const onRedo = vi.fn()
    render(<Harness onPalette={onPalette} onUndo={onUndo} onRedo={onRedo} />)

    fireEvent.keyDown(window, { key: 'k', metaKey: true })
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true })
    fireEvent.keyDown(window, { key: 'z', metaKey: true, shiftKey: true })

    expect(onPalette).toHaveBeenCalledTimes(1)
    expect(onUndo).toHaveBeenCalledTimes(1)
    expect(onRedo).toHaveBeenCalledTimes(1)
  })

  it.each(['場景名稱', '說明', '格式', '編輯器'])(
    'ignores shortcuts inside editable target %s',
    (label) => {
      const onPalette = vi.fn()
      const onUndo = vi.fn()
      const onRedo = vi.fn()
      render(<Harness onPalette={onPalette} onUndo={onUndo} onRedo={onRedo} />)
      const editable = screen.getByLabelText(label)

      fireEvent.keyDown(editable, { key: 'k', metaKey: true })
      fireEvent.keyDown(editable, { key: 'z', ctrlKey: true })

      expect(onPalette).not.toHaveBeenCalled()
      expect(onUndo).not.toHaveBeenCalled()
      expect(onRedo).not.toHaveBeenCalled()
    },
  )
})
