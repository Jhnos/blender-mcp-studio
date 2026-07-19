"""HTTP delivery adapter for atomic incremental batch transforms."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.schemas import BatchTransformRequest
from src.core.domain.batch_transform import (
    BatchTransformReceipt,
    BatchTransformSpec,
    TransformDelta,
)
from src.core.domain.exceptions import BatchTransformError, BlenderConnectionError
from src.core.domain.scene_operations import Vector3
from src.core.use_cases.batch_transform import BatchTransformService

router = APIRouter(prefix="/api/scene")


def _vector(values: tuple[float, float, float]) -> Vector3:
    return Vector3(values[0], values[1], values[2])


@router.post("/batch-transform")
async def apply_batch_transform(
    body: BatchTransformRequest,
    request: Request,
) -> BatchTransformReceipt:
    service: BatchTransformService = request.app.state.batch_transform
    try:
        spec = BatchTransformSpec(
            object_names=tuple(body.object_names),
            delta=TransformDelta(
                translation_mm=_vector(body.translation_mm),
                rotation_deg=_vector(body.rotation_deg),
                scale_percent=_vector(body.scale_percent),
            ),
        )
        return await service.apply(spec)
    except BlenderConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BatchTransformError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
