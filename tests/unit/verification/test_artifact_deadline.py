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


@pytest.mark.parametrize("suite_count", [1, 4])
def test_offline_suite_batch_budget_scales_without_extending_scene_read(monkeypatch, suite_count):
    from pathlib import Path

    from scripts.verify import lab_cable_routes_verify_real as cable_gate
    from src.adapters.verification.authorized_code import VERIFICATION_TIMEOUT_S

    calls = []

    class Oracle:
        def __init__(self, host, port, timeout):
            self.timeout = timeout

        def execute(self, code):
            calls.append(self.timeout)
            return {}

    monkeypatch.setattr(cable_gate, "BlenderSocketOracle", Oracle)
    monkeypatch.setattr(
        cable_gate, "registered_suites", lambda: (None,) * suite_count, raising=False
    )
    monkeypatch.setattr(cable_gate, "reload_modules_for", lambda *_: ())
    cable_gate.verify_cable_routes(Path("/test"))
    assert calls == [60, VERIFICATION_TIMEOUT_S * suite_count]
