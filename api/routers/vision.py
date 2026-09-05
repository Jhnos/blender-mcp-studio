"""Vision-guided refinement and image analysis."""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class RefineRequest(BaseModel):
    session_id: str
    user_request: str
    max_iterations: int = Field(default=3, ge=1, le=10)


@router.post("/refine")
async def refine_model(body: RefineRequest, request: Request) -> dict[str, object]:
    """Run iterative vision-guided refinement loop on the current Blender scene.

    Requires a vision adapter to be configured (OPENAI_API_KEY or ANTHROPIC_API_KEY).
    """
    use_case = getattr(request.app.state, "iterative_refinement", None)
    if use_case is None:
        raise HTTPException(
            status_code=503,
            detail="No vision provider configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.",
        )

    # Retrieve session for LLM context
    session_store = getattr(request.app.state, "session_store", None)
    session = None
    if session_store:
        session = await session_store.get(body.session_id)

    if session is None:
        from src.core.domain.session import Session

        session = Session()

    try:
        result = await use_case.execute(
            session,
            user_request=body.user_request,
            max_iterations=body.max_iterations,
        )
    except Exception as e:
        logger.exception("Refinement failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Save updated session
    if session_store:
        await session_store.save(result.session)

    return {
        "converged": result.converged,
        "iteration_count": result.iteration_count,
        "iterations": [
            {
                "iteration": it.iteration,
                "vision_analysis": it.vision_analysis,
                "commands_executed": it.commands_executed,
                "converged": it.converged,
            }
            for it in result.iterations
        ],
        "final_screenshot": (
            base64.b64encode(result.final_screenshot).decode() if result.final_screenshot else None
        ),
    }


@router.post("/chat/image")
async def analyze_image(request: Request) -> dict[str, object]:
    """Upload an image; vision LLM describes it; return description for use as prompt context.

    Client sends multipart/form-data with field 'image' (PNG/JPEG).
    Response: { description, suggestions, provider, model }
    Caller should prepend the description to the next chat message.
    """
    vision = getattr(request.app.state, "vision", None)
    if vision is None:
        raise HTTPException(
            status_code=503,
            detail="No vision provider configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.",
        )

    # Parse multipart body manually (FastAPI endpoint with Request gives us raw body)
    form = await request.form()
    image_field = form.get("image")
    if image_field is None or not hasattr(image_field, "read"):
        raise HTTPException(status_code=422, detail="Field 'image' is required (file upload)")

    image_bytes: bytes = await image_field.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 10MB)")

    _DEFAULT_PROMPT = (
        "Describe this 3D scene or reference image in detail. "
        "What objects, materials, lighting, and style do you see?"
    )
    prompt = str(form.get("prompt", _DEFAULT_PROMPT))

    try:
        analysis = await vision.analyze_image(image_bytes, prompt=prompt)
    except Exception as e:
        logger.exception("Vision analysis failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "description": analysis.description,
        "suggestions": list(analysis.suggestions),
        "provider": analysis.provider,
        "model": analysis.model,
    }
