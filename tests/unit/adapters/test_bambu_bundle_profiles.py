"""P2S/PLA profiles come from the installed app bundle, flattened like v80's prepare_profiles."""

import json
from pathlib import Path

import pytest

import src.adapters.slicing.bambu_studio_cli as cli_module
from src.adapters.slicing.bambu_studio_cli import SLICE_TIMEOUT_S, BambuStudioCli
from src.adapters.slicing.bundle_profiles import flatten_leaf, profiles_root
from src.core.domain.model_spec import PrintTarget
from src.core.domain.slicing import SliceRequest, ToolUnavailableError
from tests.fakes.bambu_bundle import LEAVES, flattened, make_bundle
from tests.unit.adapters.test_bambu_studio_cli import FakeRunner

_CONFIG = Path(cli_module.__file__).resolve().parents[3] / "config" / "slicer-profiles"


def _request(tmp_path: Path) -> SliceRequest:
    return SliceRequest.from_target(
        str(tmp_path / "gate.3mf"), str(tmp_path / "out"), PrintTarget()
    )


def test_vendored_full_profiles_are_gone_and_leaves_are_named() -> None:
    assert sorted(p.name for p in _CONFIG.glob("*-full.json")) == []
    assert not (_CONFIG / "profile-provenance.json").exists()
    data = json.loads((_CONFIG / "p2s-pla-profiles.json").read_text(encoding="utf-8"))
    assert (data["machine"], data["process"], data["filament"]) == (
        "BBL/machine/Bambu Lab P2S 0.4 nozzle.json",
        "BBL/process/0.20mm Standard @BBL P2S.json",
        "BBL/filament/Generic PLA @BBL P2S.json",
    )


def test_profiles_root_is_derived_from_the_binary(tmp_path: Path) -> None:
    binary = make_bundle(tmp_path)
    assert profiles_root(binary) == tmp_path / "Fake.app" / "Contents" / "Resources" / "profiles"
    assert profiles_root(tmp_path / "bare-binary") is None


@pytest.mark.parametrize("kind", sorted(LEAVES))
def test_flatten_follows_two_level_inherits_child_wins(tmp_path: Path, kind: str) -> None:
    root = profiles_root(make_bundle(tmp_path))
    assert root is not None
    assert flatten_leaf(root, f"BBL/{kind}/{LEAVES[kind]}.json") == flattened(kind)


def test_flatten_rejects_inheritance_cycle(tmp_path: Path) -> None:
    kind_dir = tmp_path / "BBL" / "machine"
    kind_dir.mkdir(parents=True)
    (kind_dir / "a.json").write_text(json.dumps({"inherits": "b"}), encoding="utf-8")
    (kind_dir / "b.json").write_text(json.dumps({"inherits": "a"}), encoding="utf-8")
    with pytest.raises(ToolUnavailableError, match="cycle"):
        flatten_leaf(tmp_path, "BBL/machine/a.json")


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
