"""Native modifications receive an exclusive, checksum-bound source snapshot."""

import json
from dataclasses import replace

import pytest

from src.adapters.artifacts.native_staging import FilesystemNativeStaging
from src.core.domain.native_revision import NativeSourceError
from tests.unit.adapters.test_native_source import fixture

RUN = "a" * 32


async def test_snapshot_copies_complete_manifest_and_stays_independent(tmp_path):
    root, manifest, spec, reader = fixture(tmp_path)
    source = await reader.resolve(spec)
    stage = FilesystemNativeStaging(reader, tmp_path / "runs")
    result = await stage.stage(spec, source, RUN)
    target = tmp_path / "runs" / result.directory
    assert result.source == source and str(tmp_path) not in repr(result)
    assert source.total_bytes == sum((root / n).stat().st_size for n in manifest)
    assert sorted(
        p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()
    ) == sorted([*manifest, "SHA256.json"])
    for name in [*manifest, "SHA256.json"]:
        assert (target / name).read_bytes() == (root / name).read_bytes()
    (root / "native.blend").write_bytes(b"later edit")
    assert (target / "native.blend").read_bytes() == b"opaque-native"
    with pytest.raises(NativeSourceError):
        await stage.stage(spec, source, RUN)


@pytest.mark.parametrize("run", ["../escape", "", "old-v80", "a" * 31, "g" * 32])
async def test_invalid_job_id_is_rejected_without_creating_any_output(tmp_path, run):
    root, _, spec, reader = fixture(tmp_path)
    stage = FilesystemNativeStaging(reader, tmp_path / "runs")
    with pytest.raises(NativeSourceError):
        await stage.stage(spec, await reader.resolve(spec), run)
    assert not (tmp_path / "runs").exists()


async def test_stale_receipt_and_existing_destination_are_not_overwritten(tmp_path):
    root, _, spec, reader = fixture(tmp_path)
    source = await reader.resolve(spec)
    stage = FilesystemNativeStaging(reader, tmp_path / "runs")
    with pytest.raises(NativeSourceError):
        await stage.stage(spec, replace(source, manifest_sha256="0" * 64), RUN)
    assert not (tmp_path / "runs").exists()
    target = tmp_path / "runs" / RUN / "native-source"
    target.mkdir(parents=True)
    sentinel = target / "keep.txt"
    sentinel.write_bytes(b"existing")
    with pytest.raises(NativeSourceError):
        await stage.stage(spec, source, RUN)
    assert sentinel.read_bytes() == b"existing" and list(target.iterdir()) == [sentinel]


async def test_symlinked_job_directory_is_rejected(tmp_path):
    root, _, spec, reader = fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    jobs = tmp_path / "runs"
    jobs.mkdir()
    (jobs / RUN).symlink_to(outside, target_is_directory=True)
    stage = FilesystemNativeStaging(reader, jobs)
    with pytest.raises(NativeSourceError):
        await stage.stage(spec, await reader.resolve(spec), RUN)
    assert not list(outside.iterdir())


@pytest.mark.parametrize("damage", ["source", "manifest", "snapshot", "extra"])
async def test_tampering_during_copy_cannot_return_a_verified_snapshot(
    tmp_path, monkeypatch, damage
):
    from src.adapters.artifacts import native_staging as module

    root, _, spec, reader = fixture(tmp_path)
    source = await reader.resolve(spec)
    jobs = tmp_path / "runs"
    stage = FilesystemNativeStaging(reader, jobs)
    actual_path = module.source_asset_path

    def injected(origin, name):
        path = actual_path(origin, name)
        if name == "native.blend":
            if damage == "source":
                path.write_bytes(b"tampered-data")
            elif damage == "manifest":
                manifest = root / "SHA256.json"
                manifest.write_bytes(manifest.read_bytes() + b" ")
            elif damage == "snapshot":
                (jobs / RUN / "native-source" / "README.md").write_bytes(b"wrong")
            else:
                (jobs / RUN / "native-source" / "extra.bin").write_bytes(b"unlisted")
        return path

    monkeypatch.setattr(module, "source_asset_path", injected)
    with pytest.raises(NativeSourceError):
        await stage.stage(spec, source, RUN)
    assert json.loads((jobs / RUN / "native-source-failure.json").read_text())["verified"] is False
    assert not (jobs / RUN / "native-source-receipt.json").exists()


async def test_repeated_cancellation_drains_file_worker_and_leaves_no_success_receipt(
    tmp_path, monkeypatch
):
    import asyncio
    import threading

    root, _, spec, reader = fixture(tmp_path)
    source = await reader.resolve(spec)
    jobs = tmp_path / "runs"
    stage = FilesystemNativeStaging(reader, jobs)
    original_copy = stage._copy
    started, release = threading.Event(), threading.Event()

    def slow_copy(*args):
        started.set()
        assert release.wait(3)
        return original_copy(*args)

    monkeypatch.setattr(stage, "_copy", slow_copy)
    task = asyncio.create_task(stage.stage(spec, source, RUN))
    try:
        assert await asyncio.to_thread(started.wait, 1)
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0.01)
            assert not task.done()
    finally:
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not (jobs / RUN / "native-source-receipt.json").exists()
    assert (jobs / RUN / "native-source-failure.json").is_file()


async def test_cancelled_collision_cannot_erase_another_completed_snapshot(tmp_path, monkeypatch):
    import asyncio
    import threading

    root, _, spec, reader = fixture(tmp_path)
    source = await reader.resolve(spec)
    jobs = tmp_path / "runs"
    stage = FilesystemNativeStaging(reader, jobs)
    await stage.stage(spec, source, RUN)
    receipt = jobs / RUN / "native-source-receipt.json"
    original = receipt.read_bytes()
    original_copy = stage._copy
    started, release = threading.Event(), threading.Event()

    def blocked_collision(*args):
        started.set()
        assert release.wait(3)
        return original_copy(*args)

    monkeypatch.setattr(stage, "_copy", blocked_collision)
    task = asyncio.create_task(stage.stage(spec, source, RUN))
    try:
        assert await asyncio.to_thread(started.wait, 1)
        task.cancel()
        await asyncio.sleep(0.01)
        assert not task.done()
    finally:
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert receipt.read_bytes() == original
    assert not (jobs / RUN / "native-source-failure.json").exists()


async def test_growing_source_stops_before_writing_beyond_verified_budget(tmp_path, monkeypatch):
    from src.adapters.artifacts import native_staging as module

    root, _, spec, reader = fixture(tmp_path)
    source = await reader.resolve(spec)
    jobs = tmp_path / "runs"
    stage = FilesystemNativeStaging(reader, jobs)
    actual_path = module.source_asset_path

    def enlarged(origin, name):
        path = actual_path(origin, name)
        if origin == root and name == "README.md":
            path.write_bytes(b"x" * (source.total_bytes + 100))
        return path

    monkeypatch.setattr(module, "source_asset_path", enlarged)
    with pytest.raises(NativeSourceError, match="verified byte budget"):
        await stage.stage(spec, source, RUN)
    assert (jobs / RUN / "native-source" / "README.md").stat().st_size == 0
    assert not (jobs / RUN / "native-source-receipt.json").exists()


async def test_receipt_io_failure_is_a_safe_failure_with_diagnostics(tmp_path, monkeypatch):
    from pathlib import Path

    root, _, spec, reader = fixture(tmp_path)
    source = await reader.resolve(spec)
    jobs = tmp_path / "runs"
    stage = FilesystemNativeStaging(reader, jobs)
    actual_open = Path.open

    def denied(path, *args, **kwargs):
        if path.name == "native-source-receipt.json":
            raise PermissionError(f"denied {path}")
        return actual_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(NativeSourceError) as error:
        await stage.stage(spec, source, RUN)
    assert str(tmp_path) not in str(error.value)
    assert not (jobs / RUN / "native-source-receipt.json").exists()
    assert (jobs / RUN / "native-source-failure.json").is_file()
