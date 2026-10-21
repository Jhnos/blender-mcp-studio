"""Import caps are data in config/tools.yaml (derived from measurement, see the yaml comment)."""

from pathlib import Path

import pytest

from src.infrastructure.tools_config import load_tools_config

_LINES = [
    "bambu_studio_bin: /opt/bambu/BambuStudio",
    "design_runs_dir: data/runs",
    "design_jobs_db: data/jobs.db",
    'artifact_roots: ["."]',
    "max_stl_files: 565",
    "max_stl_bytes: 2457920",
    "max_3mf_bytes: 7036310",
    "max_total_stl_bytes: 29292960",
]


def _load(tmp_path: Path, lines: list[str]):
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "tools.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return load_tools_config(env={}, config_dir=cfg)


def test_import_limits_are_loaded_from_yaml(tmp_path: Path) -> None:
    limits = _load(tmp_path, _LINES).import_limits
    assert (limits.max_stl_files, limits.max_stl_bytes, limits.max_3mf_bytes) == (
        565,
        2457920,
        7036310,
    )


def test_shipped_yaml_carries_the_measured_limits() -> None:
    limits = load_tools_config(env={}).import_limits
    assert limits.max_stl_files == 565 and limits.max_3mf_bytes == 7036310


@pytest.mark.parametrize(
    "key", ["max_stl_files", "max_stl_bytes", "max_3mf_bytes", "max_total_stl_bytes"]
)
def test_missing_limit_key_names_it(tmp_path: Path, key: str) -> None:
    kept = [line for line in _LINES if not line.startswith(key)]
    with pytest.raises(ValueError, match=key):
        _load(tmp_path, kept)
