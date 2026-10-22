"""Spec v2: printer and material are required; v1 keeps working through the legacy fill."""

from __future__ import annotations

import pytest

from src.core.domain.model_spec import ModelSpecError, PrintTarget, parse_model_spec
from src.core.domain.model_spec_schema import describe_model_spec
from src.infrastructure.printer_catalog_loader import load_printer_catalog

P2S, K1C = "bambu-p2s-0.4", "creality-k1c-0.4"


def _payload(version: str = "2", **extra: object) -> dict[str, object]:
    return {"spec_version": version, "name": "demo", "source": {"root_dir": "d"}, **extra}


def _parse(tmp_path, payload):
    (tmp_path / "d").mkdir(exist_ok=True)
    return parse_model_spec(payload, artifact_roots=(tmp_path,))


def test_v2_requires_printer(tmp_path):
    with pytest.raises(ModelSpecError, match="print_target.printer is required in spec v2"):
        _parse(tmp_path, _payload(print_target={"material": "PLA"}))
    with pytest.raises(ModelSpecError, match="print_target.printer is required in spec v2"):
        _parse(tmp_path, _payload())  # no print_target at all


def test_v2_requires_material(tmp_path):
    with pytest.raises(ModelSpecError, match="print_target.material is required in spec v2"):
        _parse(tmp_path, _payload(print_target={"printer": P2S}))


def test_v2_parses_an_explicit_target_without_legacy_fill(tmp_path):
    spec = _parse(tmp_path, _payload(print_target={"printer": K1C, "material": "PLA"}))
    assert (spec.print_target.printer, spec.print_target.material) == (K1C, "PLA")
    assert spec.legacy_default is False and spec.legacy_defaults == ()
    assert spec.spec_version == "2"


def test_v2_does_not_translate_v1_printer_names(tmp_path):
    spec = _parse(tmp_path, _payload(print_target={"printer": "bambu-p2s", "material": "PLA"}))
    assert spec.print_target.printer == "bambu-p2s"  # unknown to the catalog: submit rejects it


def test_v1_spec_maps_to_legacy_printer_with_note(tmp_path):
    spec = _parse(tmp_path, _payload("1"))
    assert (spec.print_target.printer, spec.print_target.material) == (P2S, "PLA")
    assert spec.legacy_default is True
    assert spec.legacy_defaults == (("printer", P2S), ("material", "PLA"))


def test_v1_names_only_what_it_left_out(tmp_path):
    spec = _parse(tmp_path, _payload("1", print_target={"printer": "bambu-p2s"}))
    assert spec.print_target.printer == P2S  # the v1 name translated to its catalog id
    assert spec.legacy_defaults == (("material", "PLA"),)
    full = _parse(tmp_path, _payload("1", print_target={"printer": P2S, "material": "PLA"}))
    assert full.legacy_default is False


def test_print_target_has_no_machine_defaults() -> None:
    with pytest.raises(TypeError):
        PrintTarget()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        PrintTarget(printer=P2S)  # type: ignore[call-arg]


def test_unknown_spec_version_error_lists_both_versions(tmp_path):
    with pytest.raises(ModelSpecError) as info:
        _parse(tmp_path, _payload("3"))
    assert str(info.value) == "unsupported spec_version: '3' (supported: '1', '2')"


def test_describe_model_spec_v2_example_parses(tmp_path):
    catalog = load_printer_catalog()
    printers = (catalog.printer(P2S), catalog.printer(K1C))
    described = describe_model_spec(printers)
    assert described["spec_version"] == "2"
    schema = described["schema"]
    assert "print_target" in schema["required"]
    target = schema["properties"]["print_target"]
    assert target["required"] == ["printer", "material"]
    assert target["properties"]["printer"]["enum"] == [P2S, K1C]
    assert "default" not in target["properties"]["printer"]
    assert "default" not in target["properties"]["material"]
    by_printer = {
        rule["if"]["properties"]["printer"]["const"]: rule["then"]["properties"]
        for rule in target["allOf"]
    }
    assert by_printer[P2S]["material"]["enum"] == ["PLA"]
    assert by_printer[K1C]["layer_height_mm"]["enum"] == [0.2]
    example = described["example"]
    assert example["print_target"] == {"printer": P2S, "material": "PLA"}
    root = tmp_path / "layout"
    source = example["source"]
    stl_dir = root / source["root_dir"] / "STL" / "列印零件"
    stl_dir.mkdir(parents=True)
    spec = parse_model_spec(example, artifact_roots=(root,))
    assert spec.spec_version == "2" and spec.legacy_default is False
