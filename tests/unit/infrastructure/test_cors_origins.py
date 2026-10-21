"""CORS default: CORS_ORIGINS env, else the resolved public origin, else [] without crashing."""

from __future__ import annotations

import pytest

import api.main as api_main


def test_env_cors_origins_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    assert api_main._origins(None) == ["https://a.example", "https://b.example"]


def test_default_is_the_public_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setattr(api_main, "public_origin", lambda: "https://box.example")
    assert api_main._origins(None) == ["https://box.example"]


def test_unresolvable_origin_degrades_to_empty_with_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail() -> str:
        raise ValueError("no tailscale")

    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setattr(api_main, "public_origin", fail)
    with caplog.at_level("WARNING"):
        assert api_main._origins(None) == []
    assert "CORS" in caplog.text
