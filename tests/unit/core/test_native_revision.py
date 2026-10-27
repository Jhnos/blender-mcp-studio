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
