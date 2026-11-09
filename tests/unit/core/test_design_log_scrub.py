"""Packaged slicer logs carry no host path, whichever slicer wrote them and however it ended."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from src.adapters.packaging.manifest_packager import ManifestPackager
from src.core.domain.design_run import StageName, StageOutcome
from src.core.use_cases.design_files import public_run_file, resolve_run_file
from tests.unit.core.test_design_pipeline import _payload, _rig, _run

_FORBIDDEN = ("/Users/", "/private/", "/var/folders")


class LoggingSlicer:
    """Wraps the fake slicer: writes two vendor-style logs full of host paths, as real ones do."""

    def __init__(self, inner, tmp_path: Path, rc: int = 0) -> None:
        self._inner, self._tmp, self.rc = inner, tmp_path, rc

    def __getattr__(self, name):
        return getattr(self._inner, name)

    async def slice(self, request):
        result = await self._inner.slice(request)
        out = Path(request.output_dir)
        noise = (
            f"load {self._tmp}/runs/x/print/a.3mf from {Path.home()}/Library/x "
            f"{self._tmp.resolve()}/z"
        )
        for name in ("slicer.log", "00000.log"):
            (out / name).write_text(f"{noise}\nbyte é\n", encoding="utf-8")
        return replace(result, passed=self.rc == 0, return_code=self.rc, message="slicer said no")


def _wire(rig, tmp_path: Path, rc: int = 0) -> None:
    rig.pipeline._stages = replace(
        rig.pipeline._stages,
        slicing=LoggingSlicer(rig.slicing, tmp_path, rc),
        packaging=ManifestPackager(),
    )


def _public_bytes(run_dir: Path) -> dict[str, bytes]:
    return {
        p.relative_to(run_dir).as_posix(): p.read_bytes()
        for p in run_dir.rglob("*")
        if p.is_file() and public_run_file(run_dir, p)
    }


def _assert_clean(run_dir: Path, tmp_path: Path) -> None:
    for name, data in _public_bytes(run_dir).items():
        text = data.decode("utf-8", errors="replace")
        for bad in (*_FORBIDDEN, str(Path.home()), str(tmp_path)):
            assert bad not in text, f"{name} leaks {bad}"


async def test_success_path_logs_are_scrubbed_and_manifest_hashes_match(tmp_path):
    rig = _rig(tmp_path)
    _wire(rig, tmp_path)
    job, _, report = await _run(rig, _relative(rig))
    assert report.passed
    run_dir = rig.runs / job.run_id
    assert (run_dir / "print" / "00000.log").is_file()
    _assert_clean(run_dir, tmp_path)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    listed = {f["path"]: f["sha256"] for f in manifest["files"]}
    for name in ("print/slicer.log", "print/00000.log"):
        assert listed[name] == hashlib.sha256((run_dir / name).read_bytes()).hexdigest()


async def test_failure_path_logs_are_scrubbed(tmp_path):
    rig = _rig(tmp_path)
    _wire(rig, tmp_path, rc=3)
    job, _, report = await _run(rig, _relative(rig))
    assert report.stages[-1].name is StageName.PRINT
    assert report.stages[-1].outcome is StageOutcome.FAILED
    run_dir = rig.runs / job.run_id
    assert (run_dir / "print" / "slicer.log").is_file()
    _assert_clean(run_dir, tmp_path)


async def test_every_downloadable_file_is_free_of_host_paths(tmp_path):
    rig = _rig(tmp_path)
    _wire(rig, tmp_path)
    job, _, _ = await _run(rig, _relative(rig))
    run_dir = rig.runs / job.run_id
    for name in _public_bytes(run_dir):
        data = resolve_run_file(rig.runs, job.run_id, name).read_bytes()
        assert not any(bad.encode() in data for bad in (*_FORBIDDEN, str(Path.home())))


def _relative(rig) -> dict:
    """The spec names its root relative to the artifact root, so spec.json is host-free too."""
    payload = _payload(rig)
    payload["source"]["root_dir"] = "artifact"
    return payload
