"""One current selection is prepared through injected source and staging ports."""

from src.adapters.artifacts.native_staging import FilesystemNativeStaging
from src.core.use_cases.artifact_catalog import ArtifactCatalog
from src.core.use_cases.native_revision import NativeRevisionService
from tests.unit.adapters.test_native_source import fixture


async def test_preparation_captures_one_current_selection_and_preserves_originals(tmp_path):
    root, manifest, spec, reader = fixture(tmp_path)
    calls = 0

    def current():
        nonlocal calls
        calls += 1
        return {
            "spec_version": "1",
            "name": f"selected-{calls}",
            "source": {
                "root_dir": "models/selected",
                "stl_glob": spec.source.stl_glob,
                "project_3mf": "plate.3mf",
            },
        }

    catalog = ArtifactCatalog((tmp_path,), 10, current, native_sources=reader)
    service = NativeRevisionService(catalog, FilesystemNativeStaging(reader, tmp_path / "runs"))
    before = {name: (root / name).read_bytes() for name in [*manifest, "SHA256.json"]}
    first = await service.prepare_source("a" * 32)
    assert calls == 1 and first.source.model_name == "selected-1"
    second = await service.prepare_source("b" * 32)
    assert calls == 2 and second.source.model_name == "selected-2"
    assert before == {name: (root / name).read_bytes() for name in before}
    assert (tmp_path / "runs" / first.directory / "native.blend").is_file()


async def test_revision_keeps_the_captured_print_target_when_selection_changes_during_staging(
    tmp_path,
):
    from dataclasses import FrozenInstanceError

    import pytest

    from src.core.domain.native_revision import NativeRevisionRequest

    _, _, spec, reader = fixture(tmp_path)
    selected = {
        "spec_version": "1",
        "name": "first",
        "source": {
            "root_dir": "models/selected",
            "stl_glob": spec.source.stl_glob,
            "project_3mf": "plate.3mf",
        },
        "print_target": {"layer_height_mm": 0.2, "support": True, "brim_mm": 3},
    }
    calls = 0

    def current():
        nonlocal calls
        calls += 1
        return selected

    actual = FilesystemNativeStaging(reader, tmp_path / "runs")

    class ChangingSelection:
        async def stage(self, captured_spec, expected, run_id):
            selected["name"] = "later"
            selected["print_target"] = {"layer_height_mm": 0.4, "support": False, "brim_mm": 0}
            return await actual.stage(captured_spec, expected, run_id)

    service = NativeRevisionService(
        ArtifactCatalog((tmp_path,), 10, current, native_sources=reader), ChangingSelection()
    )
    request = NativeRevisionRequest("screen-clamp", 30)
    prepared = await service.prepare_revision("c" * 32, request)
    assert calls == 1
    assert prepared.spec.name == prepared.staged.source.model_name == "first"
    assert prepared.request is request and prepared.request.target_angle_deg == 30
    assert prepared.spec.print_target.layer_height_mm == 0.2
    assert prepared.spec.print_target.support is True
    assert prepared.spec.print_target.brim_mm == 3
    assert selected["name"] == "later"
    with pytest.raises(FrozenInstanceError):
        prepared.spec.print_target.layer_height_mm = 0.4


async def test_a_staging_receipt_cannot_replace_the_captured_source(tmp_path):
    from dataclasses import replace

    import pytest

    from src.core.domain.native_revision import NativeRevisionError, StagedNativeSource

    _, _, spec, reader = fixture(tmp_path)
    selected = {
        "spec_version": "1",
        "name": "selected",
        "source": {
            "root_dir": "models/selected",
            "stl_glob": spec.source.stl_glob,
            "project_3mf": "plate.3mf",
        },
    }

    class WrongReceipt:
        async def stage(self, _, expected, run_id):
            return StagedNativeSource(replace(expected, model_name="another-source"), run_id)

    service = NativeRevisionService(
        ArtifactCatalog((tmp_path,), 10, lambda: selected, native_sources=reader), WrongReceipt()
    )
    with pytest.raises(NativeRevisionError, match="captured selection"):
        await service.prepare_source("d" * 32)


async def test_execute_revision_passes_the_same_capture_to_its_injected_runner(tmp_path):
    from unittest.mock import AsyncMock

    from src.core.domain.native_revision import (
        NativeRevisionRequest,
        NativeRevisionResult,
        SourceArtifact,
    )

    _, _, spec, reader = fixture(tmp_path)
    calls = 0

    def current():
        nonlocal calls
        calls += 1
        return {
            "spec_version": "1",
            "name": "selected",
            "source": {
                "root_dir": "models/selected",
                "stl_glob": spec.source.stl_glob,
                "project_3mf": "plate.3mf",
            },
        }

    runner = AsyncMock()

    async def execute(prepared):
        return NativeRevisionResult(
            prepared,
            "a" * 32 + "/native-execution",
            prepared.staged.source.native,
            SourceArtifact("changed-surfaces.json", "0" * 64, 2),
        )

    runner.execute.side_effect = execute
    service = NativeRevisionService(
        ArtifactCatalog((tmp_path,), 10, current, native_sources=reader),
        FilesystemNativeStaging(reader, tmp_path / "runs"),
        runner=runner,
    )
    request = NativeRevisionRequest("screen-clamp", 30)
    result = await service.execute_revision("a" * 32, request)
    assert calls == 1 and result.prepared.request is request
    assert runner.execute.call_args.args[0] is result.prepared


async def test_queued_native_capture_never_reselects_or_reparses_later_defaults(tmp_path):
    from src.core.domain.native_revision import NativeRevisionRequest

    _, _, spec, reader = fixture(tmp_path)
    selected = {
        "spec_version": "1",
        "name": "selected",
        "source": {
            "root_dir": "models/selected",
            "stl_glob": spec.source.stl_glob,
            "project_3mf": "plate.3mf",
        },
        "print_target": {"layer_height_mm": 0.2, "support": True, "brim_mm": 3},
    }
    calls = 0

    def current():
        nonlocal calls
        calls += 1
        return selected

    catalog = ArtifactCatalog((tmp_path,), 10, current, native_sources=reader)
    service = NativeRevisionService(catalog, FilesystemNativeStaging(reader, tmp_path / "runs"))
    intent = NativeRevisionRequest("screen-clamp", 30)
    captured = await service.capture_revision(catalog.current(), intent)
    assert calls == 1 and not (tmp_path / "runs").exists()
    selected["name"] = "later"
    selected["print_target"] = {"layer_height_mm": 0.3, "support": False, "brim_mm": 0}
    prepared = await service.prepare_captured("d" * 32, captured)
    assert calls == 1 and prepared.spec is captured.spec and prepared.request is intent
    assert prepared.staged.source == captured.source
    assert prepared.spec.print_target.layer_height_mm == 0.2
    assert prepared.spec.print_target.support and prepared.spec.print_target.brim_mm == 3
