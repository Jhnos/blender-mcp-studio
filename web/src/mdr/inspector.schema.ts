import type { UISchema } from './types'

// ===========================================================================
// Inspector UI Schema — the declarative layout of the right panel.
// This is DATA: reordering, regrouping, or adding a panel means editing this
// object, not the engine. Six flat tabs became three basic sections + one
// advanced (Log), collapsible (progressive disclosure).
// ===========================================================================

export const inspectorSchema: UISchema = {
  version: 1,
  sections: [
    {
      id: 'scene',
      title: '場景',
      icon: 'scene',
      level: 'basic',
      defaultOpen: true,
      body: { type: 'object-list' },
    },
    {
      id: 'assets',
      title: '資產',
      icon: 'material',
      level: 'basic',
      defaultOpen: false,
      body: { type: 'asset-browser' },
    },
    {
      id: 'history',
      title: '歷史',
      icon: 'history',
      level: 'basic',
      defaultOpen: false,
      body: { type: 'snapshot-list' },
    },
    {
      id: 'log',
      title: '執行記錄',
      icon: 'log',
      level: 'advanced',
      defaultOpen: false,
      body: { type: 'log-viewer' },
    },
  ],
}
