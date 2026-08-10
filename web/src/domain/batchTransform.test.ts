import { describe, expect, it } from 'vitest'
import {
  EMPTY_BATCH_TRANSFORM_DRAFT,
  toBatchTransformRequest,
  validateBatchTransform,
  type BatchTransformDraft,
} from './batchTransform'

const validDraft: BatchTransformDraft = {
  translationMm: [10, -20, 30],
  rotationDeg: [0, 0, 15],
  scalePercent: [5, 5, 5],
}

describe('batch transform request model', () => {
  it('maps all retained unit drafts to one REST request', () => {
    expect(toBatchTransformRequest(['A', 'B'], validDraft)).toEqual({
      object_names: ['A', 'B'],
      translation_mm: [10, -20, 30],
      rotation_deg: [0, 0, 15],
      scale_percent: [5, 5, 5],
    })
  })

  it('does not expose mutable shared empty vectors', () => {
    const first = structuredClone(EMPTY_BATCH_TRANSFORM_DRAFT)
    first.translationMm[0] = 99

    expect(EMPTY_BATCH_TRANSFORM_DRAFT.translationMm).toEqual([0, 0, 0])
  })

  it('rejects an all-zero draft', () => {
    expect(validateBatchTransform(EMPTY_BATCH_TRANSFORM_DRAFT)).toMatchObject({
      valid: false,
      message: expect.stringMatching(/non-zero/i),
    })
  })

  it.each([
    [{ ...validDraft, translationMm: [100_000.1, 0, 0] }, '100000'],
    [{ ...validDraft, rotationDeg: [0, -3600.1, 0] }, '3600'],
    [{ ...validDraft, scalePercent: [-100, 0, 0] }, 'greater than -100'],
    [{ ...validDraft, scalePercent: [0, 10_000.1, 0] }, '10000'],
    [{ ...validDraft, translationMm: [Number.NaN, 0, 0] }, 'finite'],
  ] as const)('rejects invalid draft %j', (draft, message) => {
    expect(validateBatchTransform(draft as BatchTransformDraft)).toMatchObject({
      valid: false,
      message: expect.stringMatching(new RegExp(message, 'i')),
    })
  })

  it('accepts the documented boundaries', () => {
    expect(validateBatchTransform({
      translationMm: [100_000, -100_000, 0],
      rotationDeg: [3600, -3600, 0],
      scalePercent: [-99.999, 10_000, 0],
    })).toEqual({ valid: true, message: null })
  })
})
