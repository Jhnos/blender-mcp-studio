"""Only print inputs may be read: suffix allowlist and hidden-path ban (review Critical)."""

from __future__ import annotations

import pytest

from src.core.domain.model_spec import ModelSpecError, parse_model_spec


def _spec(tmp_path, **source):
    (tmp_path / "v78").mkdir(exist_ok=True)
    payload = {"spec_version": "1", "name": "v78", "source": {"root_dir": "v78", **source}}
    return parse_model_spec(payload, artifact_roots=(tmp_path,))


@pytest.mark.parametrize("project", [".env", "data/sessions.db", "x.stl", "a.3mf.txt"])
def test_project_3mf_must_be_3mf(tmp_path, project):
    with pytest.raises(ModelSpecError, match="project_3mf"):
        _spec(tmp_path, project_3mf=project)


def test_project_3mf_suffix_is_case_insensitive(tmp_path):
    assert _spec(tmp_path, project_3mf="P/A.3MF").source.project_3mf == "P/A.3MF"


@pytest.mark.parametrize("glob", ["**/*", "STL/*", "*.db", "STL/*.stl.bak"])
def test_stl_glob_must_end_in_stl(tmp_path, glob):
    with pytest.raises(ModelSpecError, match="stl_glob"):
        _spec(tmp_path, stl_glob=glob)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("stl_glob", ".git/x.stl"),
        ("stl_glob", "STL/.hidden/*.stl"),
        ("project_3mf", ".claude/a.3mf"),
        ("root_dir", ".git"),
        ("root_dir", "v78/.venv"),
    ],
)
def test_hidden_path_parts_rejected(tmp_path, field, value):
    (tmp_path / ".git").mkdir()
    with pytest.raises(ModelSpecError, match=field):
        _spec(tmp_path, **{field: value})


def test_dot_root_dir_is_allowed(tmp_path):
    payload = {"spec_version": "1", "name": "x", "source": {"root_dir": "."}}
    spec = parse_model_spec(payload, artifact_roots=(tmp_path,))
    assert spec.source.root_dir == str(tmp_path.resolve())
