"""Fake ports for DesignPipeline (no Blender, slicer or sqlite), shared by unit and e2e tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.core.domain.design_run import JobRecord, JobStatus, StageName
from src.core.domain.mesh_integrity import MeshIntegrityReport, MeshVerdict
from src.core.domain.packaging import PackagedFile, PackageManifest, ToolUse
from src.core.domain.slicing import SliceResult, ToolAvailability
from src.core.domain.verification import VerificationReport
from src.core.use_cases.blender_lease import BlenderLease
from src.infrastructure.printer_catalog_loader import load_printer_catalog


class FakeJobs:
    def __init__(self) -> None:
        self.records: dict[str, JobRecord] = {}
        self.history: list[tuple[JobStatus, StageName | None]] = []

    async def create(self, run_id):
        rec = JobRecord(f"job{len(self.records)}", run_id, JobStatus.QUEUED, None, None, 0.0, 0.0)
        self.records[rec.job_id] = rec
        return rec

    async def update(self, job_id, *, status, stage=None, error=None):
        rec = JobRecord(job_id, self.records[job_id].run_id, status, stage, error, 0.0, 1.0)
        self.records[job_id] = rec
        self.history.append((status, stage))
        return rec

    async def get(self, job_id):
        return self.records.get(job_id)

    async def list_unfinished(self):
        live = (JobStatus.QUEUED, JobStatus.RUNNING)
        return tuple(r for r in self.records.values() if r.status in live)


class FakeIntegrity:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.seen: tuple[str, ...] = ()

    async def check(self, stl_paths):
        self.seen = stl_paths
        return MeshIntegrityReport(
            tuple(
                MeshVerdict(p, 8, 12, self.ok, False, None if self.ok else "open")
                for p in stl_paths
            )
        )


class FakeSimulation:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.calls: list[tuple[str, ...]] = []

    async def run(self, suites):
        self.calls.append(suites)
        return tuple(VerificationReport(s, self.ok, (), "scope", True) for s in suites)


FAKE_TIMEOUT_S = 123.0  # not the real slicer value: MCP must read it from the port


class FakeSlicing:
    """One usable printer (the P2S) unless ``printer_ids`` names more catalog printers."""

    def __init__(
        self,
        lease: BlenderLease,
        delay: float = 0.0,
        log: list | None = None,
        printer_ids: tuple[str, ...] = ("bambu-p2s-0.4",),
    ) -> None:
        self.lease, self.delay, self.log = lease, delay, log if log is not None else []
        self.requests: list = []
        self.error: Exception | None = None
        catalog = load_printer_catalog()
        self._catalog = catalog
        self._printers = tuple(catalog.printer(pid) for pid in printer_ids)

    def printers(self):
        return self._printers

    def timeout_s(self, printer_id: str) -> float:
        return FAKE_TIMEOUT_S

    def max_timeout_s(self) -> float:
        return FAKE_TIMEOUT_S

    def tool_for(self, printer_id: str) -> ToolUse:
        slicer = self._catalog.slicer(self._catalog.printer(printer_id).slicer)
        version = {"bambu-studio": "02.06.00.51", "orcaslicer": "2.4.2"}[slicer.id]
        return ToolUse(slicer.id, version, slicer.license, "subprocess")

    async def availability(self):
        return (ToolAvailability("Bambu Studio", True, "/x/bs", "02.06.00.51", "hint"),)

    async def slice(self, request):
        self.requests.append(request)
        self.log.append(("slice-start", self.lease.holder))
        if self.error:
            raise self.error
        await asyncio.sleep(self.delay)
        self.log.append(("slice-end", self.lease.holder))
        out = Path(request.output_dir)
        out.mkdir(parents=True, exist_ok=True)  # like the real adapter: evidence is openable
        (out / "out.3mf").write_bytes(b"3mf")
        (out / "log.txt").write_text("ok", encoding="utf-8")
        return SliceResult(True, f"{out}/out.3mf", None, f"{out}/log.txt", 0, "ok")


class FakePackaging:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list = []
        self.error = error

    async def package(self, run_id, spec_name, run_dir, files, *, tools=()):
        self.calls.append((run_id, spec_name, run_dir, files, tools))
        if self.error:
            raise self.error
        packed = (PackagedFile(files[0], "0" * 64, 1, None),) if files else ()
        Path(run_dir, "manifest.json").write_text("{}", encoding="utf-8")
        return PackageManifest(run_id, spec_name, packed, f"{run_dir}/manifest.json", tools)
