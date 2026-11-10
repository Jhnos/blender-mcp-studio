#!/usr/bin/env python3
"""Real-tier gate: the selected user deliverable through the public MCP URL, stage by stage.

Submits the contract's ModelSpec with ``run_design_pipeline`` (a ``selection: current`` contract
submits no spec, so the service runs its own selection), polls ``get_job_status`` with a
heartbeat, then asserts machine evidence for import, geometry, mechanism, print and package
(``design_gate_checks``; current part counts come from the verified source). Every contract
names its printer: in its spec, or for a current selection in ``print_target``, which the
selection must resolve to. Precondition: ``list_printers`` must list that printer as usable,
else FAIL with the unavailable reason and install hint. Negative controls
(``design_gate_negatives``, data in the contract): an unknown material is rejected at submit;
a printer whose bed is too small ends with print FAILED naming the fit; a copy with one STL
header truncated requires a geometry FAILED naming that file.

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
from scripts.verify import design_gate_negatives as negatives  # noqa: E402
from scripts.verify.lab_station_delivery_checks import check_delivery  # noqa: E402
from scripts.verify.mcp_verify_real import TRANSPORT_ERRORS, default_mcp_url  # noqa: E402
from src.core.domain.model_spec import ModelSpecError  # noqa: E402
from src.infrastructure.config_loader import load_selected_model_spec  # noqa: E402
from src.infrastructure.narrowing import as_mapping, as_sequence  # noqa: E402
from src.infrastructure.tools_config import load_tools_config  # noqa: E402


def job_budget_s(spec: Mapping[str, object] | None = None, *, native: bool = False) -> float:
    """Poll budget for one job; ``spec=None`` is a job the service resolves itself."""
    from src.adapters.generation.native_runner import (
        NATIVE_COMMAND_TIMEOUT_S,
        NATIVE_COMPLETION_TIMEOUT_S,
    )

    return checks.poll_budget_s(spec) + (
        NATIVE_COMMAND_TIMEOUT_S + NATIVE_COMPLETION_TIMEOUT_S if native else 0
    )


POLL_PAUSE_S = 10.0


def artifact_root(override: Path | None) -> Path:
    """The root the spec's root_dir is relative to: config/tools.yaml artifact_roots[0]."""
    return override if override is not None else load_tools_config().artifact_roots[0]


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


async def run_job(
    client: Client[Any],
    spec: Mapping[str, object] | None,
    label: str,
    *,
    revision: Mapping[str, object] | None = None,
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    """Submit, poll to a terminal job state, return (job, report)."""
    if revision is not None and spec is not None:
        raise checks.GateError("native revision cannot supply an alternate spec")
    arguments = (
        {"revision": dict(revision)}
        if revision is not None
        else ({} if spec is None else {"spec": dict(spec)})
    )
    submitted = await _object(client, "run_design_pipeline", arguments)
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
        budget_s=job_budget_s(spec, native=revision is not None),
        pause_s=POLL_PAUSE_S,
    )
    report = await _object(client, "get_run_report", {"run_id": run_id})
    return job, report


def _positive_failures(
    report: Mapping[str, object],
    manifest: Mapping[str, object],
    report_json: Mapping[str, object],
    import_json: Mapping[str, object],
    plates: list[str] | None,
    expect: Mapping[str, object],
) -> list[str]:
    failures = checks.check_report(report, expect)
    failures += checks.check_manifest(manifest, report, expect)
    failures += checks.check_import_json(import_json, expect)
    if report_json.get("stages") != report.get("stages"):
        failures.append("report.json resource disagrees with get_run_report stages")
    if plates is None:
        failures.append("print output 3MF could not be read from the run")
    else:
        failures += checks.check_plates(plates, int(expect["plates"]))  # type: ignore[call-overload]
    docs = {
        "report": report,
        "manifest": manifest,
        "report.json": report_json,
        "import.json": import_json,
    }
    failures += checks.find_path_leaks(docs, home=str(Path.home()))
    return failures


async def _positive(client: Client[Any], contract: Mapping[str, Any]) -> list[str]:
    supplied = None if contract.get("selection") == "current" else contract["spec"]
    job, report = await run_job(client, supplied, str(contract["spec"]["name"]))
    print(f"[selected] job ended {job.get('status')} error={job.get('error')}", flush=True)
    run_id = str(report["run_id"])
    early = checks.check_report(report, contract["expect"])
    try:
        saved_spec = await _resource_json(client, run_id, "spec.json")
        manifest = await _resource_json(client, run_id, "manifest.json")
        report_json = await _resource_json(client, run_id, "report.json")
        import_json = await _resource_json(client, run_id, "import.json")
        plates: list[str] | None = None
        out = checks.output_3mf(report)
        if out is not None:
            blob = await _resource_bytes(client, run_id, out)
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                plates = archive.namelist()
    except (ValueError, zipfile.BadZipFile, ToolError, McpError) as exc:
        detail = f"{type(exc).__name__}: {exc}"
        return [*early, f"evidence files unreadable from run {run_id}: {detail}"]
    failures = _positive_failures(
        report, manifest, report_json, import_json, plates, contract["expect"]
    )
    if contract.get("selection") == "current":
        failures += checks.check_import_source(
            import_json, _as_object(contract.get("native"), "verified native provenance")
        )
    if saved_spec != contract["spec"] or report.get("spec_name") != contract["spec"]["name"]:
        failures.append("run spec.json disagrees with the selected ModelSpec")
    return failures


async def _selected_contract(client: Client[Any], contract: Mapping[str, Any]) -> Mapping[str, Any]:
    """Resolve a live selection at the service, not in a client-specific copy."""
    if "selection" not in contract:
        return contract  # Deliberately supplied historical/custom contract.
    if contract["selection"] != "current" or "spec" in contract:
        raise checks.GateError("selection contract must request current without an embedded spec")
    catalog = await _object(client, "list_artifacts")
    described = await _object(client, "describe_model_spec")
    if catalog.get("default_available") is not True:
        raise checks.GateError("selected delivery is unavailable; no historical fallback")
    spec = _as_object(catalog.get("default_spec"), "default_spec")
    if spec != described.get("example"):
        raise checks.GateError("selected delivery disagrees between discovery and schema example")
    print(f"selected delivery: {spec.get('name')}", flush=True)
    return {**contract, "spec": spec, "native": catalog.get("default_native")}


def _verified_delivery(root: Path, contract: Mapping[str, Any]) -> Mapping[str, Any]:
    """Use one independently verified source for both current design gates."""
    spec = _as_object(contract["spec"], "spec")
    current = contract.get("selection") == "current"
    if current:
        try:
            declared = load_selected_model_spec(root)
        except ModelSpecError as exc:
            raise checks.GateError(f"cannot read the local current model: {exc}") from exc
        if declared != spec:
            raise checks.GateError("public selection disagrees with the local current model")
    source = _as_object(spec.get("source"), "source")
    failures = checks.check_deliverable(root, str(source["root_dir"]))
    native = contract.get("native")
    if current:
        failures += checks.check_native_source(root, spec, native)
    if current and "print_target" in contract:
        failures += checks.check_selected_target(spec, contract["print_target"])
    if failures:
        raise checks.GateError("; ".join(failures))
    if not current:
        return contract
    if contract.get("verify_delivery_evidence") is True:
        failures = check_delivery(root, native)
        if failures:
            raise checks.GateError("; ".join(failures))
    expect = _as_object(contract["expect"], "expect")
    if {"stl_count", "geometry_checked"} & expect.keys():
        raise checks.GateError("current contract must derive STL counts from verified source")
    parts = as_sequence(_as_object(native, "verified native provenance").get("parts"))
    if not parts:
        raise checks.GateError("verified native source has no parts")
    return {
        **contract,
        "expect": {**expect, "stl_count": len(parts), "geometry_checked": len(parts)},
    }


def _contract_printer(contract: Mapping[str, Any]) -> str:
    """The printer a resolved contract names; a gate never picks one."""
    named = contract.get("print_target") or _as_object(contract["spec"], "spec").get("print_target")
    printer = (as_mapping(named) or {}).get("printer")
    if not isinstance(printer, str) or not printer:
        raise checks.GateError("contract names no print_target.printer; a gate never picks one")
    return printer


async def _session(contract: Mapping[str, Any], url: str, root: Path) -> list[str]:
    failures: list[str] = []
    submission_started = False
    for attempt in (1, 2):
        try:
            async with Client(url) as client:
                resolved = await _selected_contract(client, contract)
                resolved = _verified_delivery(root, resolved)
                rows = await _tool(client, "tool_status")
                failures += checks.check_slicer(rows or [], contract["expect"]["slicer_tool"])
                listing = await _object(client, "list_printers")
                printer = _contract_printer(resolved)
                failures += checks.check_printer_listed(listing, printer)
                if failures:
                    return failures
                submission_started = True
                failures += await _positive(client, resolved)
                failures += await negatives.run_negatives(
                    lambda spec: _tool(client, "run_design_pipeline", {"spec": spec}),
                    lambda spec, label: run_job(client, spec, label),
                    resolved,
                    root,
                    listing,
                    printer,
                )
            return failures
        except TRANSPORT_ERRORS as exc:
            if attempt == 1 and not failures and not submission_started:
                print(f"transport reset ({type(exc).__name__}: {exc}); retrying once", flush=True)
                continue
            return [*failures, checks.unreachable_message(url, exc)]
        except checks.GateError as exc:
            return [*failures, str(exc)]
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "contract",
        type=Path,
        nargs="?",
        default=PROJECT_ROOT / "scripts/verify/contracts/design_pipeline_current.json",
        help="contract (default: current selected delivery)",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="directory root_dir is relative to (default: config/tools.yaml artifact_roots[0])",
    )
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    root = artifact_root(args.artifact_root)
    failures: list[str] = []
    if not failures:
        try:
            url = os.environ.get("BLENDER_MCP_URL") or default_mcp_url()
        except ValueError as exc:
            failures = [str(exc)]
        else:
            print(f"design pipeline gate via {url}", flush=True)
            started = time.monotonic()
            failures = asyncio.run(_session(contract, url, root))
            print(f"elapsed {time.monotonic() - started:.0f}s")
    print("\n=== DESIGN PIPELINE GATE ===")
    for failure in failures:
        print(f"[FAIL] {failure}")
    print("PASS" if not failures else f"{len(failures)} failure(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
