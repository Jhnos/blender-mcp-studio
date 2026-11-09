"""Pure verdict rules for the design pipeline real gate (no network, no files but the ones named).

Every function returns a list of readable failure strings (empty = pass) so the gate can print
all of them at once instead of stopping at the first. Invariants come from the contract JSON.
For the current model, part counts come from its independently verified source.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from pathlib import Path

from scripts.verify.native_source_checks import (  # explicit re-exports (file budget split)
    check_native_source as check_native_source,
)
from scripts.verify.native_source_checks import (
    check_selected_target as check_selected_target,
)
from src.adapters.slicing.orca_family_cli import SLICE_TIMEOUT_S, port_deadline_s
from src.core.domain.model_spec import ModelSpecError, parse_print_target
from src.infrastructure.narrowing import as_mapping, as_sequence
from src.infrastructure.printer_catalog_loader import load_printer_catalog

#: Slicing is the long pole; the other four stages took seconds on the same host (the v78
#: integrity check measured 1.9 s), so 300 s covers import, geometry, packaging and queueing.
POLL_MARGIN_S = 300.0
STAGE_ORDER = ("import", "geometry", "mechanism", "print", "package")
TERMINAL_JOB_STATES = frozenset({"done", "failed", "cancelled"})
#: A leaked host path starts with one of these; the home directory is added at call time.
PATH_MARKERS = ("/Users/", "/private/", "/var/folders", "/home/")
_PLATE_GCODE = re.compile(r"^Metadata/plate_\d+\.gcode$")


class GateError(RuntimeError):
    """A gate precondition or budget failed; the message is the whole explanation."""


def poll_budget_s(spec: Mapping[str, object] | None = None) -> float:
    """The slice deadline of the slicer the contract spec's printer uses, plus the margin.

    A contract spec must name its printer. The parser reads the target (a spec-v1 name becomes
    its catalog id), so a Creality contract gets the OrcaSlicer budget and a P2S contract
    Bambu Studio's. ``None`` is a job whose spec the service resolves itself (a native revision
    of the current selection): the gate names no printer, so it waits for the slowest slicer.
    """
    catalog = load_printer_catalog()

    def deadline(slicer_id: str) -> float:  # the adapter's port deadline (inspection included)
        return port_deadline_s(catalog.slicer(slicer_id), SLICE_TIMEOUT_S[slicer_id])

    if spec is None:
        return max(deadline(s.id) for s in catalog.slicers) + POLL_MARGIN_S
    target = as_mapping(spec.get("print_target")) or {}
    if "printer" not in target:
        raise GateError("contract spec has no print_target.printer; a gate never picks one")
    try:
        printer = parse_print_target(spec).printer
    except ModelSpecError as exc:
        raise GateError(f"contract spec print_target: {exc}") from exc
    return deadline(catalog.printer(printer).slicer) + POLL_MARGIN_S


def _items(value: object) -> list[object]:
    return list(as_sequence(value) or ())


def _rows(value: object) -> list[Mapping[str, object]]:
    """The mapping elements of a JSON array; anything else in it is ignored."""
    return [row for row in map(as_mapping, _items(value)) if row is not None]


def _stage(report: Mapping[str, object], name: str) -> Mapping[str, object] | None:
    return next((s for s in _rows(report.get("stages")) if s.get("name") == name), None)


def _metrics(stage: Mapping[str, object]) -> dict[str, str]:
    pairs = [_items(p) for p in _items(stage.get("metrics"))]
    return {str(p[0]): str(p[1]) for p in pairs if len(p) == 2}


def _evidence(stage: Mapping[str, object]) -> list[str]:
    return [str(e) for e in _items(stage.get("evidence"))]


def _expect_metric(
    stage_name: str, stage: Mapping[str, object], key: str, want: object
) -> list[str]:
    got = _metrics(stage).get(key)
    if got == str(want):
        return []
    return [f"{stage_name} metric {key}: expected {want}, got {got if got is not None else 'none'}"]


def _expect_outcome(name: str, stage: Mapping[str, object], want: str) -> list[str]:
    outcome = stage.get("outcome")
    if outcome == want:
        return []
    message = stage.get("message") or ""
    return [f"{name} stage must be {want}, was {outcome}: {message}".rstrip(": ")]


def output_3mf(report: Mapping[str, object]) -> str | None:
    """The sliced 3MF the print stage recorded (a run-relative path), or None."""
    stage = _stage(report, "print")
    found = [e for e in (_evidence(stage) if stage else []) if e.lower().endswith(".3mf")]
    return found[0] if found else None


def check_report(report: Mapping[str, object], expect: Mapping[str, object]) -> list[str]:
    """Stage outcomes, contract metrics, evidence paths and the overall flag of a run report."""
    failures: list[str] = []
    stages: dict[str, Mapping[str, object]] = {}
    for name in STAGE_ORDER:
        found = _stage(report, name)
        if found is None:
            failures.append(f"{name} stage is missing from the report")
        else:
            stages[name] = found
    if report.get("passed") is not True:
        failures.append(f"report passed flag is {report.get('passed')!r}, expected True")
    rules: Sequence[tuple[str, str, Mapping[str, object]]] = (
        ("import", "passed", {"stl_count": expect["stl_count"], "skipped": expect["skipped"]}),
        (
            "geometry",
            "passed",
            {"checked": expect["geometry_checked"], "failing": expect["geometry_failing"]},
        ),
        ("mechanism", "not_applicable", {}),
        ("print", "passed", {}),
        ("package", "passed", {}),
    )
    for name, outcome, metrics in rules:
        if name not in stages:
            continue
        failures += _expect_outcome(name, stages[name], outcome)
        for key, want in metrics.items():
            failures += _expect_metric(name, stages[name], key, want)
    for name in ("import", "geometry", "print", "package"):
        if name in stages and not _evidence(stages[name]):
            failures.append(f"{name} stage lists no evidence paths")
    if "print" in stages and _evidence(stages["print"]) and output_3mf(report) is None:
        failures.append("print stage evidence names no .3mf output")
    return failures


def check_import_json(doc: Mapping[str, object], expect: Mapping[str, object]) -> list[str]:
    """import.json checksums every source: the contract's STL count plus the project 3MF."""
    stls = len(_rows(doc.get("stls")))
    projects = 0 if as_mapping(doc.get("project_3mf")) is None else 1
    failures = []
    if stls != expect["stl_count"]:
        failures.append(f"import.json lists {stls} STL(s), expected {expect['stl_count']}")
    if projects != expect["import_3mf"]:
        failures.append(
            f"import.json lists {projects} project 3MF(s), expected {expect['import_3mf']}"
        )
    return failures


def check_import_source(doc: Mapping[str, object], native: Mapping[str, object]) -> list[str]:
    """Check ordinary imports against the verified source, including each byte fingerprint."""

    def artifact(row: Mapping[str, object]) -> dict[str, object]:
        return {"path": row["path"], "sha256": row["sha256"], "bytes": row["size_bytes"]}

    parts = _rows(native.get("parts"))
    project = as_mapping(native.get("project_3mf"))
    if not parts or project is None:
        return ["verified import source inventory is unavailable"]
    observed = _rows(doc.get("stls"))
    if len(observed) != len(_items(doc.get("stls"))):
        return ["import.json contains a malformed STL receipt"]
    expected = [artifact(row) for row in parts]
    failures = []
    if sorted(observed, key=lambda row: str(row.get("path"))) != sorted(
        expected, key=lambda row: str(row["path"])
    ):
        failures.append(
            "import.json STL identities or fingerprints disagree with the verified source"
        )
    if doc.get("project_3mf") != artifact(project):
        failures.append("import.json project fingerprint disagrees with the verified source")
    return failures


def count_plates(names: Iterable[str]) -> int:
    """Plates in a sliced Bambu 3MF = ``Metadata/plate_<n>.gcode`` entries (not .md5 or .json)."""
    return sum(1 for n in names if _PLATE_GCODE.match(n))


def check_plates(names: Sequence[str], want: int) -> list[str]:
    got = count_plates(names)
    if got == want:
        return []
    return [f"output 3MF holds {got} plate(s), expected {want} (counted Metadata/plate_N.gcode)"]


def check_manifest(
    manifest: Mapping[str, object], report: Mapping[str, object], expect: Mapping[str, object]
) -> list[str]:
    """Required files (contract list plus the print output) and the AGPL slicer tool entry."""
    listed = {f.get("path") for f in _rows(manifest.get("files"))}
    required = [str(p) for p in _items(expect["manifest_files"])]
    out = output_3mf(report)
    if out is not None:
        required.append(out)
    failures = [f"manifest.json does not list {path}" for path in required if path not in listed]
    tool, licence = expect["slicer_tool"], expect["slicer_license"]
    version = expect.get("slicer_version")  # pinned by vendor contracts, not by the current one
    tools = _rows(manifest.get("tools"))
    if not any(
        t.get("name") == tool
        and t.get("license") == licence
        and (version is None or t.get("version") == version)
        for t in tools
    ):
        named = tool if version is None else f"{tool} {version}"
        failures.append(f"manifest.json has no tool entry {named} with license {licence}")
    return failures


def _strings(value: object, where: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield where, value
        return
    mapping = as_mapping(value)
    if mapping is not None:
        for key, item in mapping.items():
            yield from _strings(item, f"{where}.{key}")
    for index, item in enumerate(_items(value)):
        yield from _strings(item, f"{where}[{index}]")


def find_path_leaks(documents: Mapping[str, object], *, home: str) -> list[str]:
    """Every string in the documents that contains an absolute host path marker."""
    markers = list(PATH_MARKERS) + ([home.rstrip("/")] if home.rstrip("/") else [])
    leaks = []
    for where, text in _strings(documents, ""):
        hit = next((m for m in markers if m in text), None)
        if hit is not None:
            leaks.append(f"host path {hit!r} in {where.lstrip('.')}: {text[:200]}")
    return leaks


def check_negative(report: Mapping[str, object], bad_rel: str) -> list[str]:
    """The control must fail the geometry stage and name the broken file (root-relative)."""
    geometry = _stage(report, "geometry")
    if geometry is None:
        return ["negative control: no geometry stage in the report"]
    if geometry.get("outcome") != "failed":
        return [f"negative control: geometry must be failed, was {geometry.get('outcome')}"]
    message = str(geometry.get("message") or "")
    if bad_rel not in message:
        return [f"negative control: geometry failure does not name {bad_rel}: {message[:300]}"]
    return []


def check_printer_listed(listing: Mapping[str, object], printer_id: str) -> list[str]:
    """Precondition from ``list_printers``: the contract printer must be usable on this host."""
    if any(row.get("id") == printer_id for row in _rows(listing.get("printers"))):
        return []
    row = next((r for r in _rows(listing.get("unavailable")) if r.get("id") == printer_id), None)
    if row is None:
        return [f"list_printers does not know printer {printer_id}"]
    return [
        f"printer {printer_id} is unavailable on this host: {row.get('reason')} "
        f"(install hint: {row.get('install_hint')})"
    ]


def listed_materials(listing: Mapping[str, object], printer_id: str) -> list[str]:
    """The materials ``list_printers`` offers for the printer (empty when it is not listed)."""
    for row in _rows(listing.get("printers")):
        if row.get("id") == printer_id:
            return [str(m) for m in _items(row.get("materials"))]
    return []


def check_material_rejection(error: str | None, material: str, allowed: Sequence[str]) -> list[str]:
    """Submit-time rejection: ``error`` is the tool error text, or None when a job was created."""
    if error is None:
        return [f"material negative: {material!r} was accepted at submit (a job was created)"]
    missing = [name for name in (material, *allowed) if name not in error]
    if not allowed:
        missing.append("(no allowed materials known to compare against)")
    if missing:
        return [
            f"material negative: rejection must name {material!r} and list the allowed "
            f"materials; missing {missing} in: {error[:300]}"
        ]
    return []


def check_plate_fit_negative(report: Mapping[str, object], needles: Sequence[str]) -> list[str]:
    """The too-small-printer control must end with the print stage FAILED, naming every needle."""
    stage = _stage(report, "print")
    if stage is None:
        return ["plate-fit negative: no print stage in the report"]
    if stage.get("outcome") != "failed":
        return [f"plate-fit negative: print must be failed, was {stage.get('outcome')}"]
    message = str(stage.get("message") or "")
    return [
        f"plate-fit negative: print failure lacks {needle!r}: {message[:300]}"
        for needle in needles
        if needle not in message
    ]


def poll_job(
    status: Callable[[str], Mapping[str, object]],
    job_id: str,
    *,
    budget_s: float,
    pause_s: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    say: Callable[[str], None] = lambda line: print(line, flush=True),
) -> Mapping[str, object]:
    """Poll until the job is terminal; one heartbeat line per poll (cf. ``wait_for_ollama``)."""
    started = clock()
    attempt = 0
    while True:
        attempt += 1
        job = status(job_id)
        waited = clock() - started
        say(
            f"  job {job_id} poll {attempt}: {job.get('status')} stage={job.get('stage')} "
            f"(waited {waited:.0f}s of {budget_s:g}s budget)"
        )
        if job.get("status") in TERMINAL_JOB_STATES:
            return job
        if waited >= budget_s:
            raise GateError(
                f"job {job_id} still {job.get('status')} in stage {job.get('stage')} after "
                f"{budget_s:g}s budget (slice timeout + {POLL_MARGIN_S:g}s)"
            )
        sleep(pause_s)


def check_deliverable(artifact_root: Path, root_dir: str) -> list[str]:
    if (artifact_root / root_dir).is_dir():
        return []
    return [f"deliverable not present on this host: {root_dir}"]


def check_slicer(rows: Sequence[Mapping[str, object]], tool: str) -> list[str]:
    row = next((r for r in rows if r.get("name") == tool), None)
    if row is None:
        return [f"tool_status does not report {tool}"]
    if row.get("available") is True:
        return []
    return [f"{tool} is unavailable on the server: {row.get('install_hint')}"]


def unreachable_message(url: str, exc: BaseException) -> str:
    return (
        f"MCP endpoint unreachable at {url} ({type(exc).__name__}: {exc}); "
        "set BLENDER_MCP_PUBLIC_BASE_URL or make `tailscale status --self --json` work"
    )


def truncate_header(path: Path, keep_bytes: int) -> None:
    """Cut an STL down to its first ``keep_bytes`` bytes: a header with no triangle count."""
    path.write_bytes(path.read_bytes()[:keep_bytes])
