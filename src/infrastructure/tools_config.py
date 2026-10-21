"""Typed view of ``config/tools.yaml`` with environment overrides."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.infrastructure.config_loader import default_config_dir, load_tools
from src.infrastructure.narrowing import as_sequence


@dataclass(frozen=True, slots=True)
class ToolsConfig:
    bambu_studio_bin: Path
    design_runs_dir: Path
    artifact_roots: tuple[Path, ...]


def _resolve(base: Path, value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else Path(os.path.normpath(base / path))


def load_tools_config(
    env: Mapping[str, str] | None = None, config_dir: Path | None = None
) -> ToolsConfig:
    """YAML defaults, overridden by BAMBU_STUDIO_BIN, DESIGN_RUNS_DIR and ARTIFACT_ROOTS."""
    env = os.environ if env is None else env
    raw = load_tools(config_dir)
    base = (config_dir or default_config_dir()).parent
    roots_raw = as_sequence(raw.get("artifact_roots"))
    if roots_raw is None:
        raise ValueError("config/tools.yaml: artifact_roots must be a list")
    roots_env = env.get("ARTIFACT_ROOTS")
    root_values: Sequence[object] = (
        [part for part in roots_env.split(os.pathsep) if part] if roots_env else roots_raw
    )
    return ToolsConfig(
        bambu_studio_bin=_resolve(base, env.get("BAMBU_STUDIO_BIN") or raw["bambu_studio_bin"]),
        design_runs_dir=_resolve(base, env.get("DESIGN_RUNS_DIR") or raw["design_runs_dir"]),
        artifact_roots=tuple(_resolve(base, value) for value in root_values),
    )
