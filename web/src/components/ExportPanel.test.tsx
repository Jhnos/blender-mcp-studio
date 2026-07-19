import { createRef } from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { PrintReadinessReport } from '../domain/printReadiness'
import { ExportPanel, type ExportPanelHandle } from './ExportPanel'

const READY_REPORT: PrintReadinessReport = {
  status: 'ready',
  metrics: {
    object_count: 1,
    triangle_count: 12,
    dimensions_mm: [20, 30, 40],
    estimated_volume_mm3: 24000,
    surface_area_mm2: 5200,
  },
  issues: [],
  analysis_truncated: false,
}

const REVIEW_REPORT: PrintReadinessReport = {
  ...READY_REPORT,
  status: 'review',
  issues: [
    {
      code: 'thin_walls',
      severity: 'warning',
      count: 2,
      object_names: ['CatStand'],
      message: '2 處壁厚可能低於 0.8 mm（近似檢查）',
    },
    {
      code: 'non_manifold_edges',
      severity: 'error',
      count: 1,
      object_names: ['CatStand'],
      message: '找到 1 條非流形邊',
    },
  ],
  analysis_truncated: false,
}

const INVALID_REPORT: PrintReadinessReport = {
  status: 'invalid',
  metrics: {
    object_count: 0,
    triangle_count: 0,
    dimensions_mm: [0, 0, 0],
    estimated_volume_mm3: 0,
    surface_area_mm2: 0,
  },
  issues: [{
    code: 'no_mesh',
    severity: 'error',
    count: 0,
    object_names: [],
    message: '場景中沒有可分析的可見網格',
  }],
  analysis_truncated: false,
}

const renderPanel = (
  report: PrintReadinessReport = READY_REPORT,
  sceneRevision = 0,
) => {
  const onInspect = vi.fn().mockResolvedValue(report)
  const onExport = vi.fn()
  const view = render(
    <ExportPanel
      busy={false}
      sceneRevision={sceneRevision}
      onInspect={onInspect}
      onExport={onExport}
    />,
  )
  return { ...view, onInspect, onExport }
}

describe('ExportPanel', () => {
  it('exposes focused open and rerun commands without leaking panel state', async () => {
    const ref = createRef<ExportPanelHandle>()
    const onInspect = vi.fn().mockResolvedValue(READY_REPORT)
    render(
      <ExportPanel
        ref={ref}
        busy={false}
        sceneRevision={0}
        onInspect={onInspect}
        onExport={vi.fn()}
      />,
    )

    act(() => ref.current?.open())
    await screen.findByText('可以切片')
    expect(onInspect).toHaveBeenCalledTimes(1)

    await act(async () => ref.current?.rerunInspection())
    expect(onInspect).toHaveBeenCalledTimes(2)
  })

  it('automatically inspects with FDM defaults when opened', async () => {
    const { onInspect } = renderPanel()

    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))

    await waitFor(() => expect(onInspect).toHaveBeenCalledWith({
      selectionOnly: false,
      applyModifiers: true,
      minWallThicknessMm: 0.8,
      overhangAngleDeg: 45,
    }))
    expect(screen.getByText('20 × 30 × 40 mm')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('24,000 mm³')).toBeInTheDocument()
    expect(screen.getByText('5,200 mm²')).toBeInTheDocument()
    expect(screen.getByText('可以切片')).toBeInTheDocument()
  })

  it('marks changed analysis settings stale without automatically rerunning', async () => {
    const { onInspect } = renderPanel()
    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))
    await screen.findByText('可以切片')

    fireEvent.change(screen.getByLabelText('最小壁厚（mm）'), { target: { value: '1.2' } })

    expect(screen.getByText('需要重新檢查')).toBeInTheDocument()
    expect(onInspect).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: '重新檢查' }))
    await waitFor(() => expect(onInspect).toHaveBeenLastCalledWith(expect.objectContaining({
      minWallThicknessMm: 1.2,
    })))
  })

  it('marks a scene change stale without occupying the Blender socket', async () => {
    const { onInspect, rerender } = renderPanel(READY_REPORT, 1)
    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))
    await screen.findByText('可以切片')

    rerender(
      <ExportPanel
        busy={false}
        sceneRevision={2}
        onInspect={onInspect}
        onExport={vi.fn()}
      />,
    )

    expect(screen.getByText('需要重新檢查')).toBeInTheDocument()
    expect(onInspect).toHaveBeenCalledTimes(1)
  })

  it('requires an explicit review confirmation and sorts errors first', async () => {
    const { onExport } = renderPanel(REVIEW_REPORT)
    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))

    await screen.findByText('需要確認')
    const issues = screen.getAllByTestId('print-issue')
    expect(issues[0]).toHaveTextContent('找到 1 條非流形邊')
    expect(screen.queryByRole('button', { name: '下載 STL' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '仍要下載 STL' }))

    expect(onExport).toHaveBeenCalledWith({
      format: 'stl',
      selectionOnly: false,
      applyModifiers: true,
      triangulate: true,
    })
  })

  it('blocks invalid reports and explains why', async () => {
    const { onExport } = renderPanel(INVALID_REPORT)
    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))

    await screen.findByText('無法匯出')
    expect(screen.getByText('場景中沒有可分析的可見網格')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '下載 STL' })).toBeDisabled()
    expect(onExport).not.toHaveBeenCalled()
  })

  it('shows a retry action after Blender inspection fails', async () => {
    const onInspect = vi.fn()
      .mockRejectedValueOnce(new Error('Blender is unavailable'))
      .mockResolvedValueOnce(READY_REPORT)
    render(
      <ExportPanel
        busy={false}
        sceneRevision={0}
        onInspect={onInspect}
        onExport={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))
    await screen.findByText(/Blender is unavailable/)
    fireEvent.click(screen.getByRole('button', { name: '重試檢查' }))

    await screen.findByText('可以切片')
    expect(onInspect).toHaveBeenCalledTimes(2)
  })

  it('keeps the existing format and millimetre export contract', async () => {
    const { onExport } = renderPanel()
    fireEvent.click(screen.getByRole('button', { name: '準備切片' }))
    await screen.findByText('可以切片')

    expect(screen.getByText(/自動轉為毫米/)).toBeInTheDocument()
    for (const label of ['STL', 'OBJ', 'PLY', 'GLB', 'FBX']) {
      expect(screen.getByRole('radio', { name: new RegExp(label) })).toBeInTheDocument()
    }
    fireEvent.click(screen.getByRole('radio', { name: /PLY/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: '僅匯出已選取物件' }))
    fireEvent.click(screen.getByRole('button', { name: '重新檢查' }))
    await waitFor(() => expect(screen.getByText('可以切片')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '下載 PLY' }))

    expect(onExport).toHaveBeenCalledWith({
      format: 'ply',
      selectionOnly: true,
      applyModifiers: true,
      triangulate: true,
    })
  })
})
