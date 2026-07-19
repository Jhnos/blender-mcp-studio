import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ExportPanel } from './ExportPanel'

describe('ExportPanel', () => {
  it('exposes print formats and dispatches slicer-ready options', async () => {
    const onExport = vi.fn()
    render(<ExportPanel busy={false} onExport={onExport} />)

    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))

    expect(screen.getByText('3D 列印格式')).toBeInTheDocument()
    expect(screen.getByText('交換與預覽格式')).toBeInTheDocument()
    for (const label of ['STL', 'OBJ', 'PLY', 'GLB', 'FBX']) {
      expect(screen.getByRole('radio', { name: new RegExp(label) })).toBeInTheDocument()
    }

    fireEvent.click(screen.getByRole('radio', { name: /PLY/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: '僅匯出已選取物件' }))
    fireEvent.click(screen.getByRole('button', { name: '下載 PLY' }))

    expect(onExport).toHaveBeenCalledWith({
      format: 'ply',
      selectionOnly: true,
      applyModifiers: true,
      triangulate: true,
    })
  })

  it('explains millimetre conversion for slicer formats', async () => {
    render(<ExportPanel busy={false} onExport={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))

    expect(screen.getByText(/自動轉為毫米/)).toBeInTheDocument()
  })
})
