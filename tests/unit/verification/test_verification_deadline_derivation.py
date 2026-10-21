"""The verification deadlines are derived from a measurement and nest consistently.

Observed 2026-10-21: the slowest registered suite had been measured at 274.98 s
(task 16 hand-off, 2026-09) while the Blender script deadline was 300 s, 1.09x that
measurement. On a host shared with other workloads (load average 15 on 10 cores)
one suite crossed 300 s, the adapter raised "Blender is unavailable" for a Blender
that was alive and busy, and the real tier stopped. A deadline calibrated on one
sample at 1.09x is not a deadline, it is a coin flip; the global lesson is five
times the expected duration, and every outer deadline must sit outside the inner one.
"""

from __future__ import annotations

import asyncio

from scripts.verify import verification_mcp_verify_real as gate
from src.adapters.mcp_server import server
from src.adapters.verification.authorized_code import (
    SLOWEST_SUITE_MEASURED_S,
    VERIFICATION_TIMEOUT_S,
)


def test_script_deadline_is_five_times_the_slowest_measured_suite() -> None:
    assert SLOWEST_SUITE_MEASURED_S >= 274.98, "the 2026-09 measurement must not be lowered"
    assert VERIFICATION_TIMEOUT_S == 5 * SLOWEST_SUITE_MEASURED_S


def test_tool_and_gate_deadlines_nest_outside_the_script_deadline() -> None:
    assert VERIFICATION_TIMEOUT_S < server.VERIFICATION_TOOL_TIMEOUT_S
    assert server.VERIFICATION_TOOL_TIMEOUT_S < gate.VERIFICATION_CLIENT_TIMEOUT_S


def test_registered_tool_carries_the_derived_deadline() -> None:
    """Wiring proof: the constant must reach the FastMCP decorator, not just exist."""

    class _Port:
        def __getattr__(self, name: str):  # noqa: ANN204 - any port method is never called
            raise AssertionError(f"unexpected port call {name}")

    mcp = server.create_mcp_server(_Port(), _Port(), _Port(), _Port())  # type: ignore[arg-type]
    tool = asyncio.run(mcp.get_tool("run_verification_suite"))
    assert tool.timeout == server.VERIFICATION_TOOL_TIMEOUT_S
