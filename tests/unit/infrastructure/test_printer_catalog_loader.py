"""Printer and slicer catalog: one YAML per printer, one entry per slicer, no default machine."""

from pathlib import Path

import pytest

from src.core.domain.exceptions import DomainError
from src.core.domain.model_spec import PrintTarget
from src.core.domain.printer_catalog import PrinterCatalog, UnknownPrinterError
from src.infrastructure.printer_catalog_loader import load_printer_catalog
from src.infrastructure.tools_config import load_tools_config

_SLICERS = """\
slicers:
  - id: orcaslicer
    name: OrcaSlicer
    binary_key: orcaslicer_bin
    profiles_subdir: Contents/Resources/profiles
    license: AGPL-3.0-only
    error_codes: []
    install_hint: install it
"""


def _printer(printer_id: str, slicer: str = "orcaslicer") -> str:
    return (
        f"id: {printer_id}\nvendor: Acme\nmodel: M\nnozzle_mm: 0.4\nslicer: {slicer}\n"
        "profile_vendor_dir: Acme\nmachine: m\nprocesses: {'0.20': p}\n"
        "filaments: {PLA: f}\nbed_type: Textured PEI Plate\noverrides: null\n"
    )


def _config(tmp_path: Path, files: dict[str, str]) -> Path:
    cfg = tmp_path / "config"
    (cfg / "printers" / "acme").mkdir(parents=True)
    (cfg / "slicers.yaml").write_text(_SLICERS, encoding="utf-8")
    for name, text in files.items():
        (cfg / "printers" / "acme" / name).write_text(text, encoding="utf-8")
    return cfg


def test_loads_seven_printers_and_two_slicers() -> None:
    catalog = load_printer_catalog()
    assert sorted(p.id for p in catalog.printers) == [
        "bambu-p2s-0.4",
        "creality-ender-3-v3-0.4",
        "creality-ender-3-v3-ke-0.4",
        "creality-k1-0.4",
        "creality-k1-max-0.4",
        "creality-k1c-0.4",
        "creality-k2-plus-0.4",
    ]
    assert sorted(s.id for s in catalog.slicers) == ["bambu-studio", "orcaslicer"]
    assert catalog.printer("bambu-p2s-0.4").slicer == "bambu-studio"
    assert catalog.slicer("orcaslicer").binary_key == "orcaslicer_bin"
    codes = {c.code: c for c in catalog.slicer("orcaslicer").error_codes}
    assert codes[-61].meaning == "filament does not match bed type"
    assert codes[-61].name == "CLI_FILAMENT_NOT_MATCH_BED_TYPE"


def test_every_orca_code_has_its_macro_name_and_orca_hint() -> None:
    codes = load_printer_catalog().slicer("orcaslicer").error_codes
    assert len(codes) == 46
    assert all(c.name.startswith("CLI_") and c.hint and c.meaning for c in codes)
    by_code = {c.code: c for c in codes}
    assert by_code[-52].name == "CLI_OBJECTS_PARTLY_INSIDE"
    assert by_code[-101].hint.startswith("G-code conflicts detected after slicing.")


def test_every_bambu_code_has_its_macro_name_and_hint() -> None:
    codes = load_printer_catalog().slicer("bambu-studio").error_codes
    assert len(codes) == 50  # BambuStudio v02.08.02.61 Utils.hpp, CLI_SUCCESS excluded
    assert all(c.name.startswith("CLI_") and c.hint and c.meaning for c in codes)
    by_code = {c.code: c for c in codes}
    assert by_code[-101].name == "CLI_GCODE_PATH_CONFLICTS"
    assert by_code[-105].name == "CLI_GCODE_IN_WRAPPING_DETECT_AREA"
    assert "Bambu Studio" in by_code[-100].hint


def test_unknown_error_code_key_rejected(tmp_path: Path) -> None:
    cfg = _config(tmp_path, {"a.yaml": _printer("x")})
    text = _SLICERS.replace(
        "error_codes: []", "error_codes:\n      - {code: -1, meaning: m, severity: high}"
    )
    (cfg / "slicers.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="slicers.yaml: unknown key.*severity"):
        load_printer_catalog(cfg)


def test_unknown_printer_error_lists_ids() -> None:
    catalog = load_printer_catalog()
    with pytest.raises(UnknownPrinterError) as caught:
        catalog.printer("nope")
    assert isinstance(caught.value, DomainError)
    for printer in catalog.printers:
        assert printer.id in str(caught.value)


def test_duplicate_printer_id_rejected(tmp_path: Path) -> None:
    cfg = _config(tmp_path, {"a.yaml": _printer("dup"), "b.yaml": _printer("dup")})
    with pytest.raises(ValueError, match=r"duplicate printer id 'dup'.*b\.yaml"):
        load_printer_catalog(cfg)


def test_unknown_slicer_rejected(tmp_path: Path) -> None:
    cfg = _config(tmp_path, {"a.yaml": _printer("x", slicer="ghost")})
    with pytest.raises(ValueError, match=r"a\.yaml.*unknown slicer 'ghost'"):
        load_printer_catalog(cfg)


def test_no_default_printer_exists() -> None:
    import src.core.domain.printer_catalog as domain
    import src.infrastructure.printer_catalog_loader as loader

    assert not any("default" in name.lower() for name in dir(PrinterCatalog))
    for module in (domain, loader):
        assert not any("default" in name.lower() for name in vars(module))


def test_print_target_requires_printer() -> None:
    with pytest.raises(TypeError):
        PrintTarget()  # type: ignore[call-arg]


def test_orcaslicer_bin_env_override() -> None:
    assert load_tools_config(env={}).orcaslicer_bin.name == "OrcaSlicer"
    cfg = load_tools_config(env={"ORCASLICER_BIN": "/x/Orca"})
    assert cfg.orcaslicer_bin == Path("/x/Orca")


def test_list_root_named(tmp_path: Path) -> None:
    cfg = _config(tmp_path, {"a.yaml": "- 1\n- 2\n"})
    with pytest.raises(ValueError, match="printers/acme/a.yaml: top level must be a mapping"):
        load_printer_catalog(cfg)
    (cfg / "slicers.yaml").write_text("- x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="slicers.yaml: top level must be a mapping"):
        load_printer_catalog(cfg)


def test_invalid_yaml_named(tmp_path: Path) -> None:
    cfg = _config(tmp_path, {"a.yaml": "id: [unclosed\n"})
    with pytest.raises(ValueError, match="printers/acme/a.yaml: invalid YAML") as caught:
        load_printer_catalog(cfg)
    assert str(tmp_path) not in str(caught.value)


def test_unknown_key_rejected(tmp_path: Path) -> None:
    cfg = _config(tmp_path, {"a.yaml": _printer("x") + "default: true\n"})
    with pytest.raises(ValueError, match="a.yaml: unknown key.*default"):
        load_printer_catalog(cfg)
    (cfg / "printers" / "acme" / "a.yaml").write_text(_printer("x"), encoding="utf-8")
    (cfg / "slicers.yaml").write_text(_SLICERS + "    default: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="slicers.yaml: unknown key.*default"):
        load_printer_catalog(cfg)


def test_duplicate_slicer_id_rejected(tmp_path: Path) -> None:
    cfg = _config(tmp_path, {"a.yaml": _printer("x")})
    entry = _SLICERS.split("slicers:\n")[1]
    (cfg / "slicers.yaml").write_text(_SLICERS + entry, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate slicer id 'orcaslicer'"):
        load_printer_catalog(cfg)


@pytest.mark.parametrize(
    "stray", ["printers/acme/b.yml", "printers/acme/b.txt", "printers/top.yaml"]
)
def test_stray_file_rejected(tmp_path: Path, stray: str) -> None:
    cfg = _config(tmp_path, {"a.yaml": _printer("x")})
    (cfg / stray).write_text(_printer("y"), encoding="utf-8")
    with pytest.raises(ValueError, match=stray):
        load_printer_catalog(cfg)
    (cfg / stray).unlink()
    (cfg / "printers" / "acme" / ".DS_Store").write_bytes(b"x")
    assert len(load_printer_catalog(cfg).printers) == 1


def test_empty_catalog_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no printers"):
        load_printer_catalog(_config(tmp_path, {}))


# ---- config errors fail at load, naming the key (final fix F5) ----


def test_binary_key_must_name_a_tools_config_field(tmp_path: Path) -> None:
    cfg = _config(tmp_path, {"a.yaml": _printer("acme-a")})
    bad = _SLICERS.replace("binary_key: orcaslicer_bin", "binary_key: orca_bin")
    (cfg / "slicers.yaml").write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError, match="binary_key 'orca_bin'.*orcaslicer_bin"):
        load_printer_catalog(cfg)


@pytest.mark.parametrize("key", ["fine", "0", "-0.2", "nan"])
def test_process_keys_must_be_positive_heights(tmp_path: Path, key: str) -> None:
    text = _printer("acme-a").replace("{'0.20': p}", "{'" + key + "': p}")
    with pytest.raises(ValueError, match=f"acme/a.yaml: processes key '{key}'"):
        load_printer_catalog(_config(tmp_path, {"a.yaml": text}))


def test_overrides_file_must_exist(tmp_path: Path) -> None:
    text = _printer("acme-a").replace("overrides: null", "overrides: missing.json")
    cfg = _config(tmp_path, {"a.yaml": text})
    with pytest.raises(ValueError, match="acme/a.yaml: overrides 'missing.json'"):
        load_printer_catalog(cfg)
    (cfg / "slicer-profiles").mkdir()
    (cfg / "slicer-profiles" / "missing.json").write_text("{}", encoding="utf-8")
    assert load_printer_catalog(cfg).printer("acme-a").overrides == "missing.json"


def test_float_key_rejected(tmp_path: Path) -> None:
    text = _printer("x").replace("{'0.20': p}", "{0.20: p}")
    cfg = _config(tmp_path, {"a.yaml": text})
    with pytest.raises(ValueError, match="a.yaml: processes key 0.2 must be a string.*quote"):
        load_printer_catalog(cfg)
