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
    payload["mechanism"] = {"suites": ["hand"]}
    spec = parse_model_spec(payload, artifact_roots=(tmp_path,))
    assert spec.print_target.material == "PETG" and spec.print_target.support is False
    assert spec.mechanism.suites == ("hand",)
    bad = _payload()
    bad["print_target"] = {"nozzle": 1}
    with pytest.raises(ModelSpecError):
        parse_model_spec(bad, artifact_roots=(tmp_path,))
