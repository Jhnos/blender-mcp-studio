"""Scripts must not need tailscale to import, and the stdio proxy must fail with one line."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

import src.infrastructure.public_base_url as pbu

ROOT = Path(__file__).parents[3]


def _load(rel: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _no_tailscale(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> str:
        raise OSError("tailscale unavailable")

    monkeypatch.delenv(pbu.ENV_VAR, raising=False)
    monkeypatch.setattr(pbu, "_tailscale_status", boom)


@pytest.mark.parametrize(
    "rel", ["scripts/verify/mcp_verify_rest.py", "scripts/verify/mcp_verify_chat.py"]
)
def test_verify_scripts_import_without_tailscale(monkeypatch: pytest.MonkeyPatch, rel: str) -> None:
    _no_tailscale(monkeypatch)
    _load(rel, "lazy_" + Path(rel).stem)


def test_stdio_proxy_without_tailscale_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_tailscale(monkeypatch)
    monkeypatch.delenv("BLENDER_MCP_URL", raising=False)
    module = _load("scripts/run_mcp_stdio_proxy.py", "lazy_stdio_proxy")
    with pytest.raises(SystemExit) as info:
        module.main()
    assert info.value.code == 2
    err = capsys.readouterr().err
    assert "BLENDER_MCP_URL" in err
    assert "BLENDER_MCP_PUBLIC_BASE_URL" in err
    assert "Traceback" not in err
