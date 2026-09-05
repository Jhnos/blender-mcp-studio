"""HTTP delivery adapter for 3D print-readiness reports."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas import PrintReadinessRequest
from src.core.domain.print_readiness import PrintReadinessReport, PrintReadinessSpec
from src.core.ports.print_readiness_port import PrintReadinessQueryPort

router = APIRouter(prefix="/api")


@router.post("/print-readiness")
async def check_print_readiness(
    body: PrintReadinessRequest,
    request: Request,
) -> PrintReadinessReport:
    spec = PrintReadinessSpec(
        selection_only=body.selection_only,
        apply_modifiers=body.apply_modifiers,
        min_wall_thickness_mm=body.min_wall_thickness_mm,
        overhang_angle_deg=body.overhang_angle_deg,
    )
    service: PrintReadinessQueryPort = request.app.state.print_readiness
    return await service.check(spec)
