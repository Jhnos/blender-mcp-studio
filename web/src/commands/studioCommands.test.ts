import { describe, expect, it, vi } from 'vitest'
import { createStudioCommands, type StudioCommandActions } from './studioCommands'

const actions = (): StudioCommandActions => ({
  refreshPreview: vi.fn(),
  undo: vi.fn(),
  redo: vi.fn(),
  selectAllTargets: vi.fn(),
  clearTargets: vi.fn(),
  focusBatchTransform: vi.fn(),
  focusObjectList: vi.fn(),
  openPrintReadiness: vi.fn(),
  rerunPrintReadiness: vi.fn(),
})

describe('Studio commands', () => {
  it('composes exactly the nine curated commands', () => {
    expect(createStudioCommands(actions()).map((command) => command.id)).toEqual([
      'preview.refresh',
      'history.undo',
      'history.redo',
      'batch.select-all',
      'batch.clear',
      'batch.focus-transform',
      'scene.focus-object-list',
      'print.open-readiness',
      'print.rerun-readiness',
    ])
  })

  it('delegates each command through its injected action', async () => {
    const injected = actions()

    for (const command of createStudioCommands(injected)) await command.run()

    for (const action of Object.values(injected)) expect(action).toHaveBeenCalledTimes(1)
  })

  it('includes Chinese titles and English aliases for discovery', () => {
    const commands = createStudioCommands(actions())

    expect(commands.every((command) => /[\u3400-\u9fff]/u.test(command.title))).toBe(true)
    expect(commands.every((command) => command.keywords.some((keyword) => /^[a-z]/i.test(keyword))))
      .toBe(true)
  })
})
