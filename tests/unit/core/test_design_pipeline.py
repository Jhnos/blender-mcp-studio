"""DesignPipeline with fakes for every port (no Blender, slicer or sqlite)."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import pytest

from src.core.domain.design_run import JobRecord, JobStatus, StageName, StageOutcome
from src.core.domain.mesh_integrity import MeshIntegrityReport, MeshVerdict
from src.core.domain.model_spec import ModelSpecError
from src.core.domain.packaging import PackagedFile, PackageManifest
from src.core.domain.slicing import SliceResult, ToolAvailability, ToolUnavailableError
from src.core.domain.verification import VerificationReport
from src.core.use_cases.blender_lease import BlenderLease
from src.core.use_cases.design_pipeline import DesignPipeline


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


class FakeSlicing:
    def __init__(self, lease: BlenderLease, delay: float = 0.0, log: list | None = None) -> None:
        self.lease, self.delay, self.log = lease, delay, log if log is not None else []
        self.requests: list = []
        self.error: Exception | None = None

    async def availability(self):
        return ToolAvailability("Bambu Studio", True, "/x/bs", "02.06.00.51", "hint")

    async def slice(self, request):
        self.requests.append(request)
        self.log.append(("slice-start", self.lease.holder))
        if self.error:
            raise self.error
        await asyncio.sleep(self.delay)
        self.log.append(("slice-end", self.lease.holder))
        out = request.output_dir
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
        return PackageManifest(run_id, spec_name, packed, f"{run_dir}/manifest.json", tools)


@dataclass
class Rig:
    pipeline: DesignPipeline
    jobs: FakeJobs
    integrity: FakeIntegrity
    simulation: FakeSimulation
    slicing: FakeSlicing
    packaging: FakePackaging
    lease: BlenderLease
    root: object
    runs: object
    log: list = field(default_factory=list)


def _rig(tmp_path, *, geometry_ok=True, sim_ok=True, delay=0.0, pack_error=None) -> Rig:
    root = tmp_path / "artifact"
    (root / "STL").mkdir(parents=True)
    for name in ("a.stl", "b.stl"):
        (root / "STL" / name).write_bytes(b"x")
    (root / "p.3mf").write_bytes(b"3mf")
    runs = tmp_path / "runs"
    lease, log = BlenderLease(), []
    jobs, integrity, simulation = FakeJobs(), FakeIntegrity(geometry_ok), FakeSimulation(sim_ok)
    slicing, packaging = FakeSlicing(lease, delay, log), FakePackaging(pack_error)
    pipeline = DesignPipeline(
        integrity=integrity,
        simulation=simulation,
        slicing=slicing,
        packaging=packaging,
        jobs=jobs,
        lease=lease,
        runs_dir=runs,
        artifact_roots=(tmp_path,),
    )
    return Rig(pipeline, jobs, integrity, simulation, slicing, packaging, lease, root, runs, log)


def _payload(rig: Rig, *, suites=("s1",), project="p.3mf") -> dict:
    source: dict = {"root_dir": str(rig.root)}
    if project:
        source["project_3mf"] = project
    return {
        "spec_version": "1",
        "name": "demo",
        "source": source,
        "mechanism": {"suites": list(suites)},
    }


async def _run(rig: Rig, payload: dict):
    job = await rig.pipeline.submit(payload)
    await rig.pipeline.wait_idle()
    return job, await rig.pipeline.status(job.job_id), await rig.pipeline.report(job.run_id)


async def test_run_writes_report_after_each_stage(tmp_path):
    rig = _rig(tmp_path)
    job, status, report = await _run(rig, _payload(rig))
    assert [s.name for s in report.stages] == list(StageName)
    assert report.passed and status.status is JobStatus.DONE
    assert (rig.runs / job.run_id / "report.json").is_file()
    assert not (rig.runs / job.run_id / "report.json.tmp").exists()
    # each stage moves the job to RUNNING with that stage, in order, ending DONE
    assert [s for r, s in rig.jobs.history if r is JobStatus.RUNNING] == list(StageName)
    assert rig.jobs.history[-1][0] is JobStatus.DONE
    imp = report.stages[0]
    assert dict(imp.metrics)["stl_count"] == "2" and imp.evidence == ("STL/a.stl", "STL/b.stl")
    on_disk = json.loads((rig.runs / job.run_id / "report.json").read_text())
    assert [s["name"] for s in on_disk["stages"]] == [s.value for s in StageName]


async def test_report_json_grows_one_stage_at_a_time(tmp_path):
    rig = _rig(tmp_path)
    seen: list[int] = []
    original = rig.packaging.package

    async def spy(run_id, spec_name, run_dir, files, *, tools=()):
        seen.append(len(json.loads((rig.runs / run_id / "report.json").read_text())["stages"]))
        return await original(run_id, spec_name, run_dir, files, tools=tools)

    rig.packaging.package = spy
    await _run(rig, _payload(rig))
    assert seen == [4]  # import..print already on disk when package starts


async def test_geometry_failure_stops_before_mechanism(tmp_path):
    rig = _rig(tmp_path, geometry_ok=False)
    _, status, report = await _run(rig, _payload(rig))
    assert [s.name for s in report.stages] == [StageName.IMPORT, StageName.GEOMETRY]
    assert not report.passed and status.status is JobStatus.FAILED
    assert "a.stl" in report.stages[1].message
    assert rig.simulation.calls == [] and rig.lease.holder is None


async def test_mechanism_not_applicable_when_no_suites(tmp_path):
    rig = _rig(tmp_path)
    _, _, report = await _run(rig, _payload(rig, suites=()))
    assert report.stages[2].outcome is StageOutcome.NOT_APPLICABLE and report.passed
    assert rig.simulation.calls == []


async def test_mechanism_failure_fails_run(tmp_path):
    rig = _rig(tmp_path, sim_ok=False)
    _, _, report = await _run(rig, _payload(rig))
    assert report.stages[-1].name is StageName.MECHANISM and not report.passed


async def test_print_fails_without_project_3mf(tmp_path):
    rig = _rig(tmp_path)
    _, _, report = await _run(rig, _payload(rig, project=None))
    assert report.stages[-1].name is StageName.PRINT
    assert report.stages[-1].message == "no project 3MF to slice"


async def test_slice_request_uses_run_print_dir(tmp_path):
    rig = _rig(tmp_path)
    job, _, _ = await _run(rig, _payload(rig))
    req = rig.slicing.requests[0]
    assert req.output_dir == str(rig.runs / job.run_id / "print")
    assert req.input_3mf == str(rig.root.resolve() / "p.3mf")


async def test_second_run_waits_for_blender_lease(tmp_path):
    rig = _rig(tmp_path, delay=0.05)
    j1 = await rig.pipeline.submit(_payload(rig))
    j2 = await rig.pipeline.submit(_payload(rig))
    await rig.pipeline.wait_idle()
    events = rig.log
    assert [e[0] for e in events] == ["slice-start", "slice-end", "slice-start", "slice-end"]
    assert all(holder is StageName.PRINT for _, holder in events)
    assert (await rig.pipeline.status(j1.job_id)).status is JobStatus.DONE
    assert (await rig.pipeline.status(j2.job_id)).status is JobStatus.DONE
    assert rig.lease.holder is None


def test_run_file_rejects_traversal(tmp_path):
    rig = _rig(tmp_path)
    run_id = "a" * 32
    (rig.runs / run_id).mkdir(parents=True)
    (rig.runs / run_id / "ok.txt").write_text("x")
    assert rig.pipeline.run_file(run_id, "ok.txt") == (rig.runs / run_id / "ok.txt").resolve()
    for bad in ("../x", "/etc/passwd", "..", "a/../../x"):
        with pytest.raises(ValueError):
            rig.pipeline.run_file(run_id, bad)


def test_run_file_rejects_symlink_out_of_run_dir(tmp_path):
    rig = _rig(tmp_path)
    run_id = "b" * 32
    (rig.runs / run_id).mkdir(parents=True)
    (tmp_path / "secret").write_text("s")
    (rig.runs / run_id / "link").symlink_to(tmp_path / "secret")
    with pytest.raises(ValueError):
        rig.pipeline.run_file(run_id, "link")


@pytest.mark.parametrize(
    "bad", ["../x", "A" * 32, "a" * 31, "a" * 33, "", "g" * 32, "a" * 31 + "/"]
)
def test_run_file_rejects_bad_run_id(tmp_path, bad):
    rig = _rig(tmp_path)
    with pytest.raises(ValueError):
        rig.pipeline.run_file(bad, "report.json")


async def test_import_rejects_symlink_escaping_root(tmp_path):
    rig = _rig(tmp_path)
    outside = tmp_path / "outside.stl"
    outside.write_bytes(b"secret")
    (rig.root / "STL" / "evil.stl").symlink_to(outside)
    _, status, report = await _run(rig, _payload(rig))
    assert len(report.stages) == 1 and report.stages[0].outcome is StageOutcome.FAILED
    assert "evil.stl" in report.stages[0].message
    assert rig.integrity.seen == () and status.status is JobStatus.FAILED


async def test_import_rejects_project_3mf_symlink_escape(tmp_path):
    # The parser rejects a symlinked 3MF at submit. A link swapped in between submit and run
    # is caught by the run-time re-parse of spec.json: the job FAILS and nothing is sliced.
    rig = _rig(tmp_path)
    outside = tmp_path / "outside.3mf"
    outside.write_bytes(b"x")
    job = await rig.pipeline.submit(_payload(rig))
    (rig.root / "p.3mf").unlink()
    (rig.root / "p.3mf").symlink_to(outside)
    await rig.pipeline.wait_idle()
    status = await rig.pipeline.status(job.job_id)
    assert status.status is JobStatus.FAILED and "project_3mf" in status.error
    assert rig.slicing.requests == []


async def test_import_escape_message_is_root_relative(tmp_path):
    rig = _rig(tmp_path)
    outside = tmp_path / "outside.stl"
    outside.write_bytes(b"secret")
    (rig.root / "STL" / "evil.stl").symlink_to(outside)
    _, _, report = await _run(rig, _payload(rig))
    assert report.stages[0].message.startswith("STL/evil.stl:")


async def test_submit_rejects_symlinked_project_3mf_at_parse(tmp_path):
    rig = _rig(tmp_path)
    outside = tmp_path / "outside.3mf"
    outside.write_bytes(b"x")
    (rig.root / "evil.3mf").symlink_to(outside)
    with pytest.raises(ModelSpecError):
        await rig.pipeline.submit(_payload(rig, project="evil.3mf"))


async def test_import_fails_with_zero_stls(tmp_path):
    rig = _rig(tmp_path)
    for f in (rig.root / "STL").iterdir():
        f.unlink()
    _, _, report = await _run(rig, _payload(rig))
    assert report.stages[0].outcome is StageOutcome.FAILED and len(report.stages) == 1


async def test_package_stage_records_slicer_license(tmp_path):
    rig = _rig(tmp_path)
    job, _, _ = await _run(rig, _payload(rig))
    _, _, run_dir, files, tools = rig.packaging.calls[0]
    assert (tools[0].name, tools[0].version, tools[0].license, tools[0].invocation) == (
        "Bambu Studio",
        "02.06.00.51",
        "AGPL-3.0-only",
        "subprocess",
    )
    assert run_dir == str(rig.runs / job.run_id)
    assert "report.json" not in files


async def test_stage_exception_fails_job_not_running(tmp_path):
    rig = _rig(tmp_path, pack_error=ValueError("file is outside the run directory"))
    _, status, report = await _run(rig, _payload(rig))
    last = report.stages[-1]
    assert last.name is StageName.PACKAGE and last.outcome is StageOutcome.FAILED
    assert last.message == "ValueError: file is outside the run directory"
    assert status.status is JobStatus.FAILED and "ValueError" in status.error


async def test_slicer_unavailable_fails_print_stage(tmp_path):
    rig = _rig(tmp_path)
    rig.slicing.error = ToolUnavailableError("Bambu Studio not installed; brew install it")
    _, status, report = await _run(rig, _payload(rig))
    assert report.stages[-1].name is StageName.PRINT
    assert report.stages[-1].message.startswith("ToolUnavailableError: Bambu Studio not installed")
    assert status.status is JobStatus.FAILED and rig.lease.holder is None


async def test_cancelled_run_never_stays_running(tmp_path):
    rig = _rig(tmp_path, delay=5)
    job = await rig.pipeline.submit(_payload(rig))
    for _ in range(100):
        await asyncio.sleep(0.01)
        if rig.lease.holder is StageName.PRINT:
            break
    assert rig.lease.holder is StageName.PRINT
    tasks = list(rig.pipeline._tasks)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    assert (await rig.pipeline.status(job.job_id)).status is not JobStatus.RUNNING
    assert rig.lease.holder is None


async def test_submit_rejects_invalid_spec_without_side_effects(tmp_path):
    rig = _rig(tmp_path)
    bad = {"spec_version": "1", "name": "x", "source": {"root_dir": "/etc"}}
    with pytest.raises(ModelSpecError):
        await rig.pipeline.submit(bad)
    assert rig.jobs.records == {} and not rig.runs.exists()


async def test_report_and_status_for_missing_ids_are_none(tmp_path):
    rig = _rig(tmp_path)
    assert await rig.pipeline.report("c" * 32) is None
    assert await rig.pipeline.report("../bad") is None
    assert await rig.pipeline.status("nope") is None


async def test_submit_writes_spec_json(tmp_path):
    rig = _rig(tmp_path)
    payload = _payload(rig)
    job = await rig.pipeline.submit(payload)
    await rig.pipeline.wait_idle()
    spec_file = rig.runs / job.run_id / "spec.json"
    assert json.loads(spec_file.read_text()) == payload
    assert "spec.json" in rig.packaging.calls[0][3]  # reproduction input stays in the package


async def test_missing_spec_file_fails_job(tmp_path):
    rig = _rig(tmp_path)
    job = await rig.pipeline.submit(_payload(rig))
    (rig.runs / job.run_id / "spec.json").unlink()  # no await since submit: run has not started
    await rig.pipeline.wait_idle()
    status = await rig.pipeline.status(job.job_id)
    assert status.status is JobStatus.FAILED and "spec" in status.error


async def test_corrupt_spec_file_fails_job(tmp_path):
    rig = _rig(tmp_path)
    job = await rig.pipeline.submit(_payload(rig))
    (rig.runs / job.run_id / "spec.json").write_text("{not json")
    await rig.pipeline.wait_idle()
    status = await rig.pipeline.status(job.job_id)
    assert status.status is JobStatus.FAILED and status.error


async def test_recover_interrupted_marks_queued_and_running(tmp_path):
    rig = _rig(tmp_path)
    queued = await rig.jobs.create("d" * 32)
    running = await rig.jobs.create("e" * 32)
    await rig.jobs.update(running.job_id, status=JobStatus.RUNNING, stage=StageName.GEOMETRY)
    done = await rig.jobs.create("f" * 32)
    await rig.jobs.update(done.job_id, status=JobStatus.DONE)
    assert await rig.pipeline.recover_interrupted() == 2
    for job_id in (queued.job_id, running.job_id):
        rec = await rig.pipeline.status(job_id)
        assert rec.status is JobStatus.FAILED and rec.error == "interrupted: service restarted"
    assert (await rig.pipeline.status(running.job_id)).stage is StageName.GEOMETRY
    assert (await rig.pipeline.status(done.job_id)).status is JobStatus.DONE
    assert await rig.pipeline.recover_interrupted() == 0


async def test_recover_rewrites_report_as_failed(tmp_path):
    rig = _rig(tmp_path, delay=5)
    job = await rig.pipeline.submit(_payload(rig))
    for _ in range(100):
        await asyncio.sleep(0.01)
        if rig.lease.holder is StageName.PRINT:
            break
    # Simulate a crash: the in-memory task dies without running its handlers' bookkeeping.
    for task in list(rig.pipeline._tasks):
        task.cancel()
    await asyncio.gather(*list(rig.pipeline._tasks), return_exceptions=True)
    await rig.jobs.update(job.job_id, status=JobStatus.RUNNING, stage=StageName.PRINT)
    path = rig.runs / job.run_id / "report.json"
    data = json.loads(path.read_text())
    data["stages"] = data["stages"][:3]  # as if the crash left only import..mechanism on disk
    path.write_text(json.dumps(data))
    assert await rig.pipeline.recover_interrupted() == 1
    report = await rig.pipeline.report(job.run_id)
    assert [s.name for s in report.stages][-1] is StageName.PRINT
    assert report.stages[-1].outcome is StageOutcome.FAILED
    assert report.stages[-1].message == "interrupted: service restarted"
    assert not report.passed


async def test_cancel_mid_print_marks_cancelled_and_report_failed(tmp_path):
    rig = _rig(tmp_path, delay=5)
    job = await rig.pipeline.submit(_payload(rig))
    for _ in range(100):
        await asyncio.sleep(0.01)
        if rig.lease.holder is StageName.PRINT:
            break
    tasks = list(rig.pipeline._tasks)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    assert (await rig.pipeline.status(job.job_id)).status is JobStatus.CANCELLED
    on_disk = json.loads((rig.runs / job.run_id / "report.json").read_text())
    assert on_disk["passed"] is False
    assert (on_disk["stages"][-1]["name"], on_disk["stages"][-1]["outcome"]) == ("print", "failed")
    assert on_disk["stages"][-1]["message"] == "cancelled"
    assert rig.lease.holder is None


async def test_package_excludes_slicer_scratch(tmp_path):
    # The real guarantee is the adapter's temp datadir (test_bambu_studio_cli); this pins
    # that nothing named bambu-data is handed to the packager.
    rig = _rig(tmp_path)
    await _run(rig, _payload(rig))
    files = rig.packaging.calls[0][3]
    assert not any("bambu-data" in f for f in files)


async def test_store_get_failure_is_logged_not_left_running(tmp_path, caplog):
    rig = _rig(tmp_path)

    async def boom(job_id):
        raise RuntimeError("store down")

    rig.jobs.get = boom
    await rig.pipeline.submit(_payload(rig))
    await rig.pipeline.wait_idle()
    assert "design run task failed" in caplog.text and "store down" in caplog.text
    assert rig.jobs.history == []  # no job could be read, so there is nothing to update


async def test_recover_refuses_while_runs_in_flight(tmp_path):
    rig = _rig(tmp_path, delay=5)
    await rig.pipeline.submit(_payload(rig))
    with pytest.raises(RuntimeError, match="startup-only"):
        await rig.pipeline.recover_interrupted()
    for task in list(rig.pipeline._tasks):
        task.cancel()
    await asyncio.gather(*list(rig.pipeline._tasks), return_exceptions=True)


async def test_recover_continues_past_corrupt_report(tmp_path):
    rig = _rig(tmp_path)
    ids = ("a" * 32, "b" * 32)
    jobs = []
    for run_id in ids:
        job = await rig.jobs.create(run_id)
        await rig.jobs.update(job.job_id, status=JobStatus.RUNNING, stage=StageName.GEOMETRY)
        (rig.runs / run_id).mkdir(parents=True)
        jobs.append(job)
    (rig.runs / ids[0] / "report.json").write_text("{trunc")
    assert await rig.pipeline.recover_interrupted() == 2
    for job in jobs:
        assert (await rig.pipeline.status(job.job_id)).status is JobStatus.FAILED
    report = await rig.pipeline.report(ids[0])
    assert report.stages[-1].outcome is StageOutcome.FAILED and not report.passed
    assert report.stages[-1].message == "interrupted: service restarted"
