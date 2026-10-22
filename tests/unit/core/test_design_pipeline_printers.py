"""The pipeline slices on the printer the spec names and records the slicer that actually ran."""

from __future__ import annotations

import pytest

from src.core.domain.model_spec import ModelSpecError
from src.core.domain.packaging import ToolUse
from src.core.use_cases import print_targets
from src.infrastructure.printer_catalog_loader import load_printer_catalog
from tests.fakes.design_ports import FakeSlicing
from tests.unit.core.test_design_pipeline import _payload, _rig, _run

P2S, K1C = "bambu-p2s-0.4", "creality-k1c-0.4"


def _two_printer_rig(tmp_path):
    rig = _rig(tmp_path)
    rig.slicing = FakeSlicing(rig.lease, printer_ids=(P2S, K1C))
    rig.pipeline._slicing = rig.slicing
    return rig


async def test_creality_run_records_orcaslicer_in_the_manifest(tmp_path):
    rig = _two_printer_rig(tmp_path)
    payload = {**_payload(rig), "print_target": {"printer": K1C}}
    _, status, report = await _run(rig, payload)
    assert report.passed, report
    (request,) = rig.slicing.requests
    assert request.printer_id == K1C
    (call,) = rig.packaging.calls
    assert call[4] == (ToolUse("orcaslicer", "2.4.2", "AGPL-3.0-only", "subprocess"),)


async def test_v1_printer_name_slices_on_the_p2s_and_records_bambu_studio(tmp_path):
    rig = _two_printer_rig(tmp_path)
    _, _, report = await _run(rig, _payload(rig))  # print_target omitted: v1 "bambu-p2s"
    assert report.passed
    (request,) = rig.slicing.requests
    assert (request.printer, request.printer_id) == ("bambu-p2s", P2S)
    (call,) = rig.packaging.calls
    assert call[4] == (ToolUse("bambu-studio", "02.06.00.51", "AGPL-3.0-only", "subprocess"),)


async def test_submit_rejects_a_printer_whose_slicer_is_not_usable(tmp_path):
    rig = _rig(tmp_path)  # only the P2S is usable
    payload = {**_payload(rig), "print_target": {"printer": K1C}}
    with pytest.raises(ModelSpecError, match=K1C):
        await rig.pipeline.submit(payload)
    assert rig.jobs.records == {}


def test_spec_names_list_each_usable_printer_once() -> None:
    catalog = load_printer_catalog()
    printers = (catalog.printer(P2S), catalog.printer(K1C))
    assert print_targets.spec_printer_names(printers) == ("bambu-p2s", K1C)
    assert print_targets.printer_id_for("bambu-p2s") == P2S
    assert print_targets.printer_id_for(K1C) == K1C


async def test_describe_spec_lists_usable_printers(tmp_path):
    rig = _two_printer_rig(tmp_path)
    target = rig.pipeline.describe_spec()["schema"]["properties"]["print_target"]["properties"]
    assert target["printer"]["enum"] == ["bambu-p2s", K1C]
    assert target["material"]["enum"] == ["PLA"]


def test_slice_timeout_covers_every_catalog_slicer_even_when_none_is_installed(tmp_path):
    from src.adapters.slicing.orca_family_cli import SLICE_TIMEOUT_S
    from tests.unit.core.test_design_fix_round1 import missing_slicers

    rig = _rig(tmp_path)
    rig.pipeline._slicing = missing_slicers(tmp_path)  # printers() is empty
    assert rig.pipeline.slice_timeout_s == max(SLICE_TIMEOUT_S.values()) == 855.0


async def test_mcp_slice_tool_timeout_does_not_collapse_without_slicers(tmp_path):
    from tests.unit.adapters.test_mcp_design_tools import _server
    from tests.unit.core.test_design_fix_round1 import missing_slicers

    rig = _rig(tmp_path)
    rig.pipeline._slicing = missing_slicers(tmp_path)
    tool = await _server(rig).get_tool("slice_for_print")
    assert tool.timeout == 855.0 + 30
