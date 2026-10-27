"""DesignPipeline.check_meshes / slice_file: caller paths go through the one gate and the caps."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.core.domain.design_run import StageName
from src.core.domain.model_spec import ModelSpecError, PrintTarget
from src.core.domain.slicing import SliceRequest
from tests.unit.core.test_design_pipeline import _rig


def _tight(rig, **kw):
    rig.pipeline._stages = replace(
        rig.pipeline._stages, limits=replace(rig.pipeline._stages.limits, **kw)
    )


async def test_check_meshes_passes_resolved_paths_and_reports_relative(tmp_path):
    rig = _rig(tmp_path)
    report = await rig.pipeline.check_meshes(("artifact/STL/a.stl", "artifact/STL/b.stl"))
    assert rig.integrity.seen == tuple(
        str((rig.root / "STL" / n).resolve()) for n in ("a.stl", "b.stl")
    )
    assert [v.path for v in report.verdicts] == ["artifact/STL/a.stl", "artifact/STL/b.stl"]


async def test_check_meshes_error_text_has_no_host_path(tmp_path):
    rig = _rig(tmp_path, geometry_ok=False)
    original = rig.integrity.check

    async def check(paths):
        out = await original(paths)
        return replace(
            out,
            verdicts=tuple(replace(v, error=f"{v.path}: open surface") for v in out.verdicts),
        )

    rig.integrity.check = check
    report = await rig.pipeline.check_meshes(("artifact/STL/a.stl",))
    assert report.verdicts[0].error == "artifact/STL/a.stl: open surface"
    assert str(tmp_path) not in repr(report)


@pytest.mark.parametrize("bad", ["../x.stl", "/etc/hosts.stl", "artifact/nope.stl", "a.txt"])
async def test_check_meshes_rejects_bad_paths(tmp_path, bad):
    rig = _rig(tmp_path)
    with pytest.raises(ModelSpecError):
        await rig.pipeline.check_meshes((bad,))
    assert rig.integrity.seen == ()


async def test_check_meshes_rejects_empty_list_and_count_cap(tmp_path):
    rig = _rig(tmp_path)
    with pytest.raises(ModelSpecError, match="at least one"):
        await rig.pipeline.check_meshes(())
    _tight(rig, max_stl_files=1)
    with pytest.raises(ModelSpecError, match="2 .*1"):
        await rig.pipeline.check_meshes(("artifact/STL/a.stl", "artifact/STL/b.stl"))
    assert rig.integrity.seen == ()


async def test_check_meshes_rejects_oversized_file(tmp_path):
    rig = _rig(tmp_path)
    (rig.root / "STL" / "b.stl").write_bytes(b"x" * 50)
    _tight(rig, max_stl_bytes=10)
    with pytest.raises(ModelSpecError, match="artifact/STL/b.stl"):
        await rig.pipeline.check_meshes(("artifact/STL/b.stl",))


async def test_slice_file_rejects_non_3mf_and_oversized(tmp_path):
    rig = _rig(tmp_path)
    with pytest.raises(ModelSpecError, match="3mf"):
        await rig.pipeline.slice_file("artifact/STL/a.stl", "bambu-p2s")
    _tight(rig, max_3mf_bytes=1)
    with pytest.raises(ModelSpecError, match="artifact/p.3mf"):
        await rig.pipeline.slice_file("artifact/p.3mf", "bambu-p2s")
    assert rig.slicing.requests == []


async def test_slice_file_fresh_run_dir_lease_and_print_defaults(tmp_path):
    rig = _rig(tmp_path)
    result = await rig.pipeline.slice_file("artifact/p.3mf", "bambu-p2s")
    (request,) = rig.slicing.requests
    run_dir = Path(request.output_dir).parent
    assert len(run_dir.name) == 32 and run_dir.parent == rig.runs
    assert request == SliceRequest.from_target(
        str((rig.root / "p.3mf").resolve()),
        str(run_dir / "print"),
        PrintTarget(printer="bambu-p2s"),
    )
    assert ("slice-start", StageName.PRINT) in rig.log
    assert ("slice-end", StageName.PRINT) in rig.log
    assert rig.lease.holder is None
    # paths come back relative to the runs dir: <run_id>/print/<name>
    assert result.output_3mf == f"{run_dir.name}/print/out.3mf"
    assert result.log_path == f"{run_dir.name}/print/log.txt"
    assert str(tmp_path) not in repr(result)


async def test_two_slice_files_get_distinct_run_dirs(tmp_path):
    rig = _rig(tmp_path)
    await rig.pipeline.slice_file("artifact/p.3mf", "bambu-p2s")
    await rig.pipeline.slice_file("artifact/p.3mf", "bambu-p2s")
    assert len({r.output_dir for r in rig.slicing.requests}) == 2
