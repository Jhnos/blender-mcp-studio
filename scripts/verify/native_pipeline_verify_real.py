"""Public native job → same-part STL → single-plate slice, with independent state/byte oracles.

This extends the existing design gate, never supplies Python or an alternate native path,
and never retries a submitted mutation. It is a software delivery gate, not fit/load proof.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sqlite3
import sys
import zipfile
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify import design_gate_checks as checks  # noqa: E402
from scripts.verify import native_pipeline_checks as native  # noqa: E402
from scripts.verify.design_pipeline_verify_real import (  # noqa: E402
    _object,
    _positive_failures,
    _resource_bytes,
    _resource_json,
    _selected_contract,
    run_job,
)
from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle  # noqa: E402
from scripts.verify.mcp_verify_real import ORACLE_ADDRESS, default_mcp_url  # noqa: E402
from scripts.verify.verification_mcp_verify_real import snapshot  # noqa: E402
from src.adapters.artifacts.plate_project import PlateProject  # noqa: E402
from src.core.domain.native_revision import SCREEN_CLAMP_RECIPE, NativeRevisionRequest  # noqa: E402
from src.infrastructure.narrowing import as_sequence  # noqa: E402
from src.infrastructure.tools_config import ToolsConfig, load_tools_config  # noqa: E402
from src.verification.artifact_files import binary_stl_surface  # noqa: E402


async def require_native_tool(client: Client[Any]) -> None:
    for tool in await client.list_tools():
        if tool.name == "run_design_pipeline":
            properties = native.object_value(tool.inputSchema.get("properties"))
            if "revision" in properties:
                return
    raise checks.GateError(
        "loaded run_design_pipeline does not expose revision; no import fallback"
    )


def job_ids(database: Path) -> set[str]:
    """Readonly independent oracle: invalid intent must not create an undisclosed job."""
    if not database.exists():
        return set()
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        return {str(row[0]) for row in connection.execute("SELECT job_id FROM jobs")}


async def rejection_controls(client: Client[Any], tools: ToolsConfig) -> None:
    before = await asyncio.to_thread(job_ids, tools.design_jobs_db)
    for request in (
        {"recipe_id": "unknown"},
        {"recipe_id": SCREEN_CLAMP_RECIPE, "target_angle_deg": 12},
        {"recipe_id": SCREEN_CLAMP_RECIPE, "code": "pass"},
        {"recipe_id": SCREEN_CLAMP_RECIPE, "output_path": "alternate.blend"},
    ):
        result = await client.call_tool(
            "run_design_pipeline", {"revision": request}, raise_on_error=False
        )
        if not result.is_error:
            raise checks.GateError("native invalid intent was accepted")
    if await asyncio.to_thread(job_ids, tools.design_jobs_db) != before:
        raise checks.GateError("job catalog changed during rejected native intents")


async def private_controls(
    client: Client[Any], run_id: str, selected: Mapping[str, object]
) -> list[str]:
    source_native = native.object_value(selected["native"])
    failures = []
    for name in (
        "native-execution/pending.json",
        "native-execution/terminal.json",
        "native-source/" + str(source_native["path"]),
    ):
        try:
            await _resource_bytes(client, run_id, name)
        except (ToolError, McpError):
            continue
        failures.append("private native job file is publicly readable: " + name)
    return failures


async def rest_readback(
    url: str, run_id: str, product: Mapping[str, object], saved_report: Mapping[str, object]
) -> list[str]:
    if not url.endswith("/mcp"):
        raise checks.GateError("public native gate requires the canonical MCP endpoint")
    prefix = url.removesuffix("/mcp") + "/api/design/runs/" + run_id
    async with httpx.AsyncClient(timeout=30) as client:
        for name, expected in (
            ("native-product/product.json", product),
            ("report.json", saved_report),
        ):
            response = await client.get(prefix + "/files/" + quote(name, safe="/"))
            response.raise_for_status()
            if response.json() != expected:
                return ["REST and MCP disagree for the same native job: " + name]
        response = await client.get(prefix + "/files/native-execution/terminal.json")
        if response.status_code not in (400, 404):
            return ["REST does not reject private native execution evidence"]
    return []


async def positive(
    client: Client[Any], resolved: Mapping[str, Any], tools: ToolsConfig, url: str
) -> tuple[list[str], dict[str, object]]:
    request = asdict(NativeRevisionRequest(SCREEN_CLAMP_RECIPE, 30))
    job, report = await run_job(client, None, "native", revision=request)
    run_id = str(report["run_id"])
    proof: dict[str, object] = {"job": dict(job), "report": dict(report), "request": request}
    failures = checks.check_report(report, resolved["expect"])
    if job.get("status") != "done" or failures:
        return [*failures, "native job did not complete all qualification stages"], proof
    docs = {
        name: await _resource_json(client, run_id, name)
        for name in (
            "spec.json",
            "native-request.json",
            "report.json",
            "import.json",
            "geometry.json",
            "manifest.json",
            "native-product/product.json",
            "print/extrusion.json",
        )
    }
    proof["documents"] = docs
    product = docs["native-product/product.json"]
    selected = native.object_value(resolved["native"])
    failures += native.check_product(product, selected, run_id)
    if docs["spec.json"] != resolved["spec"] or docs["native-request.json"] != request:
        failures.append("native job changed its captured spec or request")
    failures += checks.find_path_leaks(docs, home=str(Path.home()))
    if failures:
        return failures, proof
    payloads = {
        name: await _resource_bytes(client, run_id, name) for name in native.artifacts(product)
    }
    failures += native.check_downloads(product, payloads)
    if failures:
        return failures, proof
    output = checks.output_3mf(report)
    if output is None:
        return ["native print stage did not publish a sliced 3MF"], proof
    sliced = await _resource_bytes(client, run_id, output)
    stls = native.object_value(product["stls"])
    parts = native.rows(stls["parts"])
    owners = tuple(Path(str(part["path"])).stem for part in parts)
    failures += native.check_extrusion_receipt(docs["print/extrusion.json"], sliced, owners)
    with zipfile.ZipFile(io.BytesIO(sliced)) as archive:
        members = archive.namelist()
    failures += _positive_failures(
        report,
        docs["manifest.json"],
        docs["report.json"],
        docs["import.json"],
        members,
        resolved["expect"],
    )
    plate = PlateProject(
        payloads["native-product/project.3mf"], owners, max_bytes=tools.import_limits.max_3mf_bytes
    )
    proof["same_frame_errors_mm"] = plate.require_same_layout(sliced)
    failures += native.check_slice_inventory(sliced, owners)
    changed_paths = as_sequence(stls.get("changed_paths"))
    if changed_paths is None:
        raise checks.GateError("native changed paths are malformed")
    proof["changed_surface_bindings"] = plate.bind_originals(
        {
            Path(str(path)).stem: binary_stl_surface(payloads["native-product/parts/" + str(path)])
            for path in changed_paths
        }
    )
    for row in native.rows(docs["manifest.json"].get("files")):
        name = str(row.get("path"))
        if name.startswith(("native-source/", "native-execution/")):
            failures.append("manifest publishes private native input or execution evidence")
    failures += await private_controls(client, run_id, selected)
    failures += await rest_readback(url, run_id, product, docs["report.json"])
    return failures, proof


async def verify(url: str, tools: ToolsConfig) -> dict[str, object]:
    oracle = BlenderSocketOracle(*ORACLE_ADDRESS, timeout=60)
    before = await asyncio.to_thread(snapshot, oracle)
    proof: dict[str, object] = {
        "scope": "public native pipeline and same-part single-plate software qualification; not assembly, support removal or load acceptance"
    }
    try:
        async with Client(url) as client:
            await require_native_tool(client)
            contract = json.loads(
                (ROOT / "scripts/verify/contracts/design_pipeline_current.json").read_text()
            )
            resolved = await _selected_contract(client, contract)
            spec = native.object_value(resolved["spec"])
            source = native.object_value(spec["source"])
            root = tools.artifact_roots[0]
            failures = checks.check_deliverable(root, str(source["root_dir"]))
            failures += checks.check_native_source(root, spec, resolved["native"])
            if failures:
                raise checks.GateError("; ".join(failures))
            await rejection_controls(client, tools)
            failures, details = await positive(client, resolved, tools, url)
            proof.update(details)
            after_selection = await _object(client, "list_artifacts")
            if (
                after_selection.get("default_spec") != spec
                or after_selection.get("default_native") != resolved["native"]
            ):
                failures.append("native job changed the current catalog selection or source")
            failures += checks.check_native_source(
                root, spec, after_selection.get("default_native")
            )
            proof["failures"] = failures
            proof["passed"] = not failures
    finally:
        restored = await asyncio.to_thread(snapshot, oracle) == before
        proof["independent_scene_restored"] = restored
        if not restored:
            raise checks.GateError("native public job changed the original scene")
    return proof


def main() -> int:
    output = ROOT / "tmp/native-design-gate"
    output.mkdir(parents=True, exist_ok=True)
    try:
        proof = asyncio.run(
            verify(os.environ.get("BLENDER_MCP_URL") or default_mcp_url(), load_tools_config())
        )
    except (
        ValueError,
        KeyError,
        OSError,
        checks.GateError,
        ToolError,
        McpError,
        httpx.HTTPError,
    ) as exc:
        print("NATIVE PUBLIC GATE FAILED: " + str(exc), flush=True)
        return 1
    job = native.object_value(proof["job"])
    path = output / (str(job["run_id"]) + ".json")
    with path.open("x") as handle:
        json.dump(proof, handle, ensure_ascii=False, indent=2)
    print(
        json.dumps({"passed": proof["passed"], "job": job, "failures": proof["failures"]}),
        flush=True,
    )
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
