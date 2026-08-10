import type { CommandDefinition } from './types'

export interface StudioCommandActions {
  refreshPreview: () => void | Promise<void>
  undo: () => void | Promise<void>
  redo: () => void | Promise<void>
  selectAllTargets: () => void
  clearTargets: () => void
  focusBatchTransform: () => void
  focusObjectList: () => void
  openPrintReadiness: () => void
  rerunPrintReadiness: () => void | Promise<void>
}

const available = (): boolean => true

export function createStudioCommands(actions: StudioCommandActions): CommandDefinition[] {
  return [
    {
      id: 'preview.refresh', title: '刷新場景預覽',
      keywords: ['refresh', 'preview', 'reload'], isAvailable: available,
      run: actions.refreshPreview,
    },
    {
      id: 'history.undo', title: '復原上一個操作',
      keywords: ['undo', 'history', 'cmd z'], isAvailable: available,
      run: actions.undo,
    },
    {
      id: 'history.redo', title: '重做上一個操作',
      keywords: ['redo', 'history', 'shift cmd z'], isAvailable: available,
      run: actions.redo,
    },
    {
      id: 'batch.select-all', title: '全選批次目標',
      keywords: ['select all', 'batch', 'targets'], isAvailable: available,
      run: actions.selectAllTargets,
    },
    {
      id: 'batch.clear', title: '清除批次目標',
      keywords: ['clear selection', 'batch', 'targets'], isAvailable: available,
      run: actions.clearTargets,
    },
    {
      id: 'batch.focus-transform', title: '前往批次變形',
      keywords: ['focus transform', 'move', 'rotate', 'scale'], isAvailable: available,
      run: actions.focusBatchTransform,
    },
    {
      id: 'scene.focus-object-list', title: '前往場景物件列表',
      keywords: ['focus objects', 'scene list', 'inspector'], isAvailable: available,
      run: actions.focusObjectList,
    },
    {
      id: 'print.open-readiness', title: '開啟準備切片',
      keywords: ['open print readiness', 'slice', 'export'], isAvailable: available,
      run: actions.openPrintReadiness,
    },
    {
      id: 'print.rerun-readiness', title: '重新執行列印健檢',
      keywords: ['rerun print readiness', 'check', 'inspect'], isAvailable: available,
      run: actions.rerunPrintReadiness,
    },
  ]
}
