"""list_printers and the printer-required slice_for_print over a real DesignPipeline, fake ports."""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import Client

from src.core.domain.model_spec import JOB_DEFAULTS
from src.core.domain.slicing import ToolAvailability
from src.core.use_cases.design_stages import MAX_SKIPPED_EVIDENCE, MECHANISM_NOT_EVALUATED
from tests.fakes.design_ports import FakeSlicing
from tests.unit.adapters.test_mcp_design_tools import _server, _strings, _text
from tests.unit.core.test_design_pipeline import _rig

P2S, K1C = "bambu-p2s-0.4", "creality-k1c-0.4"
ENTRY_KEYS = {
    "id",
    "vendor",
    "model",
    "nozzle_mm",
    "materials",
    "layer_height_mm",
    "bed_mm",
    "max_height_mm",
    "bed_type",
    "slicer",
}


def _installed(rig, *printer_ids):
    rig.slicing = FakeSlicing(rig.lease, printer_ids=printer_ids)
    rig.pipeline._slicing = rig.slicing
    return rig


async def _list(rig):
    async with Client(_server(rig)) as client:
        return (await client.call_tool("list_printers", {})).structured_content


async def test_list_printers_only_installed(tmp_path):
    rig = _installed(_rig(tmp_path), P2S, K1C)
    data = await _list(rig)
    assert [p["id"] for p in data["printers"]] == [P2S, K1C]
    assert all(set(p) == ENTRY_KEYS for p in data["printers"])
    assert {u["id"] for u in data["unavailable"]}.isdisjoint({P2S, K1C})
    only_p2s = await _list(_installed(_rig(tmp_path / "again"), P2S))
    assert [p["id"] for p in only_p2s["printers"]] == [P2S]
    assert "creality-k1-0.4" in {u["id"] for u in only_p2s["unavailable"]}


async def test_list_printers_has_no_paths(tmp_path):
    rig = _installed(_rig(tmp_path), P2S, K1C)
    data = await _list(rig)
    blob = json.dumps(data)
    assert not [s for s in _strings(data) if s.startswith("/") or str(Path.home()) in s]
    assert str(tmp_path) not in blob and "/x/bs" not in blob
    assert "path" not in {k for p in data["printers"] for k in p}


async def test_list_printers_reports_bed_and_height(tmp_path):
    rig = _installed(_rig(tmp_path), P2S, K1C)
    by_id = {p["id"]: p for p in (await _list(rig))["printers"]}
    p2s, k1c = by_id[P2S], by_id[K1C]
    assert p2s["bed_mm"] == [256.0, 256.0] and p2s["max_height_mm"] == 256.0
    assert k1c["bed_mm"] == [220.0, 220.0] and k1c["max_height_mm"] == 250.0
    assert p2s["layer_height_mm"] == {"min": 0.08, "max": 0.28}
    # id is the catalog slicer id that tool_status and the package manifest use
    assert p2s["slicer"] == {"id": "bambu-studio", "name": "Bambu Studio", "version": "02.06.00.51"}
    assert k1c["slicer"] == {"id": "orcaslicer", "name": "OrcaSlicer", "version": "2.4.2"}
    assert p2s["materials"] == ["PLA"] and p2s["nozzle_mm"] == 0.4
    assert p2s["vendor"] and p2s["model"] and p2s["bed_type"]


async def test_list_printers_exact_heights_when_no_range_declared(tmp_path):
    rig = _installed(_rig(tmp_path), "creality-k1-0.4")  # the fake declares no range for it
    (entry,) = (await _list(rig))["printers"]
    assert entry["layer_height_mm"] == {"exact": [0.2]}
    assert entry["bed_mm"] is None and entry["max_height_mm"] is None  # fake knows no bed


async def test_list_printers_names_unavailable_with_hint(tmp_path):
    rig = _installed(_rig(tmp_path), P2S)

    async def tools():
        return (
            ToolAvailability("bambu-studio", True, "/x/bs", "02.06.00.51", ""),
            ToolAvailability("orcaslicer", False, None, None, "Install OrcaSlicer from the site"),
        )

    rig.slicing.availability = tools
    data = await _list(rig)
    missing = {u["id"]: u for u in data["unavailable"]}
    assert set(missing) >= {K1C, "creality-k2-plus-0.4"} and P2S not in missing
    assert set(missing[K1C]) == {"id", "reason", "install_hint"}
    assert "OrcaSlicer" in missing[K1C]["reason"] and "not" in missing[K1C]["reason"]
    assert missing[K1C]["install_hint"] == "Install OrcaSlicer from the site"


async def test_slice_for_print_requires_printer(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        tool = next(t for t in await client.list_tools() if t.name == "slice_for_print")
        res = await client.call_tool(
            "slice_for_print",
            {"input_3mf": "artifact/p.3mf", "material": "PLA"},
            raise_on_error=False,
        )
    assert "printer" in tool.inputSchema["required"]
    assert "default" not in tool.inputSchema["properties"]["printer"]
    assert res.is_error and rig.slicing.requests == []


async def test_slice_for_print_requires_material(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        tool = next(t for t in await client.list_tools() if t.name == "slice_for_print")
        res = await client.call_tool(
            "slice_for_print",
            {"input_3mf": "artifact/p.3mf", "printer": P2S},
            raise_on_error=False,
        )
        bad = await client.call_tool(
            "slice_for_print",
            {"input_3mf": "artifact/p.3mf", "printer": P2S, "material": "UNOBTAINIUM"},
            raise_on_error=False,
        )
    assert "material" in tool.inputSchema["required"]
    assert "default" not in tool.inputSchema["properties"]["material"]
    assert res.is_error and bad.is_error and "UNOBTAINIUM" in _text(bad)
    assert rig.slicing.requests == [] and list(rig.runs.glob("*")) == []


async def test_slice_for_print_checks_target_before_any_run_dir(tmp_path):
    rig = _installed(_rig(tmp_path), P2S)
    hint = "Install OrcaSlicer from the site"

    async def tools():
        return (ToolAvailability("orcaslicer", False, None, None, hint),)

    rig.slicing.availability = tools
    async with Client(_server(rig)) as client:
        res = await client.call_tool(
            "slice_for_print",
            {"input_3mf": "artifact/p.3mf", "printer": K1C, "material": "PLA"},
            raise_on_error=False,
        )
    assert res.is_error and K1C in _text(res)
    assert hint in _text(res)  # the user is told how to get the missing slicer
    assert rig.slicing.requests == []
    assert not rig.runs.exists() or not list(rig.runs.iterdir())


async def test_slice_for_print_passes_material_and_layer_height(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        await client.call_tool(
            "slice_for_print",
            {"input_3mf": "artifact/p.3mf", "printer": P2S, "material": "PLA"},
        )
        await client.call_tool(
            "slice_for_print",
            {
                "input_3mf": "artifact/p.3mf",
                "printer": P2S,
                "material": "PLA",
                "layer_height_mm": 0.12,
            },
        )
    first, second = rig.slicing.requests
    assert (first.material, first.layer_height_mm) == ("PLA", 0.2)
    assert second.layer_height_mm == 0.12
    assert [c[1] for c in rig.slicing.checks] == [0.2, 0.12]


async def test_tool_descriptions_point_to_list_printers(tmp_path):
    rig = _rig(tmp_path)
    async with Client(_server(rig)) as client:
        tools = {t.name: t.description or "" for t in await client.list_tools()}
    for name in ("run_design_pipeline", "describe_model_spec", "slice_for_print"):
        assert "list_printers" in tools[name], name
        assert "bed_mm" in tools[name], name
    for name in ("list_printers", "run_design_pipeline", "describe_model_spec", "slice_for_print"):
        assert len(tools[name]) <= 700, (name, len(tools[name]))
    for field in ("bed_mm", "max_height_mm", "layer_height_mm", "materials", "unavailable"):
        assert field in tools["list_printers"], field
    run = tools["run_design_pipeline"]
    assert MECHANISM_NOT_EVALUATED in run
    assert "import.json" in run and f"at most {MAX_SKIPPED_EVIDENCE}" in run
    default = f"layer_height_mm defaults to {JOB_DEFAULTS.layer_height_mm:g}"
    assert default in " ".join(tools["slice_for_print"].split())
