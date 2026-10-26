"""Config loader — reads YAML config files, zero hardcoding."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.core.domain.model_spec import ModelSpecError
from src.infrastructure.narrowing import as_str_keyed_exact


def load_yaml(path: str | Path) -> dict[str, object]:
    """Load a YAML file and return as a dict."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def default_config_dir() -> Path:
    return Path(__file__).parent.parent.parent / "config"


def load_tools(config_dir: Path | None = None) -> dict[str, object]:
    return load_yaml((config_dir or default_config_dir()) / "tools.yaml")


def load_llm_providers(config_dir: Path | None = None) -> dict[str, object]:
    base = config_dir or default_config_dir()
    return load_yaml(base / "llm_providers.yaml")


def load_mcp_servers(config_dir: Path | None = None) -> dict[str, object]:
    base = config_dir or default_config_dir()
    return load_yaml(base / "mcp_servers.yaml")


def load_selected_model_spec(project_root: Path | None = None) -> dict[str, object]:
    """Read the sole current-delivery declaration afresh; never infer a fallback version."""
    path = (project_root or default_config_dir().parent) / "models/lab-station/model-spec.json"
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ModelSpecError("selected model declaration is missing or unreadable") from exc
    selected = as_str_keyed_exact(raw)
    if selected is None:
        raise ModelSpecError("selected model declaration must be an object")
    return selected
