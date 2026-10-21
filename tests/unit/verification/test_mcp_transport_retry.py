"""The MCP protocol gate retries one transport reset that happens before any MCP call.

Observed 2026-10-21 11:51: the funnel path (Tailscale Funnel -> edge proxy ->
web preview -> API) reset the connection during the client handshake; the same
gate passed 46 s later and the API log shows nothing but 200/202. One reset on an
external relay must not cost an 80-minute real-tier rerun, but it must stay
visible, and a reset after an MCP call has started, or a second reset, is still
a failure.
"""

from __future__ import annotations

import asyncio

import pytest

from scripts.verify import mcp_verify_real as gate


class _Client:
    failures = 0

    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    async def __aenter__(self) -> _Client:
        if _Client.failures > 0:
            _Client.failures -= 1
            raise ConnectionResetError(54, "Connection reset by peer")
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def call_tool(self, name: str, arguments: dict, raise_on_error: bool = True):
        class _Result:
            is_error = False
            content = [f"{name} ok"]

        return _Result()


def _wire(monkeypatch, failures: int) -> None:
    _Client.failures = failures
    monkeypatch.setattr(gate, "Client", _Client)
    monkeypatch.setattr(gate, "_socket_is_listening", lambda: True)
    monkeypatch.setattr(gate, "_cleanup_verification_objects", lambda: 0)
    oracle = iter([{"exists": True, "vertices": 8}, [1.0, 2.0, 3.0], False, []])
    monkeypatch.setattr(gate, "_oracle_json", lambda _code: next(oracle))


def test_one_handshake_reset_is_retried_and_reported(monkeypatch, capsys) -> None:
    _wire(monkeypatch, failures=1)
    assert asyncio.run(gate._verify()) == 0
    out = capsys.readouterr().out
    assert "transport reset before any MCP call" in out
    assert "MCP transport" not in out.split("=== MCP REAL EVIDENCE ===")[1]


def test_two_handshake_resets_fail_the_gate(monkeypatch, capsys) -> None:
    _wire(monkeypatch, failures=2)
    assert asyncio.run(gate._verify()) == 1
    assert "MCP transport      FAIL" in capsys.readouterr().out


@pytest.mark.parametrize("failures", [0])
def test_no_reset_needs_no_retry(monkeypatch, capsys, failures) -> None:
    _wire(monkeypatch, failures=failures)
    assert asyncio.run(gate._verify()) == 0
    assert "retrying" not in capsys.readouterr().out
