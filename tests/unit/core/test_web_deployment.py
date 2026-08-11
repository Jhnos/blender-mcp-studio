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


def test_install_all_waits_for_blender_before_starting_the_api() -> None:
    source = (PROJECT_ROOT / "deploy/launchd/install.sh").read_text()
    main = source[source.index("main()") :]

    blender = main.index("_install_one com.blender-mcp.blender")
    ready = main.index('_wait_for_listener "127.0.0.1" "9876"', blender)
    api = main.index("_install_one com.blender-mcp.api", ready)

    assert "_wait_for_listener()" in source
    assert blender < ready < api


def test_blender_readiness_wait_covers_a_measured_cold_start() -> None:
    source = (PROJECT_ROOT / "deploy/launchd/install.sh").read_text()

    assert "for attempt in {1..180}" in source
    assert "within 90 seconds" in source


def test_start_services_delegates_to_the_launchd_ssot() -> None:
    source = (PROJECT_ROOT / "scripts/start_services.sh").read_text()

    assert 'deploy/launchd/install.sh" all' in source
    assert "nohup" not in source
    assert "node_modules/.bin/vite" not in source


def test_foreground_dev_runner_uses_canonical_api_and_dev_web_ports() -> None:
    source = (PROJECT_ROOT / "scripts/run_dev.sh").read_text()

    assert "API_PORT=19505" in source
    assert "WEB_PORT=5173" in source
    assert '--port "${API_PORT}"' in source
    assert '--port "${WEB_PORT}"' in source


def test_tailscale_registration_describes_the_production_preview() -> None:
    source = (PROJECT_ROOT / "scripts/tailscale-serve-register.sh").read_text()

    assert "production preview" in source
    assert "Vite dev server" not in source
