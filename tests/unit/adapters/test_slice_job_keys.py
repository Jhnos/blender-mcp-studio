"""Job-derived process keys: brim, support and prime tower come from the job on every vendor."""

from __future__ import annotations

import json
from pathlib import Path

from src.adapters.slicing.orca_family_cli import OrcaFamilyCli
from src.adapters.slicing.slice_job import job_process_keys
from src.core.domain.model_spec import PrintTarget
from src.core.domain.slicing import SliceRequest
from src.infrastructure.printer_catalog_loader import load_printer_catalog
from tests.unit.adapters.test_orca_family_cli import _PROFILES, P2S, FakeRunner, _binary, _request

#: The keys p2s-pla-overrides.json carried until 2026-11-09; job_process_keys overwrites each.
LEGACY_JOB_KEYS = {
    "enable_support": "1",
    "support_type": "normal(auto)",
    "support_style": "snug",
    "enable_prime_tower": "0",
    "brim_width": "3",
    "brim_type": "outer_only",
}


def _keys(**over: object) -> dict[str, str]:
    target = PrintTarget(**{"printer": P2S, "material": "PLA", **over})  # type: ignore[arg-type]
    return job_process_keys(SliceRequest.from_target("/a.3mf", "/o", target, printer_id=P2S))


def test_brim_type_outer_only_when_the_job_has_a_brim() -> None:
    keys = _keys(brim_mm=3.0)
    assert (keys["brim_type"], keys["brim_width"]) == ("outer_only", "3.0")


def test_brim_type_no_brim_when_the_job_has_none() -> None:
    assert _keys(brim_mm=0.0)["brim_type"] == "no_brim"


def test_overrides_no_longer_carry_job_keys() -> None:
    overrides = json.loads((_PROFILES / "p2s-pla-overrides.json").read_text("utf-8"))
    assert set(LEGACY_JOB_KEYS).isdisjoint(overrides)


async def _merged(tmp_path: Path, overrides_dir: Path) -> dict[str, object]:
    cli = OrcaFamilyCli(
        load_printer_catalog(),
        {"bambu-studio": _binary(tmp_path), "orcaslicer": tmp_path / "no-orca"},
        overrides_dir=overrides_dir,
        runner=FakeRunner(),  # type: ignore[arg-type]
    )
    await cli.slice(_request(tmp_path))  # the P2S v78 job: PLA, defaults (support, 3 mm brim)
    return json.loads((tmp_path / "out" / "process.json").read_text("utf-8"))


async def test_p2s_v78_merged_process_unchanged_without_the_job_keys(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    current = json.loads((_PROFILES / "p2s-pla-overrides.json").read_text("utf-8"))
    (legacy / "p2s-pla-overrides.json").write_text(json.dumps({**current, **LEGACY_JOB_KEYS}))
    before = await _merged(tmp_path / "a", legacy)
    after = await _merged(tmp_path / "b", _PROFILES)
    assert after == before
