"""Config loader — reads YAML config files, zero hardcoding."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_yaml(path: str | Path) -> dict[str, object]:
    """Load a YAML file and return as a dict."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_llm_providers(config_dir: Path | None = None) -> dict[str, object]:
    base = config_dir or Path(__file__).parent.parent.parent / "config"
    return load_yaml(base / "llm_providers.yaml")


def load_mcp_servers(config_dir: Path | None = None) -> dict[str, object]:
    base = config_dir or Path(__file__).parent.parent.parent / "config"
    return load_yaml(base / "mcp_servers.yaml")


def load_workflow(name: str, config_dir: Path | None = None) -> dict[str, object]:
    base = config_dir or Path(__file__).parent.parent.parent / "config"
    return load_yaml(base / "workflows" / f"{name}.yaml")
