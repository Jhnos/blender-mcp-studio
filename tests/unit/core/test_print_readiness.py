from __future__ import annotations

import pytest

from src.core.domain.exceptions import PrintReadinessError
from src.core.domain.print_readiness import (
    PrintInspection,
    PrintIssue,
    PrintIssueCode,
    PrintIssueSeverity,
    PrintMetrics,
    PrintReadinessSpec,
    PrintReadinessStatus,
)
from src.core.use_cases.print_readiness import PrintReadinessService


class RecordingInspector:
    def __init__(self, inspection: PrintInspection) -> None:
        self.inspection = inspection
        self.specs: list[PrintReadinessSpec] = []

    async def inspect(self, spec: PrintReadinessSpec) -> PrintInspection:
        self.specs.append(spec)
        return self.inspection


def metrics() -> PrintMetrics:
    return PrintMetrics(
        object_count=1,
        triangle_count=12,
        dimensions_mm=(20.0, 20.0, 20.0),
        estimated_volume_mm3=8000.0,
        surface_area_mm2=2400.0,
    )


@pytest.mark.asyncio
async def test_clean_inspection_is_ready_and_uses_fdm_defaults() -> None:
    inspector = RecordingInspector(PrintInspection(metrics(), (), False))
    service = PrintReadinessService(inspector)

    report = await service.check(PrintReadinessSpec())

    assert report.status is PrintReadinessStatus.READY
    assert report.metrics == metrics()
    assert inspector.specs == [
        PrintReadinessSpec(
            selection_only=False,
            apply_modifiers=True,
            min_wall_thickness_mm=0.8,
            overhang_angle_deg=45.0,
        )
    ]


@pytest.mark.asyncio
async def test_any_mesh_issue_requires_review_without_blocking_report() -> None:
    issue = PrintIssue(
        code=PrintIssueCode.NON_MANIFOLD_EDGES,
        severity=PrintIssueSeverity.ERROR,
        count=4,
        object_names=("OpenCube",),
        message="4 non-manifold edges",
    )
    service = PrintReadinessService(
        RecordingInspector(PrintInspection(metrics(), (issue,), False))
    )

    report = await service.check(PrintReadinessSpec())

    assert report.status is PrintReadinessStatus.REVIEW
    assert report.issues == (issue,)


@pytest.mark.asyncio
async def test_no_mesh_is_the_only_invalid_report() -> None:
    issue = PrintIssue(
        code=PrintIssueCode.NO_MESH,
        severity=PrintIssueSeverity.ERROR,
        count=0,
        object_names=(),
        message="No visible mesh objects",
    )
    empty = PrintMetrics(0, 0, (0.0, 0.0, 0.0), 0.0, 0.0)
    service = PrintReadinessService(
        RecordingInspector(PrintInspection(empty, (issue,), False))
    )

    report = await service.check(PrintReadinessSpec())

    assert report.status is PrintReadinessStatus.INVALID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "spec",
    [
        PrintReadinessSpec(min_wall_thickness_mm=0.0),
        PrintReadinessSpec(min_wall_thickness_mm=10.1),
        PrintReadinessSpec(overhang_angle_deg=-0.1),
        PrintReadinessSpec(overhang_angle_deg=90.1),
    ],
)
async def test_invalid_thresholds_fail_before_adapter(spec: PrintReadinessSpec) -> None:
    inspector = RecordingInspector(PrintInspection(metrics(), (), False))
    service = PrintReadinessService(inspector)

    with pytest.raises(PrintReadinessError):
        await service.check(spec)

    assert inspector.specs == []
