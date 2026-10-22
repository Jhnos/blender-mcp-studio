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
    assert (-61, "filament does not match bed type") in catalog.slicer("orcaslicer").error_codes


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


@pytest.mark.xfail(strict=True, reason="Task 4 removes the PrintTarget default")
def test_print_target_requires_printer() -> None:
    with pytest.raises(TypeError):
        PrintTarget()  # type: ignore[call-arg]


def test_orcaslicer_bin_env_override() -> None:
    assert load_tools_config(env={}).orcaslicer_bin.name == "OrcaSlicer"
    cfg = load_tools_config(env={"ORCASLICER_BIN": "/x/Orca"})
    assert cfg.orcaslicer_bin == Path("/x/Orca")
