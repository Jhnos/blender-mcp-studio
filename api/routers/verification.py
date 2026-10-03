"""REST shares the same registered verification service used by MCP."""

from fastapi import APIRouter, Request

from src.core.domain.verification import VerificationReport, VerificationSuite
from src.core.ports.verification_port import VerificationQueryPort

router = APIRouter(prefix="/api/verification")


@router.get("/suites")
async def list_verification_suites(request: Request) -> tuple[VerificationSuite, ...]:
    service: VerificationQueryPort = request.app.state.verification
    return await service.list_suites()


@router.post("/suites/{suite_id}/run")
async def run_verification_suite(suite_id: str, request: Request) -> VerificationReport:
    service: VerificationQueryPort = request.app.state.verification
    return await service.run(suite_id)
