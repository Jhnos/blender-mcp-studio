"""Slice one caller-named 3MF into a fresh run directory (the ``slice_for_print`` use case).

The caller's path goes through the one gate (``design_files.resolve_inputs``). Output paths are
absolute here; ``DesignPipeline.slice_file`` scrubs and relativises them on the way out.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from src.core.domain.design_run import StageName
from src.core.domain.import_limits import ImportLimits
from src.core.domain.model_spec import PrintTarget
from src.core.domain.slicing import SliceRequest, SliceResult, ToolUnavailableError
from src.core.ports.slicing_port import SlicingPort
from src.core.use_cases import design_files as files
from src.core.use_cases import print_targets
from src.core.use_cases.blender_lease import BlenderLease, run_to_completion

SLICER_BUSY = "slicer busy: another print job is running; retry later"


@contextlib.asynccontextmanager
async def claim_print(lease: BlenderLease, queue: bool) -> AsyncIterator[bool]:
    if queue:
        async with lease.hold(StageName.PRINT):
            yield True
    else:
        async with lease.try_hold(StageName.PRINT) as acquired:
            yield acquired


async def slice_one(
    slicing: SlicingPort,
    lease: BlenderLease,
    runs_dir: Path,
    roots: tuple[Path, ...],
    limits: ImportLimits,
    input_3mf: str,
    target: PrintTarget,
    *,
    queue: bool = True,
) -> SliceResult:
    """Slice ``input_3mf`` (relative to an artifact root) for ``target``; paths stay absolute.

    The target is checked as at spec submit (``check_print_target``) before any run directory
    exists: an unusable printer, a material it lacks or an unprintable height is a
    ``ModelSpecError``.

    With ``queue=False`` a held lease returns a "slicer busy" result at once instead of waiting.
    A missing slicer is a failed result, never an exception; a run directory that ends up
    empty (busy, failure) is removed.
    """
    (found,) = await asyncio.to_thread(
        files.resolve_inputs,
        (input_3mf,),
        suffix=".3mf",
        roots=roots,
        max_count=1,
        max_bytes=limits.max_3mf_bytes,
    )
    await print_targets.check_print_target(target, slicing)
    run_dir = runs_dir / uuid.uuid4().hex
    try:
        async with claim_print(lease, queue) as acquired:
            if not acquired:
                return SliceResult(False, None, None, "", -1, SLICER_BUSY)
            run_dir.mkdir(parents=True)
            request = SliceRequest.from_target(
                str(found.absolute),
                str(run_dir / "print"),
                target,
                printer_id=target.printer,
            )
            try:
                return await run_to_completion(slicing.slice(request))
            except ToolUnavailableError as exc:
                return SliceResult(False, None, None, "", -1, str(exc))
    finally:
        for leftover in (run_dir / "print", run_dir):
            with contextlib.suppress(OSError):
                leftover.rmdir()
