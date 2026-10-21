"""Typed view of ``config/tools.yaml`` with environment overrides."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.core.domain.import_limits import ImportLimits
from src.infrastructure.config_loader import default_config_dir, load_tools
from src.infrastructure.narrowing import as_sequence


@dataclass(frozen=True, slots=True)
class ToolsConfig:
    bambu_studio_bin: Path
    design_runs_dir: Path
    artifact_roots: tuple[Path, ...]
    import_limits: ImportLimits
    design_jobs_db: Path


def _resolve(base: Path, value: object) -> Path:
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else Path(os.path.normpath(base / path))


def _positive_int(value: object, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"config/tools.yaml: {key} must be a positive integer")
    return value


def load_tools_config(
    env: Mapping[str, str] | None = None, config_dir: Path | None = None
) -> ToolsConfig:
    """YAML defaults, overridden by BAMBU_STUDIO_BIN, DESIGN_RUNS_DIR, DESIGN_JOBS_DB and
    ARTIFACT_ROOTS.

    An empty env value falls back to the yaml value. ``~`` is expanded, then relative paths
    resolve against the repository root. A missing yaml key raises ``ValueError`` naming it.
    """
    env = os.environ if env is None else env
    raw = load_tools(config_dir)
    base = (config_dir or default_config_dir()).parent

    def yaml_value(key: str) -> object:
        if raw.get(key) is None:
            raise ValueError(f"config/tools.yaml: missing key {key}")
        return raw[key]

    roots_raw = as_sequence(yaml_value("artifact_roots"))
    if roots_raw is None:
        raise ValueError("config/tools.yaml: artifact_roots must be a list")
    roots_env = env.get("ARTIFACT_ROOTS")
    root_values: Sequence[object] = (
        [part for part in roots_env.split(os.pathsep) if part] if roots_env else roots_raw
    )
    limits = ImportLimits(
        max_stl_files=_positive_int(yaml_value("max_stl_files"), "max_stl_files"),
        max_stl_bytes=_positive_int(yaml_value("max_stl_bytes"), "max_stl_bytes"),
        max_3mf_bytes=_positive_int(yaml_value("max_3mf_bytes"), "max_3mf_bytes"),
        max_total_stl_bytes=_positive_int(yaml_value("max_total_stl_bytes"), "max_total_stl_bytes"),
    )
    return ToolsConfig(
        bambu_studio_bin=_resolve(
            base, env.get("BAMBU_STUDIO_BIN") or yaml_value("bambu_studio_bin")
        ),
        design_runs_dir=_resolve(base, env.get("DESIGN_RUNS_DIR") or yaml_value("design_runs_dir")),
        artifact_roots=tuple(_resolve(base, value) for value in root_values),
        import_limits=limits,
        design_jobs_db=_resolve(base, env.get("DESIGN_JOBS_DB") or yaml_value("design_jobs_db")),
    )
