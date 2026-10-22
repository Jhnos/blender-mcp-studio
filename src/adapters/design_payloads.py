"""Plain-dict payloads for design pipeline records, shared by REST and MCP delivery adapters.

Enums become their ``.value`` and tuples become lists. ``DesignRunReport.passed`` is a property,
so it is added by hand; ``run_dir`` is deliberately omitted (no host path leaves the process).
"""

from __future__ import annotations

from dataclasses import asdict

from src.core.domain.design_run import DesignRunReport, JobRecord, StageReport
from src.core.domain.slicing import ToolAvailability
from src.core.use_cases.printer_listing import PrinterEntry, PrinterListing


def job_dict(job: JobRecord) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "run_id": job.run_id,
        "status": job.status.value,
        "stage": None if job.stage is None else job.stage.value,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _stage_dict(stage: StageReport) -> dict[str, object]:
    return {
        "name": stage.name.value,
        "outcome": stage.outcome.value,
        "metrics": [list(pair) for pair in stage.metrics],
        "evidence": list(stage.evidence),
        "message": stage.message,
    }


def report_dict(report: DesignRunReport) -> dict[str, object]:
    return {
        "run_id": report.run_id,
        "spec_name": report.spec_name,
        "passed": report.passed,
        "stages": [_stage_dict(stage) for stage in report.stages],
    }


def _entry_dict(entry: PrinterEntry) -> dict[str, object]:
    printer = entry.printer
    heights: dict[str, object]
    if entry.layer_range is None:  # no declared range: only the catalog's own heights print
        heights = {"exact": sorted(float(key) for key, _ in printer.processes)}
    else:
        heights = {"min": entry.layer_range[0], "max": entry.layer_range[1]}
    bed = entry.bed_mm
    return {
        "id": printer.id,
        "vendor": printer.vendor,
        "model": printer.model,
        "nozzle_mm": printer.nozzle_mm,
        "materials": [material for material, _ in printer.filaments],
        "layer_height_mm": heights,
        "bed_mm": None if bed is None else [bed[0], bed[1]],
        "max_height_mm": None if bed is None else bed[2],
        "bed_type": printer.bed_type,
        "slicer": {"name": entry.slicer_name, "version": entry.slicer_version},
    }


def printer_dict(listing: PrinterListing) -> dict[str, object]:
    """The printers this host can slice for, plus those it cannot and why; no host path."""
    return {
        "printers": [_entry_dict(entry) for entry in listing.printers],
        "unavailable": [
            {"id": u.printer_id, "reason": u.reason, "install_hint": u.install_hint}
            for u in listing.unavailable
        ],
    }


def tool_dict(tool: ToolAvailability) -> dict[str, object]:
    """Availability without the binary ``path``: a host path never leaves the process."""
    row = asdict(tool)
    row.pop("path")
    return row
