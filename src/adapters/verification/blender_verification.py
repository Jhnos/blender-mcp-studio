"""Translate registered suites and strictly decode measured evidence at the boundary."""

from src.adapters.blender_response import (
    decode_marked_json,
    execute_code_output,
    mapping,
    sequence,
    text,
)
from src.adapters.blender_scripts.runner import run_script
from src.adapters.verification.authorized_code import MARKER, verification_code
from src.core.domain.verification import (
    CheckResult,
    SuiteObservation,
    VerificationError,
    VerificationSuite,
)
from src.core.ports.blender_port import BlenderPort


def decode_observation(value: object) -> SuiteObservation:
    data = mapping(value, "verification result", VerificationError)
    restored = data.get("restored")
    if type(restored) is not bool:
        raise VerificationError("Verification restoration evidence must be boolean")
    checks = []
    for raw in sequence(data.get("checks"), "verification checks", VerificationError):
        row = mapping(raw, "verification check", VerificationError)
        passed, observed = row.get("passed"), row.get("observed")
        if type(passed) is not bool or (observed is not None and not isinstance(observed, str)):
            raise VerificationError("Verification check has invalid verdict or observation")
        checks.append(
            CheckResult(
                text(row.get("name"), "check name", VerificationError),
                text(row.get("expected"), "expected outcome", VerificationError),
                observed,
                passed,
                text(row.get("detail"), "check detail", VerificationError),
            )
        )
    return SuiteObservation(
        text(data.get("suite_id"), "suite id", VerificationError), tuple(checks), restored
    )


class BlenderVerificationAdapter:
    def __init__(self, blender: BlenderPort) -> None:
        self._blender = blender

    async def run_suite(self, suite: VerificationSuite) -> SuiteObservation:
        outcome = await run_script(self._blender, verification_code(suite))
        if not outcome.success:
            raise VerificationError(outcome.error or "Verification execution failed")
        payload = decode_marked_json(
            execute_code_output(outcome.output, VerificationError),
            MARKER,
            missing="Verification returned no evidence",
            invalid="Verification returned invalid JSON",
            error=VerificationError,
        )
        return decode_observation(payload)
