export type Vector3Tuple = [number, number, number]

export interface BatchTransformDraft {
  translationMm: Vector3Tuple
  rotationDeg: Vector3Tuple
  scalePercent: Vector3Tuple
}

export interface BatchTransformRequest {
  object_names: string[]
  translation_mm: Vector3Tuple
  rotation_deg: Vector3Tuple
  scale_percent: Vector3Tuple
}

export interface BatchTransformReceipt {
  object_names: string[]
  affected_count: number
  message: string
}

export type BatchTransformValidation =
  | { valid: true; message: null }
  | { valid: false; message: string }

const frozenZero = (): Vector3Tuple => Object.freeze([0, 0, 0]) as unknown as Vector3Tuple

export const EMPTY_BATCH_TRANSFORM_DRAFT: Readonly<BatchTransformDraft> = Object.freeze({
  translationMm: frozenZero(),
  rotationDeg: frozenZero(),
  scalePercent: frozenZero(),
})

const vectors = (draft: BatchTransformDraft): Vector3Tuple[] => [
  draft.translationMm,
  draft.rotationDeg,
  draft.scalePercent,
]

export function validateBatchTransform(draft: BatchTransformDraft): BatchTransformValidation {
  const values = vectors(draft).flat()
  if (!values.every(Number.isFinite)) {
    return { valid: false, message: 'Transform values must be finite numbers' }
  }
  if (draft.translationMm.some((value) => Math.abs(value) > 100_000)) {
    return { valid: false, message: 'Translation must be within +/-100000 mm' }
  }
  if (draft.rotationDeg.some((value) => Math.abs(value) > 3_600)) {
    return { valid: false, message: 'Rotation must be within +/-3600 degrees' }
  }
  if (draft.scalePercent.some((value) => value <= -100)) {
    return { valid: false, message: 'Scale percent must be greater than -100' }
  }
  if (draft.scalePercent.some((value) => value > 10_000)) {
    return { valid: false, message: 'Scale percent must be no greater than 10000' }
  }
  if (!values.some((value) => value !== 0)) {
    return { valid: false, message: 'Enter at least one non-zero transform delta' }
  }
  return { valid: true, message: null }
}

const copyVector = (vector: Vector3Tuple): Vector3Tuple => [vector[0], vector[1], vector[2]]

export function toBatchTransformRequest(
  objectNames: readonly string[],
  draft: BatchTransformDraft,
): BatchTransformRequest {
  return {
    object_names: [...objectNames],
    translation_mm: copyVector(draft.translationMm),
    rotation_deg: copyVector(draft.rotationDeg),
    scale_percent: copyVector(draft.scalePercent),
  }
}

export function createEmptyBatchTransformDraft(): BatchTransformDraft {
  return {
    translationMm: [0, 0, 0],
    rotationDeg: [0, 0, 0],
    scalePercent: [0, 0, 0],
  }
}
