"""Generation gets its existing budget; readback and skip-generate do not."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts.verify import generated_artifact_verify_real as gate
from src.adapters.generation.authorized_code import GENERATOR_TIMEOUT_S
from src.verification.generated_artifact_verdict import VerificationEvidence, VerificationSummary


@pytest.mark.asyncio
@pytest.mark.parametrize("skip", [False, True])
async def test_only_generator_uses_generation_deadline(monkeypatch, skip):
    calls = []

    class Oracle:
        def __init__(self, host, port, timeout=180):
            self.timeout = timeout

        def execute(self, code):
            calls.append(("generate", self.timeout))

        def execute_json(self, code):
            calls.append(("read", self.timeout))
            return {}

    monkeypatch.setattr(gate, "BlenderSocketOracle", Oracle)
    monkeypatch.setattr(gate, "load_contract", lambda _: SimpleNamespace(name="test", artifacts=()))
    monkeypatch.setattr(gate, "build_generator_code", lambda *_: "generate")
    monkeypatch.setattr(gate, "oracle_code", lambda _: "read")
    monkeypatch.setattr(gate, "mcp_readiness", AsyncMock(return_value={}))
    monkeypatch.setattr(
        gate,
        "assess_verification",
        lambda *_: VerificationSummary((VerificationEvidence("ok", True, ""),)),
    )
    args = SimpleNamespace(
        contract=None,
        blender_host="test",
        blender_port=1,
        skip_generate=skip,
        mcp_url="test",
        identity="test",
    )
    assert await gate.verify(args) == 0
    assert calls == (
        [("read", 180)] if skip else [("generate", GENERATOR_TIMEOUT_S), ("read", 180)]
    )
