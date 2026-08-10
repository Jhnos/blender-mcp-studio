"""Deployment contract tests for the long-running Studio Web service."""

from __future__ import annotations

import plistlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]


def test_launchd_web_serves_the_production_build() -> None:
    plist_path = PROJECT_ROOT / "deploy/launchd/com.blender-mcp.web.plist"
    with plist_path.open("rb") as stream:
        plist = plistlib.load(stream)

    arguments = plist["ProgramArguments"]
    assert arguments[2] == "preview"
    assert "BLENDER_MCP_HMR" not in plist.get("EnvironmentVariables", {})


def test_vite_preview_reuses_the_backend_proxy_contract() -> None:
    source = (PROJECT_ROOT / "web/vite.config.ts").read_text()

    assert "const backendProxy" in source
    assert "proxy: backendProxy" in source
    assert "preview:" in source


def test_launchd_installer_builds_web_assets_before_bootstrap() -> None:
    source = (PROJECT_ROOT / "deploy/launchd/install.sh").read_text()

    assert "_build_web_assets()" in source
    assert '"${NPM_BIN}" --prefix "${PROJECT_ROOT}/web" run build' in source


def test_launchd_installer_retries_transient_bootstrap_race() -> None:
    source = (PROJECT_ROOT / "deploy/launchd/install.sh").read_text()

    assert "_wait_for_unload()" in source
    assert '_wait_for_unload "${service}"' in source
    assert "_bootstrap_with_retry()" in source
    assert '_bootstrap_with_retry "${DOMAIN}" "${target}"' in source
    assert "launchctl bootstrap" in source
