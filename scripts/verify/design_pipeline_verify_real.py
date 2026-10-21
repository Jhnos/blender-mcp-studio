#!/usr/bin/env python3
"""Real-tier gate: the user's v78 deliverable through the public MCP URL, stage by stage.

Submits the contract's ModelSpec with ``run_design_pipeline``, polls ``get_job_status`` with a
heartbeat, then asserts machine evidence for import, geometry, mechanism, print and package
(``design_gate_checks``; expected numbers live in the contract JSON). A negative control submits
a copy with one STL header truncated and requires a geometry FAILED naming that file.

Absent prerequisites (deliverable directory, slicer, MCP endpoint) are FAILs with a reason, never
a silent SKIP. The deployed API must run code that has the design tools; run this after deploy.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import os
import secrets
import shutil
import sys
import time
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify import design_gate_checks as checks  # noqa: E402
from scripts.verify.mcp_verify_real import TRANSPORT_ERRORS, default_mcp_url  # noqa: E402
from src.infrastructure.narrowing import as_mapping  # noqa: E402

POLL_PAUSE_S = 10.0
NEGATIVE_DIR = "tmp"  # git-ignored, and inside the deployed API's artifact root "."


def _payload(result: Any) -> Any:
    """Structured tool output; FastMCP wraps non-object returns as ``{"result": ...}``."""
    data = getattr(result, "structured_content", None)
    if data is None:
        data = getattr(result, "data", None)
    wrapped = as_mapping(data)
    if wrapped is not None and set(wrapped) == {"result"}:
        return wrapped["result"]
    return data


async def _tool(client: Client[Any], name: str, args: Mapping[str, object] | None = None) -> Any:
    return _payload(await client.call_tool(name, dict(args or {})))


def _as_object(value: object, what: str) -> Mapping[str, object]:
    mapping = as_mapping(value)
    if mapping is None:
        raise checks.GateError(f"{what} is not a JSON object: {str(value)[:200]}")
    return mapping


async def _object(
    client: Client[Any], name: str, args: Mapping[str, object] | None = None
) -> Mapping[str, object]:
    return _as_object(await _tool(client, name, args), name)


async def _resource_bytes(client: Client[Any], run_id: str, name: str) -> bytes:
    contents = await client.read_resource(f"run://{run_id}/{name}")
    item = contents[0]
    blob = getattr(item, "blob", None)
    if blob is not None:
        return base64.b64decode(blob)
    return str(getattr(item, "text", "")).encode("utf-8")


async def _resource_json(client: Client[Any], run_id: str, name: str) -> Mapping[str, object]:
    return _as_object(json.loads(await _resource_bytes(client, run_id, name)), name)


async def _run_spec(
    client: Client[Any], spec: Mapping[str, object], label: str
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    """Submit, poll to a terminal job state, return (job, report)."""
    submitted = await _object(client, "run_design_pipeline", {"spec": dict(spec)})
    job_id, run_id = str(submitted["job_id"]), str(submitted["run_id"])
    print(f"[{label}] submitted job {job_id} run {run_id}", flush=True)
    loop = asyncio.get_running_loop()

    async def fetch(_: str) -> Mapping[str, object]:
        return await _object(client, "get_job_status", {"job_id": job_id})

    # poll_job is synchronous (unit-testable with a fake clock); drive it from a thread and
    # hop back onto the loop for each status call.
    def status(jid: str) -> Mapping[str, object]:
        return asyncio.run_coroutine_threadsafe(fetch(jid), loop).result()

    job = await asyncio.to_thread(
        checks.poll_job,
        status,
        job_id,
        budget_s=checks.poll_budget_s(),
        pause_s=POLL_PAUSE_S,
    )
    report = await _object(client, "get_run_report", {"run_id": run_id})
    return job, report


def _positive_failures(
    report: Mapping[str, object],
    manifest: Mapping[str, object],
    report_json: Mapping[str, object],
    plates: list[str] | None,
    expect: Mapping[str, object],
) -> list[str]:
    failures = checks.check_report(report, expect)
    failures += checks.check_manifest(manifest, report, expect)
    if report_json.get("stages") != report.get("stages"):
        failures.append("report.json resource disagrees with get_run_report stages")
    if plates is None:
        failures.append("print output 3MF could not be read from the run")
    else:
        failures += checks.check_plates(plates, int(expect["plates"]))  # type: ignore[call-overload]
    docs = {"report": report, "manifest": manifest, "report.json": report_json}
    failures += checks.find_path_leaks(docs, home=str(Path.home()))
    return failures


async def _positive(client: Client[Any], contract: Mapping[str, Any]) -> list[str]:
    job, report = await _run_spec(client, contract["spec"], "v78")
    print(f"[v78] job ended {job.get('status')} error={job.get('error')}", flush=True)
    run_id = str(report["run_id"])
    early = checks.check_report(report, contract["expect"])
    try:
        manifest = await _resource_json(client, run_id, "manifest.json")
        report_json = await _resource_json(client, run_id, "report.json")
        plates: list[str] | None = None
        out = checks.output_3mf(report)
        if out is not None:
            blob = await _resource_bytes(client, run_id, out)
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                plates = archive.namelist()
    except (ValueError, zipfile.BadZipFile, ToolError, McpError) as exc:
        detail = f"{type(exc).__name__}: {exc}"
        return [*early, f"evidence files unreadable from run {run_id}: {detail}"]
    return _positive_failures(report, manifest, report_json, plates, contract["expect"])


async def _negative(client: Client[Any], contract: Mapping[str, Any]) -> list[str]:
    spec = json.loads(json.dumps(contract["spec"]))
    source = spec["source"]
    keep = int(contract["negative_control"]["keep_header_bytes"])
    work = PROJECT_ROOT / NEGATIVE_DIR / f"design-gate-negative-{secrets.token_hex(4)}"
    copy_root = work / "artifact"
    try:
        original = PROJECT_ROOT / source["root_dir"]
        stls = sorted(original.glob(source["stl_glob"]))
        if not stls:
            return [f"negative control: no STL matches {source['stl_glob']} in the deliverable"]
        target = stls[0].relative_to(original)
        (copy_root / target).parent.mkdir(parents=True)
        for stl in stls:
            shutil.copy2(stl, copy_root / stl.relative_to(original))
        checks.truncate_header(copy_root / target, keep)
        source["root_dir"] = copy_root.relative_to(PROJECT_ROOT).as_posix()
        source.pop("project_3mf", None)
        spec["name"] = "negative-control-truncated-header"
        _, report = await _run_spec(client, spec, "negative")
        return checks.check_negative(report, target.as_posix())
    finally:
        shutil.rmtree(work, ignore_errors=True)


async def _session(contract: Mapping[str, Any], url: str) -> list[str]:
    failures: list[str] = []
    for attempt in (1, 2):
        try:
            async with Client(url) as client:
                rows = await _tool(client, "tool_status")
                failures += checks.check_slicer(rows or [], contract["expect"]["slicer_tool"])
                if failures:
                    return failures
                failures += await _positive(client, contract)
                failures += await _negative(client, contract)
            return failures
        except TRANSPORT_ERRORS as exc:
            if attempt == 1 and not failures:
                print(f"transport reset ({type(exc).__name__}: {exc}); retrying once", flush=True)
                continue
            return [*failures, checks.unreachable_message(url, exc)]
        except checks.GateError as exc:
            return [*failures, str(exc)]
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "contract", type=Path, help="scripts/verify/contracts/design_pipeline_*.json"
    )
    contract = json.loads(parser.parse_args().contract.read_text(encoding="utf-8"))
    failures = checks.check_deliverable(PROJECT_ROOT, contract["spec"]["source"]["root_dir"])
    if not failures:
        try:
            url = os.environ.get("BLENDER_MCP_URL") or default_mcp_url()
        except ValueError as exc:
            failures = [str(exc)]
        else:
            print(f"design pipeline gate via {url}", flush=True)
            started = time.monotonic()
            failures = asyncio.run(_session(contract, url))
            print(f"elapsed {time.monotonic() - started:.0f}s")
    print("\n=== DESIGN PIPELINE GATE ===")
    for failure in failures:
        print(f"[FAIL] {failure}")
    print("PASS" if not failures else f"{len(failures)} failure(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
