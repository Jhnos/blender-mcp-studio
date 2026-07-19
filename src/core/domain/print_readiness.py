"""Immutable value objects for client-neutral print-readiness inspection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PrintReadinessStatus(StrEnum):
    READY = "ready"
    REVIEW = "review"
    INVALID = "invalid"


class PrintIssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class PrintIssueCode(StrEnum):
    NO_MESH = "no_mesh"
    NON_MANIFOLD_EDGES = "non_manifold_edges"
    INCONSISTENT_NORMALS = "inconsistent_normals"
    DEGENERATE_GEOMETRY = "degenerate_geometry"
    ZERO_VOLUME = "zero_volume"
    INTERSECTIONS = "intersections"
    THIN_WALLS = "thin_walls"
    OVERHANGS = "overhangs"
    NEGATIVE_SCALE = "negative_scale"
    ANALYSIS_TRUNCATED = "analysis_truncated"


@dataclass(frozen=True, slots=True)
class PrintReadinessSpec:
    selection_only: bool = False
    apply_modifiers: bool = True
    min_wall_thickness_mm: float = 0.8
    overhang_angle_deg: float = 45.0


@dataclass(frozen=True, slots=True)
class PrintMetrics:
    object_count: int
    triangle_count: int
    dimensions_mm: tuple[float, float, float]
    estimated_volume_mm3: float
    surface_area_mm2: float


@dataclass(frozen=True, slots=True)
class PrintIssue:
    code: PrintIssueCode
    severity: PrintIssueSeverity
    count: int
    object_names: tuple[str, ...]
    message: str


@dataclass(frozen=True, slots=True)
class PrintInspection:
    metrics: PrintMetrics
    issues: tuple[PrintIssue, ...]
    analysis_truncated: bool


@dataclass(frozen=True, slots=True)
class PrintReadinessReport:
    status: PrintReadinessStatus
    metrics: PrintMetrics
    issues: tuple[PrintIssue, ...]
    analysis_truncated: bool
