"""Pure verdict rules for the design pipeline real gate (no network, no files but the ones named).

Every function returns a list of readable failure strings (empty = pass) so the gate can print
all of them at once instead of stopping at the first. Expected numbers come from the contract
JSON (``scripts/verify/contracts/design_pipeline_v78.json``), never from this module.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from pathlib import Path

from src.adapters.slicing.bambu_studio_cli import SLICE_TIMEOUT_S
from src.infrastructure.narrowing import as_mapping, as_sequence

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


def check_native_source(root: Path, spec: Mapping[str, object], receipt: object) -> list[str]:
    """Independent public-receipt oracle, reading actual selected files, not the adapter.

    This establishes file identity only. No historical names, part counts, hashes or
    manufacturing claims are hard-coded, and no Blender operation is performed.
    """
    native = as_mapping(receipt)
    if native is None or native.get("available") is not True:
        return ["selected native provenance is unavailable; no historical fallback"]
    try:
        source = as_mapping(spec["source"])
        if source is None:
            raise ValueError("missing source")
        relative = Path(str(source["root_dir"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("non-relative selected root")
        selected = root / relative

        def safe_file(name: str) -> Path:
            path = selected / name
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("non-relative manifest asset")
            for ancestor in (path, *path.parents):
                if ancestor == root:
                    break
                if ancestor.is_symlink():
                    raise ValueError("symlinked source")
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("source outside artifact root")
            return path

        raw = safe_file("SHA256.json").read_bytes()
        manifest = as_mapping(json.loads(raw))
        if not manifest:
            raise ValueError("empty manifest")
        actual: dict[str, object] = {}
        total_bytes = 0
        for name, expected in manifest.items():
            path = safe_file(name)
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            if not isinstance(expected, str) or digest != expected.lower():
                raise ValueError("local manifest checksum mismatch")
            size = path.stat().st_size
            total_bytes += size
            actual[name] = {"path": name, "sha256": digest, "size_bytes": size}
        natives = [name for name in manifest if Path(name).suffix.lower() == ".blend"]
        if len(natives) != 1:
            raise ValueError("ambiguous native")
        parts = [
            p.relative_to(selected).as_posix()
            for p in sorted(selected.glob(str(source["stl_glob"])))
            if p.is_file()
        ]
        if not parts:
            raise ValueError("empty selected parts")
        expected_receipt = {
            "scope": "file_identity_only",
            "available": True,
            "model_name": spec["name"],
            "root_dir": relative.as_posix(),
            "native": actual[natives[0]],
            "parts": [actual[name] for name in parts],
            "project_3mf": actual.get(str(source.get("project_3mf"))),
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "verified_files": len(manifest),
            "total_bytes": total_bytes,
        }
        observed = dict(native)
        observed["parts"] = list(as_sequence(native.get("parts")) or ())
        return [
            f"native provenance disagrees with selected files: {field}"
            for field, value in expected_receipt.items()
            if observed.get(field) != value
        ]
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        return ["selected native source cannot be independently verified"]


def poll_budget_s() -> float:
    return SLICE_TIMEOUT_S + POLL_MARGIN_S


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
    tools = _rows(manifest.get("tools"))
    if not any(t.get("name") == tool and t.get("license") == licence for t in tools):
        failures.append(f"manifest.json has no tool entry {tool} with license {licence}")
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
