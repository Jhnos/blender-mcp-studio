"""Negative controls of the design pipeline real gate; each must fail the way its contract says.

Split from ``design_pipeline_verify_real`` (file budget). The MCP calls come in as callables so
this module needs no client of its own:

- material: the same spec with a material the printer does not offer is rejected at submit;
- plate_fit: the same spec on a printer whose bed is too small ends with print FAILED;
- negative_control: a copy with one STL header truncated ends with geometry FAILED.
"""

from __future__ import annotations

import json
import secrets
import shutil
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError

from scripts.verify import design_gate_checks as checks

NEGATIVE_DIR = "tmp"  # git-ignored, under the artifact root the deployed API reads

#: ``submit(spec)`` -> the run_design_pipeline reply; raises ToolError/McpError on rejection.
Submit = Callable[[Mapping[str, object]], Awaitable[object]]
#: ``run(spec, label)`` -> (job, report) once the job is terminal.
Run = Callable[
    [Mapping[str, object], str], Awaitable[tuple[Mapping[str, object], Mapping[str, object]]]
]


def _copy(spec: Mapping[str, object]) -> dict[str, Any]:
    copied: dict[str, Any] = json.loads(json.dumps(spec))
    return copied


async def truncated_header(run: Run, contract: Mapping[str, Any], root: Path) -> list[str]:
    spec = _copy(contract["spec"])
    source = spec["source"]
    keep = int(contract["negative_control"]["keep_header_bytes"])
    work = root / NEGATIVE_DIR / f"design-gate-negative-{secrets.token_hex(4)}"
    copy_root = work / "artifact"
    try:
        original = root / source["root_dir"]
        stls = sorted(original.glob(source["stl_glob"]))
        if not stls:
            return [f"negative control: no STL matches {source['stl_glob']} in the deliverable"]
        target = stls[0].relative_to(original)
        (copy_root / target).parent.mkdir(parents=True)
        for stl in stls:
            shutil.copy2(stl, copy_root / stl.relative_to(original))
        checks.truncate_header(copy_root / target, keep)
        source["root_dir"] = copy_root.relative_to(root).as_posix()
        source.pop("project_3mf", None)
        spec["name"] = "negative-control-truncated-header"
        _, report = await run(spec, "negative")
        return checks.check_negative(report, target.as_posix())
    finally:
        shutil.rmtree(work, ignore_errors=True)


async def unknown_material(
    submit: Submit, contract: Mapping[str, Any], listing: Mapping[str, object], printer: str
) -> list[str]:
    """The same spec with a material ``printer`` does not offer must fail at submit."""
    spec = _copy(contract["spec"])
    chosen = str(contract["negative_controls"]["material"]["material"])
    spec.setdefault("print_target", {})["material"] = chosen
    spec["name"] = "negative-control-unknown-material"
    try:
        submitted = await submit(spec)
    except (ToolError, McpError) as exc:
        error: str | None = str(exc)
    else:
        error = None
        print(f"[material] unexpectedly accepted: {str(submitted)[:200]}", flush=True)
    allowed = checks.listed_materials(listing, printer)
    return checks.check_material_rejection(error, chosen, allowed)


async def plate_too_small(run: Run, contract: Mapping[str, Any]) -> list[str]:
    """The same spec on a printer whose bed is too small must end with print FAILED."""
    control = contract["negative_controls"]["plate_fit"]
    spec = _copy(contract["spec"])
    spec["print_target"]["printer"] = control["printer"]
    spec["name"] = "negative-control-plate-too-big"
    _, report = await run(spec, "plate-fit")
    return checks.check_plate_fit_negative(report, control["message_contains"])


async def run_negatives(
    submit: Submit,
    run: Run,
    contract: Mapping[str, Any],
    root: Path,
    listing: Mapping[str, object],
    printer: str,
) -> list[str]:
    """Every negative control the contract declares, in a fixed order."""
    controls = contract.get("negative_controls", {})
    failures: list[str] = []
    if "material" in controls:
        failures += await unknown_material(submit, contract, listing, printer)
    if "plate_fit" in controls:
        failures += await plate_too_small(run, contract)
    if "negative_control" in contract:
        failures += await truncated_header(run, contract, root)
    return failures
