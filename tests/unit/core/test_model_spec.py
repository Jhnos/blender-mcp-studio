from __future__ import annotations

import pytest

from src.core.domain.model_spec import ModelSpecError, parse_model_spec


def _payload(**source: object) -> dict[str, object]:
    return {"spec_version": "1", "name": "v78", "source": {"root_dir": "v78", **source}}


def test_parse_minimal_spec_resolves_root_inside_allowed_roots(tmp_path):
    (tmp_path / "v78").mkdir()
    spec = parse_model_spec(_payload(), artifact_roots=(tmp_path,))
    assert spec.source.root_dir == str(tmp_path / "v78")
    assert spec.print_target.printer == "bambu-p2s"
    assert spec.mechanism.suites == ()


def test_imported_artifact_rejects_escape(tmp_path):
    with pytest.raises(ModelSpecError):
        parse_model_spec(_payload(root_dir="../etc"), artifact_roots=(tmp_path,))


def test_absolute_path_outside_roots_is_rejected(tmp_path):
    with pytest.raises(ModelSpecError):
        parse_model_spec(_payload(root_dir="/etc"), artifact_roots=(tmp_path,))


def test_unknown_spec_version_is_rejected(tmp_path):
    payload = _payload()
    payload["spec_version"] = "2"
    with pytest.raises(ModelSpecError):
        parse_model_spec(payload, artifact_roots=(tmp_path,))


def test_unknown_keys_are_rejected(tmp_path):
    with pytest.raises(ModelSpecError):
        parse_model_spec(_payload(code="x"), artifact_roots=(tmp_path,))
    top = _payload()
    top["extra"] = 1
    with pytest.raises(ModelSpecError):
        parse_model_spec(top, artifact_roots=(tmp_path,))


def test_print_target_and_mechanism_overrides_are_parsed(tmp_path):
    payload = _payload()
    payload["print_target"] = {"material": "PETG", "support": False}
    payload["mechanism"] = {"suites": []}  # A5: v1 rejects non-empty suites
    spec = parse_model_spec(payload, artifact_roots=(tmp_path,))
    assert spec.print_target.material == "PETG" and spec.print_target.support is False
    assert spec.mechanism.suites == ()
    bad = _payload()
    bad["print_target"] = {"nozzle": 1}
    with pytest.raises(ModelSpecError):
        parse_model_spec(bad, artifact_roots=(tmp_path,))


def _with_source(tmp_path, **source):
    (tmp_path / "v78").mkdir(exist_ok=True)
    return parse_model_spec(_payload(**source), artifact_roots=(tmp_path,))


@pytest.mark.parametrize("glob", ["../../*.stl", "/etc/*.stl", ""])
def test_stl_glob_rejects_escape(tmp_path, glob):
    with pytest.raises(ModelSpecError, match="stl_glob"):
        _with_source(tmp_path, stl_glob=glob)


@pytest.mark.parametrize("project", ["../x.3mf", "/etc/x", ""])
def test_project_3mf_rejects_escape(tmp_path, project):
    with pytest.raises(ModelSpecError, match="project_3mf"):
        _with_source(tmp_path, project_3mf=project)


def test_project_3mf_rejects_symlink_out_of_root(tmp_path):
    outside = tmp_path / "outside.3mf"
    outside.write_bytes(b"x")
    (tmp_path / "v78").mkdir()
    (tmp_path / "v78" / "link.3mf").symlink_to(outside)
    with pytest.raises(ModelSpecError, match="project_3mf"):
        parse_model_spec(_payload(project_3mf="link.3mf"), artifact_roots=(tmp_path,))


def test_relative_glob_and_project_still_parse(tmp_path):
    spec = _with_source(tmp_path, stl_glob="STL/*.stl", project_3mf="Project/a.3mf")
    assert spec.source.stl_glob == "STL/*.stl" and spec.source.project_3mf == "Project/a.3mf"


def test_non_str_key_is_model_spec_error(tmp_path):
    payload = _payload()
    payload[1] = "x"  # type: ignore[index]
    with pytest.raises(ModelSpecError):
        parse_model_spec(payload, artifact_roots=(tmp_path,))


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("layer_height_mm", -1),
        ("layer_height_mm", 0),
        ("layer_height_mm", float("nan")),
        ("layer_height_mm", float("inf")),
        ("brim_mm", -1),
        ("brim_mm", float("inf")),
    ],
)
def test_print_target_rejects_non_physical(tmp_path, key, value):
    payload = _payload()
    payload["print_target"] = {key: value}
    with pytest.raises(ModelSpecError, match=key):
        parse_model_spec(payload, artifact_roots=(tmp_path,))


def test_missing_spec_version_message(tmp_path):
    payload = _payload()
    del payload["spec_version"]
    with pytest.raises(ModelSpecError, match="missing spec_version"):
        parse_model_spec(payload, artifact_roots=(tmp_path,))
