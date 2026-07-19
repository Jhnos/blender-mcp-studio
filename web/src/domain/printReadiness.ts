export type PrintReadinessStatus = 'ready' | 'review' | 'invalid'
export type PrintIssueSeverity = 'error' | 'warning'

export type PrintIssueCode =
  | 'no_mesh'
  | 'non_manifold_edges'
  | 'inconsistent_normals'
  | 'degenerate_geometry'
  | 'zero_volume'
  | 'intersections'
  | 'thin_walls'
  | 'overhangs'
  | 'negative_scale'
  | 'analysis_truncated'

export interface PrintReadinessOptions {
  selectionOnly: boolean
  applyModifiers: boolean
  minWallThicknessMm: number
  overhangAngleDeg: number
}

export interface PrintReadinessIssue {
  code: PrintIssueCode
  severity: PrintIssueSeverity
  count: number
  object_names: string[]
  message: string
}

export interface PrintReadinessReport {
  status: PrintReadinessStatus
  metrics: {
    object_count: number
    triangle_count: number
    dimensions_mm: [number, number, number]
    estimated_volume_mm3: number
    surface_area_mm2: number
  }
  issues: PrintReadinessIssue[]
  analysis_truncated: boolean
}
