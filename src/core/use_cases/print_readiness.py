"""Application service for client-neutral print-readiness reports."""

from __future__ import annotations

from src.core.domain.exceptions import PrintReadinessError
from src.core.domain.print_readiness import (
    PrintIssueCode,
    PrintReadinessReport,
    PrintReadinessSpec,
    PrintReadinessStatus,
)
from src.core.ports.print_readiness_port import PrintReadinessPort


class PrintReadinessService:
    def __init__(self, inspector: PrintReadinessPort) -> None:
        self._inspector = inspector

    async def check(self, spec: PrintReadinessSpec) -> PrintReadinessReport:
        self._validate(spec)
        inspection = await self._inspector.inspect(spec)
        if any(issue.code is PrintIssueCode.NO_MESH for issue in inspection.issues):
            status = PrintReadinessStatus.INVALID
        elif inspection.issues:
            status = PrintReadinessStatus.REVIEW
        else:
            status = PrintReadinessStatus.READY
        return PrintReadinessReport(
            status=status,
            metrics=inspection.metrics,
            issues=inspection.issues,
            analysis_truncated=inspection.analysis_truncated,
        )

    @staticmethod
    def _validate(spec: PrintReadinessSpec) -> None:
        if not 0.0 < spec.min_wall_thickness_mm <= 10.0:
            raise PrintReadinessError("Minimum wall thickness must be above 0 and at most 10 mm")
        if not 0.0 <= spec.overhang_angle_deg <= 90.0:
            raise PrintReadinessError("Overhang angle must be between 0 and 90 degrees")
