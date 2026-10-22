"""Submit-time checks on the print target: fixed order, all before any run directory or job."""

from __future__ import annotations

import pytest

from src.adapters.slicing.bundle_profiles import IncompatibleProfileError
from src.core.domain.model_spec import ModelSpecError
from src.core.domain.slicing import LayerHeightError
from src.infrastructure.printer_catalog_loader import load_printer_catalog
from tests.unit.core.test_design_fix_round1 import _real_missing_slicer
from tests.unit.core.test_design_pipeline import _payload, _rig, _run

P2S, K1C = "bambu-p2s-0.4", "creality-k1c-0.4"


def _v2(rig, **target):
    return {**_payload(rig), "spec_version": "2", "print_target": target}


async def _rejected(rig, payload) -> str:
    with pytest.raises(ModelSpecError) as info:
        await rig.pipeline.submit(payload)
    assert rig.jobs.records == {} and not rig.runs.exists()  # no job, no run directory
    return str(info.value)


async def test_submit_rejects_unknown_printer_listing_ids(tmp_path):
    rig = _rig(tmp_path)
    message = await _rejected(rig, _v2(rig, printer="x1c", material="PLA"))
    assert "'x1c'" in message
    ids = sorted(p.id for p in load_printer_catalog().printers)
    assert all(printer_id in message for printer_id in ids)  # the whole catalog, not only usable


async def test_submit_rejects_a_v1_name_in_a_v2_spec(tmp_path):
    rig = _rig(tmp_path)
    assert "'bambu-p2s'" in await _rejected(rig, _v2(rig, printer="bambu-p2s", material="PLA"))


async def test_submit_rejects_printer_with_missing_slicer(tmp_path):
    rig = _rig(tmp_path)
    _real_missing_slicer(rig, tmp_path)
    message = await _rejected(rig, _v2(rig, printer=K1C, material="PLA"))
    slicer = load_printer_catalog().slicer("orcaslicer")
    assert "needs OrcaSlicer," in message and slicer.install_hint in message
    assert str(tmp_path) not in message


async def test_unknown_printer_is_reported_before_a_missing_slicer(tmp_path):
    rig = _rig(tmp_path)
    _real_missing_slicer(rig, tmp_path)  # neither slicer is installed
    message = await _rejected(rig, _v2(rig, printer="x1c", material="PLA"))
    assert "known printers" in message and "needs" not in message


async def test_submit_rejects_unknown_material_listing_allowed(tmp_path):
    rig = _rig(tmp_path)
    message = await _rejected(rig, _v2(rig, printer=P2S, material="PETG"))
    assert message == (f"unsupported print_target.material 'PETG' for {P2S}; allowed: PLA")
    assert rig.slicing.checks == []  # the catalog check comes before the bundle check


async def test_height_outside_machine_range_rejected(tmp_path):
    rig = _rig(tmp_path)
    rig.slicing.check_error = LayerHeightError(
        "layer_height_mm 0.5 is outside bambu-p2s-0.4's range 0.08–0.28 mm"
    )
    message = await _rejected(rig, _v2(rig, printer=P2S, material="PLA", layer_height_mm=0.5))
    assert message == "layer_height_mm 0.5 is outside bambu-p2s-0.4's range 0.08–0.28 mm"
    assert rig.slicing.checks == [(P2S, 0.5, "PLA")]  # the port decides; no catalog-key gate


async def test_v1_spec_with_0_28_still_accepted(tmp_path):
    rig = _rig(tmp_path)
    payload = {**_payload(rig), "print_target": {"layer_height_mm": 0.28}}
    _, _, report = await _run(rig, payload)
    assert report.passed
    assert rig.slicing.requests[0].layer_height_mm == 0.28
    print_stage = next(s for s in report.stages if s.name.value == "print")
    assert ("process_profile", "0.20mm Standard @BBL P2S") in print_stage.metrics


async def test_submit_rejects_incompatible_material(tmp_path):
    rig = _rig(tmp_path)
    rig.slicing.check_error = IncompatibleProfileError(
        "filament profile 'Generic PLA' does not declare machine 'M' compatible"
    )
    message = await _rejected(rig, _v2(rig, printer=P2S, material="PLA"))
    assert message.startswith(f"print_target is not sliceable on {P2S}: ")
    assert "does not declare machine 'M' compatible" in message
    assert rig.slicing.checks == [(P2S, 0.2, "PLA")]


async def test_valid_v2_submit_runs_on_the_named_printer(tmp_path):
    rig = _rig(tmp_path)
    _, _, report = await _run(rig, _v2(rig, printer=P2S, material="PLA"))
    assert report.passed
    assert rig.slicing.requests[0].printer_id == P2S
    assert report.stages[0].message == ""  # nothing was defaulted


async def test_v1_spec_maps_to_legacy_printer_with_note(tmp_path):
    rig = _rig(tmp_path)
    _, _, report = await _run(rig, _payload(rig))  # v1, no print_target
    assert report.passed
    request = rig.slicing.requests[0]
    assert (request.printer_id, request.material) == (P2S, "PLA")
    assert report.stages[0].message == (
        "spec v1 legacy defaults used: printer bambu-p2s-0.4, material PLA"
    )
