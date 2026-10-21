"""config/tools.yaml defaults with environment overrides; no hostnames or home dirs."""

import os
from pathlib import Path

from src.infrastructure.tools_config import load_tools_config

_YAML = (
    "bambu_studio_bin: /opt/bambu/BambuStudio\n"
    "design_runs_dir: data/runs\n"
    'artifact_roots: [".", "models"]\n'
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
