"""Only registry-derived scripts execute; external result decoding stays fail-closed."""

import json
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from src.adapters.security.blender_code_sandbox import BlenderCodeSandbox
from src.adapters.verification.authorized_code import (
    MARKER,
    authorized_verification_code,
    verification_code,
)
from src.adapters.verification.blender_verification import (
    BlenderVerificationAdapter,
    decode_observation,
)
from src.core.domain.verification import VerificationError
from src.core.ports.mcp_port import ToolResult
from src.verification.cable_route_cases import registered_suites


def payload() -> dict[str, object]:
    return {
        "suite_id": "cable-contact-controls",
        "restored": True,
        "checks": [
            {
                "name": "clear_path",
                "expected": "clear",
                "observed": "clear",
                "passed": True,
                "detail": "clear",
            },
        ],
    }


def test_registry_scripts_are_exactly_the_sandbox_allowlist() -> None:
    sandbox = BlenderCodeSandbox(authorized=authorized_verification_code)
    for suite in registered_suites():
        code = verification_code(suite)
        assert sandbox.validate(code).allowed
        assert not sandbox.validate(code + "\nprint(1)").allowed
    with pytest.raises(VerificationError):
        verification_code(replace(registered_suites()[0], suite_id="arbitrary.py"))


@pytest.mark.parametrize("field,value", [("restored", "true"), ("checks", None), ("suite_id", 1)])
def test_malformed_result_is_refused(field: str, value: object) -> None:
    data = {**payload(), field: value}
    with pytest.raises(VerificationError):
        decode_observation(data)


@pytest.mark.asyncio
async def test_adapter_uses_shared_port_and_decodes_marked_evidence() -> None:
    blender = AsyncMock()
    blender.execute.return_value = ToolResult(success=True, output=MARKER + json.dumps(payload()))
    suite = registered_suites()[0]
    result = await BlenderVerificationAdapter(blender).run_suite(suite)
    assert result.restored and result.checks[0].passed
    command = blender.execute.call_args.args[0]
    assert command.tool_name == "execute_code"
    assert command.arguments["code"] == verification_code(suite)
