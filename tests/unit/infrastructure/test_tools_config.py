"""config/tools.yaml defaults with environment overrides; no hostnames or home dirs."""

import os
from pathlib import Path

import pytest

from src.infrastructure.tools_config import load_tools_config

_YAML = (
    "bambu_studio_bin: /opt/bambu/BambuStudio\n"
    "design_runs_dir: data/runs\n"
    "design_jobs_db: data/jobs.db\n"
    'artifact_roots: [".", "models"]\n'
    "max_stl_files: 565\n"
    "max_stl_bytes: 2457920\n"
    "max_3mf_bytes: 7036310\n"
    "max_total_stl_bytes: 29292960\n"
)


def _config_dir(tmp_path: Path) -> Path:
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "tools.yaml").write_text(_YAML, encoding="utf-8")
    return cfg


def test_tools_config_reads_yaml_defaults(tmp_path: Path) -> None:
    cfg = load_tools_config(env={}, config_dir=_config_dir(tmp_path))
    assert cfg.bambu_studio_bin == Path("/opt/bambu/BambuStudio")
    assert cfg.design_runs_dir == tmp_path / "data" / "runs"
    assert cfg.artifact_roots == (tmp_path, tmp_path / "models")


def test_tools_config_env_overrides_yaml(tmp_path: Path) -> None:
    other = tmp_path / "elsewhere"
    env = {
        "BAMBU_STUDIO_BIN": "/x/Bambu",
        "DESIGN_RUNS_DIR": str(other / "runs"),
        "ARTIFACT_ROOTS": os.pathsep.join([str(other / "a"), str(other / "b")]),
    }
    cfg = load_tools_config(env=env, config_dir=_config_dir(tmp_path))
    assert cfg.bambu_studio_bin == Path("/x/Bambu")
    assert cfg.design_runs_dir == other / "runs"
    assert cfg.artifact_roots == (other / "a", other / "b")


def test_shipped_tools_yaml_loads() -> None:
    cfg = load_tools_config(env={})
    assert cfg.bambu_studio_bin.name == "BambuStudio"
    assert cfg.design_runs_dir.parts[-2:] == ("data", "runs")


def test_missing_yaml_key_names_it(tmp_path: Path) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "tools.yaml").write_text(
        'design_runs_dir: d\nartifact_roots: ["."]\nmax_stl_files: 1\nmax_stl_bytes: 1\nmax_3mf_bytes: 1\nmax_total_stl_bytes: 1\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="bambu_studio_bin"):
        load_tools_config(env={}, config_dir=cfg)


def test_tilde_is_expanded(tmp_path: Path) -> None:
    env = {"BAMBU_STUDIO_BIN": "~/B", "DESIGN_RUNS_DIR": "~/runs", "ARTIFACT_ROOTS": "~/a"}
    cfg = load_tools_config(env=env, config_dir=_config_dir(tmp_path))
    home = Path.home()
    assert cfg.bambu_studio_bin == home / "B"
    assert cfg.design_runs_dir == home / "runs"
    assert cfg.artifact_roots == (home / "a",)


def test_jobs_db_comes_from_yaml_with_env_override(tmp_path: Path) -> None:
    cfg_dir = _config_dir(tmp_path)
    assert load_tools_config(env={}, config_dir=cfg_dir).design_jobs_db == (
        tmp_path / "data" / "jobs.db"
    )
    env = {"DESIGN_JOBS_DB": str(tmp_path / "other" / "j.db")}
    assert load_tools_config(env=env, config_dir=cfg_dir).design_jobs_db == (
        tmp_path / "other" / "j.db"
    )


def test_shipped_tools_yaml_names_the_jobs_db() -> None:
    assert load_tools_config(env={}).design_jobs_db.parts[-2:] == ("data", "jobs.db")
