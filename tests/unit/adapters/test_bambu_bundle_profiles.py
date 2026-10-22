"""Profiles come from the installed app bundle, resolved by JSON name, flattened like v80."""

import json
from pathlib import Path

import pytest

import src.adapters.slicing.bambu_studio_cli as cli_module
from src.adapters.slicing.bambu_studio_cli import SLICE_TIMEOUT_S, BambuStudioCli
from src.adapters.slicing.bundle_profiles import (
    IncompatibleProfileError,
    UnknownProfileError,
    check_compatible,
    profiles_root,
    resolve_printer_profiles,
)
from src.core.domain.model_spec import PrintTarget
from src.core.domain.printer_catalog import PrinterProfile
from src.core.domain.slicing import SliceRequest, ToolUnavailableError
from src.infrastructure.printer_catalog_loader import load_printer_catalog
from tests.fakes.bambu_bundle import LEAVES, flattened, make_bundle, make_named_bundle
from tests.unit.adapters.test_bambu_studio_cli import FakeRunner

_CONFIG = Path(cli_module.__file__).resolve().parents[3] / "config" / "slicer-profiles"


def _request(tmp_path: Path) -> SliceRequest:
    return SliceRequest.from_target(
        str(tmp_path / "gate.3mf"), str(tmp_path / "out"), PrintTarget()
    )


def test_vendored_full_profiles_are_gone_and_leaves_live_in_the_printer_yaml() -> None:
    assert sorted(p.name for p in _CONFIG.glob("*-full.json")) == []
    assert not (_CONFIG / "profile-provenance.json").exists()
    assert not (_CONFIG / "p2s-pla-profiles.json").exists()
    p2s = load_printer_catalog().printer("bambu-p2s-0.4")
    assert (p2s.machine, dict(p2s.processes)["0.20"], dict(p2s.filaments)["PLA"]) == (
        LEAVES["machine"],
        LEAVES["process"],
        LEAVES["filament"],
    )


def test_profiles_root_is_derived_from_the_binary(tmp_path: Path) -> None:
    binary = make_bundle(tmp_path)
    assert profiles_root(binary) == tmp_path / "Fake.app" / "Contents" / "Resources" / "profiles"
    assert profiles_root(tmp_path / "bare-binary") is None


def _p2s() -> PrinterProfile:
    return load_printer_catalog().printer("bambu-p2s-0.4")


@pytest.mark.parametrize("kind", sorted(LEAVES))
def test_flatten_follows_two_level_inherits_child_wins(tmp_path: Path, kind: str) -> None:
    root = profiles_root(make_bundle(tmp_path))
    assert root is not None
    assert resolve_printer_profiles(root, _p2s(), "0.20", "PLA")[kind] == flattened(kind)


def test_flatten_rejects_inheritance_cycle(tmp_path: Path) -> None:
    kind_dir = tmp_path / "Acme" / "machine"
    kind_dir.mkdir(parents=True)
    (kind_dir / "a.json").write_text(json.dumps({"name": "a", "inherits": "b"}), encoding="utf-8")
    (kind_dir / "b.json").write_text(json.dumps({"name": "b", "inherits": "a"}), encoding="utf-8")
    with pytest.raises(ToolUnavailableError, match="cycle"):
        resolve_printer_profiles(tmp_path, _acme(machine="a"), "0.20", "PLA")


async def test_slice_writes_profiles_flattened_from_the_bundle(tmp_path: Path) -> None:
    cli = BambuStudioCli(make_bundle(tmp_path), profiles_dir=_CONFIG, runner=FakeRunner())
    await cli.slice(_request(tmp_path))
    out = tmp_path / "out"
    for kind in ("machine", "filament"):
        assert json.loads((out / f"{kind}.json").read_text(encoding="utf-8")) == flattened(kind)
    process = json.loads((out / "process.json").read_text(encoding="utf-8"))
    assert process["leaf_key"] == "leaf" and process["wall_loops"] == "3"


async def test_bundle_without_profiles_dir_is_unavailable(tmp_path: Path) -> None:
    runner = FakeRunner()
    cli = BambuStudioCli(make_bundle(tmp_path, profiles=False), profiles_dir=_CONFIG, runner=runner)
    with pytest.raises(ToolUnavailableError, match="no profiles directory") as info:
        await cli.slice(_request(tmp_path))
    assert str(tmp_path) not in str(info.value)
    assert runner.argv == []  # the slicer never started


def test_adapter_exposes_its_timeout_through_the_port(tmp_path: Path) -> None:
    cli = BambuStudioCli(make_bundle(tmp_path), profiles_dir=_CONFIG, runner=FakeRunner())
    assert cli.timeout_s == SLICE_TIMEOUT_S


# ---- resolution by JSON name, with a non-Bambu vendor whose file names differ ----


def _acme(*, machine: str = "Acme Z 0.4 nozzle", material: str = "Acme PLA") -> PrinterProfile:
    return PrinterProfile(
        id="acme-z-0.4",
        vendor="Acme",
        model="Z",
        nozzle_mm=0.4,
        slicer="orcaslicer",
        profile_vendor_dir="Acme",
        machine=machine,
        processes=(("0.20", "0.20mm Standard @Acme"),),
        filaments=(("PLA", material),),
        bed_type="Textured PEI Plate",
        overrides=None,
    )


def test_name_index_resolves_when_filename_differs(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    got = resolve_printer_profiles(root, _acme(), "0.20", "PLA")
    assert got["machine"]["name"] == "Acme Z 0.4 nozzle"
    assert got["machine"]["bed"] == "220x220"
    assert got["filament"]["name"] == "Acme PLA"
    assert got["process"]["name"] == "0.20mm Standard @Acme"


def test_inherits_resolves_by_name(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    process = resolve_printer_profiles(root, _acme(), "0.20", "PLA")["process"]
    assert process["wall_loops"] == "2"  # parent named "fdm base" lives in base_file.json
    assert process["inherits"] == ""


def test_unknown_profile_name_names_it(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    with pytest.raises(UnknownProfileError, match="Acme Gold") as info:
        resolve_printer_profiles(root, _acme(material="Acme Gold"), "0.20", "PLA")
    assert str(tmp_path) not in str(info.value)


def test_duplicate_profile_name_is_ambiguous_and_names_both_files(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    (root / "Acme" / "filament" / "f_dup.json").write_text(
        json.dumps({"name": "Acme PLA"}), encoding="utf-8"
    )
    with pytest.raises(UnknownProfileError) as info:
        resolve_printer_profiles(root, _acme(), "0.20", "PLA")
    assert "f_ok.json" in str(info.value) and "f_dup.json" in str(info.value)


def test_unreadable_json_file_is_skipped_by_the_index(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    (root / "Acme" / "filament" / "broken.json").write_text("{not json", encoding="utf-8")
    assert resolve_printer_profiles(root, _acme(), "0.20", "PLA")["filament"]["name"] == "Acme PLA"


def test_incompatible_filament_rejected(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    profiles = resolve_printer_profiles(root, _acme(material="Acme PETG"), "0.20", "PLA")
    with pytest.raises(IncompatibleProfileError, match="Acme PETG.*Acme Z 0.4 nozzle"):
        check_compatible(profiles, "Acme Z 0.4 nozzle")


def test_empty_compatible_printers_means_any(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    profiles = resolve_printer_profiles(root, _acme(), "0.20", "PLA")
    check_compatible(profiles, "Acme Z 0.4 nozzle")
    # the filament (empty list) fits any machine; the process lists only Acme Z
    check_compatible({"filament": profiles["filament"]}, "Some Other Machine")
    with pytest.raises(IncompatibleProfileError, match="0.20mm Standard @Acme"):
        check_compatible(profiles, "Some Other Machine")


def test_unrelated_duplicate_name_does_not_break_resolution(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    for stem in ("x1", "x2"):
        (root / "Acme" / "filament" / f"{stem}.json").write_text(
            json.dumps({"name": "Acme Unrelated"}), encoding="utf-8"
        )
    got = resolve_printer_profiles(root, _acme(), "0.20", "PLA")
    assert got["filament"]["name"] == "Acme PLA"


def test_unreadable_profile_named_as_unreadable(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    (root / "Acme" / "process" / "base_file.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ToolUnavailableError, match="unreadable") as info:
        resolve_printer_profiles(root, _acme(), "0.20", "PLA")
    assert "base_file.json" in str(info.value) and str(tmp_path) not in str(info.value)


def test_unevaluated_condition_is_reported(tmp_path: Path) -> None:
    root = make_named_bundle(tmp_path)
    profiles = resolve_printer_profiles(root, _acme(), "0.20", "PLA")
    assert check_compatible(profiles, "Acme Z 0.4 nozzle") == ()
    profiles["filament"]["compatible_printers_condition"] = "printer_notes=~/.*X.*/"
    notes = check_compatible(profiles, "Acme Z 0.4 nozzle")
    assert len(notes) == 1 and "filament" in notes[0] and "Acme PLA" in notes[0]
